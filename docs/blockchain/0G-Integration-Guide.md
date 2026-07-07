# 0G (Zero Gravity) — Full Integration Guide
### EVM settlement on Aristotle Mainnet · Storage · Compute · DA · Node economics
*Verified against docs.0g.ai and the 0glabs/0gfoundation GitHub, June 2026. Supersedes the prior overview; pricing re-checked and node economics expanded.*

---

## 0. Corrected pricing table (read this first)

| Service | Price | Status | Notes |
|---|---|---|---|
| **Storage (Turbo)** | **$11 / TB / month** | ✅ confirmed (0G blog, Mar 2026) | One-time endowment fee model, not a monthly invoice. ~95%/200-year language in that blog is **Arweave's**, not 0G's. |
| Storage throughput | 30+ MB/s production; 50 Gbps architected | ✅ confirmed Mar 2026 | 50 Gbps is a scaling target, not current mainnet. |
| **Compute (inference)** | provider-set, paid per token in **0G** | ⚠️ volatile | Marketplace prices float with provider rates **and** 0G/USD. Treat any specific number as point-in-time. |
| Compute ledger minimums | 3 0G to open ledger; 1 0G locked per provider sub-account | ✅ confirmed (v0.6.x contract) | Router path uses one unified balance instead. |
| **DA blob fee** | **0** by default (`BLOB_PRICE=0`) | ✅ confirmed | Admin-adjustable; budget for it turning on. |
| Chain gas | paid in 0G | ✅ | Standard EVM gas model. |

**Compute caveat (tightened):** earlier per-token figures (e.g., tiered qwen pricing, per-image z-image cost) are **denominated in 0G tokens and set by individual providers on a marketplace**. There is no Router markup — `GET /v1/models` is the source of truth — but the USD-equivalent moves with token price and providers can re-price at will. Do not hard-code these into cost models; pull them live from `/v1/models` (Router) or `broker.inference.listService()` (broker) at runtime.

---

## 1. Network & deployment foundation (Foundry → Aristotle)

0G Chain is a standard EVM L1. Your existing Foundry workflow ports directly; the only non-default requirement is the EVM version.

**`foundry.toml`**
```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
evm_version = "cancun"        # required — newer opcodes otherwise throw "invalid opcode"
optimizer = true
optimizer_runs = 200
via_ir = true                 # enable if any contract uses inline assembly

[rpc_endpoints]
og_mainnet = "https://evmrpc.0g.ai"      # chainId 16661 (Aristotle)
og_testnet = "https://evmrpc-testnet.0g.ai"  # chainId 16602 (Galileo)
```

**Deploy (mainnet, per cypherpunk2048 discipline — mainnet only, no proxies):**
```bash
forge create src/DAIO/Genius.sol:Genius \
  --rpc-url og_mainnet \
  --evm-version cancun \
  --private-key $DEPLOYER_KEY \
  --broadcast
```

**Verify on ChainScan:**
```bash
forge verify-contract \
  --chain-id 16661 \
  --num-of-optimizations 200 \
  --verifier custom \
  --verifier-api-key "PLACEHOLDER" \
  --compiler-version <SOLC_VERSION> \
  <CONTRACT_ADDRESS> src/DAIO/Genius.sol:Genius \
  --verifier-url https://chainscan.0g.ai/open/api
```

If you hit `invalid opcode` on a recent solc, either pin `--evm-version cancun` or step the compiler back (0.8.26 → 0.8.19). For the DAIO Roman-republic dependency order, deploy in sequence and capture each address; nothing about 0G changes your constructor wiring — it's a vanilla EVM target with sub-second CometBFT finality (good for governance UX where you want fast confirmation of votes).

**Key facts for the stack:**
- Chain ID **16661**, RPC `https://evmrpc.0g.ai`, explorer `chainscan.0g.ai`, storage explorer `storagescan.0g.ai`.
- Execution client is Reth (migrated from Geth, network-wide Mar 2026) — expect Ethereum-equivalent behavior.
- Gas paid in 0G. Fund the deployer from a bridge/CEX onramp before deploying.

