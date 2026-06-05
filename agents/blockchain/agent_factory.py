"""
BlockchainAgentFactory — mint a mindX agent as an ERC-7857 iNFT.

End-to-end pipeline (v1, live against Anvil-1337):

    wallet (IDManager) -> persona -> bundle+IPFS -> mintAgent (iNFT_7857)
      -> offerOnAgenticPlace -> bindBankonVault -> bindAgentId
      -> AgentRegistry.register -> write sidecar facets + production registry

Design notes
------------
* **Custody**: the iNFT is minted *to the minter EOA* (the operator/treasury
  that holds MINTER_ROLE), because iNFT_7857's bind/offer hooks require the
  caller to be the token owner and transferring an iNFT needs a sealed-key
  oracle handoff. The agent's own wallet is its cryptographic *identity*
  (recorded in the registry + walletpublickey facet); custody-to-agent transfer
  is deferred to v2.
* **dry_run=True (default)** does everything up to and including IPFS bundling
  but never broadcasts a transaction.
* Every on-chain step after the mint is best-effort and recorded; only the mint
  itself is fatal on failure.
* No LLM call is made here (persona is synthesized or read from an existing
  facet), so the no-model-pinning rule is satisfied by construction.

Reuses: agents/storage/raw_tx.py, agents/core/id_manager_agent.py,
agents/storage/multi_provider.py, and the same selector approach as
agents/storage/anchor.py (via agents/blockchain/abi_codec.py).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

from . import abi_codec, contracts, facets

logger = get_logger(__name__)

# iNFT_7857 mintAgent — a valid THOT dimension and one processing unit.
DEFAULT_DIMENSIONS = 768
DEFAULT_PARALLEL_UNITS = 1

MINT_AGENT_SIG = "mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string)"
MINT_AGENT_TYPES = ["address", "bytes32", "string", "bytes32", "uint32", "uint8", "bytes32", "string"]

OFFER_SIG = "offerOnAgenticPlace(uint256,address,uint256,bool,address)"
OFFER_TYPES = ["uint256", "address", "uint256", "bool", "address"]

BIND_VAULT_SIG = "bindBankonVault(uint256,address,bytes32)"
BIND_VAULT_TYPES = ["uint256", "address", "bytes32"]

BIND_AGENTID_SIG = "bindAgentId(uint256,string)"
BIND_AGENTID_TYPES = ["uint256", "string"]

REGISTER_SIG = "register(address,string,address,bytes32,string)"
REGISTER_TYPES = ["address", "string", "address", "bytes32", "string"]

ZERO_ADDR = "0x0000000000000000000000000000000000000000"


class BlockchainAgentFactory:
    """Singleton factory that mints agents as iNFTs."""

    _instance: Optional["BlockchainAgentFactory"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.log_prefix = "BlockchainAgentFactory:"

    @classmethod
    async def get_instance(cls, config: Optional[Config] = None) -> "BlockchainAgentFactory":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config=config)
            return cls._instance

    # ── helpers ──────────────────────────────────────────────────────────

    async def _create_wallet(self, name: str) -> Dict[str, Any]:
        """Create (or reuse) the agent's EVM identity wallet via IDManagerAgent."""
        try:
            from agents.core.id_manager_agent import IDManagerAgent

            idm = await IDManagerAgent.get_instance()
            address, env_var = await idm.create_new_wallet(f"blockchain.agent.{name}")
            return {"address": address, "env_var": env_var, "vault_id": f"agent_pk_blockchain.agent.{name}"}
        except Exception as e:  # pragma: no cover - exercised only when IDManager misconfigured
            logger.error(f"{self.log_prefix} wallet creation failed: {e}", exc_info=True)
            raise

    def _bundle(self, name: str, address: str, persona: Dict[str, Any]) -> bytes:
        """Deterministic artifact bundle: the three authored facets + identity."""
        spec_path = facets.facet_path(name, "agent")
        model_path = facets.facet_path(name, "model")
        spec = ""
        model = ""
        try:
            with open(spec_path, "r", encoding="utf-8") as fh:
                spec = fh.read()
        except FileNotFoundError:
            pass
        try:
            with open(model_path, "r", encoding="utf-8") as fh:
                model = fh.read()
        except FileNotFoundError:
            pass
        payload = {
            "name": name,
            "wallet": address,
            "agent_spec": spec,
            "model": model,
            "persona": persona,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")

    async def _upload_ipfs(self, data: bytes, name: str) -> Dict[str, Any]:
        """Upload bundle to IPFS; gracefully degrade to a local content address."""
        import hashlib

        sha = hashlib.sha256(data).hexdigest()
        provider = None
        try:
            from agents.storage.multi_provider import MultiProvider

            primary = mirror = None
            try:
                from agents.storage.lighthouse_provider import LighthouseProvider

                primary = LighthouseProvider()
            except Exception:
                primary = None
            try:
                from agents.storage.nftstorage_provider import NFTStorageProvider

                mirror = NFTStorageProvider()
            except Exception:
                mirror = None
            if primary is not None and mirror is not None:
                provider = MultiProvider(primary, mirror)
            elif primary is not None:
                provider = MultiProvider(primary)
            elif mirror is not None:
                provider = MultiProvider(mirror)
        except Exception:
            provider = None

        if provider is None:
            return {"storageURI": f"local://{sha}", "cid": None, "sha256": sha, "ipfs": False}

        try:
            cid = await provider.upload(data, f"blockchain-agent-{name}.json")
            cid_str = getattr(cid, "cid", None) or str(cid)
            return {"storageURI": f"ipfs://{cid_str}", "cid": cid_str, "sha256": sha, "ipfs": True}
        except Exception as e:
            logger.warning(f"{self.log_prefix} IPFS upload failed ({e}); using local content address")
            return {"storageURI": f"local://{sha}", "cid": None, "sha256": sha, "ipfs": False}
        finally:
            try:
                await provider.close()
            except Exception:
                pass

    def _b32(self, *parts: str) -> bytes:
        return abi_codec.keccak256("|".join(parts).encode("utf-8"))

    async def _send_and_wait(self, client, *, to: str, data: str, value: int = 0) -> Dict[str, Any]:
        """Broadcast a call and wait for its receipt; classify the outcome."""
        from agents.storage.raw_tx import RawTxError

        try:
            tx_hash = await client.send_tx(to=to, data=data, value=value)
            receipt = await client.wait_for_receipt(tx_hash)
            status = int(receipt.get("status", "0x0"), 16)
            return {"ok": status == 1, "tx_hash": tx_hash, "receipt": receipt, "status": status}
        except RawTxError as e:
            return {"ok": False, "error": str(e)}

    # ── main entrypoint ──────────────────────────────────────────────────

    async def mint_agent(
        self,
        name: str,
        *,
        dry_run: bool = True,
        chain_id: int = 1337,
        list_price_wei: int = 0,
        avatar: bool = False,
        description: Optional[str] = None,
        rpc_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        name = name.strip()
        if not name or "/" in name or "." in name:
            return {"status": "error", "error": "name must be a simple slug (no '.' or '/')"}

        description = description or f"blockchain.{name} — a mindX agent minted as an ERC-7857 iNFT."
        steps: Dict[str, Any] = {}

        # 1. authored facets (seed if absent) ---------------------------------
        facets.ensure_dir()
        facets.write_agent_spec(name, description)
        if not facets.existing_facets(name)["model"]:
            facets.write_model(name, {
                "model_facet": f"blockchain.{name}",
                "task_class": "general",
                "logical_model": "auto",
                "pinned": False,
                "note": "resolved by the self-aware selector; cascades to local Ollama",
            })

        # 2. wallet -----------------------------------------------------------
        wallet = await self._create_wallet(name)
        address = wallet["address"]
        facets.write_wallet(name, address)
        steps["wallet"] = wallet

        # 3. persona ----------------------------------------------------------
        persona = facets.read_json_facet(name, "persona") or facets.synthesize_persona(name, description)
        facets.write_persona(name, persona)
        steps["persona"] = {"agent_id": persona.get("agent_id")}
        if avatar:
            steps["avatar"] = await self._maybe_avatar(name, address)

        # 4. bundle + IPFS ----------------------------------------------------
        bundle = self._bundle(name, address, persona)
        up = await self._upload_ipfs(bundle, name)
        steps["ipfs"] = up

        salt = os.urandom(16).hex()
        content_root = self._b32("content", name, address, up["sha256"], salt)
        metadata_root = self._b32("meta", name, up["sha256"])
        sealed_key_hash = self._b32("sealed", address, name, salt)

        inft_facet: Dict[str, Any] = {
            "chainId": chain_id,
            "contract": None,
            "tokenId": None,
            "contentRoot": "0x" + content_root.hex(),
            "metadataRoot": "0x" + metadata_root.hex(),
            "storageURI": up["storageURI"],
            "dimensions": DEFAULT_DIMENSIONS,
            "parallelUnits": DEFAULT_PARALLEL_UNITS,
            "salt": salt,
            "tx_hash": None,
            "status": "dry_run" if dry_run else "pending",
            "agenticPlace": None,
            "agentRegistry": None,
            "owner_custody": None,
            "agent_wallet": address,
        }
        facets.write_inft(name, inft_facet)

        if dry_run:
            facets.write_bankon(name, {"status": "dry_run", "vault_ref": f"bankon:blockchain.{name}"})
            return {
                "status": "dry_run",
                "name": name,
                "agent_wallet": address,
                "storageURI": up["storageURI"],
                "contentRoot": inft_facet["contentRoot"],
                "facets": facets.existing_facets(name),
                "steps": steps,
            }

        # 5. resolve contracts + minter --------------------------------------
        cc = contracts.load_contracts(chain_id, rpc_url)
        if not cc.mintable:
            return {
                "status": "error",
                "error": (
                    f"no iNFT_7857 address for chain {chain_id}. Run "
                    "scripts/blockchain/bootstrap_anvil.sh to deploy Tier1 and populate "
                    "data/config/blockchain_addresses.json."
                ),
                "facets": facets.existing_facets(name),
            }

        from agents.storage.raw_tx import RawTxClient

        client = RawTxClient(
            rpc_url=cc.rpc_url, chain_id=chain_id, private_key=contracts.minter_private_key()
        )
        minter = client.address
        inft_facet["contract"] = cc.inft7857
        inft_facet["owner_custody"] = minter

        try:
            # 6. mintAgent (to minter custody) -------------------------------
            token_uri = up["storageURI"]
            data = abi_codec.encode_call(
                MINT_AGENT_SIG, MINT_AGENT_TYPES,
                [minter, content_root, up["storageURI"], metadata_root,
                 DEFAULT_DIMENSIONS, DEFAULT_PARALLEL_UNITS, sealed_key_hash, token_uri],
            )
            mint = await self._send_and_wait(client, to=cc.inft7857, data=data)
            if not mint.get("ok"):
                inft_facet["status"] = "mint_failed"
                inft_facet["tx_hash"] = mint.get("tx_hash")
                inft_facet["error"] = mint.get("error")
                facets.write_inft(name, inft_facet)
                return {"status": "error", "error": f"mint reverted/failed: {mint.get('error') or 'status 0'}",
                        "name": name, "steps": steps, "iNFT": inft_facet}

            token_id = abi_codec.parse_minted_token_id(mint["receipt"])
            inft_facet.update({"tokenId": token_id, "tx_hash": mint["tx_hash"], "status": "minted"})
            steps["mint"] = {"tx_hash": mint["tx_hash"], "tokenId": token_id}
            facets.write_inft(name, inft_facet)

            # 7. list on AgenticPlace (best-effort) --------------------------
            marketplace = cc.agenticPlace or minter  # must be non-zero
            offer = await self._send_and_wait(
                client, to=cc.inft7857,
                data=abi_codec.encode_call(OFFER_SIG, OFFER_TYPES,
                                           [token_id, marketplace, int(list_price_wei), True, ZERO_ADDR]),
            )
            inft_facet["agenticPlace"] = {"marketplace": marketplace, "price_wei": int(list_price_wei),
                                          "tx_hash": offer.get("tx_hash"), "ok": offer.get("ok")}
            steps["offer"] = inft_facet["agenticPlace"]

            # 8. bind BANKON vault (best-effort) -----------------------------
            vault = cc.bankonVault or minter  # placeholder non-zero on local
            vault_ref = self._b32("bankon", name, address)
            bind_v = await self._send_and_wait(
                client, to=cc.inft7857,
                data=abi_codec.encode_call(BIND_VAULT_SIG, BIND_VAULT_TYPES, [token_id, vault, vault_ref]),
            )
            bankon_facet = {
                "vault_ref": f"bankon:blockchain.{name}",
                "vault_addr": vault,
                "vault_ref_bytes32": "0x" + vault_ref.hex(),
                "ens_subname": None,  # v2: BankonSubnameRegistrar
                "tx_hash": bind_v.get("tx_hash"),
                "ok": bind_v.get("ok"),
            }
            facets.write_bankon(name, bankon_facet)
            steps["bankon"] = {"ok": bind_v.get("ok"), "tx_hash": bind_v.get("tx_hash")}

            # 9. bind human-readable agent id (best-effort) ------------------
            agent_id = f"blockchain.{name}"
            bind_id = await self._send_and_wait(
                client, to=cc.inft7857,
                data=abi_codec.encode_call(BIND_AGENTID_SIG, BIND_AGENTID_TYPES, [token_id, agent_id]),
            )
            steps["bindAgentId"] = {"ok": bind_id.get("ok"), "tx_hash": bind_id.get("tx_hash")}

            # 10. ERC-8004 registry (best-effort) ----------------------------
            if cc.agentRegistry:
                cap_bitmap = self._b32("cap", name)  # off-chain interpreted
                reg = await self._send_and_wait(
                    client, to=cc.agentRegistry,
                    data=abi_codec.encode_call(REGISTER_SIG, REGISTER_TYPES,
                                               [address, agent_id, cc.inft7857, cap_bitmap, up["storageURI"]]),
                )
                reg_token = abi_codec.parse_event_uint(
                    reg["receipt"], "AgentRegistered(uint256,address,bytes32,string,address,bytes32,string)", 1
                ) if reg.get("ok") else None
                inft_facet["agentRegistry"] = {"contract": cc.agentRegistry, "agentTokenId": reg_token,
                                               "tx_hash": reg.get("tx_hash"), "ok": reg.get("ok")}
                steps["registry"] = inft_facet["agentRegistry"]

            facets.write_inft(name, inft_facet)
            self._append_production_registry(name, address, wallet["vault_id"], inft_facet)

            return {
                "status": "minted",
                "name": name,
                "agent_wallet": address,
                "owner_custody": minter,
                "tokenId": token_id,
                "contract": cc.inft7857,
                "tx_hash": mint["tx_hash"],
                "storageURI": up["storageURI"],
                "facets": facets.existing_facets(name),
                "steps": steps,
                "iNFT": inft_facet,
            }
        finally:
            await client.close()

    async def _maybe_avatar(self, name: str, address: str) -> Dict[str, Any]:
        try:
            from agents.avatar_agent import AvatarAgent  # noqa: F401

            return {"status": "skipped", "note": "avatar generation hook available; not run in v1"}
        except Exception:
            return {"status": "unavailable"}

    def _append_production_registry(self, name: str, address: str, vault_id: str, inft_facet: Dict[str, Any]) -> None:
        path = os.path.join(str(PROJECT_ROOT), "data", "identity", "production_registry.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                reg = json.load(fh)
        except Exception:
            return  # don't fabricate the registry; skip silently
        agents = reg.setdefault("agents", [])
        entity_id = f"blockchain.agent.{name}"
        record = {
            "entity_id": entity_id,
            "role": "Blockchain Agent — minted as ERC-7857 iNFT",
            "address": address,
            "vault_id": vault_id,
            "blockchain": {
                "chainId": inft_facet.get("chainId"),
                "contract": inft_facet.get("contract"),
                "tokenId": inft_facet.get("tokenId"),
                "tx_hash": inft_facet.get("tx_hash"),
            },
        }
        for i, a in enumerate(agents):
            if a.get("entity_id") == entity_id:
                agents[i] = record
                break
        else:
            agents.append(record)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(reg, fh, indent=2, ensure_ascii=False)
        except Exception as e:  # pragma: no cover
            logger.warning(f"{self.log_prefix} could not write production registry: {e}")
