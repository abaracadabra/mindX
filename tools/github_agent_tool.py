# mindx/tools/github_agent_tool.py
"""
GitHub Agent Tool for MindX.

This tool is completely focused on GitHub as a tool for:
- Coordinating mindX branch backups and restores
- Making sane updates as policy from milestones
- Always backing up before mindX performs major architectural upgrades
- Ensuring mindX can always fallback to a working state from GitHub

The GitHub agent is a specialized tool that operates independently,
focusing solely on GitHub operations as a version control and backup system.
"""

import json
import subprocess
import time
import re
import asyncio
import signal
import atexit
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from enum import Enum

from agents.core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class BackupType(Enum):
    """Types of backups that can be created."""
    PRE_ARCHITECTURAL_UPGRADE = "pre_architectural_upgrade"
    MILESTONE_BACKUP = "milestone_backup"
    SCHEDULED_BACKUP = "scheduled_backup"
    MANUAL_BACKUP = "manual_backup"
    EMERGENCY_BACKUP = "emergency_backup"
    SHUTDOWN_BACKUP = "shutdown_backup"
    HOURLY_BACKUP = "hourly_backup"
    DAILY_BACKUP = "daily_backup"
    WEEKLY_BACKUP = "weekly_backup"


class ScheduleInterval(Enum):
    """Backup schedule intervals."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class GitHubAgentTool(BaseTool):
    """
    GitHub Agent Tool - Focused exclusively on GitHub operations.
    
    This agent ensures mindX always has a working fallback state in GitHub
    by creating backups before major changes and managing branches intelligently.
    """
    
    def __init__(self, 
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        self.backup_metadata_path = self.project_root / "data" / "github_backups.json"
        self.milestone_tracking_path = self.project_root / "data" / "milestones.json"
        self.architectural_changes_path = self.project_root / "data" / "architectural_changes.json"
        self.schedule_config_path = self.project_root / "data" / "github_backup_schedule.json"
        
        # Ensure data directory exists
        self.backup_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        self.backup_metadata = self._load_json(self.backup_metadata_path, {})
        self.milestone_data = self._load_json(self.milestone_tracking_path, {"milestones": [], "last_check": None})
        self.architectural_changes = self._load_json(self.architectural_changes_path, {"changes": [], "pending_backup": False})
        self.schedule_config = self._load_json(self.schedule_config_path, {
            "enabled": True,
            "schedules": {
                "hourly": {"enabled": False, "interval_seconds": 3600},
                "daily": {"enabled": True, "interval_seconds": 86400, "time": "02:00"},
                "weekly": {"enabled": False, "interval_seconds": 604800, "day": "sunday", "time": "03:00"}
            },
            "shutdown_backup": {"enabled": True}
        })
        
        # Background task management
        self.scheduled_tasks: List[asyncio.Task] = []
        self._shutdown_backup_created = False
        self._running = True
        
        # Register shutdown handlers
        self._register_shutdown_handlers()
        
        self.log_prefix = "GitHubAgentTool:"
        logger.info(f"{self.log_prefix} Initialized - GitHub-focused backup and restore agent ready.")
        
        # Auto-start scheduled backups if enabled
        if self.schedule_config.get("enabled", True):
            # Schedule startup in event loop if available
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._start_scheduled_backups())
                else:
                    loop.run_until_complete(self._start_scheduled_backups())
            except RuntimeError:
                # No event loop yet, will be started later
                pass
    
    def _load_json(self, path: Path, default: Any) -> Any:
        """Safely load JSON file."""
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to load {path}: {e}")
        return default
    
    def _save_json(self, path: Path, data: Any):
        """Safely save JSON file."""
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to save {path}: {e}", exc_info=True)
    
    def _register_shutdown_handlers(self):
        """Register shutdown handlers for backup before system shutdown."""
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            logger.warning(f"{self.log_prefix} Shutdown signal received ({signum}), creating backup...")
            # Try to run async backup
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._shutdown_backup())
                else:
                    loop.run_until_complete(self._shutdown_backup())
            except RuntimeError:
                # No event loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._shutdown_backup())
                loop.close()
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in signal handler: {e}", exc_info=True)
        
        # Register signal handlers
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except (ValueError, OSError) as e:
            logger.warning(f"{self.log_prefix} Could not register signal handlers: {e}")
        
        # Register atexit handler
        atexit.register(self._atexit_backup)
    
    async def _shutdown_backup(self):
        """Create backup before shutdown."""
        if self._shutdown_backup_created:
            logger.info(f"{self.log_prefix} Shutdown backup already created, skipping")
            return
        
        self._shutdown_backup_created = True
        logger.warning(f"{self.log_prefix} Creating backup before shutdown...")
        
        try:
            success, result = await self._create_backup(
                backup_type=BackupType.SHUTDOWN_BACKUP.value,
                reason="System shutdown - automatic backup"
            )
            if success:
                logger.info(f"{self.log_prefix} Shutdown backup created: {result.get('backup_branch', 'unknown')}")
            else:
                logger.error(f"{self.log_prefix} Shutdown backup failed: {result}")
        except Exception as e:
            logger.error(f"{self.log_prefix} Error creating shutdown backup: {e}", exc_info=True)
    
    def _atexit_backup(self):
        """Synchronous backup on exit (fallback if async fails)."""
        if self._shutdown_backup_created:
            return
        
        logger.warning(f"{self.log_prefix} Creating backup on exit (atexit)...")
        try:
            # Try to run async backup in a new event loop
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop and not loop.is_closed():
                loop.run_until_complete(self._shutdown_backup())
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in atexit backup: {e}", exc_info=True)
    
    async def execute(self, 
                     operation: str,
                     **kwargs) -> Tuple[bool, Any]:
        """
        Execute GitHub agent operations.
        
        Operations:
        - create_backup: Create a backup branch before major changes
        - restore_from_backup: Restore from a backup branch
        - check_milestones: Check for milestone updates and apply policy
        - detect_architectural_changes: Detect and backup before architectural upgrades
        - list_backups: List available backup branches
        - get_backup_status: Get status of backup system
        - sync_with_github: Sync local state with GitHub
        """
        try:
            if operation == "create_backup":
                return await self._create_backup(
                    backup_type=kwargs.get("backup_type", "manual"),
                    reason=kwargs.get("reason", "Manual backup"),
                    branch_name=kwargs.get("branch_name")
                )
            elif operation == "restore_from_backup":
                return await self._restore_from_backup(
                    branch_name=kwargs.get("branch_name"),
                    target_branch=kwargs.get("target_branch", "main")
                )
            elif operation == "check_milestones":
                return await self._check_milestones()
            elif operation == "detect_architectural_changes":
                return await self._detect_architectural_changes()
            elif operation == "list_backups":
                return await self._list_backups()
            elif operation == "get_backup_status":
                return await self._get_backup_status()
            elif operation == "sync_with_github":
                return await self._sync_with_github()
            elif operation == "pre_upgrade_backup":
                return await self._pre_upgrade_backup(
                    upgrade_description=kwargs.get("upgrade_description", "Unknown upgrade")
                )
            elif operation == "start_scheduled_backups":
                return await self._start_scheduled_backups()
            elif operation == "stop_scheduled_backups":
                return await self._stop_scheduled_backups()
            elif operation == "set_backup_schedule":
                return await self._set_backup_schedule(
                    interval=kwargs.get("interval"),
                    enabled=kwargs.get("enabled", True),
                    time=kwargs.get("time"),
                    day=kwargs.get("day")
                )
            elif operation == "get_backup_schedule":
                return await self._get_backup_schedule()
            elif operation == "shutdown_backup":
                return await self._shutdown_backup()
            else:
                return False, f"Unknown operation: {operation}"
        except Exception as e:
            logger.error(f"{self.log_prefix} Error executing operation '{operation}': {e}", exc_info=True)
            return False, f"GitHub agent error: {e}"
    
    async def _run_git_command(self, command: List[str], check: bool = True) -> Tuple[bool, str]:
        """Execute a git command and return success status and output."""
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if check and result.returncode != 0:
                return False, result.stderr or result.stdout
            return True, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Git command timed out"
        except Exception as e:
            return False, str(e)
    
    async def _get_current_branch(self) -> str:
        """Get the current git branch name."""
        success, output = await self._run_git_command(["branch", "--show-current"], check=False)
        return output if success else "unknown"
    
    async def _get_remote_branches(self) -> List[str]:
        """Get list of remote branches."""
        success, output = await self._run_git_command(["branch", "-r"], check=False)
        if not success:
            return []
        branches = [b.strip().replace("origin/", "") for b in output.split("\n") if b.strip()]
        return branches
    
    async def _create_backup(self, 
                            backup_type: str,
                            reason: str,
                            branch_name: Optional[str] = None) -> Tuple[bool, Any]:
        """
        Create a backup branch before major changes.
        
        This is the core function that ensures mindX always has a working state
        to fallback to in GitHub.
        """
        logger.info(f"{self.log_prefix} Creating backup: type={backup_type}, reason={reason}")
        
        try:
            # Get current branch and commit
            current_branch = await self._get_current_branch()
            success, current_commit = await self._run_git_command(["rev-parse", "HEAD"], check=False)
            if not success:
                return False, "Failed to get current commit"
            
            # Generate backup branch name if not provided
            if not branch_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_type_short = backup_type.replace("_", "-")[:20]
                branch_name = f"backup/{backup_type_short}-{timestamp}"
            
            # Ensure we're on a clean state (commit any uncommitted changes)
            success, status_output = await self._run_git_command(["status", "--porcelain"], check=False)
            if success and status_output.strip():
                # There are uncommitted changes - commit them first
                logger.info(f"{self.log_prefix} Committing uncommitted changes before backup")
                await self._run_git_command(["add", "-A"], check=False)
                await self._run_git_command(
                    ["commit", "-m", f"Auto-commit before backup: {reason}"],
                    check=False
                )
            
            # Create backup branch from current state
            success, output = await self._run_git_command(
                ["checkout", "-b", branch_name],
                check=False
            )
            if not success and "already exists" not in output.lower():
                # Try to checkout existing branch
                success, _ = await self._run_git_command(["checkout", branch_name], check=False)
                if not success:
                    return False, f"Failed to create/checkout backup branch: {output}"
            
            # Push backup branch to remote
            success, push_output = await self._run_git_command(
                ["push", "-u", "origin", branch_name],
                check=False
            )
            if not success:
                logger.warning(f"{self.log_prefix} Failed to push backup branch to remote: {push_output}")
            
            # Switch back to original branch
            await self._run_git_command(["checkout", current_branch], check=False)
            
            # Record backup metadata
            backup_info = {
                "branch_name": branch_name,
                "backup_type": backup_type,
                "reason": reason,
                "source_branch": current_branch,
                "source_commit": current_commit,
                "created_at": datetime.now().isoformat(),
                "status": "created"
            }
            
            if "backups" not in self.backup_metadata:
                self.backup_metadata["backups"] = []
            self.backup_metadata["backups"].append(backup_info)
            self.backup_metadata["last_backup"] = backup_info
            self.backup_metadata["last_backup_at"] = datetime.now().isoformat()
            self._save_json(self.backup_metadata_path, self.backup_metadata)
            
            # Log to memory agent
            if self.memory_agent:
                await self.memory_agent.log_process(
                    'github_backup_created',
                    backup_info,
                    {'agent_id': 'github_agent_tool'}
                )
            
            logger.info(f"{self.log_prefix} Backup created successfully: {branch_name}")
            return True, {
                "status": "success",
                "backup_branch": branch_name,
                "backup_info": backup_info
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error creating backup: {e}", exc_info=True)
            return False, f"Backup creation failed: {e}"
    
    async def _restore_from_backup(self, 
                                   branch_name: str,
                                   target_branch: str = "main") -> Tuple[bool, Any]:
        """
        Restore mindX from a backup branch.
        
        This ensures mindX can always fallback to a working state.
        """
        logger.info(f"{self.log_prefix} Restoring from backup: {branch_name} -> {target_branch}")
        
        try:
            # Verify backup branch exists
            branches = await self._get_remote_branches()
            if branch_name not in branches and f"origin/{branch_name}" not in branches:
                return False, f"Backup branch '{branch_name}' not found"
            
            # Fetch latest from remote
            await self._run_git_command(["fetch", "origin"], check=False)
            
            # Checkout target branch
            await self._run_git_command(["checkout", target_branch], check=False)
            
            # Reset target branch to backup branch state
            success, output = await self._run_git_command(
                ["reset", "--hard", f"origin/{branch_name}"],
                check=False
            )
            if not success:
                return False, f"Failed to reset branch: {output}"
            
            # Force push to update remote (if needed)
            # Note: This is destructive, but necessary for restoration
            logger.warning(f"{self.log_prefix} Restoring {target_branch} from backup {branch_name}")
            
            # Record restoration
            restore_info = {
                "backup_branch": branch_name,
                "target_branch": target_branch,
                "restored_at": datetime.now().isoformat(),
                "status": "restored"
            }
            
            if "restorations" not in self.backup_metadata:
                self.backup_metadata["restorations"] = []
            self.backup_metadata["restorations"].append(restore_info)
            self.backup_metadata["last_restoration"] = restore_info
            self._save_json(self.backup_metadata_path, self.backup_metadata)
            
            # Log to memory agent
            if self.memory_agent:
                await self.memory_agent.log_process(
                    'github_restore_completed',
                    restore_info,
                    {'agent_id': 'github_agent_tool'}
                )
            
            logger.info(f"{self.log_prefix} Restore completed successfully")
            return True, {
                "status": "success",
                "restore_info": restore_info
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error restoring from backup: {e}", exc_info=True)
            return False, f"Restore failed: {e}"
    
    async def _check_milestones(self) -> Tuple[bool, Any]:
        """
        Check for milestone updates and apply policy-based updates.
        
        This monitors GitHub milestones and makes sane updates according to policy.
        """
        logger.info(f"{self.log_prefix} Checking milestones for policy updates")
        
        try:
            # Get current branch
            current_branch = await self._get_current_branch()
            
            # Check if there are any milestone files or markers in the codebase
            # This is a simplified check - in production, this would query GitHub API
            milestone_files = [
                self.project_root / "docs" / "roadmap.md",
                self.project_root / "docs" / "MINDX.md",
                self.project_root / "data" / "milestones.json"
            ]
            
            milestones_found = []
            for milestone_file in milestone_files:
                if milestone_file.exists():
                    # Check modification time
                    mtime = milestone_file.stat().st_mtime
                    last_check = self.milestone_data.get("last_check")
                    if not last_check or mtime > last_check:
                        milestones_found.append(str(milestone_file))
            
            # Update last check time
            self.milestone_data["last_check"] = time.time()
            self._save_json(self.milestone_tracking_path, self.milestone_data)
            
            # If milestones found, create a backup before applying updates
            if milestones_found:
                logger.info(f"{self.log_prefix} Milestones detected, creating backup before updates")
                backup_success, backup_result = await self._create_backup(
                    backup_type=BackupType.MILESTONE_BACKUP.value,
                    reason=f"Milestone update detected: {', '.join(milestones_found)}"
                )
                
                return True, {
                    "status": "milestones_detected",
                    "milestones": milestones_found,
                    "backup_created": backup_success,
                    "backup_info": backup_result if backup_success else None
                }
            
            return True, {
                "status": "no_milestones",
                "message": "No new milestones detected"
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error checking milestones: {e}", exc_info=True)
            return False, f"Milestone check failed: {e}"
    
    async def _detect_architectural_changes(self) -> Tuple[bool, Any]:
        """
        Detect architectural changes and ensure backup is created before upgrades.
        
        This is critical for ensuring mindX can always fallback to a working state.
        """
        logger.info(f"{self.log_prefix} Detecting architectural changes")
        
        try:
            # Key files/directories that indicate architectural changes
            architectural_indicators = [
                "orchestration/",
                "core/",
                "agents/",
                "tools/",
                "learning/",
                "evolution/",
                "docs/ORCHESTRATION.md",
                "docs/AGENTS.md"
            ]
            
            # Check git diff for changes to architectural components
            success, diff_output = await self._run_git_command(
                ["diff", "--name-only", "HEAD"],
                check=False
            )
            
            if not success:
                # Check against remote instead
                await self._run_git_command(["fetch", "origin"], check=False)
                success, diff_output = await self._run_git_command(
                    ["diff", "--name-only", "HEAD", "origin/main"],
                    check=False
                )
            
            architectural_changes_detected = []
            if success and diff_output:
                changed_files = diff_output.strip().split("\n")
                for file in changed_files:
                    for indicator in architectural_indicators:
                        if indicator in file:
                            architectural_changes_detected.append(file)
                            break
            
            # If architectural changes detected and no backup exists, create one
            if architectural_changes_detected:
                # Check if backup already exists for this change
                last_backup = self.backup_metadata.get("last_backup")
                if not last_backup or last_backup.get("backup_type") != BackupType.PRE_ARCHITECTURAL_UPGRADE.value:
                    logger.warning(f"{self.log_prefix} Architectural changes detected without backup!")
                    logger.info(f"{self.log_prefix} Creating emergency backup before architectural upgrade")
                    
                    backup_success, backup_result = await self._create_backup(
                        backup_type=BackupType.PRE_ARCHITECTURAL_UPGRADE.value,
                        reason=f"Architectural changes detected: {len(architectural_changes_detected)} files modified"
                    )
                    
                    # Record architectural change
                    change_record = {
                        "detected_at": datetime.now().isoformat(),
                        "changed_files": architectural_changes_detected,
                        "backup_created": backup_success,
                        "backup_branch": backup_result.get("backup_branch") if backup_success else None
                    }
                    
                    self.architectural_changes["changes"].append(change_record)
                    self.architectural_changes["pending_backup"] = not backup_success
                    self._save_json(self.architectural_changes_path, self.architectural_changes)
                    
                    return True, {
                        "status": "architectural_changes_detected",
                        "changes": architectural_changes_detected,
                        "backup_created": backup_success,
                        "backup_info": backup_result if backup_success else None,
                        "warning": "Backup created before architectural upgrade"
                    }
            
            return True, {
                "status": "no_architectural_changes",
                "message": "No architectural changes detected"
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error detecting architectural changes: {e}", exc_info=True)
            return False, f"Architectural change detection failed: {e}"
    
    async def _pre_upgrade_backup(self, upgrade_description: str) -> Tuple[bool, Any]:
        """
        Create a backup before mindX performs a major architectural upgrade.
        
        This should be called by mindX before any major upgrade to ensure
        a working fallback state exists in GitHub.
        """
        logger.warning(f"{self.log_prefix} Pre-upgrade backup requested: {upgrade_description}")
        
        return await self._create_backup(
            backup_type=BackupType.PRE_ARCHITECTURAL_UPGRADE.value,
            reason=f"Pre-upgrade backup: {upgrade_description}"
        )
    
    async def _list_backups(self) -> Tuple[bool, Any]:
        """List all available backup branches."""
        try:
            backups = self.backup_metadata.get("backups", [])
            branches = await self._get_remote_branches()
            backup_branches = [b for b in branches if b.startswith("backup/")]
            
            return True, {
                "backup_branches": backup_branches,
                "backup_metadata": backups[-10:],  # Last 10 backups
                "total_backups": len(backups)
            }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error listing backups: {e}", exc_info=True)
            return False, f"Failed to list backups: {e}"
    
    async def _get_backup_status(self) -> Tuple[bool, Any]:
        """Get the current status of the backup system."""
        try:
            current_branch = await self._get_current_branch()
            last_backup = self.backup_metadata.get("last_backup")
            pending_backup = self.architectural_changes.get("pending_backup", False)
            
            return True, {
                "current_branch": current_branch,
                "last_backup": last_backup,
                "pending_backup_required": pending_backup,
                "total_backups": len(self.backup_metadata.get("backups", [])),
                "system_status": "operational" if not pending_backup else "backup_required"
            }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error getting backup status: {e}", exc_info=True)
            return False, f"Failed to get backup status: {e}"
    
    async def _sync_with_github(self) -> Tuple[bool, Any]:
        """Sync local state with GitHub remote."""
        try:
            # Fetch latest from all remotes
            success, fetch_output = await self._run_git_command(["fetch", "--all"], check=False)
            
            # Get current branch
            current_branch = await self._get_current_branch()
            
            # Check if local is behind remote
            success, status_output = await self._run_git_command(
                ["status", "-sb"],
                check=False
            )
            
            return True, {
                "status": "synced",
                "current_branch": current_branch,
                "fetch_output": fetch_output if success else "Failed to fetch"
            }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error syncing with GitHub: {e}", exc_info=True)
            return False, f"Sync failed: {e}"
    
    async def _start_scheduled_backups(self) -> Tuple[bool, Any]:
        """Start scheduled backup tasks based on configuration."""
        if not self.schedule_config.get("enabled", True):
            return True, {"status": "disabled", "message": "Scheduled backups are disabled"}
        
        try:
            # Stop existing tasks
            await self._stop_scheduled_backups()
            
            schedules = self.schedule_config.get("schedules", {})
            
            # Start hourly backup if enabled
            if schedules.get("hourly", {}).get("enabled", False):
                interval = schedules["hourly"].get("interval_seconds", 3600)
                task = asyncio.create_task(self._hourly_backup_loop(interval))
                self.scheduled_tasks.append(task)
                logger.info(f"{self.log_prefix} Started hourly backup schedule (interval: {interval}s)")
            
            # Start daily backup if enabled
            if schedules.get("daily", {}).get("enabled", False):
                backup_time = schedules["daily"].get("time", "02:00")
                task = asyncio.create_task(self._daily_backup_loop(backup_time))
                self.scheduled_tasks.append(task)
                logger.info(f"{self.log_prefix} Started daily backup schedule (time: {backup_time})")
            
            # Start weekly backup if enabled
            if schedules.get("weekly", {}).get("enabled", False):
                backup_day = schedules["weekly"].get("day", "sunday")
                backup_time = schedules["weekly"].get("time", "03:00")
                task = asyncio.create_task(self._weekly_backup_loop(backup_day, backup_time))
                self.scheduled_tasks.append(task)
                logger.info(f"{self.log_prefix} Started weekly backup schedule (day: {backup_day}, time: {backup_time})")
            
            return True, {
                "status": "started",
                "active_tasks": len(self.scheduled_tasks),
                "schedules": schedules
            }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error starting scheduled backups: {e}", exc_info=True)
            return False, f"Failed to start scheduled backups: {e}"
    
    async def _stop_scheduled_backups(self) -> Tuple[bool, Any]:
        """Stop all scheduled backup tasks."""
        try:
            stopped_count = 0
            for task in self.scheduled_tasks:
                if not task.done():
                    task.cancel()
                    stopped_count += 1
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            self.scheduled_tasks.clear()
            logger.info(f"{self.log_prefix} Stopped {stopped_count} scheduled backup tasks")
            return True, {"status": "stopped", "stopped_tasks": stopped_count}
        except Exception as e:
            logger.error(f"{self.log_prefix} Error stopping scheduled backups: {e}", exc_info=True)
            return False, f"Failed to stop scheduled backups: {e}"
    
    async def _hourly_backup_loop(self, interval_seconds: int):
        """Background task for hourly backups."""
        logger.info(f"{self.log_prefix} Hourly backup loop started (interval: {interval_seconds}s)")
        
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                if not self._running:
                    break
                
                logger.info(f"{self.log_prefix} Creating scheduled hourly backup")
                success, result = await self._create_backup(
                    backup_type=BackupType.HOURLY_BACKUP.value,
                    reason="Scheduled hourly backup"
                )
                if success:
                    logger.info(f"{self.log_prefix} Hourly backup created: {result.get('backup_branch', 'unknown')}")
                else:
                    logger.warning(f"{self.log_prefix} Hourly backup failed: {result}")
            except asyncio.CancelledError:
                logger.info(f"{self.log_prefix} Hourly backup loop cancelled")
                break
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in hourly backup loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _daily_backup_loop(self, backup_time: str):
        """Background task for daily backups at specified time."""
        logger.info(f"{self.log_prefix} Daily backup loop started (time: {backup_time})")
        
        try:
            hour, minute = map(int, backup_time.split(":"))
        except (ValueError, AttributeError):
            logger.warning(f"{self.log_prefix} Invalid backup time format '{backup_time}', using default 02:00")
            hour, minute = 2, 0
        
        while self._running:
            try:
                # Calculate next backup time
                now = datetime.now()
                next_backup = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed today, schedule for tomorrow
                if next_backup <= now:
                    next_backup += timedelta(days=1)
                
                # Calculate seconds until next backup
                wait_seconds = (next_backup - now).total_seconds()
                logger.info(f"{self.log_prefix} Next daily backup scheduled for {next_backup.isoformat()} (in {wait_seconds:.0f} seconds)")
                
                await asyncio.sleep(wait_seconds)
                
                if not self._running:
                    break
                
                logger.info(f"{self.log_prefix} Creating scheduled daily backup")
                success, result = await self._create_backup(
                    backup_type=BackupType.DAILY_BACKUP.value,
                    reason="Scheduled daily backup"
                )
                if success:
                    logger.info(f"{self.log_prefix} Daily backup created: {result.get('backup_branch', 'unknown')}")
                else:
                    logger.warning(f"{self.log_prefix} Daily backup failed: {result}")
            except asyncio.CancelledError:
                logger.info(f"{self.log_prefix} Daily backup loop cancelled")
                break
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in daily backup loop: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    async def _weekly_backup_loop(self, backup_day: str, backup_time: str):
        """Background task for weekly backups on specified day and time."""
        logger.info(f"{self.log_prefix} Weekly backup loop started (day: {backup_day}, time: {backup_time})")
        
        try:
            hour, minute = map(int, backup_time.split(":"))
        except (ValueError, AttributeError):
            logger.warning(f"{self.log_prefix} Invalid backup time format '{backup_time}', using default 03:00")
            hour, minute = 3, 0
        
        # Map day names to weekday numbers (Monday=0, Sunday=6)
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        target_weekday = day_map.get(backup_day.lower(), 6)  # Default to Sunday
        
        while self._running:
            try:
                # Calculate next backup time
                now = datetime.now()
                days_ahead = target_weekday - now.weekday()
                
                # If target day has passed this week, schedule for next week
                if days_ahead <= 0:
                    days_ahead += 7
                
                next_backup = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
                
                # Calculate seconds until next backup
                wait_seconds = (next_backup - now).total_seconds()
                logger.info(f"{self.log_prefix} Next weekly backup scheduled for {next_backup.isoformat()} (in {wait_seconds:.0f} seconds)")
                
                await asyncio.sleep(wait_seconds)
                
                if not self._running:
                    break
                
                logger.info(f"{self.log_prefix} Creating scheduled weekly backup")
                success, result = await self._create_backup(
                    backup_type=BackupType.WEEKLY_BACKUP.value,
                    reason="Scheduled weekly backup"
                )
                if success:
                    logger.info(f"{self.log_prefix} Weekly backup created: {result.get('backup_branch', 'unknown')}")
                else:
                    logger.warning(f"{self.log_prefix} Weekly backup failed: {result}")
            except asyncio.CancelledError:
                logger.info(f"{self.log_prefix} Weekly backup loop cancelled")
                break
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in weekly backup loop: {e}", exc_info=True)
                await asyncio.sleep(86400)  # Wait 1 day before retrying
    
    async def _set_backup_schedule(self, 
                                   interval: str,
                                   enabled: bool = True,
                                   time: Optional[str] = None,
                                   day: Optional[str] = None) -> Tuple[bool, Any]:
        """Set backup schedule configuration."""
        try:
            if interval not in ["hourly", "daily", "weekly"]:
                return False, f"Invalid interval: {interval}. Must be 'hourly', 'daily', or 'weekly'"
            
            if interval not in self.schedule_config.get("schedules", {}):
                self.schedule_config.setdefault("schedules", {})[interval] = {}
            
            schedule = self.schedule_config["schedules"][interval]
            schedule["enabled"] = enabled
            
            if time:
                schedule["time"] = time
            if day:
                schedule["day"] = day.lower()
            
            self._save_json(self.schedule_config_path, self.schedule_config)
            
            # Restart scheduled backups if enabled
            if enabled:
                await self._start_scheduled_backups()
            
            return True, {
                "status": "updated",
                "interval": interval,
                "config": schedule
            }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error setting backup schedule: {e}", exc_info=True)
            return False, f"Failed to set backup schedule: {e}"
    
    async def _get_backup_schedule(self) -> Tuple[bool, Any]:
        """Get current backup schedule configuration."""
        return True, {
            "enabled": self.schedule_config.get("enabled", True),
            "schedules": self.schedule_config.get("schedules", {}),
            "shutdown_backup": self.schedule_config.get("shutdown_backup", {}),
            "active_tasks": len(self.scheduled_tasks)
        }
    
    async def shutdown(self):
        """Shutdown the GitHub agent and create final backup."""
        logger.info(f"{self.log_prefix} Shutting down GitHub agent...")
        self._running = False
        
        # Stop scheduled tasks
        await self._stop_scheduled_backups()
        
        # Create shutdown backup if enabled
        if self.schedule_config.get("shutdown_backup", {}).get("enabled", True):
            await self._shutdown_backup()
        
        logger.info(f"{self.log_prefix} GitHub agent shutdown complete")

