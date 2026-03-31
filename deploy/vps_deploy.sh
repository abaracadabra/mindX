#!/bin/bash
# mindX VPS Fresh Deployment Script
# Generated: 2026-03-31T13:56:05.826766

set -e

echo "[DEPLOY] Starting mindX fresh deployment..."

# Update system
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx git

# Create mindX user if not exists
if ! id "mindx" &>/dev/null; then
    sudo useradd -m -s /bin/bash mindx
    echo "[DEPLOY] Created mindx user"
fi

# Setup directories
sudo -u mindx mkdir -p /home/mindx/{logs,data,backups}
sudo -u mindx mkdir -p /home/mindx/mindX

# Clone fresh mindX (assuming git repo)
cd /home/mindx
if [ -d "mindX/.git" ]; then
    echo "[DEPLOY] Updating existing mindX repo..."
    sudo -u mindx git -C mindX pull origin main
else
    echo "[DEPLOY] Cloning fresh mindX repo..."
    # sudo -u mindx git clone <YOUR_MINDX_REPO_URL> mindX
fi

# Setup Python environment
sudo -u mindx python3 -m venv /home/mindx/mindX/venv
sudo -u mindx /home/mindx/mindX/venv/bin/pip install -r /home/mindx/mindX/requirements.txt

# Copy fresh environment files
sudo -u mindx cp /home/mindx/mindX/.env.new /home/mindx/mindX/.env
sudo -u mindx cp /home/mindx/mindX/data/identity/.wallet_keys.env.new /home/mindx/mindX/data/identity/.wallet_keys.env

# Set secure permissions
sudo chmod 600 /home/mindx/mindX/.env
sudo chmod 600 /home/mindx/mindX/data/identity/.wallet_keys.env

# Setup systemd service
sudo tee /etc/systemd/system/mindx.service > /dev/null <<EOF
[Unit]
Description=mindX Autonomous AI System
After=network.target

[Service]
Type=simple
User=mindx
WorkingDirectory=/home/mindx/mindX
Environment=PATH=/home/mindx/mindX/venv/bin
ExecStart=/home/mindx/mindX/venv/bin/python mindx_backend_service/main_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Setup nginx proxy
sudo tee /etc/nginx/sites-available/mindx > /dev/null <<EOF
server {
    listen 80;
    server_name agenticplace.pythai.net;

    location /explore-agents {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mindx /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Enable and start mindX service
sudo systemctl daemon-reload
sudo systemctl enable mindx
sudo systemctl start mindx

echo "[DEPLOY] mindX deployment complete!"
echo "[DEPLOY] Status: sudo systemctl status mindx"
echo "[DEPLOY] Logs: sudo journalctl -u mindx -f"
