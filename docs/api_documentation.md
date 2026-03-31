# mindX API Documentation

This document provides comprehensive API documentation for the mindX production system, including authentication, endpoints, and usage examples.

## Base URL

```
Production: https://agenticplace.pythai.net
Development: http://localhost:8000
```

## Authentication

mindX uses wallet-based authentication with session tokens.

### Wallet Signature Authentication

```http
POST /users/register-with-signature
Content-Type: application/json

{
  "wallet_address": "0x742d35Cc6d244a9e3d5C5fF60b...",
  "signature": "0x1b2c3d4e5f6a7b8c9d0e1f2a3b4c...",
  "message": "mindX login request at 2026-03-31T14:30:00Z",
  "metadata": {"app": "mindX", "version": "2.0.0"}
}
```

**Response:**
```json
{
  "success": true,
  "session_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_at": "2026-04-01T14:30:00Z",
  "wallet_address": "0x742d35Cc6d244a9e3d5C5fF60b..."
}
```

### Session Validation

Include the session token in requests:

```http
GET /api/protected-endpoint
X-Session-Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Core API Endpoints

### Health & Status

#### GET /health
Basic health check endpoint.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-31T14:30:00Z"
}
```

#### GET /health/detailed
Comprehensive system health information.

```http
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-31T14:30:00Z",
  "version": "2.0.0-production",
  "services": {
    "command_handler": "available",
    "memory_agent": "available",
    "vault_manager": "available"
  }
}
```

### Agent Management

#### POST /agents
Create a new agent (requires authentication).

```http
POST /agents
Content-Type: application/json
X-Session-Token: <session_token>

{
  "agent_type": "simple_coder",
  "agent_id": "my_agent_001",
  "config": {
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": "my_agent_001",
  "agent_type": "simple_coder",
  "owner_wallet": "0x742d35Cc6d244a9e3d5C5fF60b...",
  "created_at": "2026-03-31T14:30:00Z"
}
```

#### GET /agents
List all registered agents.

```http
GET /agents
```

**Response:**
```json
{
  "success": true,
  "agents": [
    {
      "agent_id": "mastermind_prime",
      "agent_type": "mastermind_agent",
      "status": "active",
      "ethereum_address": "0x0a56d74eDaD0839E7F9278fc9A3907aB600969f7",
      "capabilities": [
        {
          "name": "Strategic Planning",
          "category": "reasoning",
          "icon": "brain"
        }
      ]
    }
  ]
}
```

#### DELETE /agents/{agent_id}
Delete an agent (requires authentication).

```http
DELETE /agents/my_agent_001
X-Session-Token: <session_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Agent my_agent_001 deleted successfully"
}
```

### Agent Commands

#### POST /commands/evolve
Evolve mindX codebase (requires authentication).

```http
POST /commands/evolve
Content-Type: application/json
X-Session-Token: <session_token>

{
  "directive": "Optimize database queries for better performance",
  "max_cycles": 5,
  "autonomous_mode": false
}
```

**Response:**
```json
{
  "success": true,
  "evolution_id": "evo_123456",
  "status": "initiated",
  "cycles_planned": 5,
  "estimated_duration": "30 minutes"
}
```

#### POST /commands/deploy
Deploy a new agent (requires authentication).

```http
POST /commands/deploy
Content-Type: application/json
X-Session-Token: <session_token>

{
  "directive": "Deploy a sentiment analysis agent for social media monitoring",
  "max_cycles": 3
}
```

#### POST /commands/introspect
Generate a new persona (requires authentication).

```http
POST /commands/introspect
Content-Type: application/json
X-Session-Token: <session_token>

{
  "directive": "Create a persona specialized in financial analysis",
  "max_cycles": 2
}
```

### Coordinator Operations

#### POST /coordinator/query
Query the Coordinator agent (requires authentication).

```http
POST /coordinator/query
Content-Type: application/json
X-Session-Token: <session_token>

{
  "query": "What is the current system performance status?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "System performance is optimal. CPU usage at 45%, memory usage at 60%. All agents responding normally.",
  "metadata": {
    "response_time": 1.2,
    "agent_id": "coordinator_agent_main"
  }
}
```

#### POST /coordinator/analyze
Trigger system analysis (requires authentication).

```http
POST /coordinator/analyze
Content-Type: application/json
X-Session-Token: <session_token>

{
  "context": "Weekly performance review"
}
```

