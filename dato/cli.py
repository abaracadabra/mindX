# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato CLI — agentic commerce from the command line.

A headless driver over dato/core so an autonomous agent can transact: spawn a
DAIO-owned dato, request-to-join paying an **x402** fee, commit data at a
permanence tier (immortal = real Arweave upload, the ~200-yr purchase), register
tiered names, and read state — all scriptable with ``--json``.

Agentic commerce:
  * ``dato join`` settles the dato's join fee over x402 — it mints a signed
    EIP-3009 payment authorization via tools/x402_rails (the agent's wallet),
    records the receipt, and is admitted. ``--simulate`` records a simulated
    receipt when no signing key is present.
  * ``dato commit --tier immortal`` performs a real ANS-104 Arweave upload via
    tools/arweave_turbo (permanence purchase) when an Arweave JWK is configured.

Examples:
  python -m dato.cli spawn guild --tier immortal --join-fee 10000
  python -m dato.cli ls --json
  python -m dato.cli join dato_xxx --wallet 0xAgent --pay --rail base
  python -m dato.cli commit dato_xxx report --tier immutable --data "hello"
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dato.core import membership, naming
from dato.core.dato_process import DatoError, DatoRegistry
from dato.core.model import PermanenceTier, Settings


# ── x402 fee settlement (agentic commerce) ───────────────────────────────────
def settle_x402_fee(
    fee_microusd: int, *, rail: str = "base", pay_to: Optional[str] = None, simulate: bool = False
) -> Dict[str, Any]:
    """Settle a dato fee over x402; returns {receipt, amount, header?}.

    Mints a real EIP-3009 payment authorization via the x402 rails service
    (signed by the agent's wallet). With ``simulate`` or no signing key, returns
    a simulated receipt so the flow is exercised.
    """
    if simulate:
        return {"receipt": "x402-sim-" + secrets.token_hex(8), "amount": fee_microusd, "simulated": True}
    try:
        from mindx_backend_service import x402_protocol as xp
        from tools.x402_rails import X402RailsService, X402RailsError

        # Resolve the rail's network/asset from pricing config.
        cfg = json.loads((Path(__file__).resolve().parents[1] / "data/config/x402_pricing.json").read_text())
        rcfg = (cfg.get("rails", {}) or {}).get(rail, {})
        network = xp.to_caip2(rcfg.get("network", rail))
        asset = rcfg.get("asset", "")
        recipient = pay_to or rcfg.get("payTo") or "0x0000000000000000000000000000000000000000"
        svc = X402RailsService(max_amount_usdc=max(0.05, fee_microusd / 1_000_000 + 0.001))
        challenge = {"accepts": [{
            "scheme": "exact", "network": network, "asset": asset,
            "payTo": recipient, "maxAmountRequired": str(fee_microusd),
        }]}
        cred = svc.issue_from_challenge(challenge)
        return {"receipt": cred.nonce, "amount": cred.amount_minor, "header": cred.header_value, "network": network, "payTo": recipient}
    except Exception as e:  # no key / signer unavailable → guide the agent
        raise DatoError(
            f"x402 settlement failed ({e}). Set a signing key (BASE_X402_PRIVATE_KEY / vault "
            f"base_x402_private_key) or pass --simulate."
        )


# ── command handlers ─────────────────────────────────────────────────────────
def cmd_spawn(reg: DatoRegistry, a) -> Dict[str, Any]:
    settings = Settings(
        default_tier=PermanenceTier.coerce(a.tier),
        join_fee_microusd=int(a.join_fee), open_join=not a.closed_join,
        max_members=a.max_members,
    )
    inst = reg.spawn(a.handle, tier=a.tier, root=a.root, deployer_wallet=a.wallet,
                     owner_daio=a.owner, entity_id=a.entity_id, settings=settings)
    return {"dato_id": inst.dato_id, "name": inst.name, "owner_daio": inst.owner_daio,
            "deployer": inst.deployer_wallet, "join_fee_microusd": inst.settings.join_fee_microusd,
            "open_join": inst.settings.open_join}


def cmd_ls(reg: DatoRegistry, a) -> Any:
    if a.names:
        return [{"name": rec.name, "tier": rec.tier.value, "dato": d.dato_id, "controller": d.deployer_wallet}
                for d in reg.list() for rec in d.records.values()]
    if a.records:
        out = []
        for d in reg.list():
            for r in d.records.values():
                out.append({"dato": d.dato_id, **r.to_dict()})
        return out
    return [{"dato_id": d.dato_id, "name": d.name, "tier": d.settings.default_tier.value,
             "members": len(d.members), "join_fee_microusd": d.settings.join_fee_microusd,
             "open_join": d.settings.open_join} for d in reg.list()]


def cmd_info(reg: DatoRegistry, a) -> Dict[str, Any]:
    inst = reg.get(a.dato_id)
    if not inst:
        raise DatoError(f"unknown dato {a.dato_id}")
    return inst.to_dict()


def cmd_quote(reg: DatoRegistry, a) -> Dict[str, Any]:
    return membership.quote_join(reg, a.dato_id)


def cmd_join(reg: DatoRegistry, a) -> Dict[str, Any]:
    quote = membership.quote_join(reg, a.dato_id)
    fee_tx, fee_paid = None, 0
    settlement = None
    if not quote["free"]:
        if not (a.pay or a.simulate):
            raise DatoError(f"dato requires a {quote['fee_microusd']} µUSD x402 fee — pass --pay (or --simulate)")
        settlement = settle_x402_fee(quote["fee_microusd"], rail=a.rail, pay_to=a.pay_to, simulate=a.simulate)
        fee_tx, fee_paid = settlement["receipt"], settlement["amount"]
    member = membership.join(reg, a.dato_id, a.wallet, settings=_parse_kv(a.settings),
                             fee_tx=fee_tx, fee_paid_microusd=fee_paid)
    return {"joined": member.wallet, "dato_id": a.dato_id, "fee_paid_microusd": member.fee_paid_microusd,
            "fee_tx": member.fee_tx, "x402": settlement}


def cmd_commit(reg: DatoRegistry, a) -> Dict[str, Any]:
    data = a.data.encode() if a.data is not None else Path(a.file).read_bytes()
    try:
        rec = reg.commit(a.dato_id, a.handle, data, tier=a.tier, root=a.root, content_type=a.content_type)
    except Exception as e:
        # immortal upload needs Arweave creds — surface clearly.
        raise DatoError(f"commit failed: {e}")
    return rec.to_dict()


def cmd_name(reg: DatoRegistry, a) -> Dict[str, Any]:
    root = a.root
    if root not in naming.roots():
        naming.add_root(root)  # roots are extensible (a-z0-9-)
    full = naming.format_name(a.handle, a.tier, root)
    # ar.io ARNS roots are a purchase — surface the directive (parity with the UI).
    if root in ("ar", "arns"):
        return {"name": full, "needs_purchase": True,
                "message": "ar.io ARNS registration is a purchase (HyperBEAM/ARIO). "
                           "Buy/assign the ARNS name, then bind it to the dato.",
                "arns": f"{a.handle}_{a.tier}"}
    reg.resolver.register(full, a.controller or "cli", None, a.dato_id or "")
    return {"name": full, "registered": True, "controller": a.controller or "cli"}


def _parse_kv(items) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for it in items or []:
        if "=" in it:
            k, v = it.split("=", 1)
            out[k] = v
    return out


# ── argparse wiring ───────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dato", description="dato — agentic commerce CLI")
    p.add_argument("--registry", default=os.environ.get("DATO_REGISTRY"), help="registry json path")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("spawn", help="spawn a DAIO-owned dato")
    sp.add_argument("handle")
    sp.add_argument("--tier", default="immortal", choices=[t.value for t in PermanenceTier])
    sp.add_argument("--root", default="blockchain")
    sp.add_argument("--join-fee", default=0, type=int, help="join fee in microUSD")
    sp.add_argument("--closed-join", action="store_true")
    sp.add_argument("--max-members", type=int, default=None)
    sp.add_argument("--owner", default=None, help="owning DAIO address/id")
    sp.add_argument("--wallet", default=None, help="deployer/participant wallet")
    sp.add_argument("--entity-id", default=None, help="mindX entity id → IDManagerAgent wallet")
    sp.set_defaults(fn=cmd_spawn)

    lp = sub.add_parser("ls", help="list datos / names / records")
    lp.add_argument("--names", action="store_true")
    lp.add_argument("--records", action="store_true")
    lp.set_defaults(fn=cmd_ls)

    ip = sub.add_parser("info", help="show a dato"); ip.add_argument("dato_id"); ip.set_defaults(fn=cmd_info)
    qp = sub.add_parser("quote", help="quote a join fee"); qp.add_argument("dato_id"); qp.set_defaults(fn=cmd_quote)

    jp = sub.add_parser("join", help="request-to-join (settles x402 fee)")
    jp.add_argument("dato_id"); jp.add_argument("--wallet", required=True)
    jp.add_argument("--pay", action="store_true", help="settle the join fee over x402")
    jp.add_argument("--simulate", action="store_true", help="simulate x402 settlement (no key)")
    jp.add_argument("--rail", default="base"); jp.add_argument("--pay-to", default=None)
    jp.add_argument("--settings", nargs="*", help="key=value per-member settings")
    jp.set_defaults(fn=cmd_join)

    cp = sub.add_parser("commit", help="commit data at a permanence tier")
    cp.add_argument("dato_id"); cp.add_argument("handle")
    cp.add_argument("--tier", default=None, choices=[t.value for t in PermanenceTier])
    cp.add_argument("--root", default="blockchain")
    g = cp.add_mutually_exclusive_group(required=True)
    g.add_argument("--data"); g.add_argument("--file")
    cp.add_argument("--content-type", default="application/octet-stream")
    cp.set_defaults(fn=cmd_commit)

    npx = sub.add_parser("name", help="register/compose a tiered name")
    npx.add_argument("handle"); npx.add_argument("--tier", default="immortal", choices=[t.value for t in PermanenceTier])
    npx.add_argument("--root", default="blockchain"); npx.add_argument("--controller", default=None)
    npx.add_argument("--dato-id", default=None)
    npx.set_defaults(fn=cmd_name)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    reg = DatoRegistry(path=Path(args.registry) if args.registry else None)
    try:
        result = args.fn(reg, args)
    except DatoError as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, default=str))
    else:
        print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
