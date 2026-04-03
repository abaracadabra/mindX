# agents/vllm_agent.py
"""
vLLMAgent — Manages vLLM build, deployment, model serving, and operational efficiency.

Responsibilities:
  1. Build vLLM from source for CPU (AVX2) when GPU is not available
  2. Manage model serving lifecycle (start, stop, health check)
  3. Monitor inference performance (latency, throughput, memory)
  4. Auto-select optimal models for available hardware
  5. Report efficiency metrics to diagnostics and improvement journal

Architecture:
  vLLMAgent sits alongside InferenceAgent in the orchestration layer.
  It manages the vLLM process and exposes metrics to the system.

  InferenceDiscovery → probes vLLM health
  vLLMAgent → manages vLLM lifecycle, builds, model selection
  VLLMHandler → sends inference requests to running vLLM server
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

VLLM_PORT = int(os.getenv("VLLM_PORT", "8001"))
VLLM_HOST = os.getenv("VLLM_HOST", "0.0.0.0")
VENV_PATH = PROJECT_ROOT / ".mindx_env"
VLLM_BIN = VENV_PATH / "bin" / "vllm"
VLLM_BUILD_LOG = PROJECT_ROOT / "data" / "logs" / "vllm_build.log"
VLLM_STATUS_FILE = PROJECT_ROOT / "data" / "vllm_status.json"


@dataclass
class VLLMStatus:
    installed: bool = False
    version: str = ""
    backend: str = "unknown"  # "gpu", "cpu", "not_available"
    serving: bool = False
    model: str = ""
    port: int = VLLM_PORT
    pid: Optional[int] = None
    build_log: str = ""
    last_health_check: float = 0.0
    health_ok: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)


class VLLMAgent:
    """
    Manages vLLM build, deployment, and operational efficiency for mindX.
    """

    _instance: Optional["VLLMAgent"] = None

    def __init__(self):
        self.config = Config()
        self.status = VLLMStatus()
        self._serving_process: Optional[asyncio.subprocess.Process] = None
        self._load_status()
        self._detect_installation()

    @classmethod
    async def get_instance(cls) -> "VLLMAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_status(self):
        """Load persisted status from disk."""
        try:
            if VLLM_STATUS_FILE.exists():
                data = json.loads(VLLM_STATUS_FILE.read_text())
                self.status.version = data.get("version", "")
                self.status.backend = data.get("backend", "unknown")
                self.status.model = data.get("model", "")
        except Exception:
            pass

    def _save_status(self):
        """Persist status to disk."""
        try:
            VLLM_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": self.status.version,
                "backend": self.status.backend,
                "model": self.status.model,
                "installed": self.status.installed,
                "serving": self.status.serving,
                "port": self.status.port,
                "timestamp": time.time(),
            }
            VLLM_STATUS_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _detect_installation(self):
        """Detect current vLLM installation state."""
        try:
            result = subprocess.run(
                [str(VENV_PATH / "bin" / "python"), "-c", "import vllm; print(vllm.__version__)"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                self.status.installed = True
                self.status.version = result.stdout.strip()

                # Check if it can actually start (GPU vs CPU)
                check = subprocess.run(
                    [str(VENV_PATH / "bin" / "python"), "-c",
                     "from vllm.engine.arg_utils import EngineArgs; print('ok')"],
                    capture_output=True, text=True, timeout=30,
                )
                if check.returncode == 0:
                    self.status.backend = "ready"
                else:
                    err = check.stderr
                    if "libcuda" in err or "CUDA" in err:
                        self.status.backend = "needs_cpu_build"
                    else:
                        self.status.backend = "error"
            else:
                self.status.installed = False
                self.status.backend = "not_installed"
        except Exception as e:
            self.status.installed = False
            self.status.backend = f"error: {str(e)[:100]}"

        self._save_status()
        logger.info(f"vLLMAgent: detected vLLM {self.status.version}, backend={self.status.backend}")

    async def build_cpu_from_source(self) -> Dict[str, Any]:
        """
        Build vLLM for CPU from source.
        This is required when the VPS has no GPU (libcuda.so missing).

        Steps:
          1. Install cmake if missing
          2. pip install vllm from source with VLLM_TARGET_DEVICE=cpu
          3. Verify the build
        """
        logger.info("vLLMAgent: starting CPU build from source...")
        VLLM_BUILD_LOG.parent.mkdir(parents=True, exist_ok=True)

        steps = []

        # Step 1: Ensure cmake is installed
        cmake_check = subprocess.run(["cmake", "--version"], capture_output=True)
        if cmake_check.returncode != 0:
            logger.info("vLLMAgent: installing cmake...")
            steps.append("installing cmake")
            result = subprocess.run(
                ["apt", "install", "-y", "cmake"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return {"success": False, "step": "cmake", "error": result.stderr[:500]}
            steps.append("cmake installed")

        # Step 2: Uninstall existing GPU vLLM
        logger.info("vLLMAgent: uninstalling GPU vLLM...")
        steps.append("uninstalling gpu vllm")
        subprocess.run(
            [str(VENV_PATH / "bin" / "pip"), "uninstall", "-y", "vllm"],
            capture_output=True, timeout=60,
        )

        # Step 3: Build from source with CPU target
        logger.info("vLLMAgent: building vLLM for CPU (this takes 10-30 minutes)...")
        steps.append("building vllm cpu from source")

        env = os.environ.copy()
        env["VLLM_TARGET_DEVICE"] = "cpu"
        env["MAX_JOBS"] = "2"  # Limit to 2 cores on VPS

        build_proc = await asyncio.create_subprocess_exec(
            str(VENV_PATH / "bin" / "pip"), "install", "vllm",
            "--no-build-isolation",
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(build_proc.communicate(), timeout=3600)

        # Log build output
        build_output = stdout.decode() + "\n" + stderr.decode()
        VLLM_BUILD_LOG.write_text(build_output)

        if build_proc.returncode != 0:
            steps.append("build FAILED")
            logger.error(f"vLLMAgent: CPU build failed. See {VLLM_BUILD_LOG}")
            return {
                "success": False,
                "step": "build",
                "error": stderr.decode()[-500:],
                "log": str(VLLM_BUILD_LOG),
                "steps": steps,
            }

        # Step 4: Verify
        steps.append("verifying build")
        self._detect_installation()

        if self.status.installed:
            steps.append(f"vLLM {self.status.version} CPU build SUCCESS")
            logger.info(f"vLLMAgent: CPU build complete — {self.status.version}")
            # Store action
            try:
                from agents import memory_pgvector as _mpg
                await _mpg.store_action_if_new(
                    "vllm_agent", "build_complete",
                    f"vLLM {self.status.version} built for CPU (AVX2)",
                    "vllm_agent", "completed",
                )
            except Exception:
                pass
        else:
            steps.append("verification failed")

        return {
            "success": self.status.installed,
            "version": self.status.version,
            "backend": self.status.backend,
            "steps": steps,
            "log": str(VLLM_BUILD_LOG),
        }

    async def serve_model(self, model: str = "mixedbread-ai/mxbai-embed-large-v1",
                          dtype: str = "float32", max_model_len: int = 512) -> Dict[str, Any]:
        """Start vLLM serving a model."""
        if not self.status.installed or self.status.backend not in ("ready", "cpu"):
            return {"success": False, "error": f"vLLM not ready (backend={self.status.backend})"}

        if self.status.serving and self._serving_process:
            return {"success": True, "message": "Already serving", "model": self.status.model}

        logger.info(f"vLLMAgent: starting model serve — {model} on port {VLLM_PORT}")

        try:
            self._serving_process = await asyncio.create_subprocess_exec(
                str(VENV_PATH / "bin" / "vllm"), "serve", model,
                "--host", VLLM_HOST,
                "--port", str(VLLM_PORT),
                "--dtype", dtype,
                "--max-model-len", str(max_model_len),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait a bit for startup
            await asyncio.sleep(10)

            if self._serving_process.returncode is not None:
                stderr = await self._serving_process.stderr.read()
                return {"success": False, "error": stderr.decode()[-500:]}

            self.status.serving = True
            self.status.model = model
            self.status.pid = self._serving_process.pid
            self._save_status()

            logger.info(f"vLLMAgent: serving {model} on port {VLLM_PORT} (pid={self._serving_process.pid})")
            return {"success": True, "model": model, "port": VLLM_PORT, "pid": self._serving_process.pid}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_serving(self) -> Dict[str, Any]:
        """Stop the vLLM serving process."""
        if self._serving_process:
            self._serving_process.terminate()
            try:
                await asyncio.wait_for(self._serving_process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self._serving_process.kill()

        self.status.serving = False
        self.status.pid = None
        self._save_status()
        logger.info("vLLMAgent: serving stopped")
        return {"success": True}

    async def health_check(self) -> Dict[str, Any]:
        """Check vLLM server health."""
        self.status.last_health_check = time.time()
        if not self.status.serving:
            self.status.health_ok = False
            return {"healthy": False, "reason": "not serving"}

        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as sess:
                async with sess.get(f"http://localhost:{VLLM_PORT}/health") as resp:
                    self.status.health_ok = resp.status == 200
                    return {"healthy": resp.status == 200, "status_code": resp.status}
        except Exception as e:
            self.status.health_ok = False
            return {"healthy": False, "error": str(e)}

    async def get_efficiency_report(self) -> Dict[str, Any]:
        """Report on vLLM operational efficiency for mindX."""
        report = {
            "installed": self.status.installed,
            "version": self.status.version,
            "backend": self.status.backend,
            "serving": self.status.serving,
            "model": self.status.model,
            "port": self.status.port,
            "health_ok": self.status.health_ok,
        }

        # If serving, get model stats
        if self.status.serving:
            try:
                import aiohttp
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as sess:
                    async with sess.get(f"http://localhost:{VLLM_PORT}/v1/models") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            report["models_loaded"] = [m.get("id") for m in data.get("data", [])]
            except Exception:
                pass

        # Hardware context
        try:
            import psutil
            report["hardware"] = {
                "cpu_count": psutil.cpu_count(),
                "cpu_model": open("/proc/cpuinfo").read().split("model name")[1].split("\n")[0].split(":")[1].strip() if os.path.exists("/proc/cpuinfo") else "unknown",
                "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "avx2": "avx2" in open("/proc/cpuinfo").read() if os.path.exists("/proc/cpuinfo") else False,
            }
        except Exception:
            pass

        # Recommendations
        recommendations = []
        if self.status.backend == "needs_cpu_build":
            recommendations.append("Build vLLM from source: POST /vllm/build-cpu")
        if self.status.installed and not self.status.serving:
            recommendations.append("Start serving: POST /vllm/serve")
        if not self.status.installed:
            recommendations.append("Install vLLM: pip install vllm")

        report["recommendations"] = recommendations
        return report

    def get_status(self) -> Dict[str, Any]:
        """Quick status for diagnostics."""
        return {
            "installed": self.status.installed,
            "version": self.status.version,
            "backend": self.status.backend,
            "serving": self.status.serving,
            "model": self.status.model,
            "port": self.status.port,
            "health_ok": self.status.health_ok,
        }