### Registry Operations

#### GET /registry/agents
Show agent registry.

```http
GET /registry/agents
```

**Response:**
```json
{
  "success": true,
  "registry": {
    "total_agents": 12,
    "active_agents": 10,
    "registered_agents": {
      "mastermind_prime": {
        "agent_type": "mastermind_agent",
        "ethereum_address": "0x0a56d74eDaD0839E7F9278fc9A3907aB600969f7",
        "status": "active",
        "last_seen": "2026-03-31T14:29:45Z"
      }
    }
  }
}
```

#### GET /registry/tools
Show tool registry.

```http
GET /registry/tools
```

**Response:**
```json
{
  "success": true,
  "tools": {
    "total_tools": 17,
    "registered_tools": {
      "github_agent_tool": {
        "version": "1.0.0",
        "status": "active",
        "capabilities": ["backup", "sync", "version_control"]
      }
    }
  }
}
```

### Vault Operations

#### GET /vault/user/keys
List keys in authenticated user's vault folder.

```http
GET /vault/user/keys
X-Session-Token: <session_token>
```

**Response:**
```json
{
  "keys": ["api_config", "personal_notes", "agent_settings"],
  "wallet_address": "0x742d35Cc6d244a9e3d5C5fF60b..."
}
```

#### GET /vault/user/keys/{key}
Get value for a key in authenticated user's vault folder.

```http
GET /vault/user/keys/api_config
X-Session-Token: <session_token>
```

**Response:**
```json
{
  "key": "api_config",
  "value": {"openai_model": "gpt-4", "temperature": 0.7},
  "wallet_address": "0x742d35Cc6d244a9e3d5C5fF60b..."
}
```

#### PUT /vault/user/keys/{key}
Set value for a key in authenticated user's vault folder.

```http
PUT /vault/user/keys/api_config
Content-Type: application/json
X-Session-Token: <session_token>

{
  "openai_model": "gpt-4-turbo",
  "temperature": 0.5
}
```

### Session Management

#### GET /users/session/validate
Validate session token.

```http
GET /users/session/validate
X-Session-Token: <session_token>
```

**Response:**
```json
{
  "wallet_address": "0x742d35Cc6d244a9e3d5C5fF60b...",
  "expires_at": "2026-04-01T14:30:00Z"
}
```

#### POST /users/logout
Invalidate session token.

```http
POST /users/logout
X-Session-Token: <session_token>
```

**Response:**
```json
{
  "logged_out": true
}
```

## mindX Control Interface API

### GET /api/mindx/diagnostics
Get system diagnostics for the control interface.

```http
GET /api/mindx/diagnostics
```

**Response:**
```json
{
  "timestamp": 1711900800,
  "server_ip": "10.0.0.155",
  "public_ip": "203.0.113.1",
  "latency": "< 1ms",
  "bandwidth": "1 Gbps",
  "cpu_usage": "15%",
  "memory_usage": "34%",
  "disk_usage": "58%",
  "connections": 12,
  "mindx_status": "active",
  "agent_count": 12,
  "fresh_deployment": true
}
```

### POST /api/mindx/resources
Update resource allocation settings.

```http
POST /api/mindx/resources
Content-Type: application/json

{
  "resource": "cpu",
  "value": 75
}
```

**Response:**
```json
{
  "success": true,
  "resource": "cpu",
  "value": 75,
  "message": "Resource allocation updated: cpu = 75"
}
```

### GET /api/mindx/status
Get comprehensive mindX system status.

```http
GET /api/mindx/status
```

**Response:**
```json
{
  "system": "mindX Autonomous AI",
  "version": "2.0-fresh",
  "status": "active",
  "deployment_type": "fresh_security_refresh",
  "agents": {
    "ceo": "0x90B794AB9de19ED81dCA87d7e6543Fb21C30E093",
    "mastermind": "0x0a56d74eDaD0839E7F9278fc9A3907aB600969f7",
    "coordinator": "0x295927d4FacdaFAf7eC3A7E7B5f116Ce733bB3A3"
  },
  "security": {
    "fresh_deployment": true,
    "wallet_rotation": "2026-03-31 14:30:00",
    "api_keys_refreshed": true
  },
  "uptime": "2d 4h 15m",
  "last_updated": 1711900800
}
```