---

## 2. Storage integration

The pattern for every 0G Storage use is the same three-step shape: **upload → get Merkle root → commit the root on-chain**. The root hash *is* the content address (a 0x-prefixed 66-char hex, deterministic for identical bytes), so your Solidity only ever stores 32 bytes regardless of payload size.

### 2.1 Upload + on-chain commitment (TypeScript)
```ts
import { ZgFile, Indexer } from '@0gfoundation/0g-storage-ts-sdk';
import { ethers } from 'ethers';

const RPC = 'https://evmrpc.0g.ai';
const INDEXER = 'https://indexer-storage-turbo.0g.ai';  // mainnet turbo
const provider = new ethers.JsonRpcProvider(RPC);
const signer   = new ethers.Wallet(process.env.PRIVATE_KEY!, provider);
const indexer  = new Indexer(INDEXER);                  // auto-discovers Flow contract — do NOT pass it

const file = await ZgFile.fromFilePath('./mindx_episode_4412.json');
const [tree, terr] = await file.merkleTree();           // MUST run before upload
if (terr) throw terr;
const rootHash = tree!.rootHash();                      // your content address

const [tx, uerr] = await indexer.upload(file, RPC, signer);
await file.close();                                     // always close
if (uerr) throw uerr;

// Commit the pointer into your contract (e.g. mindX memory registry / DAIO Tabularium)
await memoryRegistry.recordArtifact(agentId, rootHash, /*kind*/ 1);
```
Upload returns `{rootHash, txHash}` for single files or `{rootHashes[], txHashes[]}` for fragmented files >4 GB — handle both with `if ('rootHash' in tx)`. Allow **~3–5 min propagation** across shards before the root is reliably downloadable.

### 2.2 Encrypted-at-rest (matches cypherpunk2048 posture)
The SDK does client-side encryption; the network never sees plaintext.
```ts
// Symmetric (AES-256) — you hold the key, no server-side recovery
const key = crypto.randomBytes(32);
const [tx] = await indexer.upload(file, RPC, signer, { encryption: { type: 'aes256', key } });
const [blob] = await indexer.downloadToBlob(rootHash, { proof: true, decryption: { symmetricKey: key } });

// Encrypt-to-recipient (ECIES) — your wallet's secp256k1 key doubles as the decryption key
const recipientPubKey = ethers.SigningKey.computePublicKey(wallet.signingKey.publicKey, true);
await indexer.upload(file, RPC, signer, { encryption: { type: 'ecies', recipientPubKey } });
```
Note: a wrong key does **not** throw — `downloadToBlob` silently returns ciphertext. Gate on `indexer.peekHeader(rootHash)` (`version 1` = aes256, `2` = ecies, `null` = plaintext) before trusting output.

### 2.3 Python path (mindX backend, 350+ routes)
```python
from core.indexer import Indexer
from core.file import ZgFile
from eth_account import Account

indexer = Indexer("https://indexer-storage-turbo.0g.ai")
account = Account.from_key(PRIVATE_KEY)
f = ZgFile.from_file_path("./checkpoint.thot")
opts = {'tags': b'\x00', 'finalityRequired': True, 'taskSize': 10,
        'expectedReplica': 1, 'skipTx': False, 'account': account}
result, err = indexer.upload(f, "https://evmrpc.0g.ai", account, opts)
f.close()                       # result['rootHash'], result['txHash']
```
`expectedReplica` is your redundancy knob — 0G lets you choose backup count per upload (public datasets minimal, DAIO/financial state higher), unlike Filecoin's fixed 3–6 or Arweave's network-wide model.

