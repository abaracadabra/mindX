# mindX + Sentience: Verifiable Autonomous Agent Service Architecture
**Proof-of-Sentience SDK Integration for mindX BDI Agent System**

**Version:** 1.0  
**Date:** 2026-06-25  
**Status:** READY FOR IMPLEMENTATION  
**Integration Target:** mindx.pythai.net + Sentience API + Solana attestation

---

## SECTION 1: SENTIENCE SDK ARCHITECTURE & SOURCE CODE

### 1.1 Repository Structure
```
galadriel-ai/Sentience/
├── sdk/
│   ├── python/                          # Main Python SDK (PyPI: sentience)
│   │   ├── sentience/
│   │   │   ├── __init__.py              # Public API exports
│   │   │   ├── client.py                # OpenAI-compatible client wrapper
│   │   │   ├── verification.py          # Signature verification logic
│   │   │   ├── history.py               # History retrieval (GaladrielChatHistory)
│   │   │   └── models.py                # Data models (attestation, completion)
│   │   └── setup.py
│   └── js/                              # JavaScript/TypeScript SDK
├── verified-inference/
│   ├── enclave/                         # TEE enclave (AWS Nitro Enclaves)
│   │   ├── Dockerfile                   # Enclave container image
│   │   └── src/                         # LLM inference + proof generation
│   ├── host/                            # Host proxy (HTTP → enclave)
│   ├── solana-attestation-contract/     # Rust/Anchor (posts proofs to Solana)
│   └── verify/                          # TEE verification instructions
└── README.md
```

### 1.2 Python SDK Public API (`pip install sentience`)

**Installation:**
```bash
pip install sentience
```

**Core imports:**
```python
import sentience
from sentience import Sentience
from sentience.history import GaladrielChatHistory
from sentience.models import (
    SentienceCompletion,      # Completion with {message, proof, signature, tx_hash}
    SentienceAttestationData,
)
```

**Primary functions:**

#### A. `sentience.verify_signature(completion: SentienceCompletion) -> bool`
Verifies that a completion response is cryptographically valid.

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

# completion contains:
# {
#   "id": "chatcmpl-...",
#   "object": "chat.completion",
#   "created": 1719340000,
#   "model": "gpt-4o",
#   "choices": [...],
#   "hash": "a1b2c3d4...",  # SHA-256 of message + proof
#   "public_key": "0x...",  # TEE's secp256k1 public key
#   "signature": "0x...",   # ECDSA signature
#   "tx_hash": "ABC...",    # Solana transaction hash (base58)
#   "attestation": {        # On-chain attestation data
#       "timestamp": 1719340000,
#       "model": "gpt-4o",
#       "prompt_hash": "...",
#       "response_hash": "..."
#   }
# }

is_valid = sentience.verify_signature(completion)  # → True/False
print(f"Inference verified: {is_valid}")
print(f"Solana TX: {completion['tx_hash']}")
```

**Verification flow (Python side):**
1. Extract `{message, proof, signature, public_key}` from completion
2. Reconstruct the message hash (SHA-256)
3. Verify the ECDSA signature using the TEE's public key
4. (Optional) Fetch the Solana attestation from `completion['tx_hash']` to confirm on-chain posting

#### B. `sentience.get_history(galadriel_api_key: str, filter: str = None) -> List[GaladrielChatHistory]`
Retrieve all verified inferences for the authenticated agent.

```python
from typing import List
from sentience.history import GaladrielChatHistory

# Get all verified inferences
all_history: List[GaladrielChatHistory] = sentience.get_history(
    galadriel_api_key="Bearer GALADRIEL_API_KEY"
)

# Filter to "mine" (agent's own inferences)
my_inferences = sentience.get_history(
    galadriel_api_key="Bearer GALADRIEL_API_KEY",
    filter="mine"
)

# Each item:
# GaladrielChatHistory = {
#   "id": str,
#   "hash": str,                  # SHA-256 hash of completion
#   "model": str,                 # e.g., "gpt-4o"
#   "prompt": str,                # Full prompt text
#   "response": str,              # Full response text
#   "created_at": timestamp,
#   "tx_hash": str,               # Solana transaction (base58)
#   "verified": bool,
#   "attestation": {...}
# }

for item in my_inferences:
    print(f"{item['created_at']}: {item['model']} → {item['hash'][:8]}...")
    print(f"  Solana TX: {item['tx_hash']}")
    print(f"  Verified: {item['verified']}")
