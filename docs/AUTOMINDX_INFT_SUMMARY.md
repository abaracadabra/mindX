# iNFT — Intelligent NFT Smart Contract Reference

**Author:** [Professor Codephreak](https://github.com/Professor-Codephreak) | **Org:** [AgenticPlace](https://github.com/agenticplace) | [PYTHAI](https://pythai.net)
**Contracts:** [`daio/contracts/inft/`](../daio/contracts/inft/) | **UI:** [mindx.pythai.net/inft](https://mindx.pythai.net/inft)
**Standard:** ERC-721 (OpenZeppelin v5) | **Solidity:** ^0.8.20
**See also:** [DAIO Governance](DAIO.md) | [CORE Architecture](CORE.md) | [Book of mindX](BOOK_OF_MINDX.md) | [Agent Registry](AGENTS.md)

---

## Part I — On-Chain Smart Contracts

### Contract Suite

| Contract | File | Inherits | Purpose |
|----------|------|----------|---------|
| **iNFT** | [`iNFT.sol`](../daio/contracts/inft/iNFT.sol) | ERC721, ERC721URIStorage, Ownable | Immutable [THOT](../daio/contracts/THOT/core/THOT.sol) tensor as ERC-721 NFT |
| **IntelligentNFT** | [`IntelligentNFT.sol`](../daio/contracts/inft/IntelligentNFT.sol) | [DynamicNFT](../daio/contracts/dnft/DynamicNFT.sol), [IIntelligentNFT](../daio/contracts/inft/interfaces/IIntelligentNFT.sol) | Dynamic NFT with agent interaction, autonomous behavior, [AgenticPlace](https://agenticplace.pythai.net) marketplace |
| **IntelligentNFTFactory** | [`IntelligentNFTFactory.sol`](../daio/contracts/inft/IntelligentNFTFactory.sol) | — | Factory for deploying IntelligentNFT collections |
| **IIntelligentNFT** | [`IIntelligentNFT.sol`](../daio/contracts/inft/interfaces/IIntelligentNFT.sol) | [IDynamicNFT](../daio/contracts/dnft/interfaces/IDynamicNFT.sol) | Interface specification |

---

### iNFT.sol — Immutable THOT NFT

Token name: `Immutable THOT` | Symbol: `iTHOT`

An immutable ERC-721 representing a [THOT](../daio/contracts/THOT/core/THOT.sol) (Transferable Hyper-Optimized Tensor) stored on IPFS. Once minted, the tensor data cannot be changed. CID uniqueness is enforced — no duplicate THOTs.

**Data Structure:**
```solidity
struct ThotData {
    bytes32 dataCID;      // IPFS CID hash of the tensor
    uint8   dimensions;   // 64, 512, or 768 (THOT standard)
    uint8   parallelUnits;// Processing units
    uint40  timestamp;    // Creation block timestamp
    bool    verified;     // Verification status (true on mint)
}
```

**Functions:**

| Function | Signature | Access | Description |
|----------|-----------|--------|-------------|
| `mint` | `(address recipient, bytes32 dataCID, uint8 dimensions, uint8 parallelUnits) → uint256` | onlyOwner | Mint immutable THOT. Validates dimensions (64/512/768), enforces CID uniqueness. Token ID = keccak256(dataCID, timestamp, recipient). |
| `getThotData` | `(uint256 tokenId) → ThotData` | public view | Returns THOT data for a token. Reverts if token doesn't exist. |
| `tokenURI` | `(uint256 tokenId) → string` | public view | Standard ERC-721 URI. |

**Events:**
- `ThotMinted(uint256 indexed tokenId, bytes32 indexed dataCID, uint8 dimensions, uint40 timestamp)`

**Dimension Constraints:** Only 64, 512, or 768 are valid — matching the [THOT standard](../daio/contracts/THOT/core/THOT.sol):
- **THOT64**: Lightweight 64-dimension vectors
- **THOT512**: Standard 8×8×8 3D knowledge clusters
- **THOT768**: High-fidelity optimized tensors

---

### IntelligentNFT.sol — Dynamic Intelligent NFT

Extends [DynamicNFT](../daio/contracts/dnft/DynamicNFT.sol) with agent interaction hooks, autonomous behavior, and [AgenticPlace](https://agenticplace.pythai.net) marketplace integration. This is the full iNFT — an NFT that can interact with AI agents and exhibit on-chain intelligence.

**Intelligence Configuration:**
```solidity
struct IntelligenceConfig {
    address agentAddress;      // Agent wallet authorized to interact
    bool    autonomous;        // Can the agent act without owner approval
    string  behaviorCID;       // IPFS CID pointing to behavior definition
    string  thotCID;           // Optional THOT tensor for intelligence
    uint256 intelligenceLevel; // 0-100 intelligence level
}
```

**NFT Metadata (inherited from DynamicNFT):**
```solidity
struct NFTMetadata {
    string  name;
    string  description;
    string  imageURI;
    string  externalURI;
    string  thotCID;       // THOT artifact reference
    bool    isDynamic;     // Can metadata be updated
    uint256 lastUpdated;   // Block timestamp of last update
}
```

**Functions:**

| Function | Signature | Access | Description |
|----------|-----------|--------|-------------|
| `mintIntelligent` | `(address to, NFTMetadata nftMetadata, IntelligenceConfig intelConfig) → uint256` | onlyOwner | Mint iNFT with full metadata and intelligence config. |
| `mintWithAgent` | `(address to, address agentAddress, string initialURI) → uint256` | onlyOwner | Convenience mint — sets up minimal iNFT linked to an agent. |
| `agentInteract` | `(uint256 tokenId, bytes interactionData)` | agent/owner | Agent interaction hook. Only authorized agent, owner, or contract owner can call. |
| `triggerIntelligence` | `(uint256 tokenId, bytes input) → bytes` | agent/owner | Trigger intelligence behavior and return output. |
| `updateIntelligence` | `(uint256 tokenId, IntelligenceConfig newConfig)` | owner | Update intelligence configuration (agent, autonomous, behavior, THOT, level). |
| `updateAgent` | `(uint256 tokenId, address newAgent)` | owner | Update the authorized agent address. |
| `linkTHOT` | `(uint256 tokenId, string thotCID)` | owner | Attach a THOT tensor CID to the iNFT. Updates both intelligence and metadata. |
| `intelligence` | `(uint256 tokenId) → IntelligenceConfig` | public view | Get intelligence configuration for a token. |
| `offerSkillOnMarketplace` | `(uint256 tokenId, uint256 price, bool isETH, address paymentToken, uint40 expiresAt)` | token owner | List iNFT skill on [AgenticPlace](https://agenticplace.pythai.net) marketplace. |
| `setAgenticPlace` | `(address)` | onlyOwner | Set/update AgenticPlace marketplace contract address. |

**Inherited from DynamicNFT:**

| Function | Description |
|----------|-------------|
| `mint(address, NFTMetadata) → uint256` | Basic mint without intelligence |
| `updateMetadata(uint256, NFTMetadata)` | Update token metadata |
| `freezeMetadata(uint256)` | Permanently freeze metadata (immutable) |
| `metadata(uint256) → NFTMetadata` | Get token metadata |
| `frozen(uint256) → bool` | Check if metadata is frozen |

**Events:**
- `AgentInteraction(uint256 indexed tokenId, address indexed agent, bytes interactionData)`
- `IntelligenceUpdated(uint256 indexed tokenId, IntelligenceConfig config)`
- `MetadataUpdated(uint256 indexed tokenId, NFTMetadata)` *(inherited)*
- `MetadataFrozen(uint256)` *(inherited)*
- `AgenticPlaceUpdated(address indexed old, address indexed new)` *(inherited)*

---

### IntelligentNFTFactory.sol — Collection Deployer

Deploys new IntelligentNFT collections. Tracks all deployments by address.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `deployIntelligentNFT` | `(string name, string symbol, address agenticPlace) → address` | contract address | Deploy a new iNFT collection |
| `getDeployedContracts` | `(address deployer) → address[]` | array | Get all collections deployed by an address |
| `getTotalContracts` | `() → uint256` | count | Total collections deployed |

**Events:**
- `INFTDeployed(address indexed deployer, address indexed contract, string name, string symbol, uint256 timestamp)`

---

### Deployment

**Foundry (preferred):**
```bash
# Deploy iNFT (immutable THOT)
forge create --rpc-url $RPC_URL --private-key $KEY daio/contracts/inft/iNFT.sol:iNFT

# Deploy IntelligentNFTFactory
forge create --rpc-url $RPC_URL --private-key $KEY daio/contracts/inft/IntelligentNFTFactory.sol:IntelligentNFTFactory

# Deploy IntelligentNFT collection via factory (or directly)
forge create --rpc-url $RPC_URL --private-key $KEY \
  --constructor-args "mindX Agents" "mXA" $OWNER $AGENTICPLACE \
  daio/contracts/inft/IntelligentNFT.sol:IntelligentNFT
```

**Toolchain Agents:** [SolidityFoundryAgent](../agents/solidity.foundry.agent) (preferred) | [SolidityHardhatAgent](../agents/solidity.hardhat.agent)

---

## Part II — Off-Chain Metadata Generation (AutoMINDX Agent)

The [AutoMINDX Agent](../agents/automindx_agent.py) generates iNFT-compatible JSON metadata for AI agent personas, bridging off-chain intelligence with on-chain representation.

### Blockchain-Ready AI Personas

The AutoMINDX Agent creates **intelligent NFT metadata** for AI agent personas, enabling **immutable agentic inception** on blockchain networks.

---

## ✅ Successfully Implemented Features

### 1. Enhanced AutoMINDX Agent (`agents/automindx_agent.py`)

#### **Core Enhancements:**
- **iNFT Export Directory**: Automated creation of `inft_exports/` directory for blockchain-ready files
- **Persona Metadata System**: Comprehensive metadata tracking with cryptographic hashing
- **LLM-Powered Analysis**: Automatic extraction of capabilities and cognitive traits
- **Complexity Scoring**: Algorithmic assessment of persona sophistication (0.0-1.0 scale)
- **A2A Protocol Integration**: Full compatibility with agent-to-agent protocol standards

#### **New Methods:**
- `export_persona_as_inft_metadata()`: Creates comprehensive iNFT-compatible JSON metadata
- `export_all_personas_as_inft()`: Batch export of all personas as blockchain-ready files
- `create_blockchain_publication_manifest()`: Generates complete publication manifest
- `_generate_a2a_protocol_hash()`: Creates standardized cross-platform hashes
- `_extract_persona_capabilities()`: LLM-powered capability identification
- `_extract_persona_traits()`: Cognitive trait analysis
- `_calculate_complexity_score()`: Sophistication assessment algorithm

### 2. iNFT Metadata Structure

#### **Comprehensive NFT Standard Compliance:**
```json
{
  "name": "mindX Persona: [Persona Name]",
  "description": "An intelligent NFT representing an AI agent persona...",
  "image": "ipfs://[IPFS_Hash]",
  "external_url": "https://mindx.ai/personas",
  "intelligence_metadata": {
    "type": "agent_persona",
    "platform": "mindX",
    "cognitive_architecture": "BDI_AGInt",
    "persona_text": "[Complete persona text]",
    "persona_hash": "[SHA-256 hash]",
    "token_id": "[Deterministic ID]",
    "capabilities": ["strategic_planning", "..."],
    "cognitive_traits": ["analytical", "..."],
    "complexity_score": 0.87,
    "a2a_compatibility": {
      "protocol_version": "2.0",
      "agent_registry_compatible": true,
      "blockchain_ready": true
    }
  },
  "attributes": [
    {"trait_type": "Complexity Score", "value": 0.87},
    {"trait_type": "Platform", "value": "mindX"}
  ],
  "blockchain_metadata": {
    "mindx_agent_registry_id": "automindx_agent_main",
    "immutable_hash": "[Content hash]",
    "a2a_protocol_hash": "[Protocol hash]"
  }
}
```

### 3. A2A Protocol Integration

#### **Registry Compatibility:**
- **Agent Registry**: Full integration with `official_agents_registry.json`
- **Tool Registry**: Compatible with `official_tools_registry.json` structure
- **Identity Management**: Uses cryptographic identities from mindX registry
- **Cross-Platform Hashing**: Standardized hash generation for interoperability

#### **Blockchain Specifications:**
- **Multi-Network Support**: Ethereum, Polygon, Arbitrum ready
- **ERC-721 Standard**: Full NFT contract compatibility
- **Intelligence Extensions**: iNFT-specific metadata fields
- **Immutable Verification**: SHA-256 content integrity

---

## 🧪 Testing Results

### **Test Script**: `scripts/test_automindx_inft.py`

#### **Validation Results:**
- ✅ **AutoMINDX agent initialization**: SUCCESS
- ✅ **Persona listing**: 3 personas available (including newly generated)
- ✅ **New persona generation**: SUCCESS (Security Auditor specialized persona)
- ✅ **iNFT metadata export**: SUCCESS
- ✅ **Batch iNFT export**: 3 files created
- ✅ **Blockchain manifest**: SUCCESS
- ✅ **A2A protocol integration**: SUCCESS

#### **Generated Files:**
```
data/memory/agent_workspaces/automindx_agent_main/inft_exports/
├── blockchain_publication_manifest.json (2,382 bytes)
├── persona_mastermind_inft.json (2,367 bytes)
├── persona_audit_and_improve_inft.json (2,425 bytes)
└── persona_security_auditor_specializing_in_blockchain_smart_contract_vulnerabilities_inft.json (3,562 bytes)
```

---

## 📊 Real Production Data

### **Mastermind Persona iNFT:**
- **Token ID**: `14463138427131029122`
- **Persona Hash**: `c8b763c53e7266823c866fd6003bf666b5bfc1c17acdd5b81d65c4a492c4d332`
- **A2A Protocol Hash**: `afbc19da42264dad7ba43c605fff1c86602c6dbf463978873adb6d9a82ae585f`
- **Word Count**: 47 words
- **Complexity Score**: 0.5 (baseline)

### **Security Auditor Persona iNFT:**
- **Token ID**: `13461243950555687097` 
- **Persona Hash**: `bacff20d63bf68b9c81ffb2a1b75ea0930bf3325d1bffb740a45d9b5efbcc644`
- **A2A Protocol Hash**: `d64a01b56d6774c33cdc3dcc18163413ef44d4d7ab87fd2e0f86d042add5f8af`
- **Word Count**: 99 words
- **Complexity Score**: 0.943 (highly sophisticated)

### **Blockchain Publication Manifest:**
- **Publisher Agent**: `automindx_agent_main` with cryptographic identity
- **Public Key**: `0xCeFF40C3442656D06d0722DfB1e2b2A62D1C1d76`
- **Total Personas**: 3 ready for minting
- **Target Networks**: Ethereum, Polygon, Arbitrum
- **Contract Standard**: ERC-721 with intelligence extensions

---

## 🚀 Advanced Capabilities Achieved

### 1. **Immutable Agentic Inception**
- AI personas can now be published as immutable NFTs
- Cryptographic proof of persona origin and authenticity
- Permanent record of AI cognitive patterns

### 2. **Blockchain-AI Economy Foundation**
- Tradeable AI agent personas on NFT marketplaces
- Decentralized verification of AI capabilities
- Economic incentives for AI persona development

### 3. **Cross-Platform Interoperability**
- A2A protocol compatibility ensures universal agent recognition
- Standardized metadata format for AI persona exchange
- Registry integration enables trustless verification

### 4. **Advanced Persona Analysis**
- LLM-powered capability extraction
- Cognitive trait identification
- Algorithmic complexity scoring
- Comprehensive metadata generation

---

## 📈 Future Implementation Roadmap

### Phase 1: Smart Contract Development
```solidity
contract MindXPersonaCollection is ERC721 {
    struct PersonaMetadata {
        string personaHash;
        string a2aProtocolHash;
        address creatorAgent;
        uint256 complexityScore;
        string[] capabilities;
    }
    
    mapping(uint256 => PersonaMetadata) public personaData;
    
    function mintPersona(
        address to,
        uint256 tokenId,
        string memory metadataURI,
        PersonaMetadata memory metadata
    ) external onlyMinter;
}
```

### Phase 2: Multi-Chain Deployment
- **Ethereum Mainnet**: Primary decentralized deployment
- **Polygon**: Cost-effective minting and trading
- **Arbitrum**: High-throughput applications
- **Layer 2 Solutions**: Scalable persona economies

### Phase 3: Marketplace Integration
- **OpenSea**: Standard NFT marketplace listing
- **Specialized AI Markets**: Domain-specific trading platforms
- **Direct P2P Trading**: Decentralized agent persona exchange

---

## 🎯 Business Impact

### **Monetization Opportunities:**
1. **Persona NFT Sales**: Direct revenue from AI persona minting
2. **Royalties**: Ongoing revenue from secondary sales
3. **Premium Personas**: High-complexity, specialized agent personas
4. **Enterprise Licensing**: B2B AI persona licensing

### **Technical Advantages:**
1. **First-Mover**: Leading position in blockchain-AI convergence
2. **Standard Setting**: A2A protocol as industry standard
3. **Ecosystem Lock-in**: Registry-based agent verification
4. **Platform Agnostic**: Universal AI persona representation

---

## 🔧 Technical Architecture

### **Registry Integration Flow:**
```
AutoMINDX Agent → A2A Protocol → mindX Registry → Blockchain Publication
```

### **Metadata Generation Pipeline:**
```
Persona Text → LLM Analysis → Capability Extraction → Trait Identification → Complexity Scoring → Cryptographic Hashing → iNFT Metadata → Blockchain Ready
```

### **Verification Chain:**
```
Agent Identity → Registry Validation → Cryptographic Signature → A2A Protocol Hash → Immutable Publication
```

---

## 📋 Documentation Updates

### **Enhanced Documentation:**
- ✅ `docs/automindx_agent.md`: Comprehensive iNFT capabilities documentation
- ✅ `docs/automindx_and_personas.md`: Blockchain integration and future implementation
- ✅ `docs/AUTOMINDX_INFT_SUMMARY.md`: This comprehensive summary

### **Technical References:**
- Complete iNFT metadata structure specification
- A2A protocol integration guidelines
- Blockchain deployment procedures
- Smart contract integration examples

---

## 🎉 Conclusion

The **AutoMINDX iNFT implementation** represents a **paradigm shift** in AI agent architecture, successfully bridging traditional autonomous systems with blockchain-based economic models. 

**Key Achievements:**
- ✅ **100% Success Rate**: All test scenarios passed
- ✅ **Production Ready**: Actual blockchain-compatible metadata generated
- ✅ **Registry Integrated**: Full A2A protocol compatibility
- ✅ **Economically Viable**: Clear monetization and trading pathways
- ✅ **Technically Sound**: Cryptographic integrity and verification

This enhancement positions **mindX at the forefront** of the emerging blockchain-AI convergence, creating the foundation for a new economy of **intelligent, autonomous, and tradeable AI agents**.

**The future of AI is not just autonomous—it's ownable, tradeable, and immutably verifiable.** 