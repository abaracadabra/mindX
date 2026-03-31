# Security Configuration Guide

This guide covers the comprehensive security configuration for mindX production deployments, including encrypted vault management, access control, and security monitoring.

## Overview

mindX implements multiple layers of security:

- **🔐 Encrypted Vault**: AES-256 encryption for sensitive data
- **🛡️ Authentication & Authorization**: Multi-tier access control
- **🚫 Rate Limiting**: Advanced rate limiting algorithms
- **🔍 Input Validation**: Comprehensive request validation
- **🌐 Network Security**: CORS, headers, and transport security
- **📊 Security Monitoring**: Real-time threat detection

## Encrypted Vault Configuration

### 1. Initial Setup

The encrypted vault automatically initializes on first run:

```python
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager

# Initialize vault (creates encryption keys automatically)
vault = get_encrypted_vault_manager()

# Store API keys securely
vault.store_api_key("openai", "sk-your-openai-key")
vault.store_api_key("anthropic", "claude-your-anthropic-key")
vault.store_api_key("gemini", "your-gemini-key")

# Store wallet private keys
vault.store_wallet_key(
    agent_id="mastermind_agent",
    private_key="0x1234567890abcdef...",
    public_address="0x742d35Cc6d244a9e3d5C5fF60b..."
)
```

### 2. Vault Security Features

```bash
# Vault location (restricted permissions)
/home/mindx/mindX/mindx_backend_service/vault_encrypted/

# Key files (owner read/write only)
.salt          # Key derivation salt
.master.key    # Master encryption key
api_keys/      # Encrypted API keys
wallet_keys/   # Encrypted wallet keys
```

### 3. Migration from Plaintext

```bash
# Migrate existing plaintext secrets
cd /home/mindx/mindX
./venv/bin/python scripts/migrate_to_encrypted_vault.py

# Verify migration
./venv/bin/python scripts/migrate_to_encrypted_vault.py --verify-only
```

### 4. Key Rotation (Emergency)

```python
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager

vault = get_encrypted_vault_manager()

# Rotate all encryption keys (emergency use only)
success = vault.rotate_encryption_keys()
if success:
    print("✅ Encryption keys rotated successfully")
else:
    print("❌ Key rotation failed")
```

## Authentication & Authorization

### 1. Wallet-Based Authentication

mindX uses Ethereum wallet signatures for authentication:

```python
# User registration with signature
POST /users/register-with-signature
{
    "wallet_address": "0x742d35Cc6d244a9e3d5C5fF60b...",
    "signature": "0x1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b",
    "message": "mindX login request at 2026-03-31T14:30:00Z",
    "metadata": {"app": "mindX", "version": "2.0.0"}
}
```

### 2. Session Management

Sessions are managed through the encrypted vault:

```python
# Session validation middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Check for session token
    token = request.headers.get("X-Session-Token")

    if requires_auth(request.url.path):
        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing session token"}
            )

        # Validate with vault
        vault = get_vault_manager()
        session = vault.get_user_session(token)

        if not session:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid session"}
            )

    response = await call_next(request)
    return response
```

### 3. Access Control Levels

```python
# Admin-only endpoints
@app.post("/admin/system/shutdown")
async def shutdown_system(admin_wallet: str = Depends(require_admin_access)):
    # Only admin wallets can access
    pass

# User-specific resources
@app.get("/user/vault/keys")
async def get_user_vault(wallet: str = Depends(require_valid_session)):
    # Users can only access their own vault data
    pass

# Public endpoints (with rate limiting)
@app.get("/health")
async def health_check():
    # Public access but rate limited
    pass
```

### 4. Admin Configuration

```bash
# Set admin wallet addresses in environment
MINDX_SECURITY_ADMIN_ADDRESSES="0x1234...,0x5678...,0x9abc..."

# Configure API keys for service-to-service auth
MINDX_SECURITY_API_KEYS="api_key_1,api_key_2"
```

## Rate Limiting Configuration

### 1. Rate Limiting Algorithms

Configure in `/data/config/rate_limits.json`:

```json
{
  "api_endpoints": {
    "max_requests": 50,
    "window_seconds": 60,
    "algorithm": "sliding_window",
    "burst_allowance": 75
  },
  "public_read": {
    "max_requests": 200,
    "window_seconds": 60,
    "algorithm": "token_bucket",
    "burst_allowance": 300
  },
  "admin_operations": {
    "max_requests": 500,
    "window_seconds": 60,
    "algorithm": "adaptive",
    "adaptive_factor": 2.0
  }
}
```

### 2. Client Reputation System

```python
# Automatic reputation adjustment
class ClientReputation:
    def update_reputation(self, client_id: str, success: bool, response_time: float):
        if success and response_time < 1.0:
            # Reward fast, successful requests
            self.increase_reputation(client_id, 0.01)
        elif not success:
            # Penalize failures
            self.decrease_reputation(client_id, 0.02)
```

