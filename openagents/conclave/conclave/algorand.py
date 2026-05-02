"""Algorand-side honor stake via x402 and parsec-wallet.

Architecture:

    [member] ──x402──► [parsec-wallet relayer] ──Algopy txn──► [PAI escrow on Algorand]
                                  │
                                  └─── attestAlgorandBond(...) on EVM ──► ConclaveBond.sol
                                                                             │
                                                                             ▼
                                                                     EVM bond +=
                                                                     algorandTxOf set

Slashes flow back the other way: a `MemberSlashed` event on the EVM
side is consumed by the relayer, which submits an Algorand txn that
moves the staked PAI from escrow to a burn address (or to the
counter-party, depending on the conclave's slash policy).

This module provides the **client-side helpers** that a member uses to
post a bond on Algorand. The relayer itself lives in the
parsec-wallet repo. We only need:

  1. `pai_stake_payload()`     — build the x402 payment spec
  2. `pai_stake_via_x402()`    — POST it to the parsec-wallet endpoint
  3. `attest_locally()`        — call `attestAlgorandBond` (only
                                  callable by the relayer; included
                                  here for tests and dev-mode bridges)

If `web3` and `py-algorand-sdk` aren't installed, the module is still
importable; the relevant functions raise on first use.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("conclave.algorand")


@dataclass
class X402StakeRequest:
    """An x402 'payment-required' style stake request.

    Format follows Coinbase's x402 spec for HTTP 402: the relayer
    serves a 402 with this body when a stake is required, and the
    client repeats with `X-Payment` filled in.
    """

    asset: str               # e.g. "PAI" or an Algorand ASA id ("123456")
    amount: int              # base units (e.g. microPAI)
    recipient: str           # Algorand escrow address (relayer-managed)
    conclave_id: str         # 0x-prefixed bytes32, anchors the EVM gating
    member_evm: str          # 0x-prefixed EVM address of the staker
    member_algo: str         # Algorand address of the staker
    memo: str = "conclave-bond"
    chain: str = "algorand-mainnet"

    def to_dict(self) -> dict[str, Any]:
        return {
            "x402": "1",
            "scheme": "exact",
            "network": self.chain,
            "asset": self.asset,
            "amount": str(self.amount),
            "recipient": self.recipient,
            "memo": self.memo,
            "extra": {
                "conclave_id": self.conclave_id,
                "member_evm": self.member_evm,
                "member_algo": self.member_algo,
            },
        }


def pai_stake_payload(
    *,
    conclave_id: str,
    member_evm: str,
    member_algo: str,
    amount_microPAI: int,
    relayer_recipient: str,
    pai_asa_id: str = "PAI",
) -> X402StakeRequest:
    """Build the stake request a member submits via x402."""
    return X402StakeRequest(
        asset=pai_asa_id,
        amount=amount_microPAI,
        recipient=relayer_recipient,
        conclave_id=conclave_id,
        member_evm=member_evm,
        member_algo=member_algo,
    )


def pai_stake_via_x402(
    parsec_wallet_url: str,
    payload: X402StakeRequest,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """POST to parsec-wallet's stake endpoint.

    Returns the relayer's response, which includes:

      {
        "algo_txid":   "<base32 txid>",
        "evm_attest_tx": "0x<hash>",     # ConclaveBond.attestAlgorandBond
        "amount":      <microPAI>,
        "released_at": <unix>            # earliest bond release
      }
    """
    r = httpx.post(
        f"{parsec_wallet_url.rstrip('/')}/x402/stake",
        json=payload.to_dict(),
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- #
# Relayer-side helpers (only useful in tests / local dev bridges)  #
# ---------------------------------------------------------------- #


def attest_locally(
    w3: Any,                    # web3.Web3
    bond_addr: str,
    bridge_signer: str,
    private_key: str,
    conclave_id: bytes,
    member_evm: str,
    amount_wei: int,
    algo_txid_bytes: bytes,
) -> str:
    """Call `ConclaveBond.attestAlgorandBond(...)` from the bridge address.

    Used in dev-mode bridges where the relayer is co-located. In
    production the parsec-wallet relayer runs this against its own
    funded signer key.
    """
    bond_abi = [{
        "type": "function",
        "name": "attestAlgorandBond",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "conclave_id", "type": "bytes32"},
            {"name": "member", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "algoTxid", "type": "bytes32"},
        ],
        "outputs": [],
    }]
    c = w3.eth.contract(address=bond_addr, abi=bond_abi)
    fn = c.functions.attestAlgorandBond(
        conclave_id, member_evm, amount_wei, algo_txid_bytes
    )
    nonce = w3.eth.get_transaction_count(bridge_signer)
    tx = fn.build_transaction({
        "from": bridge_signer,
        "nonce": nonce,
        "gas": 200_000,
        "maxFeePerGas": w3.eth.gas_price,
        "maxPriorityFeePerGas": w3.eth.gas_price,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key)
    return w3.eth.send_raw_transaction(signed.rawTransaction).hex()
