# BankonAgenticPlaceHook

> Optional per-mint listing emitter — when a bankoneth flow opts into AgenticPlace publication, this contract emits the indexer event that builds the marketplace card.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonAgenticPlaceHook.sol`](./BankonAgenticPlaceHook.sol)

## Role in bankoneth

`BankonAgenticPlaceHook` sits on the outbound edge of all three bankoneth registration flows. Whenever a registrar (Flow A: `BankonSubnameRegistrar`, Flow B: `BankonEthRegistrar`, Flow C: `BankonDomainHosting`) decides that a freshly-minted name should appear on **agenticplace.pythai.net**, it calls `list(...)` here. The contract emits a single `AgenticPlaceListing` event that an off-chain indexer (the AgenticPlace backend) consumes to create the public marketplace card for the iNFT.

The contract is intentionally minimal — it owns no funds, holds no liquidity, and stores only a configurable webhook URL. The webhook string is on-chain so the same deployed contract can be repointed from staging to production (or to a backup indexer) by an admin call, without redeploying any registrar. The role-gated `list(...)` selector keeps random callers from spraying junk listings — only the three deployer-granted registrars hold `LISTER_ROLE` after `DeployEthereum.s.sol` finishes.

This contract is the only direct bridge between the on-chain Ethereum side of bankoneth and the off-chain PYTHAI agentic marketplace. It is the only contract in the suite whose primary output is an event; nothing on-chain reads its data.

## Inheritance

- `IBankonAgenticPlaceHook` — public interface bundle (event + functions) defined in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol).
- `AccessControl` — for `DEFAULT_ADMIN_ROLE` (webhook + role management) and the custom `LISTER_ROLE`.

## Constructor

| arg                  | type     | purpose                                                                  |
|----------------------|----------|--------------------------------------------------------------------------|
| `admin`              | `address`| Granted `DEFAULT_ADMIN_ROLE` — can change the webhook URL + grant lister.|
| `initialWebhookURL`  | `string memory`| Initial indexer endpoint (e.g. `https://agenticplace.pythai.net/v1/listings`). |

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`. **No `LISTER_ROLE` is granted at construction** — `DeployEthereum.s.sol` explicitly grants it to each of the three registrars post-deploy.

## Storage layout

| name              | type     | purpose                                                | mutable? |
|-------------------|----------|--------------------------------------------------------|----------|
| `LISTER_ROLE`     | `bytes32 constant`| `keccak256("LISTER_ROLE")` role identifier.    | no       |
| `_webhookURL`     | `string` | Off-chain indexer URL announced on every URL update.   | yes (admin) |

(AccessControl's internal `_roles` mapping is also present.)

## Roles

| Role                 | keccak256                                                        | Who holds                       | What they can do                              |
|----------------------|------------------------------------------------------------------|----------------------------------|-----------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | `0x00…00` (OpenZeppelin's default)                                | `admin` (constructor arg)        | `setWebhookURL`, `grantLister`, grant/revoke other roles. |
| `LISTER_ROLE`        | `keccak256("LISTER_ROLE")`                                       | `BankonSubnameRegistrar`, `BankonEthRegistrar`, `BankonDomainHosting` (via deploy script `grantLister`) | Call `list(...)` to emit `AgenticPlaceListing`. |

## Events

### `WebhookURLUpdated(string oldURL, string newURL)`

Emitted every time the admin calls `setWebhookURL`. Indexers and ops dashboards should monitor this to detect a webhook flip (e.g. staging → prod) — neither parameter is indexed since strings cannot be indexed by value, only by hash.

### `AgenticPlaceListing(bytes32 indexed parentNode, bytes32 indexed labelhash, address indexed tbaAddress, uint256 zeroGTokenId, string metadataURI, address author)`

Emitted by `list(...)`. Defined on the interface in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol). Indexers should:

1. Treat `(parentNode, labelhash)` as the canonical ENS identity (use the namehash to build `label.bankon.eth` or `label.<parent>.eth`).
2. Use `tbaAddress` as the ERC-6551 Token-Bound Account on the iNFT chain.
3. Pull `metadataURI` (ipfs / ar / https) for the iNFT metadata.
4. Use `author` as the credit field on the marketplace card.

All three of the first arguments are indexed for cheap event filtering.

## Errors

This contract defines no custom errors. All reverts come from OpenZeppelin's `AccessControl` (`AccessControlUnauthorizedAccount` when a non-role-holder calls a gated function).

## External / public API

### `setWebhookURL(string calldata url)`

Updates the publicly-advertised webhook URL. Emits `WebhookURLUpdated(oldURL, url)` *before* the write, so listeners see both old and new values. Access: `DEFAULT_ADMIN_ROLE`. Cheap (one SSTORE + one event).

### `webhookURL() external view returns (string memory)`

Returns the current `_webhookURL`. Reads only.

### `grantLister(address lister) external`

Convenience wrapper that grants `LISTER_ROLE` to `lister`. Access: `DEFAULT_ADMIN_ROLE`. Used by `DeployEthereum.s.sol` to register the three registrars (`grantLister(subnameRegistrar)`, `grantLister(ethRegistrar)`, `grantLister(domainHosting)`). Note: `revokeRole(LISTER_ROLE, addr)` is available via the inherited `AccessControl` surface.

### `list(bytes32 parentNode, bytes32 labelhash, address tbaAddress, uint256 zeroGTokenId, string calldata metadataURI, address author) external`

Emits an `AgenticPlaceListing` event with the six arguments unchanged. **No state is written** — this is a pure event emitter. Access: `LISTER_ROLE`. Reverts with `AccessControlUnauthorizedAccount(msg.sender, LISTER_ROLE)` for non-lister callers.

## Internal helpers

—

## Invariants

- `_webhookURL` is never required to be a valid URL on-chain (the contract is agnostic to format). Off-chain validation is the caller's responsibility.
- `list(...)` never reverts except on role check — the event always reaches the chain when the access check passes.
- No funds are ever held by this contract; it has no `receive()` or `fallback()`.

## Security considerations

- **Trust model**: any lister can emit any payload. If `LISTER_ROLE` is mis-granted to an attacker, they can spam listings; the off-chain indexer should rate-limit per `tbaAddress`.
- **No reentrancy surface**: no state mutations beyond `_webhookURL` write and role mappings.
- **Signature replay / EIP-712**: not applicable — there is no signature surface.
- **Pause behaviour**: contract is not pausable. Spam mitigation is via `revokeRole(LISTER_ROLE, attacker)`.
- **Webhook hijack**: if `DEFAULT_ADMIN_ROLE` is compromised, the attacker can repoint the advertised webhook URL. The on-chain event payload is unaffected — only the discovery hint changes.
- **String storage**: SSTORE-cost on long URLs is bounded only by gas; restrict admin to trusted multisig in production.

## Integration patterns

- `BankonSubnameRegistrar`, `BankonEthRegistrar`, `BankonDomainHosting` each receive `LISTER_ROLE` in [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) lines 119-121:
  ```solidity
  BankonAgenticPlaceHook(d.agenticPlaceHook).grantLister(d.subnameRegistrar);
  BankonAgenticPlaceHook(d.agenticPlaceHook).grantLister(d.ethRegistrar);
  BankonAgenticPlaceHook(d.agenticPlaceHook).grantLister(d.domainHosting);
  ```
- A registrar should call `list(...)` **after** its main mint side-effects succeed (the event is the public announcement and should not fire before the on-chain state is committed).
- The frontend (`@bankoneth/core`, `@bankoneth/ui`) does **not** call this contract directly; it filters past `AgenticPlaceListing` events to render the marketplace.

## Known gotchas

- `LISTER_ROLE` is not auto-renounced — re-deploying a registrar requires the admin to call `revokeRole(LISTER_ROLE, oldRegistrar)` then `grantLister(newRegistrar)`.
- The webhook URL has no on-chain length cap. Don't store >32-byte URLs cheaply; consider IPFS pinning the index endpoint and storing the CID instead in v2.
- The indexer is responsible for de-duplication. Re-running a deploy that re-grants `LISTER_ROLE` can in principle replay listings only if a registrar exposes a re-mint path — the current registrars do not.
- `WebhookURLUpdated` is emitted **before** the SSTORE; this is intentional (old then new are both readable to indexers in event order).

## See also

- [`interfaces/IBankonExtensions.md`](./interfaces/IBankonExtensions.md) — `IBankonAgenticPlaceHook` interface and `AgenticPlaceListing` event signature.
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — Flow A caller.
- [`BankonEthRegistrar.md`](./BankonEthRegistrar.md) — Flow B caller.
- [`BankonDomainHosting.md`](./BankonDomainHosting.md) — Flow C caller.
- [`BankonInftAdapter.md`](./BankonInftAdapter.md) — populates the `tbaAddress` and `zeroGTokenId` that listings emit.
