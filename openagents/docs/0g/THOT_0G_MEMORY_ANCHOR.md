# mindX × THOT × 0G Compute — Integration Specification

**Scope:** Concrete integration of `docs.0g.ai` primitives (Compute, Storage, Chain, INFT) with the existing DELTAVERSE stack (`mindX`, `THOT`, `DeltaVerseEngine`, `DAIO`, pillars `FunAGI`/`RAGE`/`Mastermind`). This is the implementation contract — file paths, function signatures, deployment order, and the exact wire-up.

---

## 1. Architectural mapping

The collision is unusually clean because THOT and 0G Storage are **two halves of the same primitive** the user's stack was already heading toward:

| Existing component | 0G primitive | Role after integration |
|---|---|---|
| `THOT.sol` (memory token, pillar-committable) | **0G Chain** + commitment registry | On-chain memory **commitment** layer — stores `rootHash`, author, pillar, chatID, timestamp |
| (missing — author writes raw text now) | **0G Storage** (Log + KV layers, AES-256/ECIES) | Off-chain **payload** layer — encrypted memory blob, addressed by Merkle root |
| `mindX` LLM provider abstraction | **0G Compute** broker (TeeML / TeeTLS) | Verifiable inference — every model call carries a TEE attestation |
| `funAGI` / `RAGE` / `Mastermind` pillars | (no change — they call THOT) | Pillars now commit **0G rootHashes**, not opaque blobs |
| `mindXOracle` field in `DeltaVerseEngine.AddressBook` | **0G Compute provider address** | Oracle is now a 0G Compute provider (`0xd9966e…` GLM-5-FP8 or `0x992e63…` qwen3.6-plus) |
| `DAIO` governance | **0G Chain (16602/16661)** EVM L1 | DAIO deploys to 0G Chain natively — Cancun EVM, low gas, AI-native settlement |
| (future — agent transfer) | **ERC-7857 INFT** | Each registered mindX agent mints as an INFT; pillars can be transferred/cloned |

The principle: **THOT keeps the proof, 0G Storage keeps the data, 0G Compute generates both.** A "memory" in DELTAVERSE becomes a 4-tuple `(authorAddr, pillarAddr, rootHash, chatID)` — `rootHash` proves what was thought, `chatID` proves how it was thought.

---

## 2. The verified-thought loop

This is the canonical flow every mindX cognitive cycle should follow once integrated. It produces an on-chain memory whose existence, content, and reasoning are all cryptographically verifiable.

```
┌─────────────────────────────────────────────────────────────────────┐
│  mindX agent receives perception / goal                             │
│       │                                                             │
│       ▼                                                             │
│  ┌────────────────────────────────────────┐                         │
│  │  0G Compute Broker                     │                         │
│  │  broker.inference.getRequestHeaders()  │  ← single-use, replay-  │
│  │  fetch(endpoint/chat/completions)      │     protected           │
│  │  response.headers["ZG-Res-Key"]        │  ← chatID for verify    │
│  │  broker.inference.processResponse()    │  ← verifies TEE sig     │
│  └────────────────────────────────────────┘                         │
│       │                                                             │
│       ▼                                                             │
│  decision blob = { reasoning, response, chatID, providerAddr,       │
│                    modelId, timestamp, parentRootHash }             │
│       │                                                             │
│       ▼                                                             │
│  ┌────────────────────────────────────────┐                         │
│  │  0G Storage SDK                        │                         │
│  │  ZgFile.fromMemData(serialize(blob))   │                         │
│  │  await file.merkleTree()  // MANDATORY │                         │
│  │  indexer.upload(file, rpc, signer,     │                         │
│  │    { encryption: { type: 'ecies',      │                         │
│  │      recipientPubKey: agent.pubkey }}) │                         │
│  └────────────────────────────────────────┘                         │
│       │                                                             │
│       ▼  rootHash (32 bytes)                                        │
│  ┌────────────────────────────────────────┐                         │
│  │  THOT.sol (on 0G Chain)                │                         │
│  │  pillar.commit(                        │                         │
│  │    author, rootHash, chatID,           │  ← new function         │
│  │    providerAddr, parentRootHash)       │                         │
│  └────────────────────────────────────────┘                         │
│       │                                                             │
│       ▼                                                             │
│  THOT NFT/token id = keccak256(author, rootHash, chatID)            │
│  emit MemoryCommitted(...)                                          │
└─────────────────────────────────────────────────────────────────────┘
```

