# IAgenticPlace

> Foundational ABI for the AgenticPlace skill / NFT marketplace — the surface that iNFT, dNFT, agent-NFT and generic ERC-721 sellers and hirers transact against.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`IAgenticPlace.sol`](./IAgenticPlace.sol)

## Role in bankoneth

`IAgenticPlace` is the externally-typed marketplace ABI that the BANKON / mindX identity stack depends on without depending on a concrete implementation. The concrete `AgenticPlace` contract lives elsewhere in the wider deployment (the on-chain projection of `agenticplace.pythai.net`), but bankoneth holds only the interface so:

- **`SoulBadger`** can store an `IAgenticPlace` pointer (`agenticPlace`) and let off-chain UIs read which marketplace this badge collection is bound to.
- **`iNFT_7857`** can emit `AgenticPlaceListed(tokenId, marketplace, …)` and store `agenticPlaceFor[tokenId]` without circular imports.
- Any future marketplace can be swapped in by deploying a fresh implementation against the same ABI — bankoneth contracts remain agnostic.

Importantly, the bankoneth interface here is the *foundational* surface (offerSkill, hireSkillETH, hireSkillERC20, getSkillOffer, whitelist helpers). The richer `IBankonAgenticPlaceHook` in [`../../interfaces/IBankonExtensions.sol`](../../interfaces/IBankonExtensions.sol) is a separate **per-mint listing emitter** built on top of this primitive.

## Interfaces defined

### `IAgenticPlace`

One ABI bundle covering: listing creation (`offerSkill`), purchase paths in ETH and ERC-20 (`hireSkillETH`, `hireSkillERC20`), read accessors, and a whitelist for opt-in NFT contracts.

**Defined enums:**

| `NFTType` value | meaning |
| --- | --- |
| `NFRLT` | NFT Royalty Token — the original DAIO royalty-bearing token kind |
| `THOT` | Transferable Hyper-Optimized Tensor — model-weight bound token |
| `AgentNFT` | AgentFactory-minted agent NFT |
| `ERC721` | Generic ERC-721 — covers iNFT, dNFT and anything else 721-compatible |

`NFTType` lets the marketplace dispatch type-specific logic (e.g. THOT verification, AgentNFT capability checks) without per-contract bespoke code.

**Defined structs:**

`SkillOffer`:

| field | type | meaning |
| --- | --- | --- |
| `skillTokenId` | `uint256` | The NFT being offered |
| `nftType` | `NFTType` | Dispatch tag — which logic path to take on hire |
| `nftContract` | `address` | The NFT contract holding the token |
| `price` | `uint256` | Listing price; semantics depend on `isETH` |
| `isETH` | `bool` | `true` ⇒ `price` is wei; `false` ⇒ base units of `paymentToken` |
| `paymentToken` | `address` | ERC-20 used when `!isETH` (`address(0)` when `isETH`) |
| `owner` | `address` | Seller; receives the payout (minus royalty / protocol fee) |
| `isActive` | `bool` | Listing flag; false after a successful hire or cancel |
| `createdAt` | `uint40` | Listing timestamp (`uint40` ~= year 36000 safe) |
| `expiresAt` | `uint40` | Listing expiry; 0 = no expiry by convention (impl-dependent) |

**Defined events:**

| Event | Signature | When emitted |
| --- | --- | --- |
| `SkillOffered` | `(uint256 indexed skillTokenId, address indexed nftContract, NFTType nftType, uint256 price, bool isETH, address paymentToken, address indexed owner, uint40 expiresAt)` | Successful `offerSkill` |
| `SkillHired` | `(uint256 indexed skillTokenId, address indexed nftContract, address indexed hirer, address owner, uint256 price, bool isETH, uint256 royaltyAmount)` | Successful `hireSkillETH` or `hireSkillERC20`; includes the `royaltyAmount` actually paid out under ERC-2981 |

Indexer-friendly indexing: `(skillTokenId, nftContract)` is the natural primary key. The `owner` / `hirer` indexes power per-account feeds.

**Defined functions:**

| Signature | view? | Purpose |
| --- | --- | --- |
| `offerSkill(uint256 skillTokenId, address nftContract, uint256 price, bool isETH, address paymentToken, uint40 expiresAt)` | no | Create or replace a listing for `(skillTokenId, nftContract)`. Caller is implicitly the seller. Implementation is expected to: verify caller is the current ERC-721 owner / approved, require `nftContract` whitelisted, write `SkillOffer`, emit `SkillOffered` |
| `hireSkillETH(uint256 skillTokenId, address nftContract) payable` | no | Pay `msg.value == price` in ETH, settle ERC-2981 royalty + protocol fee, transfer NFT (or grant usage) to caller, deactivate listing, emit `SkillHired`. Implementations may emit `SkillHired` with `isETH = true` |
| `hireSkillERC20(uint256 skillTokenId, address nftContract, uint256 amount)` | no | Same as `hireSkillETH` but settles via the listing's `paymentToken`. `amount` must equal the listing `price` (impl-checked) |
| `getSkillOffer(uint256 skillTokenId, address nftContract)` | yes | Return the current (or last) `SkillOffer` struct for the pair |
| `whitelistNFTContract(address nftContract, NFTType nftType)` | no | Permission-gated by the implementation. Marks a contract as offer-eligible and tags it with an `NFTType` |
| `isNFTContractWhitelisted(address nftContract)` | yes | Whitelist lookup |
| `getNFTType(address nftContract)` | yes | `NFTType` tag for a whitelisted contract |

**Implementers (concrete contracts in the bankoneth tree that implement this):**

- None within `bankoneth/contracts/` — the implementation lives in the wider AgenticPlace deployment outside this directory.

**Callers (contracts that hold an `IAgenticPlace` typed reference):**

- [`SoulBadger.sol`](../SoulBadger.sol) — holds `IAgenticPlace public agenticPlace`; never invokes a method (informational binding for off-chain reads).
- [`iNFT_7857.sol`](../../inft/iNFT_7857.sol) — does not hold a typed reference but stores marketplace addresses per token (`agenticPlaceFor[tokenId]`) and emits `AgenticPlaceListed` mirroring the `SkillOffered` schema.

## See also

- [`SoulBadger.sol`](../SoulBadger.sol) — caller; binds a marketplace pointer per badge collection
- [`iNFT_7857.sol`](../../inft/iNFT_7857.sol) — `offerOnAgenticPlace` hook + `agenticPlaceFor` storage
- [`IBankonExtensions.sol`](../../interfaces/IBankonExtensions.sol) — `IBankonAgenticPlaceHook` is the *per-mint listing emitter* built on top of this primitive
- ERC-2981 — royalty standard the marketplace settles
