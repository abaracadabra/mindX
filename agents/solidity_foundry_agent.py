# agents/solidity_foundry_agent.py
"""
SolidityFoundryAgent — I compile, test, and deploy Solidity contracts using Foundry.

Responsibilities:
  1. Compile contracts via forge build with gas reporting
  2. Run test suites via forge test with verbosity control
  3. Start/stop Anvil local testnet for development and testing
  4. Deploy contracts via forge script to any configured network
  5. Verify contracts on block explorers
  6. Report build status, test results, and deployment artifacts

Architecture:
  I sit in the agent layer as a specialized tool-wrapping agent.
  CoordinatorAgent or MastermindAgent can dispatch contract operations to me.
  I persist my status to data/ and log all operations via memory_agent.

  mindX/daio/contracts/ → my primary project root (Foundry)
  mindX/daio/contracts/agenticplace/ → AgenticPlace marketplace contracts
"""

import os
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from utils.config import PROJECT_ROOT, Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

FOUNDRY_BIN = Path(os.path.expanduser("~/.foundry/bin"))
FORGE_BIN = FOUNDRY_BIN / "forge"
ANVIL_BIN = FOUNDRY_BIN / "anvil"
CAST_BIN = FOUNDRY_BIN / "cast"

DEFAULT_PROJECT_ROOT = PROJECT_ROOT / "daio" / "contracts"
STATUS_FILE = PROJECT_ROOT / "data" / "solidity_foundry_status.json"


@dataclass
class FoundryStatus:
    installed: bool = False
    version: str = ""
    last_build: float = 0.0
    last_build_success: bool = False
    last_test: float = 0.0
    last_test_success: bool = False
    tests_passed: int = 0
    tests_failed: int = 0
    anvil_running: bool = False
    anvil_port: int = 8545
    anvil_pid: Optional[int] = None
    deployments: List[Dict[str, Any]] = field(default_factory=list)


