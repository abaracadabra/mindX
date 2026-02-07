# Keyminter – Vault Access Key Issuance

Contracts for **issuance of access to the vault**: holding a minted key (NFT) grants vault access when the backend access_gate checks the contract.

## Contracts

| Contract | Base | Purpose |
|----------|------|--------|
| **VaultKeyDynamic** | DynamicNFT (dNFT) | Mints dynamic keys; metadata (scope, expiry hint) is updatable until frozen. |
| **VaultKeyIntelligent** | IntelligentNFT (iNFT) | Mints intelligent keys; adds authorized `agentAddress` (e.g. backend) that can `agentInteract` to log or revoke. |

## Deployment

- **VaultKeyDynamic**: Deploy with `initialOwner` (key issuer) and `agenticPlace` (marketplace; use `address(0)` to disable).
- **VaultKeyIntelligent**: Same. Optional: set `agentAddress` per key to the mindX vault backend so it can call `agentInteract(tokenId, data)` to log access.

Build from a Foundry workspace that includes `daio/contracts` and remappings for `@openzeppelin` and `../dnft`, `../inft`, `../THOT`. Example (from repo that has OpenZeppelin and DAIO contracts):

```bash
# From project root with remappings for dnft, inft, THOT, openzeppelin
forge build --contracts daio/contracts/keyminter
```

## Minting Keys

- **Dynamic**: `mintKey(to, scope, expiryHint)` — e.g. `mintKey(user, "user_folder", "2025-12-31")`.
- **Intelligent**: `mintKeyIntelligent(to, scope, expiryHint, agentAddress)` — set `agentAddress` to vault backend for logging/revoke.

## Backend (access_gate)

Configure mindX access_gate to require holding a key:

- `MINDX_ACCESS_GATE_ENABLED=true`
- `MINDX_ACCESS_GATE_TYPE=erc721`
- `MINDX_ACCESS_GATE_CONTRACT=<VaultKeyDynamic or VaultKeyIntelligent address>`
- `MINDX_ACCESS_GATE_RPC_URL=<chain RPC>`
- Optional: `MINDX_ACCESS_GATE_TOKEN_ID=<id>` to require a specific key; otherwise `balanceOf(wallet) >= 1` grants access.

See `docs/keyminter/KEYMINTER_VAULT_ACCESS.md` for suitability assessment and design.
