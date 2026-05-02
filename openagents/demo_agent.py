#!/usr/bin/env python3
"""
mindX Open-Agents end-to-end demo.

Runs the full sequence judges see in the 3-min video:

  1. Build encrypted payload (CEO + 7 soldier personas + boardroom memory).
  2. Upload payload to 0G Storage via the Node sidecar.
  3. Mint an ERC-7857 iNFT on 0G Galileo with the merkle root anchored
     on chain.
  4. Run one BDI cycle whose inference goes through 0G Compute,
     capturing the ZG-Res-Key attestation header per call.
  5. Anchor the cycle session log on Galileo via DatasetRegistry
     (the same selector our anchor.py already speaks).
  6. Print every hash + chainscan-galileo.0g.ai URL.

Usage:
  python openagents/demo_agent.py                 # full flow (needs all keys)
  python openagents/demo_agent.py --dry-run       # no contract writes
  python openagents/demo_agent.py --skip-mint     # run inference + anchor only

Required env (loaded from BANKON Vault → environment):
  ZEROG_API_KEY            (0G Compute key)
  ZEROG_PRIVATE_KEY        (deployer / minter for Galileo)
  ZEROG_RPC_URL            (default https://evmrpc-testnet.0g.ai)
  ZEROG_SIDECAR_URL        (default http://127.0.0.1:7878)
  Deployment file:
    openagents/deployments/galileo.json      (written by deploy_galileo.sh)
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.logging_config import get_logger  # noqa: E402

logger = get_logger("openagents.demo")

EXPLORER = "https://chainscan-galileo.0g.ai"
DEPLOYMENTS_FILE = ROOT / "openagents" / "deployments" / "galileo.json"


# --------------------------------------------------------------------- #
# 1. Build payload
# --------------------------------------------------------------------- #

def collect_persona_files() -> Dict[str, str]:
    """Read the CEO + 7 soldier persona prompts + executive board config."""
    base = ROOT / "AgenticPlace"
    files = [
        "ceo_agent.prompt", "coo_agent.prompt", "cfo_agent.prompt",
        "cto_agent.prompt", "ciso_agent.prompt", "clo_agent.prompt",
        "cpo_agent.prompt", "cro_agent.prompt",
        "executive_board.yaml", "persona.json",
    ]
    out: Dict[str, str] = {}
    for f in files:
        p = base / f
        if p.exists():
            out[f] = p.read_text(encoding="utf-8")
    return out


def collect_recent_memory(max_bytes: int = 256 * 1024) -> Dict[str, Any]:
    """Pull the most recent boardroom session log + dream report (truncated)."""
    out: Dict[str, Any] = {}
    sessions_log = ROOT / "data" / "governance" / "boardroom_sessions.jsonl"
    if sessions_log.exists():
        # Tail last `max_bytes` of session log, by line.
        sz = sessions_log.stat().st_size
        with sessions_log.open("rb") as fh:
            if sz > max_bytes:
                fh.seek(sz - max_bytes)
                fh.readline()  # discard partial line
            tail = fh.read().decode("utf-8", errors="ignore")
        out["boardroom_sessions_tail"] = tail

    dreams_dir = ROOT / "data" / "memory" / "dreams"
    if dreams_dir.exists():
        reports = sorted(dreams_dir.glob("*_dream_report.json"))
        if reports:
            try:
                out["latest_dream_report"] = json.loads(reports[-1].read_text())
            except Exception as e:
                out["latest_dream_report_error"] = str(e)
    return out


def build_payload() -> bytes:
    """Build the encrypted-style payload bundle.

    For the demo we ship a gzipped JSON bundle. Real production mints would
    AES-256-GCM encrypt under a per-iNFT key sealed for the owner — those
    helpers live in the forked 0glabs/0g-agent-nft @eip-7857-draft repo
    and are wired in for the May 1 production mint.
    """
    bundle = {
        "schema": "mindx.openagents.payload.v1",
        "agnostic": True,
        "framework_compatibility": ["openclaw", "nanoclaw", "zeroclaw", "nullclaw", "any"],
        "personas": collect_persona_files(),
        "memory": collect_recent_memory(),
        "framework_version": "mindX-1.0",
        "minted_at_epoch": int(time.time()),
    }
    raw = json.dumps(bundle, separators=(",", ":")).encode("utf-8")
    gz = gzip.compress(raw)
    return gz


# --------------------------------------------------------------------- #
# 2. Upload to 0G Storage
# --------------------------------------------------------------------- #

async def upload_payload(payload: bytes) -> Dict[str, Any]:
    from agents.storage.zerog_provider import ZeroGProvider

    provider = ZeroGProvider()
    health = await provider.health()
    if not health.get("reachable"):
        raise RuntimeError(f"0G Storage sidecar not reachable: {health}")

    root, tx = await provider.upload(payload, name=f"mindx-iNFT-{int(time.time())}.json.gz")
    await provider.close()

    return {
        "root": root.value,
        "uri": root.uri,
        "tx_hash": tx,
        "tx_explorer": f"{EXPLORER}/tx/{tx}" if tx else None,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


# --------------------------------------------------------------------- #
# 3. Mint ERC-7857 iNFT on 0G Galileo
# --------------------------------------------------------------------- #

def load_deployments() -> Dict[str, Any]:
    if not DEPLOYMENTS_FILE.exists():
        raise FileNotFoundError(
            f"{DEPLOYMENTS_FILE} not found — run openagents/deploy/deploy_galileo.sh first."
        )
    return json.loads(DEPLOYMENTS_FILE.read_text())


_INFT_ABI = [
    {
        "inputs": [
            {"name": "to",            "type": "address"},
            {"name": "contentRoot",   "type": "bytes32"},
            {"name": "storageURI",    "type": "string"},
            {"name": "metadataRoot",  "type": "bytes32"},
            {"name": "dimensions",    "type": "uint32"},
            {"name": "parallelUnits", "type": "uint8"},
            {"name": "sealedKeyHash", "type": "bytes32"},
            {"name": "tokenURI_",     "type": "string"},
        ],
        "name": "mintAgent",
        "outputs": [{"name": "tokenId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "tokenId",     "type": "uint256"},
            {"indexed": True, "name": "contentRoot", "type": "bytes32"},
            {"indexed": False, "name": "dimensions", "type": "uint32"},
            {"indexed": True, "name": "owner",       "type": "address"},
        ],
        "name": "AgentMinted",
        "type": "event",
    },
]


def mint_inft_blocking(deploy: Dict[str, Any], upload_info: Dict[str, Any]) -> Dict[str, Any]:
    from web3 import Web3
    from eth_account import Account

    pk = os.environ.get("ZEROG_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("ZEROG_PRIVATE_KEY not set")

    rpc = deploy["rpc"]
    inft_addr = Web3.to_checksum_address(deploy["contracts"]["iNFT_7857"]["address"])

    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    contract = w3.eth.contract(address=inft_addr, abi=_INFT_ABI)
    account = Account.from_key(pk)

    content_root  = bytes.fromhex(upload_info["root"][2:])
    metadata_root = hashlib.sha256(b"mindx-metadata-" + content_root).digest()
    sealed_hash   = hashlib.sha256(b"sealed-key-" + content_root).digest()
    storage_uri   = upload_info["uri"]
    token_uri     = f"https://mindx.pythai.net/inft/{upload_info['root']}"

    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.mintAgent(
        account.address,
        content_root,
        storage_uri,
        metadata_root,
        2048,    # THOT2048 — cypherpunk2048 standard
        8,       # parallel units
        sealed_hash,
        token_uri,
    ).build_transaction({
        "from":    account.address,
        "nonce":   nonce,
        "chainId": w3.eth.chain_id,
        "maxFeePerGas":         w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
    })
    try:
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    except Exception:
        tx["gas"] = 1_200_000

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    # Decode AgentMinted event
    token_id: Optional[int] = None
    try:
        events = contract.events.AgentMinted().process_receipt(receipt)
        if events:
            token_id = int(events[0]["args"]["tokenId"])
    except Exception:
        pass

    return {
        "ok": receipt.status == 1,
        "contract": inft_addr,
        "owner": account.address,
        "token_id": token_id,
        "tx_hash": tx_hash.hex(),
        "tx_explorer": f"{EXPLORER}/tx/{tx_hash.hex()}",
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "content_root": upload_info["root"],
        "storage_uri": storage_uri,
    }


async def mint_inft(deploy: Dict[str, Any], upload_info: Dict[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(mint_inft_blocking, deploy, upload_info)


# --------------------------------------------------------------------- #
# 4. Run a BDI cycle through 0G Compute
# --------------------------------------------------------------------- #

async def run_bdi_cycle_via_zerog(directive: str) -> Dict[str, Any]:
    from llm.llm_factory import create_llm_handler

    handler = await create_llm_handler(
        provider_name="zerog",
        model_name="zerog/gpt-oss-120b",
    )

    soldiers = ["CEO", "COO", "CFO", "CTO", "CISO", "CLO", "CPO", "CRO"]
    votes = []

    for s in soldiers:
        prompt = (
            f"You are the {s} of the mindX boardroom. "
            f"Directive: '{directive}'.\n"
            f"Reply in one short paragraph with your role-specific take, "
            f"then end with a vote line: 'VOTE: approve/reject/abstain'."
        )
        try:
            text = await handler.generate_text(
                prompt=prompt,
                model="zerog/gpt-oss-120b",
                max_tokens=180,
                temperature=0.4,
            )
        except Exception as e:
            text = f"[ERROR] {e}"

        votes.append({
            "soldier": s,
            "response": text,
            "attestation": handler.last_attestation,
            "serving_backend": handler.last_serving_backend,
            "model": handler.last_model,
        })

    if hasattr(handler, "close"):
        await handler.close()

    return {
        "directive": directive,
        "soldier_count": len(soldiers),
        "votes": votes,
        "attestations_collected": sum(1 for v in votes if v.get("attestation")),
    }


# --------------------------------------------------------------------- #
# 5. Anchor session log via DatasetRegistry
# --------------------------------------------------------------------- #

async def anchor_session(deploy: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    """Write the session log to 0G Storage and emit a DatasetRegistry tx
    pointing at it. Reuses anchor.py's `f1783fb8` selector against the new
    DatasetRegistry address on Galileo (no anchor.py code touched).
    """
    from agents.storage.zerog_provider import ZeroGProvider

    raw = json.dumps(session, separators=(",", ":")).encode("utf-8")
    provider = ZeroGProvider()
    root, tx = await provider.upload(raw, name=f"session-{int(time.time())}.json")
    await provider.close()

    # On-chain anchor — minimal raw selector call so this works even if
    # agents/storage/anchor.py isn't configured for 0G.
    anchor = await asyncio.to_thread(_anchor_blocking, deploy, root.value, root.uri)
    return {
        "session_root": root.value,
        "session_uri": root.uri,
        "session_upload_tx": tx,
        **anchor,
    }


def _anchor_blocking(deploy: Dict[str, Any], root_hex: str, uri: str) -> Dict[str, Any]:
    from web3 import Web3
    from eth_account import Account

    pk = os.environ.get("ZEROG_PRIVATE_KEY")
    if not pk:
        return {"anchor_skipped": "no key"}

    rpc = deploy["rpc"]
    dsreg = Web3.to_checksum_address(deploy["contracts"]["DatasetRegistry"]["address"])
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    account = Account.from_key(pk)

    # registerDataset(bytes32 root, string uri) — selector 0xf1783fb8
    selector = bytes.fromhex("f1783fb8")
    root_bytes = bytes.fromhex(root_hex[2:]).rjust(32, b"\x00")
    # Encode string ABI: offset (32 bytes) | length (32 bytes) | data padded to 32
    uri_bytes = uri.encode("utf-8")
    pad = (32 - (len(uri_bytes) % 32)) % 32
    uri_encoded = (
        (32 + 32).to_bytes(32, "big")             # offset to string section (after root + offset slot)
        + len(uri_bytes).to_bytes(32, "big")
        + uri_bytes + b"\x00" * pad
    )
    data = selector + root_bytes + uri_encoded

    nonce = w3.eth.get_transaction_count(account.address)
    tx = {
        "to": dsreg,
        "from": account.address,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "data": data,
        "value": 0,
        "maxFeePerGas":         w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
        "gas": 250_000,
    }
    try:
        signed = account.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
        return {
            "anchor_contract": dsreg,
            "anchor_tx": h.hex(),
            "anchor_explorer": f"{EXPLORER}/tx/{h.hex()}",
            "anchor_status": rcpt.status,
        }
    except Exception as e:
        return {"anchor_error": str(e), "anchor_contract": dsreg}


# --------------------------------------------------------------------- #
# 6. BANKON v1 subname registration  (Module 4)
# --------------------------------------------------------------------- #

async def register_bankon_subname(agent_id: str, agent_wallet: str, persona_url: str) -> Dict[str, Any]:
    """Best-effort BANKON subname registration. Returns receipt envelope.

    Skips if SubdomainIssuer is not configured (no ENS_RPC_URL or registrar
    address). Returns the dry-run envelope from the issuer in that case.
    """
    try:
        from openagents.ens.subdomain_issuer import (
            SubdomainIssuer, AgentMetadata, get_default_issuer,
        )
        issuer = await get_default_issuer()
        if issuer is None:
            return {"ok": False, "skipped": "issuer-not-configured"}

        meta = AgentMetadata(
            agentURI=persona_url,
            mindxEndpoint=persona_url,
        )
        # Try free path first (label ≥7 chars + reputation gate); fall back to paid.
        if len(agent_id) >= 7:
            res = await issuer.register_free(agent_id, agent_wallet, meta=meta)
            if res.get("ok"):
                return res
        return await issuer.register_paid(agent_id, agent_wallet, meta=meta)
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --------------------------------------------------------------------- #
# 7. AgentRegistry (ERC-8004) registration  (Module 8)
# --------------------------------------------------------------------- #

_AGENTREG_ABI_FRAGMENT = [
    {
        "inputs": [
            {"name": "owner",            "type": "address"},
            {"name": "agentId",          "type": "string"},
            {"name": "linkedINFT_7857",  "type": "address"},
            {"name": "capabilityBitmap", "type": "bytes32"},
            {"name": "attestationURI",   "type": "string"},
        ],
        "name": "register",
        "outputs": [{"name": "agentTokenId", "type": "uint256"}],
        "stateMutability": "nonpayable", "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "agentTokenId",     "type": "uint256"},
            {"indexed": True,  "name": "owner",            "type": "address"},
            {"indexed": True,  "name": "agentIdHash",      "type": "bytes32"},
            {"indexed": False, "name": "agentId",          "type": "string"},
            {"indexed": False, "name": "linkedINFT_7857",  "type": "address"},
            {"indexed": False, "name": "capabilityBitmap", "type": "bytes32"},
            {"indexed": False, "name": "attestationURI",   "type": "string"},
        ],
        "name": "AgentRegistered", "type": "function",
    },
]


def _register_agentreg_blocking(deploy: Dict[str, Any], agent_id: str,
                                inft_addr: Optional[str], persona_url: str) -> Dict[str, Any]:
    from web3 import Web3
    from eth_account import Account

    pk = os.environ.get("ZEROG_PRIVATE_KEY")
    if not pk:
        return {"skipped": "no-zerog-pk"}
    contracts = deploy.get("contracts", {})
    addr = contracts.get("AgentRegistry", {}).get("address")
    if not addr:
        return {"skipped": "AgentRegistry-not-deployed"}

    w3 = Web3(Web3.HTTPProvider(deploy["rpc"], request_kwargs={"timeout": 30}))
    contract = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=_AGENTREG_ABI_FRAGMENT)
    account = Account.from_key(pk)

    nonce = w3.eth.get_transaction_count(account.address)
    capability_bitmap = b"\x00" * 31 + b"\x01"      # bit 0 = "can do inference"
    inft_param = Web3.to_checksum_address(inft_addr) if inft_addr else "0x" + "0" * 40
    fn = contract.functions.register(
        account.address, agent_id, inft_param, capability_bitmap, persona_url,
    )
    tx = fn.build_transaction({
        "from": account.address, "nonce": nonce, "chainId": w3.eth.chain_id,
        "maxFeePerGas":         w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
    })
    try:
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    except Exception:
        tx["gas"] = 600_000

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return {
        "ok": receipt.status == 1,
        "contract":   addr,
        "tx_hash":    tx_hash.hex(),
        "explorer":   f"{EXPLORER}/tx/{tx_hash.hex()}",
        "agent_id":   agent_id,
        "linked_inft": inft_param,
    }


async def register_with_agentregistry(deploy: Dict[str, Any], agent_id: str,
                                      inft_addr: Optional[str], persona_url: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_register_agentreg_blocking, deploy, agent_id, inft_addr, persona_url)


# --------------------------------------------------------------------- #
# 8. Conclave session compose-only demo  (Module 3)
# --------------------------------------------------------------------- #

def conclave_compose_demo(directive: str) -> Dict[str, Any]:
    """Illustrative composition: route via the boardroom adapter without
    spinning up an actual mesh. Shows the agnostic-module shape — the
    adapter never imports mindX, mindX never imports Conclave internals.
    """
    try:
        sys.path.insert(0, str(ROOT / "openagents" / "conclave"))
        from integrations.mindx_boardroom_adapter import (   # noqa: E402
            is_high_stakes, agenda_hash, _generate_conclave_id,
        )
        return {
            "ok": True,
            "directive": directive,
            "high_stakes": is_high_stakes(directive),
            "agenda_hash": agenda_hash(f"# Agenda\n\n- {directive}\n"),
            "conclave_id_preview": _generate_conclave_id(directive),
            "note": "compose-only — set up an 8-node mesh to convene live "
                    "(see openagents/conclave/examples/run_local_8node.sh)",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --------------------------------------------------------------------- #
# 9. Uniswap quote demo  (Module 6)
# --------------------------------------------------------------------- #

async def uniswap_quote_demo() -> Dict[str, Any]:
    """One-off USDC → WETH quote against Sepolia. Read-only, no signer needed."""
    try:
        from tools.uniswap_v4_tool import UniswapV4Tool
        tool = UniswapV4Tool()
        info = await tool.execute("info")
        addrs = info.get("addresses", {})
        usdc, weth = addrs.get("usdc"), addrs.get("weth")
        if not usdc or not weth:
            return {"ok": False, "error": "addresses not configured"}
        quote = await tool.execute("quote", {
            "token_in":  usdc, "token_out": weth,
            "amount_in": 1_000_000,        # 1 USDC (6 decimals)
            "fee":       3000,
            "tick_spacing": 60,
        })
        return {"ok": quote.get("ok", False), "network": info.get("network"), "quote": quote}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --------------------------------------------------------------------- #
# 10. KeeperHub bridge inbound demo  (Module 5)
# --------------------------------------------------------------------- #

async def keeperhub_inbound_demo(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Hit /p2p/keeperhub/inference without payment, capture the 402 envelope.

    Demonstrates the bridge is correctly emitting dual-network challenges
    (Base USDC + Tempo MPP) without needing actual KH wallet integration.
    """
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/p2p/keeperhub/inference",
                json={"prompt": "demo"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                body = await resp.json()
                if resp.status == 402:
                    schemes = [a.get("scheme") for a in body.get("accepts", [])]
                    nets    = [a.get("network") for a in body.get("accepts", [])]
                    return {
                        "ok": True, "status": 402, "schemes": schemes, "networks": nets,
                        "amounts_usdc_units": [a.get("maxAmountRequired") for a in body.get("accepts", [])],
                    }
                return {"ok": False, "status": resp.status, "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e), "note": f"backend not reachable at {base_url}"}


# --------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------- #

async def main():
    ap = argparse.ArgumentParser(description="mindX Open Agents end-to-end demo")
    ap.add_argument("--dry-run", action="store_true", help="No contract writes")
    ap.add_argument("--skip-mint", action="store_true", help="Skip iNFT mint, do inference + anchor only")
    ap.add_argument("--skip-extras", action="store_true",
                    help="Skip the ancillary modules (BANKON, AgentRegistry, Conclave compose, Uniswap, KH)")
    ap.add_argument("--agent-id", default="ceo-mastermind-v1",
                    help="Agent identifier for BANKON + AgentRegistry registration")
    ap.add_argument("--persona-url", default="https://mindx.pythai.net/agent/ceo-mastermind-v1")
    ap.add_argument("--directive", default="Should mindX prioritize ENS or KeeperHub integration this sprint?",
                    help="Directive for the boardroom to deliberate")
    ap.add_argument("--backend-url", default="http://localhost:8000",
                    help="Local mindX backend base URL for the KeeperHub demo")
    args = ap.parse_args()

    print("=" * 78)
    print(" mindX Open Agents Demo — agnostic agentic infrastructure")
    print("=" * 78)

    # Step 1
    print("\n[1/5] Building payload (CEO + 7 soldier personas + recent memory)…")
    payload = build_payload()
    print(f"      → {len(payload):>8} bytes  sha256={hashlib.sha256(payload).hexdigest()[:16]}…")

    if args.dry_run:
        print("\n[DRY RUN] Stopping after payload build.")
        return

    # Step 2
    print("\n[2/5] Uploading to 0G Storage via sidecar…")
    upload_info = await upload_payload(payload)
    print(f"      root      : {upload_info['root']}")
    print(f"      uri       : {upload_info['uri']}")
    print(f"      tx_hash   : {upload_info['tx_hash']}")
    if upload_info.get("tx_explorer"):
        print(f"      explorer  : {upload_info['tx_explorer']}")

    deploy = load_deployments()

    # Step 3
    if args.skip_mint:
        print("\n[3/5] Skipping iNFT mint (--skip-mint).")
        mint_info = {"skipped": True}
    else:
        print("\n[3/5] Minting ERC-7857 iNFT on Galileo…")
        mint_info = await mint_inft(deploy, upload_info)
        if mint_info.get("ok"):
            print(f"      contract  : {mint_info['contract']}")
            print(f"      tokenId   : {mint_info['token_id']}")
            print(f"      owner     : {mint_info['owner']}")
            print(f"      tx_hash   : {mint_info['tx_hash']}")
            print(f"      explorer  : {mint_info['tx_explorer']}")
        else:
            print(f"      MINT FAILED: {mint_info}")

    # Step 4
    print(f"\n[4/5] Running BDI cycle on 0G Compute  (directive: {args.directive!r})…")
    session = await run_bdi_cycle_via_zerog(args.directive)
    print(f"      soldiers polled        : {session['soldier_count']}")
    print(f"      attestations collected : {session['attestations_collected']}")
    for v in session["votes"]:
        att = (v.get("attestation") or "—")[:24]
        print(f"        {v['soldier']:5s}  attest={att}…")

    # Step 5
    print("\n[5/10] Anchoring session log on Galileo DatasetRegistry…")
    anchor = await anchor_session(deploy, session)
    print(f"       session root : {anchor.get('session_root')}")
    if anchor.get("anchor_tx"):
        print(f"       anchor tx    : {anchor['anchor_tx']}")
        print(f"       explorer     : {anchor['anchor_explorer']}")
    elif anchor.get("anchor_error"):
        print(f"       ANCHOR ERROR : {anchor['anchor_error']}")

    # ─── Ancillary modules (the rest of the 8-module composition) ───
    bankon_res    = {"skipped": True}
    agentreg_res  = {"skipped": True}
    conclave_res  = {"skipped": True}
    uniswap_res   = {"skipped": True}
    keeperhub_res = {"skipped": True}

    if not args.skip_extras:
        # Step 6 — BANKON v1 subname
        print(f"\n[6/10] Registering BANKON v1 subname for agent_id={args.agent_id!r}…")
        from web3 import Web3
        from eth_account import Account
        agent_wallet = (
            Account.from_key(os.environ["ZEROG_PRIVATE_KEY"]).address
            if os.environ.get("ZEROG_PRIVATE_KEY") else "0x" + "0"*40
        )
        bankon_res = await register_bankon_subname(args.agent_id, agent_wallet, args.persona_url)
        if bankon_res.get("ok"):
            print(f"       subname      : {bankon_res.get('subname')}")
            print(f"       tx_hash      : {bankon_res.get('tx_hash')}")
            print(f"       erc8004_id   : {bankon_res.get('erc8004_agent_id')}")
        else:
            print(f"       SKIPPED      : {bankon_res.get('reason') or bankon_res.get('skipped') or bankon_res.get('error')}")

        # Step 7 — AgentRegistry (ERC-8004)
        print(f"\n[7/10] Registering on ERC-8004 AgentRegistry…")
        inft_addr = (mint_info or {}).get("contract")
        agentreg_res = await register_with_agentregistry(deploy, args.agent_id, inft_addr, args.persona_url)
        if agentreg_res.get("ok"):
            print(f"       contract     : {agentreg_res['contract']}")
            print(f"       tx_hash      : {agentreg_res['tx_hash']}")
            print(f"       linked_inft  : {agentreg_res['linked_inft']}")
        else:
            print(f"       SKIPPED      : {agentreg_res.get('skipped') or agentreg_res.get('error')}")

        # Step 8 — Conclave composition demo
        print(f"\n[8/10] Conclave composition (high-stakes routing check)…")
        conclave_res = conclave_compose_demo(args.directive)
        print(f"       high_stakes  : {conclave_res.get('high_stakes')}")
        print(f"       agenda_hash  : {conclave_res.get('agenda_hash', '')[:20]}…")

        # Step 9 — Uniswap quote
        print(f"\n[9/10] Uniswap V4 quote (USDC → WETH on Sepolia)…")
        uniswap_res = await uniswap_quote_demo()
        if uniswap_res.get("ok"):
            q = uniswap_res.get("quote", {})
            print(f"       network      : {uniswap_res.get('network')}")
            print(f"       amount_out   : {q.get('amount_out')}")
            print(f"       gas_est      : {q.get('gas_estimate')}")
        else:
            print(f"       SKIPPED      : {uniswap_res.get('error')}")

        # Step 10 — KeeperHub inbound 402
        print(f"\n[10/10] KeeperHub bridge inbound 402 envelope…")
        keeperhub_res = await keeperhub_inbound_demo(args.backend_url)
        if keeperhub_res.get("ok"):
            print(f"       schemes      : {keeperhub_res.get('schemes')}")
            print(f"       networks     : {keeperhub_res.get('networks')}")
            print(f"       amounts      : {keeperhub_res.get('amounts_usdc_units')} (USDC base units)")
        else:
            print(f"       SKIPPED      : {keeperhub_res.get('error') or keeperhub_res.get('note')}")

    print("\n" + "=" * 78)
    print(" SUMMARY — 8-module composition")
    print("=" * 78)
    summary = {
        "payload":   {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()},
        "M2_upload":         upload_info,
        "M1_mint":           mint_info,
        "M2_session":        {
            "directive": session["directive"],
            "soldier_count": session["soldier_count"],
            "attestations_collected": session["attestations_collected"],
        },
        "M7_anchor":         anchor,
        "M4_bankon":         bankon_res,
        "M8_agentregistry":  agentreg_res,
        "M3_conclave":       conclave_res,
        "M6_uniswap":        uniswap_res,
        "M5_keeperhub":      keeperhub_res,
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
