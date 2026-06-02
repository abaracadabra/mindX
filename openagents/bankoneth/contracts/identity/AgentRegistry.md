# AgentRegistry

> Agnostic ERC-8004-aligned agent identity & capability registry that mints an ERC-721 per registered agent, tracks an off-chain-interpreted capability bitmap, and accumulates EIP-712-signed attestations.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`AgentRegistry.sol`](./AgentRegistry.sol)

## Role in bankoneth

`AgentRegistry` is one of the three identity primitives re-homed from the legacy `DAIO/` contract tree into `bankoneth/contracts/identity/`. In the BANKON ENS stack it sits **above the BANKON subname (the `.bankon` issuance) and below the cognition layer**: the BANKON registrar (or any other minter — `iNFT_7857`, `IDManagerAgent`, AgenticPlace, etc.) calls `register()` to bind a human-readable `agentId` to (a) an on-chain owner, (b) an optional linked `iNFT_7857` agent token, and (c) a capability bitmap that off-chain stacks (mindX, AgenticPlace) interpret however they like.

The registry is **deliberately agnostic** (per the explicit @notice header): it makes no assumption that mindX, AgenticPlace, BANKON, or any specific cognition framework is consuming it. Anyone implementing the public `IAgentRegistry` ABI is a peer. The registry itself only enforces uniqueness of `agentId` (via `keccak256` hash), role-gated minting, and EIP-712 attestation provenance.

Because BANKON subnames are themselves soulbound, the BANKON registrar typically sets `soulbound = true` on bundled agent mints. Standalone callers (e.g. an agent registering itself) leave the token transferable by default. Soulbound enforcement lives in the `_update` override.

## Inheritance

```
AgentRegistry
 ├─ ERC721                                  (OZ; base 721)
 ├─ ERC721URIStorage                        (OZ; per-token URI mapping)
 ├─ AccessControl                           (OZ; roles)
 ├─ EIP712                                  (OZ; typed-data domain)
 └─ IAgentRegistry                          (defined inline)
```

The `IAgentRegistry` interface is published from this same source file (lines 13-40) so external integrators can import it without pulling the implementation. Its `interfaceId` is exposed as the constant `IAGENT_REGISTRY_ID`.

## Constructor

| arg | type | purpose |
| --- | --- | --- |
| `name_` | `string memory` | ERC-721 collection name; also the EIP-712 domain name |
| `symbol_` | `string memory` | ERC-721 symbol |
| `admin` | `address` | Receives `DEFAULT_ADMIN_ROLE`. Reverts with `ZeroAddress` if `0x0` |

EIP-712 domain version is hard-coded to `"1"`. `MINTER_ROLE` and `ATTESTOR_ROLE` are NOT pre-granted — admin must `grantRole()` them post-deploy.

## Storage layout

| slot purpose | type | description |
| --- | --- | --- |
| `_agents` | `mapping(uint256 => Agent)` | Primary record per `agentTokenId` |
| `tokenOfAgentIdHash` | `mapping(bytes32 => uint256)` (public) | `keccak256(bytes(agentId)) → tokenId`. `0` means free |
| `attestNonce` | `mapping(uint256 => uint256)` (public) | Per-token EIP-712 nonce, incremented on each `attest()` |
| `_attested` | `mapping(uint256 => mapping(address => bool))` | Tracks which attestor addresses have already counted for a token |
| `_nextId` | `uint256` (private) | Monotonic id; `++` then assign means first tokenId is `1`, never `0` |

The `Agent` struct (private, accessed via getters):

| field | type | meaning |
| --- | --- | --- |
| `owner` | `address` | The original owner recorded at registration. **Note**: `getAgent` returns the *current* `_ownerOf(tokenId)`, not this field. This field is the historical mint-time owner. |
| `agentId` | `string` | Human-readable id, ≤ 64 bytes |
| `agentIdHash` | `bytes32` | `keccak256(bytes(agentId))` — indexer key |
| `linkedINFT_7857` | `address` | Optional pointer at a companion `iNFT_7857` contract; `0x0` if none |
| `capabilityBitmap` | `bytes32` | Opaque to the contract; off-chain interpretation |
| `attestationURI` | `string` | URI of the **most recent** attestation only |
| `attestorCount` | `uint256` | Number of distinct addresses that have ever attested |
| `soulbound` | `bool` | If true, `_update` reverts on non-mint / non-burn transfers |

