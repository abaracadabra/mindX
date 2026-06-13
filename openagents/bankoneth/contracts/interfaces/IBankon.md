# IBankon

> Interface bundle for the core BANKON / ENS integration surface — wraps the ENS `NameWrapper` + `PublicResolver` subsets, the length-tier BANKON price oracle, the agnostic reputation gate, the ERC-8004-style identity registry, and the BANKON payment router.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`IBankon.sol`](./IBankon.sol)

## Role in bankoneth

`IBankon.sol` is the **dependency surface** the BANKON ENS registrar (the `Bankon*` core contracts in this tree) uses to interact with the canonical ENS infrastructure on Ethereum mainnet, plus the BANKON-specific primitives it adds on top. By holding only the interfaces, the concrete registrar implementations can be unit-tested against mocks (the `mocks/Mock*` files in this tree) and deployed against the real ENS contracts without source-level coupling.

The bundle has two halves:

1. **ENS surface (external)**: `INameWrapper` + `IPublicResolver` are minimal extractions of the actual ENS contracts the registrar needs. These are real deployed contracts on mainnet (e.g. NameWrapper at `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`); bankoneth never re-implements them, only consumes them.
2. **BANKON-native surface (in-tree)**: `IBankonPriceOracle`, `IBankonReputationGate`, `IIdentityRegistry8004`, `IBankonPaymentRouter`. These are implemented by concrete `Bankon*` contracts that ship in the same `bankoneth/contracts/` tree.

The split mirrors BANKON's architectural philosophy: **agnostic primitives**. Any reputation system (BONA FIDE, ERC-8004 attestation, custom) can implement `IBankonReputationGate` and slot in. Any pricing oracle that returns USDC base units can implement `IBankonPriceOracle`. Any router that splits revenue can implement `IBankonPaymentRouter`.

This file is paired with [`IBankonExtensions.sol`](./IBankonExtensions.sol) which adds the second-tier interfaces (Subname resolver, INFT adapter, X402 attestor, AgenticPlace hook, ETH registrar, Domain hosting) on top of these primitives.

## Interfaces defined

### `INameWrapper`

Subset of the ENS NameWrapper interface this registrar uses. Reference: <https://github.com/ensdomains/ens-contracts> (`NameWrapper.sol`).

The NameWrapper is the ERC-1155 wrapper around ENS names that introduces the **fuses** model (CANNOT_UNWRAP, CANNOT_BURN_FUSES, etc.) which BANKON relies on to make subnames non-reversible.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `ownerOf(uint256 id) → address` | yes | ERC-1155 wrapped-name owner lookup |
| `getData(uint256 id) → (address owner, uint32 fuses, uint64 expiry)` | yes | Full state read: owner + fuse bitmap + expiry |
| `setSubnodeOwner(bytes32 parentNode, string label, address owner, uint32 fuses, uint64 expiry) → bytes32` | no | Mint a wrapped subname under `parentNode`. Returns the subnode hash. **Primary BANKON subname issuance primitive** |
| `setSubnodeRecord(bytes32 parentNode, string label, address owner, address resolver, uint64 ttl, uint32 fuses, uint64 expiry) → bytes32` | no | Like `setSubnodeOwner` but also sets resolver + ttl in one call |
| `setChildFuses(bytes32 parentNode, bytes32 labelhash, uint32 fuses, uint64 expiry)` | no | Burn additional fuses on a child after mint |
| `setFuses(bytes32 node, uint16 ownerControlledFuses) → uint32` | no | Burn owner-controlled fuses on a node the caller owns |
| `setResolver(bytes32 node, address resolver)` | no | Point a wrapped name at a resolver |
| `extendExpiry(bytes32 parentNode, bytes32 labelhash, uint64 expiry) → uint64` | no | Push out a wrapped subname's expiry (subject to parent's CANNOT_EXTEND_EXPIRY fuse) |
| `isWrapped(bytes32 node) → bool` | yes | True iff the name is in the wrapper |
| `setApprovalForAll(address operator, bool approved)` | no | ERC-1155 approval |
| `approve(address to, uint256 tokenId)` | no | ERC-721-style approval for ERC-1155 wrapped names |

**Implementers:** External — the canonical ENS NameWrapper deployment.
**Callers in bankoneth:** The concrete `Bankon*` registrars (BankonRegistrar, BankonEthRegistrar, BankonDomainHosting).

---

### `IPublicResolver`

Subset of the ENS PublicResolver interface the registrar writes to.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `setAddr(bytes32 node, address a)` | no | Set the canonical EVM-address record for the node |
| `setAddr(bytes32 node, uint256 coinType, bytes a)` | no | Multi-coin address record (SLIP-44 cointypes); used to set Bitcoin / Solana / other-chain addresses |
| `setText(bytes32 node, string key, string value)` | no | Set a text record (avatar, url, email, etc.). BANKON uses this for its custom namespace (`bankon.*`) |
| `setContenthash(bytes32 node, bytes hash)` | no | Set the EIP-1577 contenthash (IPFS CID, Skynet, etc.) |
| `multicall(bytes[] data) → bytes[]` | no | Atomic batch of any of the above |