### 2.4 Where this maps in your stack
- **mindX agent memory / BDI state** → Storage (KV layer for mutable state, Log layer for append-only episode logs). This is exactly the ETHGlobal pattern 0G showcases: "0G Compute for inference and 0G Storage for agent memory."
- **THOT tensors / model checkpoints / training artifacts** → Log layer, ECIES-encrypted, root committed to your registry.
- **rage.pythai.net publications** → store canonical content, anchor root on-chain for tamper-evidence.
- **agenticplace artifacts** → store the heavy payload off-chain, keep only the 32-byte root in the ERC-8004 registry record.

---

## 3. Storage node economics (run-a-node + how you get paid)

### 3.1 Hardware & footprint
| Component | Storage node | KV node |
|---|---|---|
| RAM | 32 GB | 32 GB |
| CPU | 8 cores | 8 cores |
| Disk | 500 GB–1 TB **SSD** | sized to KV streams |
| Bandwidth | 100 Mbps up/down | — |

SSD is mandatory: PoRA security assumes fast random reads (SSDs hit ~7 GB/s), which is what makes *storing* cheaper than *faking* via outsourced reads.

### 3.2 The reward formula
Rewards are fully decoupled from consensus. You claim by submitting the **first legitimate PoRA** for a mining epoch to the Storage contract. Each winning proof pays two parts:

```
R_total = R_base + R_storage
```
- **R_base** — paid for every accepted proof; **decreases over time** (issuance decay).
- **R_storage** — perpetual. When a PoRA lands in a pricing segment, **half the balance of that segment's Reward Pool** is claimed.

The Reward Pool is fed by user upload fees via an endowment:
- Storage is divided into **pricing segments every 8 GB**.
- Each segment has an **Endowment Pool** (collects upload fees for its chunks) and a **Reward Pool**.
- The Endowment Pool **releases to the Reward Pool every second at 4%/year**.

So a user's one-time $11/TB-equivalent fee is *reservoired per-8GB-segment* and bled to miners at 4%/yr — that 4% drip, not the headline price, is what you model node yield against.

### 3.3 Second income stream: data-sharing royalty
When Node B builds a valid PoRA from data Node A shared, **Node A receives a royalty** out of B's reward. Serving sync to peers is therefore revenue, not pure cost — keep `auto_sync` sensible rather than starving neighbors.

### 3.4 Fairness cap & multi-instance scaling
Mining range is **capped at 8 TB per operation**. Individuals run a single 8 TB range (still profitable); large operators run **multiple 8 TB instances** to mine several ranges in parallel. This is the lever for scaling node revenue horizontally.

### 3.5 The reward-contract model determines your real yield curve
`0g-storage-contracts` ships three interchangeable Reward implementations — confirm which is live before modeling returns:
- **ChunkDecayReward** — per-chunk pools, 25-year half-life release.
- **ChunkLinearReward** — fixed-time linear release (better capital utilization).
- **OnePoolReward** — single pool over a rolling window (e.g., only data from the last ~3 months is mineable).

Mainnet contracts: Flow `0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526`, Mine `0xCd01c5Cd953971CE4C2c9bFb95610236a7F414fe`, Reward `0x457aC76B58ffcDc118AABD6DbC63ff9072880870`. Query the live Reward impl + per-segment Endowment depth on `storagescan.0g.ai` to estimate yield; 0G publishes no static "0G/day per TB" figure because real return = f(reward model, endowment depth, your share of network storage, your proof win-rate).

### 3.6 Sharding (limited-disk operation)
`shard_position = "<shard_id>/<shard_number>"`, shard_number a power of 2.
- `"0/2"` → 50% of data; `"0/4"` → 25%.
- Sizing: `shard_number = ceil( total_network_data / (disk_capacity × 0.75) )`, rounded up to a power of 2.
- **Gotcha:** initial placement is deterministic, but when network data outgrows your disk the node **auto-doubles** shard_number and **randomly reassigns** your shard_id — you can't pick it.

