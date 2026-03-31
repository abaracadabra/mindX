#!/bin/bash
# mindX Production VPS Setup Script
# © Professor Codephreak - github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
# rage.pythai.net - Production deployment for mindX with AION integration
#
# This script sets up a production VPS environment for mindX with:
# - Dual domain configuration (agenticplace.pythai.net + aion.pythai.net)
# - Enhanced security with encrypted vault
# - AION autonomous agent deployment
# - Backup agent with git integration
# - Production monitoring and logging
# - SSL/TLS with Let's Encrypt

set -euo pipefail

# Configuration
MINDX_USER="mindx"
AION_USER="aion"
MINDX_HOME="/home/$MINDX_USER"
AION_HOME="/home/$AION_USER"
MINDX_DIR="$MINDX_HOME/mindX"
BACKUP_REPO="${BACKUP_REPO:-}" # Set via environment if using git backup
PRODUCTION_DOMAINS="${PRODUCTION_DOMAINS:-agenticplace.pythai.net,aion.pythai.net}"
VAULT_PASSWORD="${VAULT_PASSWORD:-}" # Set via environment for vault encryption

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."

    apt-get update
    apt-get install -y \
        python3-pip python3-venv python3-dev \
        nginx certbot python3-certbot-nginx \
        git curl wget unzip \
        postgresql postgresql-contrib \
        redis-server \
        htop iotop nethogs \
        fail2ban ufw \
        build-essential \
        supervisor \
        rsync

    # Install Docker for containerized components
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl enable docker
        systemctl start docker
        log_success "Docker installed"
    fi

    # Install Node.js for frontend components
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
    apt-get install -y nodejs

    log_success "System dependencies installed"
}

setup_users() {
    log_info "Setting up system users..."

    # Create mindX user
    if ! id "$MINDX_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$MINDX_USER"
        usermod -aG docker "$MINDX_USER"
        log_success "Created mindX user"
    fi

    # Create AION user with restricted privileges
    if ! id "$AION_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$AION_USER"
        usermod -aG docker "$AION_USER"
        # AION gets sudo access for system operations
        echo "$AION_USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/aion-agent
        log_success "Created AION user with elevated privileges"
    fi

    # Setup directory structure
    sudo -u "$MINDX_USER" mkdir -p "$MINDX_HOME"/{logs,data,backups,vault}
    sudo -u "$AION_USER" mkdir -p "$AION_HOME"/{logs,chroots,backups}

    # Set proper permissions
    chmod 700 "$MINDX_HOME/vault"
    chmod 700 "$AION_HOME"
    chown -R "$MINDX_USER:$MINDX_USER" "$MINDX_HOME"
    chown -R "$AION_USER:$AION_USER" "$AION_HOME"

    log_success "User setup complete"
}

setup_database() {
    log_info "Setting up PostgreSQL database..."

    # Start PostgreSQL
    systemctl enable postgresql
    systemctl start postgresql

    # Create mindX database and user
    sudo -u postgres psql -c "CREATE USER mindx WITH PASSWORD 'mindx_prod_$(openssl rand -hex 16)';"
    sudo -u postgres psql -c "CREATE DATABASE mindx OWNER mindx;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mindx TO mindx;"

    # Install pgvector extension
    sudo -u postgres psql -d mindx -c "CREATE EXTENSION IF NOT EXISTS vector;"

    log_success "PostgreSQL setup complete"
}

setup_redis() {
    log_info "Setting up Redis..."

    systemctl enable redis-server
    systemctl start redis-server

    # Configure Redis for production
    sed -i 's/# maxmemory <bytes>/maxmemory 1gb/' /etc/redis/redis.conf
    sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

    systemctl restart redis-server
    log_success "Redis setup complete"
}

