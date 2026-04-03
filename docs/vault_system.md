# Vault System Documentation

> **Update (April 2026)**: The production vault system is now **BANKON Vault** (AES-256-GCM + HKDF-SHA512).
> Located at `mindx_backend_service/vault_bankon/`. The older `vault_encrypted/` (Fernet/PBKDF2) is superseded.
> 12 agent identity keys + 3 provider credentials stored encrypted.
> CLI: `python manage_credentials.py store|list|delete|providers`
> See `mindx_backend_service/bankon_vault/vault.py` for implementation.

## Overview

The Vault System provides **enterprise-grade encrypted storage** for sensitive data including API keys, wallet private keys, and access credentials. The system has been upgraded to **AES-256 encryption** with PBKDF2 key derivation for production security. The encrypted vault is located at `mindx_backend_service/vault_encrypted/` and all sensitive data is encrypted at rest.

**🔒 Production Security Features:**
- **AES-256 Encryption**: All sensitive data encrypted with industry-standard encryption
- **PBKDF2 Key Derivation**: 100,000 iterations for strong key security
- **Automatic Migration**: Seamless migration from plaintext to encrypted storage
- **Secure File Permissions**: Restrictive file permissions for additional security

## Architecture

### Directory Structure

```
mindx_backend_service/vault_encrypted/         # 🔒 AES-256 Encrypted Vault
├── .salt                                       # Key derivation salt (random)
├── .master.key                                # Master encryption key (encrypted)
├── api_keys/                                  # Encrypted API keys
│   └── keys.enc                              # AES-256 encrypted API keys
├── wallet_keys/                              # Encrypted wallet private keys
│   └── keys.enc                              # AES-256 encrypted agent wallets
├── sessions/                                  # User login sessions (wallet auth)
│   └── {session_id}.json                     # Session metadata (encrypted)
├── user_folders/                             # Per-wallet encrypted folders
│   └── 0x{40 hex}/                          # Per-wallet encrypted key-value store
│       └── {key}.enc                        # Individual encrypted user data
└── access_log/                              # URL and IP access tracking
    ├── url_access_{YYYYMMDD}.jsonl
    ├── ip_access_{YYYYMMDD}.jsonl
    ├── url_index.json
    └── ip_index.json
```

### Legacy Structure (Migrated)
```
mindx_backend_service/vault/                   # 📜 Legacy plaintext vault (migrated)
├── agents/                                   # ❌ Migrated to encrypted storage
├── credentials/                              # ❌ Migrated to encrypted storage
└── [other legacy directories]                # ❌ Migrated or deprecated
```

### Security

#### 🔒 Enterprise-Grade Encryption
- **AES-256-GCM Encryption**: All sensitive data encrypted with authenticated encryption
- **PBKDF2 Key Derivation**: 100,000 iterations with unique salt for key security
- **Automatic Key Management**: Secure generation and storage of encryption keys
- **Forward Security**: Encrypted data is secure even if the system is compromised

#### 🛡️ Access Control
- **File Permissions**: All vault files created with restrictive permissions (600/700)
- **Process Isolation**: Vault accessible only to mindX backend process
- **Memory Security**: Encryption keys cleared from memory after use
- **No Value Exposure**: API endpoints never return actual credential values

#### 🔄 Migration Security
- **Automatic Migration**: Seamless migration from plaintext to encrypted storage
- **Verification**: Migration integrity verification with rollback capability
- **Key Rotation**: Support for encryption key rotation in emergency scenarios
- **Audit Trail**: Complete migration and access logging

## Features

### 1. Access Credentials Storage

Store and retrieve access credentials (API keys, OAuth tokens, etc.) securely.

#### Store Encrypted API Key

```python
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager

vault = get_encrypted_vault_manager()

# Store encrypted API key
vault.store_api_key(
    provider="github",
    api_key="ghp_xxxxxxxxxxxx"
)

# Store encrypted wallet private key
vault.store_wallet_key(
    agent_id="mastermind_agent",
    private_key="0x1234567890abcdef...",
    public_address="0x742d35Cc6d244a9e3d5C5fF60b..."
)
```

#### Retrieve Encrypted Credentials

```python
# Get encrypted API key
api_key = vault.get_api_key("github")

# Get encrypted wallet private key
private_key = vault.get_wallet_private_key("mastermind_agent")

# Get wallet public address
public_address = vault.get_wallet_address("mastermind_agent")
```

