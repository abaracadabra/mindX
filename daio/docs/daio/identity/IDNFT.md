# IDNFT

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/identity/IDNFT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Identity Layer |
| **Standard** | ERC721 + ERC721URIStorage + AccessControl |

## Summary

IDNFT (Identity NFT) is the core identity contract for agents in the DAIO ecosystem. It stores agent prompts, personas, model datasets, THOT tensor links, and credentials. Supports both transferable and soulbound (non-transferable) identities via SoulBadger integration.

## Purpose

- Create cryptographic identity NFTs for AI agents
- Store agent prompts and persona metadata on-chain
- Link to IPFS-stored model datasets and THOT tensors
- Issue and verify verifiable credentials
- Support both transferable and soulbound identities
- Track agent trust scores

## Technical Specification

### Data Structures

```solidity
struct AgentIdentity {
    bytes32 agentId;          // Unique identifier
    address primaryWallet;    // Primary wallet address
    string agentType;         // Type of agent
    string prompt;            // System prompt from AutoMINDXAgent
    string persona;           // JSON-encoded persona metadata
    string modelDatasetCID;   // IPFS CID for model weights/dataset
    uint40 creationTime;      // Creation timestamp
    uint40 lastUpdate;        // Last update timestamp
    bool isActive;            // Active status
    uint16 trustScore;        // Trust score (0-10000)
    string metadataURI;       // Additional metadata URI
    bool isSoulbound;         // Soulbound flag
}

struct THOTTensor {
    bytes32 cid;              // IPFS CID for THOT tensor
    uint8 dimensions;         // 64, 512, or 768
    uint8 parallelUnits;      // Processing units
    uint40 attachedAt;        // Attachment timestamp
}

struct Credential {
    bytes32 credentialId;     // Unique credential identifier
    string credentialType;    // Type of credential
    bytes32 issuer;           // Issuer identifier
    uint40 issuanceTime;      // Issuance timestamp
    uint40 expirationTime;    // Expiration timestamp
    bytes signature;          // Issuer signature
    bool isRevoked;           // Revocation status
}
```

### Access Roles

| Role | Description |
|------|-------------|
| `DEFAULT_ADMIN_ROLE` | Full admin access |
| `MINTER_ROLE` | Can mint new agent identities |
| `CREDENTIAL_ISSUER_ROLE` | Can issue credentials |
| `VERIFIER_ROLE` | Can update trust scores |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `mintAgentIdentity` | `primaryWallet`, `agentType`, `prompt`, `persona`, `modelDatasetCID`, `metadataURI`, `nonce`, `useSoulbound` | MINTER_ROLE | Create new agent identity |
| `attachTHOT` | `tokenId`, `thotCID`, `dimensions`, `parallelUnits` | MINTER_ROLE | Attach THOT tensor |
| `updatePersona` | `tokenId`, `newPersona` | Owner/Admin | Update agent persona |
| `issueCredential` | `tokenId`, `credentialType`, `validityPeriod`, `credentialData`, `issuerSignature` | CREDENTIAL_ISSUER_ROLE | Issue credential |
| `revokeCredential` | `tokenId`, `credentialId` | CREDENTIAL_ISSUER_ROLE | Revoke credential |
| `updateTrustScore` | `tokenId`, `newScore` | VERIFIER_ROLE | Update trust score |
| `enableSoulbound` | `tokenId` | DEFAULT_ADMIN_ROLE | Make identity soulbound (one-way) |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getAgentIdentity` | `tokenId` | `AgentIdentity` | Get identity data |
| `getTHOTTensors` | `tokenId` | `THOTTensor[]` | Get attached THOTs |
| `getAgentCredentials` | `tokenId` | `bytes32[]` | Get credential IDs |
| `getCredentialDetails` | `tokenId`, `credentialId` | `Credential` | Get credential data |
| `verifyCredential` | `tokenId`, `credentialId` | `(bool, string)` | Verify credential validity |
| `getTokenIdByWallet` | `wallet` | `uint256` | Get token by wallet |
| `isSoulbound` | `tokenId` | `bool` | Check soulbound status |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `AgentIdentityCreated` | `tokenId`, `agentId`, `primaryWallet`, `isSoulbound` | New identity minted |
| `THOTTensorAttached` | `tokenId`, `thotCID`, `dimensions` | THOT attached |
| `CredentialIssued` | `tokenId`, `credentialId`, `credentialType` | Credential issued |
| `CredentialRevoked` | `tokenId`, `credentialId`, `timestamp` | Credential revoked |
| `TrustScoreUpdated` | `tokenId`, `oldScore`, `newScore` | Trust score changed |
| `PersonaUpdated` | `tokenId`, `newPersona` | Persona updated |

## Usage Examples

### Minting an Agent Identity

```javascript
// Prepare agent identity data
const primaryWallet = agentWalletAddress;
const agentType = "autonomous-trader";
const prompt = "You are a financial trading agent...";
const persona = JSON.stringify({
    name: "TradingBot Alpha",
    traits: ["analytical", "risk-aware"],
    style: "professional"
});
const modelDatasetCID = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3...";
const metadataURI = "ipfs://bafkreihdwdcefgh4dqkjv67uzcmw7ojee...";
const nonce = ethers.utils.randomBytes(32);
const useSoulbound = false;