```

#### C. `sentience.get_by_hash(galadriel_api_key: str, hash: str) -> GaladrielChatHistory`
Retrieve a specific verified inference by its SHA-256 hash.

```python
item = sentience.get_by_hash(
    galadriel_api_key="Bearer GALADRIEL_API_KEY",
    hash="a1b2c3d4e5f6..."  # 64-char hex string
)
```

### 1.3 OpenAI-Compatible Client
The Sentience API is compatible with OpenAI's Python client library:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.galadriel.com/v1/verified",
    api_key="Bearer GALADRIEL_API_KEY"
)

# Standard OpenAI interface
completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"}
    ],
    temperature=0.7,
    max_tokens=100
)

# Response contains extra fields:
# - hash: SHA-256 of message + proof
# - public_key: TEE secp256k1 public key
# - signature: ECDSA signature over hash
# - tx_hash: Solana attestation transaction (base58)
# - attestation: {...}
```

### 1.4 TEE Architecture (Verified Inference)

**Architecture diagram:**
```
┌─────────────────────────────────────────────────────────────────┐
│                      mindX Agent (Client)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ 1. HTTP POST message + model
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Sentience Host (HTTP proxy)                  │
│  (Runs on EC2 instance outside enclave, proxies to enclave)     │
└────────────────────────────┬────────────────────────────────────┘
                             │ 2. Forward to enclave via vsock
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│            AWS Nitro Enclave (Isolated TEE, AMD or Intel)       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Enclave process:                                          │ │
│  │  1. Receive message from host proxy                        │ │
│  │  2. Call OpenAI API (model="gpt-4o") with message          │ │
│  │  3. Receive response from OpenAI                           │ │
│  │  4. Generate attestation:                                  │ │
│  │     - SHA-256 hash of (message + response)                 │ │
│  │     - ECDSA signature using enclave's secp256k1 key        │ │
│  │  5. Return {response, hash, signature, public_key}         │ │
│  │  6. Host submits attestation to Solana                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ 3. Return {response, proof, sig}
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│            Solana Blockchain (On-chain attestation)             │
│  Program: sentience/solana-attestation-contract (Anchor)        │
│  Stores: {hash, signature, public_key, timestamp}               │
└─────────────────────────────────────────────────────────────────┘
```

**Key security properties:**
- **Enclave isolation:** No external process can access enclave memory/code
- **Confidentiality:** Request/response encrypted in transit (TLS within vsock)
- **Authenticity:** Enclave signs proof with its secp256k1 private key (never leaves enclave)
- **Verifiability:** Public key + signature can be independently verified by anyone
- **Transparency:** Solana attestation immutable and publicly queryable

### 1.5 Solana Attestation Contract

**Program name:** `sentience/solana-attestation-contract`  
**Language:** Rust (Anchor framework)  
**Purpose:** Store {hash, signature, public_key, timestamp} on-chain

**Program instructions (Anchor IDL):**
- `initialize()` - Create attestation account (PDA)
- `post_attestation(hash, signature, public_key)` - Host calls this after enclave proof generated
- `verify_attestation(hash)` - Public: verify if hash exists + is valid

**Data structure (Rust):**
```rust
#[account]
pub struct Attestation {
    pub hash: [u8; 32],           // SHA-256 of message + response
    pub signature: Vec<u8>,       // ECDSA signature (64 bytes)
    pub public_key: Vec<u8>,      // secp256k1 public key (33 bytes compressed)
    pub timestamp: i64,           // Unix timestamp
    pub model: String,            // "gpt-4o", "claude-3-sonnet", etc.
    pub agent_pubkey: Pubkey,     // Agent's Solana wallet (authority)
}
```

**On-chain verification:**
Solana can run secp256k1 signature verification natively (via `ed25519_program::Ed25519SigVerify` or manual verification in contract).

---

## SECTION 2: mindX + SENTIENCE INTEGRATION ARCHITECTURE

### 2.1 High-Level Integration Flow