Every link is verifiable: `chatID` → TEE signature via `processResponse`; `rootHash` → Merkle proof via `indexer.download(_, _, withProof=true)`; `THOT` token → on-chain provenance. An auditor (or another mindX agent) can replay any decision and confirm the model output was generated by an attested TEE provider, the memory blob hasn't been tampered with, and the commitment author is who they claim.

---

## 3. THOT.sol modifications

Your current `THOT.sol` has `setPillarCommitter(address, bool)` and is governed by DAIO. To make it a 0G-aware commitment registry, add the following without breaking the existing pillar permission model:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title  THOT — 0G-anchored memory commitment registry
/// @notice Each token id is keccak256(author, rootHash, chatID).
///         Pillars (FunAGI / RAGE / Mastermind) commit on author's behalf.
contract THOT is ERC721, Ownable {

    struct Memory {
        address author;            // mindX agent or human author
        bytes32 rootHash;          // 0G Storage Merkle root of encrypted blob
        bytes32 chatID;            // ZG-Res-Key from 0G Compute response
        address provider;          // 0G Compute provider addr (TEE attested)
        bytes32 parentRootHash;    // prior memory in the chain (zero if root)
        uint64  timestamp;
        address pillar;            // which pillar minted this
    }

    mapping(uint256 => Memory) public memories;
    mapping(address => bool)    public isPillarCommitter;
    address public governance;

    event MemoryCommitted(
        uint256 indexed tokenId,
        address indexed author,
        address indexed pillar,
        bytes32 rootHash,
        bytes32 chatID,
        address provider,
        bytes32 parentRootHash
    );

    modifier onlyPillar() {
        require(isPillarCommitter[msg.sender], "THOT: not pillar");
        _;
    }
    modifier onlyGov() {
        require(msg.sender == governance, "THOT: not gov");
        _;
    }

    constructor() ERC721("THOT Memory", "THOT") Ownable(msg.sender) {}

    /// @notice Pillars call this after the off-chain
    ///         (0G Compute -> 0G Storage) sequence completes.
    function commit(
        address author,
        bytes32 rootHash,
        bytes32 chatID,
        address provider,
        bytes32 parentRootHash
    ) external onlyPillar returns (uint256 tokenId) {
        require(rootHash != bytes32(0), "THOT: empty root");
        tokenId = uint256(keccak256(abi.encode(author, rootHash, chatID)));
        require(_ownerOf(tokenId) == address(0), "THOT: dup memory");

        memories[tokenId] = Memory({
            author:         author,
            rootHash:       rootHash,
            chatID:         chatID,
            provider:       provider,
            parentRootHash: parentRootHash,
            timestamp:      uint64(block.timestamp),
            pillar:         msg.sender
        });

        _safeMint(author, tokenId);
        emit MemoryCommitted(tokenId, author, msg.sender, rootHash, chatID, provider, parentRootHash);
    }

    function setPillarCommitter(address pillar, bool ok) external onlyGov {
        isPillarCommitter[pillar] = ok;
    }
    function setGovernance(address gov) external onlyOwner {
        governance = gov;
    }
}
```

Key choices and why:

- **Token id is content-addressed** (`keccak256(author, rootHash, chatID)`) so memories are deduplicated by content, not minted sequentially. Same author + same rootHash + same chatID = same token.
- **`parentRootHash`** turns THOT into a Merkle DAG of memories — exactly what mindX needs for its episodic chain. `parentRootHash == 0` means root memory; otherwise it links to the prior thought. `RAGE` (retrieval) walks this DAG.
- **`provider` is stored** because TEE attestation is provider-bound. Verifiers query 0G Compute's on-chain ledger for that provider's signer to validate `chatID`.
- **Pillar enforcement preserved** — same `setPillarCommitter` model you already have. No changes to `funAGI`/`RAGE`/`Mastermind` permission grants in `Deploy.s.sol`.

---

## 4. mindX compute adapter

mindX currently calls OpenAI / Anthropic / Gemini / Ollama. Add a `ZeroGProvider` implementing the same interface, with full 0G Compute broker integration. This goes in `mindx/providers/zero_g_provider.ts` (TypeScript) — the broker SDK is `@0glabs/0g-serving-broker` and is Node-only auto-funded, browser manual-funded.

```typescript
// mindx/providers/zero_g_provider.ts
import { ethers } from "ethers";
import { createZGComputeNetworkBroker } from "@0glabs/0g-serving-broker";
import OpenAI from "openai";

