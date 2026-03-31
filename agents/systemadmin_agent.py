#!/usr/bin/env python3
"""
SystemAdmin Agent - System Administration and Privileged Operations Agent
Author: Professor Codephreak (© Professor Codephreak)
Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
Resources: rage.pythai.net

SystemAdmin Agent provides privileged system operations for AION and other agents
with secure execution and comprehensive logging.
"""

import asyncio
import logging
import os
import subprocess
import pwd
import grp
import stat
import shutil
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class PrivilegeLevel(Enum):
    """System privilege levels"""
    USER = "user"
    ADMIN = "admin"
    ROOT = "root"
    CHROOT = "chroot"


class OperationType(Enum):
    """Types of system operations"""
    FILE_OPERATION = "file_operation"
    PROCESS_MANAGEMENT = "process_management"
    NETWORK_OPERATION = "network_operation"
    SYSTEM_CONFIGURATION = "system_configuration"
    CHROOT_OPERATION = "chroot_operation"


@dataclass
class SystemCommand:
    """System command specification"""
    command: List[str]
    working_directory: Optional[str] = None
    timeout: int = 300
    privilege_level: PrivilegeLevel = PrivilegeLevel.USER
    operation_type: OperationType = OperationType.FILE_OPERATION
    require_confirmation: bool = False


@dataclass
class CommandResult:
    """Result of system command execution"""
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: List[str]
    success: bool = False