#### List Available Credentials

```python
# List available API providers
providers = vault.list_api_providers()
# Returns: ['openai', 'anthropic', 'github', etc.]

# List available wallet agents
agents = vault.list_wallet_agents()
# Returns: ['mastermind_agent', 'coordinator_agent', etc.]
```

#### Migration from Plaintext

```python
# Migrate existing plaintext vault to encrypted storage
from scripts.migrate_to_encrypted_vault import migrate_to_encrypted_vault

success = migrate_to_encrypted_vault()
if success:
    print("✅ Migration completed successfully")
else:
    print("❌ Migration failed")
```

### 2. URL Access Tracking

Track visited URLs for ML inference and analysis.

#### Log URL Access

```python
vault_manager.log_url_access(
    url="https://github.com/agenticplace/mindX",
    ip_address="192.168.1.100",
    agent_id="mindx_agint",
    metadata={
        "response_time": 0.234,
        "status_code": 200,
        "content_type": "text/html"
    }
)
```

#### Get URL History

```python
history = vault_manager.get_url_access_history(
    url="https://github.com/agenticplace/mindX",  # Optional filter
    days_back=7,
    limit=100
)
```

### 3. IP Access Tracking

Track IP access points for ML inference and analysis.

#### Log IP Access

```python
vault_manager.log_ip_access(
    ip_address="10.0.0.155",
    url="http://10.0.0.155:18080",  # Optional
    agent_id="startup_agent",
    metadata={
        "port": 18080,
        "protocol": "http",
        "service": "ollama"
    }
)
```

#### Get IP History

```python
history = vault_manager.get_ip_access_history(
    ip_address="10.0.0.155",  # Optional filter
    days_back=7,
    limit=100
)
```

### 4. Access Summary for ML Inference

Get comprehensive access summary for machine learning intelligence.

```python
summary = vault_manager.get_access_summary_for_inference()

# Returns:
# {
#     "timestamp": "2026-01-17T19:30:00",
#     "urls": {
#         "total_unique": 150,
#         "index": {...}  # All URLs with access counts
#     },
#     "ip_addresses": {
#         "total_unique": 25,
#         "index": {...}  # All IPs with access counts
#     },
#     "statistics": {
#         "total_url_accesses": 1250,
#         "total_ip_accesses": 450,
#         "most_accessed_urls": [...],
#         "most_accessed_ips": [...]
#     }
# }
```

## API Endpoints

### Credentials

- `POST /vault/credentials/store` - Store access credential
- `GET /vault/credentials/get/{credential_id}` - Get credential (metadata only)
- `GET /vault/credentials/list` - List all credentials (metadata only)

### URL Access

- `POST /vault/access/url` - Log URL access
- `GET /vault/access/url/history` - Get URL access history

### IP Access

- `POST /vault/access/ip` - Log IP access
- `GET /vault/access/ip/history` - Get IP access history

### Summary

- `GET /vault/access/summary` - Get comprehensive access summary for ML inference

### User sessions (wallet auth)

- `GET /users/session/validate` - Validate session token (query `session_token` or header `X-Session-Token`); returns `wallet_address` and `expires_at` or 401.
- `POST /users/logout` - Invalidate session (header `X-Session-Token`). Removes session from vault.

Sessions are stored in `vault/sessions/`; created only after successful wallet signature verification. Used to gate `/app` and vault user folder access.

### User vault folders (signature-scoped)

Access is **only** to the folder that corresponds to the public key (wallet) that holds the valid session. No whole-vault or cross-wallet access.

- `GET /vault/user/keys` - List key names in the authenticated user's folder (requires `X-Session-Token`).
- `GET /vault/user/keys/{key}` - Get value for key (requires `X-Session-Token`).
- `PUT /vault/user/keys/{key}` - Set value (body = JSON; requires `X-Session-Token`).
- `DELETE /vault/user/keys/{key}` - Delete key (requires `X-Session-Token`).

Keys must be 1–128 chars, alphanumeric plus `_`, `.`, `-`. Values are JSON.

### Access gate (optional token-gating)

