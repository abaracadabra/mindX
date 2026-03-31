# mindX Production Deployment Checklist

**© Professor Codephreak** - [rage.pythai.net](https://rage.pythai.net)
**Organizations**: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak

## Pre-Deployment Verification

### ✅ 1. VPS Requirements

**Hardware Requirements**
- [ ] VPS has minimum 4GB RAM (8GB recommended)
- [ ] VPS has minimum 50GB SSD storage
- [ ] VPS has 2+ CPU cores
- [ ] VPS has static IP address
- [ ] VPS has reverse DNS configured

**Operating System**
- [ ] Ubuntu 22.04 LTS or newer installed
- [ ] Root access available
- [ ] System packages are up to date

### ✅ 2. Domain Configuration

**DNS Records**
- [ ] `agenticplace.pythai.net` A record points to VPS IP
- [ ] `aion.pythai.net` A record points to VPS IP
- [ ] DNS propagation complete (check with `dig` or `nslookup`)
- [ ] Optional: AAAA records for IPv6 configured

**Domain Verification**
```bash
# Verify DNS resolution
dig agenticplace.pythai.net A
dig aion.pythai.net A
```

### ✅ 3. Security Preparation

**Vault Password**
- [ ] Strong vault password generated (32+ characters)
- [ ] Password stored securely (password manager)
- [ ] Environment variable `VAULT_PASSWORD` set

**SSH Access**
- [ ] SSH key pair generated
- [ ] Public key added to VPS authorized_keys
- [ ] SSH access verified with key authentication
- [ ] Root or sudo access confirmed

**Fresh Identities**
- [ ] Old compromised wallet files backed up
- [ ] New cryptographic identities will be generated
- [ ] Agent identity reset plan prepared

### ✅ 4. mindX Codebase Preparation

**Code Quality**
- [ ] All recent changes committed to version control
- [ ] Code passes local tests
- [ ] No debugging code or test data in production files
- [ ] All sensitive data removed from code

**Configuration Files**
- [ ] Environment templates prepared
- [ ] Database connection strings configured
- [ ] API keys and secrets prepared (will be vault-encrypted)
- [ ] AION agent configuration verified

**Dependencies**
- [ ] `requirements.txt` is up to date
- [ ] All Python dependencies are compatible
- [ ] No development-only dependencies in production requirements
- [ ] Database migration scripts ready

### ✅ 5. Backup Configuration

**Git Repository**
- [ ] Backup git repository created (if using git backups)
- [ ] Repository access configured
- [ ] `BACKUP_REPO` environment variable set
- [ ] Git credentials configured

**Blockchain Integration**
- [ ] AION network configuration verified
- [ ] IPFS node configuration prepared
- [ ] Arweave wallet configuration ready
- [ ] Ethereum network access configured

### ✅ 6. Environment Variables

**Required Variables**
```bash
export VAULT_PASSWORD="your_secure_vault_password_here"
export BACKUP_REPO="https://github.com/yourusername/mindx-backups.git"
export PRODUCTION_DOMAINS="agenticplace.pythai.net,aion.pythai.net"
```

**Optional Variables**
```bash
export POSTGRES_PASSWORD="custom_db_password"
export REDIS_PASSWORD="custom_redis_password"
export EMAIL_ADDRESS="admin@yourdomain.com"
export BACKUP_ENCRYPTION_KEY="backup_encryption_key"
```

### ✅ 7. External Services

**Email Configuration** (for SSL certificates)
- [ ] Valid email address for Let's Encrypt registration
- [ ] Email address can receive certificate expiration warnings

**Monitoring** (optional)
- [ ] External monitoring service configured
- [ ] Health check URLs prepared
- [ ] Alert notification channels set up

### ✅ 8. Network Security

**Firewall Planning**
- [ ] VPS firewall plan documented
- [ ] Required ports identified (22, 80, 443)
- [ ] Internal port restrictions planned
- [ ] DDoS protection strategy prepared

**SSL/TLS Certificates**
- [ ] Let's Encrypt rate limits understood
- [ ] Certificate installation plan prepared
- [ ] Auto-renewal strategy configured

## Deployment Execution Checklist

### ✅ 1. File Transfer

**Code Transfer**
```bash
# Transfer mindX codebase
scp -r /home/hacker/mindX root@VPS_IP:/tmp/
ssh root@VPS_IP "mv /tmp/mindX /home/hacker/"
```

- [ ] mindX codebase transferred successfully
- [ ] File permissions preserved
- [ ] All necessary files included

### ✅ 2. Environment Setup

**Environment Variables**
```bash
# Set variables on VPS
export VAULT_PASSWORD="your_password"
export BACKUP_REPO="your_repo_url"
export PRODUCTION_DOMAINS="agenticplace.pythai.net,aion.pythai.net"
```

- [ ] All environment variables set
- [ ] Variables verified with `echo $VARIABLE_NAME`
- [ ] No typos in domain names or URLs

### ✅ 3. Script Execution

**Deployment Script**
```bash
cd /home/hacker/mindX/deploy
chmod +x production_vps_setup.sh
sudo VAULT_PASSWORD="$VAULT_PASSWORD" ./production_vps_setup.sh
```

- [ ] Script has execute permissions
- [ ] Script runs without errors
- [ ] All installation steps complete
- [ ] No failed service starts

### ✅ 4. Service Verification

**System Services**
```bash
sudo systemctl status postgresql redis-server nginx
```

- [ ] PostgreSQL running and accessible
- [ ] Redis running and responding
- [ ] Nginx running and configured correctly

**mindX Services**
```bash
sudo systemctl status mindx aion-agent mindx-monitor
```

- [ ] Main mindX service running (port 8000)
- [ ] AION agent service running (port 8001)
- [ ] Monitoring service running
- [ ] No error messages in service status

### ✅ 5. Domain Accessibility

**HTTP/HTTPS Testing**
```bash
# Test both domains
curl -I https://agenticplace.pythai.net
curl -I https://aion.pythai.net
```

- [ ] agenticplace.pythai.net returns 200 OK
- [ ] aion.pythai.net returns 200 OK
- [ ] SSL certificates installed correctly
- [ ] HTTP redirects to HTTPS

### ✅ 6. API Functionality

**Health Checks**
```bash
# Test API endpoints
curl https://agenticplace.pythai.net/api/health
curl https://aion.pythai.net/status
```

- [ ] Main API health check passes
- [ ] AION status endpoint responds
- [ ] No authentication errors
- [ ] Response times reasonable (<2 seconds)

### ✅ 7. AION Agent Verification

**AION Functionality**
```bash
# Check AION logs
sudo journalctl -u aion-agent.service -n 20
```

- [ ] AION agent starts without errors
- [ ] AION.sh script has correct permissions
- [ ] AION can access systemadmin functions
- [ ] AION autonomy level set correctly

### ✅ 8. Backup System

**Backup Verification**
```bash
# Test backup system
sudo systemctl status mindx-backup.timer
sudo -u mindx python agents/backup_agent.py --test-backup
```

- [ ] Backup timer enabled and running
- [ ] Test backup completes successfully
- [ ] Git integration working (if configured)
- [ ] Blockchain storage accessible

### ✅ 9. Security Verification

**Firewall Status**
```bash
sudo ufw status
```

- [ ] UFW firewall is active
- [ ] Only necessary ports are open
- [ ] Internal services not exposed externally

**SSL Security**
```bash
# Test SSL configuration
openssl s_client -connect agenticplace.pythai.net:443 -servername agenticplace.pythai.net < /dev/null
```

- [ ] SSL certificate valid and trusted
- [ ] Certificate covers all domains
- [ ] Strong cipher suites enabled
- [ ] HSTS headers present

### ✅ 10. Monitoring and Logging

**Log Accessibility**
```bash
# Check log files
ls -la /home/mindx/logs/
ls -la /var/log/mindx/
```

- [ ] Log directories created with correct permissions
- [ ] Log files being written
- [ ] Log rotation configured
- [ ] No permission errors

**Monitoring Functionality**
- [ ] Monitoring service running
- [ ] System metrics being collected
- [ ] Health checks functioning
- [ ] Alert thresholds configured

## Post-Deployment Verification

### ✅ 1. 24-Hour Stability Test

**Service Stability**
- [ ] All services running for 24 hours without restart
- [ ] No memory leaks detected
- [ ] No unusual CPU usage
- [ ] No disk space issues

**Log Analysis**
- [ ] No recurring error patterns
- [ ] Request rates within expected range
- [ ] No authentication failures
- [ ] SSL certificate auto-renewal tested

### ✅ 2. Performance Testing

**Load Testing**
```bash
# Basic load test
ab -n 100 -c 10 https://agenticplace.pythai.net/api/health
```

- [ ] API responses under 2 seconds
- [ ] No 5xx server errors
- [ ] Rate limiting working correctly
- [ ] Server handles concurrent requests

**Resource Usage**
- [ ] Memory usage stable and reasonable
- [ ] CPU usage within normal range
- [ ] Disk I/O performance acceptable
- [ ] Network latency acceptable

### ✅ 3. Backup Verification

**Automated Backups**
- [ ] First scheduled backup completed successfully
- [ ] Backup files created with correct timestamps
- [ ] Git commits working (if configured)
- [ ] Blockchain storage confirmed

**Recovery Testing**
- [ ] Test restore procedure works
- [ ] Database backup/restore verified
- [ ] Configuration backup complete
- [ ] Recovery documentation updated

## Security Post-Deployment

### ✅ 1. Vulnerability Assessment

**System Security**
```bash
# Check for open ports
nmap -sS -T4 VPS_IP
```

- [ ] Only expected ports open (22, 80, 443)
- [ ] No unnecessary services running
- [ ] All software up to date
- [ ] Security patches applied

**Application Security**
- [ ] Vault encryption working
- [ ] Fresh cryptographic identities generated
- [ ] No sensitive data in logs
- [ ] API rate limiting functional

### ✅ 2. Monitoring Setup

**Security Monitoring**
- [ ] Failed login attempts tracked
- [ ] SSL certificate expiration monitoring
- [ ] Disk space monitoring
- [ ] Service health monitoring

**Alerting**
- [ ] Critical alerts configured
- [ ] Notification channels tested
- [ ] Escalation procedures documented
- [ ] Response team notified

## Final Checklist

### ✅ Documentation and Handoff

- [ ] Deployment documentation complete
- [ ] Administrative credentials documented securely
- [ ] Backup procedures documented
- [ ] Monitoring procedures documented
- [ ] Troubleshooting guide prepared
- [ ] Emergency contact information ready

### ✅ Professor Codephreak Attribution

- [ ] Copyright notices maintained in all files
- [ ] Augmented Intelligence terminology preserved
- [ ] Organization links functional
- [ ] rage.pythai.net resources accessible
- [ ] Attribution headers complete

### ✅ Production Sign-Off

- [ ] All checklist items completed
- [ ] System stability verified
- [ ] Performance benchmarks met
- [ ] Security requirements satisfied
- [ ] Backup/recovery tested
- [ ] Monitoring operational
- [ ] Documentation complete

## Emergency Procedures

### Critical Issues

**Service Down**
```bash
# Emergency restart procedure
sudo systemctl restart mindx aion-agent nginx
sudo journalctl -u mindx.service -n 50
```

**Database Issues**
```bash
# Database recovery
sudo systemctl restart postgresql
sudo -u postgres psql -c "SELECT version();"
```

**SSL Certificate Problems**
```bash
# Manual certificate renewal
sudo certbot renew --force-renewal
sudo nginx -t && sudo systemctl reload nginx
```

### Emergency Contacts

- **VPS Provider**: [Support contact information]
- **Domain Registrar**: [Support contact information]
- **Backup Repository**: [Access information]
- **Monitoring Service**: [Alert escalation]

---

**© Professor Codephreak** - Augmented Intelligence Production Deployment
**Organizations**: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
**Resources**: rage.pythai.net

*Complete pre-deployment checklist for mindX production environment with AION autonomous agent integration.*