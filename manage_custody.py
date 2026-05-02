#!/usr/bin/env python3
"""
BANKON Vault Custody Handoff Ceremony CLI.

Composable subcommands for the Machine → Human overseer handoff.  See the
plan at /home/hacker/.claude/plans/glimmering-growing-scroll.md §"BANKON
Vault Custody Handoff — Two-Stage Overseer Model" for the full design.

Typical Stage-1 sequence:

    export MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1
    python manage_custody.py preflight
    python manage_custody.py challenge --address 0xYOUR > ./handoff_challenge.txt
    # sign externally (MetaMask / Ledger / `cast wallet sign`)
    python manage_custody.py dry-run --address 0xYOUR --signature 0x...
    python manage_custody.py commit  --address 0xYOUR --signature 0x... --i-am-sure
    python manage_custody.py transfer-agents --chain base-sepolia --to 0xYOUR
    python manage_custody.py update-agent-map --to 0xYOUR
    python manage_custody.py lock-routes --address 0xYOUR
    python manage_custody.py smoke-test
    unset MINDX_VAULT_ALLOW_OVERSEER_ROTATION
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Paths
VAULT_DIR_DEFAULT = PROJECT_ROOT / "mindx_backend_service" / "vault_bankon"
ALT_VAULT_DIR = PROJECT_ROOT / "data" / "vault_bankon"
AGENT_MAP_PATH = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
PRODUCTION_REGISTRY = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
OVERSEER_HISTORY = PROJECT_ROOT / "data" / "governance" / "overseer_history.jsonl"
ROTATION_LOCK = None  # set after vault is located
CHALLENGE_FILE_DEFAULT = PROJECT_ROOT / "handoff_challenge.txt"


def _locate_vault_dir() -> Path:
    """Find the actual vault_bankon directory (prod vs dev layouts differ)."""
    for p in (VAULT_DIR_DEFAULT, ALT_VAULT_DIR):
        if p.exists():
            return p
    # Neither exists — return the default path; BankonVault() will create it.
    return VAULT_DIR_DEFAULT


def _load_vault(require_unlocked: bool = True):
    """Instantiate BankonVault and unlock via whichever overseer is active."""
    from mindx_backend_service.bankon_vault.vault import BankonVault
    vault_dir = _locate_vault_dir()
    v = BankonVault(vault_dir=str(vault_dir))
    if not require_unlocked:
        return v, vault_dir
    sentinel = vault_dir / ".human_overseer_active"
    if sentinel.exists():
        from mindx_backend_service.bankon_vault.overseer import load_human_from_proof
        proof_path = vault_dir / ".overseer_proof.json"
        if not proof_path.exists():
            raise RuntimeError(
                f"vault is under HumanOverseer (sentinel present) but {proof_path} missing — "
                "cannot re-unlock without operator re-signing."
            )
        overseer, challenge_bytes, evidence = load_human_from_proof(proof_path, v._salt)
        v.unlock_with_overseer(overseer, challenge_bytes, evidence)
    else:
        v.unlock_with_key_file()
    return v, vault_dir


def _check_env_flag() -> None:
    if not os.environ.get("MINDX_VAULT_ALLOW_OVERSEER_ROTATION"):
        print("ERROR: MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1 required", file=sys.stderr)
        print("       export MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1", file=sys.stderr)
        sys.exit(2)


def _normalize_addr(addr: str) -> str:
    if not addr.startswith("0x") or len(addr) != 42:
        raise argparse.ArgumentTypeError(
            f"not a 0x... 20-byte address: {addr!r}"
        )
    try:
        int(addr, 16)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not hex: {addr!r}")
    return addr.lower()


# ─────────────────────────────────────────────────────────────────────────
# preflight
# ─────────────────────────────────────────────────────────────────────────

def cmd_preflight(args: argparse.Namespace) -> int:
    vault_dir = _locate_vault_dir()
    print(f"[preflight] vault_dir: {vault_dir}")
    print(f"[preflight] exists: {vault_dir.exists()}")

    sentinel = vault_dir / ".human_overseer_active"
    master_key = vault_dir / ".master.key"
    proof = vault_dir / ".overseer_proof.json"
    entries_file = vault_dir / "entries.json"
    rotation_ok = vault_dir / ".rotation.ok"
    rotation_lock = vault_dir / ".rotation.lock"

    print(f"[preflight] sentinel .human_overseer_active: {sentinel.exists()}")
    print(f"[preflight] .master.key: exists={master_key.exists()} " + (
        f"(size={master_key.stat().st_size}, mtime={time.ctime(master_key.stat().st_mtime)})" if master_key.exists() else ""))
    print(f"[preflight] .overseer_proof.json: {proof.exists()}")
    print(f"[preflight] .rotation.ok marker (in-flight): {rotation_ok.exists()}")
    if rotation_lock.exists():
        print(f"[preflight] WARNING: .rotation.lock present — another run may be active")

    if entries_file.exists():
        try:
            data = json.loads(entries_file.read_text())
            entries = data.get("entries", [])
            agent_pk = sum(1 for e in entries if e.get("id", "").startswith("agent_pk_"))
            print(f"[preflight] entries.json: {len(entries)} entries total, {agent_pk} agent_pk_*")
        except Exception as e:
            print(f"[preflight] entries.json: unreadable: {e}")
    else:
        print(f"[preflight] entries.json: missing")

    flag_set = bool(os.environ.get("MINDX_VAULT_ALLOW_OVERSEER_ROTATION"))
    print(f"[preflight] MINDX_VAULT_ALLOW_OVERSEER_ROTATION set: {flag_set}")
    if not flag_set:
        print("[preflight] HINT: export MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1 before dry-run/commit")
    return 0


# ─────────────────────────────────────────────────────────────────────────
# challenge
# ─────────────────────────────────────────────────────────────────────────

def cmd_challenge(args: argparse.Namespace) -> int:
    addr = _normalize_addr(args.address)
    vault_dir = _locate_vault_dir()
    # Fingerprint binds this challenge to THIS specific vault
    salt = (vault_dir / ".salt").read_bytes() if (vault_dir / ".salt").exists() else b""
    entries_bytes = (vault_dir / "entries.json").read_bytes() if (vault_dir / "entries.json").exists() else b""
    fingerprint = hashlib.sha256(salt + entries_bytes[:4096]).hexdigest()[:16]
    nonce = secrets.token_hex(16)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    message = (
        "BANKON Vault Custody Handoff v1\n"
        f"Vault Fingerprint: {fingerprint}\n"
        f"Overseer Address:  {addr}\n"
        f"Issued:            {ts}\n"
        f"Nonce:             {nonce}\n"
        "By signing, I accept custodianship of this vault and all agents under its keyring."
    )
    out_path = Path(args.out) if args.out else CHALLENGE_FILE_DEFAULT
    out_path.write_text(message)
    print(f"[challenge] wrote: {out_path}")
    print("[challenge] message (sign this with your wallet — MetaMask personal_sign / Ledger / `cast wallet sign $(cat ...)`):")
    print("-" * 64)
    print(message)
    print("-" * 64)
    return 0


# ─────────────────────────────────────────────────────────────────────────
# dry-run + commit (shared internals)
# ─────────────────────────────────────────────────────────────────────────

def _build_human_overseer(address: str, signature: str, message: str, vault_salt: bytes):
    from mindx_backend_service.bankon_vault.overseer import HumanOverseer
    overseer = HumanOverseer(eth_address=address, vault_salt=vault_salt)
    if not signature.startswith("0x"):
        signature = "0x" + signature
    evidence = {"kind": "human", "signature": signature, "message": message}
    challenge_bytes = message.encode("utf-8")
    return overseer, challenge_bytes, evidence


def _load_challenge_message(path: Optional[str]) -> str:
    p = Path(path) if path else CHALLENGE_FILE_DEFAULT
    if not p.exists():
        raise FileNotFoundError(f"challenge file missing: {p}")
    return p.read_text()


def cmd_dry_run(args: argparse.Namespace) -> int:
    _check_env_flag()
    addr = _normalize_addr(args.address)
    v, vault_dir = _load_vault(require_unlocked=True)

    message = _load_challenge_message(args.challenge)
    overseer, challenge_bytes, evidence = _build_human_overseer(
        addr, args.signature, message, v._salt,
    )
    res = v.rotate_overseer(overseer, challenge_bytes, evidence,
                            reason="stage1_custody_dry_run", dry_run=True)
    print(json.dumps(res, indent=2))
    return 0 if res.get("status") == "dry_run_ok" else 1


def cmd_commit(args: argparse.Namespace) -> int:
    _check_env_flag()
    if not args.i_am_sure:
        print("ERROR: refusing to commit without --i-am-sure", file=sys.stderr)
        return 2
    addr = _normalize_addr(args.address)
    v, vault_dir = _load_vault(require_unlocked=True)

    # Re-run dry-run to ensure candidate is fresh; then commit.
    message = _load_challenge_message(args.challenge)
    overseer, challenge_bytes, evidence = _build_human_overseer(
        addr, args.signature, message, v._salt,
    )
    print("[commit] re-running dry-run to refresh candidate + marker")
    dry = v.rotate_overseer(overseer, challenge_bytes, evidence,
                            reason="stage1_custody_commit_preflight", dry_run=True)
    if dry.get("status") != "dry_run_ok":
        print("ERROR: dry-run failed; aborting commit", file=sys.stderr)
        return 1
    print("[commit] dry-run ok — committing")
    res = v.rotate_overseer(overseer, challenge_bytes, evidence,
                            reason="stage1_custody_commit", dry_run=False)
    print(json.dumps(res, indent=2, default=str))
    return 0 if res.get("status") == "committed" else 1


# ─────────────────────────────────────────────────────────────────────────
# transfer-agents
# ─────────────────────────────────────────────────────────────────────────

def cmd_transfer_agents(args: argparse.Namespace) -> int:
    """
    Bulk ERC-8004 NFT transfer.

    For each agent in daio/agents/agent_map.json that has a known tokenId
    on the target chain, retrieve that agent's operator privkey from the
    vault (under the CURRENT overseer — HumanOverseer if handoff already
    committed) and call the agentID TS `transferAgentOwnership`.

    NOTE: tokenId is not currently stored in agent_map.json (only the agent
    wallet's eth_address).  For the first pass, this command FAILS LOUDLY
    when tokenId cannot be resolved — operator must supply --token-ids
    as a comma-separated list of `agent_id=tokenId` pairs.
    """
    to = _normalize_addr(args.to)
    chain = args.chain
    rpc_url = args.rpc_url or os.environ.get(
        {"base-sepolia": "BASE_SEPOLIA_RPC", "base": "BASE_RPC"}.get(chain, ""),
        "",
    )
    if not rpc_url:
        print(f"ERROR: --rpc-url or env BASE_SEPOLIA_RPC / BASE_RPC required", file=sys.stderr)
        return 2

    # Parse --token-ids if provided
    token_map: Dict[str, int] = {}
    if args.token_ids:
        for pair in args.token_ids.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                try:
                    token_map[k.strip()] = int(v.strip())
                except ValueError:
                    print(f"WARN: bad token-id pair {pair!r} — skipping", file=sys.stderr)

    if not AGENT_MAP_PATH.exists():
        print(f"ERROR: {AGENT_MAP_PATH} missing", file=sys.stderr)
        return 2
    agent_map = json.loads(AGENT_MAP_PATH.read_text())

    # Find the agentID TS entry point — we invoke via node subprocess to keep
    # this Python-side script simple.  The TS exports a CLI binary at
    # packages/identity/dist ; if that's not present, bail cleanly.
    node_script = Path(
        "/home/hacker/agentID/packages/identity/dist/erc8004-transfer.js"
    )
    if not node_script.exists():
        print(f"ERROR: {node_script} missing — build @agentid/identity first", file=sys.stderr)
        return 2

    if not token_map:
        print(
            "NOTE: no tokenIds supplied via --token-ids; this command cannot fabricate them.\n"
            "      Retrieve tokenIds via `discovery-api` or Blockscout, then pass as\n"
            "      --token-ids 'guardian_agent_main=0,coordinator_agent_main=1,...'.",
            file=sys.stderr,
        )
        return 1

    v, vault_dir = _load_vault(require_unlocked=True)
    agents = agent_map.get("agents", {})
    history = []

    for agent_id, token_id in token_map.items():
        entry = agents.get(agent_id)
        if not entry:
            print(f"[transfer] skip {agent_id}: not in agent_map.json")
            continue
        vault_ref = f"agent_pk_{agent_id}"
        try:
            priv_hex = v.retrieve(vault_ref)
        except Exception as e:
            print(f"[transfer] {agent_id}: vault retrieve failed: {e}")
            continue
        if not priv_hex:
            print(f"[transfer] {agent_id}: no key at {vault_ref}")
            continue

        # Spawn node to run the TS transfer — minimal glue.
        env = os.environ.copy()
        env.update({
            "AGENT_FROM_PK": priv_hex,
            "CHAIN": chain,
            "RPC_URL": rpc_url,
            "TO_ADDRESS": to,
            "TOKEN_ID": str(token_id),
        })
        inline_js = """
const { transferAgentOwnership } = require("/home/hacker/agentID/packages/identity/dist/erc8004-transfer.js");
const { privateKeyToAccount } = require("viem/accounts");
const { baseSepolia, base } = require("viem/chains");
(async () => {
  try {
    const chain = process.env.CHAIN === 'base' ? base : baseSepolia;
    const from = privateKeyToAccount(
      process.env.AGENT_FROM_PK.startsWith('0x')
        ? process.env.AGENT_FROM_PK
        : ('0x' + process.env.AGENT_FROM_PK)
    );
    const r = await transferAgentOwnership({
      chain, rpcUrl: process.env.RPC_URL,
      fromAccount: from, to: process.env.TO_ADDRESS,
      tokenId: BigInt(process.env.TOKEN_ID),
    });
    console.log(JSON.stringify({
      tokenId: r.tokenId.toString(), txHash: r.txHash,
      blockNumber: r.blockNumber.toString(), to: r.to,
    }));
  } catch (e) {
    console.error('FAIL', e && e.message ? e.message : String(e));
    process.exit(1);
  }
})();
"""
        node_cwd = "/home/hacker/agentID/packages/identity"
        try:
            proc = subprocess.run(
                ["node", "-e", inline_js],
                env=env, cwd=node_cwd, capture_output=True, text=True, timeout=120,
            )
            if proc.returncode != 0:
                print(f"[transfer] {agent_id} (tokenId={token_id}): FAIL {proc.stderr.strip()}")
                continue
            result = json.loads(proc.stdout.strip().split("\n")[-1])
            print(f"[transfer] {agent_id} tokenId={token_id} → {to} tx={result['txHash']}")
            history.append({
                "timestamp": time.time(),
                "event": "nft_transfer",
                "agent_id": agent_id,
                "token_id": token_id,
                "chain": chain,
                "from": entry.get("eth_address"),
                "to": to,
                "tx_hash": result["txHash"],
            })
        except subprocess.TimeoutExpired:
            print(f"[transfer] {agent_id} tokenId={token_id}: TIMEOUT")
        except Exception as e:
            print(f"[transfer] {agent_id} tokenId={token_id}: EXCEPTION {e}")

    if history:
        OVERSEER_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with OVERSEER_HISTORY.open("a", encoding="utf-8") as f:
            for rec in history:
                f.write(json.dumps(rec) + "\n")
        print(f"[transfer] logged {len(history)} transfers to {OVERSEER_HISTORY}")
    return 0 if history else 1


# ─────────────────────────────────────────────────────────────────────────
# update-agent-map
# ─────────────────────────────────────────────────────────────────────────

def cmd_update_agent_map(args: argparse.Namespace) -> int:
    to = _normalize_addr(args.to)
    if not AGENT_MAP_PATH.exists():
        print(f"ERROR: {AGENT_MAP_PATH} missing", file=sys.stderr)
        return 2
    data = json.loads(AGENT_MAP_PATH.read_text())
    changed = 0
    for agent_id, entry in (data.get("agents") or {}).items():
        if entry.get("human_overseer") != to:
            entry["human_overseer"] = to
            # Bump tier 1 → 2 only (leave higher tiers alone).
            if entry.get("verification_tier") == 1:
                entry["verification_tier"] = 2
            changed += 1
    backup = AGENT_MAP_PATH.with_suffix(".json.bak")
    backup.write_text(AGENT_MAP_PATH.read_text())
    AGENT_MAP_PATH.write_text(json.dumps(data, indent=2))
    print(f"[agent-map] updated {changed} agents with human_overseer={to}")
    print(f"[agent-map] backup: {backup}")

    # Mirror a `custodian` field in production_registry.json
    if PRODUCTION_REGISTRY.exists():
        reg = json.loads(PRODUCTION_REGISTRY.read_text())
        reg["custodian"] = to
        PRODUCTION_REGISTRY.write_text(json.dumps(reg, indent=2))
        print(f"[agent-map] production_registry.custodian = {to}")
    return 0


# ─────────────────────────────────────────────────────────────────────────
# lock-routes
# ─────────────────────────────────────────────────────────────────────────

def cmd_lock_routes(args: argparse.Namespace) -> int:
    """
    Write security.admin_addresses=[0xYOUR] into whichever config the live
    service reads.  mindX's Config loader looks at mindx_config.json +
    production.json; safest is to write to mindx_config.json under
    security.admin_addresses (comma-separated string, per security_middleware).
    """
    addr = _normalize_addr(args.address)
    config_paths = [
        PROJECT_ROOT / "mindx_config.json",
        PROJECT_ROOT / "config" / "mindx_config.json",
        PROJECT_ROOT / "config" / "production.json",
    ]
    target = None
    for p in config_paths:
        if p.exists():
            target = p
            break
    if target is None:
        print("ERROR: no mindx_config.json / production.json found", file=sys.stderr)
        return 2

    try:
        cfg = json.loads(target.read_text())
    except Exception as e:
        print(f"ERROR: reading {target}: {e}", file=sys.stderr)
        return 2

    # security.admin_addresses is read via config.get("security.admin_addresses", "")
    # and split on "," — so we store a comma-separated string for consistency
    # with the existing accessor shape.
    cfg.setdefault("security", {})
    existing = cfg["security"].get("admin_addresses", "")
    existing_list = [a.strip() for a in existing.split(",") if a.strip()]
    if addr not in existing_list:
        existing_list.insert(0, addr)
    cfg["security"]["admin_addresses"] = ",".join(existing_list)

    backup = target.with_suffix(target.suffix + ".bak")
    backup.write_text(target.read_text())
    target.write_text(json.dumps(cfg, indent=2))
    print(f"[lock-routes] {target}: security.admin_addresses → {cfg['security']['admin_addresses']}")
    print(f"[lock-routes] backup: {backup}")
    print("[lock-routes] restart the mindx service for this to take effect")
    return 0


# ─────────────────────────────────────────────────────────────────────────
# smoke-test
# ─────────────────────────────────────────────────────────────────────────

def cmd_smoke_test(args: argparse.Namespace) -> int:
    import urllib.request

    base = args.base_url
    checks = []

    # 1. anonymous /list must 401/403
    try:
        req = urllib.request.Request(base + "/vault/credentials/list")
        with urllib.request.urlopen(req, timeout=5) as r:
            code = r.status
            checks.append(("anon_list", code, code in (401, 403)))
    except urllib.error.HTTPError as e:
        checks.append(("anon_list", e.code, e.code in (401, 403)))
    except Exception as e:
        checks.append(("anon_list", "exception", False))

    # 2. sentinel file present (vault under human overseer)
    vault_dir = _locate_vault_dir()
    sentinel = vault_dir / ".human_overseer_active"
    checks.append(("sentinel_present", sentinel.exists(), sentinel.exists()))
    checks.append(("master_key_absent", not (vault_dir / ".master.key").exists(),
                   not (vault_dir / ".master.key").exists()))

    # 3. overseer_history.jsonl has ≥1 row
    has_history = OVERSEER_HISTORY.exists() and OVERSEER_HISTORY.stat().st_size > 0
    checks.append(("overseer_history_exists", has_history, has_history))

    print("smoke-test:")
    all_pass = True
    for name, value, ok in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{mark}] {name}: {value}")
    return 0 if all_pass else 1


# ─────────────────────────────────────────────────────────────────────────
# argparse wiring
# ─────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("preflight")
    sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser("challenge")
    sp.add_argument("--address", required=True)
    sp.add_argument("--out", help="write challenge to this file (default: ./handoff_challenge.txt)")
    sp.set_defaults(func=cmd_challenge)

    sp = sub.add_parser("dry-run")
    sp.add_argument("--address", required=True)
    sp.add_argument("--signature", required=True)
    sp.add_argument("--challenge", help="path to challenge file (default: ./handoff_challenge.txt)")
    sp.set_defaults(func=cmd_dry_run)

    sp = sub.add_parser("commit")
    sp.add_argument("--address", required=True)
    sp.add_argument("--signature", required=True)
    sp.add_argument("--challenge", help="path to challenge file (default: ./handoff_challenge.txt)")
    sp.add_argument("--i-am-sure", action="store_true",
                    help="required — explicit opt-in for destructive commit")
    sp.set_defaults(func=cmd_commit)

    sp = sub.add_parser("transfer-agents")
    sp.add_argument("--chain", choices=["base-sepolia", "base"], default="base-sepolia")
    sp.add_argument("--to", required=True, help="destination (human overseer) address")
    sp.add_argument("--rpc-url", help="override env BASE_SEPOLIA_RPC / BASE_RPC")
    sp.add_argument("--token-ids",
                    help='comma-separated "agent_id=tokenId" pairs '
                         '(tokenIds are not currently stored in agent_map.json)')
    sp.set_defaults(func=cmd_transfer_agents)

    sp = sub.add_parser("update-agent-map")
    sp.add_argument("--to", required=True)
    sp.set_defaults(func=cmd_update_agent_map)

    sp = sub.add_parser("lock-routes")
    sp.add_argument("--address", required=True,
                    help="address added to security.admin_addresses")
    sp.set_defaults(func=cmd_lock_routes)

    sp = sub.add_parser("smoke-test")
    sp.add_argument("--base-url", default="http://127.0.0.1:8000")
    sp.set_defaults(func=cmd_smoke_test)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
