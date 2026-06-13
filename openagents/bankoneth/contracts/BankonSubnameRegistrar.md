# BankonSubnameRegistrar

> Flow A — ENS NameWrapper-based registrar issuing agent subnames under `bankon.eth`, bundling ERC-8004 identity, EIP-712 voucher payment, reputation gating, and length-tiered pricing.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`BankonSubnameRegistrar.sol`](./BankonSubnameRegistrar.sol)

## Role in bankoneth

`BankonSubnameRegistrar` is **Flow A**: the core agent-identity issuer. Customers (or their gateway relayer) call `register(...)`, `registerFree(...)`, `registerAgentSubname(...)`, or `renew(...)` to mint `<label>.bankon.eth` ENS subnames with the BANKON resolver record namespace pre-populated. The registrar:

- Speaks the **three-step canonical NameWrapper pattern**: temp-self-own → write records → transfer with locked fuses.
- Verifies **EIP-712 vouchers** signed by an authorized gateway signer (`GATEWAY_SIGNER_ROLE`) so the relayer cannot mint without a real off-chain payment.
- Gates eligibility via `BankonReputationGate` (paid path: not banned; free path: stake/score/TEE-attested).
- Optionally bundles an **ERC-8004 agent-identity mint** via `IIdentityRegistry8004` (toggleable via `setErc8004Bundle`).
- Records the receipt with `BankonPaymentRouter` for accounting + buyback signaling (best-effort, won't unwind the mint on router failure).
- Burns the soulbound `DEFAULT_FUSES = PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY` so the subname is non-transferable.
- Supports a special path `registerAgentSubname` (gated by `MINDX_AGENT_MINTER_ROLE`) that mints `<40-char-hex-address>.bankon.eth` for free for any mindX-registered agent.

The registrar is the most surface-rich contract in the suite. It is the only one that holds and writes to ENS NameWrapper directly. `BankonEthRegistrar` (Flow B) is for *new* `.eth` purchases; `BankonDomainHosting` (Flow C) is for *external* parents; this is the only contract that owns `bankon.eth` issuance.

## Inheritance

- `AccessControl` — multi-role surface (admin, ops, gov, gateway-signer, mindX-minter).
- `ReentrancyGuard` — all four user-facing entry points are `nonReentrant`.
- `Pausable` — `whenNotPaused` modifier on all four entry points; `pause`/`unpause` gated by `BANKON_OPS_ROLE`.
- `EIP712` — domain `("BankonSubnameRegistrar", "1")`.
- `ERC1155Holder` — temporarily holds the wrapped subname during the three-step register pattern.

Uses `ECDSA` for signature recovery on EIP-712 vouchers.

## Constructor

| arg                       | type      | purpose                                                                       |
|---------------------------|-----------|-------------------------------------------------------------------------------|
| `_nameWrapper`            | `address` | ENS NameWrapper (mainnet `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`).       |
| `_defaultResolver`        | `address` | Default resolver (typically `BankonSubnameResolver`).                         |
| `_parentNode`             | `bytes32` | `namehash("bankon.eth")` — the parent of every issued subname.                |
| `_paymentRouter`          | `address` | Payment router for receipt accounting.                                        |
| `_priceOracle`            | `address` | Price oracle.                                                                  |
| `_reputationGate`         | `address` | Reputation gate (eligibility checks).                                          |
| `_identityRegistry8004`   | `address` | Optional ERC-8004 identity registry (can be `address(0)`).                    |
| `_admin`                  | `address` | Granted `DEFAULT_ADMIN_ROLE`, `BANKON_OPS_ROLE`, `BONAFIDE_GOV_ROLE`.         |

Reverts `ZeroAddress` if any of `_nameWrapper`, `_defaultResolver`, `_paymentRouter`, `_priceOracle`, `_reputationGate`, or `_admin` is `address(0)`. Identity registry MAY be zero (the ERC-8004 bundle is then a no-op even when enabled).

Roles granted at construction: `DEFAULT_ADMIN_ROLE`, `BANKON_OPS_ROLE`, `BONAFIDE_GOV_ROLE` → `_admin`.

## Storage layout

| name                       | type                                       | purpose                                                                | mutable? |
|----------------------------|--------------------------------------------|------------------------------------------------------------------------|----------|
| `BANKON_OPS_ROLE`          | `bytes32 constant`                         | `keccak256("BANKON_OPS_ROLE")`.                                        | no       |
| `BONAFIDE_GOV_ROLE`        | `bytes32 constant`                         | `keccak256("BONAFIDE_GOV_ROLE")`.                                      | no       |
| `GATEWAY_SIGNER_ROLE`      | `bytes32 constant`                         | `keccak256("GATEWAY_SIGNER_ROLE")`.                                    | no       |
| `MINDX_AGENT_MINTER_ROLE`  | `bytes32 constant`                         | `keccak256("MINDX_AGENT_MINTER_ROLE")`.                                | no       |
| `DEFAULT_FUSES`            | `uint32 constant`                          | `0x10000 | 0x1 | 0x4 | 0x40000 = 0x50005` (soulbound default).         | no       |
| `REGISTRATION_TYPEHASH`    | `bytes32 constant`                         | EIP-712 typehash for the `Registration` struct.                        | no       |
| `RENEWAL_TYPEHASH`         | `bytes32 constant`                         | EIP-712 typehash for the `Renewal` struct.                             | no       |
| `COIN_TYPE_BASE`           | `uint256 constant`                         | `0x80002105` — Base L2 SLIP-44/ENSIP-11 coinType.                      | no       |
| `COIN_TYPE_ALGO`           | `uint256 constant`                         | `0x8000011B` — Algorand SLIP-44 283.                                   | no       |
| `nameWrapper`              | `INameWrapper` immutable                   | ENS NameWrapper.                                                        | no       |
| `defaultResolver`          | `IPublicResolver` immutable                | Default resolver for issued subnames.                                  | no       |
| `parentNode`               | `bytes32` immutable                        | `namehash("bankon.eth")`.                                              | no       |
| `paymentRouter`            | `IBankonPaymentRouter` immutable           | Receipt + revenue router.                                              | no       |
| `priceOracle`              | `IBankonPriceOracle` public                | Length-tier USD oracle.                                                | yes (gov) |
| `reputationGate`           | `IBankonReputationGate` public             | Eligibility gate.                                                       | yes (gov) |
| `identityRegistry8004`     | `IIdentityRegistry8004` public             | Optional ERC-8004 registry.                                            | yes (gov) |
| `erc8004BundleEnabled`     | `bool` public                              | Toggles ERC-8004 bundling (default `true`).                            | yes (gov) |
| `usedReceipts`             | `mapping(bytes32 => bool)` public          | EIP-712 voucher replay protection.                                      | yes (register/renew) |
| `labelOf`                  | `mapping(bytes32 => string)` public        | Node → label, for indexer lookups.                                     | yes (register*) |
| `ownerOfLabel`             | `mapping(bytes32 => address)` public       | Node → owner, for indexer lookups.                                     | yes (register*) |

## Roles

| Role                       | keccak256                                          | Who holds                                              | What they can do                                                          |
|----------------------------|----------------------------------------------------|--------------------------------------------------------|---------------------------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE`       | OpenZeppelin default                               | `_admin` (constructor)                                  | Manage all roles.                                                          |
| `BANKON_OPS_ROLE`          | `keccak256("BANKON_OPS_ROLE")`                     | `_admin` (constructor)                                  | `pause`, `unpause`.                                                        |
| `BONAFIDE_GOV_ROLE`        | `keccak256("BONAFIDE_GOV_ROLE")`                   | `_admin` (constructor)                                  | `setPriceOracle`, `setReputationGate`, `setIdentityRegistry8004`, `setErc8004Bundle`. |
| `GATEWAY_SIGNER_ROLE`      | `keccak256("GATEWAY_SIGNER_ROLE")`                 | Off-chain gateway signer EOA (granted post-deploy)     | Sign EIP-712 vouchers consumed by `register`/`renew`.                     |
| `MINDX_AGENT_MINTER_ROLE`  | `keccak256("MINDX_AGENT_MINTER_ROLE")`             | mindX agent-minter service (granted post-deploy)       | Call `registerAgentSubname(...)` for free.                                |

## Events

### `SubnameRegistered(bytes32 indexed node, string label, address indexed owner, uint64 expiry, uint256 priceUSD6, bytes32 paymentReceiptHash, uint256 erc8004AgentId, bool free)`

Emitted by all three registration paths (`register`, `registerAgentSubname`, `registerFree`). `free = true` for the two free paths; `paymentReceiptHash = bytes32(0)` for free paths.

### `SubnameRenewed(bytes32 indexed node, string label, uint64 newExpiry, uint256 priceUSD6)`

Emitted on `renew`.

### `ResolverRecordsWritten(bytes32 indexed node, address indexed owner)`

Emitted at the end of `_writeAndTransfer` (after the three-step pattern completes). Indexers should treat as "subname now fully usable".

### `PriceOracleUpdated(address oldOracle, address newOracle)` / `ReputationGateUpdated(...)` / `IdentityRegistryUpdated(...)` / `Erc8004BundleToggled(bool enabled)`

Governance events for the corresponding `set*` calls.

## Errors

### `LabelTooShort()`

Reverted by `_checkLabel` when `bytes(label).length < 3`, and by `registerFree` when `bytes(label).length < 7`.

### `LabelEmpty()`

Reverted by `_checkLabel` when `bytes(label).length == 0`.

### `ReceiptAlreadyUsed()`

Reverted when `usedReceipts[paymentReceiptHash]` is already true (replay attempt on the EIP-712 voucher).

### `VoucherExpired()`

Reverted when `block.timestamp > deadline` on the voucher.

### `InvalidGatewaySignature()`

Reverted when the recovered signer does NOT hold `GATEWAY_SIGNER_ROLE`.

### `NotEligible()`

Reverted by `register` (paid) when `reputationGate.isEligibleForRegistration(owner) == false`, or by `registerFree` when `isEligibleForFree(owner) == false`.

### `InvalidExpiry()`

Reverted by `_capExpiry` when `expiry <= block.timestamp`.

### `ZeroAddress()`

Reverted by constructor (any required address is zero) or by user-facing functions when `owner == address(0)`.

## External / public API

### `register(string label, address owner, uint64 expiry, bytes32 paymentReceiptHash, uint256 deadline, bytes gatewaySig, AgentMetadata meta) external returns (bytes32 node, uint256 agentId)`

The canonical paid path. Behaviour:
1. `_checkLabel(label)` (≥ 3 chars).
2. `owner != address(0)`.
3. `block.timestamp <= deadline` (`VoucherExpired`).
4. `!usedReceipts[paymentReceiptHash]` (`ReceiptAlreadyUsed`).
5. `reputationGate.isEligibleForRegistration(owner)` (`NotEligible`).
6. Compute EIP-712 digest over `(label, owner, expiry, paymentReceiptHash, deadline)`, recover signer via ECDSA, require `GATEWAY_SIGNER_ROLE` holder (`InvalidGatewaySignature`).
7. Mark receipt as used.
8. `_capExpiry(expiry)` to parent expiry.
9. `_writeAndTransfer(...)` — three-step mint + records.
10. If `erc8004BundleEnabled` and registry set, `identityRegistry8004.register(owner, meta.agentURI)` and best-effort metadata writes via `_safeSetMeta`.
11. `priceOracle.priceUSD(label, _yearsFromExpiry(expiry))`.
12. If `paymentRouter.splitConfigured()`, try `paymentRouter.recordReceipt(...)` (catch and ignore — never unwinds the mint).
13. Emit `SubnameRegistered(..., free=false)`.

Access: anyone (signature gates trust). Modifiers: `nonReentrant`, `whenNotPaused`. Returns `(node, agentId)`.

### `registerAgentSubname(address agent, uint64 expiry, AgentMetadata meta) external returns (bytes32 node, uint256 agentId, string label)`

Free path for mindX agents. Computes `label = _addressToLowerHex(agent)` (lowercase 40-char hex, no 0x prefix), `_capExpiry`, `_writeAndTransfer`, optional ERC-8004 bundle, and emits `SubnameRegistered(..., free=true, paymentReceiptHash=bytes32(0))`. Access: `MINDX_AGENT_MINTER_ROLE`. Modifiers: `nonReentrant`, `whenNotPaused`. The 40-char label exceeds the 7-char free-path minimum.

### `registerFree(string label, address owner, uint64 expiry, AgentMetadata meta) external returns (bytes32 node, uint256 agentId)`

Reputation-gated free path. Requires `bytes(label).length >= 7` and `reputationGate.isEligibleForFree(owner)`. Same `_writeAndTransfer` + optional ERC-8004 bundle. Access: anyone (eligibility-gated). Modifiers: `nonReentrant`, `whenNotPaused`.

### `renew(string label, uint64 newExpiry, bytes32 paymentReceiptHash, uint256 deadline, bytes gatewaySig) external`

Extends an existing subname's expiry. EIP-712 voucher with `RENEWAL_TYPEHASH = keccak256("Renewal(string label,uint64 newExpiry,bytes32 paymentReceiptHash,uint256 deadline)")`. Calls `nameWrapper.extendExpiry(parentNode, labelhash, newExpiry)` and records the receipt best-effort. Emits `SubnameRenewed`. Access: anyone (signature-gated). Modifiers: `nonReentrant`, `whenNotPaused`.

### `quoteUSD(string calldata label, uint64 expiry) external view returns (uint256 usd6)`

Returns the USD-base-units price for the label over the implied duration (`expiry` or `block.timestamp + 365 days` if zero).

### `setPriceOracle(address _o) external`

Hot-swaps the price oracle. Reverts `ZeroAddress` if `_o == address(0)`. Access: `BONAFIDE_GOV_ROLE`. Emits `PriceOracleUpdated`.

### `setReputationGate(address _g) external`

Hot-swaps the reputation gate. Access: `BONAFIDE_GOV_ROLE`. Emits `ReputationGateUpdated`.

### `setIdentityRegistry8004(address _r) external`

Hot-swaps the ERC-8004 registry (can be set to `address(0)`). Access: `BONAFIDE_GOV_ROLE`. Emits `IdentityRegistryUpdated`.

### `setErc8004Bundle(bool enabled) external`

Toggles the ERC-8004 bundling at register-time. Access: `BONAFIDE_GOV_ROLE`. Emits `Erc8004BundleToggled`.

### `pause() external` / `unpause() external`

Halt/resume all four entry points. Access: `BANKON_OPS_ROLE`.

### `supportsInterface(bytes4 interfaceId) public view returns (bool)`

ERC-165 surface combining `AccessControl` + `ERC1155Holder`.

## Internal helpers

### `_checkLabel(string calldata label) internal pure`

Reverts `LabelEmpty` on empty, `LabelTooShort` on length < 3.

### `_capExpiry(uint64 expiry) internal view returns (uint64)`

Reverts `InvalidExpiry` if `expiry <= block.timestamp`. If the parent has an expiry (`parentExpiry > 0`) and `expiry > parentExpiry`, returns `parentExpiry` (the **subname expiry never exceeds parent expiry** invariant).

### `_writeAndTransfer(string label, address owner, uint64 expiry, AgentMetadata meta) internal returns (bytes32 node)`

The **three-step canonical pattern** (from docs.ens.domains/wrapper/creating-subname-registrar):
1. `nameWrapper.setSubnodeOwner(parentNode, label, address(this), 0, expiry)` — mint to self so we can write records.
2. `_writeAgentRecords(node, owner, meta)` — multicall the resolver to populate text/contenthash/addr records.
3. `nameWrapper.setSubnodeRecord(parentNode, label, owner, defaultResolver, 0, DEFAULT_FUSES, expiry)` — transfer to owner with soulbound fuses burned.

Records `labelOf[node]` and `ownerOfLabel[node]`. Emits `ResolverRecordsWritten`.

### `_writeAgentRecords(bytes32 node, address owner, AgentMetadata meta) internal`

Dynamically sizes a `bytes[]` of selector-encoded calls (skipping empty fields), then `defaultResolver.multicall(calls)`. Always writes `setAddr(node, owner)`. Conditionally writes `setText(url)`, `setText(x402.endpoint)`, `setText(algoid.did)`, `setText(agent.card)`, `setContenthash`, multi-chain `setAddr(COIN_TYPE_BASE)`, multi-chain `setAddr(COIN_TYPE_ALGO)`.

### `_safeSetMeta(uint256 agentId, bytes32 key, bytes value) internal`

Try-wraps `identityRegistry8004.setMetadata` — never reverts on failure.

### `_yearsFromExpiry(uint64 expiry) internal view returns (uint256)`

Ceiling-rounds `(expiry - block.timestamp)` to years. Returns `0` for expired or current-block expiry.

### `_concat(string a, string b) internal pure returns (string)`

`string(abi.encodePacked(a, b))`.

### `_addressToLowerHex(address a) internal pure returns (string)`

Converts an address to its 40-char lowercase hex form (no `0x` prefix).

## Invariants

- **Subname expiry never exceeds parent expiry** (enforced in `_capExpiry`).
- **Every receipt is consumed at most once** (`usedReceipts[hash]` flips false → true and never back).
- For successful `register`/`registerAgentSubname`/`registerFree` calls, `labelOf[node]` and `ownerOfLabel[node]` are set.
- `DEFAULT_FUSES` burned on every minted subname → subname is non-transferable + parent-locked + cannot be unwrapped.
- The contract holds no funds. ERC-1155 holdings are transient (subname is held only between `setSubnodeOwner` and `setSubnodeRecord` inside `_writeAndTransfer`).
- ERC-8004 bundle is best-effort: a failed identity mint does not revert the subname.
- Receipt-router calls are best-effort: a failed `recordReceipt` does not revert the subname.
- No `receive()` declared.

## Security considerations

- **EIP-712 voucher**: domain `("BankonSubnameRegistrar", "1", chainId, this)` — vouchers are chain-bound and contract-bound. Signature recovery uses OpenZeppelin's malleability-safe `ECDSA.recover`.
- **Voucher replay**: protected by `usedReceipts` + `deadline`. The `paymentReceiptHash` should be the off-chain x402 receipt hash so replay is also prevented at the attestor layer.
- **Reentrancy**: every public entry point is `nonReentrant`. The resolver `multicall` uses `delegatecall` internally but doesn't expose state-write methods to attackers (REGISTRAR_ROLE-gated).
- **Pause behaviour**: pause halts all registrations + renewals; existing subnames are unaffected.
- **`registerAgentSubname` trust**: the role-holder is the trust anchor. A compromised mindX minter can mint arbitrary `<addr>.bankon.eth` names for free; rotate the role-holder key periodically.
- **`registerFree` reputation oracle trust**: see `BankonReputationGate.md` — a malicious oracle inflates eligibility.
- **`_writeAndTransfer` step-2 records**: the resolver multicall is wrapped in `defaultResolver.multicall(calls)`. If the resolver's multicall reverts any sub-call, the whole register reverts — the temp-self-own subname will NOT be cleaned up (it remains owned by the registrar). Recovery: admin tooling to transfer leftover wrapped subnames is not built in; consider an emergency-rescue method.
- **ERC-8004 bundle failure**: `identityRegistry8004.register` is NOT try-wrapped — if it reverts, the whole register reverts. Only `_safeSetMeta` is wrapped. Be careful when swapping the registry.
- **Best-effort receipt recording**: `recordReceipt` is try-wrapped, so missing `REGISTRAR_ROLE` on the router is silent. Check post-deploy that the router has granted the role if you want the audit ledger.
- **`COIN_TYPE_BASE` / `COIN_TYPE_ALGO`**: ENSIP-11 coinType for Base = `0x80002105` (2147483648 + 8453); SLIP-44 283 for Algorand = `0x8000011B`. Verify against latest ENSIP-11 registry before promoting new chains.
- **Soulbound fuses (`DEFAULT_FUSES = 0x50005`)**: `PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY`. CANNOT_TRANSFER (`0x4`) is the critical flag — once burned, the subname cannot be transferred away from the owner. Renewal via `extendExpiry` still works because `CAN_EXTEND_EXPIRY` is also burned.

## Integration patterns

- Off-chain gateway issues an EIP-712 `Registration` voucher after the customer pays via x402-avm (Algorand) or USDC permit (L1). The customer (or the relayer) then submits the voucher + `meta` to `register(...)`.
- The mindX agent-minter service (e.g. a backend with `MINDX_AGENT_MINTER_ROLE`) mints free per-agent subnames on agent registration: `registerAgentSubname(agentAddress, expiry, meta)`. The label is the agent's hex address — globally unique, no name-squatting.
- The resolver's `setAddr` requires `REGISTRAR_ROLE`. This is granted via `BankonSubnameResolver.grantRegistrar(d.subnameRegistrar)` at [`script/DeployEthereum.s.sol:116`](../script/DeployEthereum.s.sol).
- Gateway signer registration (post-deploy): `grantRole(GATEWAY_SIGNER_ROLE, signerEOA)`.
- mindX minter registration: `grantRole(MINDX_AGENT_MINTER_ROLE, mindxBackend)`.
- Deployed via `DeployEthereum.s.sol` line 88: `new BankonSubnameRegistrar(...)`.

## Known gotchas

- **`_writeAndTransfer` step-2 failure orphans the wrapped subname**: if the resolver multicall reverts (e.g. a sub-call selector is wrong), the subname stays owned by this contract because the function reverts. There is no auto-rescue. Mitigation: only register against an audited resolver, or add an admin-only rescue method.
- **`renew` does NOT check the EIP-712 `owner` field**: the renewal voucher binds only `(label, newExpiry, receiptHash, deadline)`. Anyone with a valid voucher can renew any label. This is intentional (renewal is permissionless) but worth knowing.
- **ERC-8004 bundle is best-effort partial**: `register` itself is NOT wrapped — only `setMetadata` is wrapped. A registry that reverts in `register` reverts the whole flow. The bundle toggle (`setErc8004Bundle(false)`) is the emergency stop.
- **`_safeSetMeta` swallows errors silently** — there's no event for failure. If you're debugging missing ERC-8004 metadata, check the registry directly.
- **`_addressToLowerHex` produces 40 chars but the registrar's `_checkLabel` requires only ≥ 3** — agent subnames are oversized intentionally, not a bug.
- **Multicall via resolver**: the resolver's `multicall` uses `delegatecall(address(this))` so each sub-call preserves `msg.sender` as this registrar — which is why this registrar holds `REGISTRAR_ROLE` on the resolver.
- **`registerAgentSubname` does not verify** that `agent` is actually a mindX agent — it trusts the role-holder.
- The `usedReceipts` mapping is keyed by the EIP-712 voucher hash, which is the **same** hash used by the payment router (`seenReceipt`) and the x402 attestor (`_spent`). Three-layer replay protection.

## See also

- [`interfaces/IBankon.md`](./interfaces/IBankon.md) — `INameWrapper`, `IPublicResolver`, `IBankonPriceOracle`, `IBankonReputationGate`, `IIdentityRegistry8004`, `IBankonPaymentRouter` interfaces.
- [`BankonSubnameResolver.md`](./BankonSubnameResolver.md) — receives the multicall'd record writes.
- [`BankonPriceOracle.md`](./BankonPriceOracle.md) — supplies USD price.
- [`BankonReputationGate.md`](./BankonReputationGate.md) — eligibility checks.
- [`BankonPaymentRouter.md`](./BankonPaymentRouter.md) — receives receipt records.
- [`BankonX402Attestor.md`](./BankonX402Attestor.md) — independent verification of x402 receipt hashes.
- [`BankonAgenticPlaceHook.md`](./BankonAgenticPlaceHook.md) — optional marketplace announcement.
- [`BankonInftAdapter.md`](./BankonInftAdapter.md) — iNFT Mode A binding target.
- [`identity/AgentRegistry.md`](./identity/AgentRegistry.md) — candidate ERC-8004 implementation.
- [`BankonEthRegistrar.md`](./BankonEthRegistrar.md) — Flow B counterpart.
- [`BankonDomainHosting.md`](./BankonDomainHosting.md) — Flow C counterpart.
