# BANKON — subdomain.bankon.eth deployment system · ETHGlobal NYC archive

> Historical archive, ETHGlobal New York 2026 (June 12). This records the
> isolated, production deployment package for the complete `subdomain.bankon.eth`
> minter system: one canonical client-side deployer, the contract bundles it
> launches, the bankon.eth admin/payment model, and the CREATE2 salts that make
> the singletons reproducible on every EVM chain.

## What this is

The whole bankon.eth minter system is grouped into **topic bundles** that a single
client-side deployer (`deployer/index.html`) launches with two buttons — **DEPLOY**
(arm) then **LAUNCH** (fire) — across one chain or every chain (the **ALL** cycle).
There is no backend and no key in the trust path: only the wallet's EIP-1193 provider.

- **Single source of truth:** `script/export-abis.mjs` → `DEPLOY_SEQUENCES`. It
  generates *both* the dApp manifest (`packages/web/public/bankon.contracts.json`)
  *and* the deployer bundles (`deployer/bundles/bankon-*.xml`) +
  `deployer/chain-params.json`. Regenerate with `node script/export-abis.mjs`.
- **Engine:** `deployer/deployer.js` — dependency-free. Dynamic ABI encoding
  (string/bytes/array, verified against `cast abi-encode`), `from="chain:<key>"`
  resolution, CREATE2 via `bankon_create2_deployer`, post-deploy `<wire>` calls
  (selectors from the artifact `methodIdentifiers`), and deployments export.

## Bundles (stage order)

| Bundle | Chains | Stages | Notes |
|---|---|---|---|
| `bankon-ens` | mainnet + Sepolia | 13 + 13 wires | Flow A/B/C registrar core, ported from `script/DeployEthereum.s.sol`. NameWrapper-bound → not CREATE2. |
| `bankon-inft` | 0G (16601/16661) | 6 + 1 wire | ERC-7857 iNFT + ERC-6551 TBA; `setMinter` wire. |
| `bankon-arc` | any EVM | 3 | AgenticPlace agent economy (reputation → escrow → market). |
| `bankon-treasury` | any EVM | 6 | cp2048 golden-ratio rail (oracle → SCIENTIFIC → RAKE → autoconvert → bridge → gas svc). |
| `bankon-custody` | any EVM | 2 | Treasury + remittance safe vaults. |

## bankon.eth is the only admin

- **Admin / authority (who can press LAUNCH):** the wallet that controls
  `bankon.eth` — `NameWrapper.ownerOf(namehash("bankon.eth"))`, currently
  `0x54165AdA93FA752cfec95F3f3bAE2676D3752A99`. On Ethereum mainnet the deployer
  **gates** DEPLOY/LAUNCH to this wallet; no other wallet can administer. On
  testnets the gate relaxes to the connected wallet for rehearsal.
- **Recipient (admin role in contracts + all fees):** resolved `bankon.eth` =
  `0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169`. Every `from="owner"` constructor
  slot and the deploy `<fee>` resolve here, immutable on every chain. Subdomain
  fees and the φ/10 rake settle home to this address.

## bankon_vault — grant a subname from a signature, without revealing the key

`BankonSubnameRegistrar` already carries `GATEWAY_SIGNER_ROLE` + an EIP-712
`Registration` voucher. The `bankon-ens` bundle's final wire grants that role to the
vault signer (`chain:vaultSigner`; auto-skipped while unset). The flow:

1. A user signs a registration request (their wallet).
2. `clients/python/subdomain_issuer.py` asks **`bankon-vault/`** (AES-256-GCM +
   HKDF-SHA512) to counter-sign the EIP-712 voucher — the private key never leaves
   the vault.
3. `register(...)` mints `name.bankon.eth` and routes payment to bankon.eth.

To enable on a chain: set the per-chain `vaultSigner` in
`deployer/chain-params.json` (regenerated from `CHAIN_PARAMS`) to the vault signer
address, then re-LAUNCH the `bankon-ens` bundle (or grant the role manually).

## CREATE2 — same address on every chain (ERC-8004 pattern)

