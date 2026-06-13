"""
DeployerService — the governed, per-chain-isolated deploy orchestrator.

Flow (spec §4/§11, mindX "authorize-then-server-deploy" variant):

  create_intent(wallet_address, signature, message, manifest, chain?)
    -> recover signer (EIP-191) -> map to participant entity -> dojo tier
    -> authorization.check (tier/chain/rate-limit/mainnet)
    -> per-stage PREFLIGHT + estimate, NO broadcast
    -> persist intent (5-min expiry); emit catalogue event

  execute_intent(intent_id)  [route gates mainnet with require_admin_access]
    -> reload intent (reject if expired)
    -> per-chain ISOLATED stages: own rpc/key/receipt/status; a failed stage
       is recorded and the loop continues (no cross-chain rollback)
    -> write batch manifest; emit catalogue events

The connected wallet is the deployer-of-record; the signing key is a
vault-scoped per-chain deploy key (keys.py), never the user's wallet.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

from . import keys
from .authorization import DeploymentAuthorization, live_tier, map_signer_to_entity
from .drivers import get_driver
from .manifest import DeployManifest, load_manifest
from .records import now, write_batch_manifest

logger = get_logger(__name__)

INTENTS_DIR = os.path.join(str(PROJECT_ROOT), "data", "governance", "deploy_intents")
INTENT_TTL_S = 300


class DeployerError(RuntimeError):
    pass


class DeployerService:
    _instance: Optional["DeployerService"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.log_prefix = "DeployerService:"

    @classmethod
    async def get_instance(cls, config: Optional[Config] = None) -> "DeployerService":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config=config)
            return cls._instance

    # ── intent persistence ────────────────────────────────────────────────

    def _intent_path(self, intent_id: str) -> str:
        return os.path.join(INTENTS_DIR, f"{intent_id}.json")

    def _save_intent(self, intent: Dict[str, Any]) -> None:
        os.makedirs(INTENTS_DIR, exist_ok=True)
        with open(self._intent_path(intent["intent_id"]), "w", encoding="utf-8") as fh:
            json.dump(intent, fh, indent=2)

    def load_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        try:
            with open(self._intent_path(intent_id), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    # ── auth ──────────────────────────────────────────────────────────────

    def _verify_signature(self, wallet_address: str, message: str, signature: str):
        from tools.user_persistence_manager import UserPersistenceManager

        upm = UserPersistenceManager()
        return upm.verify_signature(wallet_address, message, signature)

    async def _authorize(self, *, wallet_address: str, signature: str, message: str,
                         manifest: DeployManifest, stages) -> Dict[str, Any]:
        ver = self._verify_signature(wallet_address, message, signature)
        if not getattr(ver, "is_valid", False):
            raise DeployerError("signature verification failed")
        signer = ver.recovered_address
        entity_id, static_tier = map_signer_to_entity(signer)
        tier = await live_tier(entity_id, static_tier) if entity_id else 0
        authz = DeploymentAuthorization.load()
        any_mainnet = any(s.is_mainnet for s in stages)
        # check each stage's chain individually (a multi-chain intent must clear all)
        requires_confirm = manifest.mainnet_two_step or any_mainnet
        for s in stages:
            decision = authz.check(
                recovered_signer=signer, entity_id=entity_id, tier=tier, chain=s.chain,
                required_min_tier=manifest.required_min_tier, is_mainnet=s.is_mainnet,
                manifest_approvers=manifest.required_approvers)
            if not decision.allowed:
                raise DeployerError(f"authorization denied for {s.chain}: {decision.reason}")
            requires_confirm = requires_confirm or decision.requires_operator_confirm
        return {"signer": signer, "entity_id": entity_id, "tier": tier,
                "requires_operator_confirm": requires_confirm}

    # ── intent / confirm ──────────────────────────────────────────────────

    async def create_intent(self, *, wallet_address: str, signature: str, message: str,
                            manifest_path: str, chain: Optional[str] = None) -> Dict[str, Any]:
        manifest = load_manifest(manifest_path)
        stages = manifest.selected_stages(chain)
        auth = await self._authorize(wallet_address=wallet_address, signature=signature,
                                     message=message, manifest=manifest, stages=stages)

        stage_reports: List[Dict[str, Any]] = []
        for s in stages:
            key = await self._resolve_key(s)
            driver = get_driver(s.driver)
            try:
                checks = await driver.preflight(s, key)
                estimate = await driver.estimate(s, key) if hasattr(driver, "estimate") else {}
            except Exception as e:  # preflight must never broadcast; surface failure
                checks, estimate = [], {"error": str(e)}
            stage_reports.append({
                "chain": s.chain, "chain_id": s.chain_id, "driver": s.driver,
                "is_mainnet": s.is_mainnet,
                "preflight": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks],
                "preflight_ok": all(c.passed for c in checks) if checks else False,
                "estimate": estimate,
            })

        intent = {
            "intent_id": uuid.uuid4().hex,
            "project": manifest.project,
            "manifest_path": manifest_path,
            "chain": chain,
            "deployer_of_record": auth["signer"],
            "entity_id": auth["entity_id"],
            "tier": auth["tier"],
            "requires_operator_confirm": auth["requires_operator_confirm"],
            "stages": stage_reports,
            "created_at": now(),
            "expires_at": now() + INTENT_TTL_S,
            "status": "pending",
        }
        self._save_intent(intent)
        await self._emit("contract.deploy.intent", {
            "intent_id": intent["intent_id"], "project": manifest.project,
            "deployer_of_record": auth["signer"], "chains": [s.chain for s in stages]})
        return intent

    async def execute_intent(self, intent_id: str) -> Dict[str, Any]:
        intent = self.load_intent(intent_id)
        if intent is None:
            raise DeployerError(f"intent {intent_id} not found")
        if intent.get("status") == "executed":
            raise DeployerError(f"intent {intent_id} already executed")
        if now() > float(intent.get("expires_at", 0)):
            intent["status"] = "expired"
            self._save_intent(intent)
            raise DeployerError(f"intent {intent_id} expired")

        manifest = load_manifest(intent["manifest_path"])
        stages = manifest.selected_stages(intent.get("chain"))
        results: List[Dict[str, Any]] = []
        for s in stages:  # per-chain ISOLATION — independent, no cross-chain rollback
            res = {"chain": s.chain, "chain_id": s.chain_id, "driver": s.driver, "status": "init"}
            try:
                key = await self._resolve_key(s)
                driver = get_driver(s.driver)
                res["status"] = "preflight"
                checks = await driver.preflight(s, key)
                if not all(c.passed for c in checks):
                    failed = [c.name for c in checks if not c.passed]
                    res.update(status="failed",
                               error=f"preflight failed: {failed}",
                               preflight=[{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks])
                    results.append(res)
                    continue
                dr = await driver.deploy(s, key, project=manifest.project,
                                         deployer_of_record=intent["deployer_of_record"])
                if dr.ok:
                    res.update(status="recorded", record=dr.record)
                    await self._emit("contract.deploy.confirmed", {
                        "intent_id": intent_id, "chain": s.chain, "project": manifest.project,
                        "deployer_of_record": intent["deployer_of_record"], "record": dr.record})
                else:
                    res.update(status="failed", error=dr.error, logs=dr.logs)
            except Exception as e:
                logger.error(f"{self.log_prefix} stage {s.chain} crashed: {e}", exc_info=True)
                res.update(status="failed", error=str(e))
            results.append(res)

        batch = {
            "intent_id": intent_id, "project": manifest.project,
            "deployer_of_record": intent["deployer_of_record"],
            "executed_at": now(),
            "stages": results,
            "summary": {
                "succeeded": [r["chain"] for r in results if r["status"] == "recorded"],
                "failed": [r["chain"] for r in results if r["status"] == "failed"],
            },
        }
        write_batch_manifest(intent_id, batch)
        intent["status"] = "executed"
        intent["batch"] = batch["summary"]
        self._save_intent(intent)
        return batch

    # ── helpers ───────────────────────────────────────────────────────────

    async def _resolve_key(self, stage) -> Optional[str]:
        if stage.driver == "foundry":
            return await keys.resolve_deployer_key(stage.deployer_entity, stage.chain, stage.chain_id)
        return await keys.resolve_deployer_mnemonic(
            stage.deployer_entity, stage.chain, stage.config.get("deployer_mnemonic_env", ""))

    async def _emit(self, kind: str, data: Dict[str, Any]) -> None:
        try:
            from agents.catalogue.events import emit_catalogue_event

            await emit_catalogue_event(
                kind, actor="deployer_service", payload=data,
                source_log="data/governance/deployments",
                actor_wallet=data.get("deployer_of_record"))
        except Exception as e:  # catalogue is best-effort instrumentation
            logger.debug(f"{self.log_prefix} catalogue emit skipped ({kind}): {e}")
