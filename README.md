# mindX: Godel-machine
**✅ EXPERIMENTAL** - Fully Autonomous Self-Improving AI System

mindX evolutionary software project.
Mistral AI integration and comprehensive documentation.

## 🚀 What is mindX?

mindX represents an implemenation of a godel machine- a fully self-improving, economically viable, and cryptographically secure multi-agent system. We are building agents and creating a **sovereign digital polity** where intelligence operates independently, evolves continuously, and participates in economic systems.

### **evolutionary Capabilities**
- **Complete Autonomy**: 1-hour improvement cycles without human intervention
- **Economic Viability**: Real-time cost optimization and treasury management
- **Cryptographic Sovereignty**: Ethereum-compatible wallet-based agent authentication
- TODO include crossmint in IDmanagerAgent
- **Strategic Evolution**: 4-phase audit-driven self-improvement pipeline
- **Mistral AI Integration**: Advanced reasoning, code generation, and memory systems

## 🏗️ Architecture

### **Agent Registry Status**
- **Total Agents**: 9/20+ registered (45% complete)
- **Tools Secured**: 17/17 tools cryptographically secured (100%)
- **Identity Management**: Ethereum-compatible wallet system active
- **Economic System**: Real-time cost optimization and treasury management

### **Core Components**
- **MastermindAgent** (`0xb9B46126551652eb58598F1285aC5E86E5CcfB43`): Strategic orchestration with Mistral AI reasoning
- **CoordinatorAgent** (`0x7371e20033f65aB598E4fADEb5B4e400Ef22040A`): Infrastructure management and autonomous improvement
- **BDI Agent** (`0xf8f2da254D4a3F461e0472c65221B26fB4e91fB7`): Enhanced with 9 new action handlers and Mistral AI integration
- **Strategic Evolution Agent** (`0x5208088F9C7c45a38f2a19B6114E3C5D17375C65`): 4-phase audit-driven campaign pipeline
- **Guardian Agent** (`0xC2cca3d6F29dF17D1999CFE0458BC3DEc024F02D`): Security validation with cryptographic identity management
- **ID Manager Agent** (`0x290bB0497dBDbC5E8B577E0cc92457cB015A2a1f`): Ethereum-compatible wallet system for all agents
- include CrossMint in IDManagerAgent

### **Mistral AI Integration**
- **Mistral Large** (`mistral-large-latest`): Advanced reasoning and strategic thinking
- **Codestral** (`codestral-latest`): Autonomous code generation and software development
- **Mistral Nemo** (`mistral-nemo-latest`): High-speed processing for real-time operations
- **Mistral Embed** (`mistral-embed-v2`): Semantic memory and knowledge retrieval

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python dependencies
pip install -r requirements.txt

# Ensure Python 3.11+ is available
python3 --version
```

### Environment Setup
```bash
# Copy and configure environment
cp .env.sample .env

# Add your Mistral AI API key
echo "MISTRAL_API_KEY=your-mistral-api-key-here" >> .env

# Optional: Configure other API keys
echo "OPENAI_API_KEY=your-openai-key" >> .env
echo "ANTHROPIC_API_KEY=your-anthropic-key" >> .env
```

### Launch Autonomous System

#### 🚀 **Recommended: Enhanced Web Interface**
```bash
# Start MindX with enhanced web interface (backend + frontend)
./mindX.sh --frontend

# Features: Real-time monitoring, health status, agent management, system metrics
# Access: http://localhost:3000 (Frontend) + http://localhost:8000 (Backend API)
```

#### 🔧 **Advanced Deployment Options**
```bash
# Basic deployment (backend + frontend services)
./mindX.sh --run

# Interactive setup with API key configuration
./mindX.sh --interactive

# Deploy to specific directory
./mindX.sh /path/to/deployment/directory

# Custom ports
./mindX.sh --frontend --frontend-port 3001 --backend-port 8001

# Use existing configuration files
./mindX.sh --config-file /path/to/mindx_config.json --dotenv-file /path/to/.env
```

#### 📋 **mindX.sh Script Options**
```bash
# Show help and all available options
./mindX.sh --help

