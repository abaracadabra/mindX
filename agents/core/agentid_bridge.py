"""
Bridge between mindX's sync `BankonVault` and agentID's async `VaultLike` protocol.

agentID's `agentid_identity.vault.VaultLike` is async-only and stores opaque
`bytes` values. mindX's `BankonVault` is sync and stores `str` values (with a
`context` tag). This adapter wraps BankonVault so `agentid_identity.issue_agent_identity`
can use it directly without re-implementing any crypto.

The underlying encryption (AES-256-GCM + HKDF-SHA512 per-entry domain separation)
is BankonVault's existing production-grade implementation. We only translate the
interface shape.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mindx_backend_service.bankon_vault.vault import BankonVault


class BankonVaultAgentIDAdapter:
    """
    Async `VaultLike` facade over a sync `BankonVault` instance.

    Stores secrets as hex strings inside BankonVault (vault's native `value: str`
    slot), decoding back to bytes on read. Callers never see the hex form.

    Usage:
        vault = BankonVault()
        vault.unlock_with_key_file()
        adapter = BankonVaultAgentIDAdapter(vault, context="agentid_identity")

        from agentid_identity import issue_agent_identity, IssueRuntime, IssueIdentityOptions
        identity = await issue_agent_identity(
            IssueIdentityOptions(role="trading", chain="baseSepolia"),
            IssueRuntime(vault=adapter, evm_rpc_url=...),
        )
    """

    def __init__(self, vault: "BankonVault", context: str = "agentid_identity") -> None:
        if not vault.is_unlocked():
            raise RuntimeError(
                "BankonVaultAgentIDAdapter: vault must be unlocked before wrapping"
            )
        self._vault = vault
        self._context = context

    async def put(self, ref: str, secret: bytes) -> None:
        self._vault.store(ref, secret.hex(), context=self._context)

    async def get(self, ref: str) -> bytes:
        value = self._vault.retrieve(ref)
        if value is None:
            raise KeyError(f'vault: missing ref "{ref}"')
        return bytes.fromhex(value)

    async def has(self, ref: str) -> bool:
        # list_entries returns metadata without decrypting; safer than calling retrieve
        return any(e["id"] == ref for e in self._vault.list_entries())

    async def list(self, prefix: Optional[str] = None) -> list[str]:
        ids = [e["id"] for e in self._vault.list_entries()]
        if prefix:
            return [i for i in ids if i.startswith(prefix)]
        return ids
