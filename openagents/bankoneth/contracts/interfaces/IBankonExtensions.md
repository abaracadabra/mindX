# IBankonExtensions

> Second-tier interface bundle for the bankoneth contracts that live alongside the four re-homed BANKON v1 core contracts — Subname Resolver, INFT Adapter, X402 Attestor, AgenticPlace Hook, ETH Registrar, Domain Hosting.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`IBankonExtensions.sol`](./IBankonExtensions.sol)

## Role in bankoneth

`IBankonExtensions.sol` is the **second-tier ABI bundle** that sits on top of the foundational ENS + BANKON primitives in [`IBankon.sol`](./IBankon.sol). Where `IBankon.sol` exposes the ENS wrapping primitives and the BANKON oracle/reputation/router primitives, this file exposes the *user-facing flow* contracts:

| Interface | What it does | Lives in flow |
| --- | --- | --- |
| `IBankonSubnameResolver` | Resolves `<label>.bankon` to addresses + text records; iNFT Mode-A TBA override on `addr(node)` | All flows |
| `IBankonInftAdapter` | ERC-1155 receiver for the subname; emits cross-chain RequestINFTMint event picked up by 0G-side worker; tracks `(labelhash → 0G iNFT tokenId)` | Mode A |
| `IBankonX402Attestor` | EIP-712 facilitator-key registry + nonce replay guard for x402 receipts from the GoPlausible Algorand facilitator | All flows (paid mints) |
| `IBankonAgenticPlaceHook` | Per-mint listing emitter — off-chain indexer creates marketplace cards | All flows (optional) |
| `IBankonEthRegistrar` | Flow B — wraps canonical ENS ETHRegistrarController commit-reveal flow for `<newdomain>.eth` sales | Flow B |
| `IBankonDomainHosting` | Flow C — subdomain-minting-as-a-service for external `.eth` holders who enroll their parent | Flow C |

The "three flows" model the file alludes to:
- **Flow A**: `<label>.bankon` subname issuance under the canonical BANKON parent, with Mode-A iNFT binding cross-chain to 0G.
- **Flow B**: end-to-end `<newdomain>.eth` purchase through bankoneth (uses canonical ENS ETHRegistrarController under the hood).
- **Flow C**: subname-issuance-as-a-service for external `.eth` parents enrolled in bankoneth.

All four "BANKON v1 core" contracts re-homed into this tree implement at least one of these interfaces. The X402 Attestor in this file is distinct from [`X402Receipt.sol`](../x402/X402Receipt.sol) — the attestor here is the GoPlausible Algorand-facilitator EIP-712 verifier; the X402Receipt is the standalone EVM-payer-signed receipt path. Both can be wired into the BankonPaymentRouter.

## Interfaces defined

### `IBankonSubnameResolver`

