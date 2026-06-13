"""
Algorand driver — deploys an app via `algosdk` ApplicationCreateTxn straight
from the precompiled ARC56 artifact (`byteCode.approval/clear` are base64
program bytes; `state.schema` gives the global/local state schema). No algokit
CLI and no MCP needed — fully runnable inside the backend process.

Mirrors the algosdk usage already in `tools/x402_avm_client.py`.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

from ..records import algorand_record_path, build_algorand_record, now, write_record
from .base import DeployDriver, DeployResult, PreflightCheck

logger = get_logger(__name__)

# LocalNet default algod token (KMD/algod sandbox convention)
LOCALNET_TOKEN = "a" * 64
MIN_DEPLOY_MICROALGO = 200_000  # 0.2 ALGO floor for an app-create + min balance bump


def _abs(root: str) -> str:
    return root if os.path.isabs(root) else os.path.join(str(PROJECT_ROOT), root)


def _algod_token(url: str) -> str:
    tok = os.environ.get("ALGORAND_ALGOD_TOKEN")
    if tok is not None:
        return tok
    return LOCALNET_TOKEN if ("localhost" in url or "127.0.0.1" in url) else ""


def _load_arc56(artifacts_root: str, contract: str) -> Dict[str, Any]:
    path = os.path.join(_abs(artifacts_root), f"{contract}.arc56.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _schema(arc56: Dict[str, Any]):
    from algosdk import transaction

    s = (arc56.get("state") or {}).get("schema") or {}
    g = s.get("global", {}) or {}
    l = s.get("local", {}) or {}
    gs = transaction.StateSchema(int(g.get("ints", 0)), int(g.get("bytes", 0)))
    ls = transaction.StateSchema(int(l.get("ints", 0)), int(l.get("bytes", 0)))
    return gs, ls


def _network_ok(genesis_id: str, network: str) -> bool:
    gid = (genesis_id or "").lower()
    net = (network or "").lower()
    if "mainnet" in net:
        return gid.startswith("mainnet")
    if "testnet" in net:
        return gid.startswith("testnet")
    # localnet/dev: anything that isn't a public network
    return not (gid.startswith("mainnet") or gid.startswith("testnet"))


class AlgorandDriver(DeployDriver):
    name = "algorand"

    def _client(self, stage):
        from algosdk.v2client import algod

        url = os.environ.get(stage.config.get("algod_env", stage.rpc_env), "")
        return algod.AlgodClient(_algod_token(url), url), url

    async def preflight(self, stage, key) -> List[PreflightCheck]:
        checks: List[PreflightCheck] = []
        cfg = stage.config
        try:
            client, url = self._client(stage)
        except Exception as e:
            return [PreflightCheck("rpc", False, f"algod client init failed: {e}")]
        if not url:
            return [PreflightCheck("rpc", False, f"env {cfg.get('algod_env', stage.rpc_env)} unset")]
        # rpc + network
        try:
            sp = client.suggested_params()
            checks.append(PreflightCheck("rpc", True, f"algod reachable @ {url} (gen {sp.gen})"))
            checks.append(PreflightCheck("network-flag", _network_ok(sp.gen, cfg.get("network", "")),
                                         f"genesis {sp.gen} vs network {cfg.get('network')}"))
        except Exception as e:
            return checks + [PreflightCheck("rpc", False, f"algod unreachable: {e}")]
        # compiled artifacts present
        for c in cfg.get("contracts", []):
            try:
                arc = _load_arc56(cfg.get("artifacts_root"), c)
                ok = bool((arc.get("byteCode") or {}).get("approval"))
                checks.append(PreflightCheck("compiled", ok, f"{c}.arc56.json byteCode={'present' if ok else 'MISSING'}"))
            except Exception as e:
                checks.append(PreflightCheck("compiled", False, f"{c}: {e}"))
        # deployer funded
        if key:
            try:
                from algosdk import account, mnemonic

                sender = account.address_from_private_key(mnemonic.to_private_key(key))
                amt = client.account_info(sender).get("amount", 0)
                checks.append(PreflightCheck("balance", amt >= MIN_DEPLOY_MICROALGO,
                                             f"{sender} has {amt} microAlgo"))
            except Exception as e:
                checks.append(PreflightCheck("balance", False, f"account read failed: {e}"))
        else:
            checks.append(PreflightCheck("key", False, "no deployer mnemonic"))
        return checks

    async def deploy(self, stage, key, *, project: str, deployer_of_record: str) -> DeployResult:
        cfg = stage.config
        if not key:
            return DeployResult(False, error="no deployer mnemonic for algorand deploy")
        try:
            from algosdk import account, logic, mnemonic, transaction

            client, url = self._client(stage)
            sk = mnemonic.to_private_key(key)
            sender = account.address_from_private_key(sk)
        except Exception as e:
            return DeployResult(False, error=f"algosdk init failed: {e}")

        apps: List[Dict[str, Any]] = []
        for contract in cfg.get("contracts", []):
            try:
                arc = _load_arc56(cfg.get("artifacts_root"), contract)
                approval = base64.b64decode(arc["byteCode"]["approval"])
                clear = base64.b64decode(arc["byteCode"]["clear"])
                gs, ls = _schema(arc)
                sp = client.suggested_params()
                txn = transaction.ApplicationCreateTxn(
                    sender=sender, sp=sp, on_complete=transaction.OnComplete.NoOpOC,
                    approval_program=approval, clear_program=clear,
                    global_schema=gs, local_schema=ls,
                    app_args=cfg.get("app_args") or None,
                )
                txid = client.send_transaction(txn.sign(sk))
                res = transaction.wait_for_confirmation(client, txid, 8)
                app_id = res["application-index"]
                apps.append({
                    "name": contract,
                    "app_id": app_id,
                    "app_address": logic.get_application_address(app_id),
                    "tx_id": txid,
                    "arc56": f"{contract}.arc56.json",
                })
                logger.info(f"AlgorandDriver: deployed {contract} app_id={app_id}")
            except Exception as e:
                return DeployResult(False, error=f"deploy {contract} failed: {e}",
                                    record={"apps": apps})

        record = build_algorand_record(
            project=project, chain=stage.chain, network=cfg.get("network", ""),
            deployer_of_record=deployer_of_record, apps=apps, algod_url=url, deployed_at=now())
        write_record(algorand_record_path(stage.chain, project), record)
        return DeployResult(True, record=record)