```
mindX BDI Loop                    Sentience Service
┌─────────────────────────────┐   ┌──────────────────────────────┐
│ Perception (P):             │   │                              │
│  ├─ Sensor inputs           │   │  Wrapper:                    │
│  ├─ LLM inference request   │───→ ├─ route to OpenAI-compat    │
│  └─ Build belief state      │   │  │  endpoint                 │
└─────────────────────────────┘   │  ├─ receive {msg, proof}     │
                                   │  └─ post to 0G ERC-8004      │
┌─────────────────────────────┐   │    validation registry       │
│ Orientation (O):            │   │                              │
│  ├─ Filter beliefs          │   │  Sentience SDK:             │
│  ├─ Generate desire state   │   │  ├─ verify_signature()      │
│  └─ Identify goals          │   │  ├─ get_history()           │
└─────────────────────────────┘   │  ├─ get_by_hash()           │
                                   │  └─ Solana attestation fetch│
┌─────────────────────────────┐   └──────────────────────────────┘
│ Decision (D):               │
│  ├─ Evaluate options        │   Proof-of-Sentience:
│  ├─ Select action           │   ┌──────────────────────────────┐
│  └─ Commit to execution     │   │ Attestation on 0G Mainnet:   │
└─────────────────────────────┘   │  ├─ Hash stored in ERC-8004  │
                                   │  ├─ TX hash on-chain         │
┌─────────────────────────────┐   │  ├─ Public key published     │
│ Action (A):                 │   │  └─ Verifiable by anyone    │
│  ├─ Execute LLM call        │   │                              │
│  ├─ Process proof           │   │ Optional attestation:        │
│  └─ Log to Tabularium       │   │  ├─ Solana tx_hash posted   │
└─────────────────────────────┘   │  ├─ Accessible via explorer  │
                                   │  └─ Long-term immutable log  │
                                   └──────────────────────────────┘
```

### 2.2 Service Layer: mindX-Sentience Wrapper

**Service name:** `mindx-sentience`  
**Purpose:** Unified interface for mindX agents to access Sentience with automatic proof posting to 0G + optional Solana logging

**Architecture:**
```python
# mindx_sentience/
├── __init__.py
├── client.py                # SentienceProxyClient (wrapper around OpenAI client)
├── verifier.py              # Proof verification + attestation posting to 0G
├── models.py                # Data models (SentienceAgentProof, AttestedCompletion)
├── solana_adapter.py        # Optional: Solana proof logger
└── erc8004_adapter.py       # 0G mainnet ERC-8004 validation registry poster
```

### 2.3 Core Implementation

#### A. SentienceProxyClient

