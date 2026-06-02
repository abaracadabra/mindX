# SPDX-License-Identifier: Apache-2.0
"""Cross-check that wordpress.agent's vault wallet is on the WP plugin allowlist.

Prevents the silent-403 drift that broke publishing through May 2026:
    * vault holds wallet pk under wordpress.agent:pk
    * mindx-publish-auth plugin holds an allowlist of authorized EOAs
    * if the two diverge, EVERY publish 403s with no other warning

Run on each ``wordpress-agent.service`` start via ``ExecStartPre`` — non-zero
exit blocks the service from starting so the failure is visible in
``systemctl status``, not buried as a 403 the first time someone tries to
publish weeks later.

Exit codes
----------
    0  vault wallet is allowlisted; publishes will work.
    1  vault wallet is NOT allowlisted; publishes will 403. Remediation hint
       printed (add the wallet's derived address to the WP plugin allowlist,
       OR restore matching pk into vault).
    2  the plugin isn't reachable / plugin not installed / vault not unlockable.

Privacy invariants
------------------
This script NEVER prints a private key value. It prints:
    * the *derived address* of wordpress.agent:pk (public)
    * the plugin's reported allowlist_entries *count* (never the addresses)
    * the verify-endpoint status code (200 / 403 / etc.)
"""
from __future__ import annotations

import asyncio
import sys

import httpx


_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36 mindX-wordpress-agent-crosscheck/0.1"
)


async def _check(base_url: str, timeout_s: float = 10.0) -> int:
    """Run the diagnose + challenge + sign + verify round-trip. Return exit code."""
    # 1. Vault → derive the wordpress.agent's signing address.
    try:
        from agents.wordpress_agent.vault_creds import sign_with_agent_wallet
    except Exception as e:
        print(f"crosscheck: cannot import vault_creds: {e}", file=sys.stderr)
        return 2

    sig_result = sign_with_agent_wallet("crosscheck-probe")
    if sig_result is None:
        print(
            "crosscheck: wordpress.agent vault wallet not provisioned "
            "(wordpress.agent:pk missing or vault locked). "
            "Run scripts/vault/provision_wordpress_agent.py.",
            file=sys.stderr,
        )
        return 2
    _sig, vault_addr = sig_result
    print(f"crosscheck: vault wallet address = {vault_addr}")

    # 2. Probe the plugin.
    async with httpx.AsyncClient(
        headers={"User-Agent": _BROWSER_UA, "Accept": "application/json"},
        timeout=timeout_s,
    ) as client:
        try:
            r = await client.get(f"{base_url}/wp-json/mindx/v1/auth/diagnose")
        except Exception as e:
            print(f"crosscheck: cannot reach plugin /diagnose: {e}", file=sys.stderr)
            return 2
        if r.status_code != 200:
            print(
                f"crosscheck: plugin /diagnose returned HTTP {r.status_code}; "
                f"is mindx-publish-auth installed on {base_url}?",
                file=sys.stderr,
            )
            return 2
        try:
            diag = r.json()
        except Exception:
            print("crosscheck: /diagnose returned non-JSON", file=sys.stderr)
            return 2
        allowlist_count = int(diag.get("allowlist_entries", 0))
        print(
            f"crosscheck: plugin v{diag.get('plugin_version','?')} reachable; "
            f"allowlist_entries={allowlist_count}, "
            f"jwt_secret_present={diag.get('jwt_secret_present')}"
        )
        if allowlist_count <= 0:
            print(
                "crosscheck: plugin has ZERO allowlisted addresses — every publish will 403. "
                f"Add {vault_addr} to the plugin allowlist.",
                file=sys.stderr,
            )
            return 1

        # 3. Full challenge → sign → verify round-trip.
        try:
            ch = await client.get(f"{base_url}/wp-json/mindx/v1/auth/challenge")
            if ch.status_code != 200:
                print(
                    f"crosscheck: /challenge HTTP {ch.status_code}",
                    file=sys.stderr,
                )
                return 2
            challenge = ch.json()
        except Exception as e:
            print(f"crosscheck: challenge fetch failed: {e}", file=sys.stderr)
            return 2

        # Sign the plugin's challenge message with the vault wallet.
        signed = sign_with_agent_wallet(challenge["message"])
        if signed is None:
            print("crosscheck: signing failed after probe succeeded — vault changed mid-check?", file=sys.stderr)
            return 2
        sig_hex, _addr2 = signed
        # The plugin returns lowercase signature; both work but normalize 0x-prefix.
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex

        try:
            # Canonical payload fields per mindx_auth.py:210-214 — challenge_id,
            # address, signature. The plugin docstring on line 7 of mindx_auth.py
            # says {id, sig} but that's stale — the wire format is {challenge_id,
            # signature}. /verify returns 400 'rest_missing_callback_param' if
            # you send the docstring shape.
            v = await client.post(
                f"{base_url}/wp-json/mindx/v1/auth/verify",
                json={
                    "challenge_id": challenge["challenge_id"],
                    "address": vault_addr,
                    "signature": sig_hex,
                },
            )
        except Exception as e:
            print(f"crosscheck: verify POST failed: {e}", file=sys.stderr)
            return 2

        if v.status_code == 200:
            try:
                wp_user_id = v.json().get("user_id")
            except Exception:
                wp_user_id = None
            print(
                f"crosscheck: OK — vault wallet {vault_addr} IS allowlisted "
                f"(maps to wp_user_id={wp_user_id})"
            )
            return 0

        # 403 / 401 / other: render the plugin-side reason without leaking key material.
        reason = ""
        try:
            reason = v.json().get("code", "")
        except Exception:
            reason = v.text[:80]
        print(
            f"crosscheck: FAIL — vault wallet {vault_addr} is NOT allowlisted "
            f"(verify HTTP {v.status_code}, code={reason!r}). "
            f"REMEDIATION: add {vault_addr} to the mindx-publish-auth plugin's "
            f"allowlist on {base_url}, OR restore matching pk into the vault.",
            file=sys.stderr,
        )
        return 1


def main() -> int:
    # Use the wordpress.agent's own config so we hit the same base_url it will.
    try:
        from agents.wordpress_agent.vault_creds import load_wp_settings_from_vault
    except Exception as e:
        print(f"crosscheck: cannot import vault_creds: {e}", file=sys.stderr)
        return 2
    settings = load_wp_settings_from_vault()
    if settings is None:
        print(
            "crosscheck: vault settings unavailable "
            "(wordpress.agent:wp_base_url / :wp_user / :wp_app_password missing). "
            "Run scripts/vault/provision_wordpress_agent.py.",
            file=sys.stderr,
        )
        return 2
    base_url = str(settings.base_url).rstrip("/")
    return asyncio.run(_check(base_url))


if __name__ == "__main__":
    raise SystemExit(main())
