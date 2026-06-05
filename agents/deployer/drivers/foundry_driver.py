"""
EVM driver — shells out to `forge script`, mirroring the proven pattern in
`scripts/blockchain/bootstrap_anvil.sh`. No web3.py; chain reads use the raw
JSON-RPC client from `agents/storage/raw_tx.py`.

The forge script (e.g. DeployTemplate.s.sol) writes its receipt to
`deployments/<chain_id>/<RECEIPT_STAGE>.json`; this driver reads it back and,
when available, enriches tx_hash/block from `broadcast/.../run-latest.json`.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

from ..manifest import resolve_env_map
from ..records import build_evm_record, evm_record_path, now, write_record
from .base import DeployDriver, DeployResult, PreflightCheck

logger = get_logger(__name__)

DUMMY_SCAN_KEYS = (
    "ETHERSCAN_API_KEY", "BASESCAN_API_KEY", "ARBISCAN_API_KEY",
    "OPTIMISTIC_ETHERSCAN_API_KEY", "BSCSCAN_API_KEY",
)


def _abs(root: str) -> str:
    return root if os.path.isabs(root) else os.path.join(str(PROJECT_ROOT), root)


class FoundryDriver(DeployDriver):
    name = "foundry"

    async def _rpc_client(self, stage, key):
        from agents.storage.raw_tx import RawTxClient

        rpc = os.environ.get(stage.rpc_env, "")
        return RawTxClient(rpc_url=rpc, chain_id=stage.chain_id, private_key=key)

    async def preflight(self, stage, key) -> List[PreflightCheck]:
        checks: List[PreflightCheck] = []
        rpc = os.environ.get(stage.rpc_env, "")
        if not rpc:
            checks.append(PreflightCheck("rpc", False, f"env {stage.rpc_env} is unset"))
            return checks
        if not key:
            checks.append(PreflightCheck("key", False, f"no deployer key for {stage.deployer_entity}"))
            return checks
        client = await self._rpc_client(stage, key)
        try:
            try:
                cid = await client.get_chain_id()
                checks.append(PreflightCheck(
                    "rpc", cid == stage.chain_id,
                    f"chainId {cid} (expected {stage.chain_id}) @ {rpc}"))
            except Exception as e:
                checks.append(PreflightCheck("rpc", False, f"unreachable: {e}"))
                return checks
            # balance
            try:
                bal_hex = await client._rpc("eth_getBalance", [client.address, "latest"])
                bal = int(bal_hex, 16)
                checks.append(PreflightCheck("balance", bal > 0, f"{client.address} has {bal} wei"))
            except Exception as e:
                checks.append(PreflightCheck("balance", False, f"balance read failed: {e}"))
            # compiled artifact / script present
            cfg = stage.config
            script = (cfg.get("script") or "").split(":")[0]
            script_path = os.path.join(_abs(cfg.get("contracts_root", "daio/contracts")), script)
            checks.append(PreflightCheck("compiled", os.path.exists(script_path),
                                         f"script {script_path}"))
            # mainnet flag
            checks.append(PreflightCheck("network-flag", (not stage.is_mainnet) or bool(cfg.get("env")),
                                         f"is_mainnet={stage.is_mainnet}"))
        finally:
            await client.close()
        return checks

    async def estimate(self, stage, key) -> Dict[str, Any]:
        # Native-currency budget proxy (gas->USD conversion is a documented MVP simplification).
        return {"native": None, "usd": stage.gas_budget_usd, "note": "budget treated as native/USD proxy"}

    async def deploy(self, stage, key, *, project: str, deployer_of_record: str) -> DeployResult:
        cfg = stage.config
        contracts_root = _abs(cfg.get("contracts_root", "daio/contracts"))
        rpc = os.environ.get(stage.rpc_env, "")
        script = cfg.get("script")
        receipt_stage = cfg.get("receipt_stage", project)
        if not (rpc and script and key):
            return DeployResult(False, error="missing rpc/script/key for foundry deploy")

        env = dict(os.environ)
        env["FOUNDRY_PROFILE"] = cfg.get("profile", "thot_commitment")
        env["DEPLOYER_PRIVATE_KEY"] = key
        env["RECEIPT_STAGE"] = receipt_stage
        env.update(resolve_env_map(cfg.get("env", {})))
        verify = bool(cfg.get("verify", False))
        if not verify:
            for k in DUMMY_SCAN_KEYS:
                env.setdefault(k, "dummy")

        os.makedirs(os.path.join(contracts_root, "deployments", str(stage.chain_id)), exist_ok=True)
        cmd = ["forge", "script", script, "--rpc-url", rpc, "--broadcast"]
        if verify:
            cmd.append("--verify")
        if stage.chain_id in (1337, 31337):
            cmd.append("--skip-simulation")

        logger.info(f"FoundryDriver: {' '.join(cmd)} (cwd={contracts_root})")
        try:
            proc = subprocess.run(cmd, cwd=contracts_root, env=env, capture_output=True,
                                  text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return DeployResult(False, error="forge script timed out (600s)")
        logs = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.returncode != 0:
            return DeployResult(False, error=f"forge script exited {proc.returncode}", logs=logs[-4000:])

        contracts, tx_hash, block = self._parse_receipt(contracts_root, stage.chain_id, receipt_stage, script)
        record = build_evm_record(
            project=project, chain=stage.chain, chain_id=stage.chain_id,
            deployer_of_record=deployer_of_record, contracts=contracts,
            tx_hash=tx_hash, block_number=block, rpc_url=rpc, deployed_at=now())
        write_record(evm_record_path(stage.chain_id, receipt_stage), record)
        return DeployResult(True, record=record, logs=logs[-2000:])

    def _parse_receipt(self, contracts_root: str, chain_id: int, receipt_stage: str,
                       script: str):
        contracts: List[Dict[str, Any]] = []
        receipt = os.path.join(contracts_root, "deployments", str(chain_id), f"{receipt_stage}.json")
        try:
            with open(receipt, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for k, v in data.items():
                if isinstance(v, str) and v.startswith("0x") and len(v) == 42:
                    contracts.append({"name": k, "address": v})
        except (OSError, json.JSONDecodeError):
            pass
        # enrich tx_hash/block from the forge broadcast artifact
        tx_hash: Optional[str] = None
        block: Optional[int] = None
        base = os.path.basename(script).split(":")[0]
        bc = os.path.join(contracts_root, "broadcast", base, str(chain_id), "run-latest.json")
        try:
            with open(bc, "r", encoding="utf-8") as fh:
                run = json.load(fh)
            txs = run.get("transactions", [])
            if txs:
                tx_hash = txs[0].get("hash")
            receipts = run.get("receipts", [])
            if receipts:
                bn = receipts[0].get("blockNumber")
                block = int(bn, 16) if isinstance(bn, str) and bn.startswith("0x") else bn
            # if the receipt JSON had no addresses, pull contractAddress from broadcast
            if not contracts:
                for t in txs:
                    ca = t.get("contractAddress")
                    nm = t.get("contractName") or "contract"
                    if ca:
                        contracts.append({"name": nm, "address": ca})
        except (OSError, json.JSONDecodeError):
            pass
        return contracts, tx_hash, block