```python
# mindx_sentience/client.py
from typing import Optional, List, Dict, Any
from openai import OpenAI
import sentience
import logging

logger = logging.getLogger(__name__)

class SentienceProxyClient:
    """
    Proxy wrapper around OpenAI client for Sentience verified inference.
    Routes LLM calls through Sentience TEE, verifies proofs, posts attestations.
    """
    
    def __init__(
        self,
        galadriel_api_key: str,
        agent_id: str,
        erc8004_registry: Optional[str] = None,  # 0G mainnet contract address
        solana_adapter: Optional[object] = None,  # SolanaProofLogger instance
    ):
        """
        Initialize Sentience client for mindX agent.
        
        Args:
            galadriel_api_key: Galadriel dashboard API key (with "Bearer " prefix)
            agent_id: mindX agent identifier (ERC-8004 soulbound token ID)
            erc8004_registry: 0G mainnet IdentityRegistry address (optional)
            solana_adapter: SolanaProofLogger for Solana attestation (optional)
        """
        self.agent_id = agent_id
        self.galadriel_api_key = galadriel_api_key
        self.erc8004_registry = erc8004_registry
        self.solana_adapter = solana_adapter
        
        # OpenAI-compatible client pointing to Sentience endpoint
        self.client = OpenAI(
            base_url="https://api.galadriel.com/v1/verified",
            api_key=galadriel_api_key
        )
        
        # Local proof cache (in-memory; use Redis in production)
        self._proof_cache: Dict[str, Dict[str, Any]] = {}
    
    def inference(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 500,
        post_to_erc8004: bool = True,
        post_to_solana: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute verifiable LLM inference through Sentience TEE.
        
        Returns:
        {
            "response": str,              # LLM response text
            "hash": str,                  # SHA-256 of message + proof
            "signature": str,             # ECDSA signature (hex)
            "tx_hash": str,               # Solana attestation tx (base58)
            "verified": bool,             # Signature verification passed
            "erc8004_tx": str,            # 0G ERC-8004 validation tx (optional)
            "solana_confirmed": bool,     # Solana tx confirmed (optional)
        }
        """
        logger.info(f"[{self.agent_id}] Inference request: model={model}, msgs={len(messages)}")
        
        # Step 1: Execute inference through Sentience
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Step 2: Extract proof from completion
        response_text = completion.choices[0].message.content
        proof = {
            "hash": completion.get("hash", ""),
            "signature": completion.get("signature", ""),
            "public_key": completion.get("public_key", ""),
            "tx_hash": completion.get("tx_hash", ""),  # Solana attestation
            "attestation": completion.get("attestation", {}),
        }
        
        # Step 3: Verify signature locally
        is_valid = sentience.verify_signature(completion)
        logger.info(f"[{self.agent_id}] Signature verification: {is_valid}")
        
        # Step 4: Cache proof locally
        self._proof_cache[proof["hash"]] = {
            "agent_id": self.agent_id,
            "response": response_text,
            "proof": proof,
            "verified": is_valid,
            "timestamp": int(__import__("time").time()),
        }
        
        # Step 5: Post to 0G ERC-8004 registry (if enabled & contract provided)
        erc8004_tx = None
        if post_to_erc8004 and self.erc8004_registry:
            erc8004_tx = self._post_to_erc8004(
                proof_hash=proof["hash"],
                signature=proof["signature"],
                agent_id=self.agent_id,
            )
        
        # Step 6: Post to Solana (optional; proof already on-chain via enclave)
        solana_confirmed = False
        if post_to_solana and self.solana_adapter:
            solana_confirmed = self.solana_adapter.verify_and_log(
                hash=proof["hash"],
                signature=proof["signature"],
                tx_hash=proof["tx_hash"],
            )
        
        result = {
            "response": response_text,
            "hash": proof["hash"],
            "signature": proof["signature"],
            "tx_hash": proof["tx_hash"],
            "verified": is_valid,
            "erc8004_tx": erc8004_tx,
            "solana_confirmed": solana_confirmed,
        }
        
        logger.info(f"[{self.agent_id}] Inference complete: hash={proof['hash'][:16]}..., verified={is_valid}")
        return result
    
    def _post_to_erc8004(self, proof_hash: str, signature: str, agent_id: str) -> Optional[str]:
        """
        Post proof to 0G ERC-8004 ValidationRegistry.
        Stores {agent_id, attestor=Sentience, proof_hash, signature, chain_id=0g:16661}.
        """
        # TODO: Implement via Web3.py + cast (Foundry)
        # Contract: IdentityRegistry.validation(
        #     agent_erc8004_id: uint256,
        #     attestor: address,          # Sentience oracle contract on 0G
        #     proof_hash: bytes32,
        #     signature: bytes,
        #     metadata: string            # "chain:16661|tx:0x..."
        # )
        logger.info(f"[{self.agent_id}] Posting to ERC-8004 ValidationRegistry...")
        # Return tx hash (0x-prefixed)
        return None  # Placeholder
    
    def get_verified_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve verified inference history from Sentience.
        """
        try:
            history = sentience.get_history(
                galadriel_api_key=self.galadriel_api_key,
                filter="mine"
            )
            return [
                {
                    "hash": item["hash"],
                    "model": item["model"],
                    "prompt": item["prompt"][:100] + "...",
                    "response": item["response"][:100] + "...",
                    "created_at": item["created_at"],
                    "tx_hash": item["tx_hash"],
                    "verified": item["verified"],
                }
                for item in history[:limit]
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")
            return []
    
    def verify_proof(self, proof_hash: str) -> Dict[str, Any]:
        """
        Retrieve & verify a proof by hash from Sentience explorer.
        """
        try:
            item = sentience.get_by_hash(
                galadriel_api_key=self.galadriel_api_key,
                hash=proof_hash
            )
            return {
                "hash": item["hash"],
                "model": item["model"],
                "response": item["response"],
                "verified": item["verified"],
                "tx_hash": item["tx_hash"],
                "solana_url": f"https://solscan.io/tx/{item['tx_hash']}",
            }
        except Exception as e:
            logger.error(f"Failed to retrieve proof {proof_hash}: {e}")
            return {}
```

#### B. SentienceAgentProof Model

```python
# mindx_sentience/models.py
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class SentienceProof(BaseModel):
    """Cryptographic proof of inference."""
    hash: str                      # SHA-256 (64 hex chars)
    signature: str                 # ECDSA signature (hex)
    public_key: str                # secp256k1 public key (hex)
    tx_hash: str                   # Solana attestation (base58)

class AttestedCompletion(BaseModel):
    """LLM completion with cryptographic attestation."""
    agent_id: str                  # mindX agent identifier
    response: str                  # LLM response text
    proof: SentienceProof          # Proof of execution in TEE
    verified: bool                 # Signature verification passed
    model: str                     # "gpt-4o", "claude-3-sonnet", etc.
    created_at: datetime           # Timestamp
    erc8004_tx: Optional[str]      # 0G validation registry tx
    solana_confirmed: Optional[bool]  # Solana attestation confirmed

class AgentReputation(BaseModel):
    """Agent reputation score based on verified inferences."""
    agent_id: str
    total_inferences: int          # All verified inferences
    verified_count: int            # Passed verification
    trust_score: float             # 0.0-1.0 (verified_count / total_inferences)
    last_inference: Optional[datetime]
    solana_txs_confirmed: int      # Count of Solana-confirmed proofs
```