**Implementers:** External — the canonical ENS PublicResolver. BANKON's own resolver (the concrete `BankonSubnameResolver` — see `IBankonExtensions.IBankonSubnameResolver`) is a subclass that adds Mode-A TBA override on `addr(node)`.
**Callers in bankoneth:** The concrete `Bankon*` registrars (typically via `multicall` to batch initial record setup).

---

### `IBankonPriceOracle`

BANKON price oracle — length-tier USD pricing in USDC base units (6 decimals). Maps a label and a duration in years to a USD-denominated price, and to a token-denominated price.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `priceUSD(string label, uint256 durationYears) → uint256 usd6` | yes | USD price in 6-decimal base units (so $5.00 = `5_000_000`). Pricing typically tiered by `bytes(label).length` (3-char names cost more than 10-char) |
| `priceInToken(string label, uint256 durationYears, address token) → uint256 amount` | yes | Same price expressed in `token`'s base units (USDC → 6dp, USDT → 6dp, PYTHAI → 18dp, etc.). Oracle handles the conversion |

**Implementers in bankoneth:** Concrete `BankonPriceOracle` (in the same tree, not shown here).
**Callers in bankoneth:** `BankonEthRegistrar.quote(...)` and the paid-registration path; `BankonDomainHosting.issue(...)` for parent-share calculations.

---

### `IBankonReputationGate`

Agnostic eligibility surface. Any reputation system can implement this and slot into BANKON's registration flow.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `isEligibleForFree(address agent) → bool` | yes | True iff `agent` qualifies for a free subname (e.g. via BONA FIDE score, ERC-8004 attestation, allowlist) |
| `isEligibleForRegistration(address agent) → bool` | yes | True iff `agent` is allowed to register at all (gate that even paid users can fail) |
| `bonafideScore(address agent) → uint256` | yes | Numeric score for ranking / display. Caller-defined scale; BANKON treats 0 = none, higher = better |

**Implementers in bankoneth:** A concrete BONA FIDE adapter (out of scope of this file) is the canonical implementation; the interface explicitly invites alternatives.
**Callers in bankoneth:** The registrar(s) for free-tier eligibility and registration-gate enforcement.

---

### `IIdentityRegistry8004`

ERC-8004-style identity registry. Hooked optionally by the registrar to bundle agent identity mints with subname registrations.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `register(address agentWallet, string agentURI) → uint256 agentId` | no | Mint a new agent identity record. Returns the assigned `agentId` |
| `setMetadata(uint256 agentId, bytes32 key, bytes value)` | no | Attach typed metadata (capability bitmap, manifest URI, etc.) to an existing agent record |

**Implementers in bankoneth:** A concrete ERC-8004 registry adapter is the canonical implementation. The simpler [`AgentRegistry.sol`](../identity/AgentRegistry.sol) in the identity tree is an aligned-but-distinct ABI (publishes its own `IAgentRegistry` interface).
**Callers in bankoneth:** Optional bundled-mint path in the registrar — if an `IIdentityRegistry8004` is wired, paid subname mints can co-issue an agent identity.

---

### `IBankonPaymentRouter`

BANKON payment router — split + sweep of USDC / PYTHAI / ETH revenue. Sits downstream of the registrar(s) and `X402Receipt` to record receipts and distribute funds per a configured split.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `splitConfigured() → bool` | yes | True iff a revenue split has been set (operator hasn't, no distributions are possible) |
| `recordReceipt(bytes32 receiptHash, uint256 usd6, address asset)` | no | Cascade entrypoint from `X402Receipt.recordX402Receipt`. Records a receipt for downstream split. **Caller must hold `REGISTRAR_ROLE` on the router** (granted post-deploy to the `X402Receipt` contract and the various `Bankon*` registrars) |
| `distribute(address asset, uint256 amount)` | no | Push `amount` of `asset` out per the configured split. Permissioning is the router's responsibility (typically open or operator-only) |

**Implementers in bankoneth:** Concrete `BankonPaymentRouter` (in the same tree).
**Callers in bankoneth:** [`X402Receipt.sol`](../x402/X402Receipt.sol) holds an `IBankonPaymentRouter immutable router` and cascades into `recordReceipt`. The concrete `Bankon*` registrars cascade in the same way for paid subname revenue.

## See also

- [`IBankonExtensions.sol`](./IBankonExtensions.sol) — second-tier interfaces (subname resolver, INFT adapter, X402 attestor, AgenticPlace hook, ETH registrar, domain hosting) built on top of these primitives
- [`X402Receipt.sol`](../x402/X402Receipt.sol) — the canonical caller of `IBankonPaymentRouter.recordReceipt`
- [`AgentRegistry.sol`](../identity/AgentRegistry.sol) — an aligned-but-distinct agent identity ABI (publishes its own `IAgentRegistry`, not `IIdentityRegistry8004`)
- Real ENS contracts the wrapped subsets here mirror: <https://github.com/ensdomains/ens-contracts>
- ERC-8004 (in-flight) — agent identity registry spec
- EIP-1577 — contenthash (used by `IPublicResolver.setContenthash`)
- SLIP-44 — cointypes for `IPublicResolver.setAddr(node, coinType, bytes)`
- ENS NameWrapper fuse model — the cryptographic basis for BANKON subname non-reversibility