deploy_mindx() {
    log_info "Deploying mindX application..."

    cd "$MINDX_HOME"

    # Clone or copy mindX
    if [ -d "mindX/.git" ]; then
        log_info "Updating existing mindX repository..."
        sudo -u "$MINDX_USER" git -C mindX pull origin main
    else
        log_info "Setting up mindX from local files..."
        cp -r /home/hacker/mindX ./
        chown -R "$MINDX_USER:$MINDX_USER" mindX
    fi

    # Setup Python environment
    sudo -u "$MINDX_USER" python3 -m venv "$MINDX_DIR/venv"

    # Install Python dependencies
    if [ -f "$MINDX_DIR/requirements.txt" ]; then
        sudo -u "$MINDX_USER" "$MINDX_DIR/venv/bin/pip" install --upgrade pip
        sudo -u "$MINDX_USER" "$MINDX_DIR/venv/bin/pip" install -r "$MINDX_DIR/requirements.txt"
    fi

    # Additional production dependencies
    sudo -u "$MINDX_USER" "$MINDX_DIR/venv/bin/pip" install \
        gunicorn uvicorn[standard] \
        psycopg2-binary redis \
        cryptography

    log_success "mindX application deployed"
}

setup_encrypted_vault() {
    log_info "Setting up encrypted vault system..."

    if [ -z "$VAULT_PASSWORD" ]; then
        log_warn "VAULT_PASSWORD not set, generating random password"
        VAULT_PASSWORD=$(openssl rand -base64 32)
        log_warn "Generated vault password: $VAULT_PASSWORD"
        log_warn "IMPORTANT: Save this password securely!"
    fi

    # Create vault configuration
    sudo -u "$MINDX_USER" tee "$MINDX_DIR/vault_config.json" > /dev/null <<EOF
{
    "vault_path": "/home/mindx/vault",
    "encryption_enabled": true,
    "key_derivation": "PBKDF2",
    "backup_enabled": true,
    "backup_path": "/home/mindx/backups/vault"
}
EOF

    # Initialize encrypted vault
    sudo -u "$MINDX_USER" python3 -c "
import sys
sys.path.append('$MINDX_DIR')
from mindx_backend_service.encrypted_vault_manager import EncryptedVaultManager
vault = EncryptedVaultManager('$MINDX_HOME/vault', '$VAULT_PASSWORD')
vault.initialize_vault()
print('Encrypted vault initialized successfully')
"

    chmod 600 "$MINDX_DIR/vault_config.json"
    log_success "Encrypted vault setup complete"
}

setup_aion_agent() {
    log_info "Setting up AION autonomous agent..."

    # Copy AION agent files
    cp "$MINDX_DIR/agents/aion_agent.py" "$AION_HOME/"
    cp "$MINDX_DIR/agents/systemadmin_agent.py" "$AION_HOME/"
    cp "$MINDX_DIR/AION.sh" "$AION_HOME/"
    chown -R "$AION_USER:$AION_USER" "$AION_HOME"

    # Make AION.sh executable only by AION user
    chmod 700 "$AION_HOME/AION.sh"

    # Create AION service
    tee /etc/systemd/system/aion-agent.service > /dev/null <<EOF
[Unit]
Description=AION Autonomous Agent
After=network.target mindx.service

[Service]
Type=simple
User=$AION_USER
WorkingDirectory=$AION_HOME
Environment=PATH=$MINDX_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$MINDX_DIR:$AION_HOME
ExecStart=$MINDX_DIR/venv/bin/python aion_agent.py --production
Restart=always
RestartSec=15
TimeoutStopSec=30

# Security settings
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false
ReadWritePaths=$AION_HOME $MINDX_HOME /var/log/mindx

[Install]
WantedBy=multi-user.target
EOF

    # Create AION log directory
    mkdir -p /var/log/mindx
    chown "$AION_USER:$AION_USER" /var/log/mindx

    log_success "AION agent setup complete"
}

setup_backup_agent() {
    log_info "Setting up backup agent..."

    # Create backup service
    tee /etc/systemd/system/mindx-backup.service > /dev/null <<EOF
[Unit]
Description=mindX Backup Agent
After=network.target

[Service]
Type=oneshot
User=$MINDX_USER
WorkingDirectory=$MINDX_DIR
Environment=PATH=$MINDX_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$MINDX_DIR
ExecStart=$MINDX_DIR/venv/bin/python agents/backup_agent.py --backup-all
EOF

    # Create backup timer (runs every 4 hours)
    tee /etc/systemd/system/mindx-backup.timer > /dev/null <<EOF
[Unit]
Description=Run mindX backup every 4 hours
Requires=mindx-backup.service

[Timer]
OnCalendar=*-*-* 00,04,08,12,16,20:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable backup timer
    systemctl enable mindx-backup.timer
    systemctl start mindx-backup.timer

    log_success "Backup agent setup complete"
}

