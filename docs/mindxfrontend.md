# MindX Frontend Documentation

## Overview

The MindX Frontend is a sophisticated web-based control panel for managing the MindX Augmentic Intelligence system. It provides a cyberpunk-themed interface with real-time monitoring, agent management, and system control capabilities.

## Architecture

### Frontend Components

```
mindx_frontend_ui/
├── index.html          # Main application interface
├── app.js             # Core JavaScript functionality (34,341+ tokens)
├── styles3.css        # Enhanced cyberpunk styling
├── styles.css         # Fallback basic styling
├── corporate.css      # Corporate theme styling
├── server.js          # Express.js static server
├── package.json       # Node.js dependencies
├── debug.html         # Debug interface
└── test.html          # Test interface
```

### Technology Stack

- **Frontend Server**: Express.js (Node.js)
- **Styling**: CSS3 with cyberpunk theme
- **JavaScript**: Vanilla ES6+ with modern features
- **Backend Communication**: REST API with FastAPI
- **Real-time Updates**: Server-Sent Events (SSE)

## Installation & Setup

### Prerequisites

- Node.js (v14 or higher)
- Python 3.8+ with virtual environment
- MindX backend services running

### Quick Start

1. **Start the frontend**:
   ```bash
   ./mindX.sh --frontend
   ```

2. **Access the interface**:
   - Main Interface: http://localhost:3000
   - Debug Interface: http://localhost:3000/debug.html
   - Test Interface: http://localhost:3000/test.html

### Manual Setup

1. **Install dependencies**:
   ```bash
   cd mindx_frontend_ui
   npm install
   ```

2. **Start the server**:
   ```bash
   node server.js
   ```

## Configuration

### Environment Variables

- `FRONTEND_PORT`: Port for frontend server (default: 3000)
- `BACKEND_PORT`: Port for backend API (default: 8000)
- `BACKEND_HOST`: Backend host (default: localhost)

### Port Configuration

The frontend automatically detects and configures ports:
- Frontend: 3000 (configurable via `FRONTEND_PORT`)
- Backend: 8000 (configurable via `BACKEND_PORT`)

## User Interface

### Main Interface Features

#### **Navigation Tabs**
- **Dashboard**: System overview and status
- **Agents**: Agent management and monitoring
- **Commands**: Direct command execution
- **Logs**: System logs and debugging
- **Terminal**: Built-in terminal interface
- **Debug**: Advanced debugging tools