## Roles

| Role | keccak256 | Who holds | What they can do |
| --- | --- | --- | --- |
| `DEFAULT_ADMIN_ROLE` | `0x00…00` (OZ default) | `admin` from constructor | Grant/revoke all roles; call `setSoulbound` |
| `MINTER_ROLE` | `keccak256("MINTER_ROLE")` | BANKON registrar, `iNFT_7857`, `IDManagerAgent` post-deploy | Call `register()` on behalf of another owner; call `setLinkedINFT()` for any token |
| `ATTESTOR_ROLE` | `keccak256("ATTESTOR_ROLE")` | Off-chain reputation oracles, audit signers | Their ECDSA signatures over the `Attestation` EIP-712 struct are accepted by `attest()` |

Note: `MINTER_ROLE` is **not** required for self-registration — any caller may `register()` themselves as `owner` (i.e. `msg.sender == owner`). The role only matters for cross-account mints.

## Events

| Event | Emitted when | Indexer / UI use |
| --- | --- | --- |
| `AgentRegistered(uint256 indexed agentTokenId, address indexed owner, bytes32 indexed agentIdHash, string agentId, address linkedINFT_7857, bytes32 capabilityBitmap, string attestationURI)` | Inside `register()` after mint | Primary feed for agent directory UIs; three indexed params allow filtering by id, owner, or name-hash |
| `CapabilitiesUpdated(uint256 indexed agentTokenId, bytes32 newBitmap)` | `setCapabilities()` | Capability change feed; off-chain consumers must re-resolve bitmap meaning |
| `Attested(uint256 indexed agentTokenId, address indexed attestor, string attestationURI, uint256 attestorCount)` | Successful `attest()` (signature recovered to an `ATTESTOR_ROLE` holder) | Reputation feed; `attestorCount` is post-increment |
| `SoulboundSet(uint256 indexed agentTokenId, bool soulbound)` | `setSoulbound()` (admin only) | Marketplace badges should respect this — non-transferable tokens cannot be listed |
| `LinkedINFTSet(uint256 indexed agentTokenId, address indexed inft)` | `setLinkedINFT()` | Cross-link UI between agent identity and intelligence payload (`iNFT_7857`) |

## Errors

| Error | When reverted |
| --- | --- |
| `ZeroAddress()` | Admin or owner is `address(0)` |
| `EmptyAgentId()` | `agentId.length == 0` |
| `AgentIdTooLong(uint256 len)` | `agentId.length > 64` |
| `AgentIdAlreadyTaken(bytes32 hash)` | The hash already maps to a tokenId |
| `TokenDoesNotExist(uint256 agentTokenId)` | Operations on a tokenId whose `_agents[id].owner` is `0x0` |
| `NotOwnerNorMinter(address caller)` | Caller is neither the token's current owner nor holder of `MINTER_ROLE` (used by `register`, `setCapabilities`, `setLinkedINFT`) |
| `NotAttestor(address caller)` | The address recovered from the EIP-712 signature does not hold `ATTESTOR_ROLE` |
| `BadAttestationSignature()` | Declared but not used in the current code path; `ECDSA.recover` itself reverts on malformed sigs |
| `SoulboundCannotTransfer()` | `_update` blocking a non-mint / non-burn transfer on a soulbound token |

## External / public API

