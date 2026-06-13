# SoulBadger

> ERC-5484-style soulbound (non-transferable) ERC-721 badge that stores a richly-typed `UserIdentity` per credential and exposes verification hooks for an AgenticPlace marketplace.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`SoulBadger.sol`](./SoulBadger.sol)

## Role in bankoneth

`SoulBadger` is the second of the three identity primitives re-homed from `DAIO/` into `bankoneth/contracts/identity/`. While `AgentRegistry` records *machine agents* (with capability bitmaps), `SoulBadger` records *human or agent credentials* — RPG-flavoured attributes (`class`, `level`, `health`, `stamina`, `strength`, `intelligence`, `dexterity`) that came from the original DAIO gamified identity model. The badge is permanently bound to its mint recipient via an ERC-5484 transfer-block in `_update`.

In the BANKON ENS stack, a `SoulBadger` badge typically:
1. Witnesses that a wallet has earned a credential (training completed, audit passed, role granted).
2. Optionally links back to an "IDNFT" via `_badgeToTokenId` — letting an external NFT identity reference its badge bundle.
3. Is queried by `IAgenticPlace` marketplace logic via `verifyCredential(user, badgeId)` to gate listings or trade actions.

The contract is deliberately small and unopinionated about credential issuance policy: any address with `BADGE_ISSUER_ROLE` can mint, and once minted the badge is permanent (only mint or burn, never transfer). Issuance policy (who deserves a badge, what stats to assign) lives off-chain in the cognition stack that calls in.

## Inheritance

```
SoulBadger
 ├─ ERC721                    (OZ; base 721 — but ownerOf is overridden)
 └─ AccessControl             (OZ; roles)
        ↓ depends on
   IAgenticPlace              (./interfaces/IAgenticPlace.sol — typed reference, no calls in code)
```

The contract holds an `IAgenticPlace` reference (`agenticPlace`) but does **not** actually call any of its methods inside this source — the binding is informational and exists so external callers can fetch the linked marketplace from a single struct read.

## Constructor

| arg | type | purpose |
| --- | --- | --- |
| `name_` | `string memory` | ERC-721 collection name |
| `symbol_` | `string memory` | ERC-721 symbol |
| `baseBadgeUri_` | `string memory` | Base URI returned by `_baseURI()` — concatenated with tokenId by ERC-721's default `tokenURI` |
| `_agenticPlace` | `address` | Optional `IAgenticPlace` pointer; ignored if `0x0` |

The constructor grants `DEFAULT_ADMIN_ROLE` and `BADGE_ISSUER_ROLE` to `msg.sender` (the deployer). `_nextBadgeId` is initialised to `1` so the first badge is `#1`, not `#0`.

## Storage layout

| slot | type | description |
| --- | --- | --- |
| `BADGE_ISSUER_ROLE` | `bytes32` (public constant) | `keccak256("BADGE_ISSUER_ROLE")` |
| `agenticPlace` | `IAgenticPlace` (public) | Marketplace pointer; mutable via admin |
| `_userIdentities` | `mapping(uint256 => UserIdentity)` (private) | RPG attribute struct per badge |
| `_badgeOwners` | `mapping(uint256 => address)` (private) | **Shadow** of ERC-721 `_owners` — used by the overridden `ownerOf` |
| `_badgeToTokenId` | `mapping(uint256 => uint256)` (private) | Optional link `badgeId → IDNFT tokenId` |
| `_baseBadgeUri` | `string` (private) | Returned by `_baseURI` |
| `_nextBadgeId` | `uint256` (private) | Monotonic badge id, starts at 1 |

The `UserIdentity` struct (8 fields):

| field | type | meaning |
| --- | --- | --- |
| `username` | `string` | Human-readable handle |
| `class` | `string` | RPG class label ("warrior", "mage", "auditor", …) |
| `level` | `uint32` | Progression level |
| `health` | `uint32` | HP stat |
| `stamina` | `uint32` | Stamina stat |
| `strength` | `uint32` | STR stat |
| `intelligence` | `uint32` | INT stat |
| `dexterity` | `uint32` | DEX stat |

## Roles

