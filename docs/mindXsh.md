# mindX.sh - Comprehensive Deployment Script Documentation

## Overview

`mindX.sh` is a production-focused deployment script for the MindX Augmentic Intelligence System. It provides automated setup, configuration, and service management for the entire MindX ecosystem.

**Version:** 2.0.0  
**Purpose:** Complete MindX system deployment and management  
**Target:** Production environments, development setups, and hackathon deployments

## 🎯 Key Features

### **Automated Deployment**
- ✅ **Complete Environment Setup** - Python virtual environment, dependencies, and configuration
- ✅ **Service Generation** - Creates backend API and frontend UI from templates
- ✅ **Configuration Management** - Handles `.env` files and JSON configuration
- ✅ **Service Management** - Start/stop/restart services with PID tracking
- ✅ **Logging System** - Comprehensive logging for deployment and runtime

### **Modular Architecture**
- ✅ **Flexible Configuration** - Support for custom config files and environment variables
- ✅ **Service Separation** - Backend and frontend as independent services
- ✅ **Graceful Degradation** - Works with or without external API keys
- ✅ **Interactive Setup** - Prompts for API keys during installation
- ✅ **Cross-Platform** - Linux/macOS compatible with proper error handling

## 📋 Usage

### **Basic Usage**
```bash
./mindX.sh <target_install_directory>
```

### **Advanced Usage**
```bash
./mindX.sh [options] <target_install_directory>
```

### **Command Line Options**

| Option | Description | Default |
|--------|-------------|---------|
| `--config-file <path>` | Path to existing `mindx_config.json` | Auto-generated |
| `--dotenv-file <path>` | Path to existing `.env` file | Auto-generated |
| `--run` | Start services after setup | `false` |
| `--interactive` | Prompt for API keys (Gemini, Mistral AI) | `false` |
| `--venv-name <name>` | Virtual environment name | `.mindx_env` |
| `--frontend-port <port>` | Frontend service port | `3000` |
| `--backend-port <port>` | Backend service port | `8000` |
| `--log-level <level>` | Application log level | `INFO` |
| `-h, --help` | Show help message | - |

### **Examples**

#### **Quick Setup (Development)**
```bash
./mindX.sh --run /opt/mindx
```

#### **Interactive Setup with API Keys**
```bash
./mindX.sh --interactive --run /opt/mindx
# Will prompt for Gemini and Mistral AI API keys
```

#### **Production Deployment**
```bash
./mindX.sh --config-file /path/to/prod-config.json \
           --dotenv-file /path/to/prod.env \
           --log-level WARNING \
           /opt/mindx-production
```

#### **Custom Configuration**
```bash
./mindX.sh --venv-name mindx-prod \
           --frontend-port 8080 \
           --backend-port 9000 \
           --run \
           /var/www/mindx
```

## 🏗️ Architecture

### **Directory Structure**
```
<target_install_directory>/
├── .mindx_env/                    # Python virtual environment
├── data/                          # Data directory
│   ├── logs/                      # Application logs
│   ├── pids/                      # Process ID files
│   └── config/                    # Configuration files
├── mindx_backend_service/         # Backend API service
│   └── main_service.py           # FastAPI application
├── mindx_frontend_ui/             # Frontend UI service
│   ├── index.html                # Main UI page
│   ├── styles.css                # Styling
│   ├── app.js                    # Frontend logic
│   ├── server.js                 # Express server
│   └── package.json              # Node.js dependencies
├── .env                          # Environment configuration
└── [mindx source code]           # Core MindX modules
```

### **Service Architecture**

#### **Backend Service (FastAPI)**
- **Port:** Configurable (default: 8000)
- **Framework:** FastAPI with uvicorn
- **Features:** REST API, CORS support, comprehensive endpoints
- **Logging:** Structured logging to `data/logs/mindx_coordinator_service.log`

#### **Frontend Service (Express.js)**
- **Port:** Configurable (default: 3000)
- **Framework:** Express.js with static file serving
- **Features:** Web UI, real-time status monitoring, API integration
- **Logging:** Application logs to `data/logs/mindx_frontend_service.log`

## 🔧 Configuration

### **Interactive API Key Setup**

