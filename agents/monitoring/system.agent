# system.agent: Autonomous System Monitoring and Management

## Overview
`system.agent` is a Python-based autonomous monitoring agent designed to ensure the health, security, and efficiency of the system. It operates within the **AION chroot environment**, providing real-time monitoring, logging, and self-healing capabilities.

## Features
1. **Real-Time Monitoring**:
   - Tracks CPU, memory, and disk usage.
   - Detects anomalies and takes corrective action.

2. **Self-Healing**:
   - Removes stale processes.
   - Cleans up disk space by managing logs and temporary files.

3. **Resource Optimization**:
   - Runs lightweight tasks when system resources are available.
   - Updates system components like manual page indexes (`mandb`) when CPU usage is low.

4. **Security and Auditing**:
   - Logs important activities such as `.bash_history` for user accountability.
   - Provides alerts for high resource usage.

5. **Logging and Alerting**:
   - Maintains detailed logs for debugging and system analysis.
   - Sends email alerts for critical issues (optional).

---

## How `system.agent` Works
The agent runs continuously as a service, performing the following tasks:
1. **System Monitoring**:
   - Uses Python’s `psutil` library to gather system metrics.
   - Logs CPU, memory, and disk statistics to `/var/log/aion/system_agent.log`.

2. **Anomaly Detection**:
   - Triggers alerts when resource usage exceeds predefined thresholds.
   - Example: If CPU usage > 90%, it logs the top processes using CPU.

3. **Self-Healing Actions**:
   - Cleans up old logs when disk usage is high.
   - Terminates long-running or stalled processes.

4. **Background Maintenance**:
   - Updates system components like manpage indexes when system load is low.

---

## Supervisor Integration

**Supervisor** is a process control system that ensures `system.agent` runs persistently and autonomously. It provides:
1. **Automatic Restart**:
   - If `system.agent` crashes, Supervisor restarts it automatically.

2. **Logging**:
   - Captures `system.agent` output and error logs:
     - **Stdout Log**: `/var/log/aion/system_agent.out.log`
     - **Stderr Log**: `/var/log/aion/system_agent.err.log`

3. **Process Management**:
   - Allows manual start, stop, restart, and status checks for `system.agent`.

---

## Configuration

The Supervisor configuration file for `system.agent` is located at:
`/etc/supervisor/conf.d/system_agent.conf`

### Example Configuration:
```ini
[program:system_agent]
command=/opt/aion/venv/bin/python /opt/aion/system_agent/system_agent.py
autostart=true
autorestart=true
stderr_logfile=/var/log/aion/system_agent.err.log
stdout_logfile=/var/log/aion/system_agent.out.log
user=aion