| Role | keccak256 | Who holds | What they can do |
| --- | --- | --- | --- |
| `DEFAULT_ADMIN_ROLE` | `0x00…00` | Deployer (auto-granted) | Grant/revoke roles; call `setAgenticPlace` |
| `BADGE_ISSUER_ROLE` | `keccak256("BADGE_ISSUER_ROLE")` | Deployer + anyone admin grants | Call `safeMint` to issue new soulbound badges |

## Events

| Event | Emitted when | Indexer / UI use |
| --- | --- | --- |
| `BadgeMinted(uint256 indexed badgeId, address indexed to, uint256 indexed linkedTokenId)` | Inside `safeMint` after state writes | Primary feed for credential UIs; `linkedTokenId` is `0` if the badge is standalone |
| `AgenticPlaceUpdated(address indexed oldPlace, address indexed newPlace)` | `setAgenticPlace` | Marketplace UI must re-read marketplace address on this event |

## Errors

This contract uses string `require` messages, not custom errors:
- `"Nonexistent badge"` — `getUserIdentity` on an unknown badge.
- `"Owner query for nonexistent token"` — `ownerOf` on an unknown badge.
- `"Soulbound: token transfer is BLOCKED"` — `_update` on any non-mint / non-burn move.

## External / public API

### `setAgenticPlace(address _agenticPlace)`
- **Access**: `DEFAULT_ADMIN_ROLE`.
- **Behaviour**: Replaces the marketplace pointer. Accepts `0x0` (which effectively unbinds the marketplace — note this writes a contract with `address(0)` as the stored interface; that is fine for reads but any later call to a method on `agenticPlace` would revert).
- **Emits**: `AgenticPlaceUpdated`.

### `verifyCredential(address user, uint256 badgeId) view → bool`
- **Access**: Open.
- **Behaviour**: Thin wrapper — returns `ownerOf(badgeId) == user`. Reverts via the `ownerOf` override if the badge does not exist (instead of returning `false`).
- **Intended caller**: `IAgenticPlace` listings or any marketplace gate.

### `safeMint(address to, string memory username, string memory class_, uint32 level, uint32 health, uint32 stamina, uint32 strength, uint32 intelligence, uint32 dexterity, uint256 linkedTokenId) → uint256`
- **Access**: `BADGE_ISSUER_ROLE`.
- **Behaviour**: Allocates `badgeId = _nextBadgeId++`, calls `_safeMint`, writes the `UserIdentity` struct, writes `_badgeOwners[badgeId] = to`, conditionally writes `_badgeToTokenId[badgeId] = linkedTokenId` only when `linkedTokenId > 0`.
- **Side effects**: `BadgeMinted(badgeId, to, linkedTokenId)`. May call `onERC721Received` on `to` if it's a contract.

### `getUserIdentity(uint256 badgeId) view → (string, string, uint32, uint32, uint32, uint32, uint32, uint32)`
- Returns the full `UserIdentity` struct as an 8-tuple. Reverts `"Nonexistent badge"` if unknown (checks `_badgeOwners`, not ERC-721 storage).

### `ownerOf(uint256 badgeId) view → address` (override)
- Returns `_badgeOwners[badgeId]` (the shadow map), reverting `"Owner query for nonexistent token"` if `0x0`. This **shadows** the OZ ERC-721 owner storage — see "Known gotchas" below.

### `getLinkedTokenId(uint256 badgeId) view → uint256`
- Returns the linked IDNFT tokenId, or `0` if standalone.

### `supportsInterface(bytes4 interfaceId) view → bool`
- Standard composite for `ERC721` + `AccessControl`.

## Internal helpers

### `_baseURI() view → string`
- Returns `_baseBadgeUri` so the default ERC-721 `tokenURI(badgeId)` resolves to `baseBadgeUri || badgeId`.

### `_update(address to, uint256 tokenId, address auth) → address`
- ERC-5484 transfer block: `require(from == address(0) || to == address(0), "Soulbound: token transfer is BLOCKED")`. Allows mint (`from == 0`) and burn (`to == 0`); blocks everything else. Burning is permitted but no explicit `burn()` is exposed — must go through ERC-721 internal path or a subclass.