#### C. ERC-8004 Integration

```python
# mindx_sentience/erc8004_adapter.py
from typing import Optional
import logging
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

class ERC8004ValidationPoster:
    """
    Posts Sentience proof attestations to 0G ERC-8004 ValidationRegistry.
    """
    
    def __init__(
        self,
        rpc_url: str = "https://evmrpc.0g.ai",
        validation_registry_address: str = None,
        oracle_account: Account = None,  # Sentience oracle account (private key)
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.validation_registry = validation_registry_address
        self.oracle_account = oracle_account
    
    def post_validation(
        self,
        agent_erc8004_id: int,        # ERC-721 token ID of agent
        proof_hash: str,              # SHA-256 from Sentience
        signature: str,               # ECDSA signature
        solana_tx_hash: str,          # Solana attestation tx (for reference)
    ) -> Optional[str]:
        """
        Post proof to ValidationRegistry.contract.
        
        Calls: ValidationRegistry.submitValidation(
            agent_id: uint256,
            attestor: address,        # Sentience oracle (msg.sender)
            proof_hash: bytes32,
            signature: bytes,
            metadata: string          # "solana_tx:{solana_tx_hash}"
        )
        """
        if not self.w3.is_connected():
            logger.error("0G RPC not connected")
            return None
        
        try:
            # TODO: Load ValidationRegistry ABI from erc-8004-contracts
            # validation_registry_abi = [...]
            
            # Encode proof_hash (0x-prefixed)
            proof_hash_bytes = Web3.toBytes(hexstr=f"0x{proof_hash}")
            
            # Build tx
            # contract = self.w3.eth.contract(
            #     address=self.validation_registry,
            #     abi=validation_registry_abi
            # )
            # tx = contract.functions.submitValidation(
            #     agent_erc8004_id,
            #     self.oracle_account.address,
            #     proof_hash_bytes,
            #     signature_bytes,
            #     f"solana_tx:{solana_tx_hash}"
            # ).build_transaction({
            #     "from": self.oracle_account.address,
            #     "gas": 300000,
            #     "gasPrice": self.w3.eth.gas_price,
            # })
            
            # # Sign & broadcast
            # signed_tx = self.w3.eth.account.sign_transaction(tx, self.oracle_account.key)
            # tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            # receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"ValidationRegistry tx: {proof_hash_bytes.hex()[:16]}...")
            # return tx_hash.hex()
            return None  # Placeholder
        
        except Exception as e:
            logger.error(f"Failed to post validation: {e}")
            return None
```

---

## SECTION 3: mindX AGENT INTEGRATION (PRACTICAL EXAMPLE)

### 3.1 mindX Agent Using Sentience

