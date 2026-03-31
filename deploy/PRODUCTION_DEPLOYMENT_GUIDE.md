# mindX Production VPS Deployment Guide

**© Professor Codephreak** - [github.com/agenticplace](https://github.com/agenticplace), [github.com/cryptoagi](https://github.com/cryptoagi), [github.com/Professor-Codephreak](https://github.com/Professor-Codephreak)
**Resources:** [rage.pythai.net](https://rage.pythai.net)

## Overview

This guide provides comprehensive instructions for deploying mindX Augmented Intelligence Platform to a production VPS environment with dual-domain configuration, encrypted vault security, and AION autonomous agent integration.

## Architecture

### Production Domains
- **agenticplace.pythai.net** - Main mindX platform and agent exploration
- **aion.pythai.net** - AION autonomous agent interface

### Security Features
- AES-256 encrypted vault for sensitive data
- PBKDF2 key derivation with high iteration count
- Fresh cryptographic identities (compromised wallets replaced)
- Multi-layer rate limiting and DDoS protection
- SSL/TLS encryption with automatic renewal

### Core Components
- **mindX Platform** - Main Augmented Intelligence service
- **AION Agent** - Autonomous operations with chroot management
- **Backup Agent** - Git integration with immutable blockchain memories
- **Monitoring System** - Real-time performance and health tracking

## Prerequisites

### VPS Requirements
- **OS:** Ubuntu 22.04 LTS or newer
- **RAM:** Minimum 4GB (8GB recommended)
- **Storage:** Minimum 50GB SSD
- **CPU:** 2+ cores
- **Network:** Static IP with reverse DNS

### Domain Configuration
Before deployment, ensure DNS records are configured:

```bash
# A records pointing to your VPS IP
agenticplace.pythai.net.  IN  A  YOUR_VPS_IP
aion.pythai.net.          IN  A  YOUR_VPS_IP

# Optional: AAAA records for IPv6
agenticplace.pythai.net.  IN  AAAA  YOUR_VPS_IPv6
aion.pythai.net.          IN  AAAA  YOUR_VPS_IPv6
```

### Environment Variables
Set these environment variables before deployment:

```bash
export VAULT_PASSWORD="your_secure_vault_password_here"
export BACKUP_REPO="https://github.com/yourusername/mindx-backups.git"
export PRODUCTION_DOMAINS="agenticplace.pythai.net,aion.pythai.net"
```

## Deployment Steps

### 1. Transfer mindX to VPS

Transfer the mindX codebase to your VPS:

```bash
# From your local machine
scp -r /home/hacker/mindX root@YOUR_VPS_IP:/tmp/

# On VPS
mv /tmp/mindX /home/hacker/mindX
```

### 2. Run Production Setup

Execute the production deployment script:

```bash
chmod +x /home/hacker/mindX/deploy/production_vps_setup.sh
sudo VAULT_PASSWORD="$VAULT_PASSWORD" ./production_vps_setup.sh
```

The script will:
- Install all system dependencies
- Create `mindx` and `aion` users with proper permissions
- Set up PostgreSQL database with pgvector extension
- Configure Redis for caching
- Deploy mindX application with encrypted vault
- Install and configure AION autonomous agent
- Set up backup agent with git integration
- Configure Nginx reverse proxy with rate limiting
- Install SSL/TLS certificates via Let's Encrypt
- Configure firewall and security settings
- Set up monitoring and logging
- Start all production services

### 3. Verify Deployment

Check service status:

```bash
# Main services
sudo systemctl status mindx aion-agent nginx postgresql redis

# Monitoring services
sudo systemctl status mindx-monitor mindx-backup.timer

# View logs
sudo journalctl -u mindx.service -f
sudo journalctl -u aion-agent.service -f
```

### 4. Test Domains

Verify both domains are accessible:

```bash
# Test main platform
curl -I https://agenticplace.pythai.net/api/health

# Test AION interface
curl -I https://aion.pythai.net/status
```

## Configuration Files

### Main Service Environment

Located at `/home/mindx/mindX/.env.production`:

```bash
MINDX_ENVIRONMENT=production
DEBUG=false
VAULT_PASSWORD=your_secure_password
ENCRYPTION_ENABLED=true
AION_ENABLED=true
BACKUP_ENABLED=true
MONITORING_ENABLED=true
```

### Nginx Configuration

- **agenticplace.pythai.net**: `/etc/nginx/sites-available/agenticplace`
- **aion.pythai.net**: `/etc/nginx/sites-available/aion`

Both include security headers, rate limiting, and SSL/TLS termination.

### Systemd Services

- **mindx.service** - Main platform (port 8000)
- **aion-agent.service** - AION autonomous agent (port 8001)
- **mindx-monitor.service** - Real-time monitoring
- **mindx-backup.timer** - Automated backups every 4 hours

## Security Configuration

### Encrypted Vault System

The production deployment uses AES-256 encryption for all sensitive data:

```python
# Vault configuration
{
    "encryption_enabled": true,
    "key_derivation": "PBKDF2",
    "iterations": 100000,
    "backup_enabled": true
}
```

### Firewall Rules

UFW is configured with restrictive rules:

```bash
# Allowed ports
22/tcp   - SSH
80/tcp   - HTTP (redirects to HTTPS)
443/tcp  - HTTPS
8000/tcp - Internal (localhost only)
8001/tcp - Internal (localhost only)
```

### Rate Limiting

Nginx implements multiple rate limiting zones:

- **API endpoints**: 10 req/s with burst of 20
- **General access**: 30 req/s with burst of 50
- **AION interface**: 5 req/s with burst of 10 (more restrictive)

## AION Agent Configuration

### Exclusive Control

AION agent has exclusive control over `AION.sh` script:

```bash
# Only AION can execute
chmod 700 /home/aion/AION.sh
chown aion:aion /home/aion/AION.sh
```

### Chroot Management

AION can create and manage chroot environments:

```bash
# Available AION commands
./AION.sh aion_prime chroot-create --target /chroots/new --secure
./AION.sh aion_prime chroot-optimize --source /src --target /dst
./AION.sh aion_prime autonomous-action --verify
```

### System Admin Integration

AION works with systemadmin_agent for privileged operations:

```python
# AION has sudo access for system operations
# Configured in /etc/sudoers.d/aion-agent
```

## Backup System

### Git Integration

Backup agent automatically commits changes:

```bash
# Backup runs every 4 hours
systemctl status mindx-backup.timer

# Manual backup
sudo -u mindx python agents/backup_agent.py --backup-all
```

### Immutable Blockchain Memories

Backup agent integrates with multiple networks:

- **AION Network** - Primary blockchain storage
- **IPFS** - Distributed file storage
- **Arweave** - Permanent data storage
- **Ethereum** - Smart contract integration

## Monitoring and Maintenance

### Health Monitoring

Real-time monitoring includes:

- **CPU/Memory/Network** usage
- **Service health** checks
- **Database** performance
- **SSL certificate** expiration
- **Backup** success/failure

### Log Management

Logs are automatically rotated and compressed:

```bash
# View logs
tail -f /home/mindx/logs/mindx.log
tail -f /var/log/mindx/aion_operations.log

# Log rotation configured for 30-day retention
```

### Maintenance Tasks

```bash
# Update SSL certificates (automatic via certbot)
sudo certbot renew

# Update system packages
sudo apt update && sudo apt upgrade

# Restart services
sudo systemctl restart mindx aion-agent

# Check disk usage
df -h
du -sh /home/mindx/logs/
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo journalctl -u mindx.service -n 50
   sudo systemctl status mindx.service
   ```

2. **SSL certificate issues**
   ```bash
   sudo certbot certificates
   sudo certbot renew --dry-run
   ```

3. **Database connection problems**
   ```bash
   sudo -u postgres psql -c "\l"
   sudo systemctl status postgresql
   ```

4. **AION agent not responding**
   ```bash
   sudo journalctl -u aion-agent.service -n 50
   sudo systemctl restart aion-agent
   ```

### Performance Tuning

#### Database Optimization

```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
SELECT pg_reload_conf();
```

#### Redis Optimization

```bash
# Memory usage optimization
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### Nginx Optimization

```nginx
# Worker processes
worker_processes auto;
worker_connections 1024;

# Compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

## Security Hardening

### Additional Security Measures

1. **Fail2ban Configuration**
   ```bash
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

2. **SSH Key Authentication**
   ```bash
   # Disable password authentication
   echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
   systemctl reload ssh
   ```

3. **Automatic Updates**
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure unattended-upgrades
   ```

### Monitoring Security Events

```bash
# Authentication logs
sudo tail -f /var/log/auth.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Fail2ban logs
sudo tail -f /var/log/fail2ban.log
```

## Backup and Recovery

### Creating Backups

```bash
# Full system backup
sudo -u mindx python agents/backup_agent.py --backup-all --include-vault

# Database backup
sudo -u mindx pg_dump mindx > /home/mindx/backups/mindx_$(date +%Y%m%d_%H%M%S).sql

# Configuration backup
tar -czf /home/mindx/backups/config_$(date +%Y%m%d).tar.gz /etc/nginx/ /etc/systemd/system/mindx*
```

### Recovery Procedures

```bash
# Restore from backup
sudo -u mindx python agents/backup_agent.py --restore --backup-id BACKUP_ID

# Database restore
sudo -u postgres psql mindx < /home/mindx/backups/mindx_backup.sql

# Service restart after restore
sudo systemctl restart mindx aion-agent
```

## Professor Codephreak Attribution

This production deployment maintains full attribution to Professor Codephreak throughout:

- **Architecture**: Augmented Intelligence terminology
- **Documentation**: Professor Codephreak copyright notices
- **Code**: Attribution headers in all files
- **Organizations**: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
- **Resources**: rage.pythai.net

## Support and Updates

### Getting Help

1. **Check logs** for error messages
2. **Review documentation** for configuration issues
3. **Monitor resources** for performance problems
4. **Backup data** before making changes

### Updates

```bash
# Pull latest mindX updates
cd /home/mindx/mindX
sudo -u mindx git pull origin main

# Restart services
sudo systemctl restart mindx aion-agent

# Verify deployment
curl -I https://agenticplace.pythai.net/api/health
```

---

**© Professor Codephreak** - Augmented Intelligence Architecture
**Organizations**: [github.com/agenticplace](https://github.com/agenticplace), [github.com/cryptoagi](https://github.com/cryptoagi), [github.com/Professor-Codephreak](https://github.com/Professor-Codephreak)
**Resources**: [rage.pythai.net](https://rage.pythai.net)

*Production deployment guide for mindX Augmented Intelligence Platform with AION autonomous agent integration.*