`PublicResolver` subclass surface with the BANKON text-record namespace and the iNFT-Mode-A TBA override on `addr(node)`. The override is the trick that makes the **Token-Bound Account** (TBA) of a 0G-side iNFT resolve as the address for the matching ENS subname.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `addr(bytes32 node) → address` | yes | ENS-standard address resolution. **Override behaviour**: when the node has an iNFT binding, returns the TBA address rather than the underlying record |
| `text(bytes32 node, string key) → string` | yes | ENS-standard text-record resolution; BANKON adds the `bankon.*` namespace (e.g. `bankon.agent_id`, `bankon.thot_root`) |
| `setAddr(bytes32 node, address a)` | no | Set the underlying address record (subject to BANKON's setter permissions) |
| `setText(bytes32 node, string key, string value)` | no | Set a text record (BANKON namespace) |
| `setINFTBinding(bytes32 node, address tbaAddress, uint256 zeroGTokenId)` | no | **BANKON-specific**: bind the node to a 0G-side iNFT token + its TBA. After this call, `addr(node)` returns `tbaAddress`. `zeroGTokenId` is the iNFT_7857 tokenId on 0G |

**Defined events:** None on the interface (concrete implementation expected to emit).
**Defined structs:** None.
**Implementers:** Concrete `BankonSubnameResolver` (in this tree).
**Callers:** ENS clients (read-only); the registrar(s) and `BankonInftAdapter` (write).

---

### `IBankonInftAdapter`

Mode A glue. Receives the ERC-1155 subname from `NameWrapper`, emits a `RequestINFTMint` event that an off-chain 0G-side worker picks up and acts on, then maintains a registry mapping `(ensLabelhash → 0G iNFT tokenId)` populated by operator-attested `WireCrossChain.registerINFTTokenId()` calls.

**Defined events:**

| Event | Signature | When emitted |
| --- | --- | --- |
| `RequestINFTMint` | `(bytes32 indexed parentNode, bytes32 indexed labelhash, address indexed claimant, uint256 erc1155TokenId, string metadataURI)` | Inside `requestMint` after the adapter receives the wrapped subname and is ready for the 0G worker to mint the corresponding iNFT |
| `INFTBound` | `(bytes32 indexed labelhash, uint256 indexed zeroGTokenId, address indexed tbaAddress)` | After the 0G-side worker mints the iNFT and the operator calls `registerZeroGTokenId` (via the WireCrossChain operator path) |

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `requestMint(bytes32 parentNode, bytes32 labelhash, address claimant, uint256 erc1155TokenId, string metadataURI)` | no | Kick off cross-chain iNFT mint. Emits `RequestINFTMint`. Typically called by the registrar immediately after subname mint |
| `registerZeroGTokenId(bytes32 labelhash, uint256 zeroGTokenId)` | no | Operator-attested binding of an issued 0G tokenId back to the EVM labelhash. Permissioned in the concrete implementation |
| `zeroGTokenIdOf(bytes32 labelhash) → uint256` | yes | Reverse lookup |
| `tbaAddressOf(bytes32 labelhash) → address` | yes | Returns the Token-Bound Account address of the bound iNFT (the address `BankonSubnameResolver.addr(node)` resolves to) |

**Defined structs:** None.
**Implementers:** Concrete `BankonInftAdapter` (in this tree).
**Callers:** The registrar (emits `requestMint`); `BankonSubnameResolver` (reads `tbaAddressOf` for the addr-override).

---

### `IBankonX402Attestor`

EIP-712 facilitator-key registry + nonce replay guard for x402 receipts coming from the **GoPlausible Algorand facilitator**. Distinct from the EVM-payer-signed [`X402Receipt.sol`](../x402/X402Receipt.sol) — that one verifies an EVM payer signature; this one verifies a facilitator signature, where the facilitator is the Algorand-side party that already settled the USDC payment off-EVM.

**Defined structs:**

`X402Receipt` (note: same name as the standalone contract, but **different fields and purpose** — this is the in-memory struct passed to `verify`, not the canonical receipt):

| field | type | meaning |
| --- | --- | --- |
| `receiptHash` | `bytes32` | Hash returned by the Algorand facilitator (cross-chain join key) |
| `claimant` | `address` | EVM-side beneficiary of the settlement |
| `usd6` | `uint256` | USDC base units (6 decimals) |
| `nonce` | `uint64` | Monotonic per facilitator key |
| `expiresAt` | `uint64` | Unix seconds — verify rejects expired receipts |
| `signature` | `bytes` | EIP-712 signature by the registered facilitator key |

**Defined events:**

| Event | Signature | When emitted |
| --- | --- | --- |
| `FacilitatorRegistered` | `(address indexed facilitator, bool active)` | `setFacilitator` |
| `ReceiptConsumed` | `(bytes32 indexed receiptHash, address indexed claimant, uint64 nonce)` | Inside `verify` on success — single-use receipt is now spent |

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `setFacilitator(address facilitator, bool active)` | no | Operator-gated. Add (`active=true`) or remove (`active=false`) a trusted facilitator key |
| `verify(X402Receipt calldata r) → bool` | no | Verify the EIP-712 signature against an active facilitator, check expiry, check nonce, mark `receiptHash` as spent, emit `ReceiptConsumed`. Returns `true` on success, reverts on any failure |
| `isReceiptSpent(bytes32 receiptHash) → bool` | yes | Anti-replay lookup |

**Implementers:** Concrete `BankonX402Attestor` (in this tree).
**Callers:** Paid-mint paths (the registrar(s) and `BankonEthRegistrar.reveal`, `BankonDomainHosting.issue`) when the payment came via the Algorand facilitator rather than direct EVM payer signature.

---

### `IBankonAgenticPlaceHook`

Optional per-mint listing emitter. An off-chain indexer on `agenticplace.pythai.net` consumes the event and creates the marketplace card. **This is purely an event-emitter** — no actual marketplace state is written on this chain.

**Defined events:**

| Event | Signature | When emitted |
| --- | --- | --- |
| `AgenticPlaceListing` | `(bytes32 indexed parentNode, bytes32 indexed labelhash, address indexed tbaAddress, uint256 zeroGTokenId, string metadataURI, address author)` | Inside `list` |

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `list(bytes32 parentNode, bytes32 labelhash, address tbaAddress, uint256 zeroGTokenId, string metadataURI, address author)` | no | Emit `AgenticPlaceListing`. Typically invoked by the registrar immediately after a successful Mode-A bind |
| `setWebhookURL(string url)` | no | Operator-gated. The hook stores a URL that the off-chain indexer can read so the integration is self-describing |
| `webhookURL() → string` | yes | Read accessor |

**Defined structs:** None.
**Implementers:** Concrete `BankonAgenticPlaceHook` (in this tree).
**Callers:** Optional cascade from the registrar(s); off-chain indexer (reads `webhookURL`).

---

### `IBankonEthRegistrar`

Flow B. Wraps the canonical ENS `ETHRegistrarController` commit-reveal flow so customers buy `<newdomain>.eth` end-to-end through bankoneth.

**Defined structs:**

`CommitParams`:

| field | type | meaning |
| --- | --- | --- |
| `label` | `string` | Subdomain label without the `.eth` (`"newdomain"`, not `"newdomain.eth"`) |
| `owner` | `address` | Who receives the registered name |
| `durationYears` | `uint256` | Registration duration |
| `secret` | `bytes32` | Server-managed deterministic salt — re-derivable from `(label, owner, durationYears, server-secret)` so the reveal step can reconstruct it |
| `resolver` | `address` | Initial resolver (typically the `BankonSubnameResolver`) |
| `reverseRecord` | `bool` | Whether to set the reverse record (`owner → label.eth`) atomically |
| `ownerControlledFuses` | `uint16` | Initial owner-controlled fuses to burn on commit; passed through to NameWrapper |

**Defined events:**

| Event | Signature | When emitted |
| --- | --- | --- |
| `Committed` | `(bytes32 indexed commitment, address indexed payer, address indexed owner)` | Inside `commit` |
| `Registered` | `(string label, address indexed owner, uint256 cost, address asset)` | Inside `reveal` after the underlying ETHRegistrarController call succeeds. `asset` is the settlement asset (`0x0` for ETH, USDC/PYTHAI address otherwise) |

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `commit(CommitParams p) → bytes32 commitment` | no | First half of the ENS commit-reveal. Computes and stores the commitment. Emits `Committed` |
| `reveal(CommitParams p, bytes payment) payable` | no | Second half. After the ENS reveal-wait (typically 60s), this function settles the payment (via `payment` — either inline transferWithAuthorization data or an x402 receipt) and calls the underlying ETHRegistrarController to mint. Emits `Registered` |
| `quote(string label, uint256 durationYears) → (uint256 wei_, uint256 usd6)` | yes | Price quote: returns both the ETH-denominated cost and the USDC-base-units cost |

**Implementers:** Concrete `BankonEthRegistrar` (in this tree).
**Callers:** End-users via the bankoneth frontend; the `BankonPaymentRouter` is downstream of revenue.

---

### `IBankonDomainHosting`

Flow C. Subdomain-minting-as-a-service. External `.eth` holders **enroll** their domain (wrapping if needed, **burning `CANNOT_UNWRAP` for the parent-lock requirement**) and bankoneth issues subnames under their parent on demand, splitting revenue with the parent owner.

**Defined structs:**

`EnrolledParent`:

| field | type | meaning |
| --- | --- | --- |
| `parentOwner` | `address` | The `.eth` owner who enrolled |
| `pricePerLabel6` | `uint256` | Per-subname price in USDC base units (6 dp) |
| `childFuses` | `uint16` | Fuses applied to every issued subname (typically including `CANNOT_UNWRAP` to make the subname permanent) |
| `defaultExpiry` | `uint64` | Unix seconds for newly minted children |
| `ownerShareBps` | `uint16` | Basis points of revenue routed to `parentOwner` (`10000` = 100%, `5000` = 50%) |
| `active` | `bool` | Enrollment flag; `disenroll` flips to false but preserves the struct |

**Defined events:**

| Event | Signature | When emitted |
| --- | --- | --- |
| `ParentEnrolled` | `(bytes32 indexed parentNode, address indexed parentOwner, uint16 ownerShareBps)` | `enroll` |
| `SubnameIssued` | `(bytes32 indexed parentNode, string label, address indexed owner)` | `issue` |

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `enroll(bytes32 parentNode, uint256 pricePerLabel6, uint16 childFuses, uint64 defaultExpiry, uint16 ownerShareBps)` | no | Parent owner calls to enroll their wrapped `.eth` into bankoneth's hosting service. The parent must have `CANNOT_UNWRAP` burned before this works (so subnames can be permanently locked); the enrollment doesn't burn this fuse itself, just requires it |
| `disenroll(bytes32 parentNode)` | no | Parent owner stops new issuance. Existing issued subnames are unaffected |
| `issue(bytes32 parentNode, string label, address owner, bytes payment) payable → bytes32 subnameNode` | no | End-user buys a subname under an enrolled parent. Settles payment (per `payment`), splits revenue, calls NameWrapper.setSubnodeOwner with the parent's preconfigured `childFuses` + `defaultExpiry`. Emits `SubnameIssued` |
| `parentOf(bytes32 parentNode) → EnrolledParent` | yes | Read accessor |

**Implementers:** Concrete `BankonDomainHosting` (in this tree).
**Callers:** Parent `.eth` owners (`enroll` / `disenroll`); end-users (`issue`); the `BankonPaymentRouter` is downstream of revenue.

## See also

- [`IBankon.sol`](./IBankon.sol) — first-tier interfaces these depend on (`INameWrapper`, `IPublicResolver`, `IBankonPriceOracle`, `IBankonReputationGate`, `IIdentityRegistry8004`, `IBankonPaymentRouter`)
- [`X402Receipt.sol`](../x402/X402Receipt.sol) — the EVM-payer-signed counterpart to `IBankonX402Attestor`. Both can be wired downstream of the same `BankonPaymentRouter`
- [`iNFT_7857.sol`](../inft/iNFT_7857.sol) — the 0G-side intelligence token that `IBankonInftAdapter` cross-chain references (`zeroGTokenId`)
- [`AgentRegistry.sol`](../identity/AgentRegistry.sol) — alternative ABI to `IIdentityRegistry8004` for agent identity
- [`IAgenticPlace.sol`](../identity/interfaces/IAgenticPlace.sol) — the foundational marketplace ABI that `IBankonAgenticPlaceHook` event consumers ultimately feed
- ENS `ETHRegistrarController` — underlying contract `BankonEthRegistrar` wraps
- ENS `NameWrapper` fuses (`CANNOT_UNWRAP`, `CANNOT_BURN_FUSES`) — the cryptographic basis for the parent-lock requirement in `IBankonDomainHosting`
- ERC-6551 (Token-Bound Account) — the basis for the TBA override in `IBankonSubnameResolver`
- GoPlausible facilitator (Algorand) — the off-chain x402 settlement counterparty `IBankonX402Attestor` verifies
