#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""deploy_bonafide_sequence — automate the full BONA FIDE protocol deploy, one
contract at a time, recording feedback (tx / app id / ASA id) for EACH contract.

The BONA FIDE proof-of-work is the Algorand A-suite, in strict order:
  A1  AsaSuite          — modular ASA toolkit
  A2  BonaFideDeployer  — mints the canonical BONA FIDE ASA (1e12, decimals 0)
  A3  BonafideController — optInAsset → clawback/reserve → initialize → apply/revoke/ghost
  A4  X402Receipt (AVM) — HTTP-402 settlement attestation

Completing A1–A4 (BONA FIDE proof-of-work) unlocks the EVM suite.

**Signing boundary (unchanged):** an agent NEVER signs a real-chain tx. This
orchestrator runs the sequence and records feedback; the SIGNING is delegated —
either to `algokit` using the OVERSEER's configured/funded account (`--signer
algokit`), or to the OVERSEER out-of-band who pastes each tx/app id (`--signer
manual`, the default and only safe mode for mainnet). localnet/testnet may use
algokit end-to-end.

Modes:
  --mode sequence   run A1→A4 in order (default)
  --mode one        run only the next un-deployed step, then stop (one-at-a-time)
  --net             localnet | testnet | mainnet   (default: testnet)
  --signer          manual | algokit                (default: manual)

Each confirmed step is POSTed to the live realm as deploy feedback:
  POST {base}/realm/deploy/feedback   (sovereign-gated; needs OVERSEER_TOKEN)
so it appears in the OVERLORD/OVERSEER handoff + mindX improvement awareness. After
A2, the minted BONA FIDE ASA id is captured and (optionally) activated via
scripts/activate_bonafide.sh.

Env:
  MINDX_BASE        realm base URL (default https://mindx.pythai.net)
  OVERSEER_TOKEN    OVERSEER JWT (from /auth/algorand/verify) — required to record feedback
  DELTAVERSE_DIR    DeltaVerse contracts dir (default ~/DeltaVerse/contracts)
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import subprocess
import urllib.request

SEQUENCE = [
    {"stage": "A1", "contract": "AsaSuite",
     "note": "modular ASA toolkit", "mints_asa": False},
    {"stage": "A2", "contract": "BonaFideDeployer",
     "note": "mint canonical BONA FIDE ASA (total 1_000_000_000_000, decimals 0) via mintBonafideAsa(controller)",
     "mints_asa": True},
    {"stage": "A3", "contract": "BonafideController",
     "note": "optInAsset → receive clawback/reserve → initialize → apply/revoke/ghost", "mints_asa": False},
    {"stage": "A4", "contract": "X402Receipt",
     "note": "AVM HTTP-402 settlement attestation", "mints_asa": False},
]


def _base() -> str:
    return (os.environ.get("MINDX_BASE") or "https://mindx.pythai.net").rstrip("/")


def record_feedback(step: dict, *, chain: str, tx_hash: str, app_id: str, asa_id, status: str) -> bool:
    """POST one contract's confirmed deploy to the realm feedback ledger."""
    tok = os.environ.get("OVERSEER_TOKEN", "").strip()
    if not tok:
        print("  ! OVERSEER_TOKEN not set — skipping feedback record (deploy still counts).")
        return False
    body = json.dumps({
        "step": step["stage"], "contract": step["contract"], "chain": chain,
        "tx_hash": tx_hash, "address": app_id, "asa_id": (int(asa_id) if asa_id else None),
        "status": status, "note": step["note"],
    }).encode()
    req = urllib.request.Request(f"{_base()}/realm/deploy/feedback", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {tok}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = r.status < 400
            print(f"  ✓ feedback recorded ({r.status})" if ok else f"  ! feedback {r.status}")
            return ok
    except Exception as e:
        print(f"  ! feedback post failed: {e}")
        return False


def deploy_step(step: dict, *, net: str, signer: str) -> dict:
    """Deploy one contract. Returns {tx_hash, app_id, asa_id, status}. Signing is
    delegated: 'manual' prompts the OVERSEER to sign out-of-band and paste results
    (the only mainnet-safe mode); 'algokit' invokes algokit (localnet/testnet)."""
    print(f"\n=== {step['stage']} · {step['contract']} ({net}) ===\n  {step['note']}")
    if signer == "algokit" and net != "mainnet":
        dv = os.environ.get("DELTAVERSE_DIR", os.path.expanduser("~/DeltaVerse/contracts"))
        print(f"  → algokit deploy in {dv} (net={net})  [operator's configured account signs]")
        try:
            out = subprocess.run(["algokit", "project", "deploy", net], cwd=dv,
                                 capture_output=True, text=True, timeout=600)
            print(out.stdout[-800:] or "", out.stderr[-400:] or "")
        except Exception as e:
            print(f"  ! algokit invocation failed: {e} — falling back to manual entry")
    # Manual/confirm: the OVERSEER signs (Pera/algokit) and reports the result.
    print("  Sign this deploy with the OVERSEER wallet, then enter its result "
          "(blank tx = skip/abort this step):")
    tx = input("    tx id: ").strip()
    if not tx:
        return {"status": "aborted", "tx_hash": "", "app_id": "", "asa_id": None}
    app_id = input("    app id: ").strip()
    asa_id = input("    BONA FIDE ASA id (A2 only, else blank): ").strip() if step["mints_asa"] else ""
    return {"status": "confirmed", "tx_hash": tx, "app_id": app_id, "asa_id": (asa_id or None)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sequence", "one"], default="sequence")
    ap.add_argument("--net", choices=["localnet", "testnet", "mainnet"], default="testnet")
    ap.add_argument("--signer", choices=["manual", "algokit"], default="manual")
    a = ap.parse_args()
    if a.net == "mainnet" and a.signer == "algokit":
        print("refusing --signer algokit on mainnet: mainnet is OVERSEER-signed, out of band. Use --signer manual.")
        return 2
    print(f"BONA FIDE protocol deploy · mode={a.mode} net={a.net} signer={a.signer} base={_base()}")
    minted_asa = None
    for step in SEQUENCE:
        res = deploy_step(step, net=a.net, signer=a.signer)
        if res["status"] != "confirmed":
            print(f"  step {step['stage']} not confirmed ({res['status']}) — stopping."); break
        record_feedback(step, chain="algorand", tx_hash=res["tx_hash"],
                        app_id=res["app_id"], asa_id=res["asa_id"], status="confirmed")
        if step["mints_asa"] and res["asa_id"]:
            minted_asa = res["asa_id"]
            print(f"  ★ BONA FIDE ASA minted: {minted_asa}")
        if a.mode == "one":
            print("  one-at-a-time: stopping after this step."); break
    if minted_asa:
        print(f"\nActivate the .algo member gate:\n  ./scripts/activate_bonafide.sh {minted_asa} {a.net if a.net!='localnet' else 'testnet'}")
    print("\nBONA FIDE sequence run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
