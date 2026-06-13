# MockIdentityRegistry

> Minimal ERC-8004-shape identity registry mock used by `BankonSubnameRegistrar` tests to verify ERC-8004 bundle minting without deploying a real `AgentRegistry`.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`MockIdentityRegistry.sol`](./MockIdentityRegistry.sol)

## What it mocks

Stands in for the production [`contracts/identity/AgentRegistry.sol`](../../contracts/identity/AgentRegistry.sol) (an ERC-721 + ERC-8004 hybrid). Implements the [`IIdentityRegistry8004`](../../contracts/interfaces/IBankon.sol) interface — specifically `register(address, string)` and `setMetadata(uint256, bytes32, bytes)`.

**Faithfulness:** very low.
- No ERC-721 minting — just sequential ID counter + flat `ownerOf` mapping.
- No metadata schema validation.
- No access control — any caller can `register` or `setMetadata` for any agentId.
- No events.
- No URI-to-IPFS validation.

The mock exists to confirm the registrar *calls* the registry with the right args; the registry's own ERC-8004 semantics are tested separately against `AgentRegistry`.

## Storage / state

| Field | Type | Purpose / how tests use it |
|---|---|---|
| `nextId` | `uint256` (public, default 1) | Auto-incremented agent ID counter. Tests read this to confirm "no mint happened" (e.g., `test_PaidRegister_skipsErc8004WhenDisabled` asserts `idreg.nextId() == 1` after the bundle is disabled). |
| `ownerOf` | `mapping(uint256 => address)` (public) | agentId → owner wallet. Tests assert `idreg.ownerOf(agentId) == alice` after register. |
| `uriOf` | `mapping(uint256 => string)` (public) | agentId → agent metadata URI (ipfs://…). Tests assert `idreg.uriOf(agentId) == _meta().agentURI`. |
| `meta` | `mapping(uint256 => mapping(bytes32 => bytes))` (public) | agentId → metadata key → value. Stored but tests don't currently read it back. |

## Implemented methods

| Method | Production behaviour (`AgentRegistry`) | Mock behaviour | Notes |
|---|---|---|---|
| `register(address agentWallet, string agentURI) → uint256 agentId` | Mints ERC-721 NFT to `agentWallet`, stamps token URI, emits `Transfer` + `AgentRegistered`. Access-controlled (`MINTER_ROLE`). | `agentId = nextId++; ownerOf[agentId] = agentWallet; uriOf[agentId] = agentURI;` Returns the new id. | No access control. No event. No NFT-token semantics. |
| `setMetadata(uint256 agentId, bytes32 key, bytes value)` | Sets extended ERC-8004 metadata key/value with access control. Emits `MetadataSet`. | `meta[agentId][key] = value;` — silent storage write. | No access control, no event, no validation that `agentId` exists. |

## Admin / test helpers

**None.** The contract has no helper methods beyond the interface. Tests use the public getters (`nextId`, `ownerOf`, `uriOf`, `meta`) to read state directly.

## Limitations

- **No access control** — production `AgentRegistry` gates `register` behind `MINTER_ROLE` (granted to the registrar). The mock lets anyone mint, so tests cannot verify the registrar respects the role gate.
- **No ERC-721 semantics** — `transferFrom`, `safeTransferFrom`, `approve`, `balanceOf` all absent. Tests can't verify NFT transfer behavior post-mint.
- **No events** — `AgentRegistered`, `Transfer`, `MetadataSet` are all silent. Tests cannot use `expectEmit` against the mock.
- **No URI format validation** — accepts arbitrary strings.
- **No metadata schema** — `setMetadata` writes any `bytes32 key`/`bytes value`. Production may enforce key namespacing.
- **No ID-existence check on `setMetadata`** — writes to a never-registered `agentId` silently succeed.

## Used by

- [`../BankonSubnameRegistrar.t.sol`](../BankonSubnameRegistrar.t.sol) — primary consumer; instantiates as `idreg = new MockIdentityRegistry()` and asserts the registrar calls `register(...)` with correct args during ERC-8004 bundle path.

Not used by any other test file in `test/`.

## See also

- [`../../contracts/identity/AgentRegistry.sol`](../../contracts/identity/AgentRegistry.sol) — production contract this mocks.
- [`../../contracts/interfaces/IBankon.sol`](../../contracts/interfaces/IBankon.sol) — `IIdentityRegistry8004` interface this implements.
- [`MockNameWrapper.sol`](./MockNameWrapper.sol), [`MockResolver.sol`](./MockResolver.sol) — sibling test mocks.
- `docs/ERC8004_BUNDLE.md` — ERC-8004 bundle design rationale.
