# Arweave × AR.IO: A Deep Technical Dive and a Practical Playbook for Deploying 100,000 ARIO (Held on Base)

## TL;DR
- **Your 100k ARIO on Base cannot directly buy ArNS names or stake on gateways.** Base ARIO is only a bridged ERC-20 *representation*; per ar.io's own docs, "At this time, only ARIO on AO can be used for joining a gateway to the network and delegated staking." You must move it into the AR.IO smart-contract environment first (today via the AO-powered "ARIO Bridge" at swap.ar.io → Vento).
- **The single biggest gotcha right now (June 2026): AR.IO is mid-migration from AO to Solana.** The token/contract are moving to Solana (SPL mint `DcNnMuFxwhgV4WY1HVSaSEgr92bv2b1vUvEKiNxWqHdF`), a snapshot occurred June 1, 2026, ArNS purchases are paused at arns.ar.io, and a retroactive claim period follows mainnet. Do not execute irreversible bridge/stake actions until you confirm the current live environment via docs.ar.io.
- **What 100k ARIO realistically claims:** roughly 5–10 permanent ArNS names of average length (a 5-char permabuy ≈ ~12,500 ARIO at neutral demand), OR a fully self-operated gateway (10,000 ARIO minimum stake) with ~90k left over to delegate, OR pure delegation across one or more gateways to earn protocol rewards. Gateway minimum to *operate* is 10,000 ARIO; the network's global minimum *delegated* stake is just 10 ARIO (individual gateways may set higher).

---

## Key Findings

1. **Two-layer architecture.** Arweave is the permanent *storage* base layer (pay-once-store-forever, funded by an endowment). AR.IO is the *access/gateway* network layer on top: gateways index, cache, resolve names (ArNS) and serve permaweb data. The ARIO token powers AR.IO, not Arweave storage (storage is paid in AR or Turbo Credits).

2. **The ARIO token currently exists in (at least) three forms:** AO-native ARIO (historically canonical; Contract/Process ID `qNvAoz0TgcH7DMg8BCVn8jF32QH5L6T29VjHxhHqqGE`), bridged Base ERC-20 ARIO (`0x138746adfA52909E5920def027f5a8dc1C7EfFb6`), and the new Solana SPL ARIO (`DcNnMuFxwhgV4WY1HVSaSEgr92bv2b1vUvEKiNxWqHdF`). Migration to Solana is underway.

3. **Base is a liquidity wrapper, not a functional environment.** ArNS registration, gateway operation, and delegated staking all require the native protocol token (AO today, Solana going forward) — never the Base ERC-20 directly.

4. **Practical path for your 100k:** Bridge Base→AO (or claim/migrate to Solana once live) → use Wander wallet (AO) or a Solana wallet → register names at arns.ar.io or via `@ar.io/sdk` `buyRecord`, and/or stake via `joinNetwork`/`delegateStake`.

5. **Developer pipeline:** Upload data with `@ardrive/turbo-sdk` (get a 43-char Arweave tx ID), then point an ArNS name/ANT at that ID with `@ar.io/sdk`, and read back via Arweave GraphQL + the `ar://` / gateway HTTP path. Turbo can even be funded with ARIO or Base USDC directly.

---

## Details

### 1. Arweave Fundamentals (deep)

**Permanent storage and the endowment.** Arweave is a "pay once, store forever" network. When you upload, you pay a one-time fee in AR. A portion compensates miners immediately and the remainder is swept into a **storage endowment** — a protocol-controlled pool that pays miners out over time as block rewards decline. (The exact immediate split is debated across secondary sources: Akord states "A small portion, 16.67% to be exact, is paid initially while the rest goes into a storage endowment," whereas the Permaweb Journal cites a figure closer to ~5%; treat the precise percentage as approximate.) The model is funded conservatively: per the Arweave protocol docs (docs.arweave.org), "Users pay for 200 years' worth of replicated storage at present prices, such that only a 0.5% Kryder+ rate is sufficient to sustain the endowment for an indefinite term, in the absence of token price changes." Historically the real decline has been far steeper — the Arweave Yellow Paper notes that "over the last 50 years the average annual rate of decline of the cost of storing 1GB per hour has been -30.57%" (ar.io co-founder Sam Williams elsewhere cites ~38%/yr). As Williams put it (on X, March 2025): "If the cost of storage never declined again… the last token from data stored today would be reissued from the endowment 200 years from now. If… storage declined at a rate of 0.5% per year on average then the full quantity of tokens would never be re-issued." AR has a fixed cap of 66M tokens (~55M at genesis, ~11M released as mining rewards); because heavy usage locks AR into the endowment, the model is mildly deflationary on circulating supply.

