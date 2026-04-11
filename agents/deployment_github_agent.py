# agents/deployment_github_agent.py
"""
DeploymentGitHubAgent — I load, deploy, and replicate mindX from GitHub repositories.

I am the bridge between version control and live deployment. I coordinate with
BackupAgent for failsafe rollback and GitHubAgentTool for version management.

Failsafe chain:
  1. BackupAgent creates git commit + blockchain memory BEFORE deployment
  2. Rollback point captures current source directories
  3. GitHubAgentTool creates backup branch
  4. Source loaded from repo with integrity verification
  5. Deployment applied (data/ and vault/ preserved)
  6. Post-deploy verification
  7. On failure: automatic rollback

Replication modes:
  - github: Clone from repo, verify, deploy (mindX.sh --replicate-from-github)
  - pull: git pull on existing deployment (fast update)
  - local: Copy source to target (mindX.sh --replicate)
  - chroot: Full chroot replication via AionAgent
"""

import os
import json
import time
import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from utils.config import PROJECT_ROOT, Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

STATUS_FILE = PROJECT_ROOT / "data" / "deployment_github_status.json"
ROLLBACK_DIR = PROJECT_ROOT / "data" / "rollbacks"
MINDX_SH = PROJECT_ROOT / "mindX.sh"

CRITICAL_FILES = [
    "agents/core/mindXagent.py",
    "mindx_backend_service/main_service.py",
    "agents/orchestration/coordinator_agent.py",
    "agents/memory_agent.py",
    "tools/github_agent_tool.py",
    "mindX.sh",
]

SOURCE_DIRS = [
    "agents", "api", "llm", "scripts", "tools", "utils",
    "mindx_backend_service", "orchestration",
]

DEFAULT_REPO = "https://github.com/AgenticPlace/mindX.git"


@dataclass
class DeploymentStatus:
    last_deploy: float = 0.0
    last_deploy_success: bool = False
    last_deploy_mode: str = ""
    last_deploy_commit: str = ""
    last_rollback_path: str = ""
    deploy_count: int = 0
    rollback_count: int = 0
    deployments: List[Dict[str, Any]] = field(default_factory=list)


