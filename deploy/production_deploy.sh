#!/bin/bash
# mindX Production VPS Deployment Script
# Enhanced with security hardening, load balancing, and monitoring
# Version: 2.0.0-production

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MINDX_USER="mindx"
MINDX_HOME="/home/mindx"
MINDX_APP_DIR="${MINDX_HOME}/mindX"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
SYSTEMD_DIR="/etc/systemd/system"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/tmp/mindx_deploy_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Use a sudo-enabled user."
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."

    # Check Ubuntu version
    if ! grep -q "Ubuntu" /etc/os-release; then
        warn "This script is optimized for Ubuntu. Proceed with caution."
    fi

    # Check available memory (minimum 2GB)
    MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    MEMORY_GB=$((MEMORY_KB / 1024 / 1024))

    if [[ $MEMORY_GB -lt 2 ]]; then
        error "Minimum 2GB RAM required. Found: ${MEMORY_GB}GB"
    fi

    info "System requirements check passed (${MEMORY_GB}GB RAM)"
}

# Update system packages
update_system() {
    log "Updating system packages..."
    sudo apt-get update
    sudo apt-get upgrade -y

    # Install essential packages
    sudo apt-get install -y \
        curl \
        wget \
        git \
        nginx \
        python3 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        redis-server \
        ufw \
        fail2ban \
        logrotate \
        htop \
        netstat-nat \
        certbot \
        python3-certbot-nginx \
        supervisor \
        rsync \
        cron

    log "System packages updated and essential software installed"
}

# Configure firewall
configure_firewall() {
    log "Configuring UFW firewall..."

    # Reset UFW to defaults
    sudo ufw --force reset

    # Default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing

    # Allow SSH (be careful!)
    sudo ufw allow ssh

    # Allow HTTP and HTTPS
    sudo ufw allow 'Nginx Full'

    # Allow PostgreSQL only from localhost
    sudo ufw allow from 127.0.0.1 to any port 5432

    # Allow Redis only from localhost
    sudo ufw allow from 127.0.0.1 to any port 6379

    # Enable UFW
    sudo ufw --force enable

    log "Firewall configured with restrictive rules"
}

