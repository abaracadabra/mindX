document.addEventListener('DOMContentLoaded', () => {
    const backendPort = window.MINDX_BACKEND_PORT || '8000';
    const apiUrl = `http://localhost:${backendPort}`;
    
    // Global state
    let isAutonomousMode = false;
    let activityPaused = false;
    let activityLog = [];
    let seenActivities = new Set(); // Track activities we've already seen
    let autonomousInterval = null;
    let logs = [];
    let terminalHistory = [];
    let agents = [];
    let selectedAgent = null;
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
    const analyzeBtn = document.getElementById('analyze-btn');
    const replicateBtn = document.getElementById('replicate-btn');
    const improveBtn = document.getElementById('improve-btn');
    const testMistralBtn = document.getElementById('test-mistral-btn');
    const evolveDirectiveInput = document.getElementById('evolve-directive');
    const queryInput = document.getElementById('query-input');

    // Agents tab elements
    const refreshAgentsBtn = document.getElementById('refresh-agents-btn');
    const createAgentBtn = document.getElementById('create-agent-btn');
    const deleteAgentBtn = document.getElementById('delete-agent-btn');
    const agentsList = document.getElementById('agents-list');
    const agentDetails = document.getElementById('agent-details');
    
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
                                
                                if (data.type === 'status') {
                                    addAgentActivity('AGInt', data.message, 'info');
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
                                    
                                    // Update AGInt response window with completion status
                                    updateAGIntResponse(data, null);
                                    
                                    // Display final results
                                    let displayText = `AGInt Cognitive Loop Results:\n\n`;
                                    displayText += `Status: ${data.status}\n`;
                                    if (data.state_summary) {
                                        displayText += `Awareness: ${data.state_summary.awareness || 'N/A'}\n`;
                                        displayText += `LLM Operational: ${data.state_summary.llm_operational ? 'Yes' : 'No'}\n`;
                                    }
                                    if (data.last_action_context) {
                                        displayText += `Last Action: ${JSON.stringify(data.last_action_context, null, 2)}\n`;
                                    }
                                    
                                    showResponse(displayText);
                                    
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
                evolveBtn.textContent = 'Evolve';
                // Don't auto-close the window - let user close manually
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
                    
                    // Parse and display the response in a more readable format
                    let displayText = '';
                    if (response.status) {
                        displayText += `Status: ${response.status}\n`;
                    }
                    if (response.message) {
                        displayText += `Message: ${response.message}\n`;
                    }
                    if (response.content) {
                        displayText += `Content: ${response.content}\n`;
                    }
                    if (response.interaction_id) {
                        displayText += `Interaction ID: ${response.interaction_id}\n`;
                    }
                    
                    displayText += '\nFull Response:\n' + JSON.stringify(response, null, 2);
                    showResponse(displayText);
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

        statusBtn.addEventListener('click', async () => {
            addLog('Checking Mastermind status...', 'INFO');
            addAgentActivity('Mastermind Agent', 'Checking status', 'info');
            
            try {
                const response = await sendRequest('/status/mastermind');
                if (response) {
                    addLog(`Mastermind status: ${JSON.stringify(response)}`, 'SUCCESS');
                    addAgentActivity('Mastermind Agent', 'Status retrieved successfully', 'success');
                    showResponse(JSON.stringify(response, null, 2));
                }
            } catch (error) {
                addLog(`Status check failed: ${error.message}`, 'ERROR');
                addAgentActivity('Mastermind Agent', `Status check failed: ${error.message}`, 'error');
                showResponse(`Status check failed: ${error.message}`);
            }
        });

        agentsBtn.addEventListener('click', async () => {
            addLog('Fetching agents registry...', 'INFO');
            addAgentActivity('Agent Registry', 'Fetching agents list', 'info');
            
            try {
                const response = await sendRequest('/registry/agents');
                if (response) {
                    addLog(`Agents retrieved: ${JSON.stringify(response)}`, 'SUCCESS');
                    addAgentActivity('Agent Registry', 'Agents list retrieved successfully', 'success');
                    showResponse(JSON.stringify(response, null, 2));
                }
            } catch (error) {
                addLog(`Agents list failed: ${error.message}`, 'ERROR');
                addAgentActivity('Agent Registry', `Agents list failed: ${error.message}`, 'error');
                showResponse(`Agents list failed: ${error.message}`);
            }
        });

        toolsBtn.addEventListener('click', async () => {
            addLog('Fetching tools registry...', 'INFO');
            addAgentActivity('Tool Registry', 'Fetching tools list', 'info');
            
            try {
                const response = await sendRequest('/registry/tools');
                if (response) {
                    addLog(`Tools retrieved: ${JSON.stringify(response)}`, 'SUCCESS');
                    addAgentActivity('Tool Registry', 'Tools list retrieved successfully', 'success');
                    showResponse(JSON.stringify(response, null, 2));
                }
            } catch (error) {
                addLog(`Tools list failed: ${error.message}`, 'ERROR');
                addAgentActivity('Tool Registry', `Tools list failed: ${error.message}`, 'error');
                showResponse(`Tools list failed: ${error.message}`);
            }
        });

        analyzeBtn.addEventListener('click', async () => {
            const path = prompt('Enter codebase path to analyze:', './');
            if (path) {
                try {
                    await sendRequest('/commands/analyze_codebase', 'POST', { path, focus: 'general' });
                } catch (error) {
                    addLog(`Analysis failed: ${error.message}`, 'ERROR');
                }
            }
        });

        replicateBtn.addEventListener('click', async () => {
            try {
                await sendRequest('/coordinator/analyze', 'POST', { context: 'replication' });
            } catch (error) {
                addLog(`Replication failed: ${error.message}`, 'ERROR');
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
                
                if (bdiResponse.goals) {
                    bdiGoals.innerHTML = bdiResponse.goals.map(goal => 
                        `<div class="goal-item">
                            <div class="goal-priority priority-${goal.priority || 'medium'}">${goal.priority || 'medium'}</div>
                            <div class="goal-description">${goal.description || goal}</div>
                        </div>`
                    ).join('');
                }
                if (bdiResponse.plans) {
                    bdiPlans.innerHTML = bdiResponse.plans.map(plan => 
                        `<div class="plan-item">
                            <div class="plan-status">${plan.status || 'active'}</div>
                            <div class="plan-description">${plan.description || plan}</div>
                        </div>`
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
        } catch (error) {
            addLog(`Failed to load core systems: ${error.message}`, 'ERROR');
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
        if (agents.length === 0) {
            agentsList.innerHTML = '<p>No agents available</p>';
            return;
        }

        agentsList.innerHTML = agents.map((agent, index) => {
            const agentId = agent.id || agent.name || `Agent ${index}`;
            const agentType = agent.type || 'Unknown';
            const isSelected = selectedAgent === agentId ? 'selected' : '';
            
            return `
                <div class="agent-item ${isSelected}" data-agent-id="${agentId}">
                    <div class="agent-info">
                        <h4>${agentId}</h4>
                        <p>Type: ${agentType}</p>
                    </div>
                </div>
            `;
        }).join('');

        // Add click listeners to agent items
        agentsList.querySelectorAll('.agent-item').forEach(item => {
            item.addEventListener('click', () => {
                const agentId = item.getAttribute('data-agent-id');
                selectAgent(agentId);
            });
        });
    }

    function selectAgent(agentId) {
        selectedAgent = agentId;
        displayAgents(); // Refresh to show selection
        displayAgentDetails(agentId);
    }

    function displayAgentDetails(agentId) {
        const agent = agents.find(a => (a.id || a.name) === agentId);
        if (!agent) {
            agentDetails.innerHTML = '<p>Agent not found</p>';
            return;
        }

        agentDetails.innerHTML = `
            <h3>${agentId}</h3>
            <div class="agent-detail">
                <strong>Type:</strong> ${agent.type || 'Unknown'}
            </div>
            <div class="agent-detail">
                <strong>Status:</strong> ${agent.status || 'Unknown'}
            </div>
            <div class="agent-detail">
                <strong>Details:</strong> ${JSON.stringify(agent, null, 2)}
            </div>
        `;
    }

    async function createAgent() {
        const agentType = prompt('Enter agent type:', 'simple_coder');
        const agentId = prompt('Enter agent ID:', `agent_${Date.now()}`);
        
        if (agentType && agentId) {
            try {
                await sendRequest('/agents', 'POST', {
                    agent_type: agentType,
                    agent_id: agentId,
                    config: {}
                });
                addLog(`Agent ${agentId} created successfully`, 'INFO');
                loadAgents();
            } catch (error) {
                addLog(`Failed to create agent: ${error.message}`, 'ERROR');
            }
        }
    }

    async function deleteAgent() {
        if (!selectedAgent) {
            showResponse('Please select an agent to delete');
            return;
        }
        
        if (confirm(`Are you sure you want to delete agent ${selectedAgent}?`)) {
            try {
                await sendRequest(`/agents/${selectedAgent}`, 'DELETE');
                addLog(`Agent ${selectedAgent} deleted successfully`, 'INFO');
                selectedAgent = null;
                loadAgents();
            } catch (error) {
                addLog(`Failed to delete agent: ${error.message}`, 'ERROR');
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

    function initialize() {
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
        
        // Check backend status periodically
    checkBackendStatus();
        setInterval(checkBackendStatus, 10000); // Check every 10 seconds
        
        // Start agent activity simulation
        startAgentActivitySimulation();
        
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

    function startAgentActivitySimulation() {
        // Fetch real agent activity from the backend
        setInterval(async () => {
            if (!activityPaused) {
                try {
                    const response = await sendRequest('/core/agent-activity');
                    if (response && response.activities) {
                        // Add new activities that we haven't seen before
                        response.activities.forEach(activity => {
                            const activityKey = `${activity.timestamp}-${activity.agent}-${activity.message}`;
                            if (!seenActivities.has(activityKey)) {
                                seenActivities.add(activityKey);
                                addAgentActivity(activity.agent, activity.message, activity.type);
                            }
                        });
                    }
                } catch (error) {
                    // Fallback to simulated activity if real data fails
                    const agents = ['BDI Agent', 'Blueprint Agent', 'Strategic Evolution Agent', 'Mastermind Agent', 'Coordinator Agent', 'CEO Agent'];
                    const activities = [
                        'Processing new goal',
                        'Updating belief system',
                        'Executing plan',
                        'Analyzing system state',
                        'Coordinating with other agents',
                        'Making strategic decision',
                        'Learning from experience',
                        'Generating blueprint',
                        'Converting action',
                        'Monitoring performance'
                    ];
                    
                    const agent = agents[Math.floor(Math.random() * agents.length)];
                    const activity = activities[Math.floor(Math.random() * activities.length)];
                    const types = ['info', 'success', 'warning'];
                    const type = types[Math.floor(Math.random() * types.length)];
                    
                    addAgentActivity(agent, activity, type);
                }
            }
        }, 2000); // Check every 2 seconds
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
                <h3 style="margin: 0; color: #00ff88; text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);">AGInt Cognitive Loop</h3>                                                      
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
            case 'status':
                message = `[${timestamp}] STATUS: ${data.message}`;
                break;
            case 'verbose':
                message = `[${timestamp}] ${data.message}`;
                if (data.details) {
                    message += `\n    └─ ${data.details}`;
                }
                break;
            case 'action_detail':
                message = `[${timestamp}] 🎯 ACTION: ${data.action_type}`;
                if (data.details && Object.keys(data.details).length > 0) {
                    message += `\n    └─ Details: ${JSON.stringify(data.details, null, 2)}`;
                }
                if (data.result && Object.keys(data.result).length > 0) {
                    message += `\n    └─ Result: ${JSON.stringify(data.result, null, 2)}`;
                }
                message += `\n    └─ Success: ${data.success ? '✅' : '❌'}`;
                break;
            case 'phase':
                message = `[${timestamp}] ${data.phase}: ${data.message}`;
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
                if (data.state_summary) {
                    message += `\n    └─ Awareness: ${data.state_summary.awareness || 'N/A'}`;
                    message += `\n    └─ LLM Operational: ${data.state_summary.llm_operational ? 'Yes' : 'No'}`;
                }
                if (data.last_action_context) {
                    message += `\n    └─ Final Action: ${JSON.stringify(data.last_action_context, null, 2)}`;
                }
                message += `\n\n🎉 AGInt Cognitive Loop Completed Successfully! 🎉`;
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
        content.scrollTop = content.scrollHeight;
    }
    
    function hideAGIntResponseWindow() {
        if (agintResponseWindow) {
            agintResponseWindow.style.display = 'none';
        }
    }

    // Start the application
    initialize();
});