Singletons with chain-independent constructor args deploy through
`contracts/inft7857/bankon_create2_deployer.sol` (a Nick's Factory wrapper at
`0x4e59b44847b379578588920cA78FbF26c0B4956C`) with a fixed salt, so the address is
identical on every EVM chain. The address is read from the wrapper's
`Deployed(address,bytes32)` event (no client-side keccak). Salts (UTF-8 of the
contract name, right-padded to 32 bytes):

| Contract | CREATE2 salt |
|---|---|
| `treasury` | 0x7472656173757279000000000000000000000000000000000000000000000000 |
| `remittance` | 0x72656d697474616e636500000000000000000000000000000000000000000000 |
| `bankon_tba_account` | 0x62616e6b6f6e5f7462615f6163636f756e740000000000000000000000000000 |
| `bankon_tba_registry_proxy` | 0x62616e6b6f6e5f7462615f72656769737472795f70726f787900000000000000 |
| `AgentReputationRegistry` | 0x4167656e7452657075746174696f6e5265676973747279000000000000000000 |
| `AgenticMarketplaceEscrow` | 0x4167656e7469634d61726b6574706c616365457363726f770000000000000000 |

Contracts bound to per-chain infrastructure (the ENS stack → NameWrapper,
cp2048 oracle/rake → USDC/Uniswap) are **not** CREATE2 same-address: their initCode
differs per chain, exactly as ERC-8004's chain-bound contracts do.

## Admin console — `deployer/admin.html` (bankon.eth admin)

Extends the deployer protocol with the previous go-LIVE page's strengths, for the
bankon.eth admin:

- **PREVIEW** — before any broadcast, predicts each contract's address and per-stage gas.
  CREATE2 addresses are computed exactly (verified: prediction == the on-chain deploy);
  keccak lives in `deployer/keccak.js` (admin-only — the core `index.html` deploy path stays
  keccak-free). `Deployer.preview()`.
- **RETURN** — explorer tx/address links from `chains.xml` (`deployer.js` feedback).
- **ADMIN** — post-deploy operations on the *deployed* contracts, generated into
  `deployer/admin-actions.json` from `ADMIN_ACTIONS` in `export-abis.mjs` (selectors from the
  artifact `methodIdentifiers`): set bankon_vault gateway signer (grant/revoke
  `GATEWAY_SIGNER_ROLE`), set price oracle / reputation gate, pause/unpause, set AgenticPlace
  webhook, set buyback threshold. `Deployer.runAdminAction(id, inputs, target?)`, gated to the
  bankon.eth controller. A deployed-address registry (localStorage) + EXPORT round out the page.

Verified on anvil: keccak vs `cast`, CREATE2 prediction == deployed address, and a full admin
`grantRole` → `hasRole==true` round-trip (`deployer/_anvil_verify.mjs` + the admin check).

## Deployed addresses (filled after each LAUNCH)

Per-chain records live in `deployments/<chainId>.json` (slot = `deploymentKey`).
Export from the deployer's **EXPORT deployments JSON** button after a run and commit
the diff. As of this archive the on-chain slots are unfilled (testnet rehearsal +
mainnet release are operator-gated).

| Chain | Status |
|---|---|
| Ethereum (1) | operator-gated — bankon.eth controller LAUNCH |
| Sepolia (11155111) | rehearsal target (`ALLOW_TESTNET=true`) |
| Base Sepolia (84532) | cp2048 + x402 rehearsal |
| 0G Galileo (16601) | iNFT rehearsal |
| Arc testnet (5042002) | USDC settlement rehearsal |

## Reproduce

```bash
cd openagents/bankoneth
forge build                                                  # default profile
FOUNDRY_PROFILE=zerog forge build contracts/inft/iNFT_7857.sol
node script/export-abis.mjs                                  # manifest + deployer bundles + chain-params
node deployer/_encoder_parity.mjs                            # dev: encoder == cast abi-encode
python3 -m http.server 8088                                  # serve from bankoneth/ root
#   → http://localhost:8088/deployer/index.html   (connect bankon.eth wallet)
#   → http://localhost:8088/packages/web/bankon.html  (landing)
```