### 3.7 Setup spine (mainnet)
```bash
git clone -b <latest_tag> https://github.com/0gfoundation/0g-storage-node.git
cd 0g-storage-node && cargo build --release
cp run/config-mainnet-turbo.toml run/config.toml
# set in config.toml:
#   blockchain_rpc_endpoint = "https://evmrpc.0g.ai"
#   log_sync_start_block_number = 2387557
#   log/mine/reward contract addresses (from Mainnet Overview)
#   miner_key = "<64 hex chars, no 0x>"
../target/release/zgs_node --config run/config.toml
```
Run under systemd (`LimitNOFILE=65545`, `Restart=on-failure`).

**Two traps that cost real money:**
1. From a 3rd-party snapshot, include only `flow_db` and **delete `data_db`** — using someone else's `data_db` makes your node mine *for them*.
2. `miner_key` is a hot key by necessity; anyone holding it can claim your rewards. Isolate it.

---

## 4. Compute integration

Two access paths. Use the **Router** for server-side mindX inference; use the **broker SDK** when a browser dApp (PARSEC) must sign each call with the user's wallet.

### 4.1 Router path (recommended for mindX backend)
One OpenAI-compatible endpoint, one balance, automatic provider failover, no per-call signing.
```python
from openai import OpenAI
client = OpenAI(base_url="https://router-api.0g.ai/v1", api_key=ROUTER_KEY)
r = client.chat.completions.create(
    model="deepseek-chat-v3-0324",
    messages=[{"role":"user","content": prompt}],
    extra_body={"sort": "price"}      # cheapest healthy provider; omit for default failover
)
```
- Works with any OpenAI client (openai-python/node, LangChain, LlamaIndex, Vercel AI SDK) — change `base_url` + `api_key` only.
- **No Router markup** — catalog price = what you pay. Pull live prices from `GET /v1/models`.
- Paid in 0G: deposit once to the Router payment contract; it handles conversion and provider payout.
- `503 no_providers_available` if every provider for a model is unhealthy — handle it.

### 4.2 Broker path (PARSEC / wallet-signed)
```ts
import { ethers } from 'ethers';
import { createZGComputeNetworkBroker } from '@0gfoundation/0g-compute-ts-sdk'; // (formerly @0glabs/0g-serving-broker)

const broker = await createZGComputeNetworkBroker(signer);     // Wallet or browser JsonRpcSigner
await broker.ledger.addLedger(3);                               // ≥3 0G to open ledger
const providerAddr = '0x...';                                   // from broker.inference.listService()
await broker.inference.acknowledgeProviderSigner(providerAddr); // once per provider
await broker.ledger.transferFund(providerAddr, "inference", ethers.parseEther("1.0")); // ≥1 0G per provider

const { endpoint, model } = await broker.inference.getServiceMetadata(providerAddr);
const headers = await broker.inference.getRequestHeaders(providerAddr, prompt); // SINGLE-USE
const res = await fetch(`${endpoint}/chat/completions`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', ...headers },
  body: JSON.stringify({ model, messages: [{ role:'user', content: prompt }] })
});
```
- **Billing headers are the settlement proof** and are **single-use** — regenerate per request or you get failures.
- Settlement is **batched** by the provider at intervals (not per-call on-chain).
- Browser mode does **not** auto-fund sub-accounts (would spam wallet popups) — fund explicitly.

### 4.3 TEE verification (do this for any agent that signs transactions)
Inference runs in Intel TDX + NVIDIA H100/H200 enclaves (TeeML for self-hosted models, TeeTLS for proxied closed models). To verify the model you asked for is the model that ran:
```ts
const valid = await broker.inference.processResponse(providerAddr, content, chatID);
// chatID comes from the response; returns true iff the provider's signature over the output checks out
```
For mindX agents that trigger on-chain actions (DAIO votes, PARSEC/BANKON payments), gate execution on `processResponse === true`. This is the difference between "decentralized inference" and "a remote API you trust blindly."

