# bankoneth — ENSIP Coverage Map

The exact set of ENS Improvement Proposals this module implements, where
each lands in the contract surface, and how the v2 plan brought us to
canonical parity with `app.ens.domains`.

Every row links to the upstream spec on [ensips.ethereum.org](https://ensips.ethereum.org)
plus the file in this repo where the implementation lives.

## Implemented

| ENSIP | Spec | Surface | Bankoneth implementation |
|---|---|---|---|
| **1**  | [addr(node)](https://ensips.ethereum.org/ensips/1) / [EIP-137](https://eips.ethereum.org/EIPS/eip-137) | resolver | [`BankonSubnameResolver.addr`](../contracts/BankonSubnameResolver.sol), [`BankonSubnameResolverV2.addr`](../contracts/BankonSubnameResolverV2.sol) (with iNFT TBA override) |
| **3**  | reverse resolution | reverse | [`SetPrimaryNames.s.sol`](../script/SetPrimaryNames.s.sol) calls `setReverseName` on each registrar; ENS canonical ReverseRegistrar mainnet `0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb` |
| **5**  | [text records](https://ensips.ethereum.org/ensips/5) / [EIP-634](https://eips.ethereum.org/EIPS/eip-634) | resolver | `text(node, key)` — `BankonSubnameResolver` + V2. Includes the BANKON agentic-text keyset (`mindx.endpoint`, `bonafide.attestation`, `agent.capabilities`, `inft.uri`, `agenticplace.listing`, `x402.endpoint`, `algoid.did`, `agent.card`) |
| **7**  | [contenthash](https://ensips.ethereum.org/ensips/7) / [EIP-1577](https://eips.ethereum.org/EIPS/eip-1577) | resolver | `contenthash(node)` — V1 + V2. Browser-side: `@ensdomains/content-hash` v3 for encode/decode |
| **9**  | [multichain addr](https://ensips.ethereum.org/ensips/9) / [EIP-2304](https://eips.ethereum.org/EIPS/eip-2304) | resolver | `addr(node, coinType)` — V1 (custom selector) + V2 (canonical `IAddressResolver`). Interface ID `0xf1cb7e06` |
| **10** | [wildcard resolution](https://ensips.ethereum.org/ensips/10) | resolver | [`BankonSubnameResolverV2.resolve`](../contracts/BankonSubnameResolverV2.sol) (on-chain) + [`BankonOffchainResolver.resolve`](../contracts/BankonOffchainResolver.sol) (CCIP-Read). Interface ID `0x9061b923` |
| **11** | [EVM coinType derivation](https://ensips.ethereum.org/ensips/11) | resolver | Multichain setter accepts ENSIP-11-derived coinTypes; [`packages/core/src/coin-types.ts`](../packages/core/src/coin-types.ts) ships 24-chain map |
| **15** | [immutable contract naming](https://docs.ens.domains/web/naming-contracts) | reverse | `setReverseName(rr, name)` admin method on `BankonSubnameRegistrar`, `BankonEthRegistrar`, `BankonDomainHosting`, `BankonOffchainRegistrar`. Wired by [`SetPrimaryNames.s.sol`](../script/SetPrimaryNames.s.sol) |

## Bonus surfaces (not numbered ENSIPs)

| Spec | Surface | Bankoneth implementation |
|---|---|---|
| [EIP-3668 CCIP-Read](https://eips.ethereum.org/EIPS/eip-3668) | resolver | [`BankonOffchainResolver`](../contracts/BankonOffchainResolver.sol) — `OffchainLookup` revert + EIP-712-signed `resolveWithProof` callback. See [`docs/specs/CCIP_READ_REGISTRAR.md`](specs/CCIP_READ_REGISTRAR.md) |
| `INameResolver` (`name(node)`) | resolver | V2 only — `name()` getter + setter. Interface ID `0x691f3431` |
| `IMulticallable` | resolver | V1 + V2 — `multicall(bytes[])` via delegatecall. Interface ID `0xac9650d8` |
| ERC-165 | resolver | `supportsInterface` — V2 advertises every canonical interfaceId verbatim (see `contracts/BankonSubnameResolverV2.md`) |
| [EIP-4361 SIWE](https://eips.ethereum.org/EIPS/eip-4361) | identity | [`BankonAuthGate`](../contracts/identity/BankonAuthGate.sol) verifies SIWE bundles; [`packages/core/src/auth.ts`](../packages/core/src/auth.ts) builds them; `<b-siwe-signin>` is the UI |

## Forward-compat with ENSv2 (Namechain)

Every read goes through the **Universal Resolver**
`0xeEeEEEeE14D718C2B47D9923Deab1335E144EeEe` ([address registry](ADDR_REFERENCE.md)) —
an ENS-DAO-upgradable proxy whose address stays constant across UR
revisions. The UR will be re-pointed at Namechain when ENSv2 ships, so
bankoneth reads stay current without code changes.

See [`docs/V2_READINESS.md`](V2_READINESS.md) for the full forward-compat
checklist.

## Further reading

- [ENS Documentation (canonical)](https://docs.ens.domains)
- [ENS Improvement Proposals (ENSIPs)](https://ensips.ethereum.org)
- [ENS Resolver Interfaces](https://docs.ens.domains/resolvers/interfaces)
- [ENS Subdomain Issuance](https://docs.ens.domains/web/subdomains)
- [ENS Multichain Addresses](https://docs.ens.domains/web/multichain)
- [ENS Naming Contracts](https://docs.ens.domains/web/naming-contracts)
- [ENSv2 Readiness](https://docs.ens.domains/web/ensv2-readiness)
- [Creating a Subname Registrar](https://docs.ens.domains/wrapper/creating-subname-registrar)
- [CCIP-Read](https://docs.ens.domains/resolvers/ccip-read)
- [Writing a Resolver](https://docs.ens.domains/resolvers/writing)
- [ENS Universal Resolver](https://docs.ens.domains/resolvers/universal)
- [ens-contracts (v1 source)](https://github.com/ensdomains/ens-contracts)
- [namechain (ENSv2 source, formerly contracts-v2)](https://github.com/ensdomains/namechain)
- [ensjs v4 (canonical client library)](https://github.com/ensdomains/ensjs)
- [ens-app-v3 (canonical dApp)](https://github.com/ensdomains/ens-app-v3)
- [ensauth (mDeisen)](https://github.com/mDeisen/ensauth) — inspiration for `BankonAuthGate`
- [@adraffy/ens-normalize](https://github.com/adraffy/ens-normalize.js) — ENSIP-15 normalization
- [gskril/ens-offchain-registrar](https://github.com/gskril/ens-offchain-registrar) — CCIP-Read reference impl
