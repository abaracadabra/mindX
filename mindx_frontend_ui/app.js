document.addEventListener('DOMContentLoaded', () => {
    const backendPort = window.MINDX_BACKEND_PORT || '8000';
    const apiUrl = `http://localhost:${backendPort}`;
    
    // Initialize system start time for uptime calculation
    window.systemStartTime = new Date();
    
    // Initialize agent modal event listeners immediately
    const closeAgentModalBtn = document.getElementById('close-agent-modal');
    if (closeAgentModalBtn) {
        closeAgentModalBtn.addEventListener('click', closeAgentDetailsModal);
        console.log('Agent modal close button event listener added');
    } else {
        console.log('Agent modal close button not found');
    }
    
    // Close modal when clicking outside
    const agentModal = document.getElementById('agent-details-modal');
    if (agentModal) {
        agentModal.addEventListener('click', (e) => {
            if (e.target === agentModal) {
                closeAgentDetailsModal();
            }
        });
        console.log('Agent modal click outside event listener added');
    } else {
        console.log('Agent modal not found');
    }
    
    // Close modal when pressing Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('agent-details-modal');
            if (modal && modal.style.display === 'flex') {
                closeAgentDetailsModal();
            }
        }
    });
    
    // Load initial system data
    setTimeout(() => {
        updateAllSystemFields();
        updateMonitoringAgents();
        updateResourceFromSystemMetrics(); // Ensure resource monitor gets updated
        performSystemHealthCheck(); // Perform initial system health check
        startHealthCheckRefresh(); // Start periodic health check refresh
    }, 1000);
    
    // Global state
    let isAutonomousMode = false;
    let activityPaused = false;
    let activityLog = [];
    let seenActivities = new Set(); // Track activities we've already seen
    let autonomousInterval = null;
    let logs = [];
    let terminalHistory = [];
    let agents = [];
    let systemAgents = [];
    let userAgents = [];
    let selectedAgent = null;
    let currentAgentTab = 'system';
    let agintResponseWindow = null;
    
    // DOM elements
    const statusLight = document.getElementById('status-light');
    const autonomousToggle = document.getElementById('autonomous-mode');
    const responseOutput = document.getElementById('response-output');

    // Tab elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Control tab elements
    const evolveBtn = document.getElementById('evolve-btn');
    const queryBtn = document.getElementById('query-btn');
    const statusBtn = document.getElementById('status-btn');
    const agentsBtn = document.getElementById('agents-btn');
    const toolsBtn = document.getElementById('tools-btn');
    const replicateBtn = document.getElementById('replicate-btn');
    const evolveDirectiveInput = document.getElementById('evolve-directive');
    const queryInput = document.getElementById('query-input');

    // Agents tab elements
    const refreshAgentsBtn = document.getElementById('refresh-agents-btn');
    const createAgentBtn = document.getElementById('create-agent-btn');
    const deleteAgentBtn = document.getElementById('delete-agent-btn');
    const agentsList = document.getElementById('agents-list');
    const agentDetails = document.getElementById('agent-details');
    const agentTabBtns = document.querySelectorAll('.agent-tab-btn');
    
    // System tab elements
    const systemStatus = document.getElementById('system-status');
    const performanceMetrics = document.getElementById('performance-metrics');
    const resourceUsage = document.getElementById('resource-usage');
    
    // Logs tab elements
    const refreshLogsBtn = document.getElementById('refresh-logs-btn');
    const clearLogsBtn = document.getElementById('clear-logs-btn');
    const logLevelFilter = document.getElementById('log-level-filter');
    const copyLogsBtn = document.getElementById('copy-logs-btn');
    const logsOutput = document.getElementById('logs-output');
    
    // Terminal tab elements
    const refreshTerminalBtn = document.getElementById('refresh-terminal-btn');
    const clearTerminalBtn = document.getElementById('clear-terminal-btn');
    const executeCommandBtn = document.getElementById('execute-command-btn');
    const terminalOutput = document.getElementById('terminal-output');
    const terminalCommand = document.getElementById('terminal-command');
    const sendCommandBtn = document.getElementById('send-command-btn');

    // Admin tab elements
    const restartSystemBtn = document.getElementById('restart-system-btn');
    const backupSystemBtn = document.getElementById('backup-system-btn');
    const updateConfigBtn = document.getElementById('update-config-btn');
    const exportLogsBtn = document.getElementById('export-logs-btn');
    const configDisplay = document.getElementById('config-display');

    // Core Systems tab elements
    const bdiAgentStatus = document.getElementById('bdi-agent-status');
    const bdiGoals = document.getElementById('bdi-goals');
    const bdiPlans = document.getElementById('bdi-plans');
    const bdiLastAction = document.getElementById('bdi-last-action');
    const bdiGoalCount = document.getElementById('bdi-goal-count');
    const bdiStatusIndicator = document.getElementById('bdi-status-indicator');
    const beliefCount = document.getElementById('belief-count');
    const recentBeliefs = document.getElementById('recent-beliefs');
    const idManagerStatus = document.getElementById('id-manager-status');
    const activeIdentities = document.getElementById('active-identities');
    
    // Agent Activity Monitor elements
    const agentActivityLog = document.getElementById('agent-activity-log');
    const pauseActivityBtn = document.getElementById('pause-activity');
    const clearActivityBtn = document.getElementById('clear-activity');

    // Evolution tab elements
    const blueprintStatus = document.getElementById('blueprint-status');
    const currentBlueprint = document.getElementById('current-blueprint');
    const converterStatus = document.getElementById('converter-status');
    const recentConversions = document.getElementById('recent-conversions');
    const generateBlueprintBtn = document.getElementById('generate-blueprint-btn');
    const executeEvolutionBtn = document.getElementById('execute-evolution-btn');
    const analyzeSystemBtn = document.getElementById('analyze-system-btn');

    // Learning tab elements
    const seaStatus = document.getElementById('sea-status');
    const learningProgress = document.getElementById('learning-progress');
    const activeGoals = document.getElementById('active-goals');
    const completedGoals = document.getElementById('completed-goals');
    const currentPlans = document.getElementById('current-plans');
    const planExecution = document.getElementById('plan-execution');

    // Orchestration tab elements
    const mastermindStatus = document.getElementById('mastermind-status');
    const currentCampaign = document.getElementById('current-campaign');
    const coordinatorStatus = document.getElementById('coordinator-status');
    const activeInteractions = document.getElementById('active-interactions');
    const ceoStatus = document.getElementById('ceo-status');
    const strategicDecisions = document.getElementById('strategic-decisions');

    // Utility Functions
    function addLog(message, level = 'INFO') {
        const timestamp = new Date().toISOString();
        logs.unshift({ timestamp, level, message });
        
        // Keep only last 1000 logs
        if (logs.length > 1000) {
            logs = logs.slice(0, 1000);
        }
        
        updateLogsDisplay();
    }

    function showResponse(message) {
        responseOutput.textContent = message;
        // Track command activity to prevent health check refresh during active use
        window.lastCommandTime = Date.now();
    }

    function showQueryResult(response) {
        // Create query response window similar to AGInt response window
        const queryWindow = document.createElement('div');
        queryWindow.id = 'query-response-window';
        queryWindow.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            max-width: 900px;
            height: 70%;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            border: 2px solid #00a8ff;
            border-radius: 10px;
            box-shadow: 0 0 30px rgba(0, 168, 255, 0.3);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            font-family: 'Courier New', monospace;
            color: #00a8ff;
        `;
        
        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 15px;
            border-bottom: 1px solid #00a8ff;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(0, 168, 255, 0.1);
        `;
        header.innerHTML = `
            <h3 style="margin: 0; color: #00a8ff; text-shadow: 0 0 10px rgba(0, 168, 255, 0.5);">🤖 Query Coordinator Response</h3>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 12px; color: #888;">Mistral API</span>
                <button id="copy-query-output" style="background: linear-gradient(135deg, #00aa88, #008866); border: 1px solid #00aa88; color: white; padding: 8px 15px; cursor: pointer; border-radius: 5px; font-weight: bold; box-shadow: 0 2px 5px rgba(0, 170, 136, 0.3);">Copy Response</button>
                <button id="close-query-window" style="background: linear-gradient(135deg, #ff4444, #cc0000); border: 1px solid #ff4444; color: white; padding: 8px 15px; cursor: pointer; border-radius: 5px; font-weight: bold; box-shadow: 0 2px 5px rgba(255, 68, 68, 0.3);">Close</button>
            </div>
        `;
        
        // Content area
        const content = document.createElement('div');
        content.id = 'query-response-content';
        content.style.cssText = `
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.3);
            font-size: 14px;
            line-height: 1.4;
        `;
        
        // Format the response content
        const responseText = formatQueryResponse(response);
        const apiDetails = getApiDetails(response);
        
        content.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h4 style="color: #00ff88; margin-bottom: 10px; text-shadow: 0 0 5px rgba(0, 255, 136, 0.3);">📝 Query Response:</h4>
                <div style="background: rgba(0, 0, 0, 0.5); padding: 15px; border-radius: 5px; border-left: 3px solid #00ff88; white-space: pre-wrap; font-family: 'Courier New', monospace;">${responseText}</div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <h4 style="color: #00a8ff; margin-bottom: 10px; text-shadow: 0 0 5px rgba(0, 168, 255, 0.3);">🔧 API Details:</h4>
                <div style="background: rgba(0, 0, 0, 0.5); padding: 15px; border-radius: 5px; border-left: 3px solid #00a8ff;">
                    ${apiDetails}
                </div>
            </div>
            
            <div>
                <h4 style="color: #ff6b35; margin-bottom: 10px; text-shadow: 0 0 5px rgba(255, 107, 53, 0.3);">📊 Raw Response:</h4>
                <pre style="background: rgba(0, 0, 0, 0.5); padding: 15px; border-radius: 5px; border-left: 3px solid #ff6b35; overflow-x: auto; font-size: 12px;">${JSON.stringify(response, null, 2)}</pre>
            </div>
        `;
        
        queryWindow.appendChild(header);
        queryWindow.appendChild(content);
        document.body.appendChild(queryWindow);
        
        // Close button event
        const closeBtn = document.getElementById('close-query-window');
        closeBtn.addEventListener('click', function() {
            queryWindow.remove();
        });
        
        // Copy button event
        const copyBtn = document.getElementById('copy-query-output');
        copyBtn.addEventListener('click', function() {
            const text = responseText;
            navigator.clipboard.writeText(text).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                copyBtn.style.background = 'linear-gradient(135deg, #00ff00, #00cc00)';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.style.background = 'linear-gradient(135deg, #00aa88, #008866)';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                copyBtn.style.background = 'linear-gradient(135deg, #00ff00, #00cc00)';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.style.background = 'linear-gradient(135deg, #00aa88, #008866)';
                }, 2000);
            });
        });
    }

    function formatQueryResponse(response) {
        // Extract the actual response text from the coordinator response
        if (response.response && response.response.response_text) {
            return response.response.response_text;
        } else if (response.message) {
            return response.message;
        } else if (response.content) {
            return response.content;
        } else {
            return 'No response text available';
        }
    }

    function getApiDetails(response) {
        // Extract API details from the response
        let details = '';
        
        if (response.status) {
            details += `<div style="margin-bottom: 8px;"><strong>Status:</strong> ${response.status}</div>`;
        }
        if (response.interaction_id) {
            details += `<div style="margin-bottom: 8px;"><strong>Interaction ID:</strong> ${response.interaction_id}</div>`;
        }
        if (response.response && response.response.model_used) {
            details += `<div style="margin-bottom: 8px;"><strong>Model Used:</strong> ${response.response.model_used}</div>`;
        }
        if (response.response && response.response.tokens_used) {
            details += `<div style="margin-bottom: 8px;"><strong>Tokens Used:</strong> ${response.response.tokens_used}</div>`;
        }
        if (response.response && response.response.cost) {
            details += `<div style="margin-bottom: 8px;"><strong>Cost:</strong> ${response.response.cost}</div>`;
        }
        if (response.completed_at) {
            const date = new Date(response.completed_at * 1000);
            details += `<div style="margin-bottom: 8px;"><strong>Completed At:</strong> ${date.toLocaleString()}</div>`;
        }
        
        return details || '<div style="color: #888;">No API details available</div>';
    }

    function updateLogsDisplay() {
        const filterLevel = logLevelFilter.value.toUpperCase();
        const filteredLogs = logs.filter(log => 
            filterLevel === 'ALL' || log.level.toUpperCase() === filterLevel
        );
        
        logsOutput.innerHTML = filteredLogs.map(log => {
            const levelClass = `log-${log.level.toLowerCase()}`;
            return `<div class="${levelClass}">[${log.timestamp}] ${log.level}: ${log.message}</div>`;
        }).join('');
    }

    // System Monitoring
    let monitoringInterval = null;
    let isMonitoring = false;

    // Agent Activity Monitoring
    function addAgentActivity(agent, message, type = 'info') {
        if (activityPaused) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const activityEntry = {
            timestamp,
            agent,
            message,
            type
        };
        
        activityLog.unshift(activityEntry);
        if (activityLog.length > 50) activityLog.pop();
        
        updateActivityDisplay();
    }

    // Test Mistral API connectivity
    async function testMistralAPI() {
        addLog('Testing Mistral API connectivity...', 'INFO');
        addAgentActivity('Mistral API', 'Testing API connectivity', 'info');
        
        // Show loading state
        const testBtn = document.getElementById('test-mistral-btn');
        if (testBtn) {
            testBtn.disabled = true;
            testBtn.textContent = 'Testing...';
        }
        
        try {
            const response = await sendRequest('/test/mistral', 'POST', { 
                test: 'connectivity',
                message: 'Hello from MindX Control Panel'
            });
            
            if (response) {
                addLog(`Mistral API test successful: ${JSON.stringify(response)}`, 'SUCCESS');
                addAgentActivity('Mistral API', 'API connectivity test successful', 'success');
                
                // Parse and display the response in a more readable format
                let displayText = '';
                if (response.status) {
                    displayText += `Status: ${response.status}\n`;
                }
                if (response.message) {
                    displayText += `Message: ${response.message}\n`;
                }
                if (response.test_message) {
                    displayText += `Test Message: ${response.test_message}\n`;
                }
                if (response.response) {
                    displayText += `API Response: ${response.response}\n`;
                }
                if (response.timestamp) {
                    displayText += `Timestamp: ${new Date(response.timestamp * 1000).toLocaleString()}\n`;
                }
                
                displayText += '\nFull Response:\n' + JSON.stringify(response, null, 2);
                showResponse(displayText);
            }
        } catch (error) {
            addLog(`Mistral API test failed: ${error.message}`, 'ERROR');
            addAgentActivity('Mistral API', `API test failed: ${error.message}`, 'error');
            showResponse(`Mistral API test failed: ${error.message}`);
        } finally {
            // Reset button state
            if (testBtn) {
                testBtn.disabled = false;
                testBtn.textContent = 'Test Mistral API';
            }
        }
    }

    function updateActivityDisplay() {
        if (!agentActivityLog) return;
        
        agentActivityLog.innerHTML = activityLog.map(entry => {
            const typeClass = entry.type === 'error' ? 'error' : 
                             entry.type === 'success' ? 'success' : 
                             entry.type === 'warning' ? 'warning' : '';
            
            return `
                <div class="activity-entry ${typeClass}">
                    <span class="activity-timestamp">${entry.timestamp}</span>
                    <span class="activity-agent">[${entry.agent}]</span>
                    <span class="activity-message">${entry.message}</span>
                </div>
            `;
        }).join('');
    }

    function pauseActivity() {
        activityPaused = !activityPaused;
        pauseActivityBtn.textContent = activityPaused ? 'Resume' : 'Pause';
        pauseActivityBtn.style.background = activityPaused ? 
            'linear-gradient(135deg, var(--corp-orange), var(--corp-red))' : 
            'linear-gradient(135deg, var(--corp-purple), var(--corp-blue))';
    }

    function clearActivity() {
        activityLog = [];
        updateActivityDisplay();
    }

    // System Health Check Function
    async function performSystemHealthCheck() {
        try {
            const responseOutput = document.getElementById('response-output');
            if (!responseOutput) return;

            // Update status light to show connecting
            if (statusLight) {
                statusLight.className = 'status-light-yellow';
                statusLight.title = 'Connecting...';
            }

            // Show loading state
            responseOutput.textContent = 'Performing system health check...\n\n';

            let statusData = {};
            let metricsData = {};
            let resourcesData = {};

            // Fetch system status with error handling
            try {
                const statusResponse = await fetch(`${apiUrl}/system/status`);
                if (statusResponse.ok) {
                    statusData = await statusResponse.json();
                } else {
                    statusData = { error: `HTTP ${statusResponse.status}: ${statusResponse.statusText}` };
                }
            } catch (error) {
                statusData = { error: `Status endpoint failed: ${error.message}` };
            }

            // Fetch system metrics with error handling
            try {
                const metricsResponse = await fetch(`${apiUrl}/system/metrics`);
                if (metricsResponse.ok) {
                    metricsData = await metricsResponse.json();
                } else {
                    metricsData = { error: `HTTP ${metricsResponse.status}: ${metricsResponse.statusText}` };
                }
            } catch (error) {
                metricsData = { error: `Metrics endpoint failed: ${error.message}` };
            }

            // Fetch resource usage with error handling
            try {
                const resourcesResponse = await fetch(`${apiUrl}/system/resources`);
                if (resourcesResponse.ok) {
                    resourcesData = await resourcesResponse.json();
                } else {
                    resourcesData = { error: `HTTP ${resourcesResponse.status}: ${resourcesResponse.statusText}` };
                }
            } catch (error) {
                resourcesData = { error: `Resources endpoint failed: ${error.message}` };
            }

            // Format the health check response
            const healthCheckReport = formatSystemHealthCheck({
                status: statusData,
                metrics: metricsData,
                resources: resourcesData
            });

            responseOutput.textContent = healthCheckReport;

            // Update status light to show connected
            if (statusLight) {
                statusLight.className = 'status-light-green';
                statusLight.title = 'Connected';
            }

        } catch (error) {
            const responseOutput = document.getElementById('response-output');
            if (responseOutput) {
                responseOutput.textContent = `System Health Check Failed:\n\nError: ${error.message}\n\nPlease ensure the API server is running on port ${backendPort}`;
            }
            
            // Update status light to show disconnected
            if (statusLight) {
                statusLight.className = 'status-light-red';
                statusLight.title = 'Disconnected';
            }
            
            throw error; // Re-throw to be caught by the calling function
        }
    }

    // Format system health check response
    function formatSystemHealthCheck(data) {
        const timestamp = new Date().toLocaleString();
        const { status, metrics, resources } = data;

        let report = `SYSTEM HEALTH CHECK REPORT\n`;
        report += `Generated: ${timestamp}\n`;
        report += `==========================================\n\n`;

        // System Status
        report += `SYSTEM STATUS:\n`;
        if (status.error) {
            report += `❌ Status Check Failed: ${status.error}\n`;
        } else {
            report += `├─ Overall Status: ${status.status || 'Unknown'}\n`;
            if (status.components) {
                report += `├─ Components:\n`;
                Object.entries(status.components).forEach(([component, state]) => {
                    const statusIcon = state === 'online' ? '✅' : '❌';
                    report += `│  ├─ ${component}: ${statusIcon} ${state}\n`;
                });
            }
        }
        report += `\n`;

        // Performance Metrics
        report += `PERFORMANCE METRICS:\n`;
        if (metrics.error) {
            report += `❌ Metrics Check Failed: ${metrics.error}\n`;
        } else if (metrics) {
            report += `├─ Response Time: ${metrics.response_time || 'N/A'}ms\n`;
            report += `├─ Memory Usage: ${metrics.memory_usage || 'N/A'}%\n`;
            report += `├─ CPU Usage: ${metrics.cpu_usage || 'N/A'}%\n`;
            report += `├─ Disk Usage: ${metrics.disk_usage || 'N/A'}%\n`;
            report += `└─ Network I/O: ${metrics.network_usage || 'N/A'}%\n`;
        } else {
            report += `└─ No metrics available\n`;
        }
        report += `\n`;

        // Resource Usage
        report += `RESOURCE USAGE:\n`;
        if (resources.error) {
            report += `❌ Resources Check Failed: ${resources.error}\n`;
        } else if (resources) {
            if (resources.memory) {
                report += `├─ Memory:\n`;
                report += `│  ├─ Total: ${resources.memory.total || 'N/A'}\n`;
                report += `│  ├─ Used: ${resources.memory.used || 'N/A'}\n`;
                report += `│  └─ Free: ${resources.memory.free || 'N/A'}\n`;
            }
            if (resources.disk) {
                report += `├─ Disk:\n`;
                report += `│  ├─ Used: ${resources.disk.used || 'N/A'}\n`;
                report += `│  └─ Free: ${resources.disk.free || 'N/A'}\n`;
            }
            if (resources.cpu) {
                report += `└─ CPU:\n`;
                report += `   ├─ Cores: ${resources.cpu.cores || 'N/A'}\n`;
                report += `   └─ Load: ${resources.cpu.load_avg ? resources.cpu.load_avg.join(', ') : 'N/A'}\n`;
            }
        } else {
            report += `└─ No resource data available\n`;
        }
        report += `\n`;

        // System Health Summary
        report += `HEALTH SUMMARY:\n`;
        if (status.error || metrics.error || resources.error) {
            report += `⚠️ System Status: DEGRADED (API Issues Detected)\n`;
            report += `├─ API Connectivity: Issues detected\n`;
            report += `├─ System Status: ${status.error ? 'Failed' : 'Available'}\n`;
            report += `├─ Performance Metrics: ${metrics.error ? 'Failed' : 'Available'}\n`;
            report += `└─ Resource Usage: ${resources.error ? 'Failed' : 'Available'}\n`;
        } else {
            const overallStatus = status.status === 'operational' ? 'HEALTHY' : 'DEGRADED';
            const statusIcon = overallStatus === 'HEALTHY' ? '✅' : '⚠️';
            report += `${statusIcon} System Status: ${overallStatus}\n`;
            
            if (metrics) {
                const cpuStatus = (metrics.cpu_usage || 0) > 80 ? 'HIGH' : 'NORMAL';
                const memStatus = (metrics.memory_usage || 0) > 80 ? 'HIGH' : 'NORMAL';
                const diskStatus = (metrics.disk_usage || 0) > 90 ? 'HIGH' : 'NORMAL';
                
                report += `├─ CPU Usage: ${cpuStatus}\n`;
                report += `├─ Memory Usage: ${memStatus}\n`;
                report += `└─ Disk Usage: ${diskStatus}\n`;
            }
        }

        report += `\n==========================================\n`;
        report += `System monitoring active. Ready for commands.`;

        return report;
    }

    // Refresh system health check periodically
    function startHealthCheckRefresh() {
        // Refresh health check every 30 seconds
        setInterval(() => {
            // Only refresh if no recent activity (no commands executed recently)
            const lastActivity = window.lastCommandTime || 0;
            const timeSinceLastActivity = Date.now() - lastActivity;
            
            // If no activity for 30 seconds, refresh the health check
            if (timeSinceLastActivity > 30000) {
                performSystemHealthCheck();
            }
        }, 30000);
    }

    function addTerminalOutput(message) {
        const timestamp = new Date().toLocaleTimeString();
        terminalHistory.unshift(`[${timestamp}] ${message}`);
        
        // Keep only last 500 terminal entries
        if (terminalHistory.length > 500) {
            terminalHistory = terminalHistory.slice(0, 500);
        }
        
        updateTerminalDisplay();
    }

    function updateTerminalDisplay() {
        terminalOutput.textContent = terminalHistory.join('\n');
    }

    // API Functions
    async function sendRequest(endpoint, method = 'GET', body = null) {
        showResponse('Sending request...');
        addLog(`API Request: ${method} ${endpoint}`, 'INFO');
        
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' }
            };
            
            if (body && method !== 'GET') {
                options.body = JSON.stringify(body);
            }
            
            // Add timeout to prevent hanging
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            options.signal = controller.signal;
            
            const response = await fetch(`${apiUrl}${endpoint}`, options);
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                if (response.status === 503) {
                    throw new Error('Service temporarily unavailable. MindX may still be initializing.');
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            showResponse(JSON.stringify(result, null, 2));
            addLog(`API Response: ${method} ${endpoint} - Success`, 'INFO');
            return result;
        } catch (error) {
            let errorMsg;
            if (error.name === 'AbortError') {
                errorMsg = 'Error: Request timeout - Backend may be unavailable';
                addLog(`API Timeout: ${method} ${endpoint} - Backend not responding`, 'WARNING');
            } else {
                errorMsg = `Error: ${error.message}`;
                addLog(`API Error: ${method} ${endpoint} - ${error.message}`, 'ERROR');
            }
            showResponse(errorMsg);
            throw error;
        }
    }

    // Tab Management
    function initializeTabs() {
        // Ensure control tab is active by default
        const controlTab = document.getElementById('control-tab');
        const controlTabBtn = document.querySelector('[data-tab="control"]');
        
        console.log('Tab initialization:', {
            controlTab: !!controlTab,
            controlTabBtn: !!controlTabBtn,
            controlTabClasses: controlTab ? controlTab.className : 'No tab',
            controlTabBtnClasses: controlTabBtn ? controlTabBtn.className : 'No button'
        });
        
        if (controlTab && controlTabBtn) {
            controlTab.classList.add('active');
            controlTabBtn.classList.add('active');
            console.log('Control tab activated');
        } else {
            console.error('Control tab or button not found!');
        }
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.getAttribute('data-tab');
                
                // Remove active class from all tabs and contents
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding content
                btn.classList.add('active');
                document.getElementById(`${tabId}-tab`).classList.add('active');
                
                // Load tab-specific data
                loadTabData(tabId);
            });
        });
    }

    function loadTabData(tabId) {
        switch(tabId) {
            case 'control':
                // Control tab is already loaded
                console.log('Control tab loaded, refreshing update requests...');
                // Refresh update requests when control tab is shown
                setTimeout(() => {
                    loadUpdateRequests();
                }, 100);
                break;
            case 'core':
                loadCoreSystems();
                break;
            case 'evolution':
                loadEvolution();
                break;
            case 'learning':
                loadLearning();
                break;
            case 'orchestration':
                loadOrchestration();
                break;
            case 'agents':
                loadAgents();
                break;
            case 'system':
                loadSystemStatus();
                break;
            case 'logs':
                loadLogs();
                break;
            case 'terminal':
                loadTerminal();
                break;
            case 'admin':
                loadAdminData();
                break;
        }
    }

    // Control Tab Functions
    function initializeControlTab() {
        evolveBtn.addEventListener('click', async () => {
        const directive = evolveDirectiveInput.value.trim();
            if (!directive) {
                showResponse('Please enter a directive');
                return;
            }
            
            // Get cycle count and autonomous mode from controls
            const cycleCount = parseInt(document.getElementById('cycle-count').value) || 8;
            const autonomousMode = document.getElementById('evolve-autonomous-mode').checked;
            
            console.log('Cycle count from UI:', cycleCount);
            console.log('Autonomous mode from UI:', autonomousMode);
            
            addLog(`Starting AGInt cognitive loop with directive: ${directive}`, 'INFO');
            addAgentActivity('AGInt', `Starting cognitive loop: ${directive}`, 'info');
            
            // Show loading state
            evolveBtn.disabled = true;
            evolveBtn.textContent = 'Evolving...';
            
            // Show AGInt response window
            showAGIntResponseWindow();
            
            try {
                // Use AGInt streaming endpoint for real-time feedback
                const response = await fetch(`${apiUrl}/commands/agint/stream`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        directive, 
                        max_cycles: cycleCount,
                        autonomous_mode: autonomousMode
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let agintOutput = '';
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                updateAGIntResponse(data, agintOutput);
                                
                                if (data.type === 'cycle_start') {
                                    addAgentActivity('AGInt', `🔄 Starting cycle ${data.cycle}/${data.max_cycles}`, 'info');
                                } else if (data.type === 'status') {
                                    addAgentActivity('AGInt', data.message, 'info');
                                } else if (data.type === 'cycle_complete') {
                                    addAgentActivity('AGInt', `✅ Completed cycle ${data.cycle}/${data.max_cycles}`, 'success');
                                } else if (data.type === 'verbose') {
                                    addAgentActivity('AGInt', `${data.message}`, 'info');
                                    if (data.details) {
                                        addAgentActivity('AGInt', `  └─ ${data.details}`, 'info');
                                    }
                                } else if (data.type === 'action_detail') {
                                    addAgentActivity('AGInt', `🎯 ACTION DETAIL: ${data.action_type}`, 'info');
                                    if (data.details && Object.keys(data.details).length > 0) {
                                        addAgentActivity('AGInt', `  └─ Details: ${JSON.stringify(data.details)}`, 'info');
                                    }
                                    if (data.result && Object.keys(data.result).length > 0) {
                                        addAgentActivity('AGInt', `  └─ Result: ${JSON.stringify(data.result)}`, 'info');
                                    }
                                    addAgentActivity('AGInt', `  └─ Success: ${data.success ? '✅' : '❌'}`, data.success ? 'success' : 'error');
                                } else if (data.type === 'phase') {
                                    addAgentActivity('AGInt', `${data.phase}: ${data.message}`, 'info');
                                } else if (data.type === 'cycle') {
                                    addAgentActivity('AGInt', `Cycle ${data.cycle}: ${data.awareness}`, 'info');
                                    if (data.last_action) {
                                        addAgentActivity('AGInt', `Last Action: ${JSON.stringify(data.last_action)}`, 'info');
                                    }
                                } else if (data.type === 'complete') {
                                    addLog(`AGInt completed: ${JSON.stringify(data)}`, 'SUCCESS');
                                    addAgentActivity('AGInt', 'Cognitive loop completed successfully', 'success');
                                    
                                    // Update core systems after AGInt execution
                                    await loadCoreSystems();
                                } else if (data.type === 'error') {
                                    addLog(`AGInt failed: ${data.message}`, 'ERROR');
                                    addAgentActivity('AGInt', `Cognitive loop failed: ${data.message}`, 'error');
                                    showResponse(`AGInt failed: ${data.message}`);
                                }
                            } catch (e) {
                                console.error('Error parsing AGInt stream data:', e);
                            }
                        }
                    }
                }
                
            } catch (error) {
                addLog(`AGInt failed: ${error.message}`, 'ERROR');
                addAgentActivity('AGInt', `Cognitive loop failed: ${error.message}`, 'error');
                showResponse(`AGInt failed: ${error.message}`);
            } finally {
                // Reset button state
                evolveBtn.disabled = false;
                evolveBtn.textContent = 'Evolve Codebase';
                // Don't auto-close the window - let user close manually
            }
        });

        // Add Enter key functionality to evolve directive textarea
        evolveDirectiveInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault(); // Prevent new line in textarea
                evolveBtn.click(); // Trigger the evolve button click
            }
        });

        queryBtn.addEventListener('click', async () => {
            const query = queryInput.value.trim();
            if (!query) {
                showResponse('Please enter a query');
                return;
            }
            
            addLog(`Processing query: ${query}`, 'INFO');
            addAgentActivity('Coordinator Agent', `Processing query: ${query}`, 'info');
            
            // Show loading state
            queryBtn.disabled = true;
            queryBtn.textContent = 'Processing...';
            
            try {
                const response = await sendRequest('/coordinator/query', 'POST', { query });
                if (response) {
                    addLog(`Query processed: ${JSON.stringify(response)}`, 'SUCCESS');
                    addAgentActivity('Coordinator Agent', 'Query processed successfully', 'success');
                    
                    // Show query result in a popup window similar to evolve popup
                    showQueryResult(response);
                }
            } catch (error) {
                addLog(`Query failed: ${error.message}`, 'ERROR');
                addAgentActivity('Coordinator Agent', `Query failed: ${error.message}`, 'error');
                showResponse(`Query failed: ${error.message}`);
            } finally {
                // Reset button state
                queryBtn.disabled = false;
                queryBtn.textContent = 'Query';
            }
        });

        // Add Enter key functionality to query input field
        queryInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent form submission
                queryBtn.click(); // Trigger the query button click
            }
        });

        // Section tab switching functionality
        const sectionTabs = document.querySelectorAll('.section-tab');
        const sectionContents = document.querySelectorAll('.section-content');
        
        sectionTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetSection = tab.getAttribute('data-section');
                
                // Remove active class from all tabs and contents
                sectionTabs.forEach(t => t.classList.remove('active'));
                sectionContents.forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding content
                tab.classList.add('active');
                const targetContent = document.getElementById(`${targetSection}-section`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });

        statusBtn.addEventListener('click', async () => {
            addLog('Performing system health check...', 'INFO');
            addAgentActivity('System', 'Performing comprehensive system health check', 'info');
            
            try {
                // Use the existing system health check function
                await performSystemHealthCheck();
                addLog('System health check completed successfully', 'SUCCESS');
                addAgentActivity('System', 'System health check completed successfully', 'success');
            } catch (error) {
                addLog(`System health check failed: ${error.message}`, 'ERROR');
                addAgentActivity('System', `System health check failed: ${error.message}`, 'error');
                showResponse(`System Health Check Failed:\n\nError: ${error.message}\n\nPlease ensure the API server is running on port ${backendPort}`);
            }
        });

        agentsBtn.addEventListener('click', async () => {
            addLog('Fetching agents list...', 'INFO');
            addAgentActivity('Agent Registry', 'Fetching agents list', 'info');
            
            try {
                const response = await sendRequest('/agents/');
                if (response && response.agents) {
                    addLog(`Agents retrieved: ${response.total_agents} total agents`, 'SUCCESS');
                    addAgentActivity('Agent Registry', `Retrieved ${response.total_agents} agents (${response.file_agents} file agents, ${response.system_agents} system agents)`, 'success');
                    
                    // Format the response nicely
                    let formattedResponse = `AGENTS LIST\n`;
                    formattedResponse += `===========\n\n`;
                    formattedResponse += `Total Agents: ${response.total_agents}\n`;
                    formattedResponse += `File Agents: ${response.file_agents}\n`;
                    formattedResponse += `System Agents: ${response.system_agents}\n\n`;
                    
                    // Group agents by type
                    const fileAgents = response.agents.filter(a => a.type === 'file_agent');
                    const systemAgents = response.agents.filter(a => a.type === 'system_agent');
                    
                    if (fileAgents.length > 0) {
                        formattedResponse += `FILE-BASED AGENTS:\n`;
                        formattedResponse += `------------------\n`;
                        fileAgents.forEach(agent => {
                            formattedResponse += `• ${agent.name}`;
                            if (agent.class_name) {
                                formattedResponse += ` (${agent.class_name})`;
                            }
                            formattedResponse += `\n  File: ${agent.file}\n`;
                            formattedResponse += `  Description: ${agent.description}\n`;
                            formattedResponse += `  Status: ${agent.status}\n\n`;
                        });
                    }
                    
                    if (systemAgents.length > 0) {
                        formattedResponse += `SYSTEM AGENTS:\n`;
                        formattedResponse += `--------------\n`;
                        systemAgents.forEach(agent => {
                            formattedResponse += `• ${agent.name}\n`;
                            formattedResponse += `  Description: ${agent.description}\n`;
                            formattedResponse += `  Status: ${agent.status}\n\n`;
                        });
                    }
                    
                    showResponse(formattedResponse);
                } else {
                    addLog('No agents found', 'WARNING');
                    addAgentActivity('Agent Registry', 'No agents found', 'warning');
                    showResponse('No agents found');
                }
            } catch (error) {
                addLog(`Agents list failed: ${error.message}`, 'ERROR');
                addAgentActivity('Agent Registry', `Agents list failed: ${error.message}`, 'error');
                showResponse(`Agents list failed: ${error.message}`);
            }
        });

        toolsBtn.addEventListener('click', async () => {
            addLog('Fetching system tools...', 'INFO');
            addAgentActivity('System Tools', 'Fetching tools list', 'info');
            
            try {
                // Since there's no tools endpoint, we'll show available system commands
                const toolsResponse = {
                    "available_tools": [
                        {
                            "name": "System Status Check",
                            "endpoint": "/system/status",
                            "description": "Check overall system status and health"
                        },
                        {
                            "name": "System Metrics",
                            "endpoint": "/system/metrics", 
                            "description": "Get performance metrics and statistics"
                        },
                        {
                            "name": "Resource Usage",
                            "endpoint": "/system/resources",
                            "description": "Monitor CPU, memory, and disk usage"
                        },
                        {
                            "name": "System Logs",
                            "endpoint": "/system/logs",
                            "description": "Access system logs and debugging information"
                        },
                        {
                            "name": "Execute Commands",
                            "endpoint": "/system/execute-command",
                            "description": "Execute system commands like mindX.sh scripts"
                        },
                        {
                            "name": "Performance Agent",
                            "endpoint": "/system/performance-agent",
                            "description": "Get performance monitoring agent data"
                        },
                        {
                            "name": "Resource Agent", 
                            "endpoint": "/system/resource-agent",
                            "description": "Get resource monitoring agent data"
                        }
                    ],
                    "total_tools": 7,
                    "status": "active"
                };
                
                addLog(`Tools retrieved: ${JSON.stringify(toolsResponse)}`, 'SUCCESS');
                addAgentActivity('System Tools', 'Tools list retrieved successfully', 'success');
                showResponse(JSON.stringify(toolsResponse, null, 2));
            } catch (error) {
                addLog(`Tools list failed: ${error.message}`, 'ERROR');
                addAgentActivity('System Tools', `Tools list failed: ${error.message}`, 'error');
                showResponse(`Tools list failed: ${error.message}`);
            }
        });

        analyzeBtn.addEventListener('click', async () => {
            const path = prompt('Enter codebase path to analyze:', './');
            if (path) {
                try {
                    addLog('Analyzing codebase...', 'INFO');
                    addAgentActivity('Code Analysis', 'Starting codebase analysis', 'info');
                    
                    const response = await sendRequest('/system/analyze_codebase', 'POST', { path, focus: 'general' });
                    if (response) {
                        addLog(`Analysis completed: ${JSON.stringify(response)}`, 'SUCCESS');
                        addAgentActivity('Code Analysis', 'Analysis completed successfully', 'success');
                        showResponse(JSON.stringify(response, null, 2));
                    }
                } catch (error) {
                    addLog(`Analysis failed: ${error.message}`, 'ERROR');
                    addAgentActivity('Code Analysis', `Analysis failed: ${error.message}`, 'error');
                    showResponse(`Analysis failed: ${error.message}`);
                }
            }
        });

        replicateBtn.addEventListener('click', async () => {
            try {
                addLog('Triggering replication process...', 'INFO');
                addAgentActivity('System', 'Starting replication process', 'info');
                
                // Show loading state
                const originalText = replicateBtn.textContent;
                replicateBtn.textContent = 'Replicating...';
                replicateBtn.disabled = true;
                
                // Execute mindX.sh --replicate
                const response = await fetch(`${apiUrl}/system/execute-command`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        command: './mindX.sh --replicate',
                        working_directory: '/home/hacker/mindX'
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    addLog('Replication process started successfully', 'SUCCESS');
                    addAgentActivity('System', 'Replication process initiated', 'success');
                    showResponse(`Replication Process Started:\n\n${result.output || 'Process initiated successfully'}`);
                } else {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to start replication');
                }
                
            } catch (error) {
                addLog(`Replication failed: ${error.message}`, 'ERROR');
                addAgentActivity('System', `Replication failed: ${error.message}`, 'error');
                showResponse(`Replication Failed:\n\nError: ${error.message}`);
            } finally {
                // Restore button state
                replicateBtn.textContent = originalText;
                replicateBtn.disabled = false;
            }
        });

        improveBtn.addEventListener('click', async () => {
            addLog('Requesting system improvement...', 'INFO');
            addAgentActivity('Improvement System', 'Requesting system improvement', 'info');
            
            try {
                const response = await sendRequest('/coordinator/improve', 'POST', { component_id: 'system', context: 'general improvement' });
                if (response) {
                    addLog(`Improvement completed: ${JSON.stringify(response)}`, 'SUCCESS');
                    addAgentActivity('Improvement System', 'System improvement completed', 'success');
                    showResponse(JSON.stringify(response, null, 2));
                }
            } catch (error) {
                addLog(`Improvement request failed: ${error.message}`, 'ERROR');
                addAgentActivity('Improvement System', `Improvement failed: ${error.message}`, 'error');
                showResponse(`Improvement request failed: ${error.message}`);
            }
        });

        // Add Mistral API test button event listener
        const testMistralBtn = document.getElementById('test-mistral-btn');
        if (testMistralBtn) {
            testMistralBtn.addEventListener('click', testMistralAPI);
        }
    }

    // Agents Tab Functions
    function initializeAgentsTab() {
        refreshAgentsBtn.addEventListener('click', loadAgents);
        createAgentBtn.addEventListener('click', createAgent);
        deleteAgentBtn.addEventListener('click', deleteAgent);
        
        // Initialize agent tab switching
        agentTabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabType = btn.getAttribute('data-agent-tab');
                switchAgentTab(tabType);
            });
        });
        
        // Initialize agent details modal
        const closeAgentModalBtn = document.getElementById('close-agent-modal');
        if (closeAgentModalBtn) {
            closeAgentModalBtn.addEventListener('click', closeAgentDetailsModal);
        }
        
        // Close modal when clicking outside
        const agentModal = document.getElementById('agent-details-modal');
        if (agentModal) {
            agentModal.addEventListener('click', (e) => {
                if (e.target === agentModal) {
                    closeAgentDetailsModal();
                }
            });
        }
        
        // Initial display
        displayAgents();
    }
    
    function switchAgentTab(tabType) {
        currentAgentTab = tabType;
        
        // Update tab button states
        agentTabBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-agent-tab') === tabType) {
                btn.classList.add('active');
            }
        });
        
        // Update agents list based on tab
        displayAgents();
    }

    async function loadAgents() {
        try {
            const result = await sendRequest('/registry/agents');
            agents = result.agents || [];
            displayAgents();
        } catch (error) {
            addLog(`Failed to load agents: ${error.message}`, 'ERROR');
            agents = [];
            displayAgents();
        }
    }

    // Core Systems functions
    async function loadCoreSystems() {
        try {
            addAgentActivity('Core Systems', 'Loading BDI Agent status...', 'info');
            // Load BDI Agent status
            const bdiResponse = await sendRequest('/core/bdi-status');
            if (bdiResponse) {
                bdiAgentStatus.textContent = bdiResponse.status || 'Unknown';
                
                // Update status indicator
                if (bdiStatusIndicator) {
                    bdiStatusIndicator.className = 'status-indicator ' + 
                        (bdiResponse.status === 'active' ? 'active' : 'inactive');
                }
                
                // Update goal count
                if (bdiGoalCount && bdiResponse.goals) {
                    bdiGoalCount.textContent = bdiResponse.goals.length;
                }
                
                // Update last action
                if (bdiLastAction) {
                    bdiLastAction.textContent = bdiResponse.lastAction || 'None';
                }
                
                // Update chosen agent
                const bdiChosenAgent = document.getElementById('bdi-chosen-agent');
                if (bdiChosenAgent) {
                    bdiChosenAgent.textContent = bdiResponse.chosen_agent || 'None';
                }
                
                       // Update last directive
                       const bdiLastDirective = document.getElementById('bdi-last-directive');
                       if (bdiLastDirective) {
                           bdiLastDirective.textContent = bdiResponse.last_directive || 'None';
                       }
                       
                       // Update last updated
                       const bdiLastUpdated = document.getElementById('bdi-last-updated');
                       if (bdiLastUpdated) {
                           bdiLastUpdated.textContent = bdiResponse.last_updated || 'Never';
                       }
                       
                       // Update total decisions
                       const bdiTotalDecisions = document.getElementById('bdi-total-decisions');
                       if (bdiTotalDecisions) {
                           bdiTotalDecisions.textContent = bdiResponse.performance_metrics?.total_decisions || '0';
                       }
                       
                       // Update performance metrics
                       const bdiSuccessRate = document.getElementById('bdi-success-rate');
                       if (bdiSuccessRate && bdiResponse.performance_metrics) {
                           bdiSuccessRate.textContent = `${bdiResponse.performance_metrics.success_rate || 0}%`;
                       }
                       
                       const bdiAvgTime = document.getElementById('bdi-avg-time');
                       if (bdiAvgTime && bdiResponse.performance_metrics) {
                           bdiAvgTime.textContent = bdiResponse.performance_metrics.avg_decision_time || '0s';
                       }
                       
                       const bdiPreferredAgent = document.getElementById('bdi-preferred-agent');
                       if (bdiPreferredAgent && bdiResponse.performance_metrics) {
                           bdiPreferredAgent.textContent = bdiResponse.performance_metrics.preferred_agent || 'None';
                       }
                       
                       // Update system health
                       const bdiAgentHealth = document.getElementById('bdi-agent-health');
                       if (bdiAgentHealth && bdiResponse.system_health) {
                           bdiAgentHealth.textContent = bdiResponse.system_health.bdi_agent || 'Unknown';
                           bdiAgentHealth.className = `health-value ${bdiResponse.system_health.bdi_agent || 'unknown'}`;
                       }
                       
                       const bdiReasoningHealth = document.getElementById('bdi-reasoning-health');
                       if (bdiReasoningHealth && bdiResponse.system_health) {
                           bdiReasoningHealth.textContent = bdiResponse.system_health.reasoning_engine || 'Unknown';
                           bdiReasoningHealth.className = `health-value ${bdiResponse.system_health.reasoning_engine || 'unknown'}`;
                       }
                
                       // Update BDI beliefs
                       const bdiBeliefs = document.getElementById('bdi-beliefs');
                       if (bdiBeliefs && bdiResponse.beliefs) {
                           bdiBeliefs.innerHTML = bdiResponse.beliefs.map(belief => 
                               `<div class="reasoning-item">${belief}</div>`
                           ).join('');
                       }
                       
                       // Update BDI desires
                       const bdiDesires = document.getElementById('bdi-desires');
                       if (bdiDesires && bdiResponse.desires) {
                           bdiDesires.innerHTML = bdiResponse.desires.map(desire => 
                               `<div class="reasoning-item">${desire}</div>`
                           ).join('');
                       }
                       
                       // Update BDI intentions
                       const bdiIntentions = document.getElementById('bdi-intentions');
                       if (bdiIntentions && bdiResponse.intentions) {
                           bdiIntentions.innerHTML = bdiResponse.intentions.map(intention => 
                               `<div class="reasoning-item">${intention}</div>`
                           ).join('');
                       }
                       
                       // Update reasoning history
                       const bdiReasoningHistory = document.getElementById('bdi-reasoning-history');
                       if (bdiReasoningHistory && bdiResponse.reasoning_history) {
                           bdiReasoningHistory.innerHTML = bdiResponse.reasoning_history.map(reasoning => 
                               `<div class="history-item">${reasoning}</div>`
                           ).join('');
                       }
                
                if (bdiResponse.goals) {
                    bdiGoals.innerHTML = bdiResponse.goals.map(goal => 
                        `<div class="objective-item">${goal.description || goal}</div>`
                    ).join('');
                }
                if (bdiResponse.plans) {
                    bdiPlans.innerHTML = bdiResponse.plans.map(plan => 
                        `<div class="objective-item">${plan.description || plan}</div>`
                    ).join('');
                }
                addAgentActivity('BDI Agent', `Status: ${bdiResponse.status}`, 'success');
            }

            // Load Belief System
            const beliefResponse = await sendRequest('/core/beliefs');
            if (beliefResponse) {
                beliefCount.textContent = beliefResponse.count || '0';
                if (beliefResponse.recent) {
                    recentBeliefs.innerHTML = beliefResponse.recent.map(belief => 
                        `<div class="belief-item">${belief.content || belief}</div>`
                    ).join('');
                }
            }

            // Load ID Manager
            const idResponse = await sendRequest('/core/id-manager');
            if (idResponse) {
                idManagerStatus.textContent = idResponse.status || 'Unknown';
                if (idResponse.identities) {
                    activeIdentities.innerHTML = idResponse.identities.map(identity => 
                        `<div class="identity-item">${identity.name || identity}</div>`
                    ).join('');
                }
            }
            
            // Start real-time BDI monitoring
            startBDIMonitoring();
        } catch (error) {
            addLog(`Failed to load core systems: ${error.message}`, 'ERROR');
        }
    }

    // Real-time BDI monitoring
    let bdiMonitoringInterval = null;
    
    function startBDIMonitoring() {
        if (bdiMonitoringInterval) return;
        
        console.log('Starting real-time BDI monitoring...');
        addAgentActivity('BDI Agent', 'Starting real-time monitoring...', 'info');
        
        // Initial load
        updateBDIRealtime();
        
        // Poll every 2 seconds for real-time updates
        bdiMonitoringInterval = setInterval(async () => {
            try {
                await updateBDIRealtime();
            } catch (error) {
                console.error('Error in BDI monitoring:', error);
            }
        }, 2000);
    }
    
    function stopBDIMonitoring() {
        if (bdiMonitoringInterval) {
            clearInterval(bdiMonitoringInterval);
            bdiMonitoringInterval = null;
            console.log('Stopped BDI monitoring');
            addAgentActivity('BDI Agent', 'Stopped real-time monitoring', 'info');
        }
    }
    
    async function updateBDIRealtime() {
        try {
            const response = await sendRequest('/core/bdi-realtime');
            if (response) {
                updateBDIRealtimeDisplay(response);
            }
        } catch (error) {
            console.error('Error fetching real-time BDI data:', error);
        }
    }
    
    function updateBDIRealtimeDisplay(data) {
        // Update status indicators
        const statusElement = document.getElementById('bdi-agent-status');
        const statusIndicator = document.getElementById('bdi-status-indicator');
        
        if (statusElement) {
            statusElement.textContent = data.status || 'Unknown';
            statusElement.className = `status-text ${data.status || 'unknown'}`;
        }
        
        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${data.status || 'unknown'}`;
        }
        
        // Update current directive
        const directiveElement = document.getElementById('bdi-last-directive');
        if (directiveElement) {
            directiveElement.textContent = data.current_directive || 'None';
        }
        
        // Update chosen agent
        const agentElement = document.getElementById('bdi-chosen-agent');
        if (agentElement) {
            agentElement.textContent = data.chosen_agent || 'None';
        }
        
        // Update last updated time
        const lastUpdatedElement = document.getElementById('bdi-last-updated');
        if (lastUpdatedElement) {
            lastUpdatedElement.textContent = data.last_updated || 'Never';
        }
        
        // Update performance metrics
        if (data.performance_metrics) {
            const totalDecisionsElement = document.getElementById('bdi-total-decisions');
            if (totalDecisionsElement) {
                totalDecisionsElement.textContent = data.performance_metrics.total_decisions || '0';
            }
            
            const successRateElement = document.getElementById('bdi-success-rate');
            if (successRateElement) {
                successRateElement.textContent = `${data.performance_metrics.success_rate || 0}%`;
            }
            
            const avgTimeElement = document.getElementById('bdi-avg-time');
            if (avgTimeElement) {
                avgTimeElement.textContent = data.performance_metrics.avg_decision_time || '0s';
            }
            
            const preferredAgentElement = document.getElementById('bdi-preferred-agent');
            if (preferredAgentElement) {
                preferredAgentElement.textContent = data.performance_metrics.preferred_agent || 'None';
            }
        }
        
        // Update system health
        if (data.system_health) {
            const agentHealthElement = document.getElementById('bdi-agent-health');
            if (agentHealthElement) {
                agentHealthElement.textContent = data.system_health.bdi_agent || 'Unknown';
                agentHealthElement.className = `health-value ${data.system_health.bdi_agent || 'unknown'}`;
            }
            
            const reasoningHealthElement = document.getElementById('bdi-reasoning-health');
            if (reasoningHealthElement) {
                reasoningHealthElement.textContent = data.system_health.reasoning_engine || 'Unknown';
                reasoningHealthElement.className = `health-value ${data.system_health.reasoning_engine || 'unknown'}`;
            }
            
            const logHealthElement = document.getElementById('bdi-log-health');
            if (logHealthElement) {
                logHealthElement.textContent = data.system_health.log_system || 'Unknown';
                logHealthElement.className = `health-value ${data.system_health.log_system || 'unknown'}`;
            }
            
            const registryHealthElement = document.getElementById('bdi-registry-health');
            if (registryHealthElement) {
                registryHealthElement.textContent = data.system_health.agent_registry || 'Unknown';
                registryHealthElement.className = `health-value ${data.system_health.agent_registry || 'unknown'}`;
            }
        }
        
        // Update latest reasoning if available
        if (data.latest_reasoning) {
            const historyElement = document.getElementById('bdi-reasoning-history');
            if (historyElement) {
                const reasoningItem = document.createElement('div');
                reasoningItem.className = 'history-item';
                reasoningItem.innerHTML = `
                    <div class="reasoning-timestamp">${data.latest_reasoning.timestamp}</div>
                    <div class="reasoning-content">${data.latest_reasoning.reasoning}</div>
                `;
                
                // Add to top of history
                historyElement.insertBefore(reasoningItem, historyElement.firstChild);
                
                // Keep only last 5 items
                const items = historyElement.querySelectorAll('.history-item');
                if (items.length > 5) {
                    items[items.length - 1].remove();
                }
            }
        }
    }

    // Evolution functions
    async function loadEvolution() {
        try {
            // Load Blueprint Agent
            const blueprintResponse = await sendRequest('/evolution/blueprint');
            if (blueprintResponse) {
                blueprintStatus.textContent = blueprintResponse.status || 'Unknown';
                if (blueprintResponse.current) {
                    currentBlueprint.innerHTML = `<pre>${JSON.stringify(blueprintResponse.current, null, 2)}</pre>`;
                }
            }

            // Load Action Converter
            const converterResponse = await sendRequest('/evolution/converter');
            if (converterResponse) {
                converterStatus.textContent = converterResponse.status || 'Unknown';
                if (converterResponse.recent) {
                    recentConversions.innerHTML = converterResponse.recent.map(conversion => 
                        `<div class="conversion-item">${conversion.description || conversion}</div>`
                    ).join('');
                }
            }
        } catch (error) {
            addLog(`Failed to load evolution data: ${error.message}`, 'ERROR');
        }
    }

    // Learning functions
    async function loadLearning() {
        try {
            // Load Strategic Evolution Agent
            const seaResponse = await sendRequest('/learning/sea');
            if (seaResponse) {
                seaStatus.textContent = seaResponse.status || 'Unknown';
                if (seaResponse.progress) {
                    learningProgress.innerHTML = `<div class="progress-bar-fill" style="width: ${seaResponse.progress}%"></div>`;
                }
            }

            // Load Goals
            const goalsResponse = await sendRequest('/learning/goals');
            if (goalsResponse) {
                if (goalsResponse.active) {
                    activeGoals.innerHTML = goalsResponse.active.map(goal => 
                        `<div class="goal-item">${goal.description || goal}</div>`
                    ).join('');
                }
                if (goalsResponse.completed) {
                    completedGoals.innerHTML = goalsResponse.completed.map(goal => 
                        `<div class="goal-item completed">${goal.description || goal}</div>`
                    ).join('');
                }
            }

            // Load Plans
            const plansResponse = await sendRequest('/learning/plans');
            if (plansResponse) {
                if (plansResponse.current) {
                    currentPlans.innerHTML = plansResponse.current.map(plan => 
                        `<div class="plan-item">${plan.description || plan}</div>`
                    ).join('');
                }
                if (plansResponse.execution) {
                    planExecution.innerHTML = `<div class="execution-status">${plansResponse.execution.status || 'Unknown'}</div>`;
                }
            }
        } catch (error) {
            addLog(`Failed to load learning data: ${error.message}`, 'ERROR');
        }
    }

    // Orchestration functions
    async function loadOrchestration() {
        try {
            // Load Mastermind Agent
            const mastermindResponse = await sendRequest('/orchestration/mastermind');
            if (mastermindResponse) {
                mastermindStatus.textContent = mastermindResponse.status || 'Unknown';
                if (mastermindResponse.campaign) {
                    currentCampaign.innerHTML = `<div class="campaign-info">${mastermindResponse.campaign.description || mastermindResponse.campaign}</div>`;
                }
            }

            // Load Coordinator Agent
            const coordinatorResponse = await sendRequest('/orchestration/coordinator');
            if (coordinatorResponse) {
                coordinatorStatus.textContent = coordinatorResponse.status || 'Unknown';
                if (coordinatorResponse.interactions) {
                    activeInteractions.innerHTML = coordinatorResponse.interactions.map(interaction => 
                        `<div class="interaction-item">${interaction.description || interaction}</div>`
                    ).join('');
                }
            }

            // Load CEO Agent
            const ceoResponse = await sendRequest('/orchestration/ceo');
            if (ceoResponse) {
                ceoStatus.textContent = ceoResponse.status || 'Unknown';
                if (ceoResponse.decisions) {
                    strategicDecisions.innerHTML = ceoResponse.decisions.map(decision => 
                        `<div class="decision-item">${decision.description || decision}</div>`
                    ).join('');
                }
            }
        } catch (error) {
            addLog(`Failed to load orchestration data: ${error.message}`, 'ERROR');
        }
    }

    function displayAgents() {
        let agentsToShow = [];
        
        // Debug: Log system agents count
        console.log('System agents count:', systemAgents.length);
        console.log('System agents:', systemAgents.map(a => a.name));
        console.log('*** UPDATED AGENT LIST LOADED ***');
        
        // Filter agents based on current tab
        switch (currentAgentTab) {
            case 'system':
                agentsToShow = systemAgents;
                break;
            case 'user':
                agentsToShow = userAgents;
                break;
            case 'all':
                agentsToShow = [...systemAgents, ...userAgents];
                break;
            default:
                agentsToShow = agents;
        }
        
        if (agentsToShow.length === 0) {
            agentsList.innerHTML = `<p>No ${currentAgentTab} agents available</p>`;
            return;
        }
        
        // Add debug info to the UI
        const debugInfo = document.createElement('div');
        debugInfo.style.cssText = 'background: #ff6b6b; color: white; padding: 10px; margin: 10px 0; border-radius: 5px; font-weight: bold;';
        debugInfo.innerHTML = `DEBUG: Showing ${agentsToShow.length} agents (Updated: ${new Date().toLocaleTimeString()})`;
        agentsList.appendChild(debugInfo);

        agentsList.innerHTML = agentsToShow.map((agent, index) => {
            const agentId = agent.id || agent.name || `Agent ${index}`;
            const agentType = agent.type || 'Unknown';
            const isSelected = selectedAgent === agentId ? 'selected' : '';
            const statusClass = agent.status === 'active' ? 'active' : 'inactive';
            const systemBadge = agent.isSystem ? '<span class="system-agent-badge">SYSTEM</span>' : '';
            const canDelete = !agent.isSystem && agent.createdBy !== 'system';
            
            return `
                <div class="agent-item ${isSelected}" data-agent-id="${agentId}">
                    <div class="agent-info">
                        <div class="agent-name">
                            ${agent.name || agentId}
                            ${systemBadge}
                        </div>
                        <div class="agent-type">${agentType}</div>
                        <div class="agent-status ${statusClass}">${agent.status || 'Unknown'}</div>
                    </div>
                    <div class="agent-actions">
                        ${canDelete ? `<button class="agent-action-btn delete-btn" onclick="deleteAgent('${agentId}')">Delete</button>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        // Add click listeners to agent items
        agentsList.querySelectorAll('.agent-item').forEach(item => {
            item.addEventListener('click', (e) => {
                // Don't trigger if clicking on action buttons
                if (e.target.classList.contains('agent-action-btn')) {
                    return;
                }
                const agentId = item.getAttribute('data-agent-id');
                openAgentDetailsModal(agentId);
            });
        });
    }

    function selectAgent(agentId) {
        selectedAgent = agentId;
        displayAgents(); // Refresh to show selection
        displayAgentDetails(agentId);
    }

    function openAgentDetailsModal(agentId) {
        console.log('openAgentDetailsModal called with agentId:', agentId);
        const modal = document.getElementById('agent-details-modal');
        const modalAgentName = document.getElementById('modal-agent-name');
        const agentDetailsContent = document.getElementById('agent-details-content');
        
        if (!modal) {
            console.log('Modal element not found');
            return;
        }
        
        // Find the agent data
        const allAgents = [...systemAgents, ...userAgents, ...agents];
        const agent = allAgents.find(a => (a.id || a.name) === agentId);
        
        if (agent) {
            modalAgentName.textContent = agent.name || agentId;
            displayAgentDetailsInModal(agent);
            modal.style.display = 'flex';
            console.log('Modal opened successfully');
        } else {
            console.log('Agent not found:', agentId);
        }
    }

    function closeAgentDetailsModal() {
        console.log('closeAgentDetailsModal called');
        const modal = document.getElementById('agent-details-modal');
        if (modal) {
            modal.style.display = 'none';
            console.log('Modal closed successfully');
        } else {
            console.log('Modal element not found');
        }
    }
    
    // Make closeAgentDetailsModal globally available
    window.closeAgentDetailsModal = closeAgentDetailsModal;

    function displayAgentDetailsInModal(agent) {
        const agentDetailsContent = document.getElementById('agent-details-content');
        
        const agentId = agent.id || agent.name || 'Unknown';
        const agentType = agent.type || 'Unknown';
        const agentStatus = agent.status || 'Unknown';
        const agentDescription = agent.description || 'No description available';
        const isSystem = agent.isSystem || agent.createdBy === 'system';
        
        agentDetailsContent.innerHTML = `
            <h3>Basic Information</h3>
            <div class="detail-row">
                <span class="detail-label">Name:</span>
                <span class="detail-value">${agent.name || agentId}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Type:</span>
                <span class="detail-value">${agentType}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">${agentStatus}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">System Agent:</span>
                <span class="detail-value">${isSystem ? 'Yes' : 'No'}</span>
            </div>
            
            <h3>Description</h3>
            <p>${agentDescription}</p>
            
            ${agent.file ? `
                <h3>File Information</h3>
                <div class="detail-row">
                    <span class="detail-label">File:</span>
                    <span class="detail-value">${agent.file}</span>
                </div>
                ${agent.path ? `
                    <div class="detail-row">
                        <span class="detail-label">Path:</span>
                        <span class="detail-value">${agent.path}</span>
                    </div>
                ` : ''}
            ` : ''}
            
            ${agent.class_name ? `
                <h3>Technical Details</h3>
                <div class="detail-row">
                    <span class="detail-label">Class:</span>
                    <span class="detail-value">${agent.class_name}</span>
                </div>
            ` : ''}
            
            ${agent.lastActivity ? `
                <h3>Activity</h3>
                <div class="detail-row">
                    <span class="detail-label">Last Activity:</span>
                    <span class="detail-value">${agent.lastActivity}</span>
                </div>
            ` : ''}
        `;
    }

    function displayAgentDetails(agentId) {
        const agent = [...systemAgents, ...userAgents].find(a => (a.id || a.name) === agentId);
        if (!agent) {
            agentDetails.innerHTML = '<p>Agent not found</p>';
            return;
        }

        const capabilities = agent.capabilities ? agent.capabilities.map(cap => 
            `<span class="capability-tag">${cap}</span>`
        ).join('') : '';

        agentDetails.innerHTML = `
            <div class="agent-details">
                <div class="agent-detail-section">
                    <h3>Agent Information</h3>
                    <div class="agent-detail-grid">
                        <div class="agent-detail-item">
                            <span class="agent-detail-label">Name</span>
                            <span class="agent-detail-value">${agent.name || agentId}</span>
                        </div>
                        <div class="agent-detail-item">
                            <span class="agent-detail-label">Type</span>
                            <span class="agent-detail-value">${agent.type || 'Unknown'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <span class="agent-detail-label">Status</span>
                            <span class="agent-detail-value">${agent.status || 'Unknown'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <span class="agent-detail-label">Created By</span>
                            <span class="agent-detail-value">${agent.createdBy || 'Unknown'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <span class="agent-detail-label">Last Activity</span>
                            <span class="agent-detail-value">${agent.lastActivity || 'Unknown'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <span class="agent-detail-label">System Agent</span>
                            <span class="agent-detail-value">${agent.isSystem ? 'Yes' : 'No'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="agent-detail-section">
                    <h3>Description</h3>
                    <p>${agent.description || 'No description available'}</p>
                </div>
                
                <div class="agent-detail-section">
                    <h3>Capabilities</h3>
                    <div class="agent-capabilities">
                        ${capabilities || '<span class="capability-tag">No capabilities listed</span>'}
                    </div>
                </div>
                
                <div class="agent-detail-section">
                    <h3>Actions</h3>
                    <div class="agent-actions">
                        <button class="agent-action-btn" onclick="refreshAgentStatus('${agentId}')">Refresh Status</button>
                        ${!agent.isSystem && agent.createdBy !== 'system' ? 
                            `<button class="agent-action-btn delete-btn" onclick="deleteAgent('${agentId}')">Delete Agent</button>` : 
                            '<span class="agent-detail-value" style="color: var(--corp-purple); font-size: 12px;">System agents cannot be deleted</span>'
                        }
                    </div>
                </div>
            </div>
        `;
    }

    async function createAgent() {
        const agentType = prompt('Enter agent type:', 'simple_coder');
        const agentId = prompt('Enter agent ID:', `agent_${Date.now()}`);
        const agentName = prompt('Enter agent name:', `User Agent ${Date.now()}`);
        
        if (agentType && agentId && agentName) {
            try {
                const newAgent = {
                    id: agentId,
                    name: agentName,
                    type: agentType,
                    status: 'active',
                    isSystem: false,
                    capabilities: ['User Created'],
                    description: `User-created agent of type ${agentType}`,
                    createdBy: 'user',
                    lastActivity: 'Just created'
                };
                
                await sendRequest('/agents', 'POST', {
                    agent_type: agentType,
                    agent_id: agentId,
                    config: {}
                });
                addLog(`Agent ${agentName} created successfully`, 'INFO');
                
                // Add to user agents
                userAgents.push(newAgent);
                agents = [...systemAgents, ...userAgents];
                
                displayAgents();
                showResponse(`Agent ${agentName} created successfully`);
            } catch (error) {
                addLog(`Failed to create agent: ${error.message}`, 'ERROR');
                showResponse(`Failed to create agent: ${error.message}`);
            }
        }
    }
    
    function refreshAgentStatus(agentId) {
        const agent = [...systemAgents, ...userAgents].find(a => (a.id || a.name) === agentId);
        if (agent) {
            // Simulate status refresh
            agent.lastActivity = new Date().toLocaleTimeString();
            displayAgentDetails(agentId);
            addLog(`Refreshed status for agent ${agent.name || agentId}`, 'INFO');
        }
    }

    async function deleteAgent(agentId = null) {
        const targetAgentId = agentId || selectedAgent;
        if (!targetAgentId) {
            showResponse('Please select an agent to delete');
            return;
        }

        // Find the agent to check if it can be deleted
        const agent = [...systemAgents, ...userAgents].find(a => (a.id || a.name) === targetAgentId);
        if (!agent) {
            addLog('Agent not found', 'ERROR');
            return;
        }

        // Check if it's a system agent
        if (agent.isSystem || agent.createdBy === 'system') {
            addLog('System agents cannot be deleted', 'WARNING');
            showResponse('System agents cannot be deleted. Only user-created agents can be removed.');
            return;
        }
        
        if (confirm(`Are you sure you want to delete agent ${agent.name || targetAgentId}?`)) {
            try {
                await sendRequest(`/agents/${targetAgentId}`, 'DELETE');
                addLog(`Agent ${agent.name || targetAgentId} deleted successfully`, 'INFO');
                
                // Remove from user agents
                userAgents = userAgents.filter(a => (a.id || a.name) !== targetAgentId);
                agents = [...systemAgents, ...userAgents];
                
                if (selectedAgent === targetAgentId) {
                    selectedAgent = null;
                }
                
                displayAgents();
                agentDetails.innerHTML = '<p>Select an agent from the list to view details.</p>';
                showResponse(`Agent ${agent.name || targetAgentId} deleted successfully`);
            } catch (error) {
                addLog(`Failed to delete agent: ${error.message}`, 'ERROR');
                showResponse(`Failed to delete agent: ${error.message}`);
            }
        }
    }

    // System Tab Functions
    function initializeSystemTab() {
        // System tab is mostly read-only, data loaded on tab switch
    }

    async function loadSystemStatus() {
        try {
            const [status, metrics, resources, health] = await Promise.all([
                sendRequest('/status/mastermind'),
                sendRequest('/system/metrics'),
                sendRequest('/system/resources'),
                sendRequest('/health')
            ]);
            
            displaySystemStatus(status, metrics, resources, health);
        } catch (error) {
            addLog(`Failed to load system status: ${error.message}`, 'ERROR');
            displaySystemStatus(null, null, null, null);
        }
    }

    function displaySystemStatus(status, metrics, resources, health) {
        // System Status with Health Info
        if (health) {
            const healthStatus = health.status;
            const healthClass = healthStatus === 'healthy' ? 'status-healthy' : 
                               healthStatus === 'degraded' ? 'status-degraded' : 'status-unhealthy';
            
            systemStatus.innerHTML = `
                <div class="health-status ${healthClass}">
                    <h3>System Health: ${healthStatus.toUpperCase()}</h3>
                    <div class="health-components">
                        ${Object.entries(health.components || {}).map(([key, value]) => 
                            `<div class="health-component">
                                <span class="component-name">${key}:</span>
                                <span class="component-status ${value === 'running' || value === 'available' || value === 'operational' || value === 'connected' ? 'status-good' : 'status-bad'}">${value}</span>
                            </div>`
                        ).join('')}
                    </div>
                    ${health.warnings ? `<div class="health-warnings">Warnings: ${health.warnings.join(', ')}</div>` : ''}
                </div>
                <details>
                    <summary>Raw Status Data</summary>
                    <pre>${JSON.stringify(status, null, 2)}</pre>
                </details>
            `;
        } else {
            systemStatus.innerHTML = status ? 
                `<pre>${JSON.stringify(status, null, 2)}</pre>` : 
                '<p>System status unavailable</p>';
        }
            
        // Performance Metrics with better formatting
        if (metrics) {
            performanceMetrics.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-label">CPU Usage:</span>
                        <span class="metric-value">${metrics.cpu_usage?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Memory Usage:</span>
                        <span class="metric-value">${metrics.memory_usage?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Disk Usage:</span>
                        <span class="metric-value">${metrics.disk_usage?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Memory Available:</span>
                        <span class="metric-value">${formatBytes(metrics.memory_available) || 'N/A'}</span>
                    </div>
                </div>
                <details>
                    <summary>Raw Metrics Data</summary>
                    <pre>${JSON.stringify(metrics, null, 2)}</pre>
                </details>
            `;
        } else {
            performanceMetrics.innerHTML = '<p>Performance metrics unavailable</p>';
        }
            
        // Resource Usage
        resourceUsage.innerHTML = resources ? 
            `<pre>${JSON.stringify(resources, null, 2)}</pre>` : 
            '<p>Resource usage unavailable</p>';
    }

    // Helper function to format bytes
    function formatBytes(bytes) {
        if (!bytes) return 'N/A';
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Logs Tab Functions
    function initializeLogsTab() {
        refreshLogsBtn.addEventListener('click', loadLogs);
        clearLogsBtn.addEventListener('click', clearLogs);
        copyLogsBtn.addEventListener('click', copyLogsToClipboard);
        logLevelFilter.addEventListener('change', updateLogsDisplay);
    }

    async function loadLogs() {
        try {
            const result = await sendRequest('/system/logs');
            if (result.logs) {
                logs = result.logs;
                updateLogsDisplay();
            }
        } catch (error) {
            addLog(`Failed to load logs: ${error.message}`, 'ERROR');
        }
    }

    function clearLogs() {
        logs = [];
        updateLogsDisplay();
        addLog('Logs cleared', 'INFO');
    }

    function copyLogsToClipboard() {
        const logText = logs.map(log => `[${log.timestamp}] ${log.level}: ${log.message}`).join('\n');
        navigator.clipboard.writeText(logText).then(() => {
            addLog('Logs copied to clipboard', 'INFO');
        }).catch(err => {
            addLog(`Failed to copy logs: ${err.message}`, 'ERROR');
        });
    }

    // Terminal Tab Functions
    function initializeTerminalTab() {
        refreshTerminalBtn.addEventListener('click', loadTerminal);
        clearTerminalBtn.addEventListener('click', clearTerminal);
        executeCommandBtn.addEventListener('click', executeCommand);
        sendCommandBtn.addEventListener('click', sendCommand);
        
        terminalCommand.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });
    }

    async function loadTerminal() {
        try {
            const result = await sendRequest('/system/terminal');
            if (result.output) {
                terminalHistory = result.output.split('\n');
                updateTerminalDisplay();
            }
        } catch (error) {
            addLog(`Failed to load terminal: ${error.message}`, 'ERROR');
        }
    }

    function clearTerminal() {
        terminalHistory = [];
        updateTerminalDisplay();
        addLog('Terminal cleared', 'INFO');
    }

    async function executeCommand() {
        const command = prompt('Enter command to execute:', 'ls -la');
        if (command) {
            try {
                const result = await sendRequest('/system/execute', 'POST', { command });
                addTerminalOutput(`$ ${command}`);
                addTerminalOutput(result.output || result.message || 'Command executed');
            } catch (error) {
                addLog(`Command execution failed: ${error.message}`, 'ERROR');
            }
        }
    }

    function sendCommand() {
        const command = terminalCommand.value.trim();
        if (command) {
            addTerminalOutput(`$ ${command}`);
            terminalCommand.value = '';
            // In a real implementation, this would send the command to the backend
            addTerminalOutput('Command sent to backend (mock response)');
        }
    }

    // Admin Tab Functions
    function initializeAdminTab() {
        restartSystemBtn.addEventListener('click', restartSystem);
        backupSystemBtn.addEventListener('click', backupSystem);
        updateConfigBtn.addEventListener('click', updateConfig);
        exportLogsBtn.addEventListener('click', exportLogs);
    }

    async function loadAdminData() {
        try {
            const config = await sendRequest('/system/config');
            displayConfig(config);
        } catch (error) {
            addLog(`Failed to load admin data: ${error.message}`, 'ERROR');
        }
    }

    function displayConfig(config) {
        configDisplay.innerHTML = config ? 
            `<pre>${JSON.stringify(config, null, 2)}</pre>` : 
            '<p>Configuration unavailable</p>';
    }

    async function restartSystem() {
        if (confirm('Are you sure you want to restart the system?')) {
            try {
                await sendRequest('/system/restart', 'POST');
                addLog('System restart initiated', 'INFO');
            } catch (error) {
                addLog(`System restart failed: ${error.message}`, 'ERROR');
            }
        }
    }

    async function backupSystem() {
        try {
            await sendRequest('/system/backup', 'POST');
            addLog('System backup initiated', 'INFO');
        } catch (error) {
            addLog(`System backup failed: ${error.message}`, 'ERROR');
        }
    }

    async function updateConfig() {
        const newConfig = prompt('Enter new configuration (JSON):', '{}');
        if (newConfig) {
            try {
                const config = JSON.parse(newConfig);
                await sendRequest('/system/config', 'PUT', config);
                addLog('Configuration updated', 'INFO');
                loadAdminData();
            } catch (error) {
                addLog(`Configuration update failed: ${error.message}`, 'ERROR');
            }
        }
    }

    async function exportLogs() {
        try {
            const result = await sendRequest('/system/export-logs', 'POST');
            addLog('Logs exported successfully', 'INFO');
            showResponse(JSON.stringify(result, null, 2));
        } catch (error) {
            addLog(`Log export failed: ${error.message}`, 'ERROR');
        }
    }

    // Autonomous Mode Functions
    function initializeAutonomousMode() {
        autonomousToggle.addEventListener('change', (e) => {
            isAutonomousMode = e.target.checked;
            if (isAutonomousMode) {
                startAutonomousMode();
            } else {
                stopAutonomousMode();
            }
        });
    }

    function startAutonomousMode() {
        addLog('Autonomous mode activated', 'INFO');
        autonomousInterval = setInterval(async () => {
            try {
                // Autonomous operations
                await sendRequest('/status/mastermind');
                addLog('Autonomous status check completed', 'DEBUG');
            } catch (error) {
                addLog(`Autonomous operation failed: ${error.message}`, 'WARNING');
            }
        }, 30000); // Check every 30 seconds
    }

    function stopAutonomousMode() {
        addLog('Autonomous mode deactivated', 'INFO');
        if (autonomousInterval) {
            clearInterval(autonomousInterval);
            autonomousInterval = null;
        }
    }

    // Backend Status Check
    async function checkBackendStatus() {
        try {
            const health = await sendRequest('/health');
            if (health.status === 'healthy') {
                statusLight.className = 'status-light-green';
                statusLight.title = 'Connected - All systems operational';
            } else if (health.status === 'degraded') {
                statusLight.className = 'status-light-red';
                statusLight.title = 'Connected - Some systems degraded';
        } else {
                statusLight.className = 'status-light-red';
                statusLight.title = 'Connected - System unhealthy';
            }
        } catch (error) {
            statusLight.className = 'status-light-red';
            statusLight.title = `Disconnected - ${error.message}`;
        }
    }

    // Initialize everything
    // Evolution Tab Functions
    function initializeEvolutionTab() {
        generateBlueprintBtn.addEventListener('click', async () => {
            try {
                addLog('Generating new blueprint...', 'INFO');
                const response = await sendRequest('/evolution/generate-blueprint', 'POST');
                showResponse(JSON.stringify(response, null, 2));
                loadEvolution(); // Refresh the evolution data
            } catch (error) {
                addLog(`Failed to generate blueprint: ${error.message}`, 'ERROR');
                showResponse(`Error: ${error.message}`);
            }
        });

        executeEvolutionBtn.addEventListener('click', async () => {
            try {
                addLog('Executing evolution...', 'INFO');
                const response = await sendRequest('/evolution/execute', 'POST');
                showResponse(JSON.stringify(response, null, 2));
                loadEvolution(); // Refresh the evolution data
            } catch (error) {
                addLog(`Failed to execute evolution: ${error.message}`, 'ERROR');
                showResponse(`Error: ${error.message}`);
            }
        });

        analyzeSystemBtn.addEventListener('click', async () => {
            try {
                addLog('Analyzing system...', 'INFO');
                const response = await sendRequest('/evolution/analyze', 'POST');
                showResponse(JSON.stringify(response, null, 2));
                loadEvolution(); // Refresh the evolution data
            } catch (error) {
                addLog(`Failed to analyze system: ${error.message}`, 'ERROR');
                showResponse(`Error: ${error.message}`);
            }
        });
    }

    // Initialize update requests functionality
    function initializeUpdateRequests() {
        console.log('Initializing update requests functionality...');
        const refreshBtn = document.getElementById('refresh-updates-btn');
        const selectAllBtn = document.getElementById('select-all-btn');
        const approveAllBtn = document.getElementById('approve-all-btn');
        const deleteAllBtn = document.getElementById('delete-all-btn');
        
        console.log('Buttons found:', { refreshBtn, selectAllBtn, approveAllBtn, deleteAllBtn });
        
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                console.log('Refresh button clicked!');
                
                // Show loading state
                const originalText = refreshBtn.textContent;
                refreshBtn.textContent = 'Refreshing...';
                refreshBtn.disabled = true;
                
                // Call loadUpdateRequests
                loadUpdateRequests().finally(() => {
                    // Restore button state
                    refreshBtn.textContent = originalText;
                    refreshBtn.disabled = false;
                });
            });
            console.log('Refresh button event listener added');
        } else {
            console.error('Refresh button not found!');
        }
        
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', toggleSelectAll);
            console.log('Select all button event listener added');
        }
        
        if (approveAllBtn) {
            approveAllBtn.addEventListener('click', approveAllUpdates);
            console.log('Approve all button event listener added');
        }
        
        if (deleteAllBtn) {
            deleteAllBtn.addEventListener('click', deleteAllSelected);
            console.log('Delete all button event listener added');
        }
        
        // Load update requests on page load
        console.log('Loading update requests on page load...');
        
        // Add a delay to ensure DOM is ready
        setTimeout(() => {
            console.log('Delayed load of update requests...');
            loadUpdateRequests();
        }, 1000);
    }
    
    async function loadUpdateRequests() {
        try {
            console.log('Loading update requests...');
            console.log('API URL:', `${apiUrl}/simple-coder/update-requests`);
            
            const response = await fetch(`${apiUrl}/simple-coder/update-requests`);
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Data received:', data);
            console.log('Data type:', typeof data);
            console.log('Data length:', data ? data.length : 'No data');
            
            const container = document.getElementById('update-requests-container');
            const selectAllBtn = document.getElementById('select-all-btn');
            const approveAllBtn = document.getElementById('approve-all-btn');
            const deleteAllBtn = document.getElementById('delete-all-btn');
            
            console.log('Container element:', container);
            console.log('Container parent:', container ? container.parentElement : 'No container');
            console.log('Buttons found:', { selectAllBtn, approveAllBtn, deleteAllBtn });
            
            if (data && Array.isArray(data) && data.length > 0) {
                console.log(`Creating ${data.length} update request elements`);
                container.innerHTML = '';
                // Use simple display like test UI
                data.forEach((request, index) => {
                    const div = document.createElement('div');
                    div.className = 'update-request';
                    div.style.margin = '10px 0';
                    div.style.padding = '15px';
                    div.style.border = '1px solid #555';
                    div.style.borderRadius = '8px';
                    div.style.background = '#1a1a1a';
                    
                    div.innerHTML = `
                        <h4>Update Request ${index + 1}: ${request.request_id}</h4>
                        <p><strong>Original File:</strong> ${request.original_file}</p>
                        <p><strong>Sandbox File:</strong> ${request.sandbox_file}</p>
                        <p><strong>Status:</strong> ${request.status}</p>
                        <p><strong>Cycle:</strong> ${request.cycle}</p>
                        <p><strong>Changes:</strong> ${request.changes.length} modifications</p>
                        <p><strong>Timestamp:</strong> ${new Date(request.timestamp).toLocaleString()}</p>
                        <button onclick="approveUpdate('${request.request_id}')" style="margin: 5px; padding: 5px 10px; background: #00aa00; color: white; border: none; border-radius: 3px; cursor: pointer;">Approve</button>
                        <button onclick="rejectUpdate('${request.request_id}')" style="margin: 5px; padding: 5px 10px; background: #aa0000; color: white; border: none; border-radius: 3px; cursor: pointer;">Reject</button>
                    `;
                    
                    container.appendChild(div);
                    console.log(`Added element ${index + 1}`);
                });
                
                // Force container to be visible
                container.style.display = 'block';
                container.style.visibility = 'visible';
                console.log('Container forced to be visible');
                
                // Enable control buttons
                if (selectAllBtn) selectAllBtn.disabled = false;
                if (approveAllBtn) approveAllBtn.disabled = false;
                if (deleteAllBtn) deleteAllBtn.disabled = false;
                
                // Update select all button text
                updateSelectAllButton();
                console.log(`Successfully displayed ${data.length} update requests`);
                
                // Force a visual update
                container.style.display = 'block';
                container.style.visibility = 'visible';
            } else {
                console.log('No update requests found or invalid data format');
                container.innerHTML = '<p>No pending update requests</p>';
                if (selectAllBtn) selectAllBtn.disabled = true;
                if (approveAllBtn) approveAllBtn.disabled = true;
                if (deleteAllBtn) deleteAllBtn.disabled = true;
            }
        } catch (error) {
            console.error('Error loading update requests:', error);
            console.error('Error details:', error.message);
            const container = document.getElementById('update-requests-container');
            container.innerHTML = `<p>Error loading update requests: ${error.message}</p>`;
        }
    }
    
    function createUpdateRequestElement(request) {
        const div = document.createElement('div');
        div.className = 'update-request';
        div.setAttribute('data-request-id', request.request_id);
        
        // Use simple display like the test UI
        div.innerHTML = `
            <div class="update-request-header">
                <h4>Update Request: ${request.request_id}</h4>
                <span class="request-status ${request.status}">${request.status}</span>
                <input type="checkbox" class="update-request-checkbox" data-request-id="${request.request_id}">
            </div>
            
            <div class="update-request-details">
                <p><strong>Original File:</strong> ${request.original_file}</p>
                <p><strong>Sandbox File:</strong> ${request.sandbox_file}</p>
                <p><strong>Cycle:</strong> ${request.cycle}</p>
                <p><strong>Changes:</strong> ${request.changes.length} modifications</p>
                <p><strong>Timestamp:</strong> ${new Date(request.timestamp).toLocaleString()}</p>
            </div>
            
            <div class="update-request-actions">
                <button onclick="approveUpdate('${request.request_id}')" class="approve-btn">Approve</button>
                <button onclick="rejectUpdate('${request.request_id}')" class="reject-btn">Reject</button>
            </div>
        `;
        
        // Add checkbox functionality
        const checkbox = div.querySelector('.update-request-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    div.classList.add('selected');
                } else {
                    div.classList.remove('selected');
                }
                updateSelectAllButton();
                updateDeleteAllButton();
            });
        }
        
        return div;
    }
    
    async function approveUpdate(requestId) {
        try {
            const response = await fetch(`${apiUrl}/simple-coder/approve-update/${requestId}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.status === 'approved') {
                addLog(`Update request ${requestId} approved`, 'SUCCESS');
                loadUpdateRequests(); // Refresh the list
            } else {
                addLog(`Failed to approve update request ${requestId}: ${data.error}`, 'ERROR');
            }
        } catch (error) {
            console.error('Error approving update:', error);
            addLog(`Error approving update request ${requestId}: ${error.message}`, 'ERROR');
        }
    }
    
    async function rejectUpdate(requestId) {
        try {
            const response = await fetch(`${apiUrl}/simple-coder/reject-update/${requestId}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.status === 'rejected') {
                addLog(`Update request ${requestId} rejected`, 'INFO');
                loadUpdateRequests(); // Refresh the list
            } else {
                addLog(`Failed to reject update request ${requestId}: ${data.error}`, 'ERROR');
            }
        } catch (error) {
            console.error('Error rejecting update:', error);
            addLog(`Error rejecting update request ${requestId}: ${error.message}`, 'ERROR');
        }
    }
    
    async function approveAllUpdates() {
        try {
            const response = await fetch(`${apiUrl}/simple-coder/update-requests`);
            const data = await response.json();
            
            if (data && data.length > 0) {
                const pendingRequests = data.filter(r => r.status === 'pending');
                
                for (const request of pendingRequests) {
                    await approveUpdate(request.request_id);
                }
                
                addLog(`Approved ${pendingRequests.length} update requests`, 'SUCCESS');
                loadUpdateRequests(); // Refresh the list
            }
        } catch (error) {
            console.error('Error approving all updates:', error);
            addLog(`Error approving all updates: ${error.message}`, 'ERROR');
        }
    }
    
    function toggleSelectAll() {
        const checkboxes = document.querySelectorAll('.update-request-checkbox');
        const selectAllBtn = document.getElementById('select-all-btn');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = !allChecked;
            const requestDiv = checkbox.closest('.update-request');
            if (checkbox.checked) {
                requestDiv.classList.add('selected');
            } else {
                requestDiv.classList.remove('selected');
            }
        });
        
        updateSelectAllButton();
        updateDeleteAllButton();
    }
    
    function updateSelectAllButton() {
        const checkboxes = document.querySelectorAll('.update-request-checkbox');
        const selectAllBtn = document.getElementById('select-all-btn');
        
        if (checkboxes.length === 0) return;
        
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        const someChecked = Array.from(checkboxes).some(cb => cb.checked);
        
        if (allChecked) {
            selectAllBtn.textContent = 'Deselect All';
        } else if (someChecked) {
            selectAllBtn.textContent = 'Select All';
        } else {
            selectAllBtn.textContent = 'Select All';
        }
    }
    
    function updateDeleteAllButton() {
        const selectedCheckboxes = document.querySelectorAll('.update-request-checkbox:checked');
        const deleteAllBtn = document.getElementById('delete-all-btn');
        
        if (selectedCheckboxes.length > 0) {
            deleteAllBtn.textContent = `Delete All Selected (${selectedCheckboxes.length})`;
            deleteAllBtn.disabled = false;
        } else {
            deleteAllBtn.textContent = 'Delete All Selected';
            deleteAllBtn.disabled = true;
        }
    }
    
    async function deleteAllSelected() {
        const selectedCheckboxes = document.querySelectorAll('.update-request-checkbox:checked');
        
        if (selectedCheckboxes.length === 0) {
            addLog('No requests selected for deletion', 'WARNING');
            return;
        }
        
        if (!confirm(`Are you sure you want to delete ${selectedCheckboxes.length} selected update request(s)?`)) {
            return;
        }
        
        try {
            const deletePromises = Array.from(selectedCheckboxes).map(async (checkbox) => {
                const requestId = checkbox.getAttribute('data-request-id');
                return await rejectUpdate(requestId);
            });
            
            await Promise.all(deletePromises);
            addLog(`Successfully deleted ${selectedCheckboxes.length} update request(s)`, 'SUCCESS');
            loadUpdateRequests(); // Refresh the list
        } catch (error) {
            console.error('Error deleting selected updates:', error);
            addLog(`Error deleting selected updates: ${error.message}`, 'ERROR');
        }
    }
    
    function viewFile(filePath) {
        // Open file in a new window or modal
        window.open(`file://${filePath}`, '_blank');
    }
    
    function viewDiff(requestId) {
        // Placeholder for diff viewing functionality
        addLog(`Diff view for request ${requestId} - Feature coming soon`, 'INFO');
    }
    
    // Global function for manual testing
    window.testUpdateRequests = function() {
        console.log('Manual test of update requests...');
        loadUpdateRequests();
    };
    
    // Global function to force refresh
    window.forceRefreshUpdates = function() {
        console.log('Force refreshing update requests...');
        const container = document.getElementById('update-requests-container');
        if (container) {
            container.innerHTML = '<p>Loading update requests...</p>';
        }
        loadUpdateRequests();
    };
    
    // Global function to show control tab and refresh
    window.showControlTabAndRefresh = function() {
        console.log('Showing control tab and refreshing...');
        
        // Switch to control tab
        const controlTab = document.getElementById('control-tab');
        const controlTabButton = document.querySelector('[data-tab="control"]');
        
        if (controlTabButton) {
            controlTabButton.click();
            console.log('Switched to control tab');
        } else {
            console.error('Control tab button not found!');
        }
        
        // Wait a bit then refresh
        setTimeout(() => {
            forceRefreshUpdates();
        }, 500);
    };
    
    // Global function to force show control tab
    window.showControlTab = function() {
        console.log('Forcing control tab to be visible...');
        
        // Remove active from all tabs
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        // Activate control tab
        const controlTab = document.getElementById('control-tab');
        const controlTabButton = document.querySelector('[data-tab="control"]');
        
        if (controlTab && controlTabButton) {
            controlTab.classList.add('active');
            controlTabButton.classList.add('active');
            console.log('Control tab activated');
            
            // Refresh update requests
            setTimeout(() => {
                loadUpdateRequests();
            }, 100);
        } else {
            console.error('Control tab elements not found!');
        }
    };
    
    // Global function to check current state
    window.checkUpdateRequestsState = function() {
        const container = document.getElementById('update-requests-container');
        const buttons = {
            refresh: document.getElementById('refresh-updates-btn'),
            selectAll: document.getElementById('select-all-btn'),
            approveAll: document.getElementById('approve-all-btn'),
            deleteAll: document.getElementById('delete-all-btn')
        };
        
        console.log('Update requests state:');
        console.log('Container:', container);
        console.log('Container HTML:', container ? container.innerHTML : 'No container');
        console.log('Buttons:', buttons);
        console.log('Button states:', Object.fromEntries(
            Object.entries(buttons).map(([name, btn]) => [name, btn ? btn.disabled : 'Not found'])
        ));
        
        return { container, buttons };
    };
    
    // Global function to force refresh and show updates
    window.forceShowUpdates = function() {
        console.log('Force showing updates...');
        showControlTab();
        setTimeout(() => {
            loadUpdateRequests();
        }, 500);
    };
    
    // Global function to debug the current state
    window.debugUI = function() {
        console.log('=== UI DEBUG INFO ===');
        
        // Check tab visibility
        const controlTab = document.getElementById('control-tab');
        const controlTabBtn = document.querySelector('[data-tab="control"]');
        console.log('Control tab:', {
            element: !!controlTab,
            visible: controlTab ? controlTab.offsetParent !== null : false,
            classes: controlTab ? controlTab.className : 'Not found',
            display: controlTab ? getComputedStyle(controlTab).display : 'Not found'
        });
        console.log('Control tab button:', {
            element: !!controlTabBtn,
            classes: controlTabBtn ? controlTabBtn.className : 'Not found'
        });
        
        // Check container
        const container = document.getElementById('update-requests-container');
        console.log('Update requests container:', {
            element: !!container,
            visible: container ? container.offsetParent !== null : false,
            classes: container ? container.className : 'Not found',
            display: container ? getComputedStyle(container).display : 'Not found',
            innerHTML: container ? container.innerHTML.substring(0, 100) + '...' : 'Not found'
        });
        
        // Check buttons
        const refreshBtn = document.getElementById('refresh-updates-btn');
        console.log('Refresh button:', {
            element: !!refreshBtn,
            disabled: refreshBtn ? refreshBtn.disabled : 'Not found',
            text: refreshBtn ? refreshBtn.textContent : 'Not found'
        });
        
        // Test API
        testAPI().then(data => {
            console.log('API test result:', data ? `${data.length} requests` : 'Failed');
        });
        
        return { controlTab, container, refreshBtn };
    };
    
    // Global function to test the API directly
    window.testAPI = async function() {
        try {
            console.log('Testing API...');
            const response = await fetch('http://localhost:8000/simple-coder/update-requests');
            const data = await response.json();
            console.log('API Response:', data);
            console.log('Count:', data.length);
            return data;
        } catch (error) {
            console.error('API Error:', error);
            return null;
        }
    };
    
    // Global function to immediately load updates (no async)
    window.loadUpdatesNow = function() {
        console.log('=== LOAD UPDATES NOW ===');
        
        const container = document.getElementById('update-requests-container');
        if (!container) {
            console.error('Container not found!');
            return;
        }
        
        console.log('Container found, loading data...');
        
        // Use fetch with .then() for immediate execution
        fetch('http://localhost:8000/simple-coder/update-requests')
            .then(response => {
                console.log('Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Data received:', data);
                console.log('Data length:', data.length);
                
                if (data && Array.isArray(data) && data.length > 0) {
                    console.log(`Creating ${data.length} update request elements`);
                    container.innerHTML = '';
                    
                    data.forEach((request, index) => {
                        const div = document.createElement('div');
                        div.className = 'update-request';
                        div.style.margin = '10px 0';
                        div.style.padding = '15px';
                        div.style.border = '1px solid #555';
                        div.style.borderRadius = '8px';
                        div.style.background = '#1a1a1a';
                        
                        div.innerHTML = `
                            <h4>Update Request ${index + 1}: ${request.request_id}</h4>
                            <p><strong>Original File:</strong> ${request.original_file}</p>
                            <p><strong>Sandbox File:</strong> ${request.sandbox_file}</p>
                            <p><strong>Status:</strong> ${request.status}</p>
                            <p><strong>Cycle:</strong> ${request.cycle}</p>
                            <p><strong>Changes:</strong> ${request.changes.length} modifications</p>
                            <p><strong>Timestamp:</strong> ${new Date(request.timestamp).toLocaleString()}</p>
                            <button onclick="approveUpdate('${request.request_id}')" style="margin: 5px; padding: 5px 10px; background: #00aa00; color: white; border: none; border-radius: 3px; cursor: pointer;">Approve</button>
                            <button onclick="rejectUpdate('${request.request_id}')" style="margin: 5px; padding: 5px 10px; background: #aa0000; color: white; border: none; border-radius: 3px; cursor: pointer;">Reject</button>
                        `;
                        
                        container.appendChild(div);
                        console.log(`Added element ${index + 1}`);
                    });
                    
                    console.log(`Successfully displayed ${data.length} update requests`);
                } else {
                    container.innerHTML = '<p>No update requests found</p>';
                    console.log('No update requests to display');
                }
            })
            .catch(error => {
                console.error('Error loading update requests:', error);
                container.innerHTML = `<p style="color: #ff6666;">Error: ${error.message}</p>`;
            });
    };
    
    // Global function to manually load and display updates
    window.manualLoadUpdates = async function() {
        console.log('=== MANUAL LOAD UPDATES ===');
        
        // Check if elements exist
        const container = document.getElementById('update-requests-container');
        const refreshBtn = document.getElementById('refresh-updates-btn');
        
        console.log('Elements found:', {
            container: !!container,
            refreshBtn: !!refreshBtn,
            containerParent: container ? container.parentElement : 'No container'
        });
        
        if (!container) {
            console.error('Update requests container not found!');
            return;
        }
        
        try {
            console.log('Fetching data...');
            const response = await fetch('http://localhost:8000/simple-coder/update-requests');
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Data received:', data);
            console.log('Data length:', data.length);
            
            if (data && Array.isArray(data) && data.length > 0) {
                console.log(`Creating ${data.length} update request elements`);
                
                // Clear container
                container.innerHTML = '';
                
                // Create simple elements like test UI
                data.forEach((request, index) => {
                    const div = document.createElement('div');
                    div.className = 'update-request';
                    div.style.margin = '10px 0';
                    div.style.padding = '15px';
                    div.style.border = '1px solid #555';
                    div.style.borderRadius = '8px';
                    div.style.background = '#1a1a1a';
                    
                    div.innerHTML = `
                        <h4>Update Request ${index + 1}: ${request.request_id}</h4>
                        <p><strong>Original File:</strong> ${request.original_file}</p>
                        <p><strong>Sandbox File:</strong> ${request.sandbox_file}</p>
                        <p><strong>Status:</strong> ${request.status}</p>
                        <p><strong>Cycle:</strong> ${request.cycle}</p>
                        <p><strong>Changes:</strong> ${request.changes.length} modifications</p>
                        <p><strong>Timestamp:</strong> ${new Date(request.timestamp).toLocaleString()}</p>
                        <button onclick="approveUpdate('${request.request_id}')" style="margin: 5px; padding: 5px 10px; background: #00aa00; color: white; border: none; border-radius: 3px;">Approve</button>
                        <button onclick="rejectUpdate('${request.request_id}')" style="margin: 5px; padding: 5px 10px; background: #aa0000; color: white; border: none; border-radius: 3px;">Reject</button>
                    `;
                    
                    container.appendChild(div);
                    console.log(`Added element ${index + 1}`);
                });
                
                console.log(`Successfully displayed ${data.length} update requests`);
                return data;
            } else {
                container.innerHTML = '<p>No update requests found</p>';
                console.log('No update requests to display');
                return [];
            }
        } catch (error) {
            console.error('Error loading update requests:', error);
            container.innerHTML = `<p style="color: #ff6666;">Error: ${error.message}</p>`;
            return null;
        }
    };

    // Initialize system agents data
    function initializeSystemAgents() {
        systemAgents = [
            {
                id: 'memory_agent',
                name: 'Memory Agent',
                type: 'Core System',
                status: 'active',
                isSystem: true,
                capabilities: ['Memory Management', 'Timestamped Storage', 'JSON Operations'],
                description: 'Enhanced MemoryAgent with timestamped memory capabilities and ujson library for faster JSON operations',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'id_manager_agent',
                name: 'ID Manager Agent',
                type: 'Core System',
                status: 'active',
                isSystem: true,
                capabilities: ['Identity Management', 'Wallet Creation', 'Secure Key Storage'],
                description: 'Manages cryptographic identities and Ethereum-compatible wallets with secure central key store',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'guardian_agent',
                name: 'Guardian Agent',
                type: 'Security',
                status: 'active',
                isSystem: true,
                capabilities: ['Security Monitoring', 'Access Control', 'Threat Detection'],
                description: 'Security guardian providing system protection and access control',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'model_selector',
                name: 'Model Selector',
                type: 'LLM Management',
                status: 'active',
                isSystem: true,
                capabilities: ['Model Selection', 'Capability Matching', 'Performance Optimization'],
                description: 'Intelligent model selection based on capability matching, success rate, latency, and cost factors',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'model_registry',
                name: 'Model Registry',
                type: 'LLM Management',
                status: 'active',
                isSystem: true,
                capabilities: ['Model Registration', 'Provider Management', 'Handler Creation'],
                description: 'Registry managing LLM providers (Gemini, Mistral) and their handlers',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'coordinator_agent',
                name: 'Coordinator Agent',
                type: 'Orchestration',
                status: 'active',
                isSystem: true,
                capabilities: ['Task Coordination', 'Heavy Task Management', 'Agent Registration'],
                description: 'Central coordinator managing task distribution and agent interactions with concurrency limits',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'performance_monitor',
                name: 'Performance Monitor',
                type: 'Monitoring',
                status: 'active',
                isSystem: true,
                capabilities: ['Performance Metrics', 'Periodic Saving', 'System Analysis'],
                description: 'Monitors system performance with periodic metrics saving and analysis',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'resource_monitor',
                name: 'Resource Monitor',
                type: 'Monitoring',
                status: 'active',
                isSystem: true,
                capabilities: ['Resource Monitoring', 'CPU/Memory Tracking', 'Alert Management'],
                description: 'Real-time resource monitoring with CPU, memory, and disk threshold management',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'mastermind_agent',
                name: 'Mastermind Agent',
                type: 'Orchestration',
                status: 'active',
                isSystem: true,
                capabilities: ['Code Generation', 'BDI Management', 'Strategic Planning'],
                description: 'Mastermind agent with CodeBaseGenerator and BDI action handlers for system orchestration',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'automindx_agent',
                name: 'AutoMINDX Agent',
                type: 'AI Assistant',
                status: 'active',
                isSystem: true,
                capabilities: ['iNFT Capabilities', 'Avatar Support', 'A2A Protocol'],
                description: 'Advanced AI assistant with iNFT capabilities, avatar support, and A2A protocol compliance',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'bdi_agent',
                name: 'BDI Agent',
                type: 'Core System',
                status: 'active',
                isSystem: true,
                capabilities: ['Belief Management', 'Desire Processing', 'Intention Execution'],
                description: 'Belief-Desire-Intention agent with enhanced simple coder and comprehensive system access',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'simple_coder',
                name: 'Simple Coder',
                type: 'Development',
                status: 'active',
                isSystem: true,
                capabilities: ['Code Generation', 'Sandbox Management', 'Security Validation', 'Pattern Learning'],
                description: 'Streamlined and audited coding agent with enhanced security and performance optimizations',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'comprehensive_system_access_tool',
                name: 'Comprehensive System Access Tool',
                type: 'System Tool',
                status: 'active',
                isSystem: true,
                capabilities: ['Full System Access', 'File Operations', 'Process Management'],
                description: 'Tool providing comprehensive system access for BDI agent operations',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'strategic_evolution_agent',
                name: 'Strategic Evolution Agent',
                type: 'Learning',
                status: 'active',
                isSystem: true,
                capabilities: ['Strategic Planning', 'System Evolution', 'Reasoning'],
                description: 'Strategic Evolution Agent for mastermind with Mistral-based core reasoning',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'system_analyzer_tool',
                name: 'System Analyzer Tool',
                type: 'Analysis',
                status: 'active',
                isSystem: true,
                capabilities: ['System Analysis', 'Monitoring Integration', 'Coordinator Integration'],
                description: 'System analysis tool with integrated monitoring capabilities via Coordinator',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'base_gen_agent',
                name: 'Base Generation Agent',
                type: 'Code Generation',
                status: 'active',
                isSystem: true,
                capabilities: ['Code Generation', 'File Management', 'Configuration Handling'],
                description: 'Base generation agent for code creation with configurable file size limits',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'blueprint_agent',
                name: 'Blueprint Agent',
                type: 'Evolution',
                status: 'active',
                isSystem: true,
                capabilities: ['Blueprint Generation', 'System Design', 'Architecture Planning'],
                description: 'Blueprint agent for system architecture and design planning',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'blueprint_to_action_converter',
                name: 'Blueprint to Action Converter',
                type: 'Evolution',
                status: 'active',
                isSystem: true,
                capabilities: ['Blueprint Conversion', 'Action Generation', 'Implementation Planning'],
                description: 'Converts blueprints into actionable implementation plans',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'plan_management',
                name: 'Plan Management',
                type: 'Learning',
                status: 'active',
                isSystem: true,
                capabilities: ['Plan Management', 'Execution Control', 'Parallel Processing'],
                description: 'Plan manager for Strategic Evolution Agent with execution control',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'optimized_audit_gen_agent',
                name: 'Optimized Audit Generation Agent',
                type: 'Audit',
                status: 'active',
                isSystem: true,
                capabilities: ['Audit Generation', 'System Analysis', 'Performance Optimization'],
                description: 'Optimized audit generation agent with file size and chunk management',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'memory_agent_main',
                name: 'Memory Agent Main',
                type: 'Core System',
                status: 'active',
                isSystem: true,
                capabilities: ['Memory Management', 'Timestamped Storage', 'JSON Operations'],
                description: 'Main MemoryAgent instance with timestamped memory capabilities and ujson library for faster JSON operations',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'automindx_agent_main',
                name: 'AutoMINDX Agent Main',
                type: 'AI Assistant',
                status: 'active',
                isSystem: true,
                capabilities: ['iNFT Capabilities', 'Avatar Support', 'A2A Protocol Compliance', 'Persona Management'],
                description: 'Main AutoMINDX agent instance with iNFT capabilities, avatar support, and A2A protocol compliance. Personas loaded from agent workspace.',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'mastermind_prime',
                name: 'Mastermind Prime',
                type: 'Orchestration',
                status: 'active',
                isSystem: true,
                capabilities: ['System Orchestration', 'Component Management', 'Asynchronous Operations'],
                description: 'Mastermind prime instance of mindX with asynchronous component initialization and orchestration capabilities',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'sea_for_mastermind',
                name: 'Strategic Evolution Agent for Mastermind',
                type: 'Learning',
                status: 'active',
                isSystem: true,
                capabilities: ['Strategic Planning', 'System Evolution', 'Mistral-based Reasoning', 'Audit System'],
                description: 'Strategic Evolution Agent specifically configured for mastermind with Mistral-based core reasoning and integrated audit system',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'blueprint_agent_mindx_v2',
                name: 'Blueprint Agent MindX v2',
                type: 'Evolution',
                status: 'active',
                isSystem: true,
                capabilities: ['Blueprint Generation', 'System Design', 'Architecture Planning', 'LLM Integration'],
                description: 'Blueprint agent v2 for mindX with enhanced blueprint-to-action conversion capabilities and LLM integration',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'blueprint_to_action_converter_enhanced',
                name: 'Enhanced Blueprint to Action Converter',
                type: 'Evolution',
                status: 'active',
                isSystem: true,
                capabilities: ['Blueprint Conversion', 'Action Generation', 'Implementation Planning', 'Enhanced Processing'],
                description: 'Enhanced blueprint-to-action converter with advanced conversion capabilities for system implementation',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'plan_manager_sea',
                name: 'Plan Manager for SEA',
                type: 'Learning',
                status: 'active',
                isSystem: true,
                capabilities: ['Plan Management', 'Execution Control', 'Parallel Processing', 'Strategic Planning'],
                description: 'Plan manager specifically configured for Strategic Evolution Agent with parallel execution control and strategic planning',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'base_gen_agent_v1_1',
                name: 'Base Generation Agent v1.1',
                type: 'Code Generation',
                status: 'active',
                isSystem: true,
                capabilities: ['Code Generation', 'File Management', 'Configuration Handling', 'Size Management'],
                description: 'Base generation agent v1.1 with configurable file size limits and enhanced code generation capabilities',
                createdBy: 'system',
                lastActivity: 'Active'
            },
            {
                id: 'sea_audit_system',
                name: 'SEA Audit System',
                type: 'Audit',
                status: 'active',
                isSystem: true,
                capabilities: ['System Auditing', 'Component Analysis', 'Performance Monitoring', 'Strategic Assessment'],
                description: 'Audit system components for Strategic Evolution Agent with comprehensive system analysis and performance monitoring',
                createdBy: 'system',
                lastActivity: 'Active'
            }
        ];
        
        // Initialize with system agents
        agents = [...systemAgents];
        userAgents = [];
    }

    function initialize() {
        initializeSystemAgents();
        initializeTabs();
        initializeControlTab();
        initializeEvolutionTab();
        initializeAgentsTab();
        initializeSystemTab();
        initializeLogsTab();
        initializeTerminalTab();
        initializeAdminTab();
        initializeAutonomousMode();
        initializeAgentActivityMonitor();
        initializeUpdateRequests();
        
        // Force show control tab and load updates
        console.log('Forcing control tab visibility and loading updates...');
        setTimeout(() => {
            showControlTab();
        }, 1000);
        
        // Also try direct loading after a longer delay
        setTimeout(() => {
            console.log('Direct loading attempt...');
            loadUpdateRequests();
        }, 2000);
        
        // Check backend status periodically
    checkBackendStatus();
        setInterval(checkBackendStatus, 10000); // Check every 10 seconds
        
        // Start real agent activity monitoring
        startAgentActivitySimulation();
        
        // Load initial real agent activity
        loadInitialAgentActivity();
        
        addLog('MindX Control Panel initialized', 'INFO');
        addAgentActivity('System', 'MindX Control Panel initialized', 'success');
    }

    function initializeAgentActivityMonitor() {
        if (pauseActivityBtn) {
            pauseActivityBtn.addEventListener('click', pauseActivity);
        }
        if (clearActivityBtn) {
            clearActivityBtn.addEventListener('click', clearActivity);
        }
    }

    async function loadInitialAgentActivity() {
        try {
            const response = await fetch(`${apiUrl}/core/agent-activity`);
            if (response.ok) {
                const data = await response.json();
                if (data && data.activities) {
                    // Add initial activities
                    data.activities.slice(0, 5).forEach(activity => {
                        const activityKey = `${activity.timestamp}-${activity.agent}-${activity.message}`;
                        if (!seenActivities.has(activityKey)) {
                            seenActivities.add(activityKey);
                            addAgentActivity(activity.agent, activity.message, activity.type || 'info');
                        }
                    });
                }
            }
        } catch (error) {
            console.log('Initial agent activity load failed:', error.message);
        }
    }

    function startAgentActivitySimulation() {
        // Fetch REAL agent activity from mindX system
        setInterval(async () => {
            if (!activityPaused) {
                try {
                    // Try multiple endpoints to get real agent activity
                    const endpoints = [
                        '/core/agent-activity',
                        '/orchestration/coordinator/activity',
                        '/agents/activity',
                        '/system/agent-activity'
                    ];
                    
                    let activityFound = false;
                    for (const endpoint of endpoints) {
                        try {
                            const response = await fetch(`${apiUrl}${endpoint}`);
                            if (response.ok) {
                                const data = await response.json();
                                if (data && (data.activities || data.activity || data.logs)) {
                                    const activities = data.activities || data.activity || data.logs || [];
                                    activities.forEach(activity => {
                                        const activityKey = `${activity.timestamp || Date.now()}-${activity.agent || activity.source || 'Unknown'}-${activity.message || activity.text || activity.content}`;
                                        if (!seenActivities.has(activityKey)) {
                                            seenActivities.add(activityKey);
                                            addAgentActivity(
                                                activity.agent || activity.source || 'System', 
                                                activity.message || activity.text || activity.content, 
                                                activity.type || activity.level || 'info'
                                            );
                                        }
                                    });
                                    activityFound = true;
                                    break;
                                }
                            }
                        } catch (e) {
                            // Continue to next endpoint
                            continue;
                        }
                    }
                    
                    if (!activityFound) {
                        // If no real activity found, show system status
                        addAgentActivity('System', 'No active agent interactions detected', 'info');
                    }
                } catch (error) {
                    console.log('Failed to fetch real agent activity:', error.message);
                    addAgentActivity('System', `Activity monitoring error: ${error.message}`, 'error');
                }
            }
        }, 5000); // Check every 5 seconds for real activity
    }

    // AGInt Response Window Functions
    function showAGIntResponseWindow() {
        // Create AGInt response window if it doesn't exist
        if (!agintResponseWindow) {
            agintResponseWindow = document.createElement('div');
            agintResponseWindow.id = 'agint-response-window';
            agintResponseWindow.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 80%;
                max-width: 800px;
                height: 60%;
                background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
                border: 2px solid #00ff88;
                border-radius: 10px;
                box-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
                z-index: 10000;
                display: flex;
                flex-direction: column;
                font-family: 'Courier New', monospace;
                color: #00ff88;
            `;
            
            // Header
            const header = document.createElement('div');
            header.style.cssText = `
                padding: 15px;
                border-bottom: 1px solid #00ff88;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(0, 255, 136, 0.1);
            `;
            header.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <h3 style="margin: 0; color: #00ff88; text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);">AGInt Cognitive Loop</h3>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; color: #00ff88;">
                            <input type="checkbox" id="verbose-toggle" checked style="accent-color: #00ff88;">
                            Verbose Output
                        </label>
                        <label style="display: flex; align-items: center; gap: 5px; font-size: 12px; color: #00ff88;">
                            <input type="checkbox" id="code-changes-toggle" checked style="accent-color: #00ff88;">
                            Show Code Changes
                        </label>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span id="agint-status-indicator" style="font-size: 12px; color: #888;">Running...</span>
                    <button id="copy-agint-output" style="background: linear-gradient(135deg, #00aa88, #008866); border: 1px solid #00aa88; color: white; padding: 8px 15px; cursor: pointer; border-radius: 5px; font-weight: bold; box-shadow: 0 2px 5px rgba(0, 170, 136, 0.3);">Copy Output</button>
                    <button id="close-agint-window" style="background: linear-gradient(135deg, #ff4444, #cc0000); border: 1px solid #ff4444; color: white; padding: 8px 15px; cursor: pointer; border-radius: 5px; font-weight: bold; box-shadow: 0 2px 5px rgba(255, 68, 68, 0.3);">Close</button>                                                                     
                </div>
            `;
            
            // Content area
            const content = document.createElement('div');
            content.id = 'agint-response-content';
            content.style.cssText = `
                flex: 1;
                padding: 15px;
                overflow-y: auto;
                background: rgba(0, 0, 0, 0.3);
                font-size: 14px;
                line-height: 1.4;
            `;
            
            agintResponseWindow.appendChild(header);
            agintResponseWindow.appendChild(content);
            document.body.appendChild(agintResponseWindow);
            
            // Close button event
            const closeBtn = document.getElementById('close-agint-window');
            closeBtn.addEventListener('click', hideAGIntResponseWindow);
            
            // Copy button event
            const copyBtn = document.getElementById('copy-agint-output');
            copyBtn.addEventListener('click', function() {
                const content = document.getElementById('agint-response-content');
                if (content) {
                    const text = content.innerText || content.textContent;
                    navigator.clipboard.writeText(text).then(() => {
                        // Show feedback
                        const originalText = copyBtn.textContent;
                        copyBtn.textContent = 'Copied!';
                        copyBtn.style.background = 'linear-gradient(135deg, #00ff00, #00cc00)';
                        setTimeout(() => {
                            copyBtn.textContent = originalText;
                            copyBtn.style.background = 'linear-gradient(135deg, #00aa88, #008866)';
                        }, 2000);
                    }).catch(err => {
                        console.error('Failed to copy text: ', err);
                        // Fallback for older browsers
                        const textArea = document.createElement('textarea');
                        textArea.value = text;
                        document.body.appendChild(textArea);
                        textArea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textArea);
                        
                        const originalText = copyBtn.textContent;
                        copyBtn.textContent = 'Copied!';
                        copyBtn.style.background = 'linear-gradient(135deg, #00ff00, #00cc00)';
                        setTimeout(() => {
                            copyBtn.textContent = originalText;
                            copyBtn.style.background = 'linear-gradient(135deg, #00aa88, #008866)';
                        }, 2000);
                    });
                }
            });
            
            // Add hover effects for close button
            closeBtn.addEventListener('mouseenter', function() {
                this.style.background = 'linear-gradient(135deg, #ff6666, #ff0000)';
                this.style.transform = 'scale(1.05)';
            });
            closeBtn.addEventListener('mouseleave', function() {
                this.style.background = 'linear-gradient(135deg, #ff4444, #cc0000)';
                this.style.transform = 'scale(1)';
            });
            
            // Add hover effects for copy button
            copyBtn.addEventListener('mouseenter', function() {
                this.style.background = 'linear-gradient(135deg, #00ccaa, #00aa88)';
                this.style.transform = 'scale(1.05)';
            });
            copyBtn.addEventListener('mouseleave', function() {
                this.style.background = 'linear-gradient(135deg, #00aa88, #008866)';
                this.style.transform = 'scale(1)';
            });
        }
        
            // Clear previous content
            const content = document.getElementById('agint-response-content');
            content.innerHTML = `
                <div style="color: #00ff88; text-align: center; padding: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #00ff88;">AGInt Cognitive Loop Starting...</h4>
                    <div style="font-size: 12px; color: #888; margin-bottom: 15px;">
                        P-O-D-A Cycle: Perception → Orientation → Decision → Action
                    </div>
                    <div style="font-size: 11px; color: #666; background: rgba(0, 255, 136, 0.1); padding: 10px; border-radius: 5px; text-align: left;">
                        <strong>Verbose Mode Active:</strong><br>
                        🔍 PERCEPTION: System state analysis<br>
                        🧠 ORIENTATION: Options evaluation<br>
                        ⚡ DECISION: Strategy selection<br>
                        🚀 ACTION: Task execution<br>
                        🎯 DETAILS: Real-time action feedback
                    </div>
                </div>
            `;
        
        // Show the window
        agintResponseWindow.style.display = 'flex';
    }
    
    function updateAGIntResponse(data, output) {
        const content = document.getElementById('agint-response-content');
        if (!content) return;
        
        // Check toggle settings
        const verboseToggle = document.getElementById('verbose-toggle');
        const codeChangesToggle = document.getElementById('code-changes-toggle');
        const showVerbose = verboseToggle ? verboseToggle.checked : true;
        const showCodeChanges = codeChangesToggle ? codeChangesToggle.checked : true;
        
        // Update status indicator
        const statusIndicator = document.getElementById('agint-status-indicator');
        if (statusIndicator) {
            if (data.type === 'complete') {
                statusIndicator.textContent = '✅ Completed';
                statusIndicator.style.color = '#00ff88';
            } else if (data.type === 'error') {
                statusIndicator.textContent = '❌ Error';
                statusIndicator.style.color = '#ff4444';
            } else {
                statusIndicator.textContent = '🔄 Running...';
                statusIndicator.style.color = '#ffaa00';
            }
        }
        
        const timestamp = new Date().toLocaleTimeString();
        let message = '';
        
        switch (data.type) {
            case 'cycle_start':
                message = `[${timestamp}] 🔄 CYCLE ${data.cycle}/${data.max_cycles}: ${data.message}`;
                if (data.autonomous_mode) {
                    message += ` (Autonomous Mode)`;
                }
                break;
            case 'status':
                if (showVerbose) {
                    message = `[${timestamp}] ${data.icon} ${data.phase}: ${data.message}`;
                    if (data.cycle) {
                        message = `[${timestamp}] ${data.icon} CYCLE ${data.cycle}/${data.max_cycles} - ${data.phase}: ${data.message}`;
                    }
                    // Add detailed verbose information
                    if (data.state_summary) {
                        message += `\n    └─ LLM Status: ${data.state_summary.llm_status || 'Unknown'}`;
                        message += `\n    └─ Cognitive Loop: ${data.state_summary.cognitive_loop || 'Unknown'}`;
                        if (data.state_summary.awareness) {
                            message += `\n    └─ Awareness: ${data.state_summary.awareness}`;
                        }
                    }
                } else {
                    // Simplified output for non-verbose mode - just show phase and cycle
                    if (data.cycle) {
                        message = `[${timestamp}] 🔄 CYCLE ${data.cycle}/${data.max_cycles} - ${data.phase}`;
                    } else {
                        message = `[${timestamp}] ${data.icon} ${data.phase}`;
                    }
                }
                break;
            case 'cycle_complete':
                message = `[${timestamp}] ✅ CYCLE ${data.cycle}/${data.max_cycles} COMPLETE: ${data.message}`;
                if (data.cycle_duration) {
                    message += ` (${data.cycle_duration.toFixed(2)}s)`;
                }
                break;
            case 'verbose':
                if (showVerbose) {
                    message = `[${timestamp}] ${data.message}`;
                    if (data.details) {
                        message += `\n    └─ ${data.details}`;
                    }
                } else {
                    return; // Skip verbose messages when toggle is off
                }
                break;
            case 'action_detail':
                if (showVerbose) {
                    message = `[${timestamp}] 🎯 ACTION: ${data.action_type}`;
                    if (data.details && Object.keys(data.details).length > 0) {
                        message += `\n    └─ Details: ${JSON.stringify(data.details, null, 2)}`;
                    }
                    if (data.result && Object.keys(data.result).length > 0) {
                        message += `\n    └─ Result: ${JSON.stringify(data.result, null, 2)}`;
                    }
                    message += `\n    └─ Success: ${data.success ? '✅' : '❌'}`;
                } else {
                    return; // Skip action details when verbose is off
                }
                break;
            case 'phase':
                if (showVerbose) {
                    message = `[${timestamp}] ${data.phase}: ${data.message}`;
                } else {
                    return; // Skip phase messages when verbose is off
                }
                break;
            case 'cycle':
                message = `[${timestamp}] CYCLE ${data.cycle}: ${data.awareness}`;
                if (data.llm_operational !== undefined) {
                    message += ` | LLM: ${data.llm_operational ? 'Operational' : 'Offline'}`;
                }
                if (data.last_action) {
                    message += ` | Action: ${JSON.stringify(data.last_action)}`;
                }
                break;
            case 'complete':
                message = `[${timestamp}] ✅ COMPLETE: ${data.status}`;
                if (data.total_cycles) {
                    message += `\n    └─ Cycles Completed: ${data.total_cycles}`;
                }
                if (data.total_steps) {
                    message += `\n    └─ Total Steps: ${data.total_steps}`;
                }
                if (data.state_summary) {
                    message += `\n    └─ Awareness: ${data.state_summary.awareness || 'N/A'}`;
                    message += `\n    └─ LLM Operational: ${data.state_summary.llm_operational ? 'Yes' : 'No'}`;
                }
                if (data.last_action_context) {
                    message += `\n    └─ Final Action: ${JSON.stringify(data.last_action_context, null, 2)}`;
                }
                message += `\n\nClick the "Close" button above to close this window.`;
                break;
            case 'error':
                message = `[${timestamp}] ERROR: ${data.message}`;
                break;
            default:
                message = `[${timestamp}] ${JSON.stringify(data)}`;
        }
        
        const messageDiv = document.createElement('div');
        
        // Color coding for different message types
        let borderColor = '#00ff88';
        let bgColor = 'rgba(0, 255, 136, 0.05)';
        
        if (data.type === 'error') {
            borderColor = '#ff4444';
            bgColor = 'rgba(255, 68, 68, 0.1)';
        } else if (data.type === 'cycle_start') {
            borderColor = '#00aaff';
            bgColor = 'rgba(0, 170, 255, 0.1)';
        } else if (data.type === 'cycle_complete') {
            borderColor = '#00ff00';
            bgColor = 'rgba(0, 255, 0, 0.1)';
        } else if (data.type === 'verbose') {
            borderColor = '#ffaa00';
            bgColor = 'rgba(255, 170, 0, 0.15)';
        } else if (data.type === 'action_detail') {
            borderColor = '#ff6600';
            bgColor = 'rgba(255, 102, 0, 0.15)';
        } else if (data.type === 'phase') {
            borderColor = '#ffaa00';
            bgColor = 'rgba(255, 170, 0, 0.1)';
        } else if (data.type === 'cycle') {
            borderColor = '#00aaff';
            bgColor = 'rgba(0, 170, 255, 0.1)';
        } else if (data.type === 'complete') {
            borderColor = '#00ff00';
            bgColor = 'rgba(0, 255, 0, 0.1)';
        }
        
        messageDiv.style.cssText = `
            margin: 5px 0;
            padding: 8px;
            border-left: 3px solid ${borderColor};
            background: ${bgColor};
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        `;
        messageDiv.textContent = message;
        
        content.appendChild(messageDiv);
        
        // Add code changes display if present and toggle is enabled
        if (data.code_changes && data.code_changes.length > 0 && showCodeChanges) {
            const codeChangesDiv = document.createElement('div');
            codeChangesDiv.style.cssText = `
                margin: 10px 0;
                padding: 10px;
                border: 1px solid #00ff88;
                border-radius: 5px;
                background: rgba(0, 255, 136, 0.05);
                font-family: 'Courier New', monospace;
                font-size: 12px;
            `;
            
            let codeChangesHtml = `<div style="color: #00ff88; font-weight: bold; margin-bottom: 8px;">📝 Code Changes Detected:</div>`;
            
            data.code_changes.forEach(change => {
                codeChangesHtml += `<div style="margin-bottom: 8px;">`;
                codeChangesHtml += `<div style="color: #ffaa00; font-weight: bold;">📄 ${change.file} (${change.type})</div>`;
                
                change.changes.forEach(changeItem => {
                    if (changeItem.old && changeItem.new) {
                        codeChangesHtml += `<div style="margin-left: 10px; margin-bottom: 4px;">`;
                        codeChangesHtml += `<div style="color: #ff6666;">- Line ${changeItem.line}: ${changeItem.old}</div>`;
                        codeChangesHtml += `<div style="color: #66ff66;">+ Line ${changeItem.line}: ${changeItem.new}</div>`;
                        codeChangesHtml += `</div>`;
                    } else if (changeItem.new) {
                        codeChangesHtml += `<div style="margin-left: 10px; margin-bottom: 4px;">`;
                        codeChangesHtml += `<div style="color: #66ff66;">+ Line ${changeItem.line}: ${changeItem.new}</div>`;
                        codeChangesHtml += `</div>`;
                    } else if (changeItem.old) {
                        codeChangesHtml += `<div style="margin-left: 10px; margin-bottom: 4px;">`;
                        codeChangesHtml += `<div style="color: #ff6666;">- Line ${changeItem.line}: ${changeItem.old}</div>`;
                        codeChangesHtml += `</div>`;
                    }
                });
                
                codeChangesHtml += `</div>`;
            });
            
            codeChangesDiv.innerHTML = codeChangesHtml;
            content.appendChild(codeChangesDiv);
        }
        
        content.scrollTop = content.scrollHeight;
    }
    
    function hideAGIntResponseWindow() {
        if (agintResponseWindow) {
            agintResponseWindow.style.display = 'none';
        }
    }

    // System Monitoring Functions
    function startSystemMonitoring() {
        if (isMonitoring) return;
        
        isMonitoring = true;
        
        // Initial status check
        updateSystemStatus();
        updateMonitoringAgents();
        updateAllSystemFields();
        updateResourceFromSystemMetrics(); // Ensure resource monitor gets updated
        updateLastUpdateTime();
        
        monitoringInterval = setInterval(async () => {
            try {
                // Fetch system metrics and status
                const [metricsResponse, resourcesResponse, statusResponse] = await Promise.all([
                    fetch(`${apiUrl}/system/metrics`),
                    fetch(`${apiUrl}/system/resources`),
                    fetch(`${apiUrl}/system/status`)
                ]);
                
                if (metricsResponse.ok) {
                    const metrics = await metricsResponse.json();
                    updateSystemMetrics(metrics);
                }
                
                if (resourcesResponse.ok) {
                    const resources = await resourcesResponse.json();
                    updateResourceUsage(resources);
                }
                
                if (statusResponse.ok) {
                    const status = await statusResponse.json();
                    updateSystemStatus(status);
                }
                
                // Update monitoring agents
                updateMonitoringAgents();
                updateAllSystemFields();
                updateResourceFromSystemMetrics(); // Ensure resource monitor gets updated
                updateLastUpdateTime();
                updateSystemUptime();
                
                // System metrics updated (no output display needed)
                
                
            } catch (error) {
                console.error('System monitoring error:', error);
            }
        }, 5000); // Update every 5 seconds
    }
    
    function stopSystemMonitoring() {
        if (!isMonitoring) return;
        
        isMonitoring = false;
        if (monitoringInterval) {
            clearInterval(monitoringInterval);
            monitoringInterval = null;
        }
        
    }

    // Update monitoring agents data
    async function updateMonitoringAgents() {
        try {
            // Fetch performance agent data
            const perfResponse = await fetch(`${apiUrl}/system/performance-agent`);
            if (perfResponse.ok) {
                const perfData = await perfResponse.json();
                updatePerformanceAgentData(perfData);
            } else {
                // Fallback to system metrics for performance
                updatePerformanceFromSystemMetrics();
            }
            
            // Fetch resource agent data
            const resResponse = await fetch(`${apiUrl}/system/resource-agent`);
            if (resResponse.ok) {
                const resData = await resResponse.json();
                updateResourceAgentData(resData);
            } else {
                // Fallback to system metrics for resources
                updateResourceFromSystemMetrics();
            }
        } catch (error) {
            console.error('Error updating monitoring agents:', error);
            // Try fallback methods
            updatePerformanceFromSystemMetrics();
            updateResourceFromSystemMetrics();
        }
    }

    // Fallback function to get performance data from system metrics
    async function updatePerformanceFromSystemMetrics() {
        try {
            const response = await fetch(`${apiUrl}/system/metrics`);
            if (response.ok) {
                const metrics = await response.json();
                
                // Update performance metrics with system data
                document.getElementById('perf-total-calls').textContent = '0'; // Not available in system metrics
                document.getElementById('perf-success-rate').textContent = '100%'; // Assume success if system is running
                document.getElementById('perf-avg-latency').textContent = `${metrics.response_time || 0}ms`;
                document.getElementById('perf-total-cost').textContent = '$0.00'; // Not available in system metrics
            }
        } catch (error) {
            console.error('Error fetching system metrics:', error);
        }
    }

    // Update performance agent data display
    function updatePerformanceAgentData(data) {
        const statusIndicator = document.getElementById('perf-status-indicator');
        const statusText = document.getElementById('perf-agent-status');
        
        if (data.agent_status === 'active') {
            statusIndicator.className = 'status-dot active';
            statusText.textContent = 'Active';
            
            // Update metrics with actual data
            if (data.summary) {
                const totalCalls = data.summary.total_calls || 0;
                const successRate = data.summary.success_rate || 0;
                const avgLatency = data.summary.avg_latency || 0;
                const totalCost = data.summary.total_cost || 0;
                
                document.getElementById('perf-total-calls').textContent = totalCalls.toLocaleString();
                document.getElementById('perf-success-rate').textContent = `${(successRate * 100).toFixed(1)}%`;
                document.getElementById('perf-avg-latency').textContent = `${avgLatency.toFixed(1)}ms`;
                document.getElementById('perf-total-cost').textContent = `$${totalCost.toFixed(2)}`;
            } else if (data.all_metrics) {
                // Fallback to all_metrics if summary not available
                const metrics = data.all_metrics;
                let totalCalls = 0;
                let totalSuccess = 0;
                let totalLatency = 0;
                let totalCost = 0;
                
                Object.values(metrics).forEach(metric => {
                    totalCalls += metric.total_calls || 0;
                    totalSuccess += metric.successful_calls || 0;
                    totalLatency += metric.total_latency_ms || 0;
                    totalCost += metric.total_cost || 0;
                });
                
                const successRate = totalCalls > 0 ? totalSuccess / totalCalls : 0;
                const avgLatency = totalCalls > 0 ? totalLatency / totalCalls : 0;
                
                document.getElementById('perf-total-calls').textContent = totalCalls.toLocaleString();
                document.getElementById('perf-success-rate').textContent = `${(successRate * 100).toFixed(1)}%`;
                document.getElementById('perf-avg-latency').textContent = `${avgLatency.toFixed(1)}ms`;
                document.getElementById('perf-total-cost').textContent = `$${totalCost.toFixed(2)}`;
            }
        } else {
            statusIndicator.className = 'status-dot error';
            statusText.textContent = `Error: ${data.error || 'Unknown error'}`;
        }
    }

    // Update resource agent data display
    function updateResourceAgentData(data) {
        const statusIndicator = document.getElementById('res-status-indicator');
        const statusText = document.getElementById('res-agent-status');
        
        if (data.agent_status === 'active') {
            statusIndicator.className = 'status-dot active';
            statusText.textContent = 'Active';
            
            // Update metrics with actual data
            if (data.resource_usage) {
                const cpuUsage = data.resource_usage.cpu || 0;
                const memoryUsage = data.resource_usage.memory || 0;
                const diskUsage = data.resource_usage.disk || 0;
                const alerts = data.resource_usage.alerts || 0;
                
                document.getElementById('res-cpu-usage').textContent = `${cpuUsage.toFixed(1)}%`;
                document.getElementById('res-memory-usage').textContent = `${memoryUsage.toFixed(1)}%`;
                document.getElementById('res-disk-usage').textContent = `${diskUsage.toFixed(1)}%`;
                document.getElementById('res-alerts').textContent = alerts;
                
                // Update progress bars
                const cpuProgress = document.getElementById('res-cpu-progress');
                const memoryProgress = document.getElementById('res-memory-progress');
                const diskProgress = document.getElementById('res-disk-progress');
                
                if (cpuProgress) cpuProgress.style.width = `${cpuUsage}%`;
                if (memoryProgress) memoryProgress.style.width = `${memoryUsage}%`;
                if (diskProgress) diskProgress.style.width = `${diskUsage}%`;
                
                // Update additional system information if available
                if (data.detailed_metrics) {
                    updateSystemInfoFromDetailedMetrics(data.detailed_metrics);
                }
                
                // Update alerts if available
                if (data.alerts_summary) {
                    updateAlertsDisplay(data.alerts_summary);
                }
                
            } else {
                // Fallback to system metrics if resource agent data not available
                updateResourceFromSystemMetrics();
            }
        } else {
            statusIndicator.className = 'status-dot error';
            statusText.textContent = `Error: ${data.error || 'Unknown error'}`;
        }
    }

    // Update system information from detailed metrics
    function updateSystemInfoFromDetailedMetrics(detailedMetrics) {
        // Update any additional system information that might be displayed
        // This could include CPU cores, load average, uptime, etc.
        if (detailedMetrics.system) {
            // Update process count if element exists
            const processCountElement = document.getElementById('process-count');
            if (processCountElement) {
                processCountElement.textContent = detailedMetrics.system.process_count || '0';
            }
            
            // Update load average if element exists
            const loadAverageElement = document.getElementById('load-average');
            if (loadAverageElement && detailedMetrics.system.load_average) {
                const loadAvg = detailedMetrics.system.load_average;
                loadAverageElement.textContent = `${loadAvg[0].toFixed(2)}, ${loadAvg[1].toFixed(2)}, ${loadAvg[2].toFixed(2)}`;
            }
        }
        
        // Update memory details if elements exist
        if (detailedMetrics.memory) {
            const totalMemoryElement = document.getElementById('total-memory');
            const usedMemoryElement = document.getElementById('used-memory');
            const availableMemoryElement = document.getElementById('available-memory');
            
            if (totalMemoryElement) {
                totalMemoryElement.textContent = formatBytes(detailedMetrics.memory.total);
            }
            if (usedMemoryElement) {
                usedMemoryElement.textContent = formatBytes(detailedMetrics.memory.used);
            }
            if (availableMemoryElement) {
                availableMemoryElement.textContent = formatBytes(detailedMetrics.memory.available);
            }
        }
        
        // Update disk details if elements exist
        if (detailedMetrics.disk) {
            const diskSpaceElement = document.getElementById('disk-space');
            if (diskSpaceElement && detailedMetrics.disk.usage) {
                const rootUsage = detailedMetrics.disk.usage['/'] || 0;
                diskSpaceElement.textContent = `${rootUsage.toFixed(1)}% used`;
            }
        }
    }

    // Update alerts display
    function updateAlertsDisplay(alertsSummary) {
        // This could be used to display alerts in a dedicated section
        // For now, we just update the alert count which is already handled above
        if (alertsSummary.total_alerts > 0) {
            console.log(`Active alerts: ${alertsSummary.total_alerts}`, alertsSummary.recent_alerts);
        }
    }

    // Fallback function to get resource data from system metrics
    async function updateResourceFromSystemMetrics() {
        try {
            const response = await fetch(`${apiUrl}/system/resources`);
            if (response.ok) {
                const resources = await response.json();
                
                const cpuUsage = resources.cpu?.usage || 0;
                const memoryUsage = resources.memory?.percentage || 0;
                const diskUsage = resources.disk?.percentage || 0;
                
                // Update resource monitor section
                document.getElementById('res-cpu-usage').textContent = `${cpuUsage.toFixed(1)}%`;
                document.getElementById('res-memory-usage').textContent = `${memoryUsage.toFixed(1)}%`;
                document.getElementById('res-disk-usage').textContent = `${diskUsage.toFixed(1)}%`;
                document.getElementById('res-alerts').textContent = '0';
                
                // Update progress bars
                const cpuProgress = document.getElementById('res-cpu-progress');
                const memoryProgress = document.getElementById('res-memory-progress');
                const diskProgress = document.getElementById('res-disk-progress');
                
                if (cpuProgress) cpuProgress.style.width = `${cpuUsage}%`;
                if (memoryProgress) memoryProgress.style.width = `${memoryUsage}%`;
                if (diskProgress) diskProgress.style.width = `${diskUsage}%`;
                
                // Update status indicators
                const statusIndicator = document.getElementById('res-status-indicator');
                const statusText = document.getElementById('res-agent-status');
                if (statusIndicator) statusIndicator.className = 'status-dot active';
                if (statusText) statusText.textContent = 'Active (System Data)';
                
            } else {
                // Use mock data if API fails
                updateResourceMonitorWithMockData();
            }
        } catch (error) {
            console.error('Error fetching system resources:', error);
            // Use mock data as fallback
            updateResourceMonitorWithMockData();
        }
    }

    // Mock data for resource monitor when APIs fail
    function updateResourceMonitorWithMockData() {
        const cpuUsage = Math.random() * 30 + 10; // 10-40%
        const memoryUsage = Math.random() * 40 + 20; // 20-60%
        const diskUsage = Math.random() * 20 + 30; // 30-50%
        
        document.getElementById('res-cpu-usage').textContent = `${cpuUsage.toFixed(1)}%`;
        document.getElementById('res-memory-usage').textContent = `${memoryUsage.toFixed(1)}%`;
        document.getElementById('res-disk-usage').textContent = `${diskUsage.toFixed(1)}%`;
        document.getElementById('res-alerts').textContent = '0';
        
        // Update progress bars
        const cpuProgress = document.getElementById('res-cpu-progress');
        const memoryProgress = document.getElementById('res-memory-progress');
        const diskProgress = document.getElementById('res-disk-progress');
        
        if (cpuProgress) cpuProgress.style.width = `${cpuUsage}%`;
        if (memoryProgress) memoryProgress.style.width = `${memoryUsage}%`;
        if (diskProgress) diskProgress.style.width = `${diskUsage}%`;
        
        // Update status indicators
        const statusIndicator = document.getElementById('res-status-indicator');
        const statusText = document.getElementById('res-agent-status');
        if (statusIndicator) statusIndicator.className = 'status-dot active';
        if (statusText) statusText.textContent = 'Active (Mock Data)';
    }

    // Update system health indicator
    function updateSystemHealthIndicator(cpuUsage, memoryUsage, diskUsage, alerts) {
        const healthIndicator = document.getElementById('system-health-indicator');
        const overallStatus = document.getElementById('overall-status');
        
        let healthStatus = 'healthy';
        let healthClass = 'healthy';
        
        if (alerts > 0 || cpuUsage > 90 || memoryUsage > 90 || diskUsage > 90) {
            healthStatus = 'critical';
            healthClass = 'critical';
        } else if (cpuUsage > 70 || memoryUsage > 70 || diskUsage > 70) {
            healthStatus = 'warning';
            healthClass = 'warning';
        }
        
        if (healthIndicator) {
            healthIndicator.className = `health-indicator ${healthClass}`;
        }
        if (overallStatus) {
            overallStatus.textContent = healthStatus.charAt(0).toUpperCase() + healthStatus.slice(1);
        }
    }

    // Update system uptime
    function updateSystemUptime() {
        const uptimeElement = document.getElementById('system-uptime');
        if (uptimeElement) {
            const now = new Date();
            const uptime = now - window.systemStartTime;
            const hours = Math.floor(uptime / (1000 * 60 * 60));
            const minutes = Math.floor((uptime % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((uptime % (1000 * 60)) / 1000);
            uptimeElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    // Update last update timestamp
    function updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            const now = new Date();
            lastUpdateElement.textContent = now.toLocaleTimeString();
        }
    }

    // Comprehensive function to update all system fields with actual data
    async function updateAllSystemFields() {
        try {
            // Fetch comprehensive system data
            const [metricsResponse, resourcesResponse] = await Promise.all([
                fetch(`${apiUrl}/system/metrics`),
                fetch(`${apiUrl}/system/resources`)
            ]);
            
            if (metricsResponse.ok) {
                const metrics = await metricsResponse.json();
                updateSystemMetrics(metrics);
            } else {
                // Fallback to mock data if API not available
                updateSystemMetricsWithMockData();
            }
            
            if (resourcesResponse.ok) {
                const resources = await resourcesResponse.json();
                updateResourceUsage(resources);
            } else {
                // Fallback to mock data if API not available
                updateResourceUsageWithMockData();
            }
            
            // Update system health based on current metrics
            updateSystemHealthFromCurrentData();
            
        } catch (error) {
            console.error('Error updating all system fields:', error);
            // Use mock data as fallback
            updateSystemMetricsWithMockData();
            updateResourceUsageWithMockData();
        }
    }

    // Mock data fallback for system metrics
    function updateSystemMetricsWithMockData() {
        const mockMetrics = {
            cpu_usage: Math.random() * 30 + 10, // 10-40%
            memory_usage: Math.random() * 40 + 20, // 20-60%
            disk_usage: Math.random() * 20 + 30, // 30-50%
            network_usage: Math.random() * 15 + 5 // 5-20%
        };
        updateSystemMetrics(mockMetrics);
    }

    // Mock data fallback for resource usage
    function updateResourceUsageWithMockData() {
        const mockResources = {
            memory: {
                total: '16.0 GB',
                used: '8.2 GB',
                free: '7.8 GB'
            },
            disk: {
                used: '245.6 GB',
                total: '500.0 GB'
            },
            cpu: {
                cores: 8,
                load_avg: ['0.45', '0.52', '0.48']
            },
            process_count: Math.floor(Math.random() * 200) + 150 // 150-350 processes
        };
        updateResourceUsage(mockResources);
    }

    // Update system health based on current displayed data
    function updateSystemHealthFromCurrentData() {
        const cpuElement = document.getElementById('cpu-usage-text');
        const memoryElement = document.getElementById('memory-usage-text');
        const diskElement = document.getElementById('disk-usage-text');
        
        if (cpuElement && memoryElement && diskElement) {
            const cpuUsage = parseFloat(cpuElement.textContent) || 0;
            const memoryUsage = parseFloat(memoryElement.textContent) || 0;
            const diskUsage = parseFloat(diskElement.textContent) || 0;
            
            let healthStatus = 'Healthy';
            let healthClass = 'healthy';
            
            if (cpuUsage > 90 || memoryUsage > 90 || diskUsage > 90) {
                healthStatus = 'Critical';
                healthClass = 'critical';
            } else if (cpuUsage > 70 || memoryUsage > 70 || diskUsage > 70) {
                healthStatus = 'Warning';
                healthClass = 'warning';
            }
            
            // Update health indicators if they exist
            const healthIndicator = document.getElementById('system-health-indicator');
            const overallStatus = document.getElementById('overall-status');
            
            if (healthIndicator) {
                healthIndicator.className = `health-indicator ${healthClass}`;
            }
            if (overallStatus) {
                overallStatus.textContent = healthStatus;
            }
        }
    }
    
    function updateSystemMetrics(metrics) {
        // Update CPU usage
        const cpuUsage = metrics.cpu_usage || 0;
        const cpuBar = document.getElementById('cpu-usage-bar');
        const cpuText = document.getElementById('cpu-usage-text');
        cpuBar.style.width = `${cpuUsage}%`;
        cpuText.textContent = `${cpuUsage.toFixed(1)}%`;
        
        // Update Memory usage
        const memoryUsage = metrics.memory_usage || 0;
        const memoryBar = document.getElementById('memory-usage-bar');
        const memoryText = document.getElementById('memory-usage-text');
        memoryBar.style.width = `${memoryUsage}%`;
        memoryText.textContent = `${memoryUsage.toFixed(1)}%`;
        
        // Update Disk usage
        const diskUsage = metrics.disk_usage || 0;
        const diskBar = document.getElementById('disk-usage-bar');
        const diskText = document.getElementById('disk-usage-text');
        diskBar.style.width = `${diskUsage}%`;
        diskText.textContent = `${diskUsage.toFixed(1)}%`;
        
        // Update Network usage
        const networkUsage = metrics.network_usage || 0;
        const networkBar = document.getElementById('network-usage-bar');
        const networkText = document.getElementById('network-usage-text');
        networkBar.style.width = `${networkUsage}%`;
        networkText.textContent = `${networkUsage.toFixed(1)}%`;
    }
    
    function updateResourceUsage(resources) {
        // Update memory details with actual data
        if (resources.memory) {
            document.getElementById('total-memory').textContent = resources.memory.total || 'Unknown';
            document.getElementById('used-memory').textContent = resources.memory.used || 'Unknown';
            document.getElementById('available-memory').textContent = resources.memory.free || 'Unknown';
        }
        
        // Update disk details with actual data
        if (resources.disk) {
            document.getElementById('disk-space').textContent = `${resources.disk.used} / ${resources.disk.total}`;
        }
        
        // Update CPU details
        if (resources.cpu) {
            const cpuCores = resources.cpu.cores || 'Unknown';
            const cpuLoad = resources.cpu.load_avg ? resources.cpu.load_avg.join(', ') : 'Unknown';
            // Update any CPU-related fields if they exist
        }
        
        // Update process count and load average
        document.getElementById('process-count').textContent = resources.process_count || 'Unknown';
        if (resources.cpu && resources.cpu.load_avg) {
            document.getElementById('load-average').textContent = resources.cpu.load_avg.join(', ');
        } else {
            document.getElementById('load-average').textContent = 'Unknown';
        }
    }
    
    function updateSystemStatus(status) {
        // Update system health
        if (status.status) {
            const healthElement = document.getElementById('system-health');
            healthElement.textContent = status.status;
            healthElement.className = `status-value ${status.status === 'operational' ? 'success' : 'error'}`;
        }
        
        // Update uptime
        if (status.uptime) {
            document.getElementById('system-uptime').textContent = formatUptime(status.uptime);
        }
        
        // Update active agents count
        if (status.components && status.components.active_agents) {
            document.getElementById('active-agents-count').textContent = status.components.active_agents;
        }
        
        // Update LLM provider status
        if (status.components && status.components.llm_provider) {
            const llmElement = document.getElementById('llm-provider-status');
            llmElement.textContent = status.components.llm_provider;
            llmElement.className = `status-value ${status.components.llm_provider === 'online' ? 'success' : 'error'}`;
        }
        
        // Update Mistral API status
        updateMistralStatus();
        
        // Update AGInt status
        updateAGIntStatus();
        
        // Update Coordinator status
        updateCoordinatorStatus();
    }
    
    async function updateMistralStatus() {
        try {
            const response = await fetch(`${apiUrl}/test/mistral`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test: 'connectivity', message: 'Status check' })
            });
            
            const mistralElement = document.getElementById('mistral-api-status');
            if (response.ok) {
                mistralElement.textContent = 'Online';
                mistralElement.className = 'status-value success';
            } else {
                mistralElement.textContent = 'Offline';
                mistralElement.className = 'status-value error';
            }
        } catch (error) {
            const mistralElement = document.getElementById('mistral-api-status');
            mistralElement.textContent = 'Error';
            mistralElement.className = 'status-value error';
        }
    }
    
    async function updateAGIntStatus() {
        try {
            const response = await fetch(`${apiUrl}/commands/agint`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ directive: 'status check' })
            });
            
            const agintElement = document.getElementById('agint-status');
            if (response.ok) {
                const data = await response.json();
                if (data.state_summary && data.state_summary.llm_operational) {
                    agintElement.textContent = `Online - ${data.state_summary.llm_status}`;
                    agintElement.className = 'status-value success';
                } else {
                    agintElement.textContent = 'Offline';
                    agintElement.className = 'status-value error';
                }
            } else {
                agintElement.textContent = 'Error';
                agintElement.className = 'status-value error';
            }
        } catch (error) {
            const agintElement = document.getElementById('agint-status');
            agintElement.textContent = 'Error';
            agintElement.className = 'status-value error';
        }
    }
    
    async function updateCoordinatorStatus() {
        try {
            const response = await fetch(`${apiUrl}/orchestration/coordinator`);
            
            const coordinatorElement = document.getElementById('coordinator-status');
            if (response.ok) {
                const data = await response.json();
                coordinatorElement.textContent = 'Online';
                coordinatorElement.className = 'status-value success';
            } else {
                coordinatorElement.textContent = 'Offline';
                coordinatorElement.className = 'status-value error';
            }
        } catch (error) {
            const coordinatorElement = document.getElementById('coordinator-status');
            coordinatorElement.textContent = 'Error';
            coordinatorElement.className = 'status-value error';
        }
    }
    
    function formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    
    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Auto-start monitoring on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Start monitoring automatically when page loads
        setTimeout(() => {
            startSystemMonitoring();
        }, 2000);
    });

    // Export metrics data functionality
    function exportMetricsData() {
        try {
            const exportData = {
                timestamp: new Date().toISOString(),
                system_health: {
                    overall_status: document.getElementById('overall-status')?.textContent || 'Unknown',
                    uptime: document.getElementById('system-uptime')?.textContent || '00:00:00',
                    last_update: document.getElementById('last-update')?.textContent || 'Never'
                },
                performance_metrics: {
                    total_calls: document.getElementById('perf-total-calls')?.textContent || '-',
                    success_rate: document.getElementById('perf-success-rate')?.textContent || '-',
                    avg_latency: document.getElementById('perf-avg-latency')?.textContent || '-',
                    total_cost: document.getElementById('perf-total-cost')?.textContent || '-'
                },
                resource_metrics: {
                    cpu_usage: document.getElementById('res-cpu-usage')?.textContent || '-',
                    memory_usage: document.getElementById('res-memory-usage')?.textContent || '-',
                    disk_usage: document.getElementById('res-disk-usage')?.textContent || '-',
                    alerts: document.getElementById('res-alerts')?.textContent || '-'
                }
            };
            
            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `mindx-metrics-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            // Show success message
            const output = document.getElementById('monitoring-output');
            const timestamp = new Date().toLocaleTimeString();
            output.innerHTML = `<div class="monitoring-entry">[${timestamp}] Metrics data exported successfully</div>` + output.innerHTML;
            
                } catch (error) {
            console.error('Error exporting metrics:', error);
            const output = document.getElementById('monitoring-output');
            const timestamp = new Date().toLocaleTimeString();
            output.innerHTML = `<div class="monitoring-entry error">[${timestamp}] Export failed: ${error.message}</div>` + output.innerHTML;
        }
    }

    // Add export button event listener
    const exportBtn = document.getElementById('export-metrics-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportMetricsData);
    }

    // Start the application
    initialize();
});