### 4.4 Agent identity — ERC-7857 (iNFT)
0G ships **ERC-7857**, a live agentic-identity / iNFT standard: on ownership transfer, agent memory is re-encrypted inside the same enclave used for inference. For agenticplace, this composes with your **ERC-8004 Identity Registry** — ERC-8004 is the on-chain identity/discovery record; ERC-7857 carries the *transferable encrypted memory* of the agent instance. Store the heavy memory blob in 0G Storage (ECIES), reference its root from the ERC-7857 token, and keep the ERC-8004 record as the public-facing identity. Fine-tuning is available via `0g-compute-cli fine-tuning` (CVM-isolated, escrow released on verified completion) if mindX agents need bespoke adapters.

---

## 5. 0G DA (treat as testnet-grade for now)

0G DA erasure-codes blobs (≤~32 MB → 3072×1024 matrix), commits via **KZG (BN254)** + Merkle root, selects signer quorums by **VRF**, and finalizes on **>2/3 BLS aggregate signatures**; DA signers verify/sign/store but validators finalize. It integrates with **OP Stack** (da-server + 0G DA Open API) and **Arbitrum Nitro** (`das/zerogravity.go`).

**Caveat that gates production use:** the Mainnet Overview lists **no mainnet DAEntrance address**, and documented DA staking/`BLOB_PRICE` still point at testnet (`0x857C0A28...`, `BLOB_PRICE=0`). If a DELTAVERSE appchain/rollup needs DA, pilot on testnet and confirm a mainnet DA contract with the 0G team before committing. The "50 Gbps / 50,000× Ethereum DA" figures are **Galileo testnet benchmarks**, not guaranteed mainnet throughput.

---

## 6. The settlement-domain boundary: 0G EVM ↔ x402-Algorand

This is the one architectural seam to get right. **0G is an EVM domain (chainId 16661); your x402 payment rail is Algorand (CAIP-2 `algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=`, USDC ASA 31566704, GoPlausible facilitator).** These are *separate settlement domains*. 0G does not natively settle Algorand x402, and x402-avm does not natively settle 0G gas/compute. Pick a topology deliberately:

| Concern | Settle on 0G (EVM) | Settle on Algorand (x402-avm) |
|---|---|---|
| 0G storage upload fees | ✅ native (0G token) | ✗ |
| 0G compute/inference | ✅ native (0G token, Router/broker) | ✗ |
| DAIO governance, PYTHAI/PAI token state | ✅ native EVM | ✗ |
| AgentPay / API metering / micropayments | possible (EVM x402 / on-chain) | ✅ your existing exact-scheme rail |
| ERC-8004 / ERC-7857 agent identity | ✅ native EVM | ✗ |

**Recommended split:** keep **agent identity, governance, token state, and 0G-service payments on 0G/EVM**; keep **commerce/API-metering micropayments on the Algorand x402 rail** where you already have GoPlausible + USDC ASA wired. Bridge only *value summaries*, not every transaction:
- For EVM↔Algorand value movement, you need an explicit bridge (LayerZero-style messaging or a facilitator that attests cross-domain) — there is no built-in 0G↔Algorand path. Treat this as a deliberate, audited component, not an afterthought.
- For an **AgentPay Commerce** flow: agent identity + inference verification on 0G; the actual buyer→seller settlement on x402-avm; anchor the x402 receipt hash into 0G Storage (root committed on 16661) so the EVM side has tamper-evident proof of the Algorand-side payment without the two domains having to share consensus.

This keeps each domain doing what it's best at and avoids forcing 0G to understand Algorand finality (or vice-versa).

---

## 7. End-to-end reference flow (mindX agent on agenticplace, paid via AgentPay)