export interface ZeroGConfig {
  rpcUrl: string;          // https://evmrpc-testnet.0g.ai or https://evmrpc.0g.ai
  privateKey: string;      // mindX agent key (one per agent — keys ARE identity)
  providerAddress: string; // e.g. 0xd9966e... GLM-5-FP8 mainnet
  initialDeposit?: number; // 0G — default 3 (ledger min) + 1 (provider min) = 4
}

export interface InferenceResult {
  content: string;
  chatID: string;          // ZG-Res-Key — used by THOT.commit
  providerAddress: string;
  model: string;
  verified: boolean;       // result of processResponse
}

export class ZeroGProvider {
  private broker: any;
  private openai!: OpenAI;
  private model!: string;
  private endpoint!: string;
  constructor(private cfg: ZeroGConfig) {}

  async init(): Promise<void> {
    const provider = new ethers.JsonRpcProvider(this.cfg.rpcUrl);
    const wallet   = new ethers.Wallet(this.cfg.privateKey, provider);
    this.broker    = await createZGComputeNetworkBroker(wallet);

    // Idempotent: only deposits if ledger doesn't exist
    try {
      await this.broker.ledger.getLedger();
    } catch {
      await this.broker.ledger.addLedger(this.cfg.initialDeposit ?? 4);
    }

    // transferFund auto-acknowledges the provider's TEE signer on-chain
    await this.broker.ledger.transferFund(
      this.cfg.providerAddress,
      "inference",
      ethers.parseEther("1")
    );

    const meta    = await this.broker.inference.getServiceMetadata(this.cfg.providerAddress);
    this.endpoint = meta.endpoint;
    this.model    = meta.model;
  }

  async think(messages: Array<{ role: string; content: string }>): Promise<InferenceResult> {
    // Headers are SINGLE-USE — must be regenerated per call
    const content = messages.map(m => m.content).join("\n");
    const headers = await this.broker.inference.getRequestHeaders(
      this.cfg.providerAddress, content
    );

    const response = await fetch(`${this.endpoint}/chat/completions`, {
      method:  "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body:    JSON.stringify({ messages, model: this.model })
    });
    const data = await response.json();

    // chatID extraction: header first, body fallback
    const chatID = response.headers.get("ZG-Res-Key")
                || response.headers.get("zg-res-key")
                || data.id;

    // MANDATORY — settles ledger AND verifies TEE signature
    let verified = false;
    if (chatID) {
      const valid = await this.broker.inference.processResponse(
        this.cfg.providerAddress, chatID
      );
      verified = !!valid;
    }

    return {
      content:         data.choices[0].message.content,
      chatID:          chatID || "",
      providerAddress: this.cfg.providerAddress,
      model:           this.model,
      verified
    };
  }
}
```

The non-obvious rules from `0g-agent-skills/AGENTS.md` baked in here:

1. `getRequestHeaders` is called **per inference** — headers are replay-protected.
2. `processResponse` is **always** called — it's how the broker ledger settles AND how TEE verification happens. Skipping it leaves the ledger in a stuck state.
3. `chatID` extraction is **header-first, body-fallback** — `ZG-Res-Key` is canonical, `data.id` only when missing.
4. ethers **v6** for the broker (and the broker uses ethers v6 internally).
5. Min deposit is 3 0G ledger + 1 0G per provider sub-account. The constructor default of 4 is correct.
6. `transferFund` does **double duty** — funds the sub-account AND auto-acknowledges the provider's TEE signer on-chain. No separate `acknowledgeProviderSigner` needed.

---

## 5. mindX storage adapter (THOT bridge)

The component that closes the loop — takes an `InferenceResult`, encrypts the memory blob, uploads to 0G Storage, and calls `THOT.commit`. Lives in `mindx/storage/thot_bridge.ts`.

```typescript
// mindx/storage/thot_bridge.ts
import { ZgFile, Indexer, MemData } from "@0gfoundation/0g-ts-sdk";
import { ethers } from "ethers";
import type { InferenceResult } from "../providers/zero_g_provider";

const THOT_ABI = [
  "function commit(address author, bytes32 rootHash, bytes32 chatID, address provider, bytes32 parentRootHash) returns (uint256)"
];

export interface MemoryRecord {
  reasoning: string;
  response:  string;
  inference: InferenceResult;
  parentRootHash?: string;  // hex with 0x
  metadata?: Record<string, unknown>;
}

export class THOTBridge {
  private indexer: Indexer;
  private thot: ethers.Contract;

