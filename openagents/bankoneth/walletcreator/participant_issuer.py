# SPDX-License-Identifier: MIT
# (c) 2026 openBDK / Professor Codephreak
"""
OVERSEER / OVERLORD handoff — non-custodial owner recognition + signature-gated
participant walletgen.

Two custody models, deliberately separated:

  * OWNER  (the human OVERLORD): brings their OWN wallet. The software NEVER holds
    or generates their key — it only RECOGNISES them by recovering their address
    from an EIP-191 signature. This is "wallet recognition login from proof of
    signature where OWNER holds private key and software does not."

  * PARTICIPANT (an agent / bubbleroom member with no wallet of its own): the
    software walletgens an EVM keypair INTO the BANKON vault, but ONLY when an
    OWNER signs to authorise that issuance — the OVERSEER/OVERLORD handoff. The
    key is vault-custodied (so the agent can act), and its birth is attributable
    to the owner who authorised it.

The authorisation message is bound to (purpose, room, chainId, nonce) so a
captured signature cannot be replayed into a different room/chain or reused.
On-chain, the matching invariant is enforced by `OpenBDKDeployer`: the OWNER's
timelock holds all admin and the software/deploy key holds nothing.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

from eth_account import Account
from eth_account.messages import encode_defunct

HANDOFF_PREFIX = "OPENBDK-OVERLORD-HANDOFF"


class HandoffError(RuntimeError):
    pass


def build_handoff_challenge(*, room_id: int, chain_id: int, nonce: str, action: str = "issue-participant") -> str:
    """The canonical message an OWNER signs to authorise a handoff action.

    Binding room+chain+nonce makes the signature single-purpose and non-replayable.
    """
    return f"{HANDOFF_PREFIX} action={action} room={room_id} chainId={chain_id} nonce={nonce}"


def recover_signer(message: str, signature: str) -> str:
    """Recover the EIP-191 signer address. The software holds no key — it verifies."""
    return Account.recover_message(encode_defunct(text=message), signature=signature)


class OverlordHandoff:
    """Owner-gated participant walletgen over a BANKON-vault-backed WalletCreator."""

    def __init__(self, wallet_creator: Any, *, used_nonces: Optional[Set[str]] = None):
        # wallet_creator: walletcreator.wallet_creator.WalletCreator
        self.wc = wallet_creator
        # In-process replay guard. A production deployment persists consumed nonces
        # (e.g. in the vault or a DB); kept in-memory here and documented as such.
        self._used: Set[str] = used_nonces if used_nonces is not None else set()

    # ── OWNER: recognition only, never custody ──────────────────────────────
    @staticmethod
    def recognize_owner(*, message: str, signature: str, expected_owner: str) -> bool:
        """Login from proof of signature. Returns True iff the signature recovers
        to ``expected_owner``. The software stores nothing for the owner."""
        try:
            recovered = recover_signer(message, signature)
        except Exception:
            return False
        return recovered.lower() == expected_owner.lower()

    # ── PARTICIPANT: walletgen, but only under a signed owner authorisation ──
    def issue_participant_wallet(
        self,
        *,
        owner_address: str,
        room_id: int,
        chain_id: int,
        nonce: str,
        signature: str,
        label: str = "",
        action: str = "issue-participant",
    ) -> Dict[str, Any]:
        """Verify the OWNER signed the canonical handoff challenge, then walletgen a
        vault-custodied participant EVM wallet scoped to the room.

        Fails closed: a wrong signer, a replayed nonce, or a tampered message all
        raise HandoffError and NO wallet is created.
        """
        if nonce in self._used:
            raise HandoffError(f"nonce already consumed: {nonce}")

        message = build_handoff_challenge(room_id=room_id, chain_id=chain_id, nonce=nonce, action=action)
        if not self.recognize_owner(message=message, signature=signature, expected_owner=owner_address):
            raise HandoffError("owner signature did not authorise this handoff (recovery mismatch)")

        self._used.add(nonce)
        room_label = f"bubbleroom:{room_id}:{label}" if label else f"bubbleroom:{room_id}"
        wallet = self.wc.create_evm_wallet(label=room_label)
        return {
            "participant_address": wallet["address"],
            "vault_id": wallet["vault_id"],
            "room_id": room_id,
            "chain_id": chain_id,
            "authorized_by": owner_address,
            "nonce": nonce,
            "custody": "vault",  # participant key is vault-custodied (owner-authorised)
        }
