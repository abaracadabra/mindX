#!/usr/bin/env python3
"""
Fresh mindX Deployment Script
Complete security refresh for compromised systems
"""
import os
import secrets
import json
from pathlib import Path
from datetime import datetime
from eth_account import Account

# Enable wallet features
Account.enable_unaudited_hdwallet_features()

class FreshDeployment:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "deploy" / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.new_keys_file = self.project_root / "data" / "identity" / ".wallet_keys.env.new"
        self.security_log = self.project_root / "deploy" / "security_refresh.log"

    def log_security_action(self, action: str):
        """Log security actions for audit trail"""
        timestamp = datetime.now().isoformat()
        with open(self.security_log, 'a') as f:
            f.write(f"{timestamp}: {action}\n")
        print(f"[SECURITY] {action}")

    def backup_compromised_data(self):
        """Backup compromised data for investigation"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup compromised wallet file
        old_wallet_file = self.project_root / "data" / "identity" / ".wallet_keys.env"
        if old_wallet_file.exists():
            backup_wallet = self.backup_dir / "compromised_wallet_keys.env"
            backup_wallet.write_text(old_wallet_file.read_text())
            self.log_security_action(f"Backed up compromised wallets to {backup_wallet}")

        # Backup main env file
        old_env = self.project_root / ".env"
        if old_env.exists():
            backup_env = self.backup_dir / "compromised_main.env"
            backup_env.write_text(old_env.read_text())
            self.log_security_action(f"Backed up compromised .env to {backup_env}")

    def generate_fresh_agent_wallets(self) -> dict:
        """Generate completely new wallet private keys for all agents"""
        agent_ids = [
            "GUARDIAN_AGENT_MAIN",
            "COORDINATOR_AGENT_MAIN",
            "MASTERMIND_PRIME",
            "MINDX_AGINT",
            "AUTOMINDX_AGENT_MAIN",
            "SEA_FOR_MASTERMIND",
            "BLUEPRINT_AGENT_MINDX_V2",
            "CEO_AGENT_MAIN",
            "INFERENCE_AGENT_MAIN",
            "MEMORY_AGENT_MAIN",
            "VALIDATOR_AGENT_MAIN",
            "SYSTEM_STATE_TRACKER"
        ]

        fresh_wallets = {}
        wallet_env_content = "# Fresh mindX Agent Wallets - Generated " + datetime.now().isoformat() + "\n"
        wallet_env_content += "# SECURITY NOTICE: Keep this file secure and never commit to git\n\n"

        for agent_id in agent_ids:
            # Generate cryptographically secure wallet
            account = Account.create(secrets.token_hex(32))
            private_key = account.key.hex()
            public_address = account.address

            fresh_wallets[agent_id] = {
                "private_key": private_key,
                "public_address": public_address,
                "created": datetime.now().isoformat()
            }

            # Add to env file content
            wallet_env_content += f"MINDX_WALLET_PK_{agent_id}={private_key}\n"

            self.log_security_action(f"Generated fresh wallet for {agent_id}: {public_address}")

        # Write new secure wallet file
        self.new_keys_file.parent.mkdir(parents=True, exist_ok=True)
        self.new_keys_file.write_text(wallet_env_content)

        # Set restrictive permissions
        if os.name != 'nt':
            os.chmod(self.new_keys_file, 0o600)

        self.log_security_action(f"Wrote {len(fresh_wallets)} fresh wallets to {self.new_keys_file}")
        return fresh_wallets

    def generate_fresh_env_config(self):
        """Generate fresh .env with new API keys and secure defaults"""
        env_content = f"""# Fresh mindX Environment Configuration - Generated {datetime.now().isoformat()}
# SECURITY NOTICE: Replace all API keys with fresh ones

# --- API Keys (REPLACE WITH FRESH KEYS) ---
# Google Gemini API Key - GET NEW KEY FROM: https://aistudio.google.com/app/apikey
GEMINI_API_KEY="REPLACE_WITH_FRESH_GEMINI_KEY"

# Groq API Key - GET NEW KEY FROM: https://console.groq.com/keys
GROQ_API_KEY="REPLACE_WITH_FRESH_GROQ_KEY"

