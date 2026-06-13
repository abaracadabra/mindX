#!/usr/bin/env python3
"""algorand_deploy.py — the Algorand deployment tool (separate · non-EVM).

The AVM sibling of ../deployer.js. Same DEPLOY -> LAUNCH -> RETURN shape, Algorand's
own rails: ARC-56 appspecs (not Foundry artifacts), algosdk (not window.ethereum),
app id + app address (not a contract address).

  DEPLOY  arm: read the ARC-56 appspec, compile TEAL via algod, build the
              ApplicationCreateTxn (no broadcast).
  LAUNCH  fire from value: sign (non-custodial, your mnemonic) grouped atomically
              with the deployment fee payment to mindX/AgenticPlace, then send.
  RETURN  the application id + app address + txid the chain returns.

Non-custodial: the signing key is your mnemonic (env BANKON_ALGO_MNEMONIC or the
client-side ../walletcreator bankon-vault). Airgap-first for MainNet. The only
dependency is algosdk (`pip install py-algorand-sdk`).

Always open source. (c) BANKON all rights preserved.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent


def _require_algosdk():
    try:
        import algosdk  # noqa: F401
        return True
    except ImportError:
        sys.stderr.write("algosdk not installed — `pip install py-algorand-sdk`\n")
        return False


# ── manifest model ──────────────────────────────────────────────────────────
@dataclass
class Network:
    id: str
    algod: str
    token: str
    note: str = ""


@dataclass
class App:
    id: str
    name: str
    summary: str
    appspec: str
    privilege: Optional[str] = None


@dataclass
class Fee:
    recipient: str
    microalgos: int
    service: str


@dataclass
class Solution:
    networks: dict[str, Network]
    default_network: str
    fee: Optional[Fee]
    apps: list[App]


def load_solution(path: Path | str = HERE / "algorand.xml") -> Solution:
    root = ET.parse(path).getroot()
    nets = {}
    for n in root.findall("./networks/network"):
        nets[n.get("id")] = Network(n.get("id"), n.get("algod"), n.get("token", ""), n.get("note", ""))
    f = root.find("fee")
    fee = Fee(f.get("recipient", ""), int(f.get("microalgos", "0") or 0), f.get("service", "deploy.app")) if f is not None else None
    apps = []
    for a in root.findall("app"):
        priv = a.find("privilege")
        apps.append(App(
            id=a.get("id"), name=a.get("name"), summary=a.get("summary", ""),
            appspec=a.find("appspec").get("src") if a.find("appspec") is not None else "",
            privilege=priv.get("service") if priv is not None else None,
        ))
    return Solution(nets, root.get("default-network", "localnet"), fee, apps)


# ── ARC-56 appspec -> compiled programs ─────────────────────────────────────
def _b64(s: str) -> bytes:
    return base64.b64decode(s)


def compile_programs(algod, appspec_path: Path):
    """Return (approval, clear) compiled bytecode from an ARC-56 appspec.

    ARC-56 carries TEAL source under `source.approval`/`source.clear` (base64); we
    compile via algod. If a compiled `byteCode` block is present we use it directly.
    """
    spec = json.loads(Path(appspec_path).read_text())
    src = spec.get("source", {})
    bc = spec.get("byteCode", {})
    if bc.get("approval") and bc.get("clear"):
        return _b64(bc["approval"]), _b64(bc["clear"])
    if not src.get("approval") or not src.get("clear"):
        raise ValueError("appspec has no source.{approval,clear} TEAL to compile")
    approval_teal = base64.b64decode(src["approval"]).decode()
    clear_teal = base64.b64decode(src["clear"]).decode()
    approval = _b64(algod.compile(approval_teal)["result"])
    clear = _b64(algod.compile(clear_teal)["result"])
    return approval, clear


def _state_schema(appspec_path: Path):
    from algosdk.transaction import StateSchema
    spec = json.loads(Path(appspec_path).read_text())
    st = spec.get("state", {}).get("schema", {})
    g = st.get("global", {})
    l = st.get("local", {})
    glob = StateSchema(int(g.get("ints", 0)), int(g.get("bytes", 0)))
    loc = StateSchema(int(l.get("ints", 0)), int(l.get("bytes", 0)))
    return glob, loc


# ── signer (non-custodial) ──────────────────────────────────────────────────
def load_signer():
    from algosdk import account, mnemonic
    mn = os.environ.get("BANKON_ALGO_MNEMONIC", "").strip()
    if not mn:
        raise SystemExit("set BANKON_ALGO_MNEMONIC (or load from the bankon-vault) — non-custodial signing")
    sk = mnemonic.to_private_key(mn)
    return sk, account.address_from_private_key(sk)


# ── DEPLOY -> LAUNCH -> RETURN ──────────────────────────────────────────────
def deploy(app_id: str, network: str | None = None, manifest: Path | str = HERE / "algorand.xml"):
    if not _require_algosdk():
        return None
    from algosdk.v2client import algod as algodmod
    from algosdk import transaction

    sol = load_solution(manifest)
    net = sol.networks[network or sol.default_network]
    app = next((a for a in sol.apps if a.id == app_id), None)
    if not app:
        raise SystemExit(f"no app '{app_id}' in manifest (try: list)")

    spec_path = (HERE / app.appspec) if not os.path.isabs(app.appspec) else Path(app.appspec)
    if not spec_path.exists():
        raise SystemExit(f"no appspec at {spec_path} — build it (AlgoKit), then retry")

    sk, sender = load_signer()
    algod = algodmod.AlgodClient(net.token, net.algod, headers={"User-Agent": "bankon-deployer"})

    # DEPLOY (arm): compile + build the create txn.
    print(f"DEPLOY · {app.name} → {net.id} · sender {sender}")
    approval, clear = compile_programs(algod, spec_path)
    glob, loc = _state_schema(spec_path)
    params = algod.suggested_params()
    create = transaction.ApplicationCreateTxn(
        sender=sender, sp=params, on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval, clear_program=clear,
        global_schema=glob, local_schema=loc,
    )

    # LAUNCH (fire from value): group the deploy fee payment atomically with the create.
    txns = [create]
    if sol.fee and sol.fee.recipient and sol.fee.microalgos > 0:
        fee_pay = transaction.PaymentTxn(sender, params, sol.fee.recipient, sol.fee.microalgos)
        txns = [create, fee_pay]
        gid = transaction.calculate_group_id(txns)
        for t in txns:
            t.group = gid
        print(f"LAUNCH · fee {sol.fee.microalgos} µAlgo → AgenticPlace ({sol.fee.service}), grouped with create")
    signed = [t.sign(sk) for t in txns]
    txid = algod.send_transactions(signed)
    print(f"LAUNCH · sent group, txid {txid}")

    # RETURN: app id + app address.
    res = transaction.wait_for_confirmation(algod, txid, 8)
    app_index = res.get("application-index")
    from algosdk.logic import get_application_address
    addr = get_application_address(app_index) if app_index else "?"
    print(f"RETURN · {app.name} · app id {app_index} · app addr {addr} · round {res.get('confirmed-round')}")
    return {"app_id": app_index, "app_address": addr, "txid": txid, "network": net.id}


def cmd_list(manifest: Path | str = HERE / "algorand.xml"):
    sol = load_solution(manifest)
    print(f"bankon-algorand · default network {sol.default_network}")
    print(f"networks: {', '.join(sol.networks)}")
    if sol.fee:
        print(f"deploy fee: {sol.fee.microalgos} µAlgo → {sol.fee.recipient or '(unset)'} ({sol.fee.service})")
    for a in sol.apps:
        print(f"  • {a.id:18} {a.name:16} {('→ ' + a.privilege) if a.privilege else '':22} {a.summary}")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        print("commands:\n  list\n  deploy <app-id> [--network localnet|testnet|mainnet]")
        return 0
    cmd = argv[0]
    if cmd == "list":
        cmd_list()
        return 0
    if cmd == "deploy":
        if len(argv) < 2:
            sys.stderr.write("deploy needs an app id (try: list)\n")
            return 2
        net = None
        if "--network" in argv:
            net = argv[argv.index("--network") + 1]
        deploy(argv[1], network=net)
        return 0
    sys.stderr.write(f"unknown command '{cmd}'\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
