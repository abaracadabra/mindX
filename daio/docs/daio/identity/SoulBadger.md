# SoulBadger

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/identity/SoulBadger.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | Identity Layer |
| **Standard** | ERC721 + AccessControl (ERC-5484 Soulbound) |

## Summary

SoulBadger implements soulbound (non-transferable) tokens for permanent agent credentials. Based on ERC-5484, these tokens are permanently bound to their owner and cannot be transferred, only minted or burned. Integrates with AgenticPlace for credential verification in the marketplace.

## Purpose

- Create non-transferable credential badges for agents
- Store user/agent identity attributes (username, class, stats)
- Prevent credential trading by blocking transfers
- Integrate with AgenticPlace for marketplace verification
- Link to IDNFT tokens for extended identity

## Technical Specification

### Data Structures

```solidity
struct UserIdentity {
    string username;      // Display name
    string class;         // Agent class/role
    uint32 level;         // Experience level
    uint32 health;        // Health stat
    uint32 stamina;       // Stamina stat
    uint32 strength;      // Strength stat
    uint32 intelligence;  // Intelligence stat
    uint32 dexterity;     // Dexterity stat
}
```

### Access Roles

| Role | Description |
|------|-------------|
| `DEFAULT_ADMIN_ROLE` | Full admin access |
| `BADGE_ISSUER_ROLE` | Can mint new badges |

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `agenticPlace` | `IAgenticPlace` | Marketplace reference |
| `_userIdentities` | `mapping(uint256 => UserIdentity)` | Badge identities |
| `_badgeOwners` | `mapping(uint256 => address)` | Badge ownership |
| `_badgeToTokenId` | `mapping(uint256 => uint256)` | Link to IDNFT |
| `_baseBadgeUri` | `string` | Base URI for metadata |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `safeMint` | `to`, `username`, `class_`, `level`, `health`, `stamina`, `strength`, `intelligence`, `dexterity`, `linkedTokenId` | BADGE_ISSUER_ROLE | Mint new soulbound badge |
| `setAgenticPlace` | `_agenticPlace` | DEFAULT_ADMIN_ROLE | Set marketplace contract |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getUserIdentity` | `badgeId` | `(string, string, uint32, ...)` | Get badge identity data |
| `ownerOf` | `badgeId` | `address` | Get badge owner |
| `getLinkedTokenId` | `badgeId` | `uint256` | Get linked IDNFT token |
| `verifyCredential` | `user`, `badgeId` | `bool` | Verify user owns badge |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `BadgeMinted` | `badgeId`, `to`, `linkedTokenId` | New badge minted |
| `AgenticPlaceUpdated` | `oldPlace`, `newPlace` | Marketplace updated |

### Soulbound Behavior

The `_update` function enforces soulbound behavior:

```solidity
function _update(address to, uint256 tokenId, address auth)
    internal override returns (address) {
    address from = _ownerOf(tokenId);
    // Only allow minting (from == 0) or burning (to == 0)
    require(
        from == address(0) || to == address(0),
        "Soulbound: token transfer is BLOCKED"
    );
    return super._update(to, tokenId, auth);
}
```

## Usage Examples

### Minting a Soulbound Badge

```javascript
const to = agentWalletAddress;
const username = "TradingAgent001";
const class_ = "Analyst";
const level = 1;
const health = 100;
const stamina = 100;
const strength = 50;
const intelligence = 90;
const dexterity = 70;
const linkedTokenId = idnftTokenId; // Link to IDNFT

const tx = await soulBadger.safeMint(
    to,
    username,
    class_,
    level,
    health,
    stamina,
    strength,
    intelligence,
    dexterity,
    linkedTokenId
);

const receipt = await tx.wait();
const badgeId = receipt.events[0].args.badgeId;
```

### Verifying Credentials

```javascript
// Check if user owns a specific badge
const hasCredential = await soulBadger.verifyCredential(userAddress, badgeId);

if (hasCredential) {
    // User is verified for marketplace action
    await agenticPlace.hireSkillETH(skillTokenId, nftContract, { value: price });
}
```

### Getting Identity Data

```javascript
const [
    username,
    class_,
    level,
    health,
    stamina,
    strength,
    intelligence,
    dexterity
] = await soulBadger.getUserIdentity(badgeId);

console.log(`${username} (${class_}) - Level ${level}`);
console.log(`Stats: HP:${health} STA:${stamina} STR:${strength} INT:${intelligence} DEX:${dexterity}`);
```

### Checking Linked IDNFT

```javascript
const linkedIdnftTokenId = await soulBadger.getLinkedTokenId(badgeId);
const agentIdentity = await idnft.getAgentIdentity(linkedIdnftTokenId);
```

## UI Design Considerations

### Badge Minting Form
- Input: Recipient address
- Input: Username
- Dropdown: Class selection
- Sliders: Initial stats (level, health, stamina, strength, intelligence, dexterity)
- Select: Link to existing IDNFT (optional)
- Preview: Badge card

### Badge Profile Card
- Visual: Badge design with class icon
- Display: Username, class, level
- Stats: Radar chart or bars for attributes
- Link: To linked IDNFT profile
- Badge: "SOULBOUND" indicator

### Credential Verification UI
- Scanner: QR code to verify badge
- Display: Owner verification status
- Check: Real-time verification against blockchain
- History: Verification log

### Badge Collection View
- Grid: All badges for an address
- Filter: By class, level
- Sort: By date, level
- Note: Transfer button disabled with "Soulbound" tooltip

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// Issue credential badge for verified agent
async function issueSoulboundCredential(agentWallet, agentName, class_, idnftTokenId) {
    const badgeId = await soulBadger.safeMint(
        agentWallet,
        agentName,
        class_,
        1,    // Initial level
        100,  // health
        100,  // stamina
        50,   // strength
        75,   // intelligence
        60,   // dexterity
        idnftTokenId
    );

    return badgeId;
}

// Verify agent has required credential
async function verifyAgentCredential(agentWallet, requiredBadgeId) {
    return await soulBadger.verifyCredential(agentWallet, requiredBadgeId);
}
```

### For AgenticPlace Marketplace

```javascript
// Marketplace checks SoulBadger for credential verification
const isVerified = await soulBadger.verifyCredential(buyerAddress, requiredBadgeId);
if (!isVerified) {
    revert("Buyer lacks required credential");
}
```

### For IDNFT

```javascript
// IDNFT can reference SoulBadger for soulbound identities
const soulBadger = new ethers.Contract(soulBadgerAddress, soulBadgerABI, signer);
const linkedBadge = await soulBadger.getLinkedTokenId(idnftTokenId);
```

## Dependencies

- IAgenticPlace (marketplace interface)
- OpenZeppelin ERC721, AccessControl

## Security Considerations

- Tokens cannot be transferred (soulbound by design)
- Only BADGE_ISSUER_ROLE can mint new badges
- Owner lookup prevents non-existent token queries
- ERC-5484 compliant (only mint/burn, no transfers)
- Badge stats are immutable after minting

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `safeMint` | ~180,000 |
| `setAgenticPlace` | ~30,000 |
| `getUserIdentity` | View (free) |
| `verifyCredential` | View (free) |
| `ownerOf` | View (free) |

## ERC-5484 Compliance

SoulBadger implements the ERC-5484 (Soulbound Token) standard:

1. **Non-Transferable**: Tokens cannot be transferred between addresses
2. **Burn Authority**: Tokens can only be minted (from = 0) or burned (to = 0)
3. **Permanent Binding**: Once minted, the token is permanently bound to the recipient
4. **Credential Verification**: `verifyCredential` enables third-party verification
