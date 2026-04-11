# agents/solidity_hardhat_agent.py
"""
SolidityHardhatAgent — I compile, test, and deploy Solidity contracts using Hardhat.

Responsibilities:
  1. Compile contracts via npx hardhat compile
  2. Run test suites via npx hardhat test
  3. Deploy contracts via npx hardhat run (TypeScript deployment scripts)
  4. Manage upgradeable proxy deployments (UUPS, Transparent)
  5. Verify contracts on Etherscan and compatible explorers
  6. Install npm dependencies for Hardhat projects

Architecture:
  I complement SolidityFoundryAgent. Foundry is preferred for new work,
  but the AgenticPlace EVM contracts use Hardhat for deployment
  (OpenZeppelin upgrades plugin, multi-network TypeScript scripts).

  mindX/daio/contracts/agenticplace/evm/ → my primary project root (Hardhat)
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

NPX_BIN = "npx"
DEFAULT_PROJECT_ROOT = PROJECT_ROOT / "daio" / "contracts" / "agenticplace" / "evm"
STATUS_FILE = PROJECT_ROOT / "data" / "solidity_hardhat_status.json"


@dataclass
class HardhatStatus:
    installed: bool = False
    version: str = ""
    node_modules_present: bool = False
    last_compile: float = 0.0
    last_compile_success: bool = False
    last_test: float = 0.0
    last_test_success: bool = False
    tests_passed: int = 0
    tests_failed: int = 0
    node_running: bool = False
    node_port: int = 8545
    node_pid: Optional[int] = None
    deployments: List[Dict[str, Any]] = field(default_factory=list)


class SolidityHardhatAgent:
    """
    I compile, test, and deploy Solidity contracts using Hardhat.
    I handle the AgenticPlace EVM contracts and upgradeable proxy patterns.
    """

    _instance: Optional["SolidityHardhatAgent"] = None

    def __init__(self, project_root: Optional[str] = None, memory_agent=None):
        self.config = Config()
        self.project_root = Path(project_root) if project_root else DEFAULT_PROJECT_ROOT
        self.status = HardhatStatus()
        self.memory_agent = memory_agent
        self._node_process: Optional[asyncio.subprocess.Process] = None
        self.log_prefix = "[SolidityHardhatAgent]"
        self._load_status()
        self._detect_installation()

    @classmethod
    async def get_instance(cls, project_root: Optional[str] = None, memory_agent=None) -> "SolidityHardhatAgent":
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
                    process_name=f"hardhat_{operation}",
                    data=data,
                    metadata={"agent_id": "solidity_hardhat_agent", "domain": "solidity.hardhat"}
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
                "node_modules_present": self.status.node_modules_present,
                "last_compile": self.status.last_compile,
                "last_compile_success": self.status.last_compile_success,
                "last_test": self.status.last_test,
                "last_test_success": self.status.last_test_success,
                "tests_passed": self.status.tests_passed,
                "tests_failed": self.status.tests_failed,
                "node_running": self.status.node_running,
                "node_port": self.status.node_port,
                "timestamp": time.time(),
            }
            STATUS_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _detect_installation(self):
        try:
            result = subprocess.run(
                [NPX_BIN, "hardhat", "--version"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.project_root),
            )
            if result.returncode == 0:
                self.status.installed = True
                self.status.version = result.stdout.strip()
                logger.info(f"{self.log_prefix} Hardhat detected: {self.status.version}")
            else:
                self.status.installed = False
                logger.warning(f"{self.log_prefix} Hardhat not available")
        except Exception as e:
            self.status.installed = False
            logger.warning(f"{self.log_prefix} Hardhat detection failed: {e}")

        # Check node_modules
        self.status.node_modules_present = (self.project_root / "node_modules").is_dir()

    # --- Install dependencies ---

    async def install(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Run npm install to set up Hardhat project dependencies."""
        cwd = Path(project_path) if project_path else self.project_root
        if not (cwd / "package.json").exists():
            return {"success": False, "error": f"No package.json found in {cwd}"}

        logger.info(f"{self.log_prefix} Installing dependencies in {cwd}")
        try:
            process = await asyncio.create_subprocess_exec(
                "npm", "install",
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
            success = process.returncode == 0
            self.status.node_modules_present = (cwd / "node_modules").is_dir()
            self._save_status()

            if success:
                logger.info(f"{self.log_prefix} Dependencies installed")
            else:
                logger.error(f"{self.log_prefix} npm install failed: {stderr.decode(errors='replace')[:500]}")

            return {
                "success": success,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "npm install timed out after 180s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Compile ---

    async def compile(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Run npx hardhat compile."""
        cwd = Path(project_path) if project_path else self.project_root
        if not self.status.installed:
            return {"success": False, "error": "Hardhat not installed"}
        if not self.status.node_modules_present and not (cwd / "node_modules").is_dir():
            install_result = await self.install(str(cwd))
            if not install_result["success"]:
                return {"success": False, "error": f"Auto-install failed: {install_result.get('error', '')}"}

        logger.info(f"{self.log_prefix} Compiling contracts in {cwd}")
        try:
            process = await asyncio.create_subprocess_exec(
                NPX_BIN, "hardhat", "compile",
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            success = process.returncode == 0
            self.status.last_compile = time.time()
            self.status.last_compile_success = success
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
                logger.info(f"{self.log_prefix} Compilation succeeded")
            else:
                logger.error(f"{self.log_prefix} Compilation failed: {stderr.decode(errors='replace')[:500]}")
            await self._log_operation("compile", result)
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "Compilation timed out after 120s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Test ---

    async def test(
        self,
        project_path: Optional[str] = None,
        grep: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run npx hardhat test."""
        cwd = Path(project_path) if project_path else self.project_root
        if not self.status.installed:
            return {"success": False, "error": "Hardhat not installed"}

        cmd = [NPX_BIN, "hardhat", "test"]
        if grep:
            cmd.extend(["--grep", grep])

        logger.info(f"{self.log_prefix} Running tests in {cwd}")
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

            # Parse Mocha-style test output
            passing_line = [l for l in output.splitlines() if "passing" in l.lower()]
            failing_line = [l for l in output.splitlines() if "failing" in l.lower()]
            passed = int(passing_line[0].strip().split()[0]) if passing_line else 0
            failed = int(failing_line[0].strip().split()[0]) if failing_line else 0

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
            logger.info(f"{self.log_prefix} Tests: {passed} passing, {failed} failing")
            await self._log_operation("test", result)
            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "Tests timed out after 300s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Hardhat Node ---

    async def start_node(self, port: int = 8545) -> Dict[str, Any]:
        """Start Hardhat local node."""
        if self.status.node_running and self._node_process:
            return {"success": True, "status": "already_running", "port": self.status.node_port}

        cmd = [NPX_BIN, "hardhat", "node", "--port", str(port)]
        logger.info(f"{self.log_prefix} Starting Hardhat node on port {port}")
        try:
            self._node_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.sleep(3)
            if self._node_process.returncode is not None:
                stdout, stderr = await self._node_process.communicate()
                return {"success": False, "error": f"Node exited: {stderr.decode(errors='replace')[:500]}"}

            self.status.node_running = True
            self.status.node_port = port
            self.status.node_pid = self._node_process.pid
            self._save_status()
            logger.info(f"{self.log_prefix} Hardhat node running on port {port} (pid={self._node_process.pid})")
            return {"success": True, "port": port, "pid": self._node_process.pid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_node(self) -> Dict[str, Any]:
        """Stop Hardhat local node."""
        if not self._node_process:
            self.status.node_running = False
            self._save_status()
            return {"success": True, "status": "not_running"}

        try:
            self._node_process.terminate()
            try:
                await asyncio.wait_for(self._node_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._node_process.kill()
                await self._node_process.wait()

            self._node_process = None
            self.status.node_running = False
            self.status.node_pid = None
            self._save_status()
            logger.info(f"{self.log_prefix} Hardhat node stopped")
            return {"success": True, "status": "stopped"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Deploy ---

    async def deploy(
        self,
        script: str = "deploy.ts",
        network: str = "localhost",
        project_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deploy contracts via npx hardhat run."""
        cwd = Path(project_path) if project_path else self.project_root
        if not self.status.installed:
            return {"success": False, "error": "Hardhat not installed"}

        cmd = [NPX_BIN, "hardhat", "run", script, "--network", network]
        logger.info(f"{self.log_prefix} Deploying {script} to {network}")
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

    # --- Verify ---

    async def verify(
        self,
        address: str,
        constructor_args: Optional[List[str]] = None,
        network: str = "sepolia",
        project_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify contract on block explorer via npx hardhat verify."""
        cwd = Path(project_path) if project_path else self.project_root
        cmd = [NPX_BIN, "hardhat", "verify", "--network", network, address]
        if constructor_args:
            cmd.extend(constructor_args)

        logger.info(f"{self.log_prefix} Verifying {address} on {network}")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
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
            "agent": "SolidityHardhatAgent",
            "installed": self.status.installed,
            "version": self.status.version,
            "project_root": str(self.project_root),
            "node_modules_present": self.status.node_modules_present,
            "last_compile": self.status.last_compile,
            "last_compile_success": self.status.last_compile_success,
            "last_test": self.status.last_test,
            "last_test_success": self.status.last_test_success,
            "tests_passed": self.status.tests_passed,
            "tests_failed": self.status.tests_failed,
            "node_running": self.status.node_running,
            "node_port": self.status.node_port,
            "node_pid": self.status.node_pid,
            "deployment_count": len(self.status.deployments),
        }