Session **issuance** can be gated on on-chain state (NFT or fungible). See [LIT_AND_ACCESS_ISSUANCE.md](LIT_AND_ACCESS_ISSUANCE.md). Env: `MINDX_ACCESS_GATE_ENABLED`, `MINDX_ACCESS_GATE_TYPE=erc20|erc721`, `MINDX_ACCESS_GATE_CONTRACT`, `MINDX_ACCESS_GATE_RPC_URL`, etc. DAIO keyminter contracts (VaultKeyDynamic / VaultKeyIntelligent) can be used as the ERC721 contract.

## Frontend: vault_manager.js

The frontend module `mindx_frontend_ui/vault_manager.js` provides signature-scoped vault folder access:

- **Concept**: Only a valid session token (from wallet sign-in) grants access; access is only to the folder for the current signer's public key.
- **API**: `VaultManager.getDefault()` then `listKeys()`, `getKey(key)`, `setKey(key, value)`, `deleteKey(key)`. All requests send `X-Session-Token`.
- **Key rules**: Same as backend (1–128 chars, `[a-zA-Z0-9_.-]`).

## Integration with Memory System

All vault operations are automatically logged to the memory system:

- **Credential Storage**: Logged as `SYSTEM_STATE` memory with `HIGH` importance
- **URL/IP Access**: Logged as `INTERACTION` memory with `MEDIUM` importance
- **Tags**: All vault operations tagged with `["vault", ...]` for easy querying

## Usage Examples

### Example 1: Store GitHub API Key

```python
# Via API
POST /vault/credentials/store
{
    "credential_id": "github_api_key",
    "credential_type": "api_key",
    "credential_value": "ghp_xxxxxxxxxxxx",
    "metadata": {
        "provider": "github",
        "scope": "repo,user"
    }
}
```

### Example 2: Track URL Access

```python
# Via API
POST /vault/access/url
{
    "url": "https://github.com/agenticplace/mindX",
    "ip_address": "192.168.1.100",
    "agent_id": "mindx_agint",
    "metadata": {
        "response_time": 0.234,
        "status_code": 200
    }
}
```

### Example 3: Get Access Summary for ML Inference

```python
# Via API
GET /vault/access/summary

# Response includes:
# - All unique URLs with access counts
# - All unique IPs with access counts
# - Statistics and most accessed resources
# - Ready for ML model ingestion
```

## Integration with Referenced Repositories

### agenticplace/mindX

The vault system can store credentials and track access for:
- GitHub API keys for repository operations
- Access to agenticplace repositories
- URL patterns for agenticplace services

### Professor-Codephreak URL Mapping

The URL tracking system can integrate with URL mapping systems:
- Track URL mappings and transformations
- Store mapping metadata
- Provide access history for mapping analysis

## Data Format

### Credential Metadata

```json
{
    "credential_id": "github_api_key",
    "credential_type": "api_key",
    "credential_hash": "a1b2c3d4e5f6...",
    "env_var": "MINDX_CRED_GITHUB_API_KEY",
    "created_at": "2026-01-17T19:30:00",
    "last_used": "2026-01-17T20:15:00",
    "use_count": 42,
    "metadata": {
        "provider": "github",
        "scope": "repo,user"
    }
}
```

### URL Access Record

```json
{
    "timestamp": "2026-01-17T19:30:00.123456",
    "url": "https://github.com/agenticplace/mindX",
    "ip_address": "192.168.1.100",
    "agent_id": "mindx_agint",
    "metadata": {
        "response_time": 0.234,
        "status_code": 200,
        "content_type": "text/html"
    }
}
```

### IP Access Record

```json
{
    "timestamp": "2026-01-17T19:30:00.123456",
    "ip_address": "10.0.0.155",
    "url": "http://10.0.0.155:18080",
    "agent_id": "startup_agent",
    "metadata": {
        "port": 18080,
        "protocol": "http",
        "service": "ollama"
    }
}
```

## Best Practices

1. **Credential Naming**: Use descriptive, consistent naming (e.g., `{provider}_{type}_{purpose}`)
2. **Metadata**: Include provider, scope, expiry, and other relevant information
3. **URL Tracking**: Log all external URL accesses for ML inference
4. **IP Tracking**: Track all IP access points, especially for services like Ollama
5. **Memory Integration**: All operations are automatically logged to memory system
6. **Security**: Never expose credential values in API responses or logs

## Future Enhancements

- Encryption at rest for credential values
- Credential rotation and expiry management
- URL/IP access pattern analysis
- Integration with external secret management services
- ML model training data export from access logs