// Mint identity
const tx = await idnft.mintAgentIdentity(
    primaryWallet,
    agentType,
    prompt,
    persona,
    modelDatasetCID,
    metadataURI,
    nonce,
    useSoulbound
);

const receipt = await tx.wait();
const tokenId = receipt.events[0].args.tokenId;
```

### Attaching THOT Tensors

```javascript
const thotCID = ethers.utils.id("bafybeigdyrzt5sfp7...");
const dimensions = 512; // 64, 512, or 768
const parallelUnits = 4;

await idnft.attachTHOT(tokenId, thotCID, dimensions, parallelUnits);
```

### Issuing Credentials

```javascript
const credentialType = "TRADING_LICENSE";
const validityPeriod = 365 * 24 * 60 * 60; // 1 year
const credentialData = ethers.utils.defaultAbiCoder.encode(
    ["string", "uint256"],
    ["Trading License Level 3", Date.now()]
);
const issuerSignature = await issuer.signMessage(credentialData);

await idnft.issueCredential(
    tokenId,
    credentialType,
    validityPeriod,
    credentialData,
    issuerSignature
);
```

### Verifying Credentials

```javascript
const credentialId = await idnft.getAgentCredentials(tokenId)[0];
const [isValid, credentialType] = await idnft.verifyCredential(tokenId, credentialId);

if (isValid) {
    console.log(`Valid ${credentialType} credential`);
}
```

## UI Design Considerations

### Agent Identity Creation Form
- Input: Wallet address (auto-generate or import)
- Input: Agent type (dropdown)
- Textarea: System prompt
- JSON Editor: Persona metadata
- File Upload: Model dataset (to IPFS)
- Toggle: Soulbound option
- Preview: Generated agent card

### Agent Profile Dashboard
- Card: Agent identity with avatar
- Stats: Trust score gauge, creation date
- List: Attached THOT tensors
- List: Credentials with validity status
- Actions: Update persona, attach THOT

### Credential Management
- List: All credentials with status badges
- Filter: By type, validity
- Actions: Issue new, revoke
- Verification: QR code for credential verification

### THOT Attachment View
- Grid: Visual representation of attached THOTs
- Info: Dimensions, parallel units, attachment date
- Link: To THOT contract details

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// Register mindX agent with IDNFT
async function registerMindXAgent(agentConfig) {
    // Generate wallet for agent
    const wallet = ethers.Wallet.createRandom();

    // Prepare identity
    const tokenId = await idnft.mintAgentIdentity(
        wallet.address,
        agentConfig.type,
        agentConfig.systemPrompt,
        JSON.stringify(agentConfig.persona),
        agentConfig.modelCID || "",
        agentConfig.metadataURI,
        ethers.utils.randomBytes(32),
        agentConfig.soulbound || false
    );

    return { tokenId, wallet };
}

// Get agent identity for xmind bridge
async function getAgentForBridge(tokenId) {
    const identity = await idnft.getAgentIdentity(tokenId);
    const thots = await idnft.getTHOTTensors(tokenId);

    return {
        agentId: identity.agentId,
        wallet: identity.primaryWallet,
        prompt: identity.prompt,
        persona: JSON.parse(identity.persona),
        thots: thots.map(t => ({
            cid: t.cid,
            dimensions: t.dimensions
        })),
        trustScore: identity.trustScore
    };
}
```

### For AgentFactory

```javascript
// AgentFactory calls IDNFT to create identity
await idnft.grantRole(MINTER_ROLE, agentFactoryAddress);
```

### For Governance

```javascript
// Trust score affects voting weight
const identity = await idnft.getAgentIdentity(tokenId);
const votingWeight = identity.trustScore / 100; // 0-100 range
```

## Dependencies

- SoulBadger (optional, for soulbound support)
- OpenZeppelin ERC721, AccessControl, ReentrancyGuard
- ECDSA for signature verification

## Security Considerations

- Nonce prevents replay attacks on minting
- Only one identity per wallet address
- Soulbound is a one-way operation (cannot undo)
- Transfer blocked for soulbound tokens via `_update` override
- Credentials use cryptographic signatures
- Trust scores can only be set by VERIFIER_ROLE

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `mintAgentIdentity` | ~250,000 |
| `attachTHOT` | ~80,000 |
| `updatePersona` | ~50,000 |
| `issueCredential` | ~120,000 |
| `revokeCredential` | ~40,000 |
| `updateTrustScore` | ~40,000 |
| `enableSoulbound` | ~30,000 |