# OpenAI API Key (Optional)
OPENAI_API_KEY="REPLACE_WITH_FRESH_OPENAI_KEY"

# Anthropic API Key (Optional)
ANTHROPIC_API_KEY="REPLACE_WITH_FRESH_ANTHROPIC_KEY"

# --- Security Configuration ---
MINDX_SECURITY_FRESH_DEPLOYMENT="true"
MINDX_SECURITY_DEPLOYMENT_ID="{secrets.token_hex(16)}"
MINDX_SECURITY_KEY_ROTATION_DATE="{datetime.now().isoformat()}"

# --- LLM Configuration ---
MINDX_LLM_DEFAULT_PROVIDER="gemini"
MINDX_LLM_GEMINI_DEFAULT_MODEL="gemini-1.5-pro-latest"

# --- Logging Configuration ---
MINDX_LOGGING_LEVEL="INFO"
MINDX_LOGGING_CONSOLE_ENABLED="true"
MINDX_LOGGING_FILE_ENABLED="true"
MINDX_LOGGING_FILE_DIRECTORY="data/logs"
MINDX_LOGGING_FILE_NAME="mindx_runtime.log"
MINDX_LOGGING_FILE_LEVEL="DEBUG"
MINDX_LOGGING_FILE_ROTATE_WHEN="midnight"
MINDX_LOGGING_FILE_ROTATE_INTERVAL="1"
MINDX_LOGGING_FILE_ROTATE_BACKUP_COUNT="7"

# --- Agent Specific Configurations ---
MINDX_COORDINATOR_AUTONOMOUS_IMPROVEMENT_ENABLED="false"
MINDX_COORDINATOR_AUTONOMOUS_IMPROVEMENT_INTERVAL_SECONDS="36"
MINDX_COORDINATOR_MAX_CONCURRENT_SIA_TASKS="1"
MINDX_COORDINATOR_SIA_CLI_TIMEOUT_SECONDS="300"
MINDX_COORDINATOR_REQUIRE_HUMAN_APPROVAL_FOR_CRITICAL="true"

# Mastermind Agent
MINDX_MASTERMIND_AGENT_AUTONOMOUS_LOOP_ENABLED="false"
MINDX_MASTERMIND_AGENT_TOOLS_REGISTRY_PATH="data/config/official_tools_registry.json"

# BDI Agent Defaults
MINDX_BDI_ENABLE_SUBGOAL_DECOMPOSITION="true"
MINDX_BDI_PLAN_MONITORING_LLM_CHECK_ENABLED="false"

# --- Monitoring Configuration ---
MINDX_MONITORING_RESOURCE_ENABLED="true"
MINDX_MONITORING_RESOURCE_INTERVAL="15"
MINDX_MONITORING_RESOURCE_MAX_CPU_PERCENT="90.0"
MINDX_MONITORING_RESOURCE_MAX_MEMORY_PERCENT="90.0"

MINDX_MONITORING_PERFORMANCE_ENABLED="true"
MINDX_MONITORING_PERFORMANCE_SAVE_PERIODICALLY="true"
MINDX_MONITORING_PERFORMANCE_PERIODIC_SAVE_INTERVAL_SECONDS="300"
MINDX_MONITORING_PERFORMANCE_SAVE_ON_REQUEST_COUNT="20"

# --- VPS Deployment Configuration ---
MINDX_VPS_DEPLOYMENT="true"
MINDX_VPS_RESOURCE_ALLOCATION="true"
MINDX_VPS_NETWORK_DIAGNOSTICS="true"
MINDX_VPS_FOLDER_SHARING="true"
MINDX_VPS_CPU_ALLOCATION_MAX="80"
MINDX_VPS_GPU_ALLOCATION_ENABLED="true"

