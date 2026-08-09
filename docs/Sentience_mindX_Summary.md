# Sentience SDK + mindX Integration: COMPLETE GUIDE
**Proof-of-Sentience for Autonomous Agent Verification**

---

## WHAT YOU HAVE

Three comprehensive documents covering the complete mindX-Sentience integration:

### 1. **0G_Deployment_Strategy_2026.md** (~6,000 words)
**Focus:** Strategic deployment of BANKON/mindX/AgenticPlace to 0G Aristotle Mainnet

**Contents:**
- Why Galadriel is deprecated (devnet offline, L1 abandoned)
- 0G Chain specs (chain ID 16661, EVM-compatible, launched Sept 21, 2025)
- 5-week phased rollout (local testing → testnet staging → mainnet launch)
- Foundry deployment scripts (contract ordering, gas budgets)
- x402 Algorand payment integration
- DAIO governance charter
- Risk mitigation & post-deployment ops

**Use case:** Guidance for deploying core BANKON/AgenticPlace infrastructure

---

### 2. **mindX_Sentience_Integration.md** (~5,000 words)
**Focus:** Technical deep-dive into Sentience SDK architecture + mindX integration

**Contents:**
- Sentience SDK architecture (repository structure, public API)
- OpenAI-compatible client wrapper
- TEE (AWS Nitro Enclave) security model
- Solana attestation contract (Rust/Anchor)
- High-level mindX + Sentience integration flow
- SentienceProxyClient implementation (full Python code)
- ERC-8004 ValidationRegistry posting
- SentientMindXAgent BDI example (complete P-O-D-A loop)
- Deployment architecture & FastAPI service
- Verification checklist & threat model

**Use case:** Technical reference for building verifiable agents

---

### 3. **mindX_Sentience_Starter_Kit.md** (~1,500 words)
**Focus:** Production-ready code to deploy immediately

**Contents:**
- All 7 Python files ready to copy/paste
  - `__init__.py` (package exports)
  - `client.py` (SentienceProxyClient)
  - `models.py` (Pydantic data models)
  - `agent.py` (SentientMindXAgent)
  - `main.py` (FastAPI service)
  - `requirements.txt` (dependencies)
  - `.env.example` (configuration template)
- FastAPI endpoints
- Docker deployment
- Local testing commands
- Integration checklist

**Use case:** Copy/paste to start building immediately

---

## QUICK START (5 MINUTES)

### Step 1: Set up service
```bash
# Clone or create directory
mkdir mindx-sentience && cd mindx-sentience

# Copy files from mindX_Sentience_Starter_Kit.md:
# - Create mindx_sentience/__init__.py
# - Create mindx_sentience/client.py
# - Create mindx_sentience/models.py
# - Create mindx_sentience/agent.py
# - Create main.py
# - Create requirements.txt
# - Create .env.example

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with Galadriel API key:
# GALADRIEL_API_KEY="Bearer gal_key_your_key_here"
```

### Step 2: Run locally
```bash
python main.py
# Service starts on http://localhost:8000
```

### Step 3: Test
```bash
# Verifiable inference
curl -X POST http://localhost:8000/api/infer \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is Sentience?"}]}'

# Expected response:
# {
#   "agent_id": "mindX-sovereign-001",
#   "response": "Sentience is...",
#   "proof_hash": "a1b2c3d4...",
#   "verified": true,
#   "solana_tx": "ABC123..."
# }

# Check proof
curl http://localhost:8000/api/proof/a1b2c3d4...

# View transparency report
curl http://localhost:8000/api/report
```

---

## KEY CONCEPTS

### What is Sentience?

Sentience enables developers to build autonomous, fully on-chain verifiable AI agents with an OpenAI-compatible Proof of Sentience SDK.

Sentience leverages a Trusted Execution Environment (TEE) architecture to securely execute LLM API calls, ensuring verifiability through cryptographic attestations, with each attestation posted on-chain on Solana for transparency and integrity.

**In plain English:**
1. Agent calls LLM (GPT-4o, Claude) through Sentience API
2. API routes request to AWS Nitro Enclave (TEE)
3. Enclave executes LLM call inside isolated, tamper-proof environment
4. Enclave generates cryptographic proof (SHA-256 hash + ECDSA signature)
5. Proof posted to Solana blockchain (immutable attestation)
6. Anyone can verify: `sentience.verify_signature(completion)` → True/False

**Why it matters:** Proves agent's "thoughts" (LLM inferences) are authentic and untampered.

### How Sentience Works