#### **Visual Design**
- **Theme**: Cyberpunk aesthetic with neon colors
- **Color Scheme**: 
  - Primary: Electric blue (#00ffff)
  - Secondary: Neon green (#00ff00)
  - Accent: Hot pink (#ff00ff)
  - Background: Dark (#0a0a0a)
- **Typography**: Monospace fonts for technical feel
- **Animations**: Smooth transitions and hover effects

#### **Real-time Updates**
- Live system status monitoring
- Real-time log streaming
- Agent activity tracking
- Performance metrics updates

## API Integration

### Complete REST API Endpoints

The frontend communicates with the MindX backend through a comprehensive REST API. The system has two main API servers:

#### **Primary API Server (api/api_server.py) - Version 2.0.0**

**System & Commands**
- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check endpoint
- `GET /system/status` - Get system status
- `POST /system/evolve` - Evolve the entire MindX codebase
- `POST /system/analyze_codebase` - Analyze a local codebase
- `POST /system/replicate` - Trigger autonomous self-replication (Status 202)
- `GET /system/logs` - Get system logs with level filtering
- `GET /system/metrics` - Get performance metrics
- `GET /system/resources` - Get resource usage
- `GET /system/config` - Get system configuration
- `POST /system/execute` - Execute terminal command (security restricted)

**Coordinator**
- `POST /coordinator/query` - Query the Coordinator Agent
- `POST /coordinator/improve` - Request a specific component improvement
- `GET /coordinator/backlog` - Get the improvement backlog

**Agents**
- `GET /agents/` - List all registered agents
- `POST /agents/` - Create a new agent
- `DELETE /agents/{agent_id}` - Delete an agent
- `POST /agents/{agent_id}/sign` - Sign a message with an agent's identity

**Identities**
- `GET /identities/` - List all identities
- `POST /identities/` - Create a new identity

**Core Agent Activity**
- `GET /core/agent-activity` - Get agent activity status
- `POST /commands/agint/stream` - AGInt streaming endpoint
- `POST /test/mistral` - Test Mistral API
- `GET /orchestration/coordinator` - Get coordinator status

#### **Legacy API Server (mindx_backend_service/main_service.py) - Version 1.3.4**

**Commands**
- `POST /commands/evolve` - Evolve mindX codebase
- `POST /commands/deploy` - Deploy a new agent
- `POST /commands/introspect` - Generate a new persona
- `POST /commands/analyze_codebase` - Analyze a codebase
- `POST /commands/basegen` - Generate Markdown documentation
- `POST /commands/audit_gemini` - Audit Gemini models
- `POST /commands/agint/stream` - AGInt Cognitive Loop Stream

**Status & Registry**
- `GET /status/mastermind` - Get Mastermind status
- `GET /registry/agents` - Show agent registry
- `GET /registry/tools` - Show tool registry
- `GET /system/status` - System status
- `GET /health` - Health check endpoint

**Identities**
- `GET /identities` - List all identities
- `POST /identities` - Create a new identity
- `DELETE /identities` - Deprecate an identity

**Coordinator**
- `POST /coordinator/query` - Query the Coordinator
- `POST /coordinator/analyze` - Trigger system analysis
- `POST /coordinator/improve` - Request a component improvement
- `GET /coordinator/backlog` - Get the improvement backlog
- `POST /coordinator/backlog/process` - Process a backlog item
- `POST /coordinator/backlog/approve` - Approve a backlog item
- `POST /coordinator/backlog/reject` - Reject a backlog item

**Agents**
- `GET /agents` - List all registered agents
- `POST /agents` - Create a new agent
- `DELETE /agents/{agent_id}` - Delete an agent
- `POST /agents/{agent_id}/evolve` - Evolve a specific agent
- `POST /agents/{agent_id}/sign` - Sign a message with an agent's identity

**Core & BDI**
- `GET /core/bdi-status` - BDI Agent status with belief, desire, intention details
- `GET /core/agent-activity` - Get agent activity

**Simple Coder**
- `GET /simple-coder/status` - Get Simple Coder Status
- `GET /simple-coder/update-requests` - Get Update Requests
- `POST /simple-coder/approve-update/{request_id}` - Approve Update Request
- `POST /simple-coder/reject-update/{request_id}` - Reject Update Request

**Logs**
- `GET /logs/runtime` - Get runtime logs

**Root**
- `GET /` - Root endpoint with welcome message

### API Request Examples

#### System Status
```javascript
fetch('/system/status')
  .then(response => response.json())
  .then(data => console.log(data));
```

#### Evolve System
```javascript
fetch('/system/evolve', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ directive: 'Improve the user interface' })
})
.then(response => response.json())
.then(data => console.log(data));
```

#### Query Coordinator
```javascript
fetch('/coordinator/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'What is the current system status?' })
})
.then(response => response.json())
.then(data => console.log(data));
```

#### Create Agent
```javascript
fetch('/agents/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    agent_type: 'custom_agent',
    agent_id: 'my_agent_001',
    config: { capability: 'analysis' }
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

#### AGInt Streaming
```javascript
const eventSource = new EventSource('/commands/agint/stream');
eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('AGInt Update:', data);
};
```

## Features

### Agent Management
- **Real-time Monitoring**: Live status updates for all agents
- **Agent Creation**: Dynamic agent deployment
- **Agent Control**: Start, stop, and configure agents
- **Performance Metrics**: Track agent performance and resource usage

### System Monitoring
- **Health Checks**: Continuous system health monitoring
- **Resource Usage**: CPU, memory, and disk usage tracking
- **Log Management**: Centralized logging with filtering
- **Performance Metrics**: Response time and throughput monitoring

### Command Interface
- **Direct Execution**: Execute commands directly through the UI
- **Command History**: Track and replay previous commands
- **Terminal Integration**: Built-in terminal interface
- **Security Controls**: Restricted command execution for safety

### Debug Tools
- **Debug Interface**: Advanced debugging capabilities
- **Log Streaming**: Real-time log monitoring
- **Error Tracking**: Comprehensive error reporting
- **System Analysis**: Deep system introspection

## Development

### Code Structure

#### **app.js** - Main Application Logic
- **Size**: 34,341+ tokens (very large)
- **Features**:
  - Tab management and navigation
  - Real-time data updates
  - API communication
  - UI state management
  - Event handling

#### **styles3.css** - Enhanced Styling
- **Theme**: Cyberpunk aesthetic
- **Features**:
  - Responsive design
  - Animation effects
  - Color schemes
  - Typography

#### **server.js** - Express Server
- **Port**: 3000 (configurable)
- **Features**:
  - Static file serving
  - CORS configuration
  - Error handling
  - Logging

### Customization

#### **Themes**
- **Cyberpunk**: Default neon theme
- **Corporate**: Professional business theme
- **Custom**: Easily extensible theme system

#### **Configuration**
- **Ports**: Configurable via environment variables
- **API Endpoints**: Centralized configuration
- **UI Elements**: Modular component system

## Troubleshooting

### Common Issues

#### **Port Conflicts**
```bash
# Check if port is in use
lsof -i :3000

# Kill process using port
kill -9 $(lsof -t -i:3000)
```

#### **Backend Connection Issues**
- Verify backend is running on port 8000
- Check CORS configuration
- Ensure API endpoints are accessible

#### **Dependency Issues**
```bash
# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Debug Mode

Enable debug mode for detailed logging:
```bash
DEBUG=true node server.js
```

## Security

### CORS Configuration
- Configurable allowed origins
- Credential support
- Method and header restrictions

### Command Execution
- Restricted command set for security
- Timeout protection
- Error handling and logging

### API Security
- Input validation
- Error handling
- Rate limiting (configurable)

## Performance

### Optimization Features
- **Lazy Loading**: Components loaded on demand
- **Caching**: API response caching
- **Compression**: Gzip compression enabled
- **Minification**: CSS and JS minification

### Monitoring
- **Response Times**: API call timing
- **Error Rates**: Error tracking and reporting
- **Resource Usage**: Memory and CPU monitoring
- **Throughput**: Request handling capacity

## Future Enhancements

### Planned Features
- **WebSocket Support**: Real-time bidirectional communication
- **Plugin System**: Extensible architecture
- **Advanced Analytics**: Detailed performance metrics
- **Multi-language Support**: Internationalization
- **Mobile Responsiveness**: Mobile-optimized interface

### Architecture Improvements
- **Component Framework**: Modern frontend framework integration
- **State Management**: Centralized state management
- **Testing Suite**: Comprehensive test coverage
- **Documentation**: Auto-generated API documentation

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Standards
- **JavaScript**: ES6+ features
- **CSS**: BEM methodology
- **HTML**: Semantic markup
- **Documentation**: JSDoc comments

## License

This project is part of the MindX Augmentic Intelligence system. See the main project license for details.

## Support

For issues and questions:
- Check the debug interface
- Review system logs
- Consult the API documentation
- Contact the development team

---

*Last updated: 2025-01-15*
*Version: 2.0.0*