# Ollama Configuration (Update IP for your VPS)
MINDX_LLM__OLLAMA__BASE_URL="http://localhost:11434"
"""

        new_env_file = self.project_root / ".env.new"
        new_env_file.write_text(env_content)
        self.log_security_action(f"Generated fresh .env template at {new_env_file}")

    def clear_compromised_registries(self):
        """Clear agent/tool registries to force fresh identity sync"""
        registry_files = [
            "data/config/official_agents_registry.json",
            "data/config/official_tools_registry.json"
        ]

        for registry_file in registry_files:
            registry_path = self.project_root / registry_file
            if registry_path.exists():
                # Backup first
                backup_path = self.backup_dir / registry_path.name
                backup_path.write_text(registry_path.read_text())

                # Clear identities
                with open(registry_path, 'r') as f:
                    registry = json.load(f)

                # Reset agent identities
                if "registered_agents" in registry:
                    for agent_id, agent_info in registry["registered_agents"].items():
                        if "identity" in agent_info:
                            agent_info["identity"] = {
                                "public_key": "PENDING_FRESH_SYNC",
                                "signature": "PENDING_FRESH_SYNC"
                            }

                # Reset tool identities
                if "registered_tools" in registry:
                    for tool_id, tool_info in registry["registered_tools"].items():
                        if "identity" in tool_info:
                            tool_info["identity"] = {
                                "public_key": "PENDING_FRESH_SYNC",
                                "signature": "PENDING_FRESH_SYNC"
                            }

                registry["security_refresh"] = {
                    "timestamp": datetime.now().isoformat(),
                    "reason": "compromised_keys_refresh"
                }

                with open(registry_path, 'w') as f:
                    json.dump(registry, f, indent=2)

                self.log_security_action(f"Cleared identities in {registry_file}")

    def generate_vps_deployment_script(self):
        """Generate VPS deployment script for mindX"""
        deploy_script = f"""#!/bin/bash
# mindX VPS Fresh Deployment Script
# Generated: {datetime.now().isoformat()}

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
sudo -u mindx mkdir -p /home/mindx/{{logs,data,backups}}
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
server {{
    listen 80;
    server_name agenticplace.pythai.net;

    location /explore-agents {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\$host;
        proxy_set_header X-Real-IP \\$remote_addr;
        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\$scheme;
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\$host;
        proxy_set_header X-Real-IP \\$remote_addr;
        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\$scheme;
    }}
}}
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
"""

        deploy_script_path = self.project_root / "deploy" / "vps_deploy.sh"
        deploy_script_path.parent.mkdir(exist_ok=True)
        deploy_script_path.write_text(deploy_script)

        # Make executable
        if os.name != 'nt':
            os.chmod(deploy_script_path, 0o755)

        self.log_security_action(f"Generated VPS deployment script: {deploy_script_path}")

    def run_fresh_deployment(self):
        """Execute complete fresh deployment"""
        self.log_security_action("=== Starting Fresh mindX Deployment ===")

        # Step 1: Backup compromised data
        self.backup_compromised_data()

        # Step 2: Generate fresh wallets
        fresh_wallets = self.generate_fresh_agent_wallets()

        # Step 3: Generate fresh environment
        self.generate_fresh_env_config()

        # Step 4: Clear registries for fresh sync
        self.clear_compromised_registries()

        # Step 5: Generate VPS deployment script
        self.generate_vps_deployment_script()

        self.log_security_action("=== Fresh Deployment Preparation Complete ===")
        print("\n🔒 SECURITY REFRESH COMPLETE")
        print(f"📁 Backups stored in: {self.backup_dir}")
        print(f"🔑 Fresh wallets: {self.new_keys_file}")
        print(f"⚙️  Fresh .env: {self.project_root}/.env.new")
        print(f"🚀 VPS deploy script: {self.project_root}/deploy/vps_deploy.sh")
        print(f"📋 Security log: {self.security_log}")

        print("\n📝 NEXT STEPS:")
        print("1. Replace API keys in .env.new with fresh ones")
        print("2. Review and activate: mv .env.new .env")
        print("3. Review and activate: mv data/identity/.wallet_keys.env.new data/identity/.wallet_keys.env")
        print("4. Deploy to VPS using: ./deploy/vps_deploy.sh")
        print("5. Update explore-agents page for mindX interface")

        return fresh_wallets

if __name__ == "__main__":
    deployment = FreshDeployment()
    deployment.run_fresh_deployment()