# Canonical EIP-7857 + ERC-6551 modular stack (`contracts/inft7857/`)

The working, standards-compliant, **modular** iNFT stack for the ETHGlobal NYC build —
ported (pragma relaxed `^0.8.26`→`^0.8.24`) from
`docs/BANKON ENS Subname Registrar_ ERC-7857 iNFT and ERC-6551 TBA Integration.md`.
Each file is an independent module so you can swap/extend any piece without touching the rest.

## Modules

| File | Role | Extension point |
|---|---|---|
| `bankon_interfaces.sol` | Canonical `IERC7857`/`Metadata`/`DataVerifier` + structs (`AccessProof`/`OwnershipProof`/`TransferValidityProof`/`…Output`/`IntelligentData`/`OracleType{TEE,ZKP}`) + `IERC6551*`, `IERC5192/4906/7572`, `INameWrapper`, `bankon_fuses`. | one grep-able interface file |
| `bankon_inft_oracle.sol` | Pluggable `IERC7857DataVerifier` — v1 multisig EIP-712 (TEE-style). | v2: drop in Intel SGX quote / ZKP verification; the iNFT only knows `verifier()` |
| `bankon_inft_subname.sol` | **Mode A** unified iNFT-ENS: one ERC-721 that is also ERC-7857 + 5192 + 2981 + 4906 + 7572, NameWrapper-backed, soulbound belt-and-suspenders. | the marketplace-interoperable centerpiece |
| `bankon_inft_extension.sol` | **Mode B** parallel iNFT bolted onto an existing wrapped subname. | OpenSea/Blur-native ERC-1155 trading + parallel agent license |
| `bankon_inft_registrar.sol` | Mint router (`WRAPPED_ONLY`/`UNIFIED`/`PARALLEL` ± soulbound) + x402 facilitator receipt check; derives the ERC-6551 TBA. | renamed from the doc's `bankon_subname_registrar` to avoid clash with the ENS `BankonSubnameRegistrar.sol` |
| `bankon_tba_account.sol` | Lean ERC-6551 account — owner = live `ownerOf(tokenId)`, no storage write on transfer. | governance-heavy alternative: `daio` `TokenBoundAccount.sol` (modular swap) |
| `bankon_tba_registry_proxy.sol` | Event-emitting wrapper over the canonical registry `0x0000…5758`. | indexer-friendly `BankonTbaCreated` |
| `bankon_metadata_resolver.sol` | Pure-view OpenSea JSON builder. | |
| `bankon_create2_deployer.sol` | Nick's-Factory CREATE2 for `0xBANK…` multichain vanity. | |

## Soulbound (belt-and-suspenders)
1. NameWrapper `CANNOT_TRANSFER` burned (`bankon_fuses.BANKON_SOULBOUND`).
2. ERC-5192 `locked(tokenId)` = true.
3. `_update` reverts owner→owner transfer.
4. `iTransfer` reverts when locked.

## Deploy + test
- `script/deploy_bankon_inft.s.sol` — oracle → tbaImpl → proxy → unified → parallel → registrar.
  Verified mainnet ENS NameWrapper `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401` (override on testnet/fork via `NAME_WRAPPER_ADDR`).
- `test/inft7857/bankon_inft_subname_test.sol` — **15/15 pass** (mocked NameWrapper + 6551 registry,
  no RPC): soulbound, royalty, interface introspection (5192/4906/2981/7572/721), authorize/revoke,
  x402-gated unified mint + deterministic TBA, receipt replay block.

## UI
`packages/web/name-service.html` — mint a named agent iNFT (Mode A/B), compute its ERC-6551 TBA live,
name any contract (`myapp.bankon.eth`), and a generic canonical-7857 read/write panel. ABIs flow through
`script/export-abis.mjs` → `packages/web/public/abis/`. 0G Aristotle mainnet 16661 is wired
(`packages/web/iNFTabi.js` `ZEROG_CHAINS`, `chains.js`, `caip2.json`).

## Modular-later (extension points, not built now)
TEE/ZKP on-chain attestation (v2 oracle); THOTCommitmentRegistry revocation gate (in `daio/contracts/THOT/`);
multichain CREATE2 vanity; L2 Durin CCIP-Read mirror. Each plugs in without touching the core.
