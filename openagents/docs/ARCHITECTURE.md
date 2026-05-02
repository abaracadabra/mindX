# mindX × Open Agents — Architecture

## Positioning

mindX is **agnostic agentic infrastructure for the knowledge economy**. It is the substrate on top of which other frameworks (OpenClaw, NanoClaw, ZeroClaw, NullClaw) and individual agents on any blockchain can run. mindX is the *agency*. [AgenticPlace](https://agenticplace.pythai.net) is the *marketplace*.

This submission upgrades mindX with:

1. **0G Compute** — sealed inference with `ZG-Res-Key` attestation header captured per call.
2. **0G Storage** — Merkle-root-addressed durable storage for encrypted intelligence payloads.
3. **0G Chain (Galileo)** — ERC-7857 iNFT mint anchoring the merkle root on chain.
4. **KeeperHub × AgenticPlace** — bidirectional x402/MPP bridge so payments flow across ecosystems.
5. **ENS** — `<agent_id>.bankon.eth` soulbound subnames issued from a custom NameWrapper subname registrar.
6. **Uniswap V4** — BDI-reasoning trader persona with full deliberation traces.

## High-level diagram

```
                      ┌──────────────────────────────────────────────────┐
                      │  mindX — agnostic agentic infrastructure         │
                      │   BDI · AGInt · Boardroom · Dream cycle · Gödel  │
                      │   Memory tiers · Inference factory · Tool layer  │
                      └────┬───────────┬───────────┬──────────┬──────────┘
                           │           │           │          │
        ┌──────────────────┼───────────┼───────────┼──────────┼─────────────────┐
        ▼                  ▼           ▼           ▼          ▼                 ▼
┌─────────────┐    ┌─────────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│ 0G Compute  │    │ 0G Storage  │ │ 0G Chain│ │ KeeperHub│ │ ENS      │ │ Uniswap V4  │
│ (zerog_     │    │ (zerog_     │ │ Galileo │ │ × Agen.  │ │ Bankon   │ │ Trader      │
│  handler)   │    │  provider + │ │ iNFT    │ │ x402     │ │ Registrar│ │ Persona     │
│ attestation │    │  TS sidecar)│ │ 7857    │ │ bridge   │ │ soulbound│ │ BDI traces  │
└─────────────┘    └─────────────┘ └─────────┘ └──────────┘ └──────────┘ └─────────────┘
        ▲                  ▲           ▲           ▲          ▲                 ▲
        │                  │           │           │          │                 │
        └────────── catalogue (data/logs/catalogue_events.jsonl) ────────────────┘
                                       │
                                       ▼
                       /openagents.html (4-panel live dashboard)
                       /insight/openagents/* (JSON + plain-text)
```

## Module map

| Concern | New file | Existing reuse |
|---------|----------|----------------|
| 0G Compute LLM client | `llm/zerog_handler.py` | `llm/llm_factory.py` (factory wiring), `llm/vllm_handler.py` (template — OpenAI-compat) |
| 0G Compute model registry | `models/zerog.yaml` | mirrors `models/mistral.yaml` shape |
| 0G Storage adapter (Python) | `agents/storage/zerog_provider.py` | `agents/storage/provider.py` for `ZGRoot` validator pattern |
| 0G Storage sidecar (TS) | `openagents/sidecar/index.ts`, `package.json` | uses `@0glabs/0g-ts-sdk`; stands alone |
| ERC-7857 iNFT (hardened) | [`daio/contracts/inft/iNFT_7857.sol`](../../daio/contracts/inft/iNFT_7857.sol) | ERC-721 + ERC-721URIStorage + ERC-721Burnable + ERC-2981 + AccessControl (4 roles) + Pausable + ReentrancyGuard + EIP-712. Standard `transferFrom` is gated — only `transferWithSealedKey` (oracle-signed re-encryption) and `cloneAgent` (oracle-signed + clone-fee → treasury) move tokens between owners. AgenticPlace + BANKON binding hooks. Preserves prior-art `iNFT.sol` untouched. **Full reference: [docs/INFT_7857.md](../../docs/INFT_7857.md).** |
| ERC-7857 test suite | [`daio/contracts/test/inft/iNFT_7857.t.sol`](../../daio/contracts/test/inft/iNFT_7857.t.sol) | 53 unit + 3 fuzz (256 runs each) — **56/56 pass** under `FOUNDRY_PROFILE=inft forge test`. Covers transfer gating, EIP-712 oracle proof + replay nonce, AccessControl, royalty cap, burn cleanup with permanent root reservation, all bindings. |
| ERC-7857 interactive UI | [`mindx_backend_service/inft7857.html`](../../mindx_backend_service/inft7857.html) | Single-file ethers v6 + MetaMask console. 9 tabs (Overview · Mint · Inspect · Transfer · Clone · Authorize/Revoke · Burn · Bind · Admin). Live event log subscribing to all 14 contract events. Demo-mode oracle signing via paste-PK + `eip712Domain()` + `sealedKeyDigest()`. Auto-loads contract address from `openagents/deployments/galileo.json`. Live at [/inft7857](https://mindx.pythai.net/inft7857). |
| iNFT Foundry deploy | `openagents/deploy/deploy_galileo.sh` | `daio/contracts/foundry.toml` (bumped to `cancun` for OZ v5 compat) |
| ENS subname registrar | `daio/contracts/ens/BankonAgentRegistrar.sol` | NameWrapper API per `docs.ens.domains/wrapper/creating-subname-registrar` |
| ENS Foundry deploy | `openagents/ens/deploy_registrar.sh` | Sepolia (default) or mainnet |
| ENS issuer (Python) | `openagents/ens/subdomain_issuer.py` | `web3.py 7.x`, `eth_account 0.13` |
| KeeperHub bridge | `openagents/keeperhub/bridge_routes.py` | `mindx_backend_service/agenticplace_routes.py:300-518` (existing 402 plumbing) |
| KeeperHub Python client | `tools/keeperhub_x402_client.py` | `tools/pay2play_metered_tool.py` (existing x402 client shape) |
| Uniswap V4 tool | `tools/uniswap_v4_tool.py` | `agents/core/bdi_agent.BaseTool` |
| Trader persona | `personas/trader.prompt` | `agents/persona_agent.py` machinery |
| Demo orchestrator | `openagents/demo_agent.py` | composes all above |
| Dashboard | `mindx_backend_service/openagents.html` | mirrors `boardroom.html`, `feedback.html` style |
| Dashboard backend | `mindx_backend_service/routes_openagents.py` | reads `agents/catalogue/log.py` event stream |

## Data flow — end-to-end iNFT mint

```
build_payload()                         openagents/demo_agent.py
    │ (CEO + 7 soldier personas, boardroom memory, dream report)
    │ → bytes (gzipped JSON)
    ▼
ZeroGProvider.upload(bytes)             agents/storage/zerog_provider.py
    │ → POST :7878/upload               openagents/sidecar/index.ts
    │ → @0glabs/0g-ts-sdk Indexer       (Node sidecar)
    │ → Galileo Flow contract           rpc evmrpc-testnet.0g.ai
    ▼
(rootHash 0x.., tx_hash 0x..)
    │
    ▼
iNFT_7857.mintAgent(content_root, ...)   daio/contracts/inft/iNFT_7857.sol
    │ → emits AgentMinted(tokenId)       deployed on Galileo
    ▼
tokenId
    │
    ▼
ZeroGHandler.generate_text(prompt)      llm/zerog_handler.py
    │ → POST api.0g.ai /v1/proxy/...
    │ → captures ZG-Res-Key              attestation hash
    ▼
(text, attestation_hash) per soldier × 8
    │
    ▼
upload session_log → ZeroGProvider
    │ → root_hash
    ▼
DatasetRegistry.registerDataset(root, uri)   agents/storage/anchor.py
    │ (selector 0xf1783fb8 — same we already use for ARC)
    ▼
session anchored on Galileo
    │
    ▼
catalogue events emitted at every step → /insight/openagents/*
                                       → /openagents.html (live dashboard)
```

## Data flow — KeeperHub x402 bridge

**Inbound (KH wallet pays AgenticPlace):**
```
external agent → @keeperhub/wallet
                    │
                    ▼
           POST /p2p/keeperhub/inference (no X-PAYMENT)
                    │
                    ▼
   bridge_routes.py → 402 with dual-network envelope:
        accepts[0] = exact / base  / USDC / 0x833589... / 5000 units
        accepts[1] = mpp   / tempo / USDC.e / 0x20c0...  / 5000 units
                    │
       (KH wallet picks based on its USDC holdings)
                    │
                    ▼
           POST /p2p/keeperhub/inference (X-PAYMENT: base64(EIP-3009 sig))
                    │
                    ▼
   USDC settles to KH_RECIPIENT (mindX Turnkey wallet on Base)
   bridge calls llm.zerog → response + attestation
   response 200 to caller
                    │
                    ▼
   catalogue: kind=tool.invoke actor=keeperhub_bridge direction=inbound
   visible on /insight/openagents/keeperhub
```

**Outbound (mindX agent consumes paid KH workflow):**
```
mindX BDI agent
       │
       ▼
KeeperHubX402Client.fetch(method, url, json_body=...)   tools/keeperhub_x402_client.py
       │
       ▼ initial GET — receives 402 from KH workflow
       │
       │ pick_challenge() → cheapest valid scheme on preferred network
       │ sign_payment() → EIP-3009 transferWithAuthorization (eth_account)
       │
       ▼ retry with X-PAYMENT
USDC settles to KH workflow creator
response delivered to mindX agent
```

## Data flow — ENS subname issuance

```
IDManagerAgent.create_agent_wallet(agent_id)            agents/core/id_manager_agent.py
       │
       │ → generates Ethereum keypair (existing logic)
       │
       ▼ asyncio.create_task(  fire-and-forget )
SubdomainIssuer.register_agent(agent_id, wallet, ...)   openagents/ens/subdomain_issuer.py
       │
       ▼
BankonAgentRegistrar.registerAgent(agent_id, wallet,   daio/contracts/ens/BankonAgentRegistrar.sol
                                    persona_url, summary, expiry)
       │
       │ Step 1: NameWrapper.setSubnodeRecord(parent, label, THIS, resolver, 0, 0, expiry)
       │ Step 2: PublicResolver.setAddr / setText / setText / setText
       │ Step 3: NameWrapper.setSubnodeRecord(parent, label, agentWallet, resolver, 0, 0x7, expiry)
       │   (0x7 = CANNOT_UNWRAP | CANNOT_BURN_FUSES | CANNOT_TRANSFER  — soulbound)
       │
       ▼ emits AgentRegistered event
agent_id.bankon.eth is now a soulbound NFT owned by agent wallet
       │
       ▼
catalogue: kind=agent.interact actor=subdomain_issuer
visible on /insight/openagents/ens and /openagents.html
```

## What's NOT changed

To keep MVP risk low we deliberately **did not** refactor:

- `agents/storage/multi_provider.py` — stays 2-way IPFS for ordinary memory consolidation. ZeroGProvider stands alongside as the dedicated path for ERC-7857 intelligence payloads.
- `agents/storage/provider.py` `IPFSProvider` ABC — kept its `CID` return type. `ZGRoot` is a separate dataclass.
- `agents/storage/anchor.py` — already speaks the `f1783fb8` selector against any EVM RPC; works on Galileo with **zero code changes**, just env vars.

## Compatibility note

The `daio/contracts/foundry.toml` `evm_version` was bumped from `shanghai` to `cancun`. OpenZeppelin v5's `Bytes.sol` uses the `mcopy` opcode (Cancun, EIP-5656). 0G Galileo (Aristotle EVM, post-Cancun) and Sepolia (Dencun) both support it. No existing contracts are affected — they were already failing to compile under shanghai with the v5 OZ in `lib/`.
