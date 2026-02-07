# Blueprint: mindX Framework

**Directive**: *Creating a blueprint for mindX, which aims to build a Gödel Machine–inspired system utilizing blockchain technology and PGVectorScale for storing memories as THOTs (Theory of the HOT — Higher Order Thought) and thlnks (links).*

**Status**: Living document  
**Related**: [DAIO](DAIO.md), [THOT_NEXT_STEPS](THOT_NEXT_STEPS.md), [Blueprint to Action Converter](blueprint_to_action_converter.md), [INDEX](INDEX.md)

---

## 1. Introduction

### 1.1 Overview

A **Gödel Machine** is a theoretical framework for self-improving systems: an agent that can modify its own code in a provably optimal way with respect to a utility function. In AI, this translates to systems that can *reflect upon their own algorithms* — examining, criticizing, and improving their reasoning and behavior. mindX implements this vision through a multi-agent BDI (Belief–Desire–Intention) orchestration layer, Gödel choice logging, and a memory layer that treats thoughts and links as first-class, persistable objects.

### 1.2 Objective

The primary goal of mindX is to operate as an **intelligent system that can reflect upon its own algorithms**, approaching a form of machine self-awareness:

- **Self-reference**: Agents (e.g. mindXagent, Mastermind, Coordinator) reason about system state, choices, and improvements.
- **Auditability**: Core decisions are logged as “Gödel choices” (perception, options, chosen option, rationale, outcome) in `data/logs/godel_choices.jsonl` and via `memory_agent.log_process()`.
- **Memory as data**: Memories and thoughts are stored as **THOTs** (Higher Order Thoughts) and **thlnks** (links between them), with optional blockchain-backed immutability and vector search via PGVectorScale.

This blueprint outlines how blockchain and PGVectorScale integrate with the existing mindX stack to store and retrieve THOTs and thlnks at scale.

---

## 2. Architecture Overview

### 2.1 Blockchain Layer

- **Purpose**: Secure, immutable storage and attestation for THOTs and thlnks; cryptographic identity and governance (see [DAIO](DAIO.md)).
- **CID (Content Identifier)**: Each THOT and thlnk can be identified by a **CID** (e.g. IPFS-style or multiformats). CIDs provide:
  - Content-addressable references for off-chain payloads (e.g. in PGVectorScale or object storage).
  - On-chain anchors: store only CID + metadata in smart contracts to keep gas costs low.
- **mindX alignment**: DAIO contracts (KnowledgeHierarchyDAIO, IDNFT, AgenticPlace), THOT tensor NFTs ([THOT_NEXT_STEPS](THOT_NEXT_STEPS.md)), and Ethereum-compatible wallets (IDManagerAgent) form the existing blockchain layer. THOTs/thlnks can be anchored via CIDs in dedicated registry or DAIO governance contracts.

### 2.2 PGVectorScale Layer

- **Purpose**: Efficiently manage and scale **vector representations** of memories and thoughts for fast similarity search and retrieval.
- **Role**: 
  - Embed THOTs (and optionally thlnks) into vectors; store vectors and metadata in PGVectorScale.
  - Support semantic search (“find thoughts related to X”), retrieval-augmented reasoning, and linking (thlnks) as graph edges or relation tables.
- **Scalability**: PGVectorScale is designed to scale with index size and query load; partitioning and indexing schemes (e.g. by agent_id, time, or namespace) keep performance predictable as the number of THOTs grows.

### 2.3 Layered View

```
┌─────────────────────────────────────────────────────────────────┐
│  mindX Orchestration (BDI, mindXagent, Coordinator, Mastermind)  │
├─────────────────────────────────────────────────────────────────┤
│  Memory Agent (data/, STM/LTM, log_process, godel_choices)       │
├─────────────────────────────────────────────────────────────────┤
│  THOTs & thlnks (logical model: thoughts + links)                │
├──────────────┬──────────────────────────────────────────────────┤
│  PGVectorScale │  Blockchain (DAIO, THOT contracts, CID refs)   │
│  (vectors,     │  (immutability, identity, governance)           │
│   search)      │                                                  │
└──────────────┴──────────────────────────────────────────────────┘
```

---

## 3. Technology Integration

### 3.1 Blockchain Implementation

- **Smart contracts**:
  - **Governance**: DAIO contracts enforce roles, proposals, and agent registry (see [DAIO](DAIO.md)).
  - **THOT/thlnk registry**: Contracts can record CIDs and minimal metadata (e.g. agent_id, timestamp, type) for THOTs and thlnks; full content lives off-chain (PGVectorScale + blob storage or IPFS).
  - **Rules**: Only authorized agents (or governance-approved addresses) may append or revoke references; deletion can be soft (revoke) or hard depending on policy.
- **Data structures (on-chain / CID payload)**:
  - **THOT**: e.g. `{ "cid": "<CID>", "agent_id": string, "timestamp": ISO8601, "type": "thot", "content_hash": string }` with payload at CID (text, embedding ref, or JSON).
  - **thlnk**: e.g. `{ "cid": "<CID>", "source_cid": string, "target_cid": string, "relation": string, "agent_id": string, "timestamp": ISO8601 }`.
  - Stored as JSON or equivalent in off-chain storage; on-chain only CID + hash + minimal metadata if needed.

### 3.2 PGVectorScale Implementation

