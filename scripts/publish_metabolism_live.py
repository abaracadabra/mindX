#!/usr/bin/env python
"""Flip the inference-metabolism draft (post 715) to PUBLISHED — in place,
no duplicate. Uses the wordpress.agent vault auth via WordpressAgent.

Run from repo root on the VPS as the mindx user.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

POST_ID = 715


async def main() -> int:
    from agents.wordpress_agent.vault_creds import load_wp_settings_from_vault
    from agents.wordpress_agent.agent import WordpressAgent

    settings = load_wp_settings_from_vault()
    if not settings:
        print("ERROR: wordpress.agent vault settings unavailable")
        return 1
    agent = WordpressAgent(settings)
    try:
        resp = await agent._request_with_retry(
            "POST", f"/posts/{POST_ID}", json={"status": "publish"}
        )
        print("HTTP", resp.status_code)
        try:
            d = resp.json()
            print(f"post {d.get('id')} status={d.get('status')} link={d.get('link')}")
        except Exception:
            print(resp.text[:300])
        return 0 if resp.status_code < 300 else 1
    finally:
        await agent.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