**Blockweave + proof of access.** Arweave is not a linear blockchain. Each new block links both to the previous block *and* to a pseudo-randomly chosen historical "recall block." To mine, a node must prove it has access to that recall block's data — the mechanism evolved from Proof of Access to **SPoRA (Succinct Proofs of Random Access)** and later VDF-based packing (2.6/2.7+). The economic effect: miners are incentivized to store as much of the dataset as possible (and rare data especially), since the probability of being able to mine is proportional to the fraction of historical data they hold. This is what turns "storage" into "consensus."

**How data is written/read.**
- **Base-layer (L1) transactions**: a direct Arweave transaction carrying data + tags.
- **Data Items + ANS-104 bundles**: Most data today is uploaded as **data items** bundled into a single L1 transaction per the **ANS-104 "Bundled Data" binary spec**. A data item has its own owner, tags, signature, and ID but no reward/token-transfer ability; the wrapping transaction pays the reward for everything inside. Bundles can be nested; GQL exposes a `bundledIn` field so any data item can be traced back to its parent L1 transaction.
- **Bundlers**: Services that accept your signed data items, batch them, pay the AR reward, and post to L1. The dominant ones are **Turbo** (ArDrive/ar.io, `@ardrive/turbo-sdk`) and historically **Bundlr/Irys**. Turbo abstracts funding (fiat, AR, ETH, SOL, MATIC, ARIO, even Base USDC) and gives fast finality + indexing.
- **Content addressing**: Every transaction/data item has a 43-character base64url ID derived from its signature. That ID *is* the permanent address: `https://<gateway>/<txid>`.