# Configure fail2ban
configure_fail2ban() {
    log "Configuring fail2ban..."

    sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[ssh]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/*error.log
findtime = 600
bantime = 3600
maxretry = 10
EOF

    sudo systemctl restart fail2ban
    sudo systemctl enable fail2ban

    log "fail2ban configured for SSH and nginx protection"
}

# Create mindX user
create_mindx_user() {
    log "Setting up mindX user..."

    if id "$MINDX_USER" &>/dev/null; then
        info "User $MINDX_USER already exists"
    else
        sudo useradd -m -s /bin/bash "$MINDX_USER"
        sudo usermod -aG sudo "$MINDX_USER"

        # Create SSH directory with proper permissions
        sudo mkdir -p "${MINDX_HOME}/.ssh"
        sudo chown -R "$MINDX_USER:$MINDX_USER" "${MINDX_HOME}/.ssh"
        sudo chmod 700 "${MINDX_HOME}/.ssh"

        log "User $MINDX_USER created with sudo privileges"
    fi

    # Create application directories
    sudo -u "$MINDX_USER" mkdir -p "${MINDX_HOME}/"{logs,data,backups,config}
    sudo -u "$MINDX_USER" mkdir -p "${MINDX_APP_DIR}"

    # Set up log directory with proper permissions
    sudo mkdir -p /var/log/mindx
    sudo chown "$MINDX_USER:$MINDX_USER" /var/log/mindx
}

# Configure PostgreSQL
configure_postgresql() {
    log "Configuring PostgreSQL..."

    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql

    # Create mindX database and user
    sudo -u postgres createdb mindx 2>/dev/null || info "Database 'mindx' already exists"

    # Set password for postgres user (generate random password)
    PG_PASSWORD=$(openssl rand -base64 32)
    sudo -u postgres psql -c "CREATE USER mindx_user WITH PASSWORD '$PG_PASSWORD';" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER mindx_user PASSWORD '$PG_PASSWORD';"

    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mindx TO mindx_user;"

    # Store database credentials securely
    sudo -u "$MINDX_USER" tee "${MINDX_HOME}/config/database.env" > /dev/null <<EOF
DATABASE_URL=postgresql://mindx_user:${PG_PASSWORD}@localhost:5432/mindx
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mindx
DATABASE_USER=mindx_user
DATABASE_PASSWORD=${PG_PASSWORD}
EOF

    sudo chmod 600 "${MINDX_HOME}/config/database.env"

    log "PostgreSQL configured with mindx database and user"
}

# Configure Redis
configure_redis() {
    log "Configuring Redis..."

    # Configure Redis for production
    sudo tee /etc/redis/redis.conf > /dev/null <<EOF
bind 127.0.0.1 ::1
port 6379
timeout 0
tcp-keepalive 300
tcp-backlog 511
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis
EOF

    sudo systemctl restart redis
    sudo systemctl enable redis

    log "Redis configured for production use"
}

# Deploy mindX application
deploy_mindx() {
    log "Deploying mindX application..."

    # Copy application files
    if [[ -d "$PROJECT_ROOT" ]]; then
        sudo -u "$MINDX_USER" rsync -av --exclude='.git' --exclude='__pycache__' \
            --exclude='*.pyc' --exclude='node_modules' \
            "$PROJECT_ROOT/" "$MINDX_APP_DIR/"
    else
        error "Source directory $PROJECT_ROOT not found"
    fi

    # Create Python virtual environment
    sudo -u "$MINDX_USER" python3 -m venv "${MINDX_APP_DIR}/venv"

    # Install Python dependencies
    sudo -u "$MINDX_USER" "${MINDX_APP_DIR}/venv/bin/pip" install --upgrade pip
    sudo -u "$MINDX_USER" "${MINDX_APP_DIR}/venv/bin/pip" install -r "${MINDX_APP_DIR}/requirements.txt"

    # Additional production packages
    sudo -u "$MINDX_USER" "${MINDX_APP_DIR}/venv/bin/pip" install \
        uvicorn[standard] \
        gunicorn \
        psycopg2-binary \
        redis \
        cryptography \
        asyncpg \
        aioredis

    log "mindX application deployed successfully"
}

# Configure production environment
configure_environment() {
    log "Configuring production environment..."

    # Generate secure production configuration
    sudo -u "$MINDX_USER" tee "${MINDX_APP_DIR}/.env.production" > /dev/null <<EOF
# mindX Production Configuration
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Environment
MINDX_ENVIRONMENT=production
MINDX_DEBUG=false

# Security
MINDX_SECRET_KEY=$(openssl rand -hex 32)
MINDX_SECURITY_PRODUCTION_MODE=true
MINDX_SECURITY_DEVELOPMENT_MODE=false
MINDX_SECURITY_ENCRYPTION_ENABLED=true

# API Configuration
MINDX_API_HOST=0.0.0.0
MINDX_API_PORT=8000
MINDX_API_WORKERS=4
MINDX_API_TIMEOUT=30

# Database (loaded from separate file)
MINDX_DATABASE_CONFIG_FILE=${MINDX_HOME}/config/database.env

# Redis
MINDX_REDIS_URL=redis://localhost:6379/0

# CORS (Update with your actual domains)
MINDX_CORS_ALLOWED_ORIGINS=https://agenticplace.pythai.net,https://www.agenticplace.pythai.net

# Rate Limiting
MINDX_RATE_LIMIT_ENABLED=true
MINDX_RATE_LIMIT_REQUESTS=100
MINDX_RATE_LIMIT_WINDOW=60

# Monitoring
MINDX_MONITORING_ENABLED=true
MINDX_LOGGING_LEVEL=INFO
MINDX_LOGGING_FILE=/var/log/mindx/mindx.log

# Performance
MINDX_PERFORMANCE_CONNECTION_POOL_SIZE=20
MINDX_PERFORMANCE_MAX_CONNECTIONS=100
MINDX_PERFORMANCE_TIMEOUT=30

# Backup
MINDX_BACKUP_ENABLED=true
MINDX_BACKUP_INTERVAL=daily
MINDX_BACKUP_RETENTION_DAYS=30

# Health Checks
MINDX_HEALTH_CHECK_ENABLED=true
MINDX_HEALTH_CHECK_INTERVAL=60
EOF

    sudo chmod 600 "${MINDX_APP_DIR}/.env.production"

    log "Production environment configuration created"
}

# Configure nginx
configure_nginx() {
    log "Configuring nginx..."

    # Remove default nginx site
    sudo rm -f "${NGINX_ENABLED}/default"

    # Create mindX nginx configuration
    sudo tee "${NGINX_AVAILABLE}/mindx" > /dev/null <<EOF
# mindX Production nginx Configuration
upstream mindx_backend {
    server 127.0.0.1:8000;
    # Add more backends for load balancing:
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;

    keepalive 32;
}

# Rate limiting
limit_req_zone \$binary_remote_addr zone=mindx_api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=mindx_static:10m rate=50r/s;

server {
    listen 80;
    server_name agenticplace.pythai.net www.agenticplace.pythai.net;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy strict-origin-when-cross-origin;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";

    # Logs
    access_log /var/log/nginx/mindx_access.log;
    error_log /var/log/nginx/mindx_error.log;

    # Static files
    location /static/ {
        alias ${MINDX_APP_DIR}/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        limit_req zone=mindx_static burst=100 nodelay;
    }

    # Health check endpoint (no rate limiting)
    location = /health {
        proxy_pass http://mindx_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Quick timeout for health checks
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=mindx_api burst=20 nodelay;

        proxy_pass http://mindx_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Main application
    location / {
        limit_req zone=mindx_api burst=50 nodelay;

        proxy_pass http://mindx_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Security
        proxy_hide_header X-Powered-By;
    }

    # Block access to sensitive files
    location ~ /\. {
        deny all;
    }

    location ~ \.(env|log|ini)$ {
        deny all;
    }
}
EOF

    # Enable the site
    sudo ln -sf "${NGINX_AVAILABLE}/mindx" "${NGINX_ENABLED}/mindx"

    # Test nginx configuration
    sudo nginx -t

    # Restart nginx
    sudo systemctl restart nginx
    sudo systemctl enable nginx

    log "nginx configured with rate limiting and security headers"
}

# Configure systemd service
configure_systemd() {
    log "Configuring systemd service..."

    # Main mindX service
    sudo tee "${SYSTEMD_DIR}/mindx.service" > /dev/null <<EOF
[Unit]
Description=mindX Autonomous AI System
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=${MINDX_USER}
Group=${MINDX_USER}
WorkingDirectory=${MINDX_APP_DIR}
Environment=PATH=${MINDX_APP_DIR}/venv/bin
EnvironmentFile=${MINDX_APP_DIR}/.env.production
ExecStart=${MINDX_APP_DIR}/venv/bin/uvicorn mindx_backend_service.main_service_production:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mindx

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${MINDX_HOME} /var/log/mindx /tmp
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
TasksMax=4096

[Install]
WantedBy=multi-user.target
EOF

    # Health monitoring service
    sudo tee "${SYSTEMD_DIR}/mindx-health.service" > /dev/null <<EOF
[Unit]
Description=mindX Health Monitor
After=mindx.service
BindsTo=mindx.service

[Service]
Type=exec
User=${MINDX_USER}
Group=${MINDX_USER}
WorkingDirectory=${MINDX_APP_DIR}
Environment=PATH=${MINDX_APP_DIR}/venv/bin
EnvironmentFile=${MINDX_APP_DIR}/.env.production
ExecStart=${MINDX_APP_DIR}/scripts/health_monitor.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Timer for health checks
    sudo tee "${SYSTEMD_DIR}/mindx-health.timer" > /dev/null <<EOF
[Unit]
Description=mindX Health Check Timer
Requires=mindx.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1min
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable services
    sudo systemctl enable mindx.service
    sudo systemctl enable mindx-health.timer

    log "systemd services configured with security restrictions"
}

# Configure backup system
configure_backup() {
    log "Configuring backup system..."

    # Create backup script
    sudo -u "$MINDX_USER" tee "${MINDX_HOME}/scripts/backup.sh" > /dev/null <<'EOF'
#!/bin/bash
# mindX Backup Script

set -euo pipefail

BACKUP_DIR="/home/mindx/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mindx_backup_${DATE}.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
pg_dump -h localhost -U mindx_user mindx > "${BACKUP_DIR}/database_${DATE}.sql"

# Application backup
tar -czf "$BACKUP_FILE" \
    --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    -C /home/mindx mindX/ config/

# Clean old backups (keep last 30 days)
find "$BACKUP_DIR" -name "mindx_backup_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "database_*.sql" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

    sudo chmod +x "${MINDX_HOME}/scripts/backup.sh"

    # Add to crontab
    (sudo -u "$MINDX_USER" crontab -l 2>/dev/null; echo "0 2 * * * ${MINDX_HOME}/scripts/backup.sh") | \
    sudo -u "$MINDX_USER" crontab -

    log "Daily backup system configured"
}

# Configure log rotation
configure_logging() {
    log "Configuring log rotation..."

    sudo tee "/etc/logrotate.d/mindx" > /dev/null <<EOF
/var/log/mindx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 mindx mindx
    postrotate
        systemctl reload mindx || true
    endscript
}

/var/log/nginx/mindx_*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    postrotate
        systemctl reload nginx || true
    endscript
}
EOF

    log "Log rotation configured"
}

# Create health monitoring script
create_health_monitor() {
    log "Creating health monitoring script..."

    sudo -u "$MINDX_USER" mkdir -p "${MINDX_APP_DIR}/scripts"

    sudo -u "$MINDX_USER" tee "${MINDX_APP_DIR}/scripts/health_monitor.py" > /dev/null <<'EOF'
#!/usr/bin/env python3
"""
mindX Health Monitor
Monitors system health and alerts on issues
"""

import asyncio
import aiohttp
import time
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mindx/health.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self):
        self.endpoint = "http://127.0.0.1:8000/health/detailed"
        self.check_interval = 60  # seconds
        self.alert_file = "/var/log/mindx/alerts.log"

    async def check_health(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.endpoint, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self.process_health_data(data)
                    else:
                        await self.alert(f"Health check failed with status: {response.status}")
        except Exception as e:
            await self.alert(f"Health check exception: {str(e)}")

    async def process_health_data(self, data):
        status = data.get("status", "unknown")

        if status != "healthy":
            issues = data.get("issues", [])
            await self.alert(f"System status: {status}, Issues: {', '.join(issues)}")

        # Check individual services
        services = data.get("services", {})
        for service, service_status in services.items():
            if service_status == "unavailable":
                await self.alert(f"Service {service} is unavailable")

    async def alert(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = f"{timestamp} - ALERT: {message}"

        logger.warning(alert_msg)

        # Write to alert file
        with open(self.alert_file, "a") as f:
            f.write(alert_msg + "\n")

    async def run_forever(self):
        logger.info("Health monitor started")

        while True:
            try:
                await self.check_health()
                await asyncio.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("Health monitor stopped")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = HealthMonitor()
    asyncio.run(monitor.run_forever())
EOF

    sudo chmod +x "${MINDX_APP_DIR}/scripts/health_monitor.py"

    log "Health monitoring script created"
}

# Install SSL certificate
install_ssl() {
    log "Installing SSL certificate..."

    # Only proceed if domain is configured
    if [[ $(hostname -f) != "localhost" ]] && [[ $(hostname -f) != "127.0.0.1" ]]; then
        sudo certbot --nginx -d "$(hostname -f)" --non-interactive --agree-tos --email admin@$(hostname -f)
        log "SSL certificate installed and configured"
    else
        warn "SSL certificate not installed - configure domain name first"
    fi
}

# Start services
start_services() {
    log "Starting mindX services..."

    # Start and enable services
    sudo systemctl start mindx.service
    sudo systemctl enable mindx.service

    # Start health monitoring
    sudo systemctl start mindx-health.timer

    # Check service status
    sleep 5

    if sudo systemctl is-active --quiet mindx.service; then
        log "mindX service started successfully"
    else
        error "Failed to start mindX service"
    fi
}

# Display deployment summary
deployment_summary() {
    log "Deployment Summary"
    echo "===================="
    echo "mindX Production Deployment Complete!"
    echo ""
    echo "Services:"
    echo "  - mindX API: http://$(hostname -i):80"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - nginx: Port 80/443"
    echo ""
    echo "Logs:"
    echo "  - Application: /var/log/mindx/mindx.log"
    echo "  - Health: /var/log/mindx/health.log"
    echo "  - nginx: /var/log/nginx/mindx_*.log"
    echo "  - Deployment: $LOG_FILE"
    echo ""
    echo "Management Commands:"
    echo "  - Status: sudo systemctl status mindx"
    echo "  - Restart: sudo systemctl restart mindx"
    echo "  - Logs: sudo journalctl -u mindx -f"
    echo "  - Health: curl http://localhost:8000/health"
    echo ""
    echo "Configuration Files:"
    echo "  - App Config: ${MINDX_APP_DIR}/.env.production"
    echo "  - nginx: ${NGINX_AVAILABLE}/mindx"
    echo "  - Systemd: ${SYSTEMD_DIR}/mindx.service"
    echo ""
    echo "Security:"
    echo "  - Firewall: UFW enabled"
    echo "  - fail2ban: Active protection"
    echo "  - SSL: $(if [[ -f /etc/letsencrypt/live/$(hostname -f)/cert.pem ]]; then echo "Configured"; else echo "Not configured"; fi)"
    echo ""
    echo "Next Steps:"
    echo "  1. Configure DNS to point to this server"
    echo "  2. Update CORS origins in .env.production"
    echo "  3. Set up monitoring dashboards"
    echo "  4. Configure API keys in encrypted vault"
    echo ""
}

# Main deployment function
main() {
    log "Starting mindX production deployment..."

    check_root
    check_requirements

    # Core system setup
    update_system
    configure_firewall
    configure_fail2ban

    # User and application setup
    create_mindx_user
    configure_postgresql
    configure_redis

    # Application deployment
    deploy_mindx
    configure_environment

    # Web server and services
    configure_nginx
    configure_systemd

    # Monitoring and maintenance
    configure_backup
    configure_logging
    create_health_monitor

    # SSL and startup
    install_ssl
    start_services

    deployment_summary

    log "mindX production deployment completed successfully!"
}

# Run main function
main "$@"