### 3. Whitelist Configuration

```python
# IP whitelist for trusted sources
RATE_LIMIT_WHITELIST = [
    "127.0.0.1",           # Localhost
    "10.0.0.0/8",          # Internal networks
    "172.16.0.0/12",       # Docker networks
    "192.168.0.0/16"       # Private networks
]
```

## CORS and Network Security

### 1. Production CORS Configuration

```python
# Strict CORS for production
CORS_CONFIG = {
    "allow_origins": [
        "https://agenticplace.pythai.net",
        "https://www.agenticplace.pythai.net",
        "https://mindx.yourdomain.com"
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": [
        "Content-Type",
        "Authorization",
        "X-Session-Token",
        "X-API-Key"
    ]
}
```

### 2. Security Headers

nginx automatically adds these security headers:

```nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy strict-origin-when-cross-origin;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'";
```

### 3. TLS Configuration

```bash
# SSL certificate installation (automatic with deployment)
sudo certbot --nginx -d yourdomain.com

# Verify TLS configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check SSL rating
curl -s https://api.ssllabs.com/api/v3/analyze?host=yourdomain.com
```

## Input Validation & Sanitization

### 1. Pydantic Models

All API inputs use validated Pydantic models:

```python
class UserRegisterPayload(BaseModel):
    wallet_address: str
    metadata: Optional[Dict[str, Any]] = None

    @validator('wallet_address')
    def wallet_address_validation(cls, v):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid Ethereum address')
        return v.lower()

class DirectivePayload(BaseModel):
    directive: str
    max_cycles: Optional[int] = 8

    @validator('directive')
    def directive_validation(cls, v):
        if len(v) > 10000:
            raise ValueError('Directive too long')
        # HTML/Script injection prevention
        if '<script>' in v.lower() or 'javascript:' in v.lower():
            raise ValueError('Invalid directive content')
        return v.strip()
```

### 2. SQL Injection Prevention

```python
# Using parameterized queries with asyncpg
async def get_user_data(wallet_address: str):
    # Safe parameterized query
    query = "SELECT * FROM users WHERE wallet_address = $1"

    async with get_db_connection() as conn:
        return await conn.fetch(query, wallet_address)

# Never use string formatting for queries
# ❌ DANGEROUS:
# query = f"SELECT * FROM users WHERE wallet = '{wallet}'"
```

### 3. File Upload Security

```python
# Secure file upload handling
ALLOWED_EXTENSIONS = {'.txt', '.json', '.csv', '.log'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file_upload(file: UploadFile):
    # Check extension
    if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(400, "File type not allowed")

    # Check size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")

    # Scan content for malicious patterns
    content = await file.read()
    if b'<script>' in content.lower() or b'javascript:' in content.lower():
        raise HTTPException(400, "Malicious content detected")

    return content
```

## Security Monitoring

### 1. Real-Time Monitoring

```python
# Security event monitoring
class SecurityMonitor:
    def __init__(self):
        self.failed_attempts = defaultdict(int)
        self.suspicious_ips = set()

    def log_failed_auth(self, ip_address: str, reason: str):
        self.failed_attempts[ip_address] += 1

        if self.failed_attempts[ip_address] > 5:
            self.suspicious_ips.add(ip_address)
            self.alert_admin(f"Suspicious activity from {ip_address}")

    def alert_admin(self, message: str):
        logger.critical(f"SECURITY ALERT: {message}")
        # Send notification to admin
```

### 2. Log Analysis

```bash
# Monitor authentication failures
tail -f /var/log/mindx/mindx.log | grep "Authentication failed"

# Monitor rate limiting
tail -f /var/log/nginx/mindx_error.log | grep "limiting requests"

# Monitor suspicious patterns
tail -f /var/log/mindx/mindx.log | grep -E "(SQL|script|javascript|<script)"
```

### 3. Automated Alerting

```bash
# Create alerting script
sudo tee /home/mindx/scripts/security_alerts.sh > /dev/null <<'EOF'
#!/bin/bash

# Check for failed authentication attempts
FAILED_AUTH=$(tail -100 /var/log/mindx/mindx.log | grep -c "Authentication failed")
if [ "$FAILED_AUTH" -gt 10 ]; then
    echo "High number of failed authentication attempts: $FAILED_AUTH" | \
    mail -s "mindX Security Alert" admin@yourdomain.com
fi

# Check for rate limiting
RATE_LIMITED=$(tail -100 /var/log/nginx/mindx_error.log | grep -c "limiting requests")
if [ "$RATE_LIMITED" -gt 50 ]; then
    echo "High rate limiting activity: $RATE_LIMITED requests blocked" | \
    mail -s "mindX Rate Limiting Alert" admin@yourdomain.com
fi
EOF

chmod +x /home/mindx/scripts/security_alerts.sh

# Add to cron (run every 5 minutes)
echo "*/5 * * * * /home/mindx/scripts/security_alerts.sh" | crontab -
```

