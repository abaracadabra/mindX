#!/usr/bin/env python3
"""Provision the `wordpress.agent` vault namespace.

Idempotent: safe to re-run. It will

  1. Mint a fresh Ethereum wallet IF `wordpress.agent:pk` is not already in the
     vault, and store the private key + checksum address under
     `context="wordpress.agent.keys"` (HKDF-isolated from every other credential).
  2. Mirror the address into `data/identity/production_registry.json` under
     `agents["wordpress.agent"]`.
  3. Store `wordpress.agent:{wp_base_url,wp_user,wp_app_password}` under the same
     context. The WP Application Password is read via `getpass` so it never
     appears in argv or shell history.
  4. Optionally seed the `wordpress_publisher_addresses` allowlist (env-mapped;
     comma-separated 0x EOAs permitted to authorize a publish).

The runtime path (wordpress-agent service) reads these on demand via
`agents.wordpress_agent.vault_creds`; **no `WP_*` env vars are set in production**.

Usage:
  python scripts/vault/provision_wordpress_agent.py \\
      --wp-base-url https://rage.pythai.net \\
      --wp-user codephreak \\
      [--wp-app-password 'xxxx xxxx xxxx xxxx xxxx xxxx']  # otherwise prompts
      [--publisher-addresses 0xAaa...,0xBbb...]            # optional allowlist
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Repo root on path so the imports work whether invoked from scripts/ or repo root.
_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_ROOT))

from mindx_backend_service.bankon_vault.vault import BankonVault  # noqa: E402
from agents.wordpress_agent.vault_creds import (  # noqa: E402
    ENTRY_ADDRESS,
    ENTRY_PK,
    ENTRY_WP_APP_PASSWORD,
    ENTRY_WP_BASE_URL,
    ENTRY_WP_USER,
    VAULT_CONTEXT,
)

REGISTRY_PATH = _ROOT / "data" / "identity" / "production_registry.json"


def _mint_wallet() -> tuple[str, str]:
    from eth_account import Account
    from web3 import Web3
    acct = Account.create()
    return acct.key.hex(), Web3.to_checksum_address(acct.address)


def _registry_write_address(address: str) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if REGISTRY_PATH.exists():
        try:
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    agents = data.setdefault("agents", {})
    block = agents.get("wordpress.agent", {})
    block["address"] = address
    block.setdefault("created_at", time.time())
    block["updated_at"] = time.time()
    agents["wordpress.agent"] = block
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, REGISTRY_PATH)


def _require_https(url: str) -> str:
    if not url.startswith("https://") and not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
        raise SystemExit(f"refusing non-https wp_base_url: {url!r}")
    return url.rstrip("/")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wp-base-url", required=True, help="WordPress site base URL (must be https://)")
    p.add_argument("--wp-user", required=True, help="WordPress username")
    p.add_argument("--wp-app-password", default=None,
                   help="WordPress Application Password (prompted via getpass if omitted)")
    p.add_argument("--publisher-addresses", default=None,
                   help="Comma-separated 0x EOAs allowed to authorize a publish (allowlist)")
    p.add_argument("--no-mint", action="store_true",
                   help="Do not mint a wallet; assume wordpress.agent:pk already in vault")
    args = p.parse_args(argv)

    base_url = _require_https(args.wp_base_url)

    app_password = args.wp_app_password
    if not app_password:
        app_password = getpass.getpass("WordPress Application Password (input hidden): ").strip()
        if not app_password:
            raise SystemExit("empty WordPress Application Password — aborting")

    vault = BankonVault()
    vault.unlock_with_key_file()
    try:
        # Mint or re-use the wordpress.agent wallet.
        existing_pk = vault.retrieve(ENTRY_PK)
        existing_addr = vault.retrieve(ENTRY_ADDRESS)
        if existing_pk and not args.no_mint:
            print(f"wordpress.agent wallet already provisioned (address={existing_addr or '?'}) — keeping it")
        elif args.no_mint:
            if not existing_pk:
                raise SystemExit("--no-mint set but wordpress.agent:pk is missing")
            print(f"--no-mint: keeping existing wallet (address={existing_addr or '?'})")
        else:
            pk_hex, addr = _mint_wallet()
            vault.store(ENTRY_PK, pk_hex, context=VAULT_CONTEXT)
            vault.store(ENTRY_ADDRESS, addr, context=VAULT_CONTEXT)
            _registry_write_address(addr)
            existing_addr = addr
            print(f"minted wordpress.agent wallet: address={addr}")

        # WP REST credentials.
        vault.store(ENTRY_WP_BASE_URL, base_url, context=VAULT_CONTEXT)
        vault.store(ENTRY_WP_USER, args.wp_user, context=VAULT_CONTEXT)
        vault.store(ENTRY_WP_APP_PASSWORD, app_password, context=VAULT_CONTEXT)
        print(f"stored wp_base_url / wp_user / wp_app_password under context={VAULT_CONTEXT!r}")

        # Optional allowlist (this one IS env-mapped — see PROVIDER_ENV_MAP).
        if args.publisher_addresses:
            normalized = ",".join(a.strip() for a in args.publisher_addresses.split(",") if a.strip())
            vault.store("wordpress_publisher_addresses", normalized, context="provider")
            print(f"stored wordpress_publisher_addresses → WORDPRESS_PUBLISHER_ADDRESSES ({len(normalized.split(','))} entries)")

        # Mirror address into the production registry even if we re-used the wallet.
        if existing_addr:
            _registry_write_address(existing_addr)

    finally:
        vault.lock()

    print("done. WP API key is now encrypted at rest; wordpress-agent will decrypt on demand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