The script supports interactive collection of API keys during setup using the `--interactive` flag:

```bash
./mindX.sh --interactive /opt/mindx
```

When interactive mode is enabled, the script will prompt for:

1. **Gemini API Key** - From Google AI Studio (https://aistudio.google.com/app/apikey)
2. **Mistral AI API Key** - From Mistral AI Console (https://console.mistral.ai/)

**Features:**
- ✅ **User-friendly prompts** - Clear instructions with helpful URLs
- ✅ **Optional input** - Press Enter to skip and use default placeholders
- ✅ **Secure handling** - Keys are stored with proper file permissions (600)
- ✅ **Logging** - All key collection activities are logged for audit

**Example Interactive Session:**
```
=== API Key Configuration ===
Enter your API keys (press Enter to skip and use defaults):

Gemini API Key (from https://aistudio.google.com/app/apikey): your-gemini-key-here

Mistral AI API Key (from https://console.mistral.ai/): your-mistral-key-here

[INFO] Gemini API key provided.
[INFO] Mistral AI API key provided.
[INFO] API key collection complete.
```

### **Environment Variables (.env)**

The script generates a comprehensive `.env` file with the following sections:

#### **General Configuration**
```bash
# Logging Level
MINDX_LOG_LEVEL="INFO"

# Default LLM Provider
MINDX_LLM__DEFAULT_PROVIDER="ollama"
```

#### **LLM Provider Configuration**
```bash
# Ollama Configuration
MINDX_LLM__OLLAMA__DEFAULT_MODEL="nous-hermes2:latest"
MINDX_LLM__OLLAMA__DEFAULT_MODEL_FOR_CODING="deepseek-coder:6.7b-instruct"

# Gemini Configuration
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
MINDX_LLM__GEMINI__DEFAULT_MODEL="gemini-1.5-flash-latest"

# Mistral AI Configuration
MISTRAL_API_KEY="YOUR_MISTRAL_API_KEY_HERE"
MINDX_LLM__MISTRAL__DEFAULT_MODEL="mistral-large-latest"
MINDX_LLM__MISTRAL__DEFAULT_MODEL_FOR_CODING="codestral-latest"
```

#### **Agent-Specific Configuration**
```bash
# Self-Improvement Agent
MINDX_SELF_IMPROVEMENT_AGENT__LLM__PROVIDER="ollama"
MINDX_SELF_IMPROVEMENT_AGENT__LLM__MODEL="deepseek-coder:6.7b-instruct"

# Coordinator Agent
MINDX_COORDINATOR__LLM__PROVIDER="ollama"
MINDX_COORDINATOR__LLM__MODEL="nous-hermes2:latest"
```

#### **Monitoring Configuration**
```bash
# Resource Monitoring
MINDX_MONITORING__RESOURCE__ENABLED="true"
MINDX_MONITORING__RESOURCE__INTERVAL="15.0"

# Performance Monitoring
MINDX_MONITORING__PERFORMANCE__ENABLE_PERIODIC_SAVE="true"
MINDX_MONITORING__PERFORMANCE__PERIODIC_SAVE_INTERVAL_SECONDS="300"
```

### **JSON Configuration (mindx_config.json)**

The script generates a comprehensive JSON configuration file:

```json
{
  "system": {
    "version": "0.4.0",
    "name": "MindX Self-Improving System (Augmentic)"
  },
  "logging": {
    "uvicorn_level": "info"
  },
  "llm": {
    "providers": {
      "ollama": {"enabled": true},
      "gemini": {"enabled": true}
    }
  },
  "self_improvement_agent": {
    "analysis": {
      "max_code_chars": 70000,
      "max_description_tokens": 350
    }
  },
  "coordinator": {
    "autonomous_improvement": {
      "critical_components": [
        "mindx.learning.self_improve_agent",
        "mindx.orchestration.coordinator_agent",
        "mindx.utils.config"
      ]
    }
  },
  "tools": {
    "note_taking": {"enabled": true},
    "summarization": {"enabled": true},
    "web_search": {"enabled": true}
  }
}
```

## 🚀 Service Management

### **Starting Services**

#### **Automatic Start (with --run flag)**
```bash
./mindX.sh --run /opt/mindx
```

#### **Manual Start**
```bash
# Backend Service
cd /opt/mindx/mindx_backend_service
/opt/mindx/.mindx_env/bin/python main_service.py

# Frontend Service
cd /opt/mindx/mindx_frontend_ui
node server.js
```

### **Service Monitoring**

#### **Check Service Status**
```bash
# Check if services are running
ps aux | grep -E "(uvicorn|node server.js)"

# Check PID files
cat /opt/mindx/data/pids/mindx_backend.pid
cat /opt/mindx/data/pids/mindx_frontend.pid
```

#### **View Logs**
```bash
# Backend logs
tail -f /opt/mindx/data/logs/mindx_coordinator_service.log

# Frontend logs
tail -f /opt/mindx/data/logs/mindx_frontend_service.log

# Deployment logs
tail -f /opt/mindx/data/logs/mindx_deployment_setup.log
```

### **Stopping Services**

#### **Graceful Stop (Ctrl+C)**
The script handles SIGINT/SIGTERM signals and gracefully stops all services.

#### **Manual Stop**
```bash
# Stop backend
kill $(cat /opt/mindx/data/pids/mindx_backend.pid)

# Stop frontend
kill $(cat /opt/mindx/data/pids/mindx_frontend.pid)
```

## 🔌 API Endpoints

The script generates a comprehensive FastAPI backend with the following endpoints:

### **Core Commands**
- `POST /commands/evolve` - Evolve mindX codebase
- `POST /commands/deploy` - Deploy a new agent
- `POST /commands/introspect` - Generate a new persona
- `POST /commands/analyze_codebase` - Analyze a codebase
- `POST /commands/basegen` - Generate Markdown documentation

### **System Status**
- `GET /status/mastermind` - Get Mastermind status
- `GET /registry/agents` - Show agent registry
- `GET /registry/tools` - Show tool registry
- `GET /logs/runtime` - Get runtime logs

### **Identity Management**
- `GET /identities` - List all identities
- `POST /identities` - Create a new identity
- `DELETE /identities` - Deprecate an identity

### **Coordinator Operations**
- `POST /coordinator/query` - Query the Coordinator
- `POST /coordinator/analyze` - Trigger system analysis
- `POST /coordinator/improve` - Request component improvement
- `GET /coordinator/backlog` - Get improvement backlog

### **Agent Management**
- `GET /agents` - List all registered agents
- `POST /agents` - Create a new agent
- `DELETE /agents/{agent_id}` - Delete an agent
- `POST /agents/{agent_id}/evolve` - Evolve a specific agent
- `POST /agents/{agent_id}/sign` - Sign a message with agent's identity

## 🎨 Frontend Interface

The script generates a modern web interface with:

### **Features**
- **Real-time Status Monitoring** - Connection status indicator
- **Command Interface** - Send directives and queries
- **Response Display** - Formatted JSON responses
- **Responsive Design** - Works on desktop and mobile

### **UI Components**
- **Evolve Codebase** - Text area for high-level directives
- **Query Coordinator** - Input field for coordinator queries
- **Response Output** - Pre-formatted JSON response display
- **Status Light** - Visual connection indicator (red/green)

## 🛠️ Development Features

### **Graceful Degradation**
- ✅ **Works without API keys** - Mock responses for missing services
- ✅ **Flexible configuration** - Adapts to available resources
- ✅ **Clear error messages** - Helpful debugging information

### **Logging System**
- ✅ **Structured logging** - Consistent log format across all components
- ✅ **Multiple log levels** - DEBUG, INFO, WARNING, ERROR, CRITICAL
- ✅ **Log rotation** - Automatic log management
- ✅ **Service-specific logs** - Separate logs for each service

### **Error Handling**
- ✅ **Comprehensive error checking** - Validates all operations
- ✅ **Graceful failure recovery** - Continues operation when possible
- ✅ **Clear error messages** - Helpful debugging information
- ✅ **Cleanup on exit** - Proper resource cleanup

## 🔒 Security Features

### **File Permissions**
- ✅ **Secure .env files** - 600 permissions for sensitive data
- ✅ **Protected configuration** - Appropriate permissions for config files
- ✅ **Log file security** - Proper permissions for log files

### **Process Management**
- ✅ **PID file tracking** - Prevents duplicate processes
- ✅ **Graceful shutdown** - Proper signal handling
- ✅ **Resource cleanup** - Clean exit procedures

## 📊 Monitoring & Maintenance

### **Health Checks**
- ✅ **Service status monitoring** - Real-time service health
- ✅ **Connection testing** - API connectivity verification
- ✅ **Resource monitoring** - CPU, memory, disk usage tracking

### **Maintenance Tasks**
- ✅ **Log rotation** - Automatic log file management
- ✅ **PID cleanup** - Orphaned process cleanup
- ✅ **Configuration validation** - Settings verification

## 🚨 Troubleshooting

### **Common Issues**

#### **Service Won't Start**
```bash
# Check logs
tail -f /opt/mindx/data/logs/mindx_coordinator_service.log

# Check Python environment
/opt/mindx/.mindx_env/bin/python --version

# Check dependencies
/opt/mindx/.mindx_env/bin/pip list
```

#### **Port Conflicts**
```bash
# Check port usage
netstat -tlnp | grep :8000
netstat -tlnp | grep :3000

# Use different ports
./mindX.sh --backend-port 9000 --frontend-port 4000 /opt/mindx
```

#### **Permission Issues**
```bash
# Fix permissions
chmod +x mindX.sh
chmod 600 /opt/mindx/.env
chmod 644 /opt/mindx/data/config/mindx_config.json
```

### **Debug Mode**
```bash
# Enable debug logging
./mindX.sh --log-level DEBUG --run /opt/mindx

# Check deployment logs
tail -f /opt/mindx/data/logs/mindx_deployment_setup.log
```

## 🎯 Best Practices

### **Production Deployment**
1. **Use dedicated user** - Run as non-root user
2. **Configure firewall** - Restrict port access
3. **Set up monitoring** - Use external monitoring tools
4. **Regular backups** - Backup configuration and data
5. **Update dependencies** - Keep packages current

### **Development Setup**
1. **Use virtual environments** - Isolate dependencies
2. **Enable debug logging** - For troubleshooting
3. **Use local API keys** - For testing
4. **Monitor logs** - Watch for errors
5. **Test regularly** - Verify functionality

### **Hackathon Deployment**
1. **Quick setup** - Use `--run` flag for immediate start
2. **Default configuration** - Use built-in defaults
3. **Monitor status** - Check service health
4. **Test endpoints** - Verify API functionality
5. **Document changes** - Keep track of modifications

## 📈 Performance Optimization

### **Resource Management**
- **Memory usage** - Monitor Python and Node.js memory
- **CPU utilization** - Check service CPU usage
- **Disk I/O** - Monitor log file growth
- **Network traffic** - Check API request volume

### **Scaling Considerations**
- **Load balancing** - Multiple backend instances
- **Database integration** - External data storage
- **Caching** - Response caching for performance
- **CDN** - Static asset delivery

## 🔄 Updates & Maintenance

### **Script Updates**
```bash
# Backup current deployment
cp -r /opt/mindx /opt/mindx-backup-$(date +%Y%m%d)

# Update script
wget https://raw.githubusercontent.com/your-repo/mindX.sh
chmod +x mindX.sh

# Re-deploy
./mindX.sh --run /opt/mindx
```

### **Configuration Updates**
```bash
# Edit configuration
nano /opt/mindx/.env
nano /opt/mindx/data/config/mindx_config.json

# Restart services
pkill -f "uvicorn\|node server.js"
./mindX.sh --run /opt/mindx
```

## 🎉 Conclusion

`mindX.sh` is a comprehensive deployment script that provides:

- ✅ **Complete automation** - One-command deployment
- ✅ **Production-ready** - Robust error handling and logging
- ✅ **Flexible configuration** - Adapts to any environment
- ✅ **Service management** - Start/stop/monitor services
- ✅ **Security features** - Proper permissions and cleanup
- ✅ **Monitoring capabilities** - Health checks and logging
- ✅ **Developer-friendly** - Clear documentation and examples

The script enables rapid deployment of the MindX system for development, testing, production, and hackathon environments while maintaining security, reliability, and maintainability.