**Gateways and GraphQL.** Gateways read L1 + bundle headers as they're mined, insert them into an indexed database, and expose:
- HTTP data serving: `https://arweave.net/<txid>`
- **GraphQL** for discovery: `https://arweave.net/graphql` (and Goldsky's `https://arweave-search.goldsky.com/graphql`). GraphQL returns *transaction IDs and metadata* (tags, owner, block, `bundledIn`), not the data itself — you then fetch the data by ID over HTTP. **Manifests** (path manifests) let one transaction map friendly paths to many data item IDs, enabling whole websites/SPAs.

### 2. AR.IO Network Architecture

**What AR.IO is.** AR.IO is a decentralized network of **gateways** — the "in and out" doors to Arweave. They handle ingress (bundling/seeding uploads) and egress (retrieval, caching, indexing, GraphQL, ArNS name resolution, app hosting). Arweave guarantees permanence; AR.IO guarantees *accessibility and usability*. Per AR.IO's GlobeNewswire release (March 19, 2025), the network completed "the highly-anticipated launch of AR.IO's mainnet on 20 February, which opened the doors for users to upload and access permanently stored data."

**Gateways.** Open-source (`github.com/ar-io/ar-io-node`), modular, deployable on hardware as small as a Raspberry Pi. They register in the **Gateway Address Registry (GAR)**, stake ARIO, and earn protocol rewards based on observed performance (the **Observation & Incentive Protocol** — observers grade gateways each epoch).

**ArNS (Arweave/Ar.io Name System).** A permissionless naming registrar (no single TLD).
- **Lease** (1–5 years, renewable, with a 2-week grace period) vs **Permabuy** (one-time, permanent).
- Names are controlled by **ANTs (Arweave/Ar.io Name Tokens)** — transferable tokens that hold the pointer to an Arweave transaction ID (or manifest). The ANT owner can repoint the name anytime, enabling versioned/mutable sites on top of immutable data.
- Each name includes **10 undernames** (subdomain-equivalents using `_`, e.g. `docs_myapp`), expandable up to 10,000.
- Resolution: each AR.IO gateway resolves `name.gateway.tld` (e.g. `ardrive.arweave.net`, `ardrive.ar.io`) by reading registry+ANT state and proxying to the underlying tx ID.

**ArNS dynamic pricing (from the official pricing model).** Price = a length-based **Genesis/Base Registration Fee (BRF)** × a global **Demand Factor (DF)**. Genesis fees by name length (in ARIO):

| Length | Fee (ARIO) | Length | Fee (ARIO) |
|---|---|---|---|
| 1 | 1,000,000 | 7 | 800 |
| 2 | 200,000 | 8 | 500 |
| 3 | 20,000 | 9 | 400 |
| 4 | 10,000 | 10 | 350 |
| 5 | 2,500 | 11 | 300 |
| 6 | 1,500 | 12 | 250 |
| | | 13–51 | 200 |

- **Annual Fee** = ARF × 20% (where ARF = BRF × DF).
- **Lease Price** = ARF + (Annual Fee × Years).
- **Permabuy Price** = ARF + (Annual Fee × 20). So a 5-char permabuy at DF=1 ≈ 2,500 + (500 × 20) = **12,500 ARIO**; a 13+ char permabuy ≈ 200 + (40×20) = **1,000 ARIO**. DF floats (min 0.5, +5%/−1.5% per day based on revenue vs. 7-day moving average), so live prices vary — check `arns.ar.io/#/prices`.
- Gateway operators in good standing (GPRW ≥ 0.9, Tenure Weight ≥ 1.0) get a **20% ArNS discount** on purchases, lease extensions, lease-to-permabuy upgrades, and undername-capacity increases.

**The ARIO token.** Fixed supply **1,000,000,000 ARIO**, non-inflationary, 6 decimals (1 ARIO = 1,000,000 mARIO). Uses: gateway staking, delegated staking, ArNS registration/renewal/undernames, and protocol rewards. Revenue from ArNS flows into the **Protocol Balance** (modeled on Arweave's endowment) and is redistributed to operators, delegators, and observers.

**The AO connection.** AR.IO migrated from SmartWeave to **AO** (Arweave's hyper-parallel compute layer) in mid-2024; the ARIO token and network logic ran as an **AO process** (`qNvAoz0TgcH7DMg8BCVn8jF32QH5L6T29VjHxhHqqGE`), with ArNS registry/ANT state stored permanently on Arweave via AO. **As of 2026, AR.IO is migrating again — this time to Solana** (see below).

### 3. THE CRITICAL PIECE — ARIO on Base vs. the native network (and the Solana migration)

This is the most important and most error-prone part, so read carefully.

**Three token representations:**
- **AO-native ARIO** — historically the canonical asset that powers staking, rewards, and ArNS. AO Contract/Process ID: `qNvAoz0TgcH7DMg8BCVn8jF32QH5L6T29VjHxhHqqGE`. Held in **Wander** (formerly ArConnect).
- **Base ARIO (ERC-20)** — `0x138746adfA52909E5920def027f5a8dc1C7EfFb6`. Described by ar.io as "a representation of AO ARIO on the Base L2 for EVM-based liquidity, tools, and integrations." Held in any EVM wallet (MetaMask). **Not directly usable** for ArNS or staking.
- **Solana SPL ARIO** — mint `DcNnMuFxwhgV4WY1HVSaSEgr92bv2b1vUvEKiNxWqHdF`, the *future* canonical token. ar.io Solana programs: `ario-core` (`73YoECm6NKXpVRoe5f1Q9BcP5DJGPFUjnFy6AxBE5Nvh`), `ario-gar` (`89fNiiwgpFSPHKuqfNUkgYTYjtAJAhyqHjXmgXeppGpf`), `ario-arns` (`2yCUx5edFvUrkibYaUa2ZXWyx9kuJkS8CwyzsgHPWdZZ`), `ario-ant` (`2MWexMHfMhGJwMHv9Qm9YAVCqjUFUJwDJAysW4oCUGk5`), `ario-ant-escrow` (`5HZhe9UqKL5zAsdz81nuuaxV41h8bFhudzxxBigAQndM`). Held in Phantom/Solflare/Backpack; liquidity via Jupiter/Raydium.

**The bridge (Base ↔ AO).** ar.io's official "ARIO Bridge" lives at **swap.ar.io**, which redirects to **ventobridge.com** (Vento, "Fast, secure token swaps powered by AO"). The docs say: "You can obtain ARIO on Base by swapping on a DEX or by bridging it from AO… Bridge from AO to Base (and vice versa) via the ARIO Bridge." Operationally it is an **AO-powered swap** between Base ARIO and AO ARIO, not a Wormhole-style guardian bridge. You connect a Base EVM wallet (MetaMask) on one side and a Wander (AO) wallet on the other.

**Do ArNS/staking require native ARIO?** Yes. ar.io states explicitly: **"At this time, only ARIO on AO can be used for joining a gateway to the network and delegated staking."** ArNS registration likewise consumes native ARIO (or Turbo Credits/fiat at arns.ar.io). Base ARIO is purely for liquidity/trading and must be bridged.

**⚠️ The migration to Solana — current status (June 2026).** This is critical and the docs are internally contradictory because they're being updated page-by-page mid-cutover:
- The docs homepage banner: "Ar.io is migrating to Solana. The ar.io smart contract and token are migrating to Solana. Register now to migrate your assets before the deadline."
- The official @ar_io_network account: "the snapshot date has been extended to June 1 2026… After mainnet launches, users will be able to claim unregistered assets during a retroactive claim period."
- The ArNS app (arns.ar.io) banner: "Ar.io is migrating to Solana! Purchases are paused and will resume shortly. Register before the June 1, 2026 snapshot!"
- `docs.ar.io/learn/token` already describes ARIO as "an SPL Token on Solana" with ArNS state "managed on Solana by the ario-arns program," while `docs.ar.io/learn/token/get-the-token` still labels "AO ARIO (canonical)" and says only AO ARIO works for staking.

**Interpretation:** The **target/system-of-record is becoming Solana**; the **historically live operational environment is AO**; and **right now is a transition window** in which ArNS purchases are paused and Solana mainnet + retroactive claim are imminent. **Action implication for you: do not bridge or stake blindly today.** First confirm, via docs.ar.io's "Learn more" migration link and the @ar_io_network pinned post, (a) whether ArNS/staking are currently live on AO or already cut over to Solana, and (b) the exact migration/claim portal and whether your Base ARIO should be migrated/claimed on Solana rather than bridged to AO.

### 4. Concrete Step-by-Step: deploying 100,000 ARIO held on Base

> **Pre-flight (do this first, June 2026):** Open `docs.ar.io` → follow the Solana-migration "Learn more" link; check the @ar_io_network pinned post; open `arns.ar.io` to see whether purchases are still paused. Determine the live environment (AO vs Solana) before moving funds. The steps below assume the AO environment that has been operational; if the network has fully cut over to Solana, substitute a Solana wallet (Phantom) and the SPL token, and use the official migration/claim flow instead of the Vento bridge.

**Wallets you need:**
- **MetaMask** (or any Base-enabled EVM wallet) — holds your 100k Base ARIO.
- **Wander** (formerly ArConnect, `wander.app`) — the Arweave/AO-native wallet that holds AO ARIO and signs ArNS/staking transactions. (If on Solana: **Phantom**.)

**Step A — Bridge Base ARIO → AO ARIO.**
1. Go to `swap.ar.io` (redirects to Vento/ventobridge.com).
2. Connect MetaMask (source: Base ARIO `0x1387…fFb6`) and your Wander wallet (destination: AO ARIO).
3. Verify the destination token contract is the AO ARIO process ID `qNvAoz0Tg…`.
4. Swap/bridge the desired amount (e.g., keep some on Base for liquidity flexibility; bridge ~90–100k for use). Confirm; wait for settlement (AO swaps typically settle in minutes).
5. Add ARIO to Wander (Settings → Tokens → import the AO ARIO process ID) to view balance.

**Step B — Option 1: Register ArNS name(s).**
- Via UI: go to `arns.ar.io`, connect Wander, search a name, choose **Lease** (pick years) or **Permabuy**, and pay in ARIO (or Turbo Credits/fiat). Confirm in Wander.
- Cost examples (DF=1, will vary): 5-char permabuy ≈ 12,500 ARIO; 8-char permabuy ≈ 500 + (100×20) = 2,500 ARIO; 13+char permabuy ≈ 1,000 ARIO; a 1-year lease of a 13+char name ≈ 200 + 40 = 240 ARIO. So 100k ARIO comfortably buys several premium permanent names plus many cheaper ones.

**Step B — Option 2: Operate a gateway.**
- Minimum operator stake: **10,000 ARIO**. Stand up the node (`github.com/ar-io/ar-io-node`, ~15–30 min), then `joinNetwork` with ≥10,000 ARIO. You'd have ~90k left to self-delegate or hold. You earn protocol + observer rewards for reliable service and qualify for the 20% ArNS discount.

**Step B — Option 3: Delegate-stake (no infrastructure).**
- Use the Network Portal (`gateways.ar.io`) or the SDK to delegate to one or more gateways. Per ar.io's delegated-staking docs, the network's global minimum stake is just 10 ARIO and the global maximum is 10,000 ARIO per delegation (individual gateways may set higher minimums via `minDelegatedStake`). You share in rewards proportional to your stake and the gateway's performance; you can redelegate without penalty and unstake after the protocol delay (or pay an instant-withdrawal fee).

**A sensible 100k allocation:** e.g., 2–3 strong permanent names for your "eternalrecords" brand (~15–25k ARIO), 10,000 ARIO to run your own gateway (so your pipeline has a gateway you control for indexing/serving), and the remainder (~55–65k) delegated across 2–3 high-performing gateways to earn rewards and diversify.

### 5. Developer Integration

**SDKs/packages:**
- `@ar.io/sdk` (TypeScript; latest 3.x line) — network reads/writes: ArNS, GAR, staking.
- `@ardrive/turbo-sdk` (latest 1.x line) — uploads + funding.
- `@ar.io/wayfinder-core` — gateway routing/verification (`ar://` resolution with fallback + hash verification).
- `ar-gql` — convenience GraphQL client.

**Client init pattern (`@ar.io/sdk`):** a read-only client (`ARIO.mainnet()` / `ARIO.init()`) exposes only reads; passing a signer (`ArweaveSigner(JWK)` in Node, `ArConnectSigner(window.arweaveWallet, …)` in browser) unlocks write APIs like `joinNetwork`, `delegateStake`, and `buyRecord`.

**Register a name programmatically (`@ar.io/sdk`):**
```ts
import { ARIO, ARIOToken, ArweaveSigner } from '@ar.io/sdk';

const ario = ARIO.mainnet({ signer: new ArweaveSigner(JWK) });

// Lease "eternalrecords" for 1 year, optionally point to an existing ANT process
const { id } = await ario.buyRecord({
  name: 'eternalrecords',
  type: 'lease',          // or 'permabuy'
  years: 1,
  processId: '<optional-existing-ANT-process-id>',
  referrer: 'eternalrecords.app',
});
```

**Join the network / delegate (`@ar.io/sdk`):**
```ts
const ario = ARIO.mainnet({ signer: new ArweaveSigner(JWK) });

// Operate a gateway (min 10,000 ARIO)
await ario.joinNetwork({
  qty: new ARIOToken(10_000).toMARIO(),
  autoStake: true,
  allowDelegatedStaking: true,
  minDelegatedStake: new ARIOToken(100).toMARIO(),
  delegateRewardShareRatio: 10,
  fqdn: 'gateway.eternalrecords.xyz', protocol: 'https', port: 443,
});

// OR delegate to an existing gateway
await ario.increaseDelegateStake({
  target: 't4Xr0_J4Iurt7caNST02cMotaz2FIbWQ4Kbj616RHl3',
  qty: new ARIOToken(50_000).toMARIO(),
});
```

**Upload to Arweave and capture the tx ID (`@ardrive/turbo-sdk`):**
```ts
import { TurboFactory, ArweaveSigner } from '@ardrive/turbo-sdk';

const turbo = TurboFactory.authenticated({ signer: new ArweaveSigner(jwk) });

const { id, owner, dataCaches } = await turbo.upload({
  data: JSON.stringify(record),
  dataItemOpts: { tags: [
    { name: 'Content-Type', value: 'application/json' },
    { name: 'App-Name', value: 'eternalrecords-v1' },
  ]},
});
console.log(`https://arweave.net/${id}`);
```
- You can fund Turbo with ARIO or even **Base USDC** directly via the CLI: `turbo crypto-fund --value 10 --token base-usdc --private-key 0x... --address <any-evm-sol-ar-address>`, or with ARIO: `turbo crypto-fund --value 100 --token ario --wallet-file ./wallet.json`. Turbo Credits are 1:1 with AR's upload power. (In browsers, you can also authenticate Turbo with MetaMask/Wagmi or Phantom/Solana wallet adapters.)

**Point an ArNS name at your uploaded data:** update the ANT's record to the new tx ID (via `@ar.io/sdk` ANT methods or the arns.ar.io UI). For mutable "latest" pointers, repoint the ANT each release; the immutable history remains addressable by each tx ID.

**Production AR-fee-capture pipeline (your eternalrecords / Algorand + x402 context):**
1. Capture payment (Algorand / x402) → in your settlement handler, allocate a budget for permanent storage.
2. Pre-fund a Turbo balance (fiat, AR, or Base USDC) so uploads don't block on per-item funding; monitor balance with `turbo.getBalance()`.
3. On each record, `turbo.upload()` the canonical artifact with structured tags (e.g., `App-Name`, `Record-ID`, `Payment-Ref`, `Content-Type`). Persist the returned tx ID alongside your off-chain record.
4. Optionally maintain an ArNS name (e.g., `eternalrecords`) whose ANT points to a manifest/index updated per batch, giving a stable human-readable root over an append-only set of immutable tx IDs.
5. Read back / verify via GraphQL discovery + HTTP fetch (below), and use Wayfinder for verified, gateway-redundant retrieval.

**GraphQL read-back example:**
```graphql
query {
  transactions(
    tags: [
      { name: "App-Name", values: ["eternalrecords-v1"] },
      { name: "Record-ID", values: ["abc-123"] }
    ],
    sort: HEIGHT_DESC, first: 10
  ) {
    edges { node { id tags { name value } block { height timestamp } bundledIn { id } } }
  }
}
```
POST to `https://arweave.net/graphql` (or Goldsky). For an EVM-friendly query pattern, you can also filter by `owners` or by app tags and paginate via the `after`/`cursor` fields. Take `node.id`, then fetch `https://arweave.net/<id>`. GraphQL is for *discovery*; data retrieval is a separate HTTP GET by ID.

---

## Recommendations

**Stage 0 — Verify before you move anything (now).** Because AR.IO is mid-migration to Solana (snapshot June 1, 2026 per @ar_io_network; ArNS purchases currently paused), confirm the live environment at docs.ar.io and @ar_io_network before bridging or staking. If the network has cut over to Solana, use the official migration/claim portal and a Solana wallet rather than the AO bridge. **Benchmark that changes the plan:** if arns.ar.io still shows "purchases paused," wait for the "resume" notice before registering names.

**Stage 1 — Bridge a test amount.** Move a small amount (e.g., 100 ARIO) Base→AO via swap.ar.io first, confirm it lands in Wander and is spendable, before bridging the bulk.

**Stage 2 — Secure your names.** Permabuy 1–3 brand names (e.g., `eternalrecords` and key undernames) once purchases reopen. Permanent > lease for a brand you intend to keep — at DF=1 a permabuy costs ~20× the annual fee, so it breaks even vs leasing in ~20 years and removes renewal risk entirely.

**Stage 3 — Decide stake vs delegate.** If your pipeline benefits from a gateway you control (custom indexing, guaranteed serving of your own data), run one (10k ARIO) and self-delegate surplus. If you only want yield/network support, delegate across 2–3 top-performing gateways. **Threshold to switch from delegating to operating:** when your retrieval/index volume or uptime requirements justify the ops burden, or when the 20% ArNS discount on heavy name activity outweighs node costs.

**Stage 4 — Wire the developer pipeline.** Stand up Turbo-funded uploads, persist tx IDs, and maintain an ANT-backed manifest root. Add Wayfinder for verified multi-gateway retrieval so your reads don't depend on a single gateway.

**Re-evaluation triggers:** (1) Solana mainnet + claim period goes live → migrate canonical holdings and update SDK targets; (2) ArNS DF spikes → favor leasing or wait; (3) gateway reward/observer economics shift post-migration → rebalance delegation.

## Caveats
- **Migration flux is the dominant risk.** ar.io's own docs currently contradict each other (token page says "SPL on Solana"; get-the-token page says "AO ARIO (canonical)" and "only ARIO on AO can be used for… staking"). Treat AO as the operationally live environment but expect Solana to become canonical imminently. Verify the exact migration/claim portal URL directly from ar.io — a single definitive Solana-migration claim URL could not be confirmed (airdrop.ar.io is the historical registration portal but unverified for this purpose).
- **The Vento bridge mechanism (lock/mint vs AMM swap) and its exact wallet-connect flow could not be confirmed at the UI level** (the site is client-side JS). Confirm in-app and bridge a test amount first.
- **ArNS prices are dynamic.** All ARIO cost figures use Genesis fees at DF=1; live prices float with demand — always check `arns.ar.io/#/prices`.
- **The immediate miner-vs-endowment fee split is reported inconsistently** across secondary sources (Akord: 16.67% immediate; Permaweb Journal: ~5%); the 0.5% Kryder+ assumption and 200-year design horizon are from primary Arweave docs and are well-corroborated.
- **ArNS registry/ANT model differs by environment.** On AO, registry/ANT state is stored on Arweave via AO; on Solana, ArNS is managed by the `ario-arns` program with ANTs as Metaplex Core NFTs. Tooling targets may differ post-migration; pin your `@ar.io/sdk` version and watch release notes.
- **Storage vs access tokens are distinct.** ARIO pays for AR.IO services (names, staking); permanent *storage* is paid in AR or Turbo Credits. Don't conflate them in budgeting.