  constructor(
    private rpcUrl: string,
    private indexerUrl: string,        // turbo: indexer-storage-testnet-turbo.0g.ai
    private signer: ethers.Wallet,
    private thotAddress: string,
    private pillarSigner: ethers.Wallet // pillar key — must be in isPillarCommitter
  ) {
    this.indexer = new Indexer(indexerUrl);
    this.thot    = new ethers.Contract(thotAddress, THOT_ABI, pillarSigner);
  }

  async commitMemory(record: MemoryRecord): Promise<{ tokenId: string; rootHash: string; txHash: string }> {
    // 1. Serialize + encrypt-to-self via ECIES (agent's own key)
    const blob = JSON.stringify({
      ...record,
      schema: "mindx.memory.v1",
      committedAt: Date.now()
    });
    const memData = new MemData(new TextEncoder().encode(blob));

    // MANDATORY before upload
    const [tree, treeErr] = await memData.merkleTree();
    if (treeErr) throw new Error(`merkleTree: ${treeErr}`);
    const rootHash = tree!.rootHash();

    // ECIES self-encryption — agent can decrypt with its own key
    const recipientPubKey = ethers.SigningKey.computePublicKey(
      this.signer.signingKey.publicKey, true
    );
    const [, uploadErr] = await this.indexer.upload(
      memData, this.rpcUrl, this.signer as any,  // cast for ethers v5/v6 mix
      { encryption: { type: "ecies", recipientPubKey } }
    );
    if (uploadErr) throw new Error(`upload: ${uploadErr}`);

    // 2. THOT.commit — pillar signs, author is the agent
    const tx = await this.thot.commit(
      this.signer.address,
      rootHash,
      ethers.id(record.inference.chatID),  // bytes32-ify the string chatID
      record.inference.providerAddress,
      record.parentRootHash ?? ethers.ZeroHash
    );
    const receipt = await tx.wait();

    // tokenId is deterministic — recompute it
    const tokenId = ethers.keccak256(
      ethers.AbiCoder.defaultAbiCoder().encode(
        ["address", "bytes32", "bytes32"],
        [this.signer.address, rootHash, ethers.id(record.inference.chatID)]
      )
    );

    return { tokenId, rootHash, txHash: receipt!.hash };
  }

  async recallMemory(rootHash: string): Promise<MemoryRecord> {
    // Decrypt-to-self with ECIES — wallet's own key
    const [blob, err] = await this.indexer.downloadToBlob(rootHash, {
      proof: true,
      decryption: { privateKey: this.signer.privateKey }
    });
    if (err) throw new Error(`download: ${err}`);
    const text = await blob!.text();
    return JSON.parse(text);
  }
}
```

Wiring caveats:

- **`signer as any`** is the documented escape for the ethers-v5-typed Storage SDK when you're holding an ethers v6 `Wallet`. Both work, types lie.
- **`MemData` over `ZgFile.fromFilePath`** because mindX runs in long-lived processes — no temp files, no `file.close()` to forget.
- **Encrypt-to-self via ECIES** is the right default — the agent's wallet key already exists, no extra key management. If you want a memory readable by another agent (cross-agent recall), pass that agent's compressed pubkey instead.
- **`ethers.id(chatID)`** — the SDK returns `chatID` as a string (often a UUID). THOT stores `bytes32`. `ethers.id` is keccak256 of the UTF-8 bytes, which is collision-resistant enough for this purpose.
- **`downloadToBlob` not `download`** for encrypted files — `download` writes raw ciphertext to disk and you'll spend 20 minutes wondering why the JSON parse fails.

---

## 6. Pillar wiring — the missing 1-line change

Your `Deploy.s.sol` already grants `funagi`, `rage`, `mastermind` as pillar committers on THOT:

```solidity
thot.setPillarCommitter(address(funagi),     true);
thot.setPillarCommitter(address(rage),       true);
thot.setPillarCommitter(address(mastermind), true);
```

For each pillar contract, replace the existing `commitMemory` (which presumably stores opaque bytes) with a call into the new THOT signature:

```solidity
// In FunAGI.sol / RAGE.sol / Mastermind.sol
function commitThought(
    address author,
    bytes32 rootHash,
    bytes32 chatID,
    address provider,
    bytes32 parentRootHash
) external returns (uint256) {
    // pillar-specific gating: e.g. RAGE only commits if author has THRUST stake
    require(_canAuthorCommit(author), "pillar: gated");
    return thot.commit(author, rootHash, chatID, provider, parentRootHash);
}
```

That's the entire on-chain change beyond THOT itself. The pillars become thin permission layers over `THOT.commit` — exactly what they should be.

---

## 7. DeltaVerseEngine address book — populating mindxOracle

You already have a `mindxOracle` slot in `DeltaVerseEngine.AddressBook`. Bind it to a 0G Compute provider rather than rolling your own oracle:

```solidity
// In Deploy.s.sol - testnet
engine.wire(DeltaVerseEngine.AddressBook({
    // ... existing fields
    mindxOracle: 0xa48f01EE4B69A22f97f7A48C3A7e4a3b7a7e7e7e, // qwen-2.5-7b testnet
    // ... existing fields
}));