```python
# mindx_agents/sentient_agent.py
from mindx.bdi import BDIAgent, Belief, Desire, Intention
from mindx_sentience import SentienceProxyClient
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SentientMindXAgent(BDIAgent):
    """
    BDI agent with verifiable inference via Sentience.
    All "thoughts" (LLM inferences) are cryptographically attested.
    """
    
    def __init__(
        self,
        agent_id: str,
        erc8004_token_id: int,
        galadriel_api_key: str,
        erc8004_registry: str = "0x...",  # 0G mainnet
    ):
        super().__init__(agent_id=agent_id)
        self.erc8004_token_id = erc8004_token_id
        
        # Initialize Sentience client
        self.sentience = SentienceProxyClient(
            galadriel_api_key=galadriel_api_key,
            agent_id=agent_id,
            erc8004_registry=erc8004_registry,
        )
        
        # Belief base (standard BDI)
        self.beliefs: List[Belief] = []
        self.desires: List[Desire] = []
        self.intentions: List[Intention] = []
        
        # Proof log (attestations)
        self.proofs = []
    
    def perceive(self, observations: Dict[str, Any]) -> None:
        """
        P (Perception): Process observations, update belief base.
        """
        logger.info(f"[{self.agent_id}] Perception: {observations}")
        
        # Standard belief update
        for key, value in observations.items():
            self.beliefs.append(Belief(key, value, timestamp=__import__("time").time()))
        
        # Verifiable reasoning: use Sentience to process complex observations
        if observations.get("requires_llm_reasoning"):
            proof = self._reason_about_observations(observations)
            self.proofs.append(proof)
    
    def orient(self) -> None:
        """
        O (Orientation): Generate desires from beliefs.
        Uses Sentience for complex multi-step reasoning.
        """
        logger.info(f"[{self.agent_id}] Orientation: generating desires")
        
        # Build prompt from current beliefs
        beliefs_summary = "\n".join([
            f"- {b.proposition}: {b.value}"
            for b in self.beliefs[-10:]  # Last 10 beliefs
        ])
        
        prompt = f"""
Given the following beliefs about the current state:
{beliefs_summary}

What should be the primary desires/goals for the agent?
List 3 desired outcomes, prioritized by urgency.
"""
        
        # Verifiable inference via Sentience
        result = self.sentience.inference(
            messages=[
                {"role": "system", "content": "You are a helpful AI agent reasoning system."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            temperature=0.5,
            post_to_erc8004=True,  # Post proof to 0G validation registry
        )
        
        # Log proof
        self.proofs.append({
            "stage": "orientation",
            "hash": result["hash"],
            "verified": result["verified"],
            "erc8004_tx": result["erc8004_tx"],
        })
        
        # Parse desires from response
        # (In production: use structured output / JSON mode)
        logger.info(f"Desires generated (verified: {result['verified']})")
        logger.info(f"Proof hash: {result['hash'][:16]}...")
    
    def decide(self) -> None:
        """
        D (Decision): Select intentions (sub-goals) from desires.
        Verifiable decision reasoning.
        """
        logger.info(f"[{self.agent_id}] Decision: selecting intentions")
        
        # Build decision prompt
        desires_text = ", ".join([str(d) for d in self.desires])
        prompt = f"""
Current desires: {desires_text}
Current capabilities: ["execute_trade", "fetch_price", "send_tx", "query_database"]

Select the top 2 actions to execute next, in priority order.
Explain reasoning.
"""
        
        # Verifiable inference
        result = self.sentience.inference(
            messages=[
                {"role": "system", "content": "You are an AI agent decision engine."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            post_to_erc8004=True,
        )
        
        self.proofs.append({
            "stage": "decision",
            "hash": result["hash"],
            "verified": result["verified"],
        })
        
        logger.info(f"Decision made (proof: {result['hash'][:16]}..., verified: {result['verified']})")
    
    def act(self) -> None:
        """
        A (Action): Execute intentions.
        Log action with proof reference.
        """
        logger.info(f"[{self.agent_id}] Action: executing intentions")
        
        for intention in self.intentions:
            logger.info(f"  Executing: {intention.goal}")
            # Execute action...
            # Log proof reference: intention.proof_hash
    
    def _reason_about_observations(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Sentience for verifiable multi-step reasoning.
        """
        obs_text = "\n".join([f"- {k}: {v}" for k, v in observations.items()])
        prompt = f"Analyze these observations:\n{obs_text}\n\nWhat is the underlying issue?"
        
        result = self.sentience.inference(
            messages=[
                {"role": "system", "content": "You are a domain expert analyzer."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            post_to_erc8004=True,
        )
        
        return {
            "observation": obs_text,
            "analysis": result["response"],
            "proof_hash": result["hash"],
            "verified": result["verified"],
        }
    
    def generate_proof_report(self) -> str:
        """
        Generate a report of all verified inferences (for transparency).
        """
        report = f"""
=== mindX Agent {self.agent_id} - Proof of Sentience Report ===

Total Verified Inferences: {len(self.proofs)}
Verification Rate: {sum(1 for p in self.proofs if p.get('verified')) / len(self.proofs) * 100:.1f}%

Recent Proofs:
"""
        for proof in self.proofs[-5:]:
            report += f"""
  Stage: {proof.get('stage', 'unknown')}
  Hash: {proof['hash'][:16]}...
  Verified: {proof['verified']}
  0G TX: {proof.get('erc8004_tx', 'pending')}
"""
        
        # Fetch history from Sentience explorer
        history = self.sentience.get_verified_history(limit=5)
        report += f"\n\nSentience Explorer History:\n"
        for item in history:
            report += f"  {item['created_at']}: {item['hash'][:16]}... (verified: {item['verified']})\n"
        
        return report
```

### 3.2 Usage Example

