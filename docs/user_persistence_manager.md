# User Persistence Manager Documentation

## Overview

The `UserPersistenceManager` manages user identities using wallet addresses as primary identifiers. All user actions are verified using wallet signatures, ensuring secure and authenticated user operations.

**File**: `tools/user_persistence_manager.py`  
**Class**: `UserPersistenceManager`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Wallet-Based Identity**: Wallet address as primary identifier
2. **Signature Verification**: All actions require signature verification
3. **User Agents**: Users can create and manage agents
4. **Persistent Storage**: JSON-based storage
5. **Security-First**: Cryptographic verification for all operations

### Core Components

```python
class UserPersistenceManager:
    - participants_dir: Path - Participants directory
    - users: Dict[str, UserIdentity] - User registry
    - signatures: Dict[str, List] - Signature history
    - user_agents: Dict[str, List] - User agents
```

## Data Structures

### UserIdentity

```python
@dataclass
class UserIdentity:
    wallet_address: str          # Primary identifier
    user_id: str                # Generated user ID
    created_at: float           # Creation timestamp
    last_active: float         # Last activity timestamp
    signature_count: int       # Total signatures
    agent_count: int           # Number of agents
    metadata: Dict[str, Any]   # Additional metadata
    public_key: Optional[str]  # Public key
```

### SignatureVerification

```python
@dataclass
class SignatureVerification:
    is_valid: bool              # Verification result
    message: str                # Signed message
    signature: str              # Signature
    recovered_address: Optional[str]  # Recovered address
    timestamp: float            # Verification timestamp
```

## Available Methods

### 1. `register_user`

Registers a new user with signature verification.

**Parameters**:
- `wallet_address` (str): User's wallet address
- `signature` (str): Signature of challenge message
- `message` (str): Challenge message
- `metadata` (Dict, optional): User metadata

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 2. `verify_signature`

Verifies a wallet signature.

**Parameters**:
- `wallet_address` (str): Wallet address
- `message` (str): Signed message
- `signature` (str): Signature

**Returns**: `SignatureVerification` object

### 3. `verify_user_action`

Verifies a user action with signature.

**Parameters**:
- `wallet_address` (str): User wallet
- `action` (str): Action name
- `signature` (str): Signature
- `message` (str): Challenge message

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 4. `create_user_agent`

Creates a user agent with signature verification.

**Parameters**:
- `wallet_address` (str): User wallet
- `agent_id` (str): Agent identifier
- `agent_type` (str): Agent type
- `signature` (str): Signature
- `message` (str): Challenge message
- `metadata` (Dict, optional): Agent metadata

**Returns**:
```python
Tuple[bool, str, Optional[str]]  # (success, message, agent_wallet)
```

### 5. `delete_user_agent`

Deletes a user agent with signature verification.

**Parameters**:
- `wallet_address` (str): User wallet
- `agent_id` (str): Agent to delete
- `signature` (str): Signature
- `message` (str): Challenge message

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 6. `get_user_agents`

Gets all agents for a user.

**Parameters**:
- `wallet_address` (str): User wallet

**Returns**: `List[Dict[str, Any]]`

### 7. `get_user_stats`

Gets user statistics.

**Parameters**:
- `wallet_address` (str): User wallet

**Returns**: `Dict[str, Any]`

### 8. `generate_challenge_message`

Generates a challenge message for signature.

**Parameters**:
- `wallet_address` (str): User wallet
- `action` (str): Action name

**Returns**: `str` (challenge message)

## Usage

### Register User

```python
from tools.user_persistence_manager import UserPersistenceManager

manager = UserPersistenceManager()

# Generate challenge
challenge = manager.generate_challenge_message(
    wallet_address="0x...",
    action="register"
)

# User signs challenge, then register
success, message = manager.register_user(
    wallet_address="0x...",
    signature="0x...",
    message=challenge,
    metadata={"name": "User Name"}
)
```

### Create User Agent

```python
# Generate challenge
challenge = manager.generate_challenge_message(
    wallet_address="0x...",
    action="create_agent"
)

# Create agent
success, message, agent_wallet = manager.create_user_agent(
    wallet_address="0x...",
    agent_id="user_agent_001",
    agent_type="analysis_agent",
    signature="0x...",
    message=challenge
)
```

### Verify Action

```python
# Verify user action
success, message = manager.verify_user_action(
    wallet_address="0x...",
    action="execute_task",
    signature="0x...",
    message=challenge
)
```

## Storage Structure

### Files

- `data/participants/users.json` - User identities
- `data/participants/signatures.json` - Signature history
- `data/participants/user_agents.json` - User agents

### Directory Structure

```
data/participants/
├── users.json
├── signatures.json
└── user_agents.json
```

## Security Features

### 1. Signature Verification

All operations require:
- Wallet signature
- Message verification
- Address recovery
- Signature validation

### 2. Challenge Messages

Challenge messages include:
- Action name
- Wallet address
- Timestamp
- Nonce

### 3. Signature History

Tracks all signatures:
- Verification results
- Timestamps
- Messages
- Recovered addresses

## Limitations

### Current Limitations

1. **eth_account Dependency**: Requires eth_account library
2. **No Multi-Chain**: Ethereum only
3. **Basic Storage**: JSON file storage
4. **No Encryption**: No data encryption
5. **No Backup**: No backup system

### Recommended Improvements

1. **Multi-Chain Support**: Support multiple blockchains
2. **Database Storage**: Use database instead of JSON
3. **Data Encryption**: Encrypt sensitive data
4. **Backup System**: Automatic backups
5. **Rate Limiting**: Prevent abuse
6. **Audit Logging**: Comprehensive audit logs
7. **API Integration**: REST API access

## Integration

### With eth_account

Uses eth_account for:
- Signature verification
- Address recovery
- Message encoding

## Examples

### Complete User Lifecycle

```python
# 1. Register user
challenge = manager.generate_challenge_message("0x...", "register")
success, _ = manager.register_user("0x...", signature, challenge)

# 2. Create agent
challenge = manager.generate_challenge_message("0x...", "create_agent")
success, _, agent_wallet = manager.create_user_agent(
    "0x...", "agent_001", "analysis", signature, challenge
)

# 3. Get user stats
stats = manager.get_user_stats("0x...")
```

## Technical Details

### Dependencies

- `eth_account`: Ethereum account management
- `dataclasses`: Data structures
- `hashlib`: Nonce generation
- `utils.config.Config`: Configuration

### Signature Verification

Uses Ethereum message signing:
```python
message_hash = encode_defunct(text=message)
recovered_address = Account.recover_message(message_hash, signature=signature)
```

## Future Enhancements

1. **Multi-Chain**: Support multiple blockchains
2. **Database**: Use database storage
3. **Encryption**: Encrypt sensitive data
4. **Backup**: Automatic backups
5. **API**: REST API access
6. **Rate Limiting**: Prevent abuse
7. **Audit Logs**: Comprehensive logging



