# mindx/tools/system_health_tool.py
"""
SystemHealthTool for mindX

This tool is a refactoring of a classic imperative system monitoring agent into a
callable, modular tool for the mindX Augmentic Intelligence ecosystem. It provides
discrete, callable functions for monitoring system resources (CPU, disk, network, temp)
and performing basic remediation actions.

Each function returns a structured dictionary, allowing the calling agent to reason
about the outcome and build dynamic plans. The tool is configured via the central
mindX Config object under the 'tools.system_health' key.
"""
import os
import psutil
import subprocess
import json
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import asyncio
from typing import Dict, Any, Optional

from core.bdi_agent import BaseTool
from utils.config import Config
from utils.logging_config import get_logger

class SystemHealthTool(BaseTool):
    """A tool for monitoring system health and performing basic administrative tasks."""

    def __init__(self, config: Optional[Config] = None, **kwargs):
        """
        Initializes the SystemHealthTool.

        Args:
            config: The main mindX Config object.
        """
        super().__init__(config=config, **kwargs)
        # The BaseTool's __init__ already sets self.config and self.logger
        
        # Task dispatcher maps a command string to a class method
        self.tasks = {
            "monitor_cpu": self.monitor_cpu,
            "monitor_memory_disk": self.monitor_memory_and_disk,
            "monitor_network": self.monitor_network,
            "monitor_temperatures": self.monitor_temperatures,
            "get_top_cpu_processes": self.get_top_cpu_processes,
            "clean_log_directory": self.clean_log_directory,
            "update_man_db": self.update_man_db_if_permitted,
            "kill_stale_processes": self.self_healing
        }
        self.logger.info("SystemHealthTool initialized.")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Executes a specific system health task.

        Args:
            **kwargs: Must contain a 'task' key specifying which action to perform.
                      e.g., {"task": "monitor_cpu"}

        Returns:
            A dictionary containing the status and result of the executed task.
        """
        task_name = kwargs.get("task")
        if not task_name:
            return {"status": "ERROR", "message": "No 'task' specified in arguments."}

        handler = self.tasks.get(task_name)
        if not handler:
            return {"status": "ERROR", "message": f"Unknown task: '{task_name}'"}

        self.logger.info(f"Executing system health task: '{task_name}'")
        try:
            # Pass through any additional kwargs to the handler
            result = await handler(**kwargs)
            return result
        except Exception as e:
            self.logger.error(f"Error executing task '{task_name}': {e}", exc_info=True)
            return {"status": "ERROR", "message": str(e)}

    async def _send_email_alert(self, subject: str, body: str) -> bool:
        """Helper method to send email alerts if configured."""
        if not self.config.get("tools.system_health.email_alerts", False):
            return False
        
        recipient = self.config.get("tools.system_health.email_recipient")
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "system-agent@mindx.local"
        msg["To"] = recipient
        try:
            # Note: smtplib is synchronous. For a truly async system, aioesmtp would be better.
            with smtplib.SMTP("localhost") as server:
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())
            self.logger.info(f"Email alert sent to {recipient} with subject: {subject}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False

    async def monitor_cpu(self, **kwargs) -> Dict[str, Any]:
        """Monitors CPU usage and returns status and data."""
        cpu_usage = psutil.cpu_percent(interval=1)
        threshold = self.config.get("tools.system_health.cpu_alert_threshold", 90)
        
        if cpu_usage > threshold:
            message = f"High CPU usage detected: {cpu_usage}%"
            self.logger.warning(message)
            await self._send_email_alert("High CPU Usage Alert", message)
            return {"status": "ALERT", "cpu_usage": cpu_usage, "threshold": threshold, "message": message}
        
        return {"status": "OK", "cpu_usage": cpu_usage, "threshold": threshold}

    async def monitor_memory_and_disk(self, **kwargs) -> Dict[str, Any]:
        """Monitors memory and root disk usage."""
        mem_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage("/")
        mem_threshold = self.config.get("tools.system_health.mem_alert_threshold", 90)
        disk_threshold = self.config.get("tools.system_health.disk_alert_threshold", 80)
        
        alerts = []
        if mem_info.percent > mem_threshold:
            alerts.append(f"High Memory Usage: {mem_info.percent}%")
        if disk_info.percent > disk_threshold:
            alerts.append(f"High Disk Usage: {disk_info.percent}%")

        if alerts:
            message = ", ".join(alerts)
            self.logger.warning(message)
            await self._send_email_alert("System Resource Alert", message)
            return {"status": "ALERT", "memory_usage": mem_info.percent, "disk_usage": disk_info.percent, "message": message}

        return {"status": "OK", "memory_usage": mem_info.percent, "disk_usage": disk_info.percent}

    async def monitor_network(self, **kwargs) -> Dict[str, Any]:
        """Monitors network usage over a 1-second interval."""
        net_before = psutil.net_io_counters()
        await asyncio.sleep(1)
        net_after = psutil.net_io_counters()
        
        sent_kbs = (net_after.bytes_sent - net_before.bytes_sent) / 1024
        recv_kbs = (net_after.bytes_recv - net_before.bytes_recv) / 1024
        threshold_kbs = self.config.get("tools.system_health.network_alert_threshold", 1000)

        if max(sent_kbs, recv_kbs) > threshold_kbs:
            message = f"High network usage detected: Sent={sent_kbs:.2f} KB/s, Received={recv_kbs:.2f} KB/s"
            self.logger.warning(message)
            await self._send_email_alert("High Network Usage Alert", message)
            return {"status": "ALERT", "sent_kbs": sent_kbs, "recv_kbs": recv_kbs, "message": message}

        return {"status": "OK", "sent_kbs": sent_kbs, "recv_kbs": recv_kbs}
        
    async def get_top_cpu_processes(self, **kwargs) -> Dict[str, Any]:
        """Returns the top 10 CPU-consuming processes."""
        self.logger.info("Investigating top CPU processes.")
        try:
            # Using subprocess for portability and to avoid complex psutil logic
            output = subprocess.check_output(["ps", "aux", "--sort=-%cpu", "--no-headers"], text=True)
            top_lines = output.strip().split("\n")[:10]
            return {"status": "SUCCESS", "processes": top_lines}
        except Exception as e:
            self.logger.error(f"Failed to gather process list: {e}")
            return {"status": "ERROR", "message": f"Failed to run 'ps': {e}"}

    async def clean_log_directory(self, **kwargs) -> Dict[str, Any]:
        """Removes all files in the specified log directory."""
        log_dir_path = kwargs.get("directory", "/var/log/aion")
        self.logger.warning(f"Attempting disk cleanup in '{log_dir_path}'.")
        
        if not os.path.isdir(log_dir_path):
             return {"status": "ERROR", "message": f"Directory not found: {log_dir_path}"}
             
        removed_files = []
        errors = []
        try:
            for item in os.listdir(log_dir_path):
                item_path = os.path.join(log_dir_path, item)
                if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                        removed_files.append(item)
                    except Exception as e_file:
                        errors.append(f"Failed to remove {item}: {e_file}")
            
            message = f"Cleanup complete. Removed {len(removed_files)} files."
            if errors:
                message += f" Encountered {len(errors)} errors."
            self.logger.info(message)
            return {"status": "SUCCESS", "removed_count": len(removed_files), "errors": errors, "message": message}
        except Exception as e:
            self.logger.error(f"Failed to clean up logs in {log_dir_path}: {e}")
            return {"status": "ERROR", "message": f"General error cleaning directory: {e}"}

    async def update_man_db_if_permitted(self, **kwargs) -> Dict[str, Any]:
        """Updates the manual page index database if CPU is below a threshold."""
        cpu_permit_threshold = self.config.get("tools.system_health.cpu_permit_man_update", 50)
        cpu_usage = psutil.cpu_percent(interval=1)

        if cpu_usage < cpu_permit_threshold:
            self.logger.info(f"CPU usage low ({cpu_usage}%), running `mandb`.")
            try:
                # Use asyncio's subprocess for non-blocking execution
                process = await asyncio.create_subprocess_exec("mandb", "-q", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = await process.communicate()
                if process.returncode == 0:
                    message = "Manual page indexes updated successfully."
                    self.logger.info(message)
                    return {"status": "SUCCESS", "executed": True, "message": message}
                else:
                    message = f"`mandb` update failed with code {process.returncode}: {stderr.decode()}"
                    self.logger.error(message)
                    return {"status": "ERROR", "executed": True, "message": message}
            except FileNotFoundError:
                return {"status": "ERROR", "executed": False, "message": "`mandb` command not found."}
            except Exception as e:
                return {"status": "ERROR", "executed": False, "message": f"`mandb` update failed: {e}"}
        else:
            message = f"CPU usage {cpu_usage}% too high for `mandb` update (threshold: {cpu_permit_threshold}%)."
            self.logger.info(message)
            return {"status": "SKIPPED", "executed": False, "message": message}

    async def self_healing(self, **kwargs) -> Dict[str, Any]:
        """Kills stale Python processes running longer than a configured duration."""
        max_runtime_hours = kwargs.get("max_runtime_hours", 1)
        process_name_filter = kwargs.get("process_name", "python")
        
        max_runtime_seconds = max_runtime_hours * 3600
        killed_processes = []
        
        for proc in psutil.process_iter(['pid', 'create_time', 'cmdline', 'name']):
            try:
                if process_name_filter in (proc.info.get("name", "") or "").lower():
                    running_time = time.time() - proc.info['create_time']
                    if running_time > max_runtime_seconds:
                        self.logger.warning(f"Killing stale '{process_name_filter}' process PID {proc.info['pid']} running for {running_time:.0f}s")
                        proc.kill()
                        killed_processes.append({"pid": proc.info['pid'], "runtime": running_time})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        message = f"Self-healing complete. Killed {len(killed_processes)} stale processes."
        self.logger.info(message)
        return {"status": "SUCCESS", "killed_count": len(killed_processes), "details": killed_processes}
