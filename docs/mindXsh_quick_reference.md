# mindX.sh Quick Reference Guide

## 🚀 Quick Start

### **Basic Deployment**
```bash
# Make executable
chmod +x mindX.sh

# Deploy and start services
./mindX.sh --run /opt/mindx
```

### **Development Setup**
```bash
# Quick dev setup with debug logging
./mindX.sh --log-level DEBUG --run ~/mindx-dev

# Interactive setup with API keys
./mindX.sh --interactive --run ~/mindx-dev
```

### **Production Deployment**
```bash
# Production with custom config
./mindX.sh --config-file prod-config.json \
           --dotenv-file prod.env \
           --log-level WARNING \
           /opt/mindx-production
```

## 📋 Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--run` | Start services after setup | `./mindX.sh --run /opt/mindx` |
| `--config-file` | Use existing config | `--config-file /path/config.json` |
| `--dotenv-file` | Use existing .env | `--dotenv-file /path/.env` |
| `--interactive` | Prompt for API keys | `--interactive` |
| `--venv-name` | Custom venv name | `--venv-name myenv` |
| `--frontend-port` | Frontend port | `--frontend-port 3000` |
| `--backend-port` | Backend port | `--backend-port 8000` |
| `--log-level` | Log level | `--log-level DEBUG` |
| `-h, --help` | Show help | `./mindX.sh --help` |

## 🔧 Service Management

### **Check Status**
```bash
# Check if running
ps aux | grep -E "(uvicorn|node server.js)"

# Check PIDs
cat /opt/mindx/data/pids/mindx_backend.pid
cat /opt/mindx/data/pids/mindx_frontend.pid
```

### **View Logs**
```bash
# Backend logs
tail -f /opt/mindx/data/logs/mindx_coordinator_service.log

# Frontend logs
tail -f /opt/mindx/data/logs/mindx_frontend_service.log

# Deployment logs
tail -f /opt/mindx/data/logs/mindx_deployment_setup.log
```

### **Stop Services**
```bash
# Graceful stop (Ctrl+C)
# Or manual stop:
kill $(cat /opt/mindx/data/pids/mindx_backend.pid)
kill $(cat /opt/mindx/data/pids/mindx_frontend.pid)
```

## 🌐 Access Points

### **Services**
- **Backend API:** http://localhost:8000
- **Frontend UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

### **Key Endpoints**
- `GET /` - Root endpoint
- `POST /commands/evolve` - Evolve codebase
- `POST /coordinator/query` - Query coordinator
- `GET /status/mastermind` - System status
- `GET /identities` - List identities

## ⚙️ Configuration Files

### **Environment (.env)**
```bash
# Key settings
MINDX_LOG_LEVEL="INFO"
MINDX_LLM__DEFAULT_PROVIDER="ollama"
GEMINI_API_KEY="your-key-here"
MISTRAL_API_KEY="your-mistral-key-here"
```

### **Interactive Setup**
```bash
# Prompt for API keys during setup
./mindX.sh --interactive /opt/mindx

# Will ask for:
# - Gemini API Key (https://aistudio.google.com/app/apikey)
# - Mistral AI API Key (https://console.mistral.ai/)
```

### **JSON Config (mindx_config.json)**
```json
{
  "system": {"version": "0.4.0"},
  "llm": {"providers": {"ollama": {"enabled": true}}},
  "tools": {"note_taking": {"enabled": true}}
}
```

## 🚨 Troubleshooting

### **Common Issues**

#### **Permission Denied**
```bash
chmod +x mindX.sh
chmod 600 /opt/mindx/.env
```

#### **Port Already in Use**
```bash
# Check ports
netstat -tlnp | grep :8000
netstat -tlnp | grep :3000

# Use different ports
./mindX.sh --backend-port 9000 --frontend-port 4000 /opt/mindx
```

#### **Python/Node Not Found**
```bash
# Install Python 3
sudo apt install python3 python3-venv

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs
```

#### **Service Won't Start**
```bash
# Check logs
tail -f /opt/mindx/data/logs/mindx_deployment_setup.log

# Check Python environment
/opt/mindx/.mindx_env/bin/python --version

# Check dependencies
/opt/mindx/.mindx_env/bin/pip list
```

### **Debug Mode**
```bash
# Enable debug logging
./mindX.sh --log-level DEBUG --run /opt/mindx

# Check all logs
tail -f /opt/mindx/data/logs/*.log
```

## 📁 Directory Structure

```
/opt/mindx/
├── .mindx_env/                    # Python virtual environment
├── data/
│   ├── logs/                      # All log files
│   ├── pids/                      # Process ID files
│   └── config/                    # Configuration files
├── mindx_backend_service/         # Backend API
│   └── main_service.py
├── mindx_frontend_ui/             # Frontend UI
│   ├── index.html
│   ├── server.js
│   └── package.json
├── .env                          # Environment config
└── [mindx source code]           # Core modules
```

## 🔄 Maintenance

### **Update Dependencies**
```bash
cd /opt/mindx
source .mindx_env/bin/activate
pip install --upgrade -r requirements.txt
```

### **Restart Services**
```bash
# Stop services
pkill -f "uvicorn\|node server.js"

# Start services
./mindX.sh --run /opt/mindx
```

### **Backup Configuration**
```bash
# Backup config
tar -czf mindx-config-backup.tar.gz /opt/mindx/.env /opt/mindx/data/config/
```

## 🎯 Use Cases

### **Hackathon**
```bash
# Quick setup
./mindX.sh --run ~/hackathon-mindx
# Access: http://localhost:3000
```

### **Development**
```bash
# Dev with debug
./mindX.sh --log-level DEBUG --run ~/mindx-dev
# Edit code in ~/mindx-dev/
```

### **Production**
```bash
# Production setup
./mindX.sh --config-file prod-config.json \
           --dotenv-file prod.env \
           --log-level WARNING \
           /opt/mindx
```

## 📞 Support

### **Logs Location**
- Deployment: `/opt/mindx/data/logs/mindx_deployment_setup.log`
- Backend: `/opt/mindx/data/logs/mindx_coordinator_service.log`
- Frontend: `/opt/mindx/data/logs/mindx_frontend_service.log`

### **Configuration Files**
- Environment: `/opt/mindx/.env`
- JSON Config: `/opt/mindx/data/config/mindx_config.json`

### **Process Management**
- Backend PID: `/opt/mindx/data/pids/mindx_backend.pid`
- Frontend PID: `/opt/mindx/data/pids/mindx_frontend.pid`