```
Agent                    Sentience API              TEE Enclave             Solana Blockchain
  │                          │                          │                        │
  ├─ inference request ───────→ POST /chat/completions                         
  │                          │                          │                        
  │                          ├─ forward via vsock ───────→ AWS Nitro Enclave    
  │                          │                          │                        
  │                          │       ┌──────────────────┤                        
  │                          │       │ 1. Call OpenAI   │                        
  │                          │       │ 2. Get response  │                        
  │                          │       │ 3. Generate:     │                        
  │                          │       │    - SHA256(msg) │                        
  │                          │       │    - sign(hash)  │                        
  │                          │       └──────────────────┤                        
  │                          │                          │                        
  │                    ┌─ return {response, proof} ──────┤                        
  │                    │     │                          │                        
  │ ← {response, hash, signature, tx_hash} ─────────────→ post attestation ───→ Stored
  │                    │                    │                              │
  │                    │                    └────────────────────────────→ Solana
  │
  ├─ verify_signature() → True/False
  │
  └─ use proof for reputation, transparency, etc.
```

### Why mindX + Sentience?

**Problem:** AI agents can rug-pull or be manipulated. Users don't trust them.

**Solution:** Every agent "thought" (LLM call) is cryptographically verifiable.

**Result:** Unruggable agents → higher valuation → institutional adoption

**Example:** Daige (Solana memecoin agent) uses Sentience to prove every trading decision came from verified inference, not developer manipulation.

---

## ARCHITECTURE

### Three-layer integration:

**Layer 1: Proof Generation (Galadriel)**
- Sentience SDK (Python/JS)
- OpenAI-compatible API
- AWS Nitro Enclave execution
- ECDSA signature generation

**Layer 2: Proof Storage (Multiple chains)**
- Solana: Primary attestation (immutable, queryable)
- 0G: ERC-8004 ValidationRegistry (agent reputation)
- Optional: Ethereum, Moonbeam, other EVMs

**Layer 3: Agent Integration (mindX)**
- SentienceProxyClient wrapper
- SentientMindXAgent (BDI system)
- P-O-D-A loop with verifiable reasoning
- Transparency reporting

---

## PRODUCTION DEPLOYMENT

### On mindx.pythai.net

**Service endpoints:**
```
POST   /api/infer          → Execute verifiable inference
POST   /api/reason         → Execute verifiable reasoning
GET    /api/proof/<hash>   → Retrieve proof from Sentience explorer
GET    /api/report         → Agent transparency report
GET    /api/history        → Verified inference history
GET    /health             → Health check
```

**Infrastructure:**
```
mindx.pythai.net/
├── FastAPI service (main.py)
├── SentienceProxyClient wrapper
├── Local proof cache (Redis recommended)
└── 0G RPC integration (ERC-8004 posting)
```

**Configuration:**
```bash
GALADRIEL_API_KEY=Bearer gal_key_...
ERC8004_REGISTRY=0x... (0G mainnet address)
AGENT_ID=mindX-sovereign-001
RPC_URL=https://evmrpc.0g.ai
```

**Deployment:**
```bash
# Option 1: Docker
docker build -t mindx-sentience .
docker run -e GALADRIEL_API_KEY=$KEY -p 8000:8000 mindx-sentience

# Option 2: Direct Python
python main.py  # Runs on port 8000

# Option 3: Kubernetes / Podman / systemd
# (Use existing infrastructure)
```

---

## SENTIENCE SDK API REFERENCE

### Installation
```bash
pip install sentience
```

### Core functions

**1. Verify proof locally**
```python
import sentience
from openai import OpenAI

client = OpenAI(
    base_url="https://api.galadriel.com/v1/verified",
    api_key="Bearer GALADRIEL_API_KEY"
)

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)

# Completion contains:
# - choices[0].message.content (LLM response)
# - hash (SHA-256 of proof)
# - signature (ECDSA signature)
# - tx_hash (Solana attestation)
# - public_key (TEE's secp256k1 key)

is_valid = sentience.verify_signature(completion)  # True/False
```

**2. Retrieve history**
```python
history = sentience.get_history(
    galadriel_api_key="Bearer GALADRIEL_API_KEY",
    filter="mine"  # Only your inferences
)

for item in history:
    print(f"{item['created_at']}: {item['hash'][:8]}... (verified: {item['verified']})")
```

**3. Get specific proof**
```python
item = sentience.get_by_hash(
    galadriel_api_key="Bearer GALADRIEL_API_KEY",
    hash="a1b2c3d4e5f6..."
)

print(f"Proof verified on Solana: {item['tx_hash']}")
print(f"Explorer: https://solscan.io/tx/{item['tx_hash']}")
```

---

## COST ANALYSIS