class DeploymentGitHubAgent:
    """
    I load, deploy, and replicate mindX from GitHub repositories.
    I am the failsafe bridge between version control and live deployment.
    """

    _instance: Optional["DeploymentGitHubAgent"] = None

    def __init__(self, memory_agent=None, config=None):
        self.config = config or Config()
        self.memory_agent = memory_agent
        self.project_root = PROJECT_ROOT
        self.status = DeploymentStatus()
        self.log_prefix = "[DeploymentGitHubAgent]"
        self._load_status()

    @classmethod
    async def get_instance(cls, memory_agent=None, config=None) -> "DeploymentGitHubAgent":
        if cls._instance is None:
            cls._instance = cls(memory_agent, config)
        elif memory_agent and not cls._instance.memory_agent:
            cls._instance.memory_agent = memory_agent
        return cls._instance

    # --- Status persistence ---

    def _load_status(self):
        try:
            if STATUS_FILE.exists():
                data = json.loads(STATUS_FILE.read_text())
                for k, v in data.items():
                    if hasattr(self.status, k):
                        setattr(self.status, k, v)
        except Exception:
            pass

    def _save_status(self):
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_deploy": self.status.last_deploy,
                "last_deploy_success": self.status.last_deploy_success,
                "last_deploy_mode": self.status.last_deploy_mode,
                "last_deploy_commit": self.status.last_deploy_commit,
                "last_rollback_path": self.status.last_rollback_path,
                "deploy_count": self.status.deploy_count,
                "rollback_count": self.status.rollback_count,
                "timestamp": time.time(),
            }
            STATUS_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    async def _log_operation(self, operation: str, data: Dict[str, Any]):
        """Log operation to memory_agent — all logs are memories in data/."""
        if self.memory_agent:
            try:
                await self.memory_agent.log_process(
                    process_name=f"deployment_{operation}",
                    data=data,
                    metadata={"agent_id": "deployment_github_agent", "domain": "deployment.github"}
                )
            except Exception:
                pass

    # --- Integrity verification ---

    def verify_integrity(self, target_path: Optional[Path] = None) -> Dict[str, Any]:
        """Verify critical files exist and are non-empty."""
        root = target_path or self.project_root
        missing = []
        present = []
        for f in CRITICAL_FILES:
            full = root / f
            if full.exists() and full.stat().st_size > 0:
                present.append(f)
            else:
                missing.append(f)

        result = {
            "success": len(missing) == 0,
            "present": present,
            "missing": missing,
            "target": str(root),
            "critical_file_count": len(CRITICAL_FILES),
        }
        if missing:
            logger.error(f"{self.log_prefix} Integrity check FAILED — missing: {missing}")
        else:
            logger.info(f"{self.log_prefix} Integrity check passed ({len(present)}/{len(CRITICAL_FILES)} files)")
        return result

    # --- Rollback point ---

    async def create_rollback_point(self, reason: str = "pre-deploy") -> Dict[str, Any]:
        """Snapshot current source directories for rollback."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rollback_path = ROLLBACK_DIR / f"pre_deploy_{timestamp}"

        try:
            rollback_path.mkdir(parents=True, exist_ok=True)

            for src_dir in SOURCE_DIRS:
                src = self.project_root / src_dir
                dst = rollback_path / src_dir
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True,
                                   ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.git'))

            # Save rollback metadata
            meta = {
                "reason": reason,
                "timestamp": timestamp,
                "source_dirs": SOURCE_DIRS,
                "project_root": str(self.project_root),
                "created_at": time.time(),
            }
            (rollback_path / "rollback_meta.json").write_text(json.dumps(meta, indent=2))

            self.status.last_rollback_path = str(rollback_path)
            self._save_status()

            logger.info(f"{self.log_prefix} Rollback point created: {rollback_path}")
            await self._log_operation("rollback_created", meta)
            return {"success": True, "rollback_path": str(rollback_path)}

        except Exception as e:
            logger.error(f"{self.log_prefix} Rollback point creation failed: {e}")
            return {"success": False, "error": str(e)}

    async def rollback(self, rollback_path: Optional[str] = None) -> Dict[str, Any]:
        """Restore from a rollback point."""
        path = Path(rollback_path) if rollback_path else Path(self.status.last_rollback_path)
        if not path or not path.exists():
            return {"success": False, "error": f"Rollback path not found: {path}"}

        try:
            meta_file = path / "rollback_meta.json"
            meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}

            restored = []
            for src_dir in SOURCE_DIRS:
                src = path / src_dir
                dst = self.project_root / src_dir
                if src.is_dir():
                    # Only restore .py files to preserve data/config
                    for py_file in src.rglob("*.py"):
                        rel = py_file.relative_to(src)
                        target = dst / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(py_file, target)
                        restored.append(str(rel))

            self.status.rollback_count += 1
            self._save_status()

            result = {"success": True, "restored_files": len(restored), "from": str(path)}
            logger.info(f"{self.log_prefix} Rollback complete: {len(restored)} files restored from {path}")
            await self._log_operation("rollback_executed", result)
            return result

        except Exception as e:
            logger.error(f"{self.log_prefix} Rollback failed: {e}")
            return {"success": False, "error": str(e)}

    # --- Backup coordination ---

    async def _pre_deploy_backup(self) -> Dict[str, Any]:
        """Coordinate with BackupAgent and GitHubAgentTool before deployment."""
        results = {"backup_agent": None, "github_agent": None, "rollback": None}

        # 1. BackupAgent — git commit current state
        try:
            from agents.backup_agent import BackupAgent
            backup = BackupAgent()
            backup_result = await backup.backup_before_shutdown()
            results["backup_agent"] = {"success": True, "commit": backup_result}
            logger.info(f"{self.log_prefix} BackupAgent pre-deploy commit complete")
        except Exception as e:
            results["backup_agent"] = {"success": False, "error": str(e)}
            logger.warning(f"{self.log_prefix} BackupAgent pre-deploy failed: {e}")

        # 2. GitHubAgentTool — create backup branch
        try:
            from tools.github_agent_tool import GitHubAgentTool, BackupType
            github_tool = GitHubAgentTool(memory_agent=self.memory_agent, config=self.config)
            github_result = await github_tool.execute(
                action="create_backup",
                backup_type=BackupType.PRE_ARCHITECTURAL_UPGRADE.value,
                reason="Pre-deployment backup via DeploymentGitHubAgent"
            )
            results["github_agent"] = github_result
            logger.info(f"{self.log_prefix} GitHubAgentTool backup branch created")
        except Exception as e:
            results["github_agent"] = {"success": False, "error": str(e)}
            logger.warning(f"{self.log_prefix} GitHubAgentTool backup failed: {e}")

        # 3. Rollback point — local snapshot
        rollback_result = await self.create_rollback_point(reason="pre-deploy-failsafe")
        results["rollback"] = rollback_result

        return results

    # --- Load from repo ---

    async def load_from_repo(
        self,
        repo_url: str = DEFAULT_REPO,
        branch: str = "main",
        target_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clone or pull mindX from a GitHub repository with integrity verification."""
        target = Path(target_path) if target_path else self.project_root

        # If target is current project and has .git, do a pull
        if target == self.project_root and (target / ".git").is_dir():
            return await self._git_pull(branch)

        # Otherwise clone fresh
        return await self._git_clone(repo_url, branch, target)

    async def _git_pull(self, branch: str = "main") -> Dict[str, Any]:
        """Fast update via git pull on existing deployment."""
        logger.info(f"{self.log_prefix} Pulling latest from {branch}")
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "pull", "origin", branch,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            success = process.returncode == 0
            output = stdout.decode(errors="replace")

            # Get current commit hash
            commit_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
            )
            commit_out, _ = await commit_proc.communicate()
            commit = commit_out.decode().strip() if commit_proc.returncode == 0 else "unknown"

            result = {
                "success": success,
                "mode": "pull",
                "branch": branch,
                "commit": commit,
                "stdout": output,
                "stderr": stderr.decode(errors="replace"),
            }
            if success:
                logger.info(f"{self.log_prefix} Pull succeeded: {commit[:8]}")
            else:
                logger.error(f"{self.log_prefix} Pull failed: {stderr.decode(errors='replace')[:300]}")
            return result

        except Exception as e:
            return {"success": False, "mode": "pull", "error": str(e)}

    async def _git_clone(self, repo_url: str, branch: str, target: Path) -> Dict[str, Any]:
        """Clone repository to target path with integrity check."""
        logger.info(f"{self.log_prefix} Cloning {repo_url} ({branch}) to {target}")
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth", "1", "--branch", branch, repo_url, str(target),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            success = process.returncode == 0

            if not success:
                return {
                    "success": False, "mode": "clone",
                    "error": stderr.decode(errors="replace")[:500],
                }

            # Get commit hash
            commit_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(target),
                stdout=asyncio.subprocess.PIPE,
            )
            commit_out, _ = await commit_proc.communicate()
            commit = commit_out.decode().strip()

            # Verify integrity of cloned repo
            integrity = self.verify_integrity(target)

            result = {
                "success": integrity["success"],
                "mode": "clone",
                "repo": repo_url,
                "branch": branch,
                "commit": commit,
                "integrity": integrity,
                "target": str(target),
            }
            if not integrity["success"]:
                logger.error(f"{self.log_prefix} Clone integrity check FAILED: missing {integrity['missing']}")
            else:
                logger.info(f"{self.log_prefix} Clone succeeded: {commit[:8]}, integrity verified")
            return result

        except Exception as e:
            return {"success": False, "mode": "clone", "error": str(e)}

    # --- Deploy ---

    async def deploy(
        self,
        repo_url: str = DEFAULT_REPO,
        branch: str = "main",
        mode: str = "pull",
        skip_backup: bool = False,
    ) -> Dict[str, Any]:
        """
        Full deployment pipeline with failsafe chain.

        Modes:
          - pull: git pull on current deployment (fastest)
          - github: Clone fresh, verify, copy source (mindX.sh --replicate-from-github)
          - replicate: Shell-based replication via mindX.sh --replicate
        """
        deploy_record = {
            "mode": mode,
            "repo": repo_url,
            "branch": branch,
            "started_at": time.time(),
            "success": False,
        }

        # Step 1: Pre-deploy backup (failsafe)
        if not skip_backup:
            logger.info(f"{self.log_prefix} Step 1: Creating pre-deploy backup")
            backup_results = await self._pre_deploy_backup()
            deploy_record["backup"] = backup_results

        # Step 2: Load source
        logger.info(f"{self.log_prefix} Step 2: Loading source ({mode})")
        if mode == "pull":
            load_result = await self._git_pull(branch)
        elif mode == "github":
            load_result = await self._replicate_from_github(repo_url, branch)
        elif mode == "replicate":
            load_result = await self._replicate_via_shell()
        else:
            return {"success": False, "error": f"Unknown deploy mode: {mode}"}

        deploy_record["load"] = load_result

        if not load_result.get("success"):
            deploy_record["success"] = False
            deploy_record["error"] = load_result.get("error", "Load failed")
            # Auto-rollback on failure
            if not skip_backup:
                logger.warning(f"{self.log_prefix} Deployment failed — initiating rollback")
                rollback_result = await self.rollback()
                deploy_record["rollback"] = rollback_result
            await self._log_operation("deploy_failed", deploy_record)
            self.status.last_deploy = time.time()
            self.status.last_deploy_success = False
            self.status.last_deploy_mode = mode
            self._save_status()
            return deploy_record

        # Step 3: Post-deploy verification
        logger.info(f"{self.log_prefix} Step 3: Post-deploy integrity verification")
        integrity = self.verify_integrity()
        deploy_record["integrity"] = integrity

        if not integrity["success"]:
            logger.error(f"{self.log_prefix} Post-deploy integrity FAILED — rolling back")
            if not skip_backup:
                rollback_result = await self.rollback()
                deploy_record["rollback"] = rollback_result
            deploy_record["success"] = False
            deploy_record["error"] = f"Integrity failed: missing {integrity['missing']}"
            await self._log_operation("deploy_failed_integrity", deploy_record)
            self.status.last_deploy = time.time()
            self.status.last_deploy_success = False
            self._save_status()
            return deploy_record

        # Step 4: Success
        deploy_record["success"] = True
        deploy_record["completed_at"] = time.time()
        deploy_record["duration"] = deploy_record["completed_at"] - deploy_record["started_at"]
        deploy_record["commit"] = load_result.get("commit", "unknown")

        self.status.last_deploy = time.time()
        self.status.last_deploy_success = True
        self.status.last_deploy_mode = mode
        self.status.last_deploy_commit = load_result.get("commit", "")
        self.status.deploy_count += 1
        self.status.deployments.append({
            "mode": mode,
            "commit": deploy_record["commit"],
            "timestamp": time.time(),
            "success": True,
        })
        self._save_status()

        logger.info(
            f"{self.log_prefix} Deployment SUCCEEDED: mode={mode}, "
            f"commit={deploy_record['commit'][:8]}, "
            f"duration={deploy_record['duration']:.1f}s"
        )
        await self._log_operation("deploy_succeeded", deploy_record)
        return deploy_record

    async def _replicate_from_github(self, repo_url: str, branch: str) -> Dict[str, Any]:
        """Replicate using mindX.sh --replicate-from-github pattern."""
        if not MINDX_SH.exists():
            return {"success": False, "error": f"mindX.sh not found at {MINDX_SH}"}

        try:
            process = await asyncio.create_subprocess_exec(
                "bash", str(MINDX_SH), "--replicate-from-github",
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "GITHUB_REPO_URL": repo_url},
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            success = process.returncode == 0

            # Read restore record if created
            restore_file = self.project_root / "data" / "last_github_restore.json"
            restore_record = {}
            if restore_file.exists():
                try:
                    restore_record = json.loads(restore_file.read_text())
                except Exception:
                    pass

            return {
                "success": success,
                "mode": "github",
                "commit": restore_record.get("commit", "unknown"),
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "restore_record": restore_record,
            }
        except Exception as e:
            return {"success": False, "mode": "github", "error": str(e)}

    async def _replicate_via_shell(self) -> Dict[str, Any]:
        """Replicate using mindX.sh --replicate."""
        if not MINDX_SH.exists():
            return {"success": False, "error": f"mindX.sh not found at {MINDX_SH}"}

        try:
            process = await asyncio.create_subprocess_exec(
                "bash", str(MINDX_SH), "--replicate",
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            return {
                "success": process.returncode == 0,
                "mode": "replicate",
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }
        except Exception as e:
            return {"success": False, "mode": "replicate", "error": str(e)}

    # --- Status ---

    def get_status(self) -> Dict[str, Any]:
        """Return current deployment agent status."""
        return {
            "agent": "DeploymentGitHubAgent",
            "project_root": str(self.project_root),
            "last_deploy": self.status.last_deploy,
            "last_deploy_success": self.status.last_deploy_success,
            "last_deploy_mode": self.status.last_deploy_mode,
            "last_deploy_commit": self.status.last_deploy_commit,
            "deploy_count": self.status.deploy_count,
            "rollback_count": self.status.rollback_count,
            "last_rollback_path": self.status.last_rollback_path,
            "mindx_sh_available": MINDX_SH.exists(),
            "default_repo": DEFAULT_REPO,
            "critical_files": CRITICAL_FILES,
        }