1. **Identity** — agent registered in ERC-8004 registry (mainnet `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`); instance memory carried as ERC-7857 iNFT on 0G.
2. **Memory** — BDI state + episode logs in 0G Storage (KV mutable + Log append-only), ECIES-encrypted, roots committed to your registry contract on 16661.
3. **Cognition** — mindX calls inference via Router (server) or broker (PARSEC dApp); `processResponse` verifies TEE signature before any state-changing action.
4. **Governance** — DAIO contracts (Genius/Senatus/Curia/…) deployed via Foundry on Aristotle; 9/13 supermajority votes confirm with sub-second finality.
5. **Commerce** — buyer pays the agent over the **Algorand x402-avm** rail (USDC ASA, GoPlausible exact scheme); the x402 receipt hash is stored to 0G Storage and its root anchored on 16661 for cross-domain proof.
6. **Publication** — outputs published to rage.pythai.net with the canonical artifact in 0G Storage, root on-chain for tamper-evidence.

Every step is mainnet (cypherpunk2048: no proxies, no admin keys post-deploy, Foundry-tested), and every cross-domain hop is an explicit, auditable anchor rather than an implicit trust assumption.

---

## 8. Integration checklist

- [ ] `foundry.toml` with `evm_version = "cancun"`, `via_ir = true`; deployer funded with 0G.
- [ ] DAIO + token contracts deployed in Roman-republic dependency order on 16661, verified on ChainScan.
- [ ] Storage SDK wired (TS for PARSEC, Python for mindX); upload→root→on-chain-commit pattern in place; ECIES for sensitive blobs; `peekHeader` guard before trusting decrypts.
- [ ] Compute: Router key for backend; broker SDK for wallet-signed dApp calls; `processResponse` gating any agent-triggered on-chain action; live pricing pulled from `/v1/models`, never hard-coded.
- [ ] ERC-7857 iNFT memory linked to ERC-8004 identity; heavy memory in Storage.
- [ ] DA: testnet pilot only until a mainnet DAEntrance address is confirmed.
- [ ] Settlement boundary documented: 0G/EVM for identity+governance+0G-services; Algorand x402 for commerce; cross-domain proofs anchored as Storage roots.
- [ ] (Optional revenue) storage node(s): SSD, 8 TB range(s), live Reward-impl + endowment depth checked on storagescan before modeling yield; `miner_key` isolated; snapshot `data_db` deleted.

---

## Sources & verification notes
- Storage $11/TB Turbo, 30+ MB/s, endowment framing — 0G blog "Decentralized Storage for AI" (Mar 2026). The 95%/200-year endowment line in that post describes **Arweave**, not 0G.
- Mining reward (R_base + R_storage, 8 GB pricing segments, 4%/yr endowment release) — `0g-storage-node/docs/incentive-mechanism/mining-reward.md`.
- Reward-contract variants — `0glabs/0g-storage-contracts` README.
- PoRA, 8 TB cap, sealing economics, data-sharing royalty — 0G whitepaper breakdown + whitepaper PDF.
- Node hardware, config, sharding, snapshot trap — `docs.0g.ai/run-a-node/storage-node`.
- Storage SDK (ZgFile/merkleTree/Indexer, encryption, fragmentation) — `docs.0g.ai` Storage SDK + `0g-storage-ts-starter-kit`; Python — `0g-storage-sdk` (PyPI).
- Compute (Router base URL, broker `createZGComputeNetworkBroker`, ledger minimums, single-use headers, processResponse, no Router markup) — `docs.0g.ai` Inference/Compute + `0g-compute-ts-starter-kit` + Router FAQ.
- Foundry/Hardhat config, chain IDs 16661/16602, evmVersion cancun, verify — `docs.0g.ai` Deploy Contracts + `awesome-0g`.
- DA (KZG/BN254, VRF quorums, BLS 2/3, OP/Nitro integration, testnet contract) — `docs.0g.ai` DA + rollup integration pages.
- Compute token pricing is provider-set and 0G-denominated; pull live, do not hard-code.