### `register(address owner, string calldata agentId, address linkedINFT_7857, bytes32 capabilityBitmap, string calldata attestationURI) → uint256 agentTokenId`
- **Access**: `msg.sender == owner` OR `hasRole(MINTER_ROLE, msg.sender)`.
- **Behaviour**: Validates `owner != 0`, `0 < agentId.length ≤ 64`, `agentId` unused. Allocates new `tokenId = ++_nextId`, fills the `Agent` struct (`soulbound=false` by default), records hash→id mapping, `_safeMint`s to `owner`.
- **Returns**: New `agentTokenId`.
- **Side effects**: Emits `AgentRegistered`; may invoke `onERC721Received` on `owner` if it's a contract.

### `setCapabilities(uint256 agentTokenId, bytes32 newBitmap)`
- **Access**: Current token owner only (`_ownerOf(agentTokenId) == msg.sender`). Note `MINTER_ROLE` is NOT a fallback here despite the `NotOwnerNorMinter` error name.
- **Behaviour**: Overwrites `capabilityBitmap`. Bitmap meaning is off-chain.

### `setLinkedINFT(uint256 agentTokenId, address inft)`
- **Access**: Current token owner OR `MINTER_ROLE`.
- **Behaviour**: Sets the linked `iNFT_7857` address (may be `0x0` to clear). Accepts any address — no interface check.

### `setSoulbound(uint256 agentTokenId, bool isSoulbound)`
- **Access**: `DEFAULT_ADMIN_ROLE` only.
- **Behaviour**: Flips the per-token soulbound flag. Active immediately on the next `_update` call.

### `attest(uint256 agentTokenId, string calldata attestationURI, bytes calldata signature)`
- **Access**: Open — but the signature must recover to an `ATTESTOR_ROLE` holder.
- **Behaviour**: Reads and increments `attestNonce[agentTokenId]`. Builds the EIP-712 digest over `(ATTESTATION_TYPEHASH, agentTokenId, keccak256(attestationURI), nonce)`. Recovers the signer. If signer ∈ `ATTESTOR_ROLE`, sets `_attested[id][signer] = true` (only once-counted), overwrites `attestationURI` with the new one, increments `attestorCount` on first attestation by this signer.
- **Side effects**: Emits `Attested(id, attestor, uri, attestorCount)`.

### `attestationDigest(uint256 agentTokenId, string calldata attestationURI, uint256 nonce) view → bytes32`
- Helper to compute the EIP-712 digest a signer would need to produce. Pure read; does not consume nonces.

### `getAgent(uint256 agentTokenId) view → (address owner, string agentId, address linkedINFT_7857, bytes32 capabilityBitmap, string attestationURI, uint256 attestorCount)`
- Returns the *current* `_ownerOf(tokenId)` (not the historical mint owner stored in `Agent.owner`). Reverts `TokenDoesNotExist` if unknown.

### `isSoulbound(uint256 agentTokenId) view → bool`
- Per-token soulbound flag.

### `totalAgents() view → uint256`
- Equal to `_nextId`. Note this does not decrement on burn — it's a strictly monotonic mint counter.

### `tokenURI(uint256 tokenId) view → string`
- Standard `ERC721URIStorage` resolution.

### `supportsInterface(bytes4 interfaceId) view → bool`
- True for `IAGENT_REGISTRY_ID` plus all inherited interfaces (`IERC721`, `IERC721Metadata`, `IAccessControl`, etc.).

## Internal helpers

### `_update(address to, uint256 tokenId, address auth) → address`
- Override that adds the soulbound gate: when `from != 0 && to != 0 && _agents[tokenId].soulbound`, revert `SoulboundCannotTransfer`. Otherwise defer to `super._update`.

## Invariants

1. `agentTokenId == 0` is reserved (`_nextId` starts at 0 and pre-increments). Code uses `0` as the "not found" sentinel in `tokenOfAgentIdHash`.
2. `keccak256(bytes(agentId))` → `tokenId` is bijective for the live set; the reverse `tokenId → agentId` lives in `_agents[id].agentId`.
3. `attestorCount` is monotonic per token. It tracks **distinct** attestors, not total attestations — re-attestation by the same signer updates `attestationURI` and `attestNonce` but does not bump `attestorCount`.
4. The contract stores only the **most recent** attestation URI. Historical attestations live in the event log.
5. The historical mint owner (`Agent.owner`) and the current ERC-721 owner can diverge after a transfer; `getAgent` returns the live ERC-721 owner, but `Agent.owner` retains the mint-time owner.