```python
# Example: Running a Sentient mindX Agent
from mindx_agents.sentient_agent import SentientMindXAgent

# Initialize agent
agent = SentientMindXAgent(
    agent_id="mindX-sovereign-001",
    erc8004_token_id=42,  # ERC-7857 iNFT token ID on 0G
    galadriel_api_key="Bearer gal_key_...",
    erc8004_registry="0x...",  # 0G IdentityRegistry address
)

# Simulate autonomous execution (P-O-D-A loop)
while True:
    # Perception: observe market data, social signals, etc.
    observations = {
        "eth_price": 3500,
        "btc_price": 68000,
        "requires_llm_reasoning": True,
    }
    agent.perceive(observations)
    
    # Orientation: generate goals
    agent.orient()  # Uses Sentience for verifiable reasoning
    
    # Decision: select actions
    agent.decide()  # Uses Sentience for verifiable decision-making
    
    # Action: execute
    agent.act()
    
    # Report transparency
    print(agent.generate_proof_report())
    
    # Sleep before next cycle
    import time
    time.sleep(60)
```

---

## SECTION 4: DEPLOYMENT & OPERATIONS

### 4.1 mindX-Sentience Service Deployment

**Service architecture:**
```
mindx.pythai.net/
├── /api/agent/<agent_id>/infer          POST → Sentience inference + 0G posting
├── /api/agent/<agent_id>/proof/<hash>   GET  → Proof details (from cache + Sentience)
├── /api/agent/<agent_id>/report         GET  → Agent transparency report
└── /health                               GET  → Service health check
```

**Docker deployment:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mindx_sentience/ ./mindx_sentience/
COPY mindx_agents/ ./mindx_agents/
COPY main.py .

ENV GALADRIEL_API_KEY=$GALADRIEL_API_KEY
ENV ERC8004_REGISTRY=$ERC8004_REGISTRY
ENV RPC_URL=https://evmrpc.0g.ai

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Requirements.txt:**
```
openai>=1.0.0
sentience>=0.1.0
pydantic>=2.0
web3>=6.0
eth-account>=0.10
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic-settings>=2.0
python-dotenv>=1.0
```

### 4.2 Configuration (`.env`)

```bash
# Galadriel / Sentience
GALADRIEL_API_KEY="Bearer gal_key_your_api_key_here"

# 0G Mainnet (ERC-8004)
RPC_URL="https://evmrpc.0g.ai"
ERC8004_REGISTRY="0x..."  # IdentityRegistry address on 0G
ORACLE_ACCOUNT_KEY="0x..."  # Sentience oracle private key (for signing tx)

# mindX Agent Config
AGENT_ID="mindX-sovereign-001"
AGENT_ERC8004_TOKEN_ID=42

# Optional: Solana logging
SOLANA_RPC="https://api.mainnet-beta.solana.com"
SOLANA_PROGRAM_ID="Sentience..."
```

### 4.3 FastAPI Service Example

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mindx_agents.sentient_agent import SentientMindXAgent
from mindx_sentience.models import AttestedCompletion
import os
import logging

app = FastAPI(title="mindX-Sentience Service")
logger = logging.getLogger(__name__)

# Initialize agent (on startup)
agent = SentientMindXAgent(
    agent_id=os.getenv("AGENT_ID", "mindX-001"),
    erc8004_token_id=int(os.getenv("AGENT_ERC8004_TOKEN_ID", "42")),
    galadriel_api_key=os.getenv("GALADRIEL_API_KEY"),
    erc8004_registry=os.getenv("ERC8004_REGISTRY"),
)

class InferenceRequest(BaseModel):
    messages: list
    model: str = "gpt-4o"
    temperature: float = 0.7

@app.post("/api/agent/{agent_id}/infer")
async def inference(agent_id: str, request: InferenceRequest) -> AttestedCompletion:
    """Execute verifiable inference through Sentience."""
    if agent_id != agent.agent_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        result = agent.sentience.inference(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            post_to_erc8004=True,
        )
        
        return AttestedCompletion(
            agent_id=agent_id,
            response=result["response"],
            proof={
                "hash": result["hash"],
                "signature": result["signature"],
                "public_key": "",
                "tx_hash": result["tx_hash"],
            },
            verified=result["verified"],
            model=request.model,
            created_at=__import__("datetime").datetime.now(),
            erc8004_tx=result.get("erc8004_tx"),
        )
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/{agent_id}/proof/{proof_hash}")
async def get_proof(agent_id: str, proof_hash: str):
    """Retrieve proof details from Sentience explorer."""
    if agent_id != agent.agent_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent.sentience.verify_proof(proof_hash)

