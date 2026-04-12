"""
HostingerVPSAgent — I know my home. I manage my infrastructure.

Three MCP channels for reaching the VPS:
  1. SSH (primary) — root@168.231.126.58, direct shell access
  2. Hostinger API — https://developers.hostinger.com/api/vps/v1/
     restart, metrics, backups, status (no SSH needed)
  3. mindX Backend API — https://mindx.pythai.net/
     health, diagnostics, governance, activity (public endpoints)

Persistent state in data/deployment/vps_state.json survives restarts.
SSH credentials from env (MINDX_VPS_SSH_KEY) or ~/.ssh/id_rsa.
Hostinger API key from env (HOSTINGER_API_KEY) or BANKON vault.

Available Hostinger API endpoints (discovered 2026-04-12):
  GET  /virtual-machines                    — list VPS instances
  GET  /virtual-machines/{id}               — VPS details
  GET  /virtual-machines/{id}/actions       — action history
  GET  /virtual-machines/{id}/backups       — backup list
  GET  /virtual-machines/{id}/metrics       — CPU/RAM/disk/network metrics
  POST /virtual-machines/{id}/start         — start VPS
  POST /virtual-machines/{id}/stop          — stop VPS
  POST /virtual-machines/{id}/restart       — restart VPS
  POST /virtual-machines/{id}/recreate      — recreate VPS
  GET  /data-centers                        — list data centers
  GET  /templates                           — list OS templates

mindX Backend public endpoints (no auth):
  GET  /health                              — service health
  GET  /diagnostics/live                    — full system telemetry
  GET  /activity/stream                     — SSE real-time events
  GET  /activity/recent                     — recent activity (JSON)
  GET  /inference/status                    — inference providers
  GET  /dojo/standings                      — agent reputation
  GET  /governance/status                   — governance chain

Usage:
    agent = await HostingerVPSAgent.get_instance()
    result = await agent.deploy()              # scp + restart on VPS
    result = await agent.check_health()        # SSH + API + backend
    result = await agent.restart_via_api()     # Hostinger API restart (no SSH)
    result = await agent.get_metrics()         # Hostinger API metrics
    result = await agent.get_backups()         # Hostinger API backups
    result = await agent.check_backend()       # mindX backend /diagnostics/live

Author: Professor Codephreak
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.config import PROJECT_ROOT, Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

STATE_FILE = PROJECT_ROOT / "data" / "deployment" / "vps_state.json"

# Default VPS parameters (from agents/hostinger.vps.agent)
DEFAULT_HOST = "168.231.126.58"
DEFAULT_USER = "mindx"
DEFAULT_PORT = 22
DEFAULT_REMOTE_PATH = "/home/mindx/mindX"
DEFAULT_SERVICE = "mindx"
DEFAULT_REPO = "https://github.com/AgenticPlace/mindX.git"
DEFAULT_BRANCH = "main"
VPS_ID = "926215"
HOSTINGER_API = "https://developers.hostinger.com/api/vps/v1"
MINDX_BACKEND = "https://mindx.pythai.net"


@dataclass
class VPSConnectionState:
    """Persistent connection state — survives process restarts."""
    host: str = DEFAULT_HOST
    user: str = DEFAULT_USER
    port: int = DEFAULT_PORT
    remote_path: str = DEFAULT_REMOTE_PATH
    ssh_key_path: str = ""
    service_name: str = DEFAULT_SERVICE

    # Connection health
    last_connected: float = 0.0
    last_connection_success: bool = False
    last_error: str = ""
    consecutive_failures: int = 0

    # Deployment history
    last_deploy: float = 0.0
    last_deploy_success: bool = False
    last_deploy_commit: str = ""
    deploy_count: int = 0

    # VPS state (from last health check)
    vps_hostname: str = ""
    vps_uptime: str = ""
    vps_ram_used_pct: float = 0.0
    vps_disk_used_pct: float = 0.0
    vps_ollama_models: List[str] = field(default_factory=list)
    vps_service_active: bool = False
    last_health_check: float = 0.0


class HostingerVPSAgent:
    """
    I manage the Hostinger VPS at mindx.pythai.net.
    Persistent SSH connection state, deployment, health checks, service control.
    """

    _instance: Optional["HostingerVPSAgent"] = None

    def __init__(self, memory_agent=None, config: Optional[Config] = None):
        self.config = config or Config()
        self.memory_agent = memory_agent
        self.log_prefix = "[HostingerVPS]"
        self.state = VPSConnectionState()
        self._load_state()
        self._resolve_ssh_config()
        self._hostinger_api_key = os.getenv("HOSTINGER_API_KEY", "")
        logger.info(
            f"{self.log_prefix} Initialized — "
            f"ssh={'set' if self.state.ssh_key_path else 'unset'}, "
            f"api={'set' if self._hostinger_api_key else 'unset'}, "
            f"backend={MINDX_BACKEND}"
        )

    @classmethod
    async def get_instance(cls, memory_agent=None, config=None) -> "HostingerVPSAgent":
        if cls._instance is None:
            cls._instance = cls(memory_agent, config)
        elif memory_agent and not cls._instance.memory_agent:
            cls._instance.memory_agent = memory_agent
        return cls._instance

    # -----------------------------------------------------------------------
    # Configuration — resolve SSH credentials from env/vault/config
    # -----------------------------------------------------------------------

    def _resolve_ssh_config(self):
        """Resolve SSH connection parameters from environment, vault, or config."""
        # Host override
        host = os.getenv("MINDX_VPS_HOST")
        if host:
            self.state.host = host

        # User override
        user = os.getenv("MINDX_VPS_USER")
        if user:
            self.state.user = user

        # Port override
        port = os.getenv("MINDX_VPS_PORT")
        if port:
            self.state.port = int(port)

        # SSH key — try multiple sources
        key_path = os.getenv("MINDX_VPS_SSH_KEY")
        if not key_path:
            # Try common key locations
            candidates = [
                Path.home() / ".ssh" / "mindx_vps",
                Path.home() / ".ssh" / "id_ed25519",
                Path.home() / ".ssh" / "id_rsa",
            ]
            for p in candidates:
                if p.exists():
                    key_path = str(p)
                    break

        if key_path and Path(key_path).exists():
            self.state.ssh_key_path = key_path

        # Remote path override
        remote = os.getenv("MINDX_VPS_REMOTE_PATH")
        if remote:
            self.state.remote_path = remote

    # -----------------------------------------------------------------------
    # State persistence
    # -----------------------------------------------------------------------

    def _load_state(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                for k, v in data.items():
                    if hasattr(self.state, k):
                        setattr(self.state, k, v)
        except Exception:
            pass

    def _save_state(self):
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = asdict(self.state)
            data["_saved_at"] = time.time()
            data["_saved_from"] = os.uname().nodename
            STATE_FILE.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.debug(f"{self.log_prefix} Failed to save state: {e}")

    # -----------------------------------------------------------------------
    # SSH execution — the core transport layer
    # -----------------------------------------------------------------------

    async def _ssh_exec(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Execute a command on the VPS via SSH.
        Returns (success, stdout, stderr).
        Persists connection state on every call.
        """
        ssh_args = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "BatchMode=yes",
        ]

        if self.state.ssh_key_path:
            ssh_args.extend(["-i", self.state.ssh_key_path])

        if self.state.port != 22:
            ssh_args.extend(["-p", str(self.state.port)])

        ssh_args.append(f"{self.state.user}@{self.state.host}")
        ssh_args.append(command)

        try:
            proc = await asyncio.create_subprocess_exec(
                *ssh_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            success = proc.returncode == 0

            # Update connection state
            self.state.last_connected = time.time()
            self.state.last_connection_success = success
            if success:
                self.state.consecutive_failures = 0
                self.state.last_error = ""
            else:
                self.state.consecutive_failures += 1
                self.state.last_error = stderr_str[:200]

            self._save_state()
            return success, stdout_str, stderr_str

        except asyncio.TimeoutError:
            self.state.consecutive_failures += 1
            self.state.last_error = f"SSH timeout after {timeout}s"
            self._save_state()
            return False, "", f"Timeout after {timeout}s"

        except Exception as e:
            self.state.consecutive_failures += 1
            self.state.last_error = str(e)[:200]
            self._save_state()
            return False, "", str(e)

    # -----------------------------------------------------------------------
    # Operations
    # -----------------------------------------------------------------------

    async def check_health(self) -> Dict[str, Any]:
        """Query VPS status: uptime, RAM, disk, service, Ollama."""
        cmd = (
            "echo HOSTNAME=$(hostname);"
            "echo UPTIME=$(uptime -p);"
            "echo RAM=$(free -m | awk '/Mem:/{printf \"%.1f\", $3/$2*100}');"
            "echo DISK=$(df -h / | awk 'NR==2{print $5}' | tr -d '%');"
            "echo SERVICE=$(systemctl is-active mindx 2>/dev/null || echo inactive);"
            "echo OLLAMA=$(curl -s http://localhost:11434/api/tags 2>/dev/null "
            "| python3 -c \"import sys,json;print(','.join(m['name'] for m in json.load(sys.stdin).get('models',[])))\" 2>/dev/null || echo unavailable)"
        )

        success, stdout, stderr = await self._ssh_exec(cmd, timeout=15)
        if not success:
            return {"success": False, "error": stderr or "SSH connection failed", "host": self.state.host}

        # Parse key=value output
        health = {"success": True, "host": self.state.host, "raw": stdout}
        for line in stdout.split("\n"):
            if "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if key == "HOSTNAME":
                    self.state.vps_hostname = val
                    health["hostname"] = val
                elif key == "UPTIME":
                    self.state.vps_uptime = val
                    health["uptime"] = val
                elif key == "RAM":
                    try:
                        self.state.vps_ram_used_pct = float(val)
                    except ValueError:
                        pass
                    health["ram_used_pct"] = val
                elif key == "DISK":
                    try:
                        self.state.vps_disk_used_pct = float(val)
                    except ValueError:
                        pass
                    health["disk_used_pct"] = val
                elif key == "SERVICE":
                    self.state.vps_service_active = val == "active"
                    health["service"] = val
                elif key == "OLLAMA":
                    models = [m.strip() for m in val.split(",") if m.strip() and m.strip() != "unavailable"]
                    self.state.vps_ollama_models = models
                    health["ollama_models"] = models
                    health["ollama_model_count"] = len(models)

        self.state.last_health_check = time.time()
        self._save_state()

        logger.info(
            f"{self.log_prefix} Health: {health.get('hostname', '?')} | "
            f"RAM {health.get('ram_used_pct', '?')}% | Disk {health.get('disk_used_pct', '?')}% | "
            f"Service {health.get('service', '?')} | {health.get('ollama_model_count', 0)} models"
        )
        return health

    async def deploy(self, branch: str = DEFAULT_BRANCH) -> Dict[str, Any]:
        """Deploy: git pull on VPS + restart service."""
        deploy_record = {
            "started_at": time.time(),
            "branch": branch,
            "host": self.state.host,
        }

        # Step 1: git pull
        logger.info(f"{self.log_prefix} Deploying: git pull origin {branch}")
        pull_cmd = f"cd {self.state.remote_path} && git pull origin {branch} 2>&1"
        success, stdout, stderr = await self._ssh_exec(pull_cmd, timeout=60)

        deploy_record["git_pull"] = {"success": success, "output": stdout[:500]}
        if not success:
            deploy_record["success"] = False
            deploy_record["error"] = stderr[:200] or stdout[:200]
            logger.error(f"{self.log_prefix} git pull failed: {deploy_record['error']}")
            await self._log_operation("deploy_failed", deploy_record)
            return deploy_record

        # Extract commit hash
        commit_cmd = f"cd {self.state.remote_path} && git rev-parse --short HEAD"
        _, commit, _ = await self._ssh_exec(commit_cmd, timeout=10)
        deploy_record["commit"] = commit.strip()

        # Step 2: restart service
        logger.info(f"{self.log_prefix} Restarting service: {self.state.service_name}")
        restart_cmd = f"sudo systemctl restart {self.state.service_name} 2>&1"
        success, stdout, stderr = await self._ssh_exec(restart_cmd, timeout=30)

        deploy_record["restart"] = {"success": success, "output": (stdout or stderr)[:200]}
        if not success:
            deploy_record["success"] = False
            deploy_record["error"] = f"Restart failed: {stderr[:200]}"
            logger.error(f"{self.log_prefix} Restart failed: {stderr[:100]}")
            await self._log_operation("deploy_restart_failed", deploy_record)
            return deploy_record

        # Step 3: verify service is running
        await asyncio.sleep(3)  # Give it a moment to start
        verify_cmd = f"systemctl is-active {self.state.service_name} 2>/dev/null"
        success, status, _ = await self._ssh_exec(verify_cmd, timeout=10)

        deploy_record["service_status"] = status.strip()
        deploy_record["success"] = status.strip() == "active"
        deploy_record["completed_at"] = time.time()
        deploy_record["duration_s"] = deploy_record["completed_at"] - deploy_record["started_at"]

        # Update state
        self.state.last_deploy = time.time()
        self.state.last_deploy_success = deploy_record["success"]
        self.state.last_deploy_commit = deploy_record.get("commit", "")
        self.state.deploy_count += 1
        self._save_state()

        if deploy_record["success"]:
            logger.info(
                f"{self.log_prefix} Deploy SUCCESS — commit {deploy_record.get('commit', '?')} "
                f"in {deploy_record['duration_s']:.1f}s"
            )
        else:
            logger.error(f"{self.log_prefix} Deploy FAILED — service status: {status}")

        await self._log_operation("deploy", deploy_record)
        return deploy_record

    async def restart_service(self) -> Dict[str, Any]:
        """Restart mindx.service on the VPS."""
        cmd = f"sudo systemctl restart {self.state.service_name} 2>&1 && systemctl is-active {self.state.service_name}"
        success, stdout, stderr = await self._ssh_exec(cmd, timeout=30)
        result = {
            "success": success and "active" in stdout,
            "service": self.state.service_name,
            "status": stdout.strip().split("\n")[-1] if stdout else "unknown",
            "host": self.state.host,
        }
        self.state.vps_service_active = result["success"]
        self._save_state()
        return result

    async def check_models(self) -> Dict[str, Any]:
        """List Ollama models installed on the VPS."""
        cmd = (
            "curl -s http://localhost:11434/api/tags 2>/dev/null | "
            "python3 -c \""
            "import sys,json;"
            "d=json.load(sys.stdin);"
            "[print(f'{m[\\\"name\\\"]} {m.get(\\\"details\\\",{}).get(\\\"parameter_size\\\",\\\"?\\\")}')"
            " for m in d.get('models',[])]\""
        )
        success, stdout, stderr = await self._ssh_exec(cmd, timeout=15)
        if not success:
            return {"success": False, "error": stderr or "Cannot reach Ollama on VPS"}

        models = []
        for line in stdout.strip().split("\n"):
            parts = line.strip().split()
            if parts:
                models.append({"name": parts[0], "size": parts[1] if len(parts) > 1 else "?"})

        self.state.vps_ollama_models = [m["name"] for m in models]
        self._save_state()
        return {"success": True, "models": models, "count": len(models), "host": self.state.host}

    async def check_disk(self) -> Dict[str, Any]:
        """Check disk usage on VPS."""
        cmd = "df -h / | awk 'NR==2{print $2,$3,$4,$5}' && du -sh /home/mindx/mindX/data/ 2>/dev/null | cut -f1"
        success, stdout, stderr = await self._ssh_exec(cmd, timeout=15)
        if not success:
            return {"success": False, "error": stderr}

        lines = stdout.strip().split("\n")
        disk_info = lines[0].split() if lines else []
        data_size = lines[1].strip() if len(lines) > 1 else "?"

        return {
            "success": True,
            "total": disk_info[0] if len(disk_info) > 0 else "?",
            "used": disk_info[1] if len(disk_info) > 1 else "?",
            "available": disk_info[2] if len(disk_info) > 2 else "?",
            "used_pct": disk_info[3] if len(disk_info) > 3 else "?",
            "data_dir_size": data_size,
            "host": self.state.host,
        }

    async def tail_logs(self, lines: int = 50) -> Dict[str, Any]:
        """Get recent mindx service logs."""
        cmd = f"journalctl -u {self.state.service_name} --no-pager -n {lines} 2>&1"
        success, stdout, stderr = await self._ssh_exec(cmd, timeout=15)
        return {"success": success, "logs": stdout, "lines": lines, "host": self.state.host}

    async def test_connection(self) -> Dict[str, Any]:
        """Test SSH connection to VPS."""
        success, stdout, stderr = await self._ssh_exec("echo connected && hostname", timeout=10)
        return {
            "success": success,
            "connected": "connected" in stdout,
            "hostname": stdout.split("\n")[-1].strip() if success else "",
            "host": self.state.host,
            "user": self.state.user,
            "key": self.state.ssh_key_path or "(default)",
            "error": stderr if not success else "",
        }

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current persisted state + channel availability."""
        return {
            "channels": {
                "ssh": {"available": bool(self.state.ssh_key_path), "user": self.state.user, "host": self.state.host},
                "hostinger_api": {"available": bool(self._hostinger_api_key), "vps_id": VPS_ID},
                "mindx_backend": {"available": True, "url": MINDX_BACKEND},
            },
            "host": self.state.host,
            "user": self.state.user,
            "port": self.state.port,
            "remote_path": self.state.remote_path,
            "ssh_key_set": bool(self.state.ssh_key_path),
            "hostinger_api_set": bool(self._hostinger_api_key),
            "last_connected": self.state.last_connected,
            "last_connection_success": self.state.last_connection_success,
            "consecutive_failures": self.state.consecutive_failures,
            "last_error": self.state.last_error,
            "last_deploy": self.state.last_deploy,
            "last_deploy_success": self.state.last_deploy_success,
            "last_deploy_commit": self.state.last_deploy_commit,
            "deploy_count": self.state.deploy_count,
            "vps_hostname": self.state.vps_hostname,
            "vps_service_active": self.state.vps_service_active,
            "vps_ram_used_pct": self.state.vps_ram_used_pct,
            "vps_disk_used_pct": self.state.vps_disk_used_pct,
            "vps_ollama_model_count": len(self.state.vps_ollama_models),
            "last_health_check": self.state.last_health_check,
        }

    # -----------------------------------------------------------------------
    # Channel 2: Hostinger API (no SSH needed)
    # -----------------------------------------------------------------------

    async def _hostinger_api_get(self, endpoint: str, timeout: int = 15) -> Optional[Dict]:
        """GET request to Hostinger API."""
        if not self._hostinger_api_key:
            return None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{HOSTINGER_API}/{endpoint}",
                    headers={"Authorization": f"Bearer {self._hostinger_api_key}"},
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"HTTP {resp.status}", "status": resp.status}
        except Exception as e:
            return {"error": str(e)}

    async def _hostinger_api_post(self, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> Optional[Dict]:
        """POST request to Hostinger API."""
        if not self._hostinger_api_key:
            return None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{HOSTINGER_API}/{endpoint}",
                    headers={"Authorization": f"Bearer {self._hostinger_api_key}", "Content-Type": "application/json"},
                    json=data or {},
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def restart_via_api(self) -> Dict[str, Any]:
        """Restart VPS via Hostinger API (no SSH needed)."""
        result = await self._hostinger_api_post(f"virtual-machines/{VPS_ID}/restart")
        if result and "error" not in result:
            logger.info(f"{self.log_prefix} VPS restart triggered via Hostinger API")
            await self._log_operation("api_restart", result)
            return {"success": True, "method": "hostinger_api", **result}
        return {"success": False, "method": "hostinger_api", "error": str(result)}

    async def get_metrics(self, date_from: str = "", date_to: str = "") -> Dict[str, Any]:
        """Get VPS performance metrics (CPU, RAM, disk, network) via Hostinger API."""
        if not date_from:
            from datetime import datetime, timedelta
            date_to = datetime.utcnow().strftime("%Y-%m-%d")
            date_from = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = await self._hostinger_api_get(
            f"virtual-machines/{VPS_ID}/metrics?date_from={date_from}&date_to={date_to}"
        )
        if result and "error" not in result:
            return {"success": True, "method": "hostinger_api", "metrics": result}
        return {"success": False, "method": "hostinger_api", "error": str(result)}

    async def get_backups(self) -> Dict[str, Any]:
        """List VPS backups via Hostinger API."""
        result = await self._hostinger_api_get(f"virtual-machines/{VPS_ID}/backups")
        if result and "error" not in result:
            return {"success": True, "method": "hostinger_api", "backups": result}
        return {"success": False, "method": "hostinger_api", "error": str(result)}

    async def get_vps_info(self) -> Dict[str, Any]:
        """Get full VPS details via Hostinger API."""
        result = await self._hostinger_api_get(f"virtual-machines/{VPS_ID}")
        if result and "error" not in result:
            return {"success": True, "method": "hostinger_api", "vps": result}
        return {"success": False, "method": "hostinger_api", "error": str(result)}

    async def get_actions_history(self) -> Dict[str, Any]:
        """Get VPS action history via Hostinger API."""
        result = await self._hostinger_api_get(f"virtual-machines/{VPS_ID}/actions")
        if result and "error" not in result:
            return {"success": True, "method": "hostinger_api", "actions": result}
        return {"success": False, "method": "hostinger_api", "error": str(result)}

    # -----------------------------------------------------------------------
    # Channel 3: mindX Backend API (public HTTPS, no auth)
    # -----------------------------------------------------------------------

    async def _backend_get(self, path: str, timeout: int = 10) -> Optional[Dict]:
        """GET request to mindX backend."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{MINDX_BACKEND}{path}",
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception:
            return None

    async def check_backend(self) -> Dict[str, Any]:
        """Check mindX backend health and diagnostics via HTTPS."""
        health = await self._backend_get("/health")
        diagnostics = await self._backend_get("/diagnostics/live")
        inference = await self._backend_get("/inference/status")
        dojo = await self._backend_get("/dojo/standings")
        activity = await self._backend_get("/activity/recent?limit=5")

        return {
            "success": health is not None,
            "method": "mindx_backend_https",
            "health": health,
            "system": diagnostics.get("system") if diagnostics else None,
            "agents": len(diagnostics.get("agents", [])) if diagnostics else 0,
            "memories": diagnostics.get("database", {}).get("memories") if diagnostics else None,
            "inference_available": inference.get("available") if inference else None,
            "inference_total": inference.get("total") if inference else None,
            "dojo_agents": len(dojo.get("standings", dojo) if isinstance(dojo, dict) else dojo or []),
            "recent_activity": len(activity.get("events", [])) if activity else 0,
            "autonomous": diagnostics.get("autonomous") if diagnostics else None,
        }

    async def full_health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check using ALL three channels.
        SSH → direct system metrics
        Hostinger API → VPS status + historical metrics
        mindX Backend → application-level health
        """
        results = {"timestamp": time.time(), "channels": {}}

        # Channel 1: SSH
        ssh_result = await self.check_health()
        results["channels"]["ssh"] = ssh_result

        # Channel 2: Hostinger API
        if self._hostinger_api_key:
            api_info = await self.get_vps_info()
            api_metrics = await self.get_metrics()
            results["channels"]["hostinger_api"] = {
                "vps_state": api_info.get("vps", {}).get("state") if api_info.get("success") else "unavailable",
                "metrics_available": api_metrics.get("success", False),
            }
        else:
            results["channels"]["hostinger_api"] = {"available": False, "reason": "HOSTINGER_API_KEY not set"}

        # Channel 3: mindX Backend
        backend_result = await self.check_backend()
        results["channels"]["mindx_backend"] = backend_result

        # Summary
        results["healthy"] = (
            ssh_result.get("success", False) or
            backend_result.get("success", False)
        )
        results["channels_available"] = sum(1 for c in results["channels"].values()
                                            if c.get("success", c.get("available", False)))

        self._save_state()
        await self._log_operation("full_health_check", results)
        return results

    # -----------------------------------------------------------------------
    # MCP Context Registration
    # -----------------------------------------------------------------------

    async def register_mcp_context(self):
        """Register this agent's capabilities as MCP tool definitions."""
        try:
            from tools.communication.mcp_tool import MCPTool
            mcp = MCPTool.__new__(MCPTool)
            # Register VPS management tools for other agents to discover
            await mcp._register_tool(
                tool_id="hostinger_vps_deploy",
                tool_name="VPS Deploy",
                description="Deploy latest code to mindx.pythai.net via SSH (scp + restart)",
                parameters={"branch": {"type": "string", "default": "main"}},
                agent_id="hostinger_vps_agent",
            )
            await mcp._register_tool(
                tool_id="hostinger_vps_health",
                tool_name="VPS Health Check",
                description="Full health check across SSH, Hostinger API, and mindX backend",
                parameters={},
                agent_id="hostinger_vps_agent",
            )
            await mcp._register_tool(
                tool_id="hostinger_vps_restart",
                tool_name="VPS Restart (API)",
                description="Restart VPS via Hostinger API (no SSH needed)",
                parameters={},
                agent_id="hostinger_vps_agent",
            )
            logger.info(f"{self.log_prefix} MCP tools registered (3 capabilities)")
        except Exception as e:
            logger.debug(f"{self.log_prefix} MCP registration skipped: {e}")

    # -----------------------------------------------------------------------
    # Memory logging
    # -----------------------------------------------------------------------

    async def _log_operation(self, operation: str, data: Dict[str, Any]):
        if self.memory_agent:
            try:
                await self.memory_agent.log_process(
                    process_name=f"vps_{operation}",
                    data=data,
                    metadata={"agent_id": "hostinger_vps_agent", "domain": "infrastructure.hosting"}
                )
            except Exception:
                pass