class SolidityFoundryAgent:
    """
    I compile, test, and deploy Solidity contracts using Foundry (forge + anvil).
    I am mindX's preferred Solidity toolchain agent.
    """

    _instance: Optional["SolidityFoundryAgent"] = None

    def __init__(self, project_root: Optional[str] = None, memory_agent=None):
        self.config = Config()
        self.project_root = Path(project_root) if project_root else DEFAULT_PROJECT_ROOT
        self.status = FoundryStatus()
        self.memory_agent = memory_agent
        self._anvil_process: Optional[asyncio.subprocess.Process] = None
        self.log_prefix = "[SolidityFoundryAgent]"
        self._load_status()
        self._detect_installation()

    @classmethod
    async def get_instance(cls, project_root: Optional[str] = None, memory_agent=None) -> "SolidityFoundryAgent":
        if cls._instance is None:
            cls._instance = cls(project_root, memory_agent)
        elif memory_agent and not cls._instance.memory_agent:
            cls._instance.memory_agent = memory_agent
        return cls._instance

    async def _log_operation(self, operation: str, data: Dict[str, Any]):
        """Log operation to memory_agent — all logs are memories in data/."""
        if self.memory_agent:
            try:
                await self.memory_agent.log_process(
                    process_name=f"foundry_{operation}",
                    data=data,
                    metadata={"agent_id": "solidity_foundry_agent", "domain": "solidity.foundry"}
                )
            except Exception:
                pass

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
                "installed": self.status.installed,
                "version": self.status.version,
                "last_build": self.status.last_build,
                "last_build_success": self.status.last_build_success,
                "last_test": self.status.last_test,
                "last_test_success": self.status.last_test_success,
                "tests_passed": self.status.tests_passed,
                "tests_failed": self.status.tests_failed,
                "anvil_running": self.status.anvil_running,
                "anvil_port": self.status.anvil_port,
                "timestamp": time.time(),
            }
            STATUS_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _detect_installation(self):
        try:
            result = subprocess.run(
                [str(FORGE_BIN), "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                self.status.installed = True
                self.status.version = result.stdout.strip()
                logger.info(f"{self.log_prefix} Foundry detected: {self.status.version}")
            else:
                self.status.installed = False
                logger.warning(f"{self.log_prefix} Foundry not found at {FORGE_BIN}")
        except Exception as e:
            self.status.installed = False
            logger.warning(f"{self.log_prefix} Foundry detection failed: {e}")

    # --- Build ---

    async def build(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Run forge build. Returns build result with gas report."""
        cwd = Path(project_path) if project_path else self.project_root
        if not self.status.installed:
            return {"success": False, "error": "Foundry not installed"}
        if not (cwd / "foundry.toml").exists():
            return {"success": False, "error": f"No foundry.toml found in {cwd}"}

        logger.info(f"{self.log_prefix} Building contracts in {cwd}")
        try:
            process = await asyncio.create_subprocess_exec(
                str(FORGE_BIN), "build", "--sizes",
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            success = process.returncode == 0
            self.status.last_build = time.time()
            self.status.last_build_success = success
            self._save_status()

            result = {
                "success": success,
                "returncode": process.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "project": str(cwd),
                "timestamp": time.time(),
            }
            if success:
                logger.info(f"{self.log_prefix} Build succeeded")
            else:
                logger.error(f"{self.log_prefix} Build failed: {stderr.decode(errors='replace')[:500]}")
            await self._log_operation("build", result)
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "Build timed out after 120s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Test ---

    async def test(
        self,
        project_path: Optional[str] = None,
        match_test: Optional[str] = None,
        match_contract: Optional[str] = None,
        verbosity: int = 2,
        gas_report: bool = False,
    ) -> Dict[str, Any]:
        """Run forge test. Returns test results with pass/fail counts."""
        cwd = Path(project_path) if project_path else self.project_root
        if not self.status.installed:
            return {"success": False, "error": "Foundry not installed"}

        cmd = [str(FORGE_BIN), "test", f"-{'v' * verbosity}"]
        if match_test:
            cmd.extend(["--match-test", match_test])
        if match_contract:
            cmd.extend(["--match-contract", match_contract])
        if gas_report:
            cmd.append("--gas-report")

        logger.info(f"{self.log_prefix} Running tests in {cwd}: {' '.join(cmd)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            output = stdout.decode(errors="replace")
            success = process.returncode == 0

            # Parse test counts from output
            passed = output.count("[PASS]")
            failed = output.count("[FAIL]")

            self.status.last_test = time.time()
            self.status.last_test_success = success
            self.status.tests_passed = passed
            self.status.tests_failed = failed
            self._save_status()

            result = {
                "success": success,
                "returncode": process.returncode,
                "tests_passed": passed,
                "tests_failed": failed,
                "stdout": output,
                "stderr": stderr.decode(errors="replace"),
                "project": str(cwd),
                "timestamp": time.time(),
            }
            logger.info(f"{self.log_prefix} Tests: {passed} passed, {failed} failed")
            await self._log_operation("test", result)
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "Tests timed out after 300s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Anvil ---

    async def start_anvil(self, port: int = 8545, fork_url: Optional[str] = None) -> Dict[str, Any]:
        """Start Anvil local testnet."""
        if self.status.anvil_running and self._anvil_process:
            return {"success": True, "status": "already_running", "port": self.status.anvil_port}

        cmd = [str(ANVIL_BIN), "--port", str(port), "--host", "127.0.0.1"]
        if fork_url:
            cmd.extend(["--fork-url", fork_url])

        logger.info(f"{self.log_prefix} Starting Anvil on port {port}")
        try:
            self._anvil_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Wait briefly for startup
            await asyncio.sleep(2)
            if self._anvil_process.returncode is not None:
                stdout, stderr = await self._anvil_process.communicate()
                return {"success": False, "error": f"Anvil exited: {stderr.decode(errors='replace')[:500]}"}

            self.status.anvil_running = True
            self.status.anvil_port = port
            self.status.anvil_pid = self._anvil_process.pid
            self._save_status()
            logger.info(f"{self.log_prefix} Anvil running on port {port} (pid={self._anvil_process.pid})")
            return {"success": True, "port": port, "pid": self._anvil_process.pid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_anvil(self) -> Dict[str, Any]:
        """Stop Anvil local testnet."""
        if not self._anvil_process:
            self.status.anvil_running = False
            self._save_status()
            return {"success": True, "status": "not_running"}

        try:
            self._anvil_process.terminate()
            try:
                await asyncio.wait_for(self._anvil_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._anvil_process.kill()
                await self._anvil_process.wait()

            self._anvil_process = None
            self.status.anvil_running = False
            self.status.anvil_pid = None
            self._save_status()
            logger.info(f"{self.log_prefix} Anvil stopped")
            return {"success": True, "status": "stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Deploy ---

    async def deploy(
        self,
        script: str,
        network: str = "localhost",
        project_path: Optional[str] = None,
        broadcast: bool = False,
        verify: bool = False,
    ) -> Dict[str, Any]:
        """Deploy contracts via forge script."""
        cwd = Path(project_path) if project_path else self.project_root
        if not self.status.installed:
            return {"success": False, "error": "Foundry not installed"}

        cmd = [str(FORGE_BIN), "script", script, "--rpc-url", network, "-vvvv"]
        if broadcast:
            cmd.append("--broadcast")
        if verify:
            cmd.append("--verify")

        logger.info(f"{self.log_prefix} Deploying {script} to {network} (broadcast={broadcast})")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            success = process.returncode == 0
            output = stdout.decode(errors="replace")

            deployment_record = {
                "script": script,
                "network": network,
                "broadcast": broadcast,
                "success": success,
                "timestamp": time.time(),
                "output_preview": output[:1000],
            }
            self.status.deployments.append(deployment_record)
            self._save_status()

            if success:
                logger.info(f"{self.log_prefix} Deployment succeeded: {script} -> {network}")
            else:
                logger.error(f"{self.log_prefix} Deployment failed: {stderr.decode(errors='replace')[:500]}")
            await self._log_operation("deploy", deployment_record)

            return {
                "success": success,
                "returncode": process.returncode,
                "stdout": output,
                "stderr": stderr.decode(errors="replace"),
                "deployment": deployment_record,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Deployment timed out after 300s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Snapshot / Gas ---

    async def snapshot(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Run forge snapshot for gas benchmarking."""
        cwd = Path(project_path) if project_path else self.project_root
        try:
            process = await asyncio.create_subprocess_exec(
                str(FORGE_BIN), "snapshot",
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Status ---

    def get_status(self) -> Dict[str, Any]:
        """Return current agent status."""
        return {
            "agent": "SolidityFoundryAgent",
            "installed": self.status.installed,
            "version": self.status.version,
            "project_root": str(self.project_root),
            "last_build": self.status.last_build,
            "last_build_success": self.status.last_build_success,
            "last_test": self.status.last_test,
            "last_test_success": self.status.last_test_success,
            "tests_passed": self.status.tests_passed,
            "tests_failed": self.status.tests_failed,
            "anvil_running": self.status.anvil_running,
            "anvil_port": self.status.anvil_port,
            "anvil_pid": self.status.anvil_pid,
            "deployment_count": len(self.status.deployments),
            "forge_bin": str(FORGE_BIN),
            "anvil_bin": str(ANVIL_BIN),
        }