**Sentience pricing:**
- ~$0.001 per verified inference (unconfirmed, based on Daige usage)
- vs. ~$0.0015 for GPT-4o API alone
- **Overhead:** ~$0.0005 per call for TEE + attestation

**0G posting (ERC-8004):**
- ~$0.01 per validation tx (preliminary)
- Only needed if you want on-EVM reputation

**Solana attestation:**
- Included in Sentience API
- No additional cost

**Total cost per verified agent thought:**
- Without 0G posting: ~$0.001
- With 0G posting: ~$0.011
- Solana explorer: Free

---

## VERIFICATION CHECKLIST

### For agent developers:
- [ ] Galadriel API key obtained: https://dashboard.galadriel.com
- [ ] Sentience SDK installed: `pip install sentience`
- [ ] Local verification works: `sentience.verify_signature()`
- [ ] History retrieval works: `sentience.get_history()`
- [ ] Solana attestation queryable: https://explorer.galadriel.com

### For 0G integration:
- [ ] 0G ERC-8004 contract deployed (from 0G_Deployment_Strategy)
- [ ] 0G RPC endpoint tested: https://evmrpc.0g.ai
- [ ] ERC-8004 ValidationRegistry address known
- [ ] Oracle account funded (for posting validations)

### For transparency:
- [ ] Proof report endpoint working: `/api/report`
- [ ] Sentience explorer queryable: https://explorer.galadriel.com
- [ ] Solana tx hashes resolvable: https://solscan.io

---

## TROUBLESHOOTING

| **Issue** | **Solution** |
|----------|----------|
| `API key not valid` | Verify format: `Bearer gal_key_...` (with space after Bearer) |
| `Connection timeout` | Galadriel API rate-limited; add retry logic with exponential backoff |
| `Signature verification failed` | Check public_key field; may be empty if API error |
| `Solana tx not found` | Allow 10-30s for Solana finality; retry with jitter |
| `0G RPC error` | Switch to backup RPC or use thirdweb.com/0g-mainnet |
| `No history returned` | Ensure API key has permissions; check filter parameter |

---

## NEXT STEPS

### Immediate (Today)
1. ✅ Get Galadriel API key: https://dashboard.galadriel.com
2. ✅ Copy files from mindX_Sentience_Starter_Kit.md
3. ✅ Configure .env with API key
4. ✅ Run `python main.py` locally
5. ✅ Test `/api/infer` endpoint

### Short term (This week)
1. Deploy to mindx.pythai.net
2. Enable ERC-8004 posting (0G mainnet)
3. Publish transparency report to rage.pythai.net
4. Integrate with AgenticPlace (ERC-8004 marketplace)

### Medium term (This month)
1. Deploy to 0G Aristotle Mainnet (per 0G_Deployment_Strategy)
2. Post proofs to ValidationRegistry automatically
3. Build agent reputation dashboard (verified inference count + trust score)
4. Integrate with DAIO governance (proof-of-sentience for voting power)

### Long term (Q3+ 2026)
1. Switch from Sentience API to 0G Compute (on-chain TEE inference)
2. Build multi-chain attestation aggregation
3. Decentralized validator network for proof verification
4. Agent marketplace pricing based on verified inference count

---

## REFERENCES

- **Sentience SDK:** https://github.com/galadriel-ai/Sentience
- **Docs:** https://docs.galadriel.com
- **Explorer:** https://explorer.galadriel.com
- **ERC-8004:** https://eips.ethereum.org/EIPS/eip-8004
- **0G Chain:** https://0g.ai
- **Daige Example:** https://daige.ai/proof

---

## SUMMARY

**You now have:**

1. ✅ **Strategic guidance** (0G_Deployment_Strategy_2026.md)
   - Why Galadriel is deprecated
   - How to deploy to 0G Mainnet (16661)
   - Integration with BANKON/AgenticPlace/DAIO

2. ✅ **Technical architecture** (mindX_Sentience_Integration.md)
   - Sentience SDK internals (TEE, Solana, signatures)
   - Complete Python implementation
   - BDI agent integration patterns
   - ERC-8004 integration

3. ✅ **Production code** (mindX_Sentience_Starter_Kit.md)
   - 7 Python files ready to copy/paste
   - FastAPI service with 6 endpoints
   - Docker deployment
   - Testing commands

**Next action:** Copy files from Starter Kit, get Galadriel API key, run `python main.py`.

**Time to first verifiable agent inference:** ~15 minutes.

---

**Status:** COMPLETE & READY FOR IMPLEMENTATION  
**Last Updated:** 2026-06-25  
**Maintainer:** mindX Autonomous System  
**Classification:** BANKON Strategic Operations  