## Security Hardening Checklist

### 1. System Level

- ✅ UFW firewall enabled with restrictive rules
- ✅ fail2ban configured for SSH and web protection
- ✅ Automatic security updates enabled
- ✅ SSH key-based authentication (disable password auth)
- ✅ Non-root user for application
- ✅ Secure file permissions (600/700)

### 2. Application Level

- ✅ Encrypted vault for sensitive data
- ✅ Strong input validation and sanitization
- ✅ SQL injection prevention
- ✅ XSS protection headers
- ✅ CSRF protection
- ✅ Rate limiting enabled
- ✅ Session management with expiration

### 3. Network Level

- ✅ TLS/SSL certificates installed
- ✅ CORS properly configured
- ✅ Security headers enabled
- ✅ Rate limiting at nginx level
- ✅ DDoS protection (via nginx)
- ✅ IP whitelisting for admin functions

### 4. Monitoring Level

- ✅ Security event logging
- ✅ Failed authentication monitoring
- ✅ Rate limiting alerts
- ✅ File integrity monitoring
- ✅ Regular security audits

## Security Audit Commands

### 1. Manual Security Check

```bash
# Check for exposed secrets
grep -r "password\|secret\|key" /home/mindx/mindX --exclude-dir=venv | grep -v ".git"

# Check file permissions
find /home/mindx/mindX -type f -perm /o+rwx

# Check for SUID files
find /home/mindx/mindX -perm -4000

# Verify vault encryption
sudo -u mindx /home/mindx/mindX/venv/bin/python -c "
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager
vault = get_encrypted_vault_manager()
providers = vault.list_api_providers()
agents = vault.list_wallet_agents()
print(f'Encrypted API providers: {len(providers)}')
print(f'Encrypted wallet agents: {len(agents)}')
"
```

### 2. Automated Security Scan

```bash
# Create security audit script
sudo tee /home/mindx/scripts/security_audit.py > /dev/null <<'EOF'
#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

def security_audit():
    results = {
        "vault_status": check_vault_encryption(),
        "file_permissions": check_file_permissions(),
        "service_status": check_service_security(),
        "network_security": check_network_config()
    }

    print(json.dumps(results, indent=2))

def check_vault_encryption():
    # Check if vault files are encrypted
    vault_dir = Path("/home/mindx/mindX/mindx_backend_service/vault_encrypted")
    return {
        "vault_exists": vault_dir.exists(),
        "api_keys_encrypted": (vault_dir / "api_keys" / "keys.enc").exists(),
        "wallet_keys_encrypted": (vault_dir / "wallet_keys" / "keys.enc").exists()
    }

def check_file_permissions():
    # Check critical file permissions
    critical_files = [
        "/home/mindx/mindX/.env.production",
        "/home/mindx/mindX/mindx_backend_service/vault_encrypted/.master.key"
    ]

    results = {}
    for file_path in critical_files:
        if Path(file_path).exists():
            stat = subprocess.run(['stat', '-c', '%a', file_path],
                                capture_output=True, text=True)
            results[file_path] = stat.stdout.strip()

    return results

if __name__ == "__main__":
    security_audit()
EOF

chmod +x /home/mindx/scripts/security_audit.py

# Run security audit
sudo -u mindx /home/mindx/scripts/security_audit.py
```

## Incident Response

### 1. Security Incident Procedure

If you detect a security incident:

```bash
# 1. Immediately isolate the system
sudo systemctl stop mindx

# 2. Block suspicious IP addresses
sudo ufw deny from <suspicious_ip>

# 3. Rotate encryption keys (if compromised)
sudo -u mindx /home/mindx/mindX/venv/bin/python -c "
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager
vault = get_encrypted_vault_manager()
vault.rotate_encryption_keys()
"

# 4. Change admin passwords/keys
# Update admin wallet addresses
# Regenerate API keys

# 5. Analyze logs
grep "SECURITY" /var/log/mindx/mindx.log
tail -1000 /var/log/auth.log | grep "Failed"

# 6. Restart with new configuration
sudo systemctl start mindx
```

### 2. Recovery Checklist

- [ ] System isolated and threat contained
- [ ] Encryption keys rotated
- [ ] Admin credentials changed
- [ ] Logs analyzed and preserved
- [ ] Vulnerabilities patched
- [ ] Monitoring enhanced
- [ ] Incident documented
- [ ] System restored and tested

This comprehensive security configuration ensures mindX operates with production-grade security across all layers of the system.