setup_nginx() {
    log_info "Setting up Nginx reverse proxy..."

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Create agenticplace.pythai.net configuration
    tee /etc/nginx/sites-available/agenticplace > /dev/null <<'EOF'
server {
    listen 80;
    server_name agenticplace.pythai.net;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;

    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Explorer interface
    location /explore-agents {
        limit_req zone=general burst=50 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /home/mindx/mindX/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Default location
    location / {
        limit_req zone=general burst=50 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

    # Create aion.pythai.net configuration
    tee /etc/nginx/sites-available/aion > /dev/null <<'EOF'
server {
    listen 80;
    server_name aion.pythai.net;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # AION-specific rate limiting (more restrictive)
    limit_req_zone $binary_remote_addr zone=aion:10m rate=5r/s;

    # AION agent interface
    location / {
        limit_req zone=aion burst=10 nodelay;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # AION-specific security
        proxy_set_header X-AION-Request "true";
        proxy_timeout 120s;
        proxy_read_timeout 120s;
    }

    # AION status endpoint
    location /status {
        proxy_pass http://127.0.0.1:8001/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        access_log off;
    }
}
EOF

    # Enable sites
    ln -sf /etc/nginx/sites-available/agenticplace /etc/nginx/sites-enabled/
    ln -sf /etc/nginx/sites-available/aion /etc/nginx/sites-enabled/

    # Test configuration
    nginx -t
    systemctl reload nginx

    log_success "Nginx configuration complete"
}

setup_ssl() {
    log_info "Setting up SSL/TLS certificates..."

    # Install certificates for both domains
    IFS=',' read -ra DOMAINS <<< "$PRODUCTION_DOMAINS"

    for domain in "${DOMAINS[@]}"; do
        domain=$(echo "$domain" | xargs) # trim whitespace
        log_info "Obtaining SSL certificate for $domain"

        certbot --nginx -d "$domain" --non-interactive --agree-tos \
            --email "admin@$domain" --redirect
    done

    # Setup auto-renewal
    systemctl enable certbot.timer
    systemctl start certbot.timer

    log_success "SSL/TLS setup complete"
}

setup_firewall() {
    log_info "Setting up firewall..."

    # Configure UFW
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH, HTTP, HTTPS
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Allow internal services
    ufw allow from 127.0.0.1 to any port 8000
    ufw allow from 127.0.0.1 to any port 8001

    ufw --force enable

    log_success "Firewall configured"
}

setup_monitoring() {
    log_info "Setting up monitoring and logging..."

    # Create monitoring service
    tee /etc/systemd/system/mindx-monitor.service > /dev/null <<EOF
[Unit]
Description=mindX Production Monitor
After=network.target

[Service]
Type=simple
User=$MINDX_USER
WorkingDirectory=$MINDX_DIR
Environment=PATH=$MINDX_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$MINDX_DIR
ExecStart=$MINDX_DIR/venv/bin/python scripts/analyze_monitoring_data.py --production
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Setup log rotation
    tee /etc/logrotate.d/mindx > /dev/null <<EOF
/home/mindx/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    su mindx mindx
}

/var/log/mindx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    su aion aion
}
EOF

    log_success "Monitoring setup complete"
}

setup_main_service() {
    log_info "Setting up main mindX service..."

    # Create main service configuration
    tee /etc/systemd/system/mindx.service > /dev/null <<EOF
[Unit]
Description=mindX Augmented Intelligence Platform
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=$MINDX_USER
WorkingDirectory=$MINDX_DIR
Environment=PATH=$MINDX_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$MINDX_DIR
Environment=MINDX_ENVIRONMENT=production
Environment=VAULT_PASSWORD=$VAULT_PASSWORD
ExecStart=$MINDX_DIR/venv/bin/gunicorn mindx_backend_service.main_service_production:app -b 0.0.0.0:8000 -w 4 --timeout 60 --keep-alive 5
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
TimeoutStopSec=30

# Security
PrivateTmp=true
NoNewPrivileges=true
ProtectKernelTunables=true
ProtectControlGroups=true
ProtectKernelModules=true

[Install]
WantedBy=multi-user.target
EOF

    log_success "Main service configuration complete"
}

setup_production_environment() {
    log_info "Setting up production environment..."

    # Create production environment file
    sudo -u "$MINDX_USER" tee "$MINDX_DIR/.env.production" > /dev/null <<EOF
# mindX Production Environment Configuration
# © Professor Codephreak - rage.pythai.net

MINDX_ENVIRONMENT=production
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://mindx:mindx_prod_password@localhost/mindx
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SECRET_KEY=$(openssl rand -base64 64)
VAULT_PASSWORD=$VAULT_PASSWORD
ENCRYPTION_ENABLED=true

# API Configuration
API_RATE_LIMIT=100
API_TIMEOUT=60

# AION Configuration
AION_ENABLED=true
AION_PORT=8001
AION_LOG_LEVEL=INFO

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_INTERVAL=14400  # 4 hours
GIT_BACKUP_ENABLED=true
BLOCKCHAIN_BACKUP_ENABLED=true

# Monitoring Configuration
MONITORING_ENABLED=true
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# Professor Codephreak Attribution
AUTHOR="Professor Codephreak"
ORGANIZATIONS="github.com/agenticplace,github.com/cryptoagi,github.com/Professor-Codephreak"
RESOURCES="rage.pythai.net"
EOF

    chmod 600 "$MINDX_DIR/.env.production"

    # Link to main .env
    sudo -u "$MINDX_USER" ln -sf .env.production "$MINDX_DIR/.env"

    log_success "Production environment configured"
}

start_services() {
    log_info "Starting all services..."

    # Reload systemd
    systemctl daemon-reload

    # Enable and start services in order
    systemctl enable postgresql redis-server nginx
    systemctl enable mindx.service mindx-monitor.service aion-agent.service

    # Start database services first
    systemctl start postgresql redis-server

    # Start main application
    systemctl start mindx.service
    sleep 5

    # Start supporting services
    systemctl start mindx-monitor.service aion-agent.service

    # Restart nginx to ensure proper proxy
    systemctl restart nginx

    log_success "All services started"
}

print_status() {
    echo ""
    log_success "mindX Production VPS Setup Complete!"
    echo ""
    echo "=== Service Status ==="
    systemctl status mindx.service --no-pager -l
    echo ""
    systemctl status aion-agent.service --no-pager -l
    echo ""
    echo "=== Domain Access ==="
    echo "AgenticPlace: https://agenticplace.pythai.net"
    echo "AION Agent:   https://aion.pythai.net"
    echo ""
    echo "=== Useful Commands ==="
    echo "View mindX logs:  sudo journalctl -u mindx.service -f"
    echo "View AION logs:   sudo journalctl -u aion-agent.service -f"
    echo "Service status:   sudo systemctl status mindx aion-agent"
    echo "Restart services: sudo systemctl restart mindx aion-agent"
    echo ""
    echo "=== Security Notes ==="
    echo "Vault password: $VAULT_PASSWORD"
    echo "Save this password securely!"
    echo ""
    echo "=== Professor Codephreak Production Deployment ==="
    echo "© Professor Codephreak - rage.pythai.net"
    echo "Organizations: github.com/agenticplace, github.com/cryptoagi"
    echo "Architecture: Augmented Intelligence Platform"
    echo ""
}

main() {
    log_info "Starting mindX Production VPS Setup..."
    log_info "© Professor Codephreak - rage.pythai.net"

    check_root
    install_dependencies
    setup_users
    setup_database
    setup_redis
    deploy_mindx
    setup_encrypted_vault
    setup_aion_agent
    setup_backup_agent
    setup_nginx
    setup_firewall
    setup_monitoring
    setup_main_service
    setup_production_environment

    # Skip SSL setup if certificates exist
    if [ ! -f "/etc/letsencrypt/live/agenticplace.pythai.net/fullchain.pem" ]; then
        setup_ssl
    else
        log_info "SSL certificates already exist, skipping setup"
    fi

    start_services
    print_status
}

# Run main function
main "$@"