## Error Handling

All API endpoints return consistent error responses:

### Standard Error Format

```json
{
  "error": "Authentication failed",
  "status_code": 401,
  "path": "/agents",
  "timestamp": "2026-03-31T14:30:00Z"
}
```

### Common HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request format or parameters
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Rate Limiting Headers

Rate-limited responses include headers:

```http
HTTP/1.1 429 Too Many Requests
X-Rate-Limit-Remaining: 0
X-Rate-Limit-Reset: 1711900860
Retry-After: 60

{
  "error": "Rate limit exceeded",
  "message": "Maximum 100 requests per 60 seconds",
  "retry_after": 60
}
```

## SDK Examples

### Python SDK Usage

```python
import aiohttp
import asyncio

class MindXClient:
    def __init__(self, base_url, session_token=None):
        self.base_url = base_url
        self.session_token = session_token

    async def authenticate(self, wallet_address, signature, message):
        async with aiohttp.ClientSession() as session:
            payload = {
                "wallet_address": wallet_address,
                "signature": signature,
                "message": message
            }
            async with session.post(
                f"{self.base_url}/users/register-with-signature",
                json=payload
            ) as response:
                data = await response.json()
                self.session_token = data["session_token"]
                return data

    async def create_agent(self, agent_type, agent_id, config):
        headers = {"X-Session-Token": self.session_token}
        payload = {
            "agent_type": agent_type,
            "agent_id": agent_id,
            "config": config
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/agents",
                json=payload,
                headers=headers
            ) as response:
                return await response.json()

    async def query_coordinator(self, query):
        headers = {"X-Session-Token": self.session_token}
        payload = {"query": query}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/coordinator/query",
                json=payload,
                headers=headers
            ) as response:
                return await response.json()

# Usage example
async def main():
    client = MindXClient("https://agenticplace.pythai.net")

    # Authenticate
    auth_result = await client.authenticate(
        wallet_address="0x742d35Cc6d244a9e3d5C5fF60b...",
        signature="0x1b2c3d4e5f6a7b8c9d0e1f2a3b4c...",
        message="mindX login request at 2026-03-31T14:30:00Z"
    )

    # Create agent
    agent_result = await client.create_agent(
        agent_type="simple_coder",
        agent_id="my_coding_agent",
        config={"model": "gpt-4", "temperature": 0.7}
    )

    # Query coordinator
    query_result = await client.query_coordinator(
        "What is the current system status?"
    )

    print(f"Agent created: {agent_result}")
    print(f"Coordinator response: {query_result}")

asyncio.run(main())
```

### JavaScript/TypeScript SDK

```typescript
class MindXClient {
    private baseUrl: string;
    private sessionToken?: string;

    constructor(baseUrl: string, sessionToken?: string) {
        this.baseUrl = baseUrl;
        this.sessionToken = sessionToken;
    }

    async authenticate(walletAddress: string, signature: string, message: string) {
        const response = await fetch(`${this.baseUrl}/users/register-with-signature`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wallet_address: walletAddress,
                signature,
                message
            })
        });

        const data = await response.json();
        this.sessionToken = data.session_token;
        return data;
    }

    async createAgent(agentType: string, agentId: string, config: any) {
        const response = await fetch(`${this.baseUrl}/agents`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-Token': this.sessionToken!
            },
            body: JSON.stringify({
                agent_type: agentType,
                agent_id: agentId,
                config
            })
        });

        return await response.json();
    }

    async getSystemHealth() {
        const response = await fetch(`${this.baseUrl}/health/detailed`);
        return await response.json();
    }
}

// Usage
const client = new MindXClient('https://agenticplace.pythai.net');

// Authenticate and create agent
client.authenticate(walletAddress, signature, message)
    .then(() => client.createAgent('simple_coder', 'my_agent', {}))
    .then(result => console.log('Agent created:', result));
```

## WebSocket API (Future)

mindX will support WebSocket connections for real-time updates:

```javascript
// WebSocket connection (planned)
const ws = new WebSocket('wss://agenticplace.pythai.net/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'agent_update') {
        console.log('Agent status update:', data.payload);
    }
};

// Subscribe to agent updates
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'agent_updates',
    session_token: sessionToken
}));
```

This comprehensive API documentation covers all public endpoints and provides examples for integrating with the mindX system.