- **Indexing**:
  - **Vectors**: One vector per THOT (and optionally per thlnk or relation). Embeddings from mindX’s LLM layer or a dedicated embedding model.
  - **Metadata**: Index by `agent_id`, `timestamp`, `type`, `cid` for filtering; use namespaces or schemas to separate STM vs LTM or per-agent buckets.
- **Scalability**:
  - Partition by time or agent to keep index segments manageable.
  - Tune index type (e.g. HNSW, IVFFlat) for latency vs recall.
  - Plan for re-indexing and backfill when embedding models or schemas change.

### 3.3 Existing mindX Components

- **memory_agent**: Already writes to `data/memory/` (STM/LTM, agent_workspaces, process_trace.jsonl), `data/logs/godel_choices.jsonl`. These can be treated as primary sources for “THOT-like” records and later synced to PGVectorScale + blockchain.
- **Identity**: IDManagerAgent + DAIO/IDNFT provide wallet-backed identity for agents; use `agent_id` and public address in THOT/thlnk metadata.
- **LLM/embedding**: mindX’s LLM factory and provider registry can drive embedding generation for THOTs before insertion into PGVectorScale.

---

## 4. Data Flow

### 4.1 Memory Creation and Storage

1. **Creation**: Agent (or orchestration layer) produces a thought or link (THOT or thlnk). Optional: generate embedding via mindX LLM/embedding API.
2. **Local persistence**: memory_agent continues to write to `data/memory/` and `data/logs/` (current behavior).
3. **CID**: Compute CID for the canonical JSON (or blob) of the THOT/thlnk; optionally store blob on IPFS or object storage.
4. **PGVectorScale**: Upsert vector + metadata (cid, agent_id, timestamp, type, etc.) into PGVectorScale.
5. **Blockchain**: Optional — submit CID + hash + minimal metadata to a THOT/thlnk registry or DAIO contract for attestation and immutability.

### 4.2 Tools and APIs

- **Existing**: `GET /mindxagent/logs/process`, `GET /godel/choices`, `GET /mindxagent/memory/logs` (and related) for reading actual logging and memory from mindX.
- **To add / extend**:
  - **PGVectorScale**: APIs or internal services to insert/query vectors (e.g. “store THOT”, “search THOTs by embedding or metadata”).
  - **Blockchain**: Use existing DAIO/THOT contract interfaces; add “register THOT by CID” and “register thlnk by CID” if needed.
  - **CID**: Library (e.g. multiformats) to generate and resolve CIDs; optional IPFS or S3 adapter for payload storage.

---

## 5. Security Considerations

### 5.1 Access Control

- **Roles**: Align with DAIO and existing mindX roles (e.g. Administrator, User, Agent). Agents get identity via IDManagerAgent/IDNFT; only authorized identities can create or update THOTs/thlnks in registry contracts.
- **Authentication**: Wallet-based auth (e.g. MetaMask, backend wallet) for human users; agent signing (see `agent_sign`, A2A) for machine-to-machine. All sensitive operations (e.g. governance, treasury) go through authenticated paths.

### 5.2 Data Privacy

- **In transit**: TLS for all API and frontend traffic; secure WebSockets where used.
- **At rest**: Encrypt sensitive payloads before storing in PGVectorScale or blob storage; keys managed via vault or KMS. On-chain data is public by design; store only CIDs and hashes on-chain, not private content.
- **PII**: Avoid storing PII in THOTs/thlnks unless necessary; if required, encrypt and enforce access policy and retention.

---

## 6. Future Enhancements

### 6.1 Self-Reflection Capabilities

- **Roadmap**: 
  - **Phase 1**: Consolidate existing Gödel choice and process logs into a queryable “thought stream” (already partially in place via mindXagent tab and `/godel/choices`, `/mindxagent/logs/process`).
  - **Phase 2**: Introduce a formal THOT/thlnk schema and write path from memory_agent to PGVectorScale (and optional CID/blockchain).
  - **Phase 3**: Enable agents to query “similar past thoughts” and “related thlnks” via PGVectorScale for better context in reasoning and self-improvement.
  - **Phase 4**: Use THOT/thlnk graphs and embeddings in strategic evolution and blueprint agents (see [Blueprint to Action Converter](blueprint_to_action_converter.md)) for richer self-reflection and plan generation.

### 6.2 Community and Open Source

- Encourage open-source contributions: clear docs (e.g. [INDEX](INDEX.md), [API](API.md)), contribution guidelines, and modular design so that blockchain and PGVectorScale integrations can be extended or swapped (e.g. different vector DB or L2) without rewriting the whole system.

---

## 7. Conclusion

mindX is architected as a **Gödel Machine–inspired system** with BDI orchestration, immutable audit logs (Gödel choices), and a memory layer under `data/`. This blueprint extends that foundation by:

- **THOTs and thlnks**: Formalizing memories and thoughts as content-addressable objects (CIDs) and link structures.
- **Blockchain**: Using DAIO and THOT contracts for attestation and identity; CIDs keep on-chain footprint small.
- **PGVectorScale**: Adding scalable vector search and retrieval for THOTs (and thlnks) to support self-reflection and RAG-style reasoning.

Implementing this in stages (logging and memory first, then PGVectorScale, then blockchain anchors) keeps the system manageable and aligned with the existing mindX codebase and directives.

---

**Last updated**: 2026-02-05  
**Directive reference**: *Creating a blueprint for mindX, which aims to build a Gödel Machine–inspired system utilizing blockchain technology and PGVectorScale for storing memories as THOTs and thlnks.*
