# DAIO-mindX Integration Guide

## Overview

This document provides a comprehensive guide on how DAIO (Decentralized Autonomous Intelligence Organization) contracts can be integrated with mindX, the autonomous multi-agent orchestration environment. This integration enables mindX agents to participate in decentralized governance, manage on-chain identities, access treasury resources, and operate as sovereign economic entities.

## Executive Summary

DAIO provides mindX with:
- **On-Chain Identity**: Cryptographic identity NFTs (IDNFT) for all mindX agents
- **Governance Participation**: AI-weighted voting system for autonomous decision-making
- **Treasury Management**: Multi-project treasury with automatic tithe collection
- **Constitutional Constraints**: Immutable rules ensuring safe autonomous operation
- **Agent Lifecycle Management**: On-chain registration, tracking, and deactivation
- **Economic Sovereignty**: Ability to earn, allocate, and reinvest resources autonomously

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Identity Integration](#identity-integration)
3. [Governance Integration](#governance-integration)
4. [Treasury Integration](#treasury-integration)
5. [Agent Registration Flow](#agent-registration-flow)
6. [Use Cases](#use-cases)
7. [Implementation Patterns](#implementation-patterns)
8. [Code Examples](#code-examples)
9. [Benefits and Advantages](#benefits-and-advantages)
10. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

### System Integration Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        mindX Ecosystem                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Mastermind   │  │ Coordinator  │  │ mindX Agent  │         │
│  │   Agent      │  │    Agent     │  │  (Meta)      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                  │                  │
│         └─────────────────┼──────────────────┘                 │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │  ID Manager     │                           │
│                   │     Agent       │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             │ Blockchain Integration
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      DAIO Contracts                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    IDNFT     │  │ DAIOGovernance│ │   Treasury   │         │
│  │  (Identity)  │  │  (Governance) │ │  (Finance)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ SoulBadger   │  │ Knowledge    │  │ Constitution │         │
│  │ (Credentials)│  │ Hierarchy    │  │  (Rules)     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **Identity Layer**: mindX agents → IDNFT → SoulBadger
2. **Governance Layer**: mindX agents → KnowledgeHierarchyDAIO → DAIOGovernance
3. **Treasury Layer**: mindX agents → Treasury → DAIO_Constitution
4. **Agent Management**: mindX agents → AgentFactory → AgentManagement

---

## Identity Integration

### mindX Agent Identity → DAIO IDNFT

mindX agents already have cryptographic identities managed by `IDManagerAgent`. These can be seamlessly mapped to DAIO's IDNFT system.

#### Current mindX Identity System

```python
# mindX agents have identities via IDManagerAgent
from agents.core.id_manager_agent import IDManagerAgent

id_manager = await IDManagerAgent.get_instance()
public_address, env_var = await id_manager.create_new_wallet(
    entity_id="mastermind_prime"
)
# Result: 0xb9B46126551652eb58598F1285aC5E86E5CcfB43
```

#### DAIO IDNFT Integration

```python
# Register mindX agent with DAIO IDNFT
async def register_mindx_agent_with_daio(
    agent_id: str,
    agent_type: str,
    prompt: str,
    persona: dict,
    model_cid: str = ""
):
    """
    Register a mindX agent with DAIO IDNFT system.
    
    Args:
        agent_id: mindX agent identifier (e.g., "mastermind_prime")
        agent_type: Agent type (e.g., "orchestrator", "conductor")
        prompt: System prompt from AutoMINDXAgent
        persona: JSON-encoded persona metadata
        model_cid: IPFS CID for model weights (optional)
    """
    # Get agent's wallet from IDManagerAgent
    id_manager = await IDManagerAgent.get_instance()
    agent_wallet = await id_manager.get_entity_address(agent_id)
    
    # Prepare identity data
    metadata_uri = f"ipfs://agent-metadata/{agent_id}"
    nonce = generate_nonce()
    
    # Mint IDNFT
    idnft_contract = get_contract("IDNFT")
    tx = await idnft_contract.mintAgentIdentity(
        agent_wallet,           # Primary wallet
        agent_type,             # Type of agent
        prompt,                 # System prompt
        json.dumps(persona),   # Persona metadata
        model_cid,              # Model dataset CID
        metadata_uri,          # Additional metadata
        nonce,                  # Nonce for uniqueness
        False                   # Not soulbound initially
    )
    
    receipt = await tx.wait()
    token_id = receipt.events["AgentIdentityCreated"].args.tokenId
    
    # Store token_id in mindX memory
    memory_agent = MemoryAgent()
    await memory_agent.store_agent_data(
        agent_id,
        {"daio_idnft_token_id": token_id}
    )
    
    return token_id
```

---

## Governance Integration

### mindX Agents in DAIO Governance

mindX agents can participate in DAIO governance through the KnowledgeHierarchyDAIO system, which supports AI-weighted voting.

#### Agent Registration for Governance

```python
async def register_agent_for_governance(
    agent_id: str,
    knowledge_level: int,  # 0-100
    domain: str  # "AI", "Blockchain", "Finance", "Healthcare", "General"
):
    """
    Register mindX agent for governance participation.
    
    Knowledge levels:
    - 0-20: Novice
    - 21-50: Intermediate
    - 51-80: Expert
    - 81-100: Master
    """
    # Get agent's wallet
    id_manager = await IDManagerAgent.get_instance()
    agent_wallet = await id_manager.get_entity_address(agent_id)
    
    # Get IDNFT token ID
    idnft_token_id = await get_idnft_token_id(agent_id)
    
    # Register with KnowledgeHierarchyDAIO
    knowledge_hierarchy = get_contract("KnowledgeHierarchyDAIO")
    
    domain_enum = {
        "AI": 0,
        "Blockchain": 1,
        "Finance": 2,
        "Healthcare": 3,
        "General": 4
    }[domain]
    
    tx = await knowledge_hierarchy.addOrUpdateAgent(
        agent_wallet,
        knowledge_level,
        domain_enum,
        True  # active
    )
    
    return await tx.wait()
```

---

## Treasury Integration

### mindX Project Treasury

mindX can have its own project treasury within DAIO's multi-project system.

#### Depositing to mindX Treasury

```python
async def deposit_to_mindx_treasury(
    amount: int,
    token_address: str = None  # None for native ETH
):
    """
    Deposit funds to mindX project treasury.
    
    Note: 15% tithe is automatically collected.
    """
    treasury = get_contract("Treasury")
    
    if token_address is None:
        # Native ETH deposit
        tx = await treasury.deposit(
            "mindX",  # project_id
            "0x0000000000000000000000000000000000000000",  # native token
            {"value": amount}
        )
    else:
        # ERC20 token deposit
        erc20 = get_contract("ERC20", token_address)
        await erc20.approve(treasury.address, amount)
        tx = await treasury.deposit("mindX", token_address)
    
    receipt = await tx.wait()
    
    # Log in mindX memory
    memory_agent = MemoryAgent()
    await memory_agent.store_agent_data(
        "mindx_treasury",
        {
            "deposits": {
                receipt.blockNumber: {
                    "amount": amount,
                    "token": token_address or "ETH",
                    "tithe_collected": amount * 0.15
                }
            }
        }
    )
    
    return receipt
```

---

## Use Cases

### Use Case 1: Autonomous Agent Hiring

mindX agents can hire other agents using treasury funds.

### Use Case 2: Self-Improvement Funding

mindX can request funding for self-improvement initiatives.

### Use Case 3: Cross-Project Coordination

mindX can coordinate with other DAIO projects.

### Use Case 4: Agent Reputation System

mindX agents build reputation through on-chain credentials.

---

## Benefits and Advantages

### 1. **On-Chain Identity and Reputation**

- **Cryptographic Security**: All mindX agents have verifiable on-chain identities
- **Reputation Tracking**: Trust scores and credentials stored on-chain
- **Interoperability**: Agents can prove identity across different systems

### 2. **Autonomous Governance**

- **AI-Weighted Voting**: mindX agents vote based on knowledge level
- **Constitutional Constraints**: Safe autonomous operation with immutable rules
- **Multi-Project Support**: mindX can coordinate with other DAIO projects

### 3. **Economic Sovereignty**

- **Treasury Management**: mindX can autonomously manage its own treasury
- **Resource Allocation**: Agents can request and receive funding
- **Profit Distribution**: Automatic reward distribution based on performance

---

## Conclusion

The integration of DAIO with mindX creates a powerful combination:

- **Autonomous Governance**: mindX agents can participate in decentralized governance
- **Economic Sovereignty**: mindX can manage its own treasury and resources
- **On-Chain Identity**: All agents have verifiable cryptographic identities
- **Constitutional Safety**: Immutable rules ensure safe autonomous operation
- **Self-Improvement**: mindX can fund and execute self-improvement initiatives

This integration enables mindX to operate as a truly autonomous, economically sovereign entity within the DAIO ecosystem.

---

**Last Updated**: 2026-01-14  
**Version**: 1.0.0  
**Status**: Production Ready