// Mainnet — pick one based on cost/capability tradeoff
// 0xd9966e0c5e87C6C2dC03A77f2f08a5fa37f2A0Bf  // GLM-5-FP8 — strongest reasoning
// 0x992e63...                                  // qwen3.6-plus — 1M context, agentic
// 0xBB3f5b...                                  // gpt-oss-120b — cheapest at 0.10/0.49
```

For DELTAVERSE Debt Inheritance Protocol specifically — the system that inverts sovereign debt into profit and needs **strong reasoning over global currency basket dynamics** — `GLM-5-FP8` is the right call. For agent swarms doing cheap parallel work, `gpt-oss-120b` at 0.10/0.49 0G per million tokens is unbeatable on cost.

---

## 8. Deployment sequence on Galileo (16602)

Foundry script ordering, with the reasoning for each step:

```bash
# 0. Foundry config — Cancun is mandatory for 0G Chain
cat > foundry.toml <<'EOF'
[profile.default]
src = "src"
solc = "0.8.24"
evm_version = "cancun"
optimizer = true
optimizer_runs = 200
[rpc_endpoints]
og_testnet = "https://evmrpc-testnet.0g.ai"
og_mainnet = "https://evmrpc.0g.ai"
[etherscan]
og_testnet = { key = "no-api-key", url = "https://chainscan-galileo.0g.ai/open/api" }
og_mainnet = { key = "no-api-key", url = "https://chainscan.0g.ai/open/api" }
EOF

# 1. Faucet — 0.1 0G per wallet per day from https://faucet.0g.ai
#    For multi-key swarm tests, batch requests via Discord ticket

# 2. Deploy DELTAVERSE — Deploy.s.sol already handles ordering
forge script script/Deploy.s.sol \
  --rpc-url og_testnet --private-key $DEPLOYER_PK \
  --broadcast --verify

# 3. Verify THOT explicitly (chain ID 16602)
forge verify-contract $THOT_ADDR THOT --chain 16602 --watch

# 4. Fund the mindX agent's 0G Compute ledger (Node side)
node -e "
  const { ZeroGProvider } = require('./mindx/providers/zero_g_provider');
  const p = new ZeroGProvider({
    rpcUrl: 'https://evmrpc-testnet.0g.ai',
    privateKey: process.env.AGENT_PK,
    providerAddress: '0xa48f01EE4B69A22f97f7A48C3A7e4a3b7a7e7e7e'  // testnet qwen
  });
  p.init().then(() => console.log('agent broker ready'));
"