## Invariants

1. Badges are **non-transferable** after mint — only mint and burn paths execute through `_update`.
2. First `badgeId` is `1`, never `0`. `_badgeOwners[0] == address(0)` is always true.
3. `_badgeOwners[id]` and the underlying ERC-721 `_owners[id]` are written together on mint but the **public `ownerOf` reads only the shadow map**.
4. `linkedTokenId == 0` means "no linked IDNFT". The mapping value `0` is never a valid link.
5. `verifyCredential(user, id)` is true iff `_badgeOwners[id] == user`.

## Security considerations

- **Two owner sources of truth**: `_badgeOwners` (shadow) and the inherited OZ `_owners` mapping. The override means external `ownerOf` calls always read the shadow, but OZ's internal `_ownerOf` (used by `_update`, `_isAuthorized`, etc.) reads the real OZ storage. They are kept in sync only through `_safeMint`'s OZ writes and the post-mint manual `_badgeOwners[badgeId] = to`. **Burn does not clear `_badgeOwners`** — after a burn, `ownerOf(badgeId)` would still return the pre-burn owner. This is a state-divergence hazard.
- **No burn function exposed**: ERC-721 internal `_burn` is reachable only via subclass. The contract is effectively mint-only as deployed. If a future subclass adds burn, the `_badgeOwners` shadow must be cleared in lockstep.
- **No fuses on issuance**: any `BADGE_ISSUER_ROLE` holder may mint any `UserIdentity` to any address with any `linkedTokenId`. There is no on-chain check that `linkedTokenId` exists in any external contract.
- **No mass / per-token revocation**: there is no admin escape hatch to clawback a misissued badge short of burning (which isn't exposed).
- **`agenticPlace` set to `0x0`**: the setter accepts the zero address. Any code that subsequently calls a method on `agenticPlace` would revert. Today nothing does.
- **String error messages cost more gas**: legacy DAIO-era pattern. Custom errors would be cheaper.
- **No `uint256 linkedTokenId` validation**: arbitrary numbers can be written. Off-chain consumers should treat them as advisory only.

## Integration patterns

**Issuance from a credential-issuing agent (off-chain authority):**
```solidity
soulBadger.safeMint(
    candidate,
    "alice",
    "auditor",
    /* level */ 5,
    /* health */ 100, /* stamina */ 80,
    /* strength */ 40, /* intelligence */ 90, /* dexterity */ 60,
    /* linkedTokenId */ idnftTokenId
);
```

**Marketplace gate inside an AgenticPlace listing:**
```solidity
require(
    soulBadger.verifyCredential(msg.sender, requiredBadgeId),
    "missing credential"
);
```

**Wiring the marketplace after deploy:**
```solidity
soulBadger.setAgenticPlace(address(agenticPlace));
```

## Known gotchas

- **`ownerOf` divergence after burn**: there is no override of `_burn` or `_update` to clear `_badgeOwners`. If a subclass burns, the shadow stays stale. Today no burn path is exposed, but any subclass adding one must also `delete _badgeOwners[id]`.
- **`_badgeToTokenId[badgeId] = 0` is the sentinel for "no link"** — clients must not interpret `0` as "linked to IDNFT #0".
- **The contract holds a typed `IAgenticPlace`** but never calls into it from this source. It's a read-only handle.
- **No `_userIdentities` setter**: badge stats are immutable after mint. Level-ups, stat changes, etc. must be modelled off-chain or via a subclass.
- **`safeMint`'s 11-argument calldata is brittle**. Wrap in a helper at the integration layer.
- **String `require` messages**: search by string in revert reasons, not by selector.

## See also

- [`IAgenticPlace.sol`](./interfaces/IAgenticPlace.sol) — the marketplace interface this contract holds a reference to
- [`AgentRegistry.sol`](./AgentRegistry.sol) — sibling agent identity registry (machine-side, capability-based)
- ERC-5484 — Consensual Soulbound Tokens spec
- Legacy `DAIO/contracts/identity/SoulBadger.sol` — predecessor (now re-homed here)
