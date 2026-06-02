"""
agents.marketing.onchain — Python clients for the marketing receipt + identity contracts.

Phase 1 invariants:
  - Every client has a `dry_run=True` default. Live submission needs
    explicit `dry_run=False` from the caller (typically only `bind_identity --execute`).
  - We reuse `agents/storage/raw_tx.py:RawTxClient` for the EIP-1559 sender;
    no new web3 sender is introduced.
  - Signing uses `eth_account.Account` (already a repo dep).
  - Tests inject a mock RawTxClient; production callers wire one against
    the operator's BANKON Vault key.
"""
from __future__ import annotations