# Available options:
--frontend                   # Start enhanced web interface (recommended)
--run                        # Start backend and frontend services
--interactive                # Prompt for API keys during setup
--replicate                  # Copy source code to target directory
--config-file <path>         # Use existing mindx_config.json
--dotenv-file <path>         # Use existing .env file
--venv-name <name>           # Override virtual environment name
--frontend-port <port>       # Override frontend port (default: 3000)
--backend-port <port>        # Override backend port (default: 8000)
--log-level <level>          # Set log level (DEBUG, INFO, etc.)
```

#### 🎯 **Quick Start Examples**
```bash
# 1. First-time setup with interactive API key configuration
./mindX.sh --frontend --interactive

# 2. Production deployment with custom configuration
./mindX.sh --frontend --config-file production_config.json

# 3. Development setup with custom ports
./mindX.sh --frontend --frontend-port 3001 --backend-port 8001

# 4. Full system deployment without web interface
./mindX.sh --run
```

#### 🔄 **Alternative Launch Methods**
```bash
# Direct execution (legacy)
python3 augmentic.py

# Web interface launcher (legacy)
./run_mindx_web.sh

# Simple version (minimal features)
python3 augmentic_simple.py
```

### Monitor System Status
```bash
# Check system status
python3 augmentic.py --status

# View agent performance metrics
python3 augmentic.py --metrics

# Monitor Mistral AI usage and costs
python3 augmentic.py --costs

