# Production Deployment Guide

> **Note**: This is a **generic deployment template**. For the actual live production setup at
> mindx.pythai.net, see [DEPLOYMENT_MINDX_PYTHAI_NET.md](DEPLOYMENT_MINDX_PYTHAI_NET.md)
> which uses Apache2 (not nginx), BANKON Vault, pgvector, and Ollama qwen3:0.6b.

This guide covers the complete production deployment of mindX on a VPS with security hardening, monitoring, and backup systems.

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or newer (recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 50GB+ SSD storage
- **CPU**: 2+ cores, 4+ cores recommended
- **Network**: Static IP address recommended
- **Domain**: Optional but recommended for SSL

### Prerequisites Check

```bash
# Check Ubuntu version
lsb_release -a

# Check available resources
free -h
df -h
nproc
```

## Quick Production Deployment

### 1. One-Command Deployment

```bash
# Clone the repository
git clone https://github.com/cryptoagi/mindX.git
cd mindX

# Make deployment script executable
chmod +x deploy/production_deploy.sh

# Run production deployment (requires sudo access)
./deploy/production_deploy.sh
```

This script will automatically:
- ✅ Update system packages and install dependencies
- ✅ Configure firewall (UFW) with restrictive rules
- ✅ Set up fail2ban for intrusion prevention
- ✅ Create mindX user with proper permissions
- ✅ Install and configure PostgreSQL database
- ✅ Set up Redis for caching and sessions
- ✅ Deploy mindX application with virtual environment
- ✅ Configure nginx with rate limiting and security headers
- ✅ Set up systemd services with security restrictions
- ✅ Configure automated backups and log rotation
- ✅ Install SSL certificates (if domain configured)

## Manual Deployment Steps

If you prefer manual control or need to customize the deployment:

### 1. System Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install essential packages
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    postgresql postgresql-contrib \
    redis-server nginx \
    ufw fail2ban \
    git curl wget htop
```

### 2. Security Configuration

```bash
# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Configure fail2ban
sudo cp deploy/config/fail2ban-jail.local /etc/fail2ban/jail.local
sudo systemctl restart fail2ban
```

### 3. Database Setup

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create mindX database and user
sudo -u postgres createdb mindx
sudo -u postgres psql -c "CREATE USER mindx_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mindx TO mindx_user;"
```

### 4. Application Deployment

```bash
# Create mindX user
sudo useradd -m -s /bin/bash mindx
sudo usermod -aG sudo mindx

# Deploy application
sudo -u mindx mkdir -p /home/mindx/mindX
sudo -u mindx rsync -av ./ /home/mindx/mindX/

# Set up virtual environment
sudo -u mindx python3 -m venv /home/mindx/mindX/venv
sudo -u mindx /home/mindx/mindX/venv/bin/pip install -r /home/mindx/mindX/requirements.txt
```

### 5. Environment Configuration

```bash
# Copy production configuration
sudo -u mindx cp /home/mindx/mindX/.env.production.template /home/mindx/mindX/.env.production

# Edit configuration (update domains, credentials, etc.)
sudo -u mindx nano /home/mindx/mindX/.env.production
```

### 6. nginx Configuration

```bash
# Copy nginx configuration
sudo cp deploy/config/nginx-mindx.conf /etc/nginx/sites-available/mindx
sudo ln -s /etc/nginx/sites-available/mindx /etc/nginx/sites-enabled/

# Remove default nginx site
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Systemd Service

```bash
# Copy systemd service files
sudo cp deploy/config/mindx.service /etc/systemd/system/
sudo cp deploy/config/mindx-health.service /etc/systemd/system/
sudo cp deploy/config/mindx-health.timer /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable mindx.service
sudo systemctl enable mindx-health.timer

# Start services
sudo systemctl start mindx.service
sudo systemctl start mindx-health.timer
```

## Post-Deployment Configuration

### 1. API Keys Migration

Migrate your API keys to the encrypted vault:

```bash
# Run the migration script
sudo -u mindx /home/mindx/mindX/venv/bin/python scripts/migrate_to_encrypted_vault.py

# Store additional API keys
sudo -u mindx /home/mindx/mindX/venv/bin/python -c "
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager
vault = get_encrypted_vault_manager()
vault.store_api_key('openai', 'your-openai-key')
vault.store_api_key('anthropic', 'your-anthropic-key')
vault.store_api_key('gemini', 'your-gemini-key')
"
```

### 2. Domain Configuration

If you have a domain name:

```bash
# Update nginx configuration with your domain
sudo sed -i 's/agenticplace.pythai.net/your-domain.com/g' /etc/nginx/sites-available/mindx

# Install SSL certificate
sudo certbot --nginx -d your-domain.com

# Update CORS configuration
sudo -u mindx sed -i 's/https:\/\/agenticplace.pythai.net/https:\/\/your-domain.com/g' /home/mindx/mindX/.env.production

# Restart services
sudo systemctl restart mindx nginx
```

### 3. Database Initialization

```bash
# Run database migrations (if any)
sudo -u mindx /home/mindx/mindX/venv/bin/python scripts/init_database.py

# Verify database connection
sudo -u mindx /home/mindx/mindX/venv/bin/python -c "
import asyncpg
import asyncio
async def test_db():
    conn = await asyncpg.connect('postgresql://mindx_user:secure_password@localhost/mindx')
    result = await conn.fetchval('SELECT version()')
    print(f'Database: {result}')
    await conn.close()
asyncio.run(test_db())
"
```

## Verification and Testing

### 1. Service Status Check

```bash
# Check service status
sudo systemctl status mindx
sudo systemctl status mindx-health
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Check logs
sudo journalctl -u mindx -f
```

### 2. Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# External access (if domain configured)
curl https://your-domain.com/health
```

### 3. Performance Test

```bash
# Install hey for load testing
sudo apt-get install -y hey

# Basic load test
hey -n 100 -c 10 http://localhost:8000/health

# API endpoint test
hey -n 50 -c 5 -H "Content-Type: application/json" \
    -d '{"test":"data"}' \
    http://localhost:8000/api/test
```

### 4. Security Verification

```bash
# Check firewall status
sudo ufw status verbose

# Check fail2ban status
sudo fail2ban-client status

# Check SSL certificate (if configured)
sudo certbot certificates

# Verify encrypted vault
sudo -u mindx /home/mindx/mindX/venv/bin/python scripts/migrate_to_encrypted_vault.py --verify-only
```

## Monitoring and Maintenance

### 1. Log Files

```bash
# Application logs
tail -f /var/log/mindx/mindx.log

# Health monitor logs
tail -f /var/log/mindx/health.log

# nginx logs
tail -f /var/log/nginx/mindx_access.log
tail -f /var/log/nginx/mindx_error.log

# System logs
sudo journalctl -u mindx -f
```

### 2. Performance Monitoring

```bash
# System resources
htop
iotop
nethogs

# Database performance
sudo -u postgres psql mindx -c "SELECT * FROM pg_stat_activity;"

# Redis monitoring
redis-cli info stats
```

### 3. Backup Verification

```bash
# Check backup script
sudo -u mindx /home/mindx/scripts/backup.sh

# List backups
ls -la /home/mindx/backups/

# Verify backup cron job
sudo -u mindx crontab -l
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service status
sudo systemctl status mindx

# Check logs for errors
sudo journalctl -u mindx --no-pager

# Check configuration
sudo -u mindx /home/mindx/mindX/venv/bin/python -m py_compile /home/mindx/mindX/mindx_backend_service/main_service_production.py
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "SELECT version();"

# Check database user privileges
sudo -u postgres psql -c "\du mindx_user"
```

#### nginx Configuration Issues

```bash
# Test nginx configuration
sudo nginx -t

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log

# Reload nginx configuration
sudo systemctl reload nginx
```

#### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate (if expired)
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal
```

### Performance Issues

#### High Memory Usage

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Restart mindX service
sudo systemctl restart mindx

# Check for memory leaks
sudo -u mindx /home/mindx/mindX/venv/bin/python scripts/memory_analysis.py
```

#### High CPU Usage

```bash
# Check CPU usage
top
htop

# Check mindX processes
ps aux | grep mindx

# Analyze performance
sudo -u mindx /home/mindx/mindX/venv/bin/python scripts/performance_analysis.py
```

## Security Best Practices

### 1. Regular Updates

```bash
# Create update script
sudo tee /home/mindx/scripts/update_system.sh > /dev/null <<'EOF'
#!/bin/bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get autoremove -y
sudo -u mindx /home/mindx/mindX/venv/bin/pip install --upgrade -r /home/mindx/mindX/requirements.txt
sudo systemctl restart mindx
EOF

sudo chmod +x /home/mindx/scripts/update_system.sh

# Add to cron (weekly updates)
echo "0 2 * * 0 /home/mindx/scripts/update_system.sh" | sudo tee -a /etc/crontab
```

### 2. Security Monitoring

```bash
# Monitor failed login attempts
sudo tail -f /var/log/auth.log | grep "Failed password"

# Check fail2ban status
sudo fail2ban-client status ssh

# Monitor nginx access
sudo tail -f /var/log/nginx/mindx_access.log | grep -E "(40[0-9]|50[0-9])"
```

### 3. Backup Security

```bash
# Encrypt backups
sudo -u mindx tee /home/mindx/scripts/backup_encrypted.sh > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR="/home/mindx/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mindx_backup_${DATE}.tar.gz"

# Create encrypted backup
tar -czf - /home/mindx/mindX /home/mindx/config | \
gpg --symmetric --cipher-algo AES256 --compress-algo 2 \
    --output "${BACKUP_FILE}.gpg"

# Remove unencrypted backup
rm -f "$BACKUP_FILE"

echo "Encrypted backup created: ${BACKUP_FILE}.gpg"
EOF

sudo chmod +x /home/mindx/scripts/backup_encrypted.sh
```

## Scaling Considerations

### 1. Load Balancing

For high-traffic deployments, set up multiple mindX instances:

```bash
# Copy systemd service for additional instances
sudo cp /etc/systemd/system/mindx.service /etc/systemd/system/mindx-2.service
sudo cp /etc/systemd/system/mindx.service /etc/systemd/system/mindx-3.service

# Edit ports in additional services (8001, 8002)
sudo sed -i 's/--port 8000/--port 8001/g' /etc/systemd/system/mindx-2.service
sudo sed -i 's/--port 8000/--port 8002/g' /etc/systemd/system/mindx-3.service

# Update nginx upstream configuration
sudo nano /etc/nginx/sites-available/mindx
# Add: server 127.0.0.1:8001; and server 127.0.0.1:8002;
```

### 2. Database Scaling

For high-load scenarios:

```bash
# Enable PostgreSQL connection pooling
sudo apt-get install -y pgbouncer

# Configure pgbouncer
sudo nano /etc/pgbouncer/pgbouncer.ini
# Add mindX database configuration

# Update application to use pgbouncer
# DATABASE_URL=postgresql://mindx_user:password@localhost:6432/mindx
```

### 3. Caching Layer

```bash
# Configure Redis for session storage and caching
sudo nano /etc/redis/redis.conf
# Increase maxmemory and configure persistence

# Update application configuration
# MINDX_REDIS_URL=redis://localhost:6379/0
# MINDX_SESSION_STORAGE=redis
```

This completes the comprehensive production deployment guide for mindX. Follow these steps carefully and customize based on your specific requirements.