class SystemAdminAgent:
    """
    System Administration Agent for privileged operations

    Provides secure system administration capabilities for AION and other agents
    including file operations, process management, and chroot administration.
    """

    def __init__(self, agent_id: str = "systemadmin_agent", parent_agent: str = None):
        self.agent_id = agent_id
        self.parent_agent = parent_agent
        self.logger = logging.getLogger(f"SystemAdminAgent.{agent_id}")

        # Security settings
        self.max_privilege_level = PrivilegeLevel.ADMIN
        self.audit_log_path = "/var/log/mindx/systemadmin_audit.log"
        self.command_history = []

        # Operation limits
        self.max_command_timeout = 3600  # 1 hour
        self.max_file_size = 10 * 1024 * 1024 * 1024  # 10GB

        self.logger.info(f"SystemAdmin Agent {agent_id} initialized for {parent_agent}")

    async def execute_privileged_command(self, command: List[str],
                                       working_directory: Optional[str] = None,
                                       timeout: int = 300,
                                       privilege_level: PrivilegeLevel = PrivilegeLevel.USER) -> CommandResult:
        """
        Execute privileged system command with comprehensive logging and security
        """
        try:
            # Validate command
            if not self._validate_command(command, privilege_level):
                raise PermissionError(f"Command not permitted: {' '.join(command)}")

            # Create command specification
            cmd_spec = SystemCommand(
                command=command,
                working_directory=working_directory,
                timeout=min(timeout, self.max_command_timeout),
                privilege_level=privilege_level
            )

            # Log command execution attempt
            await self._audit_log_command(cmd_spec, "EXECUTE_ATTEMPT")

            # Execute command
            start_time = time.time()
            result = await self._execute_system_command(cmd_spec)
            execution_time = time.time() - start_time

            # Create result
            command_result = CommandResult(
                return_code=result.returncode,
                stdout=result.stdout.decode('utf-8') if result.stdout else '',
                stderr=result.stderr.decode('utf-8') if result.stderr else '',
                execution_time=execution_time,
                command=command,
                success=(result.returncode == 0)
            )

            # Log command completion
            await self._audit_log_command(cmd_spec, "EXECUTE_COMPLETE", command_result)

            # Store in command history
            self.command_history.append({
                'timestamp': time.time(),
                'command': command,
                'result': command_result,
                'parent_agent': self.parent_agent
            })

            self.logger.info(f"Command executed: {' '.join(command)[:100]} - Success: {command_result.success}")
            return command_result

        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            error_result = CommandResult(
                return_code=-1,
                stdout='',
                stderr=str(e),
                execution_time=0.0,
                command=command,
                success=False
            )
            return error_result

    async def copy_directory_structure(self, source: str, target: str,
                                     preserve_permissions: bool = True,
                                     secure: bool = False) -> bool:
        """
        Copy directory structure with permission preservation
        """
        try:
            self.logger.info(f"Copying directory: {source} → {target}")

            # Validate paths
            if not os.path.exists(source):
                self.logger.error(f"Source directory does not exist: {source}")
                return False

            # Create target directory
            os.makedirs(target, exist_ok=True)

            # Use rsync for efficient copying
            rsync_cmd = [
                "rsync",
                "-av",  # Archive mode, verbose
                "--progress"
            ]

            if preserve_permissions:
                rsync_cmd.append("--perms")
                rsync_cmd.append("--owner")
                rsync_cmd.append("--group")

            if secure:
                rsync_cmd.append("--chmod=600")  # Secure permissions

            rsync_cmd.extend([f"{source}/", target])

            # Execute copy operation
            result = await self.execute_privileged_command(
                rsync_cmd,
                timeout=3600,  # 1 hour for large copies
                privilege_level=PrivilegeLevel.ADMIN
            )

            if result.success:
                self.logger.info(f"Directory copy successful: {source} → {target}")

                # Verify copy if secure mode
                if secure:
                    await self._secure_directory_permissions(target)

                return True
            else:
                self.logger.error(f"Directory copy failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Directory copy error: {e}")
            return False

    async def create_chroot_environment(self, chroot_path: str,
                                      base_system: str = "minimal") -> bool:
        """
        Create chroot environment for system isolation
        """
        try:
            self.logger.info(f"Creating chroot environment: {chroot_path}")

            # Create base directory structure
            base_dirs = [
                "bin", "sbin", "lib", "lib64", "usr/bin", "usr/sbin", "usr/lib", "usr/lib64",
                "etc", "var", "tmp", "proc", "sys", "dev", "home", "root"
            ]

            for dir_name in base_dirs:
                dir_path = os.path.join(chroot_path, dir_name)
                os.makedirs(dir_path, exist_ok=True)

            # Set proper permissions
            os.chmod(chroot_path, 0o755)
            os.chmod(os.path.join(chroot_path, "tmp"), 0o1777)  # Sticky bit for tmp

            # Copy essential system binaries if requested
            if base_system != "minimal":
                await self._setup_chroot_binaries(chroot_path)

            # Setup device nodes
            await self._setup_chroot_devices(chroot_path)

            self.logger.info(f"Chroot environment created: {chroot_path}")
            return True

        except Exception as e:
            self.logger.error(f"Chroot creation error: {e}")
            return False

    async def mount_chroot_filesystems(self, chroot_path: str) -> bool:
        """
        Mount necessary filesystems in chroot environment
        """
        try:
            self.logger.info(f"Mounting chroot filesystems: {chroot_path}")

            mount_points = [
                ("proc", "proc", "proc"),
                ("sysfs", "sys", "sysfs"),
                ("/dev", "dev", "bind")
            ]

            for source, target_dir, mount_type in mount_points:
                target = os.path.join(chroot_path, target_dir)

                if mount_type == "bind":
                    mount_cmd = ["mount", "--bind", source, target]
                else:
                    mount_cmd = ["mount", "-t", mount_type, source, target]

                result = await self.execute_privileged_command(
                    mount_cmd,
                    privilege_level=PrivilegeLevel.ROOT
                )

                if not result.success:
                    self.logger.error(f"Failed to mount {source} in chroot")
                    return False

            self.logger.info("Chroot filesystems mounted successfully")
            return True

        except Exception as e:
            self.logger.error(f"Chroot mount error: {e}")
            return False

    async def unmount_chroot_filesystems(self, chroot_path: str) -> bool:
        """
        Safely unmount chroot filesystems
        """
        try:
            self.logger.info(f"Unmounting chroot filesystems: {chroot_path}")

            # Unmount in reverse order
            mount_points = ["dev", "sys", "proc"]

            for mount_point in mount_points:
                target = os.path.join(chroot_path, mount_point)

                if os.path.ismount(target):
                    umount_cmd = ["umount", target]

                    result = await self.execute_privileged_command(
                        umount_cmd,
                        privilege_level=PrivilegeLevel.ROOT
                    )

                    if not result.success:
                        self.logger.warning(f"Failed to unmount {target}")
                        # Try force unmount
                        force_umount_cmd = ["umount", "-f", target]
                        await self.execute_privileged_command(
                            force_umount_cmd,
                            privilege_level=PrivilegeLevel.ROOT
                        )

            self.logger.info("Chroot filesystems unmounted")
            return True

        except Exception as e:
            self.logger.error(f"Chroot unmount error: {e}")
            return False

    async def execute_in_chroot(self, chroot_path: str, command: List[str],
                              user: str = "root") -> CommandResult:
        """
        Execute command inside chroot environment
        """
        try:
            # Construct chroot command
            chroot_cmd = ["chroot", chroot_path]

            # Add user specification if not root
            if user != "root":
                chroot_cmd.extend(["sudo", "-u", user])

            chroot_cmd.extend(command)

            # Execute in chroot
            result = await self.execute_privileged_command(
                chroot_cmd,
                privilege_level=PrivilegeLevel.ROOT
            )

            return result

        except Exception as e:
            self.logger.error(f"Chroot execution error: {e}")
            return CommandResult(
                return_code=-1,
                stdout='',
                stderr=str(e),
                execution_time=0.0,
                command=command,
                success=False
            )

    async def get_status(self) -> Dict[str, Any]:
        """Get SystemAdmin agent status"""
        return {
            'agent_id': self.agent_id,
            'parent_agent': self.parent_agent,
            'max_privilege_level': self.max_privilege_level.value,
            'commands_executed': len(self.command_history),
            'audit_log_path': self.audit_log_path,
            'operational_status': 'active',
            'capabilities': [
                'privileged_command_execution',
                'directory_operations',
                'chroot_management',
                'system_configuration',
                'audit_logging'
            ]
        }

    def _validate_command(self, command: List[str], privilege_level: PrivilegeLevel) -> bool:
        """Validate command for security and permission level"""
        if not command:
            return False

        command_name = command[0]

        # Blacklisted commands
        dangerous_commands = ["rm", "format", "dd", "mkfs"]
        if any(dangerous in command_name for dangerous in dangerous_commands):
            # Allow only with explicit approval and proper flags
            if "--force" in command or "-rf" in " ".join(command):
                self.logger.warning(f"Dangerous command detected: {command_name}")
                return False

        # Privilege level validation
        root_only_commands = ["mount", "umount", "chroot", "systemctl"]
        if command_name in root_only_commands and privilege_level != PrivilegeLevel.ROOT:
            return False

        return True

    async def _execute_system_command(self, cmd_spec: SystemCommand) -> subprocess.CompletedProcess:
        """Execute system command with proper privilege escalation"""
        # Prepare command with privilege escalation if needed
        if cmd_spec.privilege_level == PrivilegeLevel.ROOT:
            final_command = ["sudo"] + cmd_spec.command
        else:
            final_command = cmd_spec.command

        # Execute command
        process = await asyncio.create_subprocess_exec(
            *final_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cmd_spec.working_directory
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=cmd_spec.timeout
            )

            return subprocess.CompletedProcess(
                args=final_command,
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command timed out after {cmd_spec.timeout} seconds")

    async def _audit_log_command(self, cmd_spec: SystemCommand, event_type: str,
                                result: Optional[CommandResult] = None):
        """Log command execution for audit trail"""
        try:
            # Ensure audit log directory exists
            audit_dir = os.path.dirname(self.audit_log_path)
            os.makedirs(audit_dir, exist_ok=True)

            # Prepare audit entry
            audit_entry = {
                'timestamp': time.time(),
                'agent_id': self.agent_id,
                'parent_agent': self.parent_agent,
                'event_type': event_type,
                'command': cmd_spec.command,
                'privilege_level': cmd_spec.privilege_level.value,
                'working_directory': cmd_spec.working_directory,
                'timeout': cmd_spec.timeout
            }

            if result:
                audit_entry.update({
                    'return_code': result.return_code,
                    'success': result.success,
                    'execution_time': result.execution_time
                })

            # Write to audit log
            with open(self.audit_log_path, 'a') as audit_file:
                audit_file.write(f"{audit_entry}\n")

        except Exception as e:
            self.logger.error(f"Audit logging failed: {e}")

    async def _setup_chroot_binaries(self, chroot_path: str):
        """Setup essential binaries in chroot environment"""
        essential_binaries = [
            "/bin/bash", "/bin/sh", "/bin/ls", "/bin/cat", "/bin/cp", "/bin/mv",
            "/usr/bin/python3", "/usr/bin/which", "/usr/bin/id"
        ]

        for binary in essential_binaries:
            if os.path.exists(binary):
                target = os.path.join(chroot_path, binary.lstrip('/'))
                target_dir = os.path.dirname(target)
                os.makedirs(target_dir, exist_ok=True)

                # Copy binary
                shutil.copy2(binary, target)

                # Copy required libraries
                await self._copy_binary_dependencies(binary, chroot_path)

    async def _copy_binary_dependencies(self, binary: str, chroot_path: str):
        """Copy shared library dependencies for binary"""
        try:
            # Get dependencies using ldd
            result = await self.execute_privileged_command(["ldd", binary])

            if result.success:
                for line in result.stdout.split('\n'):
                    if '=>' in line:
                        parts = line.split('=>')
                        if len(parts) > 1:
                            lib_path = parts[1].split()[0]
                            if os.path.exists(lib_path):
                                target = os.path.join(chroot_path, lib_path.lstrip('/'))
                                target_dir = os.path.dirname(target)
                                os.makedirs(target_dir, exist_ok=True)
                                shutil.copy2(lib_path, target)

        except Exception as e:
            self.logger.warning(f"Failed to copy dependencies for {binary}: {e}")

    async def _setup_chroot_devices(self, chroot_path: str):
        """Setup essential device nodes in chroot"""
        dev_path = os.path.join(chroot_path, "dev")

        # Create essential device nodes
        devices = [
            ("null", 1, 3, 0o666),
            ("zero", 1, 5, 0o666),
            ("random", 1, 8, 0o666),
            ("urandom", 1, 9, 0o666)
        ]

        for name, major, minor, mode in devices:
            device_path = os.path.join(dev_path, name)
            if not os.path.exists(device_path):
                try:
                    os.mknod(device_path, stat.S_IFCHR | mode, os.makedev(major, minor))
                except PermissionError:
                    # Try with sudo
                    await self.execute_privileged_command([
                        "mknod", device_path, "c", str(major), str(minor)
                    ], privilege_level=PrivilegeLevel.ROOT)

    async def _secure_directory_permissions(self, directory: str):
        """Apply secure permissions to directory structure"""
        for root, dirs, files in os.walk(directory):
            # Secure directory permissions
            os.chmod(root, 0o700)

            # Secure file permissions
            for file_name in files:
                file_path = os.path.join(root, file_name)
                os.chmod(file_path, 0o600)

    async def execute_directive(self, directive) -> bool:
        """Execute directive from parent agent"""
        try:
            command_name = directive.command

            if command_name == "create_chroot":
                chroot_path = directive.parameters.get('chroot_path')
                base_system = directive.parameters.get('base_system', 'minimal')
                return await self.create_chroot_environment(chroot_path, base_system)

            elif command_name == "mount_chroot":
                chroot_path = directive.parameters.get('chroot_path')
                return await self.mount_chroot_filesystems(chroot_path)

            elif command_name == "unmount_chroot":
                chroot_path = directive.parameters.get('chroot_path')
                return await self.unmount_chroot_filesystems(chroot_path)

            elif command_name == "execute_command":
                command = directive.parameters.get('command')
                privilege_level = PrivilegeLevel(directive.parameters.get('privilege_level', 'user'))
                result = await self.execute_privileged_command(command, privilege_level=privilege_level)
                return result.success

            else:
                self.logger.warning(f"Unknown directive: {command_name}")
                return False

        except Exception as e:
            self.logger.error(f"Directive execution error: {e}")
            return False


# Factory function for SystemAdmin agent creation
def create_systemadmin_agent(agent_id: str = "systemadmin_agent",
                           parent_agent: str = None) -> SystemAdminAgent:
    """Create SystemAdmin agent"""
    return SystemAdminAgent(agent_id, parent_agent)