# Check evolution progress
python3 augmentic.py --evolution
```

## 📁 Project Structure

```
mindX/
├── docs/                    # Complete documentation (103+ files)
│   ├── agents_architectural_reference.md
│   ├── mistral_api.md
│   ├── hackathon.md
│   └── [100+ more documentation files]
├── tests/                   # Comprehensive test suite (30+ files)
│   ├── test_mistral_chat_completion_api.py
│   ├── test_agent_lifecycle_complete.py
│   └── [25+ more test files]
├── agents/                  # Agent implementations
│   ├── mastermind_agent.py
│   ├── guardian_agent.py
│   └── [other agent files]
├── api/                     # API components
│   ├── mistral_api.py
│   └── api_server.py
├── core/                    # Core system components
│   ├── bdi_agent.py
│   ├── agint.py
│   └── belief_system.py
├── orchestration/           # Orchestration agents
│   ├── coordinator_agent.py
│   └── ceo_agent.py
├── learning/                # Learning and evolution
│   ├── strategic_evolution_agent.py
│   └── self_improve_agent.py
├── monitoring/              # Performance monitoring
│   ├── enhanced_monitoring_system.py
│   └── performance_monitor.py
├── tools/                   # Tool ecosystem (27+ tools)
│   ├── audit_and_improve_tool.py
│   ├── augmentic_intelligence_tool.py
│   └── [25+ more tools]
├── models/                  # Model configurations
│   ├── mistral.yaml
│   └── gemini.yaml
├── augmentic.py             # Main entry point
├── augmentic_simple.py      # Simplified version
├── start_autonomous_evolution.py
├── mindX.sh                 # Enhanced deployment script with web interface
├── run_mindx_web.sh         # Legacy web interface launcher (deprecated)
├── mindx_frontend_ui/       # Enhanced frontend UI files
│   ├── index.html           # Main HTML interface
│   ├── app.js               # Frontend JavaScript with full integration
│   ├── styles3.css          # Cyberpunk 2049 theme CSS
│   └── server.js            # Frontend server
├── mindx_backend_service/   # Backend API service
│   └── main_service.py      # FastAPI backend with all endpoints
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies
├── .env.sample              # Environment template
└── .gitignore               # Git ignore rules
```

## 🎯 Key Features

### **Autonomous Operation**
- **Complete Autonomy**: 1-hour improvement cycles without human intervention
- **Strategic Evolution**: 4-phase audit-driven self-improvement pipeline
- **Economic Viability**: Real-time cost optimization and treasury management
- **Cryptographic Security**: Ethereum-compatible wallet-based authentication

### **Mistral AI Integration**
- **Advanced Reasoning**: Mistral Large for complex strategic thinking
- **Code Generation**: Codestral for autonomous software development
- **High-Speed Processing**: Mistral Nemo for real-time operations
- **Semantic Memory**: Mistral Embed for knowledge retrieval and storage

### **Production Ready**
- **Agent Registry**: 9/20+ agents registered with cryptographic identities
- **Tool Ecosystem**: 17/17 tools cryptographically secured
- **Comprehensive Testing**: 30+ test files with full coverage
- **Complete Documentation**: 103+ documentation files

## 📚 Documentation

### **Core Architecture**
- **[Agent Architecture](https://github.com/abaracadabra/mindX/blob/main/docs/agents_architectural_reference.md)** - Complete agent registry and capabilities
- **[Autonomous Civilization](https://github.com/abaracadabra/mindX/blob/main/docs/autonomous_civilization.md)** - Philosophical and technical foundation
- **[BDI Agent](https://github.com/abaracadabra/mindX/blob/main/docs/bdi_agent.md)** - Belief-Desire-Intention architecture
- **[Mastermind Agent](https://github.com/abaracadabra/mindX/blob/main/docs/mastermind_agent.md)** - Strategic orchestration system

### **Mistral AI Integration**
- **[Mistral API Documentation](https://github.com/abaracadabra/mindX/blob/main/docs/mistral_api.md)** - Complete API integration guide
- **[Mistral API Compliance](https://github.com/abaracadabra/mindX/blob/main/docs/mistral_chat_completion_api_compliance.md)** - Official API 1.0.0 compliance
- **[Mistral Models Configuration](https://github.com/abaracadabra/mindX/blob/main/docs/mistral_models.md)** - Model selection and optimization

### **Advanced Features**
- **[Strategic Evolution](https://github.com/abaracadabra/mindX/blob/main/docs/strategic_evolution_agent.md)** - Autonomous improvement system
- **[Memory Architecture](https://github.com/abaracadabra/mindX/blob/main/docs/memory.md)** - Scalable memory management
- **[Blueprint Agent](https://github.com/abaracadabra/mindX/blob/main/docs/blueprint_agent.md)** - System design automation
- **[Guardian Agent](https://github.com/abaracadabra/mindX/blob/main/docs/guardian_agent.md)** - Security and validation

### **Hackathon & Competition**
- **[Hackathon Submission](https://github.com/abaracadabra/mindX/blob/main/docs/hackathon.md)** - Internet of Agents competition entry
- **[Technical Architecture](https://github.com/abaracadabra/mindX/blob/main/docs/TECHNICAL.md)** - Complete system design

## 🧪 Testing

### **Run Test Suite**
```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_mistral_chat_completion_api.py
python -m pytest tests/test_agent_lifecycle_complete.py

# Run with coverage
python -m pytest tests/ --cov=.
```

### **Test Categories**
- **Mistral AI Integration**: API compliance and functionality tests
- **Agent Lifecycle**: Complete agent creation and management tests
- **System Integration**: End-to-end autonomous operation tests
- **Performance**: Load testing and optimization validation

## 🌐 Enhanced Web Interface

### **Real-Time Monitoring Dashboard**
The enhanced web interface provides a comprehensive control panel with:

- **🔴🟢 Health Status**: Live system health indicators with component-level monitoring
- **📊 Performance Metrics**: Real-time CPU, memory, and disk usage tracking
- **🤖 Agent Management**: Complete agent registry with real-time status updates
- **📝 System Logs**: Live log streaming with filtering and search capabilities
- **💻 Terminal Access**: Built-in terminal for system commands and monitoring
- **⚙️ Admin Controls**: System restart, backup, configuration management

### **Access the Web Interface**
```bash
# Start enhanced web interface
./mindX.sh --frontend

# Access URLs:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### **Web Interface Features**
- **Cyberpunk 2049 Theme**: Professional UI with advanced animations
- **Real-Time Updates**: Live data refresh without page reload
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Error Handling**: Graceful degradation and user-friendly error messages
- **API Integration**: Complete backend-frontend integration with all endpoints

