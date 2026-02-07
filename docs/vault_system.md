# Vault System Documentation

## Overview

The Vault System provides persistent local storage for access credentials and tracks URL/IP access points for ML inference ingestion. The vault is located at `mindx_backend_service/vault/` and provides secure, encrypted storage for sensitive data.

## Architecture

### Directory Structure

```
mindx_backend_service/vault/
├── agents/              # Agent private keys
│   └── .agent_keys.env
├── postgresql/          # Database credentials
│   ├── config.json
│   └── .credentials.env
├── secrets/             # General secrets
├── credentials/         # Access credentials (API keys, tokens)
│   ├── .credentials.env
│   └── {credential_id}.json
├── sessions/            # User login sessions (wallet auth); one file per session
│   └── {session_id}.json
├── user_folders/        # One folder per wallet (0x...); access only with valid session
│   └── 0x{40 hex}/      # Per-wallet key-value store (*.json)
└── access_log/          # URL and IP access tracking
    ├── url_access_{YYYYMMDD}.jsonl
    ├── ip_access_{YYYYMMDD}.jsonl
    ├── url_index.json
    └── ip_index.json
```

### Security

- **File Permissions**: All vault files are created with restrictive permissions (owner read/write only)
- **Environment Variables**: Sensitive values stored in `.env` files, not in JSON
- **Hashing**: Credentials are hashed for verification
- **No Value Exposure**: API endpoints never return actual credential values

## Features

### 1. Access Credentials Storage

Store and retrieve access credentials (API keys, OAuth tokens, etc.) securely.

#### Store Credential

```python
from mindx_backend_service.vault_manager import get_vault_manager

vault_manager = get_vault_manager()

vault_manager.store_access_credential(
    credential_id="github_api_key",
    credential_type="api_key",
    credential_value="ghp_xxxxxxxxxxxx",
    metadata={
        "provider": "github",
        "scope": "repo,user",
        "expires_at": "2026-12-31T23:59:59"
    }
)
```

#### Retrieve Credential

```python
credential_value = vault_manager.get_access_credential(
    credential_id="github_api_key",
    mark_used=True  # Update last_used timestamp
)
```

#### List Credentials

```python
credentials = vault_manager.list_access_credentials()
# Returns metadata only (no actual values)
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