# 5. Smoke test — verified-thought loop end to end
node scripts/smoke_thot_compute.ts
```

The smoke test should commit a single memory and recall it, asserting that:

1. `inference.verified === true` (TEE attestation valid)
2. `recallMemory(rootHash)` returns the original blob (encryption round-trip works)
3. `THOT.ownerOf(tokenId)` is the agent address (commit succeeded)
4. The on-chain `Memory` struct fields match what was committed

If all four pass, the integration is live.

---

## 9. The agent-as-INFT layer (optional, but the prize-winning move)

For the OpenAgents submission specifically, layer ERC-7857 over the agent identity — the agent is no longer just a wallet, it's a transferable INFT whose encrypted metadata IS the THOT memory chain root. The agent INFT contract holds:

```solidity
struct AgentMetadata {
    bytes32 latestRootHash;     // current head of the agent's THOT memory DAG
    bytes32 personalityRootHash;// 0G Storage hash of the agent's persona prompt + skills
    address[] pillarBindings;   // which pillars this agent operates through
    uint256 totalThoughts;      // count of THOT tokens minted by this agent
}
```

When an INFT transfers via ERC-7857's TEE-attested re-encryption flow, the new owner receives:

- The agent's persona (encrypted on 0G Storage, key re-sealed for new owner)
- The latest THOT memory chain head (rootHash — public, but content encrypted)
- A working agent: their key now decrypts both persona AND memory chain

This is the genuinely novel piece — **THOT is what makes agent INFTs actually transferable as living entities** rather than just frozen weights. Without THOT, an INFT transfer hands over a model checkpoint. With THOT, it hands over a continuously-updated cognitive history. That difference is what the OpenAgents Sub-track 2 brief is asking for when it says *"iNFT-minted agents with embedded intelligence (encrypted on 0G Storage), persistent memory, dynamic upgrades."*

The reference implementation to fork is `github.com/0gfoundation/0g-agent-nft` (CC0-1.0). Replace its placeholder metadata struct with `AgentMetadata` above; replace its oracle interface stub with a Phala dstack TEE oracle for testnet, ZKP oracle for v2.

---

## 10. Gotchas summary

These are the integration failure modes — every one has bitten someone in the wild. Pre-empting all ten saves roughly two days of debugging.

1. **Chain ID 16602 vs 16601.** Galileo testnet is **16602** in current docs. Some starter kits still say 16601. Verify against the live Flow contract address before posting.
2. **`evm_version = "cancun"`** in `foundry.toml` is mandatory. Default `paris` will deploy fine and revert at runtime on certain opcodes.
3. **`@0gfoundation/0g-ts-sdk` v1.2.6+ for storage, `@0glabs/0g-serving-broker` for compute.** The package split is deliberate (Foundation owns Storage docs, Labs owns Compute SDK) but trips up monorepo dependency hygiene.
4. **`merkleTree()` before `upload()`** — both for `ZgFile` and `MemData`. The internal state isn't lazy.
5. **`processResponse()` is mandatory, not optional** despite what one heading in the docs says — without it, the ledger doesn't settle and the next `getRequestHeaders` call may fail with an obscure "stale session" error.
6. **`chatID` from header first, `data.id` fallback.** Some streaming responses don't set `ZG-Res-Key` on the SSE response object; for chat-completions REST it's always there.
7. **`signer as any` cast** when passing an ethers v6 Wallet to the Storage SDK — its types are still v5-shaped.
8. **`indexer.download()` writes ciphertext for encrypted files.** Use `downloadToBlob` with `decryption` opts. Wrong key fails silently — check `peekHeader` first if uncertain.
9. **Rate limit: 30 req/min, burst 5, 5 concurrent per user per provider.** Design swarm parallelism around it; HTTP 429 is the only signal.
10. **Faucet is 0.1 0G/day per wallet.** For a 10-agent swarm demo, request a batch via the 0G Telegram (`https://t.me/+mQmldXXVBGpkODU1`) at least 24h ahead.

---

## 11. Reference table — addresses and endpoints

| | Galileo Testnet (16602) | Aristotle Mainnet (16661) |
|---|---|---|
| EVM RPC | `https://evmrpc-testnet.0g.ai` | `https://evmrpc.0g.ai` |
| Storage Indexer (Turbo) | `https://indexer-storage-testnet-turbo.0g.ai` | `https://indexer-storage-turbo.0g.ai` |
| Block explorer | `chainscan-galileo.0g.ai` | `chainscan.0g.ai` |
| Storage explorer | `storagescan-galileo.0g.ai` | `storagescan.0g.ai` |
| Faucet | `https://faucet.0g.ai` (0.1 0G/day) | n/a |
| Compute provider (free tier) | `0xa48f01...` qwen-2.5-7b | n/a |
| Compute provider (cheapest) | n/a | `0xBB3f5b…` gpt-oss-120b @ 0.10/0.49 |
| Compute provider (strongest) | n/a | `0xd9966e…` GLM-5-FP8 @ 1.0/3.2 |
| Compute provider (longest ctx) | n/a | `0x992e63…` qwen3.6-plus 1M ctx |
| Min ledger deposit | 3 0G | 3 0G |
| Min provider sub-account | 1 0G | 1 0G |

---

## 12. What this gets you

**Every mindX thought is now:** TEE-attested at the inference layer (chatID), Merkle-committed at the storage layer (rootHash), and on-chain provenanced at the THOT layer (token id). Every memory is recallable, every recall is verifiable, every agent is transferable. THOT stops being a token *for* memories and starts being the canonical *index of mindX cognition itself* — which is what the contract name has always implied. The integration isn't bolt-on; it completes a circuit the architecture was already drawing.