## 🚀 Deployment

### **Production Deployment**
```bash
# Enhanced web interface (recommended)
./mindX.sh --frontend

# Basic services deployment
./mindX.sh --run

# Custom deployment directory
./mindX.sh /opt/mindx --frontend

# Production with custom configuration
./mindX.sh --frontend --config-file production_config.json --dotenv-file .env.prod
```

### **Development & Testing**
```bash
# Development with custom ports
./mindX.sh --frontend --frontend-port 3001 --backend-port 8001

# Interactive setup for first-time users
./mindX.sh --frontend --interactive

# Replicate source code to target directory
./mindX.sh --replicate /path/to/deployment
```

### **Legacy Deployment Methods**
```bash
# Legacy web interface (deprecated)
./run_mindx_web.sh

# Docker deployment (if available)
docker build -t mindx .
docker run -p 8000:8000 mindx
```

### **Environment Requirements**
- **Python**: 3.11+
- **Memory**: 8GB+ RAM recommended
- **Storage**: 10GB+ free space
- **Network**: Internet access for Mistral AI API

## 🔧 Troubleshooting

### **Common Issues & Solutions**

#### **Port Already in Use**
```bash
# Check what's using the ports
lsof -i :3000  # Frontend port
lsof -i :8000  # Backend port

# Kill processes if needed
sudo kill -9 $(lsof -ti:3000)
sudo kill -9 $(lsof -ti:8000)

# Use different ports
./mindX.sh --frontend --frontend-port 3001 --backend-port 8001
```

#### **Permission Denied**
```bash
# Make script executable
chmod +x mindX.sh

# Run with proper permissions
sudo ./mindX.sh --frontend
```

#### **Python Environment Issues**
```bash
# Ensure Python 3.11+ is installed
python3 --version

# Create virtual environment manually
python3 -m venv .mindx_env
source .mindx_env/bin/activate
pip install -r requirements.txt
```

#### **API Key Configuration**
```bash
# Interactive setup for API keys
./mindX.sh --frontend --interactive

# Manual .env configuration
cp .env.sample .env
nano .env  # Add your API keys
```

#### **Frontend Not Loading**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check frontend logs
tail -f data/logs/mindx_frontend_service.log

# Restart with verbose logging
./mindX.sh --frontend --log-level DEBUG
```

#### **Backend API Errors**
```bash
# Check backend logs
tail -f data/logs/mindx_coordinator_service.log

# Test API endpoints
curl http://localhost:8000/
curl http://localhost:8000/status/mastermind
curl http://localhost:8000/health
```

### **Getting Help**
- Check the logs in `data/logs/` directory
- Run `./mindX.sh --help` for all available options
- Review the API documentation at `http://localhost:8000/docs`
- Check the [Issues](https://github.com/abaracadabra/mindX/issues) page

## 🤝 Contributing

This is the evolution of mindX - a production-ready godel-machine. The system is designed to operate independently while providing comprehensive documentation and testing capabilities.

### **Development Guidelines**
- Follow the existing code structure and patterns
- Add comprehensive tests for new features
- Update documentation for any changes
- Ensure Mistral AI integration compatibility

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🔗 Links

- **Repository**: [GitHub - abaracadabra/mindX](https://github.com/abaracadabra/mindX)
- **Documentation**: [Complete Documentation](https://github.com/abaracadabra/mindX/tree/main/docs)
- **Hackathon Entry**: [Internet of Agents Submission](https://github.com/abaracadabra/mindX/blob/main/docs/hackathon.md)

---

## 🎉 **mindX: The First Autonomous Digital Civilization**

**Status**: ✅ **EXPERIMENTAL** - Fully Deployed & Operational  
**Achievement**: World's first autonomous digital civilization with economic viability  
**Innovation**: Complete Mistral AI integration with cryptographic sovereignty  
**Impact**: Transforming intelligence from service to stakeholder  

*Where Intelligence Meets Autonomy - The Dawn of Agentic Sovereignty*

(c) 2025 PYTHAI Institute for Emergent Systems