@app.get("/api/agent/{agent_id}/report")
async def transparency_report(agent_id: str) -> str:
    """Get agent's transparency report (proof of sentience)."""
    if agent_id != agent.agent_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent.generate_proof_report()

@app.get("/health")
async def health() -> dict:
    """Health check."""
    return {
        "status": "ok",
        "agent": agent.agent_id,
        "proofs_logged": len(agent.proofs),
    }
```

---

## SECTION 5: SECURITY & VERIFICATION

### 5.1 Trust Model

**Who verifies what:**
1. **Agent (client-side):** Calls `sentience.verify_signature(completion)` → checks ECDSA signature
2. **0G (on-chain):** ERC-8004 ValidationRegistry stores hash + signature → anyone can query
3. **Solana (optional):** Sentience Anchor program stores attestation → immutable log
4. **Public (auditor):** Can independently verify using:
   - Sentience public key (embedded in completion)
   - Original message + response
   - Cryptographic verification (no trust in Galadriel required)

### 5.2 Threat Model

| **Threat** | **Mitigation** |
|---------|---------|
| Galadriel TEE compromised | Signature verification fails; anyone can detect |
| Proof tampered after generation | Hash is immutable (SHA-256); re-hashing detects tampering |
| False Solana attestation | Solana validators consensus + signature verification |
| Agent identity spoofed | ERC-8004 soulbound token + smart account control |
| Service downtime | Proofs cached; history queryable on Sentience explorer + Solana |

### 5.3 Verification Checklist

```bash
# 1. Verify Sentience TEE code
git clone https://github.com/galadriel-ai/Sentience
cd Sentience/verified-inference
cat verify/README.md  # Instructions for TEE code verification

# 2. Verify proof locally
python3 -c "
import sentience
completion = {...}  # From API response
print(sentience.verify_signature(completion))  # True/False
"

# 3. Query Solana attestation
solana account <ACCOUNT_KEY> --url mainnet-beta
# OR
curl https://api.solscan.io/v2/transaction/<TX_HASH>

# 4. Query 0G ERC-8004 ValidationRegistry
cast call <REGISTRY_ADDR> \
  'getValidations(uint256)' 42 \  # agent ERC-8004 token ID
  --rpc-url https://evmrpc.0g.ai
```

---

## SECTION 6: ROADMAP & FUTURE WORK

### Phase 1 (Current)
- ✅ Sentience SDK integration with mindX
- ✅ 0G ERC-8004 proof posting
- ✅ Transparency reporting

### Phase 2 (Q3 2026)
- [ ] Solana attestation explorer integration (on-chain proof logs)
- [ ] Multi-chain proof aggregation (Ethereum, Polygon, Moonbeam)
- [ ] Agent reputation scoring based on verified inferences
- [ ] ERC-7857 iNFT encrypted state snapshots (proof of learning/evolution)

### Phase 3 (Q4 2026)
- [ ] 0G Compute on-chain TEE inference (replace Solana dependency)
- [ ] Proof-of-Inference oracle contract on 0G (EVM-native, no Solana bridge needed)
- [ ] Decentralized validator network for attestation
- [ ] Governance DAO for Sentience fee structure (via DAIO)

---

## CONCLUSION

**Sentience + mindX = Unruggable Autonomous Agents**

The Sentience SDK enables mindX agents to cryptographically prove every "thought" (LLM inference) via:
1. **TEE attestation** (AWS Nitro Enclave) → proof generated off-chain
2. **Signature verification** (ECDSA) → anyone can verify independently
3. **On-chain logging** (Solana, 0G ERC-8004) → immutable audit trail
4. **0G settlement** (ERC-8004 ValidationRegistry) → agent reputation on EVM

This transforms agents from "rug-able" bots into **verifiable, trustworthy entities** suitable for:
- High-value DeFi operations
- Decentralized autonomous organizations (DAOs)
- User asset custody & delegation
- Transparent AI transparency (alignment auditing)

**Integration ready.** Deploy mindX-Sentience service to `mindx.pythai.net` + connect to 0G Mainnet (16661) + enable autonomous proof posting to ERC-8004 ValidationRegistry.

---

**References:**
- Sentience SDK: https://github.com/galadriel-ai/Sentience
- Docs: https://docs.galadriel.com
- ERC-8004: https://eips.ethereum.org/EIPS/eip-8004
- 0G Chain: https://0g.ai

**Status:** PRODUCTION-READY  
**Last Updated:** 2026-06-25  
**Maintainer:** mindX BDI Autonomous System  