## Security considerations

- **MINTER_ROLE trust**: holders may mint agents under any `owner` address with any `agentId`. Compromised minter ⇒ identity squatting. Issue narrowly and audit grantees.
- **ATTESTOR_ROLE replay**: nonces are scoped to `(agentTokenId)` and incremented before signature recovery, so a signed message cannot be replayed against the same token. It also cannot be replayed against a different token because `agentTokenId` is in the typed data. Cross-chain replay is blocked by the EIP-712 domain separator (which mixes in `chainid`).
- **Soulbound oversight**: only `DEFAULT_ADMIN_ROLE` can toggle. There is no per-owner self-soulbinding. If the admin key is compromised, an attacker can mass-unbind tokens.
- **No `onlyAttestor` modifier**: any caller may submit an attestation as long as the recovered signer is authorized. This means a third party can post an attestor's signature on their behalf (front-running risk for attestor-controlled UX).
- **`BadAttestationSignature` is dead code**: `ECDSA.recover` itself reverts with its own `ECDSAInvalidSignature*` errors before this can fire. Cosmetic.
- **Capability bitmap is unconstrained**: zero on-chain semantics. Mis-set bitmaps don't break the contract but can mislead off-chain consumers.
- **No burn function**: tokens can never be destroyed. A misregistered `agentId` is permanently squatted.

## Integration patterns

**BANKON-driven bundled mint (soulbound):**
```solidity
// Inside the BANKON registrar after a paid subname mint:
uint256 agentTokenId = agentRegistry.register(
    subnameOwner,
    "myagent",
    address(inft7857),                  // linked intelligence payload
    capabilityBitmap,
    attestationURI
);
agentRegistry.setSoulbound(agentTokenId, true);  // requires DEFAULT_ADMIN_ROLE on registry
```

**Self-registration (transferable by default):**
```solidity
agentRegistry.register(
    msg.sender,
    "freelance-agent",
    address(0),
    0,
    ""
);
```

**Off-chain attestation signing (TypeScript pseudo):**
```ts
const digest = await registry.attestationDigest(tokenId, uri, await registry.attestNonce(tokenId));
const sig = await attestorWallet.signMessage(getBytes(digest));  // EIP-712 raw digest
await registry.attest(tokenId, uri, sig);
```

## Known gotchas

- **First tokenId is `1`, not `0`**. Don't store `0` as a meaningful agent id in client code.
- **`setCapabilities` is owner-only**, despite the error message `NotOwnerNorMinter`. `MINTER_ROLE` does not give you capability-edit rights — only the current ERC-721 owner.
- **`attestationURI` is mutable** — every `attest()` overwrites it. If you need an immutable history, index `Attested` events off-chain.
- **`Agent.owner` is stale after transfer**. Read `_ownerOf(tokenId)` or use `getAgent` for the live owner.
- **`totalAgents` is mint-only**, doesn't reflect burns (and there are no burns anyway).
- **No `tokenURI` setter** is exposed in the public ABI of this contract. ERC721URIStorage's `_setTokenURI` is internal. Operators wanting per-token URIs must either subclass or rely on `attestationURI` instead.

## See also

- [`SoulBadger.sol`](./SoulBadger.sol) — ERC-5484 soulbound credential badges (paired identity primitive)
- [`iNFT_7857.sol`](../inft/iNFT_7857.sol) — the intelligence payload pointed at by `linkedINFT_7857`
- [`IBankon.sol`](../interfaces/IBankon.sol) — `IIdentityRegistry8004` (a more elaborate identity surface that wraps this)
- ERC-8004 (in-flight) — the spec this registry is "aligned with" without claiming compliance
