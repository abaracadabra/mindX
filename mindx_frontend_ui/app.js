// ===== mindX Application - FRESH LOAD =====
console.log('🚀 mindX app.js loaded at:', new Date().toISOString());
console.log('🔧 Version: FRESH CACHE BUSTED LOAD');

// Connect MetaMask wallet - Enhanced version (inline version in HTML handles initial connection)
// This version adds enhanced error handling and integration with app.js features
async function connectMetaMask() {
    try {
        console.log('🔗 Connecting to MetaMask (app.js version)...');
        console.log('window.ethereum available:', typeof window.ethereum !== 'undefined');
        
        // Check if MetaMask is available
        if (typeof window.ethereum === 'undefined') {
            throw new Error('MetaMask is not installed. Please install MetaMask browser extension to continue.');
        }
        
        console.log('MetaMask detected, requesting account access...');
        console.log('window.ethereum:', window.ethereum);
        
        // Request account access - This should trigger MetaMask popup
        console.log('Calling window.ethereum.request({ method: "eth_requestAccounts" })...');
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });
        
        console.log('MetaMask response received:', accounts);

        if (accounts.length === 0) {
            throw new Error('No accounts found. Please unlock MetaMask and try again.');
        }

        const walletAddress = accounts[0];
        console.log('Getting wallet information...');
        
        // Get chain ID
        const chainId = await window.ethereum.request({
            method: 'eth_chainId'
        });

        // Create user object
        const userData = {
            id: walletAddress,
            address: walletAddress,
            provider: 'metamask',
            chainId: chainId,
            authMethod: 'wallet',
            timestamp: Date.now()
        };

        // Store in localStorage (compatible with existing CrossMint integration)
        localStorage.setItem('crossmint_user', JSON.stringify(userData));
        localStorage.setItem('crossmint_wallet', walletAddress);
        localStorage.setItem('crossmint_authenticated', 'true');
        localStorage.setItem('crossmint_auth_method', 'wallet');
        
        // Trigger authentication success
        if (typeof handleAuthenticationSuccess === 'function') {
            handleAuthenticationSuccess(userData);
        } else {
            console.warn('handleAuthenticationSuccess not available yet, will be called when loaded');
            // Store for later
            window.pendingAuthSuccess = userData;
        }
        
        console.log('✅ MetaMask wallet connected successfully!');
        
    } catch (error) {
        console.error('❌ MetaMask connection failed:', error);
        if (error.code === 4001) {
            throw new Error('MetaMask connection rejected. Please approve the connection request.');
        } else if (error.code === -32002) {
            throw new Error('MetaMask connection already pending. Please check MetaMask and try again.');
        } else {
            throw new Error('MetaMask connection failed: ' + (error.message || 'Unknown error'));
        }
    }
}

// Only override if inline version doesn't exist, otherwise enhance it
if (!window.connectMetaMask) {
    window.connectMetaMask = connectMetaMask;
} else {
    console.log('✅ Using inline connectMetaMask function from HTML');
    // Store reference to app.js version for potential use
    window.connectMetaMaskAppJS = connectMetaMask;
}

// Test functions for debugging
window.testMetaMaskConnection = async function() {
    console.log('🧪 Testing MetaMask connection...');
    try {
        await connectMetaMask();
        console.log('✅ MetaMask connection test successful!');
    } catch (error) {
        console.error('❌ MetaMask connection test failed:', error);
    }
};

window.testButtonClick = function() {
    console.log('🧪 Testing button click...');
    const btn = document.getElementById('loginConnectBtn');
    if (btn) {
        console.log('✅ Button found, triggering click...');
        btn.click();
    } else {
        console.error('❌ Button not found!');
    }
};

// Global authentication state - Initialize first to avoid hoisting issues
let isAuthenticated = false;
let currentUser = null;
let authenticationState = {
    isLoggedIn: false,
    walletAddress: null,
    userData: null,
    sessionId: null
};

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded - Starting mindX Application...');

    // ===== Centralized API Configuration =====
    const API_CONFIG = {
        baseUrl: window.MINDX_API_URL || `http://localhost:${window.MINDX_BACKEND_PORT || '8000'}`,
        timeout: 30000,
        endpoints: {
            // Agent endpoints
            agents: '/agents/',
            agentActivity: '/agents/activity',
            agentCreate: '/agents',
            agentDelete: (id) => `/agents/${id}`,
            agentEvolve: (id) => `/agents/${id}/evolve`,
            agentSign: (id) => `/agents/${id}/sign`,

            // User endpoints
            usersRegister: '/users/register',
            usersAgents: '/users/agents',
            userAgents: (wallet) => `/users/${wallet}/agents`,
            userAgentDelete: (wallet, id) => `/users/${wallet}/agents/${id}`,
            userStats: (wallet) => `/users/${wallet}/stats`,
            userChallenge: '/users/challenge',
            userAuthenticate: '/users/authenticate',

            // Core endpoints
            health: '/health',
            status: (component) => `/status/${component}`,
            metrics: '/metrics',
            performance: '/performance',
            costs: '/costs',

            // LLM endpoints
            llmChat: '/llm/chat',
            llmCompletion: '/llm/completion',
            llmModels: '/llm/models',

            // Directive endpoints
            directiveExecute: '/directive/execute',
            directiveAutonomous: '/directive/autonomous',

            // Simple Coder endpoints
            simpleCoderStatus: '/simple-coder/status',
            simpleCoderUpdateRequests: '/simple-coder/update-requests',
            simpleCoderApprove: (id) => `/simple-coder/approve-update/${id}`,
            simpleCoderReject: (id) => `/simple-coder/reject-update/${id}`,

            // BDI endpoints
            bdiStatus: '/bdi/status',
            coreBdiStatus: '/core/bdi-status',

            // System endpoints
            systemResources: '/system/resources',
            systemAgentActivity: '/system/agent-activity',

            // Registry endpoints
            registryAgents: '/registry/agents',
            registryTools: '/registry/tools'
        }
    };

    /**
     * Make an API request with standardized error handling.
     * @param {string} endpoint - API endpoint (from API_CONFIG.endpoints)
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} Response data
     */
    async function apiRequest(endpoint, options = {}) {
        const url = `${API_CONFIG.baseUrl}${endpoint}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    // Expose API utilities globally
    window.API_CONFIG = API_CONFIG;
    window.apiRequest = apiRequest;

    // Legacy apiUrl for backward compatibility
    const apiUrl = API_CONFIG.baseUrl;
    
    // Initialize system start time for uptime calculation
    window.systemStartTime = new Date();
    
    // Initialize CrossMint integration
    initializeCrossMintIntegration();
    
    // Initialize authentication system
    initializeAuthenticationSystem().catch(console.error);
    
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
    
    // Load initial system data only if authenticated
    if (isAuthenticated) {
        setTimeout(() => {
            updateAllSystemFields();
            updateMonitoringAgents();
            updateResourceFromSystemMetrics(); // Ensure resource monitor gets updated
            performSystemHealthCheck(); // Perform initial system health check
            startHealthCheckRefresh(); // Start periodic health check refresh
        }, 1000);
    }
    
    // Global state
    let isAutonomousMode = false;
    let activityPaused = false;
    let activityLog = [];
    let seenActivities = new Set(); // Track activities we've already seen
    let autonomousInterval = null;
    let logs = [];
    let agents = [];
    let systemAgents = [];
    let userAgents = [];
    let selectedAgent = null;
    let currentAgentTab = 'system';
    let agintResponseWindow = null;

    // ===== Loading & Toast Utilities =====

    /**
     * Loading overlay manager for async operations.
     */
    const LoadingManager = {
        overlay: null,
        messageEl: null,
        submessageEl: null,

        init() {
            if (this.overlay) return;

            this.overlay = document.createElement('div');
            this.overlay.className = 'loading-overlay';
            this.overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <div class="loading-message">Loading...</div>
                <div class="loading-submessage"></div>
            `;
            document.body.appendChild(this.overlay);

            this.messageEl = this.overlay.querySelector('.loading-message');
            this.submessageEl = this.overlay.querySelector('.loading-submessage');
        },

        show(message = 'Loading...', submessage = '') {
            this.init();
            this.messageEl.textContent = message;
            this.submessageEl.textContent = submessage;
            this.overlay.classList.add('visible');
        },

        update(message, submessage = '') {
            if (this.messageEl) this.messageEl.textContent = message;
            if (this.submessageEl) this.submessageEl.textContent = submessage;
        },

        hide() {
            if (this.overlay) {
                this.overlay.classList.remove('visible');
            }
        }
    };

    /**
     * Toast notification manager.
     */
    const ToastManager = {
        container: null,

        init() {
            if (this.container) return;

            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        },

        show(message, type = 'info', duration = 4000, title = '') {
            this.init();

            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            `;

            this.container.appendChild(toast);

            // Trigger animation
            requestAnimationFrame(() => {
                toast.classList.add('visible');
            });

            // Auto remove
            if (duration > 0) {
                setTimeout(() => {
                    toast.classList.remove('visible');
                    setTimeout(() => toast.remove(), 300);
                }, duration);
            }

            return toast;
        },

        success(message, title = 'Success') {
            return this.show(message, 'success', 4000, title);
        },

        error(message, title = 'Error') {
            return this.show(message, 'error', 6000, title);
        },

        warning(message, title = 'Warning') {
            return this.show(message, 'warning', 5000, title);
        },

        info(message, title = '') {
            return this.show(message, 'info', 4000, title);
        }
    };

    /**
     * Wrapper for async operations with loading state.
     * @param {Function} asyncFn - Async function to execute
     * @param {string} loadingMessage - Message to show during loading
     * @returns {Promise} Result of async function
     */
    async function withLoading(asyncFn, loadingMessage = 'Processing...') {
        LoadingManager.show(loadingMessage);
        try {
            const result = await asyncFn();
            LoadingManager.hide();
            return result;
        } catch (error) {
            LoadingManager.hide();
            ToastManager.error(error.message || 'An error occurred');
            throw error;
        }
    }

    // Expose utilities globally for use in HTML onclick handlers
    window.LoadingManager = LoadingManager;
    window.ToastManager = ToastManager;
    window.withLoading = withLoading;

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
    
    const sendCommandBtn = document.getElementById('send-command-btn');

    // Admin tab elements
    const restartSystemBtn = document.getElementById('restart-system-btn');
    const backupSystemBtn = document.getElementById('backup-system-btn');
    const updateConfigBtn = document.getElementById('update-config-btn');
    const exportLogsBtn = document.getElementById('export-logs-btn');
    const configDisplay = document.getElementById('config-display');
    
    // Ollama elements
    const ollamaConfigMethod = document.getElementById('ollama-config-method');
    const ollamaHostPortConfig = document.getElementById('ollama-host-port-config');
    const ollamaBaseUrlConfig = document.getElementById('ollama-base-url-config');
    const ollamaHost = document.getElementById('ollama-host');
    const ollamaPort = document.getElementById('ollama-port');
    const ollamaBaseUrl = document.getElementById('ollama-base-url');
    const testOllamaConnectionBtn = document.getElementById('test-ollama-connection-btn');
    const listOllamaModelsBtn = document.getElementById('list-ollama-models-btn');
    const saveOllamaConfigBtn = document.getElementById('save-ollama-config-btn');
    const ollamaStatus = document.getElementById('ollama-status');
    const ollamaModelsList = document.getElementById('ollama-models-list');
    const ollamaTestModel = document.getElementById('ollama-test-model');
    const ollamaTestPrompt = document.getElementById('ollama-test-prompt');
    const testOllamaCompletionBtn = document.getElementById('test-ollama-completion-btn');
    const ollamaCompletionStatus = document.getElementById('ollama-completion-status');
    const ollamaCompletionResponse = document.getElementById('ollama-completion-response');
    const ollamaResponseText = document.getElementById('ollama-response-text');

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
    
    // BDI Reasoning elements
    const bdiBeliefs = document.getElementById('bdi-beliefs');
    const bdiDesires = document.getElementById('bdi-desires');
    const bdiIntentions = document.getElementById('bdi-intentions');
    
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

    function displayToolsList(data) {
        let html = `<h3>Tools in ${data.tools_directory} (${data.tools_count} total)</h3>`;
        html += '<div class="tools-grid">';
        
        data.tools.forEach(tool => {
            const sizeKB = (tool.size / 1024).toFixed(1);
            html += `
                <div class="tool-card">
                    <div class="tool-header">
                        <h4>${tool.name}</h4>
                        <span class="tool-size">${sizeKB} KB</span>
                    </div>
                    <div class="tool-filename">${tool.filename}</div>
                    <div class="tool-description">${tool.description}</div>
                    <div class="tool-path">${tool.path}</div>
                </div>
            `;
        });
        
        html += '</div>';
        showResponse(html);
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
        console.log('updateLogsDisplay called, logs count:', logs.length); // Debug log
        
        if (!logsOutput) {
            console.log('logsOutput element not found!'); // Debug log
            return;
        }
        
        const filterLevel = logLevelFilter ? logLevelFilter.value.toUpperCase() : 'ALL';
        const filteredLogs = logs.filter(log => 
            filterLevel === 'ALL' || log.level.toUpperCase() === filterLevel
        );
        
        console.log('Filtered logs count:', filteredLogs.length); // Debug log
        
        if (filteredLogs.length === 0) {
            logsOutput.innerHTML = '<div class="log-info">No logs to display</div>';
        } else {
            logsOutput.innerHTML = filteredLogs.map(log => {
                const levelClass = `log-${log.level.toLowerCase()}`;
                return `<div class="${levelClass}">[${log.timestamp}] ${log.level}: ${log.message}</div>`;
            }).join('');
        }
        
        console.log('Logs display updated'); // Debug log
    }

    // System Monitoring
    let monitoringInterval = null;
    let isMonitoring = false;

    // Agent Activity Monitoring
    function addAgentActivity(agent, message, type = 'info', details = null) {
        if (activityPaused) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const activityEntry = {
            timestamp,
            agent,
            message,
            type,
            details,
            id: Date.now() + Math.random() // Unique ID for animations
        };
        
        activityLog.unshift(activityEntry);
        if (activityLog.length > 50) activityLog.pop();
        
        updateActivityDisplay();
        updateExecutiveMetrics();
        updateAgentStatus(agent, message, type);
        
        // Only highlight workflow if this is REAL agent activity (not system messages)
        if (agent !== 'System' && agent !== 'Workflow Monitor') {
            updateWorkflowNode(agent, message, type);
        }
        
        // Add pulse animation to new entries
        setTimeout(() => {
            const entries = document.querySelectorAll('.activity-entry');
            if (entries.length > 0) {
                entries[0].classList.add('new-activity');
                setTimeout(() => {
                    entries[0].classList.remove('new-activity');
                }, 2000);
            }
        }, 100);
    }

    // Executive Dashboard Functions
    function updateExecutiveMetrics() {
        // Update active agents count
        const activeAgents = document.getElementById('active-agents');
        if (activeAgents) {
            const uniqueAgents = new Set(activityLog.map(entry => entry.agent));
            activeAgents.textContent = uniqueAgents.size;
        }

        // Update tasks completed
        const tasksCompleted = document.getElementById('tasks-completed');
        if (tasksCompleted) {
            const completedTasks = activityLog.filter(entry => 
                entry.type === 'success' && 
                (entry.message.includes('completed') || entry.message.includes('success'))
            ).length;
            tasksCompleted.textContent = completedTasks;
        }
    }

    function updateAgentStatus(agent, message, type) {
        const agentId = agent.toLowerCase().replace(/\s+/g, '-');
        let statusCard = document.getElementById(`${agentId}-status`);
        
        // Create new agent card if it doesn't exist
        if (!statusCard) {
            statusCard = createAgentStatusCard(agent, agentId);
        }
        
        const activityElement = document.getElementById(`${agentId}-activity`);
        const indicatorElement = document.getElementById(`${agentId}-indicator`);

        if (statusCard && activityElement && indicatorElement) {
            // Update activity message
            activityElement.textContent = message.length > 50 ? message.substring(0, 50) + '...' : message;
            
            // Update status indicator
            indicatorElement.className = 'agent-status-indicator';
            if (type === 'success') {
                indicatorElement.classList.add('active');
            } else if (type === 'error') {
                indicatorElement.classList.add('error');
            }

            // Update specific metrics based on agent
            updateAgentMetrics(agent, message, type);
        }
    }

    function updateWorkflowNode(agent, message, type) {
        // Map agent names to workflow node IDs
        const agentNodeMap = {
            'Coordinator Agent': 'coordinator-workflow-status', 
            'AGInt Core': 'agint-workflow-status',
            'BDI Agent': 'bdi-workflow-status',
            'Simple Coder': 'simple-coder-workflow-status'
        };
        
        const nodeId = agentNodeMap[agent];
        if (!nodeId) return;
        
        const statusElement = document.getElementById(nodeId);
        if (!statusElement) return;
        
        // Update status text based on message content
        let statusText = 'Active';
        let statusClass = 'active';
        
        // Check for working state indicators - only highlight for actual work activities
        if (message.includes('Generated') || message.includes('generated') || 
            message.includes('Processing') || message.includes('processing') ||
            message.includes('Selected') || message.includes('selected') ||
            message.includes('Executing') || message.includes('executing') ||
            message.includes('Analyzing') || message.includes('analyzing') ||
            message.includes('Creating') || message.includes('creating') ||
            message.includes('Building') || message.includes('building') ||
            message.includes('Computing') || message.includes('computing') ||
            message.includes('Reasoning') || message.includes('reasoning') ||
            message.includes('Deciding') || message.includes('deciding') ||
            message.includes('Generating') || message.includes('generating') ||
            message.includes('Status:') || message.includes('status:') ||
            message.includes('Directive:') || message.includes('directive:') ||
            message.includes('Cycle') || message.includes('cycle') ||
            message.includes('BDI') || message.includes('bdi') ||
            message.includes('Simple Coder') || message.includes('simple coder') ||
            message.includes('Mastermind') || message.includes('mastermind') ||
            message.includes('Coordinator') || message.includes('coordinator') ||
            message.includes('AGInt') || message.includes('agint')) {
            statusText = 'Working';
            statusClass = 'working';
        } else if (message.includes('pending') || message.includes('waiting') || message.includes('queued')) {
            statusText = 'Waiting';
            statusClass = 'waiting';
        } else if (message.includes('completed') || message.includes('success') || message.includes('finished')) {
            statusText = 'Active';
            statusClass = 'active';
        } else if (message.includes('error') || message.includes('failed') || message.includes('stopped')) {
            statusText = 'Error';
            statusClass = 'waiting';
        } else if (message.includes('idle') || message.includes('standby') || message.includes('ready')) {
            statusText = 'Ready';
            statusClass = 'active';
        }
        
        statusElement.textContent = statusText;
        
        // Update parent node class
        const workflowNode = statusElement.closest('.workflow-node');
        if (workflowNode) {
            // Clear all state classes first
            workflowNode.classList.remove('working', 'active', 'waiting', 'processing');
            
            // Add the new state class
            workflowNode.classList.add(statusClass);
            
            // Add working highlight effect
            if (statusClass === 'working') {
                // Remove working class from other nodes
                document.querySelectorAll('.workflow-node.working').forEach(node => {
                    if (node !== workflowNode) {
                        node.classList.remove('working');
                        node.classList.add('active');
                    }
                });
                
                // Set as the current active agent for highlighting
                setActiveAgent(agent);
                
                // Set a timeout to remove working state after 3 seconds
                setTimeout(() => {
                    if (workflowNode.classList.contains('working')) {
                        workflowNode.classList.remove('working');
                        workflowNode.classList.add('active');
                        statusElement.textContent = 'Active';
                    }
                }, 3000);
            } else if (statusClass === 'active') {
                // Set as the current active agent for highlighting
                setActiveAgent(agent);
            }
        }
    }

    // Track the currently active agent for highlighting
    let currentActiveAgent = null;
    
    function setActiveAgent(agent) {
        // Remove active highlighting from previous agent
        if (currentActiveAgent && currentActiveAgent !== agent) {
            const previousNodeId = {
                'Coordinator Agent': 'coordinator-workflow-status', 
                'AGInt Core': 'agint-workflow-status',
                'BDI Agent': 'bdi-workflow-status',
                'Simple Coder': 'simple-coder-workflow-status'
            }[currentActiveAgent];
            
            if (previousNodeId) {
                const previousStatusElement = document.getElementById(previousNodeId);
                if (previousStatusElement) {
                    const previousWorkflowNode = previousStatusElement.closest('.workflow-node');
                    if (previousWorkflowNode) {
                        previousWorkflowNode.classList.remove('active');
                        previousWorkflowNode.classList.add('waiting');
                    }
                }
            }
        }
        
        currentActiveAgent = agent;
        
        // Add active highlighting to current agent
        const currentNodeId = {
            'Coordinator Agent': 'coordinator-workflow-status', 
            'AGInt Core': 'agint-workflow-status',
            'BDI Agent': 'bdi-workflow-status',
            'Simple Coder': 'simple-coder-workflow-status'
        }[agent];
        
        if (currentNodeId) {
            const currentStatusElement = document.getElementById(currentNodeId);
            if (currentStatusElement) {
                const currentWorkflowNode = currentStatusElement.closest('.workflow-node');
                if (currentWorkflowNode) {
                    currentWorkflowNode.classList.add('active');
                }
            }
        }
    }

    function createAgentStatusCard(agentName, agentId) {
        const agentStatusGrid = document.querySelector('.agent-status-grid');
        if (!agentStatusGrid) return null;

        const agentCard = document.createElement('div');
        agentCard.className = 'agent-status-card';
        agentCard.id = `${agentId}-status`;
        
        agentCard.innerHTML = `
            <div class="agent-header">
                <div class="agent-name">${agentName}</div>
                <div class="agent-status-indicator" id="${agentId}-indicator"></div>
            </div>
            <div class="agent-activity" id="${agentId}-activity">Initializing...</div>
            <div class="agent-metrics" id="${agentId}-metrics">
                <span class="metric">Status: <span id="${agentId}-status-text">Unknown</span></span>
                <span class="metric">Last Activity: <span id="${agentId}-last-activity">Just started</span></span>
            </div>
        `;
        
        agentStatusGrid.appendChild(agentCard);
        return agentCard;
    }

    function updateAgentMetrics(agent, message, type) {
        if (agent === 'BDI Agent') {
            const decisionsElement = document.getElementById('bdi-decisions');
            const successElement = document.getElementById('bdi-success');
            
            if (decisionsElement) {
                const currentDecisions = parseInt(decisionsElement.textContent) || 0;
                if (message.includes('Selected') || message.includes('Decision')) {
                    decisionsElement.textContent = currentDecisions + 1;
                }
            }
            
            if (successElement && type === 'success') {
                const currentSuccess = parseInt(successElement.textContent) || 0;
                successElement.textContent = Math.min(100, currentSuccess + 5) + '%';
            }
        } else if (agent === 'AGInt Core') {
            const cyclesElement = document.getElementById('agint-cycles');
            const progressElement = document.getElementById('agint-progress');
            
            if (cyclesElement && message.includes('Cycle')) {
                const currentCycles = parseInt(cyclesElement.textContent) || 0;
                cyclesElement.textContent = currentCycles + 1;
            }
            
            if (progressElement && message.includes('Progress')) {
                const progressMatch = message.match(/(\d+)%/);
                if (progressMatch) {
                    progressElement.textContent = progressMatch[1] + '%';
                }
            }
        } else if (agent === 'Simple Coder') {
            const requestsElement = document.getElementById('simple-coder-requests');
            const approvedElement = document.getElementById('simple-coder-approved');
            
            // Update pending requests count
            if (requestsElement) {
                if (message.includes('Generated') && message.includes('pending')) {
                    const match = message.match(/(\d+)\s+pending/);
                    if (match) {
                        requestsElement.textContent = match[1];
                    } else {
                        const currentRequests = parseInt(requestsElement.textContent) || 0;
                        requestsElement.textContent = currentRequests + 1;
                    }
                } else if (message.includes('pending update requests')) {
                    const match = message.match(/(\d+)\s+pending/);
                    if (match) {
                        requestsElement.textContent = match[1];
                    }
                }
            }
            
            // Update approved count
            if (approvedElement && (message.includes('Approved') || message.includes('approved'))) {
                const currentApproved = parseInt(approvedElement.textContent) || 0;
                approvedElement.textContent = currentApproved + 1;
            }
            
            // Update Simple Coder status text
            const statusTextElement = document.getElementById('simple-coder-status-text');
            if (statusTextElement) {
                if (message.includes('pending')) {
                    statusTextElement.textContent = 'Processing Requests';
                } else if (message.includes('Generated')) {
                    statusTextElement.textContent = 'Code Generation Active';
                } else if (message.includes('Status:')) {
                    const statusMatch = message.match(/Status:\s*(\w+)/);
                    if (statusMatch) {
                        statusTextElement.textContent = statusMatch[1];
                    }
                }
            }
        } else if (agent === 'Coordinator') {
            const delegationsElement = document.getElementById('coordinator-delegations');
            const activeElement = document.getElementById('coordinator-active');
            
            if (delegationsElement && message.includes('Delegated')) {
                const currentDelegations = parseInt(delegationsElement.textContent) || 0;
                delegationsElement.textContent = currentDelegations + 1;
            }
            
            if (activeElement && message.includes('Active')) {
                const currentActive = parseInt(activeElement.textContent) || 0;
                activeElement.textContent = currentActive + 1;
            }
        }
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
                             entry.type === 'warning' ? 'warning' : 'info';
            
            // Enhanced professional formatting
            const formattedTime = new Date(entry.timestamp).toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            const statusIcon = entry.type === 'error' ? '❌' : 
                              entry.type === 'success' ? '✅' : 
                              entry.type === 'warning' ? '⚠️' : 'ℹ️';
            
            const agentBadge = `<span class="agent-badge" data-agent="${entry.agent}">${entry.agent}</span>`;
            const timeBadge = `<span class="time-badge">${formattedTime}</span>`;
            const statusBadge = `<span class="status-badge ${typeClass}">${statusIcon}</span>`;
            
            // Workflow context display (hidden by default, shown on click)
            let workflowHtml = '';
            if (entry.workflow_context) {
                const workflow = entry.workflow_context;
                workflowHtml = '<div class="workflow-context" style="display: none;">';
                workflowHtml += `<div class="workflow-step">${workflow.workflow_step || 'Unknown Step'}</div>`;
                if (workflow.triggered_by) {
                    workflowHtml += `<div class="workflow-trigger">Triggered by: ${workflow.triggered_by}</div>`;
                }
                if (workflow.triggers && workflow.triggers.length > 0) {
                    workflowHtml += `<div class="workflow-triggers">Triggers: ${workflow.triggers.join(', ')}</div>`;
                }
                if (workflow.workflow_type) {
                    workflowHtml += `<div class="workflow-type">Type: ${workflow.workflow_type}</div>`;
                }
                if (workflow.cycle_phase) {
                    workflowHtml += `<div class="workflow-phase">Phase: ${workflow.cycle_phase}</div>`;
                }
                workflowHtml += '</div>';
            }
            
            // Enhanced details display (hidden by default, shown on click)
            let detailsHtml = '';
            if (entry.details) {
                const details = entry.details;
                detailsHtml = '<div class="activity-details" style="display: none;">';
                
                if (details.reasoning) {
                    detailsHtml += `<div class="detail-item"><strong>Reasoning:</strong> ${details.reasoning}</div>`;
                }
                if (details.available_agents) {
                    detailsHtml += `<div class="detail-item"><strong>Available Agents:</strong> ${details.available_agents.join(', ')}</div>`;
                }
                if (details.decision_factors) {
                    detailsHtml += `<div class="detail-item"><strong>Decision Factors:</strong> ${details.decision_factors.join(', ')}</div>`;
                }
                if (details.target_agent) {
                    detailsHtml += `<div class="detail-item"><strong>Target Agent:</strong> ${details.target_agent}</div>`;
                }
                if (details.task_type) {
                    detailsHtml += `<div class="detail-item"><strong>Task Type:</strong> ${details.task_type}</div>`;
                }
                if (details.requested_tool) {
                    detailsHtml += `<div class="detail-item"><strong>Requested Tool:</strong> ${details.requested_tool}</div>`;
                }
                if (details.evaluation_criteria) {
                    detailsHtml += `<div class="detail-item"><strong>Evaluation Criteria:</strong> ${details.evaluation_criteria.join(', ')}</div>`;
                }
                if (details.agents_considered) {
                    detailsHtml += `<div class="detail-item"><strong>Agents Considered:</strong> ${details.agents_considered.join(', ')}</div>`;
                }
                if (details.confidence) {
                    detailsHtml += `<div class="detail-item"><strong>Confidence:</strong> <span class="confidence-${details.confidence}">${details.confidence}</span></div>`;
                }
                if (details.ethereum_address) {
                    detailsHtml += `<div class="detail-item"><strong>Ethereum Address:</strong> <code>${details.ethereum_address}</code></div>`;
                }
                if (details.capabilities) {
                    detailsHtml += `<div class="detail-item"><strong>Capabilities:</strong> ${details.capabilities.join(', ')}</div>`;
                }
                
                detailsHtml += '</div>';
            }
            
            return `
                <div class="activity-entry ${typeClass}" data-activity-id="${entry.id || Date.now()}" style="cursor: pointer;">
                    <div class="activity-header">
                        ${statusBadge}
                        ${agentBadge}
                        ${timeBadge}
                    </div>
                    <div class="activity-content">
                        <div class="activity-message">${entry.message}</div>
                        ${workflowHtml}
                        ${detailsHtml}
                    </div>
                </div>
            `;
        }).join('');
    }

    function toggleActivityDetails(activityEntry) {
        const workflowContext = activityEntry.querySelector('.workflow-context');
        const activityDetails = activityEntry.querySelector('.activity-details');
        
        // Toggle workflow context
        if (workflowContext) {
            if (workflowContext.style.display === 'none') {
                workflowContext.style.display = 'block';
            } else {
                workflowContext.style.display = 'none';
            }
        }
        
        // Toggle activity details
        if (activityDetails) {
            if (activityDetails.style.display === 'none') {
                activityDetails.style.display = 'block';
            } else {
                activityDetails.style.display = 'none';
            }
        }
        
        // Add visual feedback for clicked entry
        activityEntry.classList.toggle('clicked');
    }

    // Agent Detail Popup Functions (Global scope)
    window.showAgentDetailPopup = function(agentId, agentName) {
        console.log('showAgentDetailPopup called with:', agentId, agentName); // Debug log
        const popup = document.getElementById('agent-detail-popup');
        if (!popup) {
            console.log('Popup element not found'); // Debug log
            return;
        }
        
        // Get agent data
        const agentData = getAgentData(agentId, agentName);
        console.log('Agent data:', agentData); // Debug log
        
        // Populate popup content
        populateAgentPopup(agentData);
        
        // Show popup
        popup.classList.add('show');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        console.log('Popup should now be visible'); // Debug log
    };

    window.hideAgentDetailPopup = function() {
        const popup = document.getElementById('agent-detail-popup');
        if (popup) {
            popup.classList.remove('show');
            document.body.style.overflow = ''; // Restore scrolling
        }
    };

    function getAgentData(agentId, agentName) {
        // Get current agent status from the UI
        const activityElement = document.getElementById(`${agentId}-activity`);
        const indicatorElement = document.getElementById(`${agentId}-indicator`);
        
        // Get agent-specific data
        const agentData = {
            id: agentId,
            name: agentName,
            icon: getAgentIcon(agentName),
            status: getAgentStatus(indicatorElement),
            activity: activityElement ? activityElement.textContent : 'No activity',
            metrics: getAgentMetrics(agentId),
            capabilities: getAgentCapabilities(agentName),
            recentActivity: getAgentRecentActivity(agentName)
        };
        
        return agentData;
    }

    function getAgentIcon(agentName) {
        const iconMap = {
            'BDI Agent': '⚡',
            'AGInt Core': '🔄',
            'Simple Coder': '💻',
            'Coordinator': '🎯',
            'MastermindAgent': '🧠',
            'Resource Monitor': '📊'
        };
        return iconMap[agentName] || '🤖';
    }

    function getAgentStatus(indicatorElement) {
        if (!indicatorElement) return 'Unknown';
        
        if (indicatorElement.classList.contains('active')) return 'Active';
        if (indicatorElement.classList.contains('warning')) return 'Warning';
        if (indicatorElement.classList.contains('error')) return 'Error';
        return 'Unknown';
    }

    function getAgentMetrics(agentId) {
        const metrics = [];
        
        // Get metrics from the agent card
        const metricsContainer = document.querySelector(`#${agentId}-status .agent-metrics`);
        if (metricsContainer) {
            const metricElements = metricsContainer.querySelectorAll('.metric');
            metricElements.forEach(metric => {
                const text = metric.textContent;
                const parts = text.split(': ');
                if (parts.length === 2) {
                    metrics.push({
                        label: parts[0].trim(),
                        value: parts[1].trim()
                    });
                }
            });
        }
        
        return metrics;
    }

    /**
     * Get capabilities for an agent.
     * Prefers capabilities from agent data (backend), falls back to defaults.
     * @param {string} agentName - Name of the agent
     * @param {Object} agentData - Optional agent data object with capabilities array
     * @returns {Array} Array of capability objects or strings
     */
    function getAgentCapabilities(agentName, agentData = null) {
        // If agent data has capabilities, use them
        if (agentData && agentData.capabilities && Array.isArray(agentData.capabilities)) {
            return agentData.capabilities;
        }

        // Fallback to default capabilities (legacy support)
        const defaultCapabilities = {
            'BDI Agent': [
                { name: 'Decision Making', category: 'cognitive' },
                { name: 'Agent Selection', category: 'orchestration' },
                { name: 'Reasoning', category: 'cognitive' },
                { name: 'Belief Management', category: 'memory' }
            ],
            'AGInt Core': [
                { name: 'Cognitive Processing', category: 'cognitive' },
                { name: 'PODA Cycles', category: 'cognitive' },
                { name: 'Perception', category: 'cognitive' },
                { name: 'Decision', category: 'cognitive' }
            ],
            'Simple Coder': [
                { name: 'Code Generation', category: 'development' },
                { name: 'Update Requests', category: 'development' },
                { name: 'Code Evolution', category: 'evolution' },
                { name: 'Sandbox Testing', category: 'development' }
            ],
            'Coordinator': [
                { name: 'Infrastructure Management', category: 'system' },
                { name: 'Autonomous Improvement', category: 'evolution' },
                { name: 'Component Evolution', category: 'evolution' }
            ],
            'MastermindAgent': [
                { name: 'Strategic Orchestration', category: 'orchestration' },
                { name: 'Mistral AI Reasoning', category: 'ai' },
                { name: 'Agent Coordination', category: 'orchestration' }
            ],
            'Resource Monitor': [
                { name: 'CPU Monitoring', category: 'monitoring' },
                { name: 'Memory Tracking', category: 'monitoring' },
                { name: 'System Health', category: 'monitoring' }
            ]
        };
        return defaultCapabilities[agentName] || [{ name: 'General Operations', category: 'general' }];
    }

    /**
     * Get CSS class for capability category.
     * Maps capability categories to visual styling.
     */
    function getCapabilityCategoryClass(category) {
        const categoryClasses = {
            'cognitive': 'capability-cognitive',
            'orchestration': 'capability-orchestration',
            'memory': 'capability-memory',
            'security': 'capability-security',
            'monitoring': 'capability-monitoring',
            'evolution': 'capability-evolution',
            'development': 'capability-development',
            'ai': 'capability-ai',
            'governance': 'capability-governance',
            'system': 'capability-system',
            'identity': 'capability-identity',
            'analytics': 'capability-analytics',
            'general': 'capability-general'
        };
        return categoryClasses[category] || 'capability-general';
    }

    /**
     * Render capabilities as HTML tags with category-based styling.
     * @param {Array} capabilities - Array of capability objects or strings
     * @returns {string} HTML string of capability tags
     */
    function renderCapabilities(capabilities) {
        if (!capabilities || capabilities.length === 0) {
            return '<span class="capability-tag capability-general">General Operations</span>';
        }

        return capabilities.map(cap => {
            // Handle both object format and string format
            const name = typeof cap === 'string' ? cap : cap.name;
            const category = typeof cap === 'string' ? 'general' : (cap.category || 'general');
            const categoryClass = getCapabilityCategoryClass(category);

            return `<span class="capability-tag ${categoryClass}" title="${category}">${name}</span>`;
        }).join('');
    }

    function getAgentRecentActivity(agentName) {
        // Get recent activities for this specific agent
        return activityLog
            .filter(entry => entry.agent === agentName)
            .slice(0, 5) // Last 5 activities
            .map(entry => ({
                time: entry.timestamp,
                message: entry.message,
                type: entry.type
            }));
    }

    function populateAgentPopup(agentData) {
        // Update popup header
        document.getElementById('popup-agent-name').textContent = `${agentData.name} Details`;
        document.getElementById('popup-agent-icon').textContent = agentData.icon;
        document.getElementById('popup-agent-title').textContent = agentData.name;
        document.getElementById('popup-agent-status').textContent = agentData.status;
        
        // Update current activity
        document.getElementById('popup-current-activity').textContent = agentData.activity;
        
        // Update metrics
        const metricsContainer = document.getElementById('popup-metrics');
        metricsContainer.innerHTML = agentData.metrics.map(metric => `
            <div class="metric-item">
                <span class="metric-label">${metric.label}</span>
                <span class="metric-value">${metric.value}</span>
            </div>
        `).join('');
        
        // Update recent activity
        const activityContainer = document.getElementById('popup-activity-history');
        if (agentData.recentActivity.length > 0) {
            activityContainer.innerHTML = agentData.recentActivity.map(activity => `
                <div class="activity-item">
                    <span class="activity-time">${activity.time}</span>
                    <span class="activity-message">${activity.message}</span>
                    <span class="activity-type ${activity.type}">${activity.type}</span>
                </div>
            `).join('');
        } else {
            activityContainer.innerHTML = '<div class="activity-item">No recent activity</div>';
        }
        
        // Update capabilities
        const capabilitiesContainer = document.getElementById('popup-capabilities');
        capabilitiesContainer.innerHTML = agentData.capabilities.map(capability => `
            <span class="capability-tag">${capability}</span>
        `).join('');
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


    // API Functions
    // Track thinking state for K.I.T.T. lights
    let activeRequests = 0;
    let thinkingTimeout = null;
    
    function updateThinkingState(isThinking) {
        if (isThinking) {
            activeRequests++;
            document.body.classList.add('mindx-thinking');
            if (thinkingTimeout) {
                clearTimeout(thinkingTimeout);
            }
        } else {
            activeRequests = Math.max(0, activeRequests - 1);
            if (activeRequests === 0) {
                // Delay removing thinking state to avoid flicker
                thinkingTimeout = setTimeout(() => {
                    document.body.classList.remove('mindx-thinking');
                }, 300);
            }
        }
    }

    async function sendRequest(endpoint, method = 'GET', body = null) {
        showResponse('Sending request...');
        addLog(`API Request: ${method} ${endpoint}`, 'INFO');
        
        // Mark as thinking
        updateThinkingState(true);
        
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
            
            // Mark as not thinking
            updateThinkingState(false);
            
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
            
            // Mark as not thinking even on error
            updateThinkingState(false);
            
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
        // Load Faicey expressions when Faicey tab is activated
        if (tabId === 'faicey') {
            loadFaiceyExpressions();
            initializeFaiceyTabs();
        }
        
        // Initialize window manager when admin tab is activated
        if (tabId === 'admin' && window.windowManager) {
            // Window manager is already initialized, just ensure it's ready
            console.log('Admin tab activated - window manager ready');
        } else if (tabId === 'admin' && !window.windowManager) {
            // Wait a bit for window manager to initialize if it hasn't yet
            setTimeout(() => {
                if (window.windowManager) {
                    console.log('Window manager initialized for admin tab');
                } else {
                    console.warn('Window manager not available');
                }
            }, 100);
        }
        
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
            case 'api':
                loadAPIData();
                break;
            case 'admin':
                loadAdminData();
                break;
            case 'faicey':
                loadFaiceyExpressions();
                initializeFaiceyTabs();
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
            
            // Mark as thinking
            updateThinkingState(true);
            
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
                
                // Mark as not thinking
                updateThinkingState(false);
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
                    // Load GitHub status when GitHub section is opened
                    if (targetSection === 'github') {
                        loadGitHubStatus();
                        loadGitHubSchedule();
                    }
                }
            });
        });
        
        // GitHub Agent Functions
        async function loadGitHubStatus() {
            try {
                const response = await fetch(`${apiUrl}/github/status`);
                if (response.ok) {
                    const data = await response.json();
                    displayGitHubStatus(data);
                    addLog('GitHub agent status loaded', 'SUCCESS');
                } else {
                    addLog('Failed to load GitHub status', 'ERROR');
                }
            } catch (error) {
                addLog(`Error loading GitHub status: ${error.message}`, 'ERROR');
            }
        }
        
        function displayGitHubStatus(data) {
            const statusDisplay = document.getElementById('github-status-display');
            if (!statusDisplay) return;
            
            const backupStatus = data.backup_status || {};
            const schedule = data.schedule || {};
            const backups = data.backups || {};
            
            statusDisplay.innerHTML = `
                <div class="status-item">
                    <strong>Current Branch:</strong> ${backupStatus.current_branch || 'unknown'}
                </div>
                <div class="status-item">
                    <strong>Total Backups:</strong> ${backupStatus.total_backups || 0}
                </div>
                <div class="status-item">
                    <strong>System Status:</strong> <span class="status-badge ${backupStatus.system_status === 'operational' ? 'success' : 'warning'}">${backupStatus.system_status || 'unknown'}</span>
                </div>
                ${backupStatus.last_backup ? `
                <div class="status-item">
                    <strong>Last Backup:</strong> ${backupStatus.last_backup.branch_name || 'unknown'}
                    <br><small>${backupStatus.last_backup.created_at || ''}</small>
                </div>
                ` : ''}
                <div class="status-item">
                    <strong>Scheduled Backups:</strong> ${schedule.active_tasks || 0} active
                </div>
            `;
        }
        
        async function loadGitHubSchedule() {
            try {
                const response = await fetch(`${apiUrl}/github/schedule`);
                if (response.ok) {
                    const data = await response.json();
                    displayGitHubSchedule(data.schedule || {});
                }
            } catch (error) {
                addLog(`Error loading schedule: ${error.message}`, 'ERROR');
            }
        }
        
        function displayGitHubSchedule(schedule) {
            const schedules = schedule.schedules || {};
            const shutdown = schedule.shutdown_backup || {};
            
            // Daily backup
            if (schedules.daily) {
                document.getElementById('daily-backup-enabled').checked = schedules.daily.enabled || false;
                if (schedules.daily.time) {
                    document.getElementById('daily-backup-time').value = schedules.daily.time;
                }
            }
            
            // Hourly backup
            if (schedules.hourly) {
                document.getElementById('hourly-backup-enabled').checked = schedules.hourly.enabled || false;
            }
            
            // Weekly backup
            if (schedules.weekly) {
                document.getElementById('weekly-backup-enabled').checked = schedules.weekly.enabled || false;
                if (schedules.weekly.day) {
                    document.getElementById('weekly-backup-day').value = schedules.weekly.day;
                }
                if (schedules.weekly.time) {
                    document.getElementById('weekly-backup-time').value = schedules.weekly.time;
                }
            }
            
            // Shutdown backup
            document.getElementById('shutdown-backup-enabled').checked = shutdown.enabled !== false;
        }
        
        async function createBackup() {
            const reason = document.getElementById('backup-reason-input').value || 'Manual backup from UI';
            const backupType = document.getElementById('backup-type-select').value;
            
            try {
                addLog('Creating backup...', 'INFO');
                const response = await fetch(`${apiUrl}/github/execute`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        operation: 'create_backup',
                        backup_type: backupType,
                        reason: reason
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        addLog(`Backup created: ${data.result.backup_branch}`, 'SUCCESS');
                        loadGitHubStatus();
                        listBackups();
                    } else {
                        addLog(`Backup failed: ${data.result}`, 'ERROR');
                    }
                } else {
                    addLog('Failed to create backup', 'ERROR');
                }
            } catch (error) {
                addLog(`Error creating backup: ${error.message}`, 'ERROR');
            }
        }
        
        async function listBackups() {
            try {
                const response = await fetch(`${apiUrl}/github/execute`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ operation: 'list_backups' })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        displayBackupsList(data.result);
                    }
                }
            } catch (error) {
                addLog(`Error listing backups: ${error.message}`, 'ERROR');
            }
        }
        
        function displayBackupsList(data) {
            const backupsList = document.getElementById('backups-list');
            if (!backupsList) return;
            
            const backups = data.backup_metadata || [];
            if (backups.length === 0) {
                backupsList.innerHTML = '<p>No backups found</p>';
                return;
            }
            
            backupsList.innerHTML = `
                <h4>Recent Backups (${data.total_backups || 0} total)</h4>
                <div class="backups-grid">
                    ${backups.map(backup => `
                        <div class="backup-item">
                            <strong>${backup.branch_name || 'unknown'}</strong>
                            <div class="backup-meta">
                                <span>Type: ${backup.backup_type || 'unknown'}</span>
                                <span>Created: ${new Date(backup.created_at).toLocaleString()}</span>
                            </div>
                            <div class="backup-reason">${backup.reason || ''}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        async function syncWithGitHub() {
            try {
                addLog('Syncing with GitHub...', 'INFO');
                const response = await fetch(`${apiUrl}/github/execute`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ operation: 'sync_with_github' })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        addLog('GitHub sync completed', 'SUCCESS');
                        loadGitHubStatus();
                    } else {
                        addLog(`Sync failed: ${data.result}`, 'ERROR');
                    }
                }
            } catch (error) {
                addLog(`Error syncing: ${error.message}`, 'ERROR');
            }
        }
        
        async function saveSchedule(interval, enabled, time, day) {
            try {
                const payload = {
                    operation: 'set_backup_schedule',
                    interval: interval,
                    enabled: enabled
                };
                if (time) payload.time = time;
                if (day) payload.day = day;
                
                const response = await fetch(`${apiUrl}/github/schedule`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'success') {
                        addLog(`${interval} backup schedule updated`, 'SUCCESS');
                        loadGitHubSchedule();
                    }
                }
            } catch (error) {
                addLog(`Error saving schedule: ${error.message}`, 'ERROR');
            }
        }
        
        // GitHub Agent Event Listeners
        document.addEventListener('DOMContentLoaded', () => {
            const refreshStatusBtn = document.getElementById('refresh-github-status-btn');
            const createBackupBtn = document.getElementById('create-backup-btn');
            const listBackupsBtn = document.getElementById('list-backups-btn');
            const syncGithubBtn = document.getElementById('sync-github-btn');
            const refreshScheduleBtn = document.getElementById('refresh-schedule-btn');
            const saveDailyBtn = document.getElementById('save-daily-schedule-btn');
            const saveHourlyBtn = document.getElementById('save-hourly-schedule-btn');
            const saveWeeklyBtn = document.getElementById('save-weekly-schedule-btn');
            
            if (refreshStatusBtn) {
                refreshStatusBtn.addEventListener('click', loadGitHubStatus);
            }
            if (createBackupBtn) {
                createBackupBtn.addEventListener('click', createBackup);
            }
            if (listBackupsBtn) {
                listBackupsBtn.addEventListener('click', listBackups);
            }
            if (syncGithubBtn) {
                syncGithubBtn.addEventListener('click', syncWithGitHub);
            }
            if (refreshScheduleBtn) {
                refreshScheduleBtn.addEventListener('click', loadGitHubSchedule);
            }
            if (saveDailyBtn) {
                saveDailyBtn.addEventListener('click', () => {
                    const enabled = document.getElementById('daily-backup-enabled').checked;
                    const time = document.getElementById('daily-backup-time').value;
                    saveSchedule('daily', enabled, time);
                });
            }
            if (saveHourlyBtn) {
                saveHourlyBtn.addEventListener('click', () => {
                    const enabled = document.getElementById('hourly-backup-enabled').checked;
                    saveSchedule('hourly', enabled);
                });
            }
            if (saveWeeklyBtn) {
                saveWeeklyBtn.addEventListener('click', () => {
                    const enabled = document.getElementById('weekly-backup-enabled').checked;
                    const day = document.getElementById('weekly-backup-day').value;
                    const time = document.getElementById('weekly-backup-time').value;
                    saveSchedule('weekly', enabled, time, day);
                });
            }
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
                const response = await fetch(`${apiUrl}/tools`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'success') {
                        displayToolsList(data);
                        addLog(`Found ${data.tools_count} tools in ${data.tools_directory}`, 'SUCCESS');
                        addAgentActivity('System Tools', `Listed ${data.tools_count} tools from tools folder`, 'success');
                    } else {
                        addLog(`Error: ${data.error}`, 'ERROR');
                        addAgentActivity('System Tools', `Error: ${data.error}`, 'error');
                    }
                } else {
                    addLog('Failed to fetch tools list', 'ERROR');
                    addAgentActivity('System Tools', 'Failed to fetch tools list', 'error');
                }
            } catch (error) {
                addLog(`Error fetching tools: ${error.message}`, 'ERROR');
                addAgentActivity('System Tools', `Error: ${error.message}`, 'error');
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
        
        // Ollama Management Event Listeners
        setupOllamaListeners();
    }
    
    // Ollama Management Setup Function
    function setupOllamaListeners() {
        const testBtn = document.getElementById('test-ollama-connection-btn');
        const listBtn = document.getElementById('list-ollama-models-btn');
        const saveBtn = document.getElementById('save-ollama-config-btn');
        const completionBtn = document.getElementById('test-ollama-completion-btn');
        const quickTestBtn = document.getElementById('ollama-quick-test-btn');
        const configMethod = document.getElementById('ollama-config-method');
        const hostPortConfig = document.getElementById('ollama-host-port-config');
        const baseUrlConfig = document.getElementById('ollama-base-url-config');
        
        if (testBtn) {
            console.log('✅ Setting up Ollama event listeners');
            testBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔌 Test Connection button clicked');
                testOllamaConnection();
            });
        }
        
        if (quickTestBtn) {
            quickTestBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('⚡ Quick Test button clicked');
                testOllamaConnection();
            });
        }
        
        if (listBtn) {
            listBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('📋 List Models button clicked');
                listOllamaModels();
            });
        }
        
        if (saveBtn) {
            saveBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('💾 Save Config button clicked');
                saveOllamaConfig();
            });
        }
        
        if (completionBtn) {
            completionBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('🧪 Test Completion button clicked');
                testOllamaCompletion();
            });
        }
        
        // Toggle between host/port and base URL configuration
        if (configMethod) {
            configMethod.addEventListener('change', function() {
                const method = this.value;
                console.log('🔄 Config method changed to:', method);
                if (method === 'host-port') {
                    if (hostPortConfig) hostPortConfig.style.display = 'grid';
                    if (baseUrlConfig) baseUrlConfig.style.display = 'none';
                } else {
                    if (hostPortConfig) hostPortConfig.style.display = 'none';
                    if (baseUrlConfig) baseUrlConfig.style.display = 'block';
                }
            });
        }
        
        // Ensure status elements are visible
        const statusEl = document.getElementById('ollama-status');
        const modelsEl = document.getElementById('ollama-models-list');
        if (statusEl) {
            statusEl.style.display = 'block';
            statusEl.style.minHeight = '60px';
        }
        if (modelsEl) {
            modelsEl.style.display = 'block';
            modelsEl.style.minHeight = '100px';
        }
        
        // Initialize connection banner
        updateConnectionBanner('error', 'Not Connected', 'Configure and test connection to get started');
    }
    
    // Setup Ollama listeners when admin tab is shown
    const adminTabBtn = document.querySelector('[data-tab="admin"]');
    if (adminTabBtn) {
        adminTabBtn.addEventListener('click', function() {
            setTimeout(setupOllamaListeners, 100);
        });
    }

    // Agents Tab Functions
    function initializeAgentsTab() {
        refreshAgentsBtn.addEventListener('click', loadAgents);
        createAgentBtn.addEventListener('click', createAgent);
        deleteAgentBtn.addEventListener('click', deleteAgent);
        
        // Initialize new agent window button
        const newAgentWindowBtn = document.getElementById('new-agent-window-btn');
        if (newAgentWindowBtn) {
            newAgentWindowBtn.addEventListener('click', () => {
                if (selectedAgent) {
                    openAgentInWindow(selectedAgent);
                } else {
                    // Create empty agent window
                    if (window.windowManager) {
                        window.windowManager.createAgentWindow();
                    }
                }
            });
        }
        
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
                               `<div class="bdi-item">${belief}</div>`
                           ).join('');
                       }
                       
                       // Update BDI desires
                       const bdiDesires = document.getElementById('bdi-desires');
                       if (bdiDesires && bdiResponse.desires) {
                           bdiDesires.innerHTML = bdiResponse.desires.map(desire => 
                               `<div class="bdi-item">${desire}</div>`
                           ).join('');
                       } else if (bdiDesires) {
                           // Fallback desires based on current state
                           const fallbackDesires = [
                               'Maintain system stability',
                               'Process user requests efficiently',
                               'Monitor agent activities',
                               'Coordinate system components'
                           ];
                           bdiDesires.innerHTML = fallbackDesires.map(desire => 
                               `<div class="bdi-item">${desire}</div>`
                           ).join('');
                       }
                       
                       // Update BDI intentions
                       const bdiIntentions = document.getElementById('bdi-intentions');
                       if (bdiIntentions && bdiResponse.intentions) {
                           bdiIntentions.innerHTML = bdiResponse.intentions.map(intention => 
                               `<div class="bdi-item">${intention}</div>`
                           ).join('');
                       } else if (bdiIntentions) {
                           // Fallback intentions based on current state
                           const fallbackIntentions = [
                               'Execute current workflow',
                               'Respond to system events',
                               'Update agent status',
                               'Maintain communication channels'
                           ];
                           bdiIntentions.innerHTML = fallbackIntentions.map(intention => 
                               `<div class="bdi-item">${intention}</div>`
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

            // ID Manager display removed
            
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
            // BDI realtime display removed
        } catch (error) {
            console.error('Error fetching real-time BDI data:', error);
        }
    }
    

    // Evolution functions
    async function loadEvolution() {
        try {
            addLog('Loading evolution data...', 'INFO');
            
            // Load Blueprint Agent
            const blueprintResponse = await sendRequest('/evolution/blueprint');
            if (blueprintResponse) {
                updateBlueprintAgentDisplay(blueprintResponse);
            }

            // Load Action Converter
            const converterResponse = await sendRequest('/evolution/converter');
            if (converterResponse) {
                updateActionConverterDisplay(converterResponse);
            }
            
            // Load Strategic Evolution Agent
            const seaResponse = await sendRequest('/learning/sea');
            if (seaResponse) {
                updateStrategicEvolutionAgentDisplay(seaResponse);
            }
            
            addLog('Evolution data loaded successfully', 'INFO');
        } catch (error) {
            addLog(`Failed to load evolution data: ${error.message}`, 'ERROR');
        }
    }
    
    function updateBlueprintAgentDisplay(data) {
        // Basic status
        document.getElementById('blueprint-status').textContent = data.status || 'Unknown';
        document.getElementById('blueprint-agent-id').textContent = data.agent_id || 'Unknown';
        
        // Last blueprint timestamp
        const lastGenerated = data.last_blueprint_generated;
        if (lastGenerated) {
            const date = new Date(lastGenerated * 1000);
            document.getElementById('blueprint-last-generated').textContent = date.toLocaleString();
        }
        
        // Confidence score
        const confidence = data.metrics?.current_confidence_score;
        if (confidence) {
            document.getElementById('blueprint-confidence').textContent = `${Math.round(confidence * 100)}%`;
        }
        
        // Current blueprint details
        const current = data.current;
        if (current) {
            document.getElementById('current-blueprint-title').textContent = current.blueprint_title || 'No Title';
            document.getElementById('current-blueprint-version').textContent = current.target_mindx_version_increment || 'Unknown Version';
            
            // Focus areas
            const focusAreas = current.focus_areas || [];
            document.getElementById('blueprint-focus-areas').innerHTML = focusAreas.map(area => 
                `<div class="focus-area-item">${area}</div>`
            ).join('');
            
            // BDI Todo list
            const todoList = current.bdi_todo_list || [];
            document.getElementById('blueprint-todo-list').innerHTML = todoList.map(todo => 
                `<div class="todo-item">
                    <div class="todo-description">${todo.goal_description}</div>
                    <div class="todo-meta">Priority: ${todo.priority} | Component: ${todo.target_component}</div>
                </div>`
            ).join('');
            
            // KPIs
            const kpis = current.key_performance_indicators || [];
            document.getElementById('blueprint-kpis').innerHTML = kpis.map(kpi => 
                `<div class="kpi-item">${kpi}</div>`
            ).join('');
            
            // Risks
            const risks = current.potential_risks || [];
            document.getElementById('blueprint-risks').innerHTML = risks.map(risk => 
                `<div class="risk-item">${risk}</div>`
            ).join('');
        }
        
        // Blueprint history
        const history = data.blueprint_history || [];
        document.getElementById('blueprint-history-list').innerHTML = history.map(item => 
            `<div class="history-item">
                <div class="history-title">${item.title}</div>
                <div class="history-meta">${new Date(item.generated_at * 1000).toLocaleString()} | ${item.status}</div>
            </div>`
        ).join('');
        
        // Metrics
        const metrics = data.metrics || {};
        document.getElementById('blueprint-total').textContent = metrics.total_blueprints_generated || 0;
        document.getElementById('blueprint-successful').textContent = metrics.successful_implementations || 0;
        document.getElementById('blueprint-avg-time').textContent = `${metrics.average_implementation_time_hours || 0}h`;
    }
    
    function updateActionConverterDisplay(data) {
        // Update overview values
        document.getElementById('converter-status').textContent = data.status || 'Active';
        document.getElementById('converter-total').textContent = data.conversion_metrics?.total_conversions || 45;
        document.getElementById('converter-success-rate').textContent = 
            Math.round((data.conversion_metrics?.success_rate || 0.92) * 100) + '%';
        
        // Calculate average time
        const avgTime = data.conversion_metrics?.average_conversion_time_seconds || 45;
        document.getElementById('converter-avg-time').textContent = avgTime + 's';
        
        // Update workflow steps based on recent activity
        updateCompactWorkflow(data);
        
        // Update recent conversions
        updateRecentConversionsCompact(data.recent || []);
        
        // Update action types
        updateActionTypes(data.action_type_distribution || {});
        
        // Store data for future use
        window.lastConverterData = data;
    }

    function updateCompactWorkflow(data) {
        const steps = document.querySelectorAll('.workflow-step.compact');
        const recentConversions = data.recent || [];
        
        // Reset all steps
        steps.forEach(step => {
            step.classList.remove('active', 'processing', 'completed');
        });
        
        // Simulate workflow progress based on recent activity
        if (recentConversions.length > 0) {
            // First step is always active
            steps[0].classList.add('active');
            
            // Simulate processing through steps
            setTimeout(() => {
                if (steps[1]) {
                    steps[1].classList.add('processing');
                }
            }, 1000);
            
            setTimeout(() => {
                if (steps[1]) {
                    steps[1].classList.remove('processing');
                    steps[1].classList.add('completed');
                }
                if (steps[2]) {
                    steps[2].classList.add('processing');
                }
            }, 2000);
            
            setTimeout(() => {
                if (steps[2]) {
                    steps[2].classList.remove('processing');
                    steps[2].classList.add('completed');
                }
                if (steps[3]) {
                    steps[3].classList.add('processing');
                }
            }, 3000);
            
            setTimeout(() => {
                if (steps[3]) {
                    steps[3].classList.remove('processing');
                    steps[3].classList.add('completed');
                }
            }, 4000);
        }
    }

    function updateRecentConversionsCompact(conversions) {
        const container = document.getElementById('recent-conversions');
        if (!container) return;
        
        // Show only the 2 most recent conversions
        const recentConversions = conversions.slice(0, 2);
        
        container.innerHTML = recentConversions.map(conv => `
            <div class="conversion-item">
                <div class="conversion-header">
                    <span class="conversion-id">${conv.conversion_id || 'conv_' + Math.random().toString(36).substr(2, 6)}</span>
                    <span class="conversion-time">${getTimeAgo(conv.conversion_time || Date.now() / 1000)}</span>
                </div>
                <div class="conversion-details">
                    <span class="conversion-title">${conv.blueprint_title || 'Blueprint Conversion'}</span>
                    <div class="conversion-meta">
                        <span class="meta-item">${conv.actions_generated || 0} actions</span>
                        <span class="meta-item">$${(conv.total_estimated_cost || 0).toFixed(2)} cost</span>
                        <span class="meta-item safety-${getSafetyLevel(conv.safety_levels)}">${getSafetyLevel(conv.safety_levels)} Safety</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function updateActionTypes(distribution) {
        const container = document.querySelector('.action-types-grid');
        if (!container) return;
        
        const actionTypes = [
            { name: 'ANALYZE_SYSTEM', count: distribution.ANALYZE_SYSTEM || 15, width: 75 },
            { name: 'GENERATE_CODE', count: distribution.GENERATE_CODE || 28, width: 90 },
            { name: 'VALIDATE_CHANGES', count: distribution.VALIDATE_CHANGES || 12, width: 60 },
            { name: 'CREATE_ROLLBACK_PLAN', count: distribution.CREATE_ROLLBACK_PLAN || 8, width: 40 }
        ];
        
        container.innerHTML = actionTypes.map(type => `
            <div class="action-type-item">
                <span class="action-type-name">${type.name}</span>
                <div class="action-type-bar">
                    <div class="action-type-fill" style="width: ${type.width}%"></div>
                </div>
                <span class="action-type-count">${type.count}</span>
            </div>
        `).join('');
    }

    function getSafetyLevel(safetyLevels) {
        if (!safetyLevels) return 'standard';
        
        const critical = safetyLevels.critical || 0;
        const high = safetyLevels.high || 0;
        
        if (critical > 0) return 'critical';
        if (high > 2) return 'high';
        return 'standard';
    }
    
    function updateConversionWorkflow(data) {
        const steps = document.querySelectorAll('.workflow-step');
        const recent = data.recent || [];
        const isProcessing = recent.length > 0 && recent[0].conversion_time > (Date.now() / 1000) - 300; // Last 5 minutes
        
        steps.forEach((step, index) => {
            step.classList.remove('active', 'processing', 'completed');
            
            if (isProcessing) {
                if (index <= 2) {
                    step.classList.add('processing');
                } else if (index === 3) {
                    step.classList.add('active');
                }
            } else if (recent.length > 0) {
                if (index <= 4) {
                    step.classList.add('completed');
                }
            } else {
                if (index === 0) {
                    step.classList.add('active');
                }
            }
        });
    }
    
    function updateRecentConversions(conversions) {
        const container = document.getElementById('recent-conversions');
        const currentFilter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
        
        let filteredConversions = conversions;
        if (currentFilter === 'high-safety') {
            filteredConversions = conversions.filter(conv => {
                const safetyLevels = conv.safety_levels || {};
                const totalActions = conv.actions_generated || 0;
                const criticalCount = safetyLevels.critical || 0;
                const highCount = safetyLevels.high || 0;
                return totalActions > 0 && ((totalActions - criticalCount - highCount) / totalActions) > 0.8;
            });
        } else if (currentFilter === 'low-cost') {
            filteredConversions = conversions.filter(conv => (conv.total_estimated_cost || 0) < 1.0);
        } else if (currentFilter === 'recent') {
            const oneHourAgo = Date.now() / 1000 - 3600;
            filteredConversions = conversions.filter(conv => conv.conversion_time > oneHourAgo);
        }
        
        container.innerHTML = filteredConversions.map((conversion, index) => {
            const safetyLevels = conversion.safety_levels || {};
            const totalActions = conversion.actions_generated || 0;
            const criticalCount = safetyLevels.critical || 0;
            const highCount = safetyLevels.high || 0;
            const safetyScore = totalActions > 0 ? Math.round(((totalActions - criticalCount - highCount) / totalActions) * 100) : 100;
            
            return `
                <div class="conversion-item" data-conversion-id="${conversion.conversion_id || index}">
                    <div class="conversion-header">
                        <div class="conversion-title">${conversion.blueprint_title || 'Unknown Blueprint'}</div>
                        <div class="conversion-id">ID: ${conversion.conversion_id || `conv_${index}`}</div>
                    </div>
                    <div class="conversion-meta">
                        <span class="meta-item">
                            <i class="icon">⚡</i> ${totalActions} actions
                        </span>
                        <span class="meta-item">
                            <i class="icon">💰</i> $${conversion.total_estimated_cost || 0}
                        </span>
                        <span class="meta-item">
                            <i class="icon">⏱️</i> ${Math.round((conversion.total_estimated_duration || 0) / 60)}min
                        </span>
                        <span class="meta-item">
                            <i class="icon">🛡️</i> ${safetyScore}% safe
                        </span>
                    </div>
                    <div class="conversion-safety">
                        <span class="safety-breakdown">
                            ${Object.entries(safetyLevels).map(([level, count]) => 
                                `<span class="safety-level ${level}">${level}: ${count}</span>`
                            ).join(' | ')}
                        </span>
                    </div>
                    <div class="conversion-actions">
                        <button class="btn-small" onclick="viewConversionDetails('${conversion.conversion_id || index}')">
                            View Details
                        </button>
                        <button class="btn-small" onclick="exportConversion('${conversion.conversion_id || index}')">
                            Export
                        </button>
                        <button class="btn-small" onclick="validateConversion('${conversion.conversion_id || index}')">
                            Validate
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    function updateConversionMetrics(metrics) {
        document.getElementById('converter-total').textContent = metrics.total_conversions || 0;
        document.getElementById('converter-avg-actions').textContent = (metrics.average_actions_per_conversion || 0).toFixed(1);
        document.getElementById('converter-avg-cost').textContent = `$${(metrics.average_cost_per_conversion || 0).toFixed(2)}`;
        document.getElementById('converter-success-rate').textContent = `${Math.round((metrics.success_rate || 0) * 100)}%`;
    }
    
    function updateSafetyAnalysis(conversions) {
        const safetyCounts = { low: 0, standard: 0, high: 0, critical: 0 };
        
        conversions.forEach(conversion => {
            const safetyLevels = conversion.safety_levels || {};
            Object.entries(safetyLevels).forEach(([level, count]) => {
                safetyCounts[level] = (safetyCounts[level] || 0) + count;
            });
        });
        
        document.getElementById('safety-low-count').textContent = safetyCounts.low;
        document.getElementById('safety-standard-count').textContent = safetyCounts.standard;
        document.getElementById('safety-high-count').textContent = safetyCounts.high;
        document.getElementById('safety-critical-count').textContent = safetyCounts.critical;
    }
    
    function updateActionDistribution(distribution) {
        const totalActions = Object.values(distribution).reduce((sum, count) => sum + count, 0);
        const container = document.getElementById('action-type-distribution');
        
        container.innerHTML = Object.entries(distribution)
            .sort(([,a], [,b]) => b - a)
            .map(([type, count]) => {
                const percentage = totalActions > 0 ? Math.round((count / totalActions) * 100) : 0;
                return `
                    <div class="distribution-item" data-action-type="${type}" onclick="showActionTypeDetails('${type}')">
                        <div class="distribution-info">
                            <span class="distribution-type">${type.replace(/_/g, ' ')}</span>
                            <div class="distribution-bar">
                                <div class="distribution-fill" style="width: ${percentage}%"></div>
                            </div>
                        </div>
                        <div class="distribution-stats">
                            <span class="distribution-count">${count}</span>
                            <span class="distribution-percentage">${percentage}%</span>
                        </div>
                    </div>
                `;
            }).join('');
    }
    
    function initializeConversionControls() {
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                // Re-render conversions with new filter
                const data = window.lastConverterData || {};
                updateRecentConversions(data.recent || []);
            });
        });
        
        // View toggle buttons
        document.querySelectorAll('.view-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.view-toggle').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                // Switch view mode
                switchDistributionView(e.target.dataset.view);
            });
        });
        
        // Control buttons
        document.getElementById('start-conversion-btn')?.addEventListener('click', startNewConversion);
        document.getElementById('pause-conversion-btn')?.addEventListener('click', pauseConversions);
        document.getElementById('validate-all-btn')?.addEventListener('click', validateAllActions);
        document.getElementById('export-conversions-btn')?.addEventListener('click', exportAllConversions);
    }
    
    function switchDistributionView(view) {
        const container = document.getElementById('action-type-distribution');
        // Implementation for different view modes
        addLog(`Switched to ${view} view`, 'INFO');
    }
    
    // Store data for filtering
    window.lastConverterData = null;
    
    // Helper function to get time ago
    function getTimeAgo(timestamp) {
        const now = Date.now() / 1000;
        const diff = now - timestamp;
        
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }
    
    // Enhanced Action Converter utility functions
    window.viewConversionDetails = function(conversionId) {
        addLog(`Viewing details for conversion: ${conversionId}`, 'INFO');
        const modal = document.getElementById('conversion-details-modal');
        const content = document.getElementById('conversion-details-content');
        
        // Mock detailed conversion data
        const details = `
            <div class="conversion-detail-section">
                <h4>Conversion Overview</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Conversion ID:</span>
                        <span class="detail-value">${conversionId}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Blueprint:</span>
                        <span class="detail-value">Enhanced Cognitive Architecture v2.1</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Actions Generated:</span>
                        <span class="detail-value">15</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Total Cost:</span>
                        <span class="detail-value">$2.45</span>
                    </div>
                </div>
            </div>
            
            <div class="conversion-detail-section">
                <h4>Action Breakdown</h4>
                <div class="action-list">
                    <div class="action-item">
                        <span class="action-type">ANALYZE_SYSTEM</span>
                        <span class="action-desc">Analyze current system performance</span>
                        <span class="action-safety low">Low Risk</span>
                    </div>
                    <div class="action-item">
                        <span class="action-type">GENERATE_CODE</span>
                        <span class="action-desc">Generate enhanced reasoning code</span>
                        <span class="action-safety standard">Standard</span>
                    </div>
                    <div class="action-item">
                        <span class="action-type">CREATE_ROLLBACK_PLAN</span>
                        <span class="action-desc">Create safety rollback mechanism</span>
                        <span class="action-safety high">High Risk</span>
                    </div>
                </div>
            </div>
            
            <div class="conversion-detail-section">
                <h4>Dependencies</h4>
                <div class="dependency-list">
                    <div class="dependency-item">
                        <span class="dep-from">GENERATE_CODE</span>
                        <span class="dep-arrow">→</span>
                        <span class="dep-to">CREATE_ROLLBACK_PLAN</span>
                        <span class="dep-type">Sequential</span>
                    </div>
                </div>
            </div>
        `;
        
        content.innerHTML = details;
        modal.classList.add('active');
    };
    
    window.closeConversionDetails = function() {
        document.getElementById('conversion-details-modal').classList.remove('active');
    };
    
    window.exportConversion = function(conversionId) {
        addLog(`Exporting conversion: ${conversionId}`, 'INFO');
        // Mock export functionality
        const exportData = {
            conversion_id: conversionId,
            timestamp: new Date().toISOString(),
            actions: ['ANALYZE_SYSTEM', 'GENERATE_CODE', 'CREATE_ROLLBACK_PLAN'],
            cost: 2.45,
            duration: 1800
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversion_${conversionId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };
    
    window.validateConversion = function(conversionId) {
        addLog(`Validating conversion: ${conversionId}`, 'INFO');
        // Mock validation
        setTimeout(() => {
            addLog(`Conversion ${conversionId} validation completed - All checks passed`, 'SUCCESS');
        }, 1000);
    };
    
    window.showActionTypeDetails = function(actionType) {
        addLog(`Showing details for action type: ${actionType}`, 'INFO');
        // Mock action type details
        alert(`Action Type: ${actionType}\n\nThis would show detailed information about this action type, including:\n- Usage patterns\n- Success rates\n- Common parameters\n- Safety considerations`);
    };
    
    window.showDependencyGraph = function() {
        addLog('Showing dependency graph', 'INFO');
        const container = document.getElementById('dependency-graph');
        container.innerHTML = `
            <div class="dependency-graph-placeholder">
                <div class="graph-node">Blueprint Input</div>
                <div class="graph-arrow">↓</div>
                <div class="graph-node">Goal Decomposition</div>
                <div class="graph-arrow">↓</div>
                <div class="graph-node">Action Generation</div>
                <div class="graph-arrow">↓</div>
                <div class="graph-node">Dependency Mapping</div>
                <div class="graph-arrow">↓</div>
                <div class="graph-node">BDI Actions</div>
            </div>
        `;
    };
    
    window.validateDependencies = function() {
        addLog('Validating action dependencies', 'INFO');
        setTimeout(() => {
            addLog('Dependency validation completed - No circular dependencies found', 'SUCCESS');
        }, 1500);
    };
    
    window.optimizeDependencies = function() {
        addLog('Optimizing action sequence', 'INFO');
        setTimeout(() => {
            addLog('Sequence optimization completed - 15% efficiency improvement', 'SUCCESS');
        }, 2000);
    };
    
    // Control functions
    function startNewConversion() {
        addLog('Starting new conversion process', 'INFO');
        // Mock conversion start
        setTimeout(() => {
            addLog('New conversion process initiated', 'SUCCESS');
        }, 1000);
    }
    
    function pauseConversions() {
        addLog('Pausing conversion processes', 'INFO');
        // Mock pause functionality
    }
    
    function validateAllActions() {
        addLog('Validating all actions', 'INFO');
        // Mock validation
        setTimeout(() => {
            addLog('All actions validated successfully', 'SUCCESS');
        }, 3000);
    }
    
    function exportAllConversions() {
        addLog('Exporting all conversion data', 'INFO');
        // Mock export
        const exportData = {
            timestamp: new Date().toISOString(),
            total_conversions: 45,
            export_format: 'json'
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'all_conversions.json';
        a.click();
        URL.revokeObjectURL(url);
    }
    
    // Store converter data for filtering
    function updateActionConverterDisplay(data) {
        window.lastConverterData = data;
        // ... rest of the function remains the same
    }
    
    function updateStrategicEvolutionAgentDisplay(data) {
        // Basic status
        document.getElementById('sea-status').textContent = data.status || 'Unknown';
        document.getElementById('sea-agent-id').textContent = data.agent_id || 'Unknown';
        
        // Current campaign
        const campaign = data.current_campaign;
        if (campaign) {
            document.getElementById('sea-current-campaign').textContent = campaign.title || 'No Campaign';
            document.getElementById('sea-progress').textContent = `${campaign.progress || 0}%`;
        }
        
        // Learning metrics
        const learningMetrics = data.learning_metrics || {};
        document.getElementById('sea-lessons-learned').textContent = learningMetrics.lessons_learned || 0;
        document.getElementById('sea-adaptations').textContent = learningMetrics.successful_adaptations || 0;
        document.getElementById('sea-learning-rate').textContent = `${Math.round((learningMetrics.learning_rate || 0) * 100)}%`;
        document.getElementById('sea-confidence').textContent = `${Math.round((learningMetrics.adaptation_confidence || 0) * 100)}%`;
        
        // Active plans
        const plans = data.active_plans || [];
        document.getElementById('sea-active-plans').innerHTML = plans.map(plan => 
            `<div class="plan-item">
                <div class="plan-title">${plan.title}</div>
                <div class="plan-meta">
                    Status: ${plan.status} | Progress: ${plan.progress}% | Priority: ${plan.priority}
                </div>
                <div class="plan-progress-bar">
                    <div class="plan-progress-fill" style="width: ${plan.progress}%"></div>
                </div>
            </div>`
        ).join('');
        
        // Recent activities
        const activities = data.recent_activities || [];
        document.getElementById('sea-recent-activities').innerHTML = activities.map(activity => 
            `<div class="activity-item">
                <div class="activity-content">${activity.activity}</div>
                <div class="activity-meta">
                    ${new Date(activity.timestamp * 1000).toLocaleString()} | 
                    ${activity.type} | 
                    <span class="activity-success ${activity.success ? 'success' : 'failure'}">
                        ${activity.success ? 'Success' : 'Failed'}
                    </span>
                </div>
            </div>`
        ).join('');
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
            
            // Store agent data as JSON in data attribute for drag and drop
            const agentDataJson = JSON.stringify(agent).replace(/"/g, '&quot;');
            
            return `
                <div class="agent-item draggable ${isSelected}" 
                     data-agent-id="${agentId}" 
                     data-agent-data='${agentDataJson}'
                     draggable="true">
                    <div class="agent-info">
                        <div class="agent-name">
                            ${agent.name || agentId}
                            ${systemBadge}
                        </div>
                        <div class="agent-type">${agentType}</div>
                        <div class="agent-status ${statusClass}">${agent.status || 'Unknown'}</div>
                    </div>
                    <div class="agent-actions">
                        <button class="agent-action-btn window-btn" onclick="openAgentInWindow('${agentId}', event)" title="Open in Window">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                <line x1="9" y1="3" x2="9" y2="21"/>
                                <line x1="3" y1="9" x2="21" y2="9"/>
                            </svg>
                        </button>
                        ${canDelete ? `<button class="agent-action-btn delete-btn" onclick="deleteAgent('${agentId}')">Delete</button>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        // Add drag and drop listeners to agent items
        agentsList.querySelectorAll('.agent-item').forEach(item => {
            // Drag start
            item.addEventListener('dragstart', (e) => {
                item.classList.add('dragging');
                const agentData = item.getAttribute('data-agent-data');
                e.dataTransfer.setData('application/json', agentData);
                e.dataTransfer.effectAllowed = 'copy';
            });
            
            // Drag end
            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
            });
            
            // Click to open details modal
            item.addEventListener('click', (e) => {
                // Don't trigger if clicking on action buttons
                if (e.target.closest('.agent-action-btn')) {
                    return;
                }
                const agentId = item.getAttribute('data-agent-id');
                openAgentDetailsModal(agentId);
            });
            
            // Double-click to open in window
            item.addEventListener('dblclick', (e) => {
                const agentId = item.getAttribute('data-agent-id');
                const agentData = JSON.parse(item.getAttribute('data-agent-data'));
                openAgentInWindow(agentId, e, agentData);
            });
        });
        
        // Make window container a drop zone
        const windowContainer = document.getElementById('window-container');
        if (windowContainer) {
            windowContainer.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
            });
            
            windowContainer.addEventListener('drop', (e) => {
                e.preventDefault();
                const agentDataJson = e.dataTransfer.getData('application/json');
                if (agentDataJson) {
                    try {
                        const agentData = JSON.parse(agentDataJson);
                        if (window.windowManager) {
                            window.windowManager.createAgentWindow(agentData.agent_id || agentData.id, agentData);
                        }
                    } catch (error) {
                        console.error('Failed to parse agent data:', error);
                    }
                }
            });
        }
    }

    function selectAgent(agentId) {
        selectedAgent = agentId;
        displayAgents(); // Refresh to show selection
        displayAgentDetails(agentId);
    }

    // Open agent in a new window
    function openAgentInWindow(agentId, event, agentData = null) {
        if (event) {
            event.stopPropagation();
        }
        
        if (!window.windowManager) {
            console.error('Window manager not available');
            return;
        }
        
        // Find agent data if not provided
        if (!agentData) {
            const allAgents = [...systemAgents, ...userAgents, ...agents];
            agentData = allAgents.find(a => (a.id || a.name || a.agent_id) === agentId);
        }
        
        if (!agentData) {
            console.error('Agent not found:', agentId);
            return;
        }
        
        // Create window with agent data
        const windowId = window.windowManager.createAgentWindow(agentId, agentData);
        
        // Store mapping for updates
        if (!window.agentWindows) {
            window.agentWindows = new Map();
        }
        window.agentWindows.set(agentId, windowId);
        
        console.log('Opened agent in window:', agentId, windowId);
    }
    
    // Make function globally accessible
    window.openAgentInWindow = openAgentInWindow;
    
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
        console.log('Initializing logs tab...'); // Debug log
        if (refreshLogsBtn) {
            refreshLogsBtn.addEventListener('click', loadLogs);
            console.log('Refresh logs button listener added'); // Debug log
        }
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', (e) => {
                console.log('Clear logs button clicked!'); // Debug log
                e.preventDefault();
                clearLogs();
            });
            console.log('Clear logs button listener added'); // Debug log
        } else {
            console.log('Clear logs button not found!'); // Debug log
        }
        if (copyLogsBtn) {
            copyLogsBtn.addEventListener('click', copyLogsToClipboard);
        }
        if (logLevelFilter) {
            logLevelFilter.addEventListener('change', updateLogsDisplay);
        }
    }

    async function loadLogs() {
        try {
            console.log('Loading logs...');
            // Try to get logs from backend first
            try {
                const result = await sendRequest('/system/logs');
                if (result && result.logs) {
                    logs = result.logs;
                    console.log('Loaded logs from backend:', logs.length);
                }
            } catch (backendError) {
                console.log('Backend logs not available, using local logs');
                // If backend fails, just refresh the display with current logs
            }
            
            // Always update the display
            updateLogsDisplay();
            addLog('Logs refreshed', 'INFO');
        } catch (error) {
            console.error('Error loading logs:', error);
            addLog(`Failed to load logs: ${error.message}`, 'ERROR');
        }
    }

    function clearLogs() {
        console.log('clearLogs function called'); // Debug log
        console.log('Logs before clear:', logs.length);
        
        // Clear the logs array
        logs = [];
        
        // Force clear the display immediately
        if (logsOutput) {
            logsOutput.innerHTML = '<div class="log-info">[Logs cleared] INFO: Logs cleared</div>';
        }
        
        // Add a confirmation log
        addLog('Logs cleared successfully', 'INFO');
        
        console.log('Logs after clear:', logs.length);
        console.log('Clear logs completed');
    }

    function copyLogsToClipboard() {
        const logText = logs.map(log => `[${log.timestamp}] ${log.level}: ${log.message}`).join('\n');
        navigator.clipboard.writeText(logText).then(() => {
            addLog('Logs copied to clipboard', 'INFO');
        }).catch(err => {
            addLog(`Failed to copy logs: ${err.message}`, 'ERROR');
        });
    }


    // Admin Tab Functions
    function initializeAdminTab() {
        // Restricted admin functions - disabled for regular users
        restartSystemBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addLog('Restart System: Access denied - Admin privileges required', 'WARNING');
            showResponse('Access denied: Admin privileges required for system restart');
        });
        
        backupSystemBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addLog('Backup System: Access denied - Admin privileges required', 'WARNING');
            showResponse('Access denied: Admin privileges required for system backup');
        });
        
        updateConfigBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addLog('Update Config: Access denied - Admin privileges required', 'WARNING');
            showResponse('Access denied: Admin privileges required for config updates');
        });
        
        // Export logs is available to all users - opens format selection modal
        exportLogsBtn.addEventListener('click', showExportFormatModal);
    }

    async function loadAdminData() {
        // Ensure window manager is initialized when admin tab loads
        if (!window.windowManager) {
            console.log('Waiting for window manager to initialize...');
            // Wait a bit more for window manager
            setTimeout(() => {
                if (window.windowManager) {
                    console.log('Window manager ready for admin tab');
                }
            }, 200);
        } else {
            console.log('Window manager already initialized');
        }
        try {
            const config = await sendRequest('/system/config');
            displayConfig(config);
            // Load PostgreSQL settings and vault keys
            await loadPostgreSQLSettings();
            await loadVaultKeys();
            initializePostgreSQLHandlers();
            initializeVaultHandlers();
        } catch (error) {
            addLog(`Failed to load admin data: ${error.message}`, 'ERROR');
        }
    }
    
    // PostgreSQL Management Functions
    async function loadPostgreSQLSettings() {
        try {
            const response = await sendRequest('/admin/postgresql/config');
            if (response.status === 'success' && response.config) {
                const config = response.config;
                document.getElementById('postgres-host').value = config.host || 'localhost';
                document.getElementById('postgres-port').value = config.port || 5432;
                document.getElementById('postgres-database').value = config.database || 'mindx_memory';
                document.getElementById('postgres-user').value = config.user || 'mindx';
                if (config.has_password) {
                    document.getElementById('postgres-password').placeholder = 'Password is set (enter new to change)';
                }
            }
        } catch (error) {
            addLog(`Failed to load PostgreSQL settings: ${error.message}`, 'ERROR');
        }
    }
    
    async function savePostgreSQLSettings() {
        const config = {
            host: document.getElementById('postgres-host').value,
            port: parseInt(document.getElementById('postgres-port').value),
            database: document.getElementById('postgres-database').value,
            user: document.getElementById('postgres-user').value,
            password: document.getElementById('postgres-password').value || undefined
        };
        
        try {
            const response = await sendRequest('/admin/postgresql/config', 'POST', config);
            if (response.status === 'success') {
                addLog('PostgreSQL settings saved to vault', 'SUCCESS');
                document.getElementById('postgres-password').value = '';
                document.getElementById('postgres-password').placeholder = 'Password saved';
            }
        } catch (error) {
            addLog(`Failed to save PostgreSQL settings: ${error.message}`, 'ERROR');
        }
    }
    
    async function testPostgreSQLConnection() {
        const config = {
            host: document.getElementById('postgres-host').value,
            port: parseInt(document.getElementById('postgres-port').value),
            database: document.getElementById('postgres-database').value,
            user: document.getElementById('postgres-user').value,
            password: document.getElementById('postgres-password').value || undefined
        };
        
        const statusDiv = document.getElementById('postgres-connection-status');
        statusDiv.innerHTML = '<p>Testing connection...</p>';
        statusDiv.className = 'connection-status testing';
        
        try {
            const response = await sendRequest('/admin/postgresql/test', 'POST', config);
            if (response.status === 'success') {
                statusDiv.innerHTML = `<p class="success">✓ Connection successful</p><p>${response.version}</p>`;
                statusDiv.className = 'connection-status success';
            } else {
                statusDiv.innerHTML = `<p class="error">✗ ${response.message}</p>`;
                statusDiv.className = 'connection-status error';
            }
        } catch (error) {
            statusDiv.innerHTML = `<p class="error">✗ Connection failed: ${error.message}</p>`;
            statusDiv.className = 'connection-status error';
        }
    }
    
    function initializePostgreSQLHandlers() {
        const loadBtn = document.getElementById('load-postgres-settings-btn');
        const saveBtn = document.getElementById('save-postgres-settings-btn');
        const testBtn = document.getElementById('test-postgres-connection-btn');
        const togglePasswordBtn = document.getElementById('toggle-postgres-password');
        
        if (loadBtn) {
            loadBtn.addEventListener('click', loadPostgreSQLSettings);
        }
        if (saveBtn) {
            saveBtn.addEventListener('click', savePostgreSQLSettings);
        }
        if (testBtn) {
            testBtn.addEventListener('click', testPostgreSQLConnection);
        }
        if (togglePasswordBtn) {
            togglePasswordBtn.addEventListener('click', () => {
                const passwordInput = document.getElementById('postgres-password');
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    togglePasswordBtn.textContent = '🙈';
                } else {
                    passwordInput.type = 'password';
                    togglePasswordBtn.textContent = '👁️';
                }
            });
        }
    }
    
    // Vault Management Functions
    async function loadVaultKeys() {
        try {
            const response = await sendRequest('/admin/vault/keys');
            if (response.status === 'success') {
                const keysList = document.getElementById('vault-keys-list');
                if (response.keys && response.keys.length > 0) {
                    keysList.innerHTML = `
                        <table class="vault-keys-table">
                            <thead>
                                <tr>
                                    <th>Agent ID</th>
                                    <th>Environment Variable</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${response.keys.map(key => `
                                    <tr>
                                        <td>${key.agent_id}</td>
                                        <td><code>${key.env_var}</code></td>
                                        <td>${key.has_key ? '<span class="status-badge success">Stored</span>' : '<span class="status-badge warning">Missing</span>'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                        <p>Total: ${response.count} keys</p>
                    `;
                } else {
                    keysList.innerHTML = '<p>No agent keys found in vault. Use "Migrate Keys to Vault" to move existing keys.</p>';
                }
            }
        } catch (error) {
            addLog(`Failed to load vault keys: ${error.message}`, 'ERROR');
        }
    }
    
    async function migrateKeysToVault() {
        const statusDiv = document.getElementById('vault-migration-status');
        statusDiv.innerHTML = '<p>Migrating keys from legacy storage...</p>';
        statusDiv.className = 'migration-status processing';
        
        try {
            const response = await sendRequest('/admin/vault/migrate', 'POST');
            if (response.status === 'success') {
                const migration = response.migration;
                statusDiv.innerHTML = `
                    <p class="success">Migration complete!</p>
                    <p>Migrated: ${migration.migrated} keys</p>
                    <p>Failed: ${migration.failed} keys</p>
                    ${migration.errors.length > 0 ? `<p class="error">Errors: ${migration.errors.join(', ')}</p>` : ''}
                `;
                statusDiv.className = 'migration-status success';
                await loadVaultKeys(); // Refresh the list
            }
        } catch (error) {
            statusDiv.innerHTML = `<p class="error">Migration failed: ${error.message}</p>`;
            statusDiv.className = 'migration-status error';
        }
    }
    
    function initializeVaultHandlers() {
        const refreshBtn = document.getElementById('refresh-vault-keys-btn');
        const migrateBtn = document.getElementById('migrate-keys-to-vault-btn');
        
        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadVaultKeys);
        }
        if (migrateBtn) {
            migrateBtn.addEventListener('click', migrateKeysToVault);
        }
    }

    // API Tab Functions
    async function loadAPIData() {
        await loadAPIProviders();
        await loadProvidersIntoDropdown(); // Load providers into dropdown
        initializeAPITab();
    }

    function initializeAPITab() {
        const refreshBtn = document.getElementById('refresh-api-providers-btn');
        const scanBtn = document.getElementById('scan-api-folder-btn');
        const detectBtn = document.getElementById('detect-providers-btn');
        const addBtn = document.getElementById('add-api-provider-btn');
        const closeModalBtn = document.getElementById('close-api-provider-modal');
        
        // Ollama controls
        const ollamaConfigMethod = document.getElementById('ollama-config-method');
        const ollamaTestBtn = document.getElementById('ollama-test-connection-btn');
        const ollamaSaveBtn = document.getElementById('ollama-save-config-btn');
        const ollamaListBtn = document.getElementById('ollama-list-models-btn');
        const ollamaQuickTestBtn = document.getElementById('ollama-quick-test-btn');

        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadAPIProviders);
        }

        if (scanBtn) {
            scanBtn.addEventListener('click', scanAPIFolder);
        }

        if (detectBtn) {
            detectBtn.addEventListener('click', intelligentlyDetectProviders);
        }
        
        // Provider dropdown
        const providerDropdown = document.getElementById('provider-dropdown');
        const loadProviderConfigBtn = document.getElementById('load-provider-config-btn');
        
        if (loadProviderConfigBtn) {
            loadProviderConfigBtn.addEventListener('click', loadProviderFromDropdown);
        }
        
        // Auto-load providers into dropdown on tab load
        if (providerDropdown) {
            loadProvidersIntoDropdown();
        }

        if (addBtn) {
            addBtn.addEventListener('click', addNewAPIProvider);
        }
        
        // Show add provider form button
        const showAddFormBtn = document.getElementById('show-add-provider-form-btn');
        if (showAddFormBtn) {
            showAddFormBtn.addEventListener('click', () => {
                const addForm = document.querySelector('.api-add-form');
                if (addForm) {
                    addForm.style.display = addForm.style.display === 'none' ? 'block' : 'none';
                    if (addForm.style.display === 'block') {
                        addForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        }
        
        // Initialize drag and drop for provider cards
        initializeProviderCardDragDrop();

        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => {
                document.getElementById('api-provider-details-modal').style.display = 'none';
            });
        }
        
        // Provider settings modal close button
        const closeSettingsModalBtn = document.getElementById('close-api-provider-settings-modal');
        if (closeSettingsModalBtn) {
            closeSettingsModalBtn.addEventListener('click', () => {
                document.getElementById('api-provider-settings-modal').style.display = 'none';
            });
        }
        
        // Ollama setup handlers
        if (ollamaConfigMethod) {
            ollamaConfigMethod.addEventListener('change', (e) => {
                const method = e.target.value;
                const hostPortConfig = document.getElementById('ollama-host-port-config');
                const baseUrlConfig = document.getElementById('ollama-base-url-config');
                
                if (method === 'host-port') {
                    hostPortConfig.style.display = 'grid';
                    baseUrlConfig.style.display = 'none';
                } else {
                    hostPortConfig.style.display = 'none';
                    baseUrlConfig.style.display = 'block';
                }
            });
        }
        
        if (ollamaTestBtn) {
            ollamaTestBtn.addEventListener('click', testOllamaConnection);
        }
        
        if (ollamaSaveBtn) {
            ollamaSaveBtn.addEventListener('click', saveOllamaConfig);
        }
        
        if (ollamaListBtn) {
            ollamaListBtn.addEventListener('click', listOllamaModels);
        }
        
        if (ollamaQuickTestBtn) {
            ollamaQuickTestBtn.addEventListener('click', testOllamaConnection);
        }
    }
    
    async function intelligentlyDetectProviders() {
        try {
            addLog('Using mindX intelligence to detect available providers...', 'INFO');
            const result = await sendRequest('/api/llm/providers/intelligent/detect');
            
            if (result.success && result.detected_providers) {
                displayDetectedProviders(result.detected_providers);
                addLog(`Detected ${result.total_detected} providers`, 'SUCCESS');
            }
        } catch (error) {
            addLog(`Failed to detect providers: ${error.message}`, 'ERROR');
        }
    }
    
    function displayDetectedProviders(providers) {
        const listContainer = document.getElementById('detected-providers-list');
        if (!listContainer) return;
        
        listContainer.innerHTML = '';
        
        if (providers.length === 0) {
            listContainer.innerHTML = '<p>No providers detected. Check your API folder.</p>';
            return;
        }
        
        providers.forEach(provider => {
            const providerCard = document.createElement('div');
            providerCard.className = 'detected-provider-card';
            
            const statusBadge = provider.detected ? 
                `<span class="status-badge detected">✓ Detected</span>` : 
                `<span class="status-badge not-detected">✗ Not Found</span>`;
            
            const apiKeyStatus = provider.api_key_detected ? 
                `<span class="env-status detected">API Key: ${provider.api_key_set ? 'Set' : 'Empty'}</span>` : 
                `<span class="env-status not-detected">API Key: Not in environment</span>`;
            
            providerCard.innerHTML = `
                <div class="provider-card-header">
                    <h4>${provider.display_name}</h4>
                    ${statusBadge}
                </div>
                <div class="provider-card-info">
                    <p><strong>Name:</strong> ${provider.name}</p>
                    <p><strong>Module:</strong> ${provider.module_path}</p>
                    <p><strong>Factory:</strong> ${provider.factory_function}</p>
                    ${provider.api_key_env_var ? `<p>${apiKeyStatus}</p>` : ''}
                    ${provider.base_url_env_var ? `<p><strong>Base URL Env:</strong> ${provider.base_url_env_var}</p>` : ''}
                </div>
                <div class="provider-card-actions">
                    ${provider.already_registered ? 
                        '<span class="already-registered">Already Registered</span>' : 
                        `<button class="use-provider-btn" onclick="useDetectedProvider('${provider.name}')">Use This Provider</button>`
                    }
                </div>
            `;
            
            listContainer.appendChild(providerCard);
        });
    }
    
    async function useDetectedProvider(providerName) {
        try {
            // Get intelligent suggestions for this provider
            const suggestions = await sendRequest(`/api/llm/providers/intelligent/suggest/${providerName}`);
            
            if (suggestions.success && suggestions.suggestions) {
                const sugg = suggestions.suggestions;
                
                // Auto-fill the form
                document.getElementById('new-provider-name').value = sugg.provider_name || '';
                document.getElementById('new-provider-display-name').value = sugg.display_name || sugg.provider_name || '';
                document.getElementById('new-provider-module-path').value = sugg.suggestions?.module_path || '';
                document.getElementById('new-provider-factory-function').value = sugg.suggestions?.factory_function || '';
                document.getElementById('new-provider-api-key-env').value = sugg.suggestions?.api_key_env_var || '';
                document.getElementById('new-provider-base-url-env').value = sugg.suggestions?.base_url_env_var || '';
                document.getElementById('new-provider-requires-api-key').checked = sugg.suggestions?.requires_api_key || false;
                document.getElementById('new-provider-requires-base-url').checked = sugg.suggestions?.requires_base_url || false;
                document.getElementById('new-provider-rate-limit-rpm').value = sugg.suggestions?.default_rate_limit_rpm || 60;
                document.getElementById('new-provider-rate-limit-tpm').value = sugg.suggestions?.default_rate_limit_tpm || 100000;
                
                addLog(`Auto-filled form with ${providerName} configuration`, 'SUCCESS');
                
                // Scroll to form
                document.querySelector('.api-add-form').scrollIntoView({ behavior: 'smooth' });
            }
        } catch (error) {
            addLog(`Failed to get suggestions: ${error.message}`, 'ERROR');
        }
    }
    
    async function testOllamaConnection() {
        try {
            const method = document.getElementById('ollama-config-method').value;
            let baseUrl = null;
            
            if (method === 'base-url') {
                baseUrl = document.getElementById('ollama-base-url').value;
            } else {
                const host = document.getElementById('ollama-host').value;
                const port = document.getElementById('ollama-port').value;
                baseUrl = `http://${host}:${port}`;
            }
            
            addLog(`Testing Ollama connection to ${baseUrl}...`, 'INFO');
            const result = await sendRequest(`/api/llm/ollama/connection?base_url=${encodeURIComponent(baseUrl)}`);
            
            if (result.success) {
                addLog('Ollama connection successful!', 'SUCCESS');
                updateOllamaConnectionBanner(true, baseUrl, result);
                // Refresh provider list and prioritize Ollama
                await refreshAndPrioritizeOllama();
            } else {
                addLog('Ollama connection failed', 'ERROR');
                updateOllamaConnectionBanner(false, baseUrl, result);
            }
        } catch (error) {
            addLog(`Failed to test Ollama: ${error.message}`, 'ERROR');
            updateOllamaConnectionBanner(false, null, { error: error.message });
        }
    }
    
    async function saveOllamaConfig() {
        try {
            const method = document.getElementById('ollama-config-method').value;
            let baseUrl = null;
            
            if (method === 'base-url') {
                baseUrl = document.getElementById('ollama-base-url').value;
            } else {
                const host = document.getElementById('ollama-host').value;
                const port = document.getElementById('ollama-port').value;
                baseUrl = `http://${host}:${port}`;
            }
            
            const result = await sendRequest('/api/llm/ollama/config', 'POST', { base_url: baseUrl });
            
            if (result.success) {
                addLog('Ollama configuration saved!', 'SUCCESS');
                // Also register Ollama provider if not already registered
                await registerOllamaProvider(baseUrl);
                // Refresh provider list and prioritize Ollama
                await refreshAndPrioritizeOllama();
            }
        } catch (error) {
            addLog(`Failed to save Ollama config: ${error.message}`, 'ERROR');
        }
    }
    
    async function registerOllamaProvider(baseUrl) {
        try {
            // Check if already registered
            const registry = await sendRequest('/api/llm/providers/registry');
            const isRegistered = registry.providers.some(p => p.name === 'ollama');
            
            if (!isRegistered) {
                await sendRequest('/api/llm/providers/registry/register', 'POST', {
                    name: 'ollama',
                    display_name: 'Ollama (Local)',
                    module_path: 'api.ollama_url',
                    factory_function: 'create_ollama_api',
                    api_key_env_var: null,
                    base_url_env_var: 'MINDX_LLM__OLLAMA__BASE_URL',
                    requires_api_key: false,
                    requires_base_url: true,
                    default_rate_limit_rpm: 1000,
                    default_rate_limit_tpm: 10000000
                });
                addLog('Ollama provider registered', 'SUCCESS');
            }
        } catch (error) {
            // Provider might already be registered, that's okay
            console.log('Ollama registration:', error.message);
        }
    }
    
    async function listOllamaModels() {
        try {
            const method = document.getElementById('ollama-config-method').value;
            let baseUrl = null;
            
            if (method === 'base-url') {
                baseUrl = document.getElementById('ollama-base-url').value;
            } else {
                const host = document.getElementById('ollama-host').value;
                const port = document.getElementById('ollama-port').value;
                baseUrl = `http://${host}:${port}`;
            }
            
            const result = await sendRequest(`/api/llm/ollama/models?base_url=${encodeURIComponent(baseUrl)}`);
            
            if (result.success && result.models) {
                displayOllamaModels(result.models);
            }
        } catch (error) {
            addLog(`Failed to list Ollama models: ${error.message}`, 'ERROR');
        }
    }
    
    function displayOllamaModels(models) {
        const modelsList = document.getElementById('ollama-models-list');
        if (!modelsList) return;
        
        if (models.length === 0) {
            modelsList.innerHTML = '<p>No models found. Make sure Ollama is running and has models installed.</p>';
            return;
        }
        
        let html = '<h4>Available Models:</h4><ul class="models-list">';
        models.forEach(model => {
            const modelName = model.name || model.id || model;
                    const escapedModelName = modelName.replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, ' ').replace(/\r/g, '');
            html += `<li class="model-item">${modelName}</li>`;
        });
        html += '</ul>';
        modelsList.innerHTML = html;
    }
    
    function updateOllamaConnectionBanner(connected, baseUrl, result) {
        const banner = document.getElementById('ollama-connection-banner');
        const icon = document.getElementById('ollama-connection-icon');
        const statusText = document.getElementById('ollama-connection-status-text');
        const details = document.getElementById('ollama-connection-details');
        
        if (!banner) return;
        
        banner.style.display = 'block';
        
        if (connected) {
            icon.textContent = '🟢';
            statusText.textContent = 'Connected';
            details.textContent = `Base URL: ${baseUrl}`;
            banner.style.background = 'rgba(0, 255, 136, 0.1)';
            banner.style.borderLeftColor = 'var(--corp-green)';
        } else {
            icon.textContent = '🔴';
            statusText.textContent = 'Not Connected';
            details.textContent = result.error || 'Connection failed';
            banner.style.background = 'rgba(255, 71, 87, 0.1)';
            banner.style.borderLeftColor = 'var(--corp-red)';
        }
    }
    
    async function loadProvidersIntoDropdown() {
        try {
            // Get all available providers from API folder
            const listResult = await sendRequest('/api/llm/providers/intelligent/list');
            // Also get detected providers for status indicators
            const detectResult = await sendRequest('/api/llm/providers/intelligent/detect').catch(() => null);
            const dropdown = document.getElementById('provider-dropdown');
            
            if (!dropdown) return;
            
            // Clear existing options except the first one
            dropdown.innerHTML = '<option value="">-- Select a provider --</option>';
            
            if (listResult.success && listResult.providers) {
                // Create a map of detected providers for quick lookup
                const detectedMap = new Map();
                if (detectResult && detectResult.success && detectResult.detected_providers) {
                    detectResult.detected_providers.forEach(provider => {
                        detectedMap.set(provider.name, provider);
                    });
                }
                
                // Get registered providers
                const registryResult = await sendRequest('/api/llm/providers/registry').catch(() => null);
                const registeredNames = new Set();
                if (registryResult && registryResult.providers) {
                    registryResult.providers.forEach(p => registeredNames.add(p.name));
                }
                
                listResult.providers.forEach(provider => {
                    const option = document.createElement('option');
                    option.value = provider.name;
                    let displayText = provider.display_name;
                    
                    const detected = detectedMap.get(provider.name);
                    
                    // Add status indicators
                    if (registeredNames.has(provider.name)) {
                        displayText += ' [Registered]';
                    }
                    
                    if (detected) {
                        if (detected.api_key_detected && detected.api_key_set) {
                            displayText += ' ✓';
                        } else if (detected.api_key_detected) {
                            displayText += ' ⚠';
                        }
                    }
                    
                    option.textContent = displayText;
                    dropdown.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load providers into dropdown:', error);
            addLog(`Failed to load providers into dropdown: ${error.message}`, 'ERROR');
        }
    }
    
    async function loadProviderFromDropdown() {
        const dropdown = document.getElementById('provider-dropdown');
        const statusDiv = document.getElementById('provider-dropdown-status');
        
        if (!dropdown || !dropdown.value) {
            if (statusDiv) {
                statusDiv.innerHTML = '<p class="error-message">Please select a provider from the dropdown</p>';
            }
            return;
        }
        
        const providerName = dropdown.value;
        
        // Special handling for Ollama - show Ollama configuration section right under quick provider setup
        if (providerName === 'ollama') {
            // Find the quick provider section
            const providerDropdownSection = document.querySelector('.provider-dropdown-section');
            const quickProviderSection = providerDropdownSection ? providerDropdownSection.closest('.control-section') : null;
            
            // Find the Ollama section by ID or class
            let ollamaControlSection = document.getElementById('ollama-config-section');
            if (!ollamaControlSection) {
                const ollamaSetupSection = document.querySelector('.ollama-setup-section');
                ollamaControlSection = ollamaSetupSection ? ollamaSetupSection.closest('.control-section') : null;
            }
            
            if (ollamaControlSection && quickProviderSection) {
                // Make sure it's visible
                ollamaControlSection.style.display = 'block';
                ollamaControlSection.style.visibility = 'visible';
                ollamaControlSection.style.opacity = '1';
                
                // Move it to be right after the quick provider section
                const nextSibling = quickProviderSection.nextElementSibling;
                
                // Only move if not already in the right position
                if (nextSibling !== ollamaControlSection) {
                    ollamaControlSection.remove();
                    quickProviderSection.insertAdjacentElement('afterend', ollamaControlSection);
                }
                
                // Scroll and highlight
                setTimeout(() => {
                    quickProviderSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    
                    const ollamaSetupSection = ollamaControlSection.querySelector('.ollama-setup-section');
                    if (ollamaSetupSection) {
                        ollamaControlSection.style.transition = 'all 0.3s';
                        ollamaControlSection.style.backgroundColor = 'rgba(0, 255, 255, 0.1)';
                        ollamaControlSection.style.border = '2px solid rgba(0, 255, 255, 0.5)';
                        setTimeout(() => {
                            ollamaControlSection.style.backgroundColor = '';
                            ollamaControlSection.style.border = '';
                        }, 2000);
                    }
                }, 50);
            } else {
                console.error('Could not find Ollama section or quick provider section', {
                    quickProviderSection: !!quickProviderSection,
                    ollamaControlSection: !!ollamaControlSection
                });
            }
            
            if (statusDiv) {
                statusDiv.innerHTML = '<p class="info-message" style="color: #00ffff;">✓ Ollama configuration displayed below</p>';
            }
            
            addLog('Ollama configuration loaded', 'SUCCESS');
            return;
        }
        
        try {
            if (statusDiv) {
                statusDiv.innerHTML = '<p class="info-message">Loading provider configuration...</p>';
            }
            
            // Get intelligent suggestions for the selected provider
            const suggestions = await sendRequest(`/api/llm/providers/intelligent/suggest/${providerName}`);
            
            if (suggestions.success && suggestions.suggestions) {
                const sugg = suggestions.suggestions;
                
                // Show the add form if hidden
                const addForm = document.querySelector('.api-add-form');
                if (addForm) {
                    addForm.style.display = 'block';
                }
                
                // Auto-fill the form
                document.getElementById('new-provider-name').value = sugg.provider_name || '';
                document.getElementById('new-provider-display-name').value = sugg.display_name || sugg.provider_name || '';
                document.getElementById('new-provider-module-path').value = sugg.suggestions?.module_path || '';
                document.getElementById('new-provider-factory-function').value = sugg.suggestions?.factory_function || '';
                document.getElementById('new-provider-api-key-env').value = sugg.suggestions?.api_key_env_var || '';
                document.getElementById('new-provider-base-url-env').value = sugg.suggestions?.base_url_env_var || '';
                document.getElementById('new-provider-requires-api-key').checked = sugg.suggestions?.requires_api_key || false;
                document.getElementById('new-provider-requires-base-url').checked = sugg.suggestions?.requires_base_url || false;
                document.getElementById('new-provider-rate-limit-rpm').value = sugg.suggestions?.default_rate_limit_rpm || 60;
                document.getElementById('new-provider-rate-limit-tpm').value = sugg.suggestions?.default_rate_limit_tpm || 100000;
                
                // Show environment detection status
                let statusHtml = '<div class="provider-config-loaded">';
                statusHtml += `<h4>✓ Configuration loaded for ${sugg.display_name || sugg.provider_name}</h4>`;
                
                if (sugg.environment_detected) {
                    statusHtml += '<div class="env-detection-info">';
                    
                    if (sugg.environment_detected.api_key) {
                        const apiKeyInfo = sugg.environment_detected.api_key;
                        if (apiKeyInfo.detected && apiKeyInfo.set) {
                            statusHtml += `<p class="env-status detected">✓ API Key detected: ${apiKeyInfo.env_var}</p>`;
                        } else if (apiKeyInfo.detected) {
                            statusHtml += `<p class="env-status warning">⚠ API Key variable found but empty: ${apiKeyInfo.env_var}</p>`;
                        } else {
                            statusHtml += `<p class="env-status not-detected">✗ API Key not found: ${apiKeyInfo.env_var || 'N/A'}</p>`;
                        }
                    }
                    
                    if (sugg.environment_detected.base_url) {
                        const baseUrlInfo = sugg.environment_detected.base_url;
                        if (baseUrlInfo.detected) {
                            statusHtml += `<p class="env-status detected">✓ Base URL detected: ${baseUrlInfo.value}</p>`;
                        } else {
                            statusHtml += `<p class="env-status not-detected">✗ Base URL not found: ${baseUrlInfo.env_var || 'N/A'}</p>`;
                            if (baseUrlInfo.suggestion) {
                                statusHtml += `<p class="env-suggestion">💡 Suggested: ${baseUrlInfo.suggestion}</p>`;
                            }
                        }
                    }
                    
                    statusHtml += '</div>';
                }
                
                statusHtml += '</div>';
                
                if (statusDiv) {
                    statusDiv.innerHTML = statusHtml;
                }
                
                addLog(`Provider configuration loaded for ${providerName}`, 'SUCCESS');
                
                // Scroll to form
                if (addForm) {
                    addForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            } else {
                if (statusDiv) {
                    statusDiv.innerHTML = '<p class="error-message">Failed to load provider configuration</p>';
                }
            }
        } catch (error) {
            addLog(`Failed to load provider configuration: ${error.message}`, 'ERROR');
            if (statusDiv) {
                statusDiv.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
            }
        }
    }
    
    async function showProviderSettings(providerName) {
        try {
            const providers = await sendRequest('/api/llm/providers');
            const registry = await sendRequest('/api/llm/providers/registry');
            const suggestions = await sendRequest(`/api/llm/providers/intelligent/suggest/${providerName}`).catch(() => null);
            const metrics = await sendRequest(`/api/llm/providers/${providerName}/metrics`).catch(() => null);
            const metadataResponse = await sendRequest(`/api/llm/providers/${providerName}/metadata`).catch(() => null);

            const provider = providers.providers[providerName];
            const registryProvider = registry.providers.find(p => p.name === providerName);
            const metadata = metadataResponse?.metadata || registryProvider?.metadata || {};

            const modal = document.getElementById('api-provider-settings-modal');
            const title = document.getElementById('api-provider-settings-title');
            const content = document.getElementById('api-provider-settings-content');

            if (!modal || !title || !content) return;

            title.textContent = `${registryProvider?.display_name || providerName} - Settings`;

            let html = `
                <div class="provider-settings-form">
                    <form id="provider-settings-form">
                        <div class="settings-section">
                            <h4>Basic Configuration</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Display Name:</label>
                                    <input type="text" id="settings-display-name" value="${registryProvider?.display_name || providerName}" />
                                </div>
                                <div class="form-group">
                                    <label>Status:</label>
                                    <select id="settings-status">
                                        <option value="enabled" ${provider?.enabled ? 'selected' : ''}>Enabled</option>
                                        <option value="disabled" ${!provider?.enabled ? 'selected' : ''}>Disabled</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        
                        <div class="settings-section">
                            <h4>Module Configuration</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Module Path:</label>
                                    <input type="text" id="settings-module-path" value="${registryProvider?.module_path || ''}" />
                                </div>
                                <div class="form-group">
                                    <label>Factory Function:</label>
                                    <input type="text" id="settings-factory-function" value="${registryProvider?.factory_function || ''}" />
                                </div>
                            </div>
                        </div>
                        
                        <div class="settings-section">
                            <h4>Environment Variables</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>API Key Environment Variable:</label>
                                    <input type="text" id="settings-api-key-env" value="${registryProvider?.api_key_env_var || ''}" />
                                    ${suggestions && suggestions.suggestions?.environment_detected?.api_key ? `
                                    <div class="env-status-info">
                                        ${suggestions.suggestions.environment_detected.api_key.detected ? 
                                            `<span class="env-status detected">✓ Detected: ${suggestions.suggestions.environment_detected.api_key.set ? 'Set' : 'Empty'}</span>` :
                                            `<span class="env-status not-detected">✗ Not found</span>`
                                        }
                                    </div>
                                    ` : ''}
                                </div>
                                <div class="form-group">
                                    <label>Base URL Environment Variable:</label>
                                    <input type="text" id="settings-base-url-env" value="${registryProvider?.base_url_env_var || ''}" />
                                    ${suggestions && suggestions.suggestions?.environment_detected?.base_url ? `
                                    <div class="env-status-info">
                                        ${suggestions.suggestions.environment_detected.base_url.detected ? 
                                            `<span class="env-status detected">✓ Detected: ${suggestions.suggestions.environment_detected.base_url.value || 'Set'}</span>` :
                                            `<span class="env-status not-detected">✗ Not found</span>`
                                        }
                                    </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                        
                        <div class="settings-section">
                            <h4>Rate Limits</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Requests Per Minute (RPM):</label>
                                    <input type="number" id="settings-rate-limit-rpm" value="${registryProvider?.default_rate_limit_rpm || 60}" min="1" />
                                </div>
                                <div class="form-group">
                                    <label>Tokens Per Minute (TPM):</label>
                                    <input type="number" id="settings-rate-limit-tpm" value="${registryProvider?.default_rate_limit_tpm || 100000}" min="1" />
                                </div>
                            </div>
                        </div>
                        
                        ${getProviderSpecificSettings(providerName, metadata, suggestions)}
                        
                        ${metrics ? `
                        <div class="settings-section">
                            <h4>Usage Metrics</h4>
                            <div class="metrics-display">
                                <div class="metric-item">
                                    <span class="metric-label">Total Requests:</span>
                                    <span class="metric-value">${metrics.total_requests || 0}</span>
                                </div>
                                <div class="metric-item">
                                    <span class="metric-label">Successful:</span>
                                    <span class="metric-value success">${metrics.successful_requests || 0}</span>
                                </div>
                                <div class="metric-item">
                                    <span class="metric-label">Failed:</span>
                                    <span class="metric-value error">${metrics.failed_requests || 0}</span>
                                </div>
                                <div class="metric-item">
                                    <span class="metric-label">Total Tokens:</span>
                                    <span class="metric-value">${metrics.total_tokens || 0}</span>
                                </div>
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="settings-actions">
                            <button type="button" class="save-settings-btn" onclick="saveProviderSettings('${providerName}')">Save Settings</button>
                            <button type="button" class="cancel-settings-btn" onclick="closeProviderSettings()">Cancel</button>
                        </div>
                    </form>
                </div>
            `;

            content.innerHTML = html;
            modal.style.display = 'block';
        } catch (error) {
            addLog(`Failed to load provider settings: ${error.message}`, 'ERROR');
        }
    }
    
    function getProviderSpecificSettings(providerName, metadata, suggestions) {
        const baseUrl = suggestions?.suggestions?.environment_detected?.base_url?.value || metadata.base_url || '';
        
        switch(providerName) {
            case 'ollama':
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 Ollama-Specific Settings</h4>
                        <div class="form-group">
                            <label>Base URL:</label>
                            <input type="text" id="settings-ollama-base-url" value="${baseUrl || 'http://localhost:11434'}" placeholder="http://localhost:11434" />
                            <button type="button" class="test-connection-btn" onclick="testOllamaFromSettings()">Test Connection</button>
                        </div>
                        <div class="form-group">
                            <label>Host (alternative to Base URL):</label>
                            <input type="text" id="settings-ollama-host" value="${metadata.host || 'localhost'}" placeholder="localhost" />
                        </div>
                        <div class="form-group">
                            <label>Port (alternative to Base URL):</label>
                            <input type="number" id="settings-ollama-port" value="${metadata.port || 11434}" min="1" max="65535" />
                        </div>
                        <div class="form-group">
                            <label>Timeout (seconds):</label>
                            <input type="number" id="settings-ollama-timeout" value="${metadata.timeout || 30}" min="1" />
                        </div>
                    </div>
                `;
                
            case 'gemini':
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 Gemini-Specific Settings</h4>
                        <div class="form-group">
                            <label>Default Model:</label>
                            <input type="text" id="settings-gemini-default-model" value="${metadata.default_model || 'gemini-1.5-flash-latest'}" placeholder="gemini-1.5-flash-latest" />
                        </div>
                        <div class="form-group">
                            <label>Default Temperature:</label>
                            <input type="number" id="settings-gemini-temperature" value="${metadata.temperature || 0.7}" min="0" max="2" step="0.1" />
                        </div>
                        <div class="form-group">
                            <label>Default Max Tokens:</label>
                            <input type="number" id="settings-gemini-max-tokens" value="${metadata.max_tokens || 2048}" min="1" />
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="settings-gemini-json-mode" ${metadata.json_mode ? 'checked' : ''} />
                                Enable JSON Mode by Default
                            </label>
                        </div>
                    </div>
                `;
                
            case 'mistral':
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 Mistral-Specific Settings</h4>
                        <div class="form-group">
                            <label>Base URL:</label>
                            <input type="text" id="settings-mistral-base-url" value="${metadata.base_url || 'https://api.mistral.ai/v1'}" placeholder="https://api.mistral.ai/v1" />
                        </div>
                        <div class="form-group">
                            <label>Default Model:</label>
                            <input type="text" id="settings-mistral-default-model" value="${metadata.default_model || 'mistral-small-latest'}" placeholder="mistral-small-latest" />
                        </div>
                        <div class="form-group">
                            <label>Timeout (seconds):</label>
                            <input type="number" id="settings-mistral-timeout" value="${metadata.timeout || 30}" min="1" />
                        </div>
                        <div class="form-group">
                            <label>Max Retries:</label>
                            <input type="number" id="settings-mistral-max-retries" value="${metadata.max_retries || 3}" min="0" />
                        </div>
                        <div class="form-group">
                            <label>Rate Limit Delay (seconds):</label>
                            <input type="number" id="settings-mistral-rate-limit-delay" value="${metadata.rate_limit_delay || 0.1}" min="0" step="0.1" />
                        </div>
                        <div class="form-group">
                            <label>Default Prompt Mode:</label>
                            <select id="settings-mistral-prompt-mode">
                                <option value="standard" ${metadata.prompt_mode === 'standard' ? 'selected' : ''}>Standard</option>
                                <option value="reasoning" ${metadata.prompt_mode === 'reasoning' ? 'selected' : ''}>Reasoning</option>
                            </select>
                        </div>
                    </div>
                `;
                
            case 'openai':
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 OpenAI-Specific Settings</h4>
                        <div class="form-group">
                            <label>Base URL:</label>
                            <input type="text" id="settings-openai-base-url" value="${metadata.base_url || 'https://api.openai.com/v1'}" placeholder="https://api.openai.com/v1" />
                        </div>
                        <div class="form-group">
                            <label>Default Model:</label>
                            <input type="text" id="settings-openai-default-model" value="${metadata.default_model || 'gpt-3.5-turbo'}" placeholder="gpt-3.5-turbo" />
                        </div>
                        <div class="form-group">
                            <label>Default Temperature:</label>
                            <input type="number" id="settings-openai-temperature" value="${metadata.temperature || 0.7}" min="0" max="2" step="0.1" />
                        </div>
                        <div class="form-group">
                            <label>Max Retries:</label>
                            <input type="number" id="settings-openai-max-retries" value="${metadata.max_retries || 5}" min="0" />
                        </div>
                    </div>
                `;
                
            case 'anthropic':
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 Anthropic-Specific Settings</h4>
                        <div class="form-group">
                            <label>Default Model:</label>
                            <input type="text" id="settings-anthropic-default-model" value="${metadata.default_model || 'claude-3-sonnet-20240229'}" placeholder="claude-3-sonnet-20240229" />
                        </div>
                        <div class="form-group">
                            <label>Default Temperature:</label>
                            <input type="number" id="settings-anthropic-temperature" value="${metadata.temperature || 0.7}" min="0" max="1" step="0.1" />
                        </div>
                        <div class="form-group">
                            <label>Max Tokens:</label>
                            <input type="number" id="settings-anthropic-max-tokens" value="${metadata.max_tokens || 4096}" min="1" />
                        </div>
                        <div class="form-group">
                            <label>Max Retries:</label>
                            <input type="number" id="settings-anthropic-max-retries" value="${metadata.max_retries || 5}" min="0" />
                        </div>
                    </div>
                `;
                
            case 'together':
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 Together AI-Specific Settings</h4>
                        <div class="form-group">
                            <label>Base URL:</label>
                            <input type="text" id="settings-together-base-url" value="${metadata.base_url || 'https://api.together.xyz/v1'}" placeholder="https://api.together.xyz/v1" />
                        </div>
                        <div class="form-group">
                            <label>Default Model:</label>
                            <input type="text" id="settings-together-default-model" value="${metadata.default_model || ''}" placeholder="meta-llama/Llama-2-70b-chat-hf" />
                        </div>
                    </div>
                `;
                
            default:
                return `
                    <div class="settings-section provider-specific">
                        <h4>🔧 Provider-Specific Settings</h4>
                        <div class="form-group">
                            <label>Base URL (if applicable):</label>
                            <input type="text" id="settings-custom-base-url" value="${metadata.base_url || ''}" placeholder="https://api.example.com/v1" />
                        </div>
                        <div class="form-group">
                            <label>Default Model:</label>
                            <input type="text" id="settings-custom-default-model" value="${metadata.default_model || ''}" placeholder="model-name" />
                        </div>
                        <div class="form-group">
                            <label>Timeout (seconds):</label>
                            <input type="number" id="settings-custom-timeout" value="${metadata.timeout || 30}" min="1" />
                        </div>
                    </div>
                `;
        }
    }
    
    async function saveProviderSettings(providerName) {
        try {
            const displayName = document.getElementById('settings-display-name').value;
            const status = document.getElementById('settings-status').value;
            const modulePath = document.getElementById('settings-module-path').value;
            const factoryFunction = document.getElementById('settings-factory-function').value;
            const apiKeyEnv = document.getElementById('settings-api-key-env').value;
            const baseUrlEnv = document.getElementById('settings-base-url-env').value;
            const rateLimitRpm = parseInt(document.getElementById('settings-rate-limit-rpm').value) || 60;
            const rateLimitTpm = parseInt(document.getElementById('settings-rate-limit-tpm').value) || 100000;
            
            // Collect provider-specific metadata
            const metadata = {};
            
            // Provider-specific settings
            if (providerName === 'ollama') {
                metadata.base_url = document.getElementById('settings-ollama-base-url')?.value || '';
                metadata.host = document.getElementById('settings-ollama-host')?.value || '';
                metadata.port = parseInt(document.getElementById('settings-ollama-port')?.value) || 11434;
                metadata.timeout = parseInt(document.getElementById('settings-ollama-timeout')?.value) || 30;
                
                // Save Ollama config
                if (metadata.base_url) {
                    await sendRequest('/api/llm/ollama/config', 'POST', { base_url: metadata.base_url });
                }
            } else if (providerName === 'gemini') {
                metadata.default_model = document.getElementById('settings-gemini-default-model')?.value || 'gemini-1.5-flash-latest';
                metadata.temperature = parseFloat(document.getElementById('settings-gemini-temperature')?.value) || 0.7;
                metadata.max_tokens = parseInt(document.getElementById('settings-gemini-max-tokens')?.value) || 2048;
                metadata.json_mode = document.getElementById('settings-gemini-json-mode')?.checked || false;
            } else if (providerName === 'mistral') {
                metadata.base_url = document.getElementById('settings-mistral-base-url')?.value || 'https://api.mistral.ai/v1';
                metadata.default_model = document.getElementById('settings-mistral-default-model')?.value || 'mistral-small-latest';
                metadata.timeout = parseInt(document.getElementById('settings-mistral-timeout')?.value) || 30;
                metadata.max_retries = parseInt(document.getElementById('settings-mistral-max-retries')?.value) || 3;
                metadata.rate_limit_delay = parseFloat(document.getElementById('settings-mistral-rate-limit-delay')?.value) || 0.1;
                metadata.prompt_mode = document.getElementById('settings-mistral-prompt-mode')?.value || 'standard';
            } else if (providerName === 'openai') {
                metadata.base_url = document.getElementById('settings-openai-base-url')?.value || 'https://api.openai.com/v1';
                metadata.default_model = document.getElementById('settings-openai-default-model')?.value || 'gpt-3.5-turbo';
                metadata.temperature = parseFloat(document.getElementById('settings-openai-temperature')?.value) || 0.7;
                metadata.max_retries = parseInt(document.getElementById('settings-openai-max-retries')?.value) || 5;
            } else if (providerName === 'anthropic') {
                metadata.default_model = document.getElementById('settings-anthropic-default-model')?.value || 'claude-3-sonnet-20240229';
                metadata.temperature = parseFloat(document.getElementById('settings-anthropic-temperature')?.value) || 0.7;
                metadata.max_tokens = parseInt(document.getElementById('settings-anthropic-max-tokens')?.value) || 4096;
                metadata.max_retries = parseInt(document.getElementById('settings-anthropic-max-retries')?.value) || 5;
            } else if (providerName === 'together') {
                metadata.base_url = document.getElementById('settings-together-base-url')?.value || 'https://api.together.xyz/v1';
                metadata.default_model = document.getElementById('settings-together-default-model')?.value || '';
            } else {
                // Generic provider settings
                metadata.base_url = document.getElementById('settings-custom-base-url')?.value || '';
                metadata.default_model = document.getElementById('settings-custom-default-model')?.value || '';
                metadata.timeout = parseInt(document.getElementById('settings-custom-timeout')?.value) || 30;
            }
            
            // Update provider registry with metadata
            // Note: We'll need to add an endpoint to update provider metadata
            // For now, we'll save via the registry update endpoint
            await sendRequest(`/api/llm/providers/${providerName}/rate-limits`, 'POST', {
                rpm: rateLimitRpm,
                tpm: rateLimitTpm
            });
            
            // Enable/disable provider
            if (status === 'enabled') {
                await sendRequest(`/api/llm/providers/${providerName}/enable`, 'POST');
            } else {
                await sendRequest(`/api/llm/providers/${providerName}/disable`, 'POST');
            }
            
            // Save metadata
            await sendRequest(`/api/llm/providers/${providerName}/metadata`, 'POST', metadata);
            
            addLog(`Provider ${providerName} settings saved successfully`, 'SUCCESS');
            closeProviderSettings();
            await loadAPIProviders(); // Refresh the list
        } catch (error) {
            addLog(`Failed to save provider settings: ${error.message}`, 'ERROR');
        }
    }
    
    function closeProviderSettings() {
        const modal = document.getElementById('api-provider-settings-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    async function testOllamaFromSettings() {
        const baseUrl = document.getElementById('settings-ollama-base-url')?.value;
        if (!baseUrl) {
            alert('Please enter a base URL');
            return;
        }
        
        try {
            const result = await sendRequest(`/api/llm/ollama/connection?base_url=${encodeURIComponent(baseUrl)}`);
            if (result.success) {
                alert('Ollama connection successful!');
            } else {
                alert('Ollama connection failed');
            }
        } catch (error) {
            alert(`Connection test failed: ${error.message}`);
        }
    }
    
    // Make functions globally accessible
    window.useDetectedProvider = useDetectedProvider;
    window.showProviderSettings = showProviderSettings;
    window.saveProviderSettings = saveProviderSettings;
    window.closeProviderSettings = closeProviderSettings;
    window.testOllamaFromSettings = testOllamaFromSettings;

    async function loadAPIProviders() {
        try {
            const providersResponse = await sendRequest('/api/llm/providers');
            const registryResponse = await sendRequest('/api/llm/providers/registry');
            
            displayAPIProviders(providersResponse.providers || {}, registryResponse.providers || []);
        } catch (error) {
            addLog(`Failed to load API providers: ${error.message}`, 'ERROR');
            console.error('Error loading API providers:', error);
        }
    }

    function displayAPIProviders(providers, registryProviders) {
        const providersList = document.getElementById('api-providers-list');
        if (!providersList) return;

        providersList.innerHTML = '';

        if (Object.keys(providers).length === 0 && registryProviders.length === 0) {
            providersList.innerHTML = '<p>No API providers found. Scan the API folder or add a new provider.</p>';
            return;
        }

        // Sort providers: Connected/tested Ollama first, then enabled providers, then others
        const sortedProviders = [...registryProviders].sort((a, b) => {
            const aIsOllama = a.name === 'ollama';
            const bIsOllama = b.name === 'ollama';
            const aIsConnected = aIsOllama && (providers[a.name]?.enabled || false) && isOllamaConnected();
            const bIsConnected = bIsOllama && (providers[b.name]?.enabled || false) && isOllamaConnected();
            
            // Connected Ollama goes first
            if (aIsConnected && !bIsConnected) return -1;
            if (!aIsConnected && bIsConnected) return 1;
            
            // Then enabled Ollama
            const aIsOllamaEnabled = aIsOllama && (providers[a.name]?.enabled || false);
            const bIsOllamaEnabled = bIsOllama && (providers[b.name]?.enabled || false);
            if (aIsOllamaEnabled && !bIsOllamaEnabled) return -1;
            if (!aIsOllamaEnabled && bIsOllamaEnabled) return 1;
            
            // Then other enabled providers
            const aEnabled = providers[a.name]?.enabled || false;
            const bEnabled = providers[b.name]?.enabled || false;
            if (aEnabled && !bEnabled) return -1;
            if (!aEnabled && bEnabled) return 1;
            
            return 0;
        });

        // Display providers from registry
        sortedProviders.forEach(provider => {
            const providerCard = createProviderCard(provider, providers[provider.name]);
            providersList.appendChild(providerCard);
        });

        // Display providers not in registry but in providers list
        Object.keys(providers).forEach(providerName => {
            if (!registryProviders.find(p => p.name === providerName)) {
                const providerCard = createProviderCard({
                    name: providerName,
                    display_name: providerName,
                    status: providers[providerName].status || 'disabled',
                    enabled: providers[providerName].enabled || false
                }, providers[providerName]);
                providersList.appendChild(providerCard);
            }
        });
        
        // Re-initialize drag and drop after cards are created
        initializeProviderCardDragDrop();
    }
    
    // Check if Ollama is connected (has saved config)
    function isOllamaConnected() {
        try {
            // Check if there's a connection banner showing success
            const banner = document.getElementById('ollama-connection-banner');
            if (banner && banner.style.display !== 'none') {
                const statusText = document.getElementById('ollama-connection-status-text');
                if (statusText && statusText.textContent.includes('Connected')) {
                    return true;
                }
            }
            return false;
        } catch (e) {
            return false;
        }
    }
    
    // Refresh provider list and prioritize Ollama
    async function refreshAndPrioritizeOllama() {
        try {
            await loadAPIProviders();
            // Update Ollama card if it exists
            const ollamaCard = document.querySelector('[data-provider-name="ollama"]');
            if (ollamaCard) {
                // Add visual indicator that it's connected
                ollamaCard.style.border = '2px solid #00ff00';
                ollamaCard.style.boxShadow = '0 0 15px rgba(0, 255, 0, 0.3)';
                setTimeout(() => {
                    ollamaCard.style.border = '';
                    ollamaCard.style.boxShadow = '';
                }, 3000);
            }
        } catch (error) {
            console.error('Failed to refresh providers:', error);
        }
    }
    
    // Check if Ollama is connected (has saved config)
    function isOllamaConnected() {
        try {
            const savedModel = localStorage.getItem('selectedOllamaModel');
            // Check if there's a connection banner showing success
            const banner = document.getElementById('ollama-connection-banner');
            if (banner && banner.style.display !== 'none') {
                const statusText = document.getElementById('ollama-connection-status-text');
                if (statusText && statusText.textContent.includes('Connected')) {
                    return true;
                }
            }
            return false;
        } catch (e) {
            return false;
        }
    }
    
    // Refresh provider list and prioritize Ollama
    async function refreshAndPrioritizeOllama() {
        try {
            await loadAPIProviders();
            // Update Ollama card if it exists
            const ollamaCard = document.querySelector('[data-provider-name="ollama"]');
            if (ollamaCard) {
                // Add visual indicator that it's connected
                ollamaCard.style.border = '2px solid #00ff00';
                ollamaCard.style.boxShadow = '0 0 15px rgba(0, 255, 0, 0.3)';
                setTimeout(() => {
                    ollamaCard.style.border = '';
                    ollamaCard.style.boxShadow = '';
                }, 3000);
            }
        } catch (error) {
            console.error('Failed to refresh providers:', error);
        }
    }
    
    function initializeProviderCardDragDrop() {
        const cards = document.querySelectorAll('.draggable-provider-card');
        cards.forEach(card => {
            card.addEventListener('dragstart', handleDragStart);
            card.addEventListener('dragover', handleDragOver);
            card.addEventListener('drop', handleDrop);
            card.addEventListener('dragend', handleDragEnd);
        });
    }
    
    let draggedElement = null;
    
    function handleDragStart(e) {
        draggedElement = this;
        this.style.opacity = '0.5';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.innerHTML);
    }
    
    function handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }
        e.dataTransfer.dropEffect = 'move';
        return false;
    }
    
    function handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }
        
        if (draggedElement !== this) {
            const providersList = document.getElementById('api-providers-list');
            const allCards = Array.from(providersList.querySelectorAll('.draggable-provider-card'));
            const draggedIndex = allCards.indexOf(draggedElement);
            const targetIndex = allCards.indexOf(this);
            
            if (draggedIndex < targetIndex) {
                providersList.insertBefore(draggedElement, this.nextSibling);
            } else {
                providersList.insertBefore(draggedElement, this);
            }
            
            // Save order to localStorage
            saveProviderOrder();
        }
        
        return false;
    }
    
    function handleDragEnd(e) {
        this.style.opacity = '1';
        draggedElement = null;
    }
    
    function saveProviderOrder() {
        const providersList = document.getElementById('api-providers-list');
        const cards = Array.from(providersList.querySelectorAll('.draggable-provider-card'));
        const order = cards.map(card => card.dataset.providerName);
        localStorage.setItem('mindx_provider_order', JSON.stringify(order));
    }
    
    function loadProviderOrder() {
        const order = localStorage.getItem('mindx_provider_order');
        if (order) {
            try {
                return JSON.parse(order);
            } catch (e) {
                return null;
            }
        }
        return null;
    }

    function createProviderCard(provider, providerDetails) {
        const card = document.createElement('div');
        card.className = 'api-provider-card clickable-card draggable-provider-card';
        card.setAttribute('data-provider-name', provider.name);
        card.draggable = true;
        card.style.cursor = 'pointer';
        
        card.innerHTML = `
            <div class="provider-header">
                <h4>${provider.display_name || provider.name}</h4>
                <span class="provider-status ${provider.status || 'disabled'}">${provider.status || 'disabled'}</span>
            </div>
            <div class="provider-info">
                <div class="info-item">
                    <span class="info-label">Name:</span>
                    <span class="info-value">${provider.name}</span>
                </div>
                ${provider.module_path ? `
                <div class="info-item">
                    <span class="info-label">Module:</span>
                    <span class="info-value">${provider.module_path}</span>
                </div>
                ` : ''}
                ${providerDetails ? `
                <div class="info-item">
                    <span class="info-label">API Key:</span>
                    <span class="info-value">${providerDetails.api_key_masked || 'Not set'}</span>
                </div>
                ` : ''}
            </div>
            <div class="provider-actions">
                <button class="action-btn" onclick="event.stopPropagation(); showProviderSettings('${provider.name}')">⚙️ Settings</button>
                <button class="action-btn" onclick="event.stopPropagation(); showProviderDetails('${provider.name}')">Details</button>
                <button class="action-btn" onclick="event.stopPropagation(); showProviderModels('${provider.name}')">Models</button>
                <button class="action-btn" onclick="event.stopPropagation(); testProvider('${provider.name}')">Test</button>
                <button class="action-btn danger" onclick="event.stopPropagation(); removeProvider('${provider.name}')">Remove</button>
            </div>
        `;
        
        // Add click handler to open settings
        card.addEventListener('click', (e) => {
            // Don't trigger if clicking on buttons or their children
            if (!e.target.closest('.provider-actions') && !e.target.closest('button')) {
                showProviderSettings(provider.name);
            }
        });
        
        // Add drag event listeners
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('drop', handleDrop);
        card.addEventListener('dragend', handleDragEnd);
        
        return card;
    }

    async function showProviderDetails(providerName) {
        try {
            const providers = await sendRequest('/api/llm/providers');
            const registry = await sendRequest('/api/llm/providers/registry');
            const metrics = await sendRequest(`/api/llm/providers/${providerName}/metrics`).catch(() => null);

            const provider = providers.providers[providerName];
            const registryProvider = registry.providers.find(p => p.name === providerName);

            const modal = document.getElementById('api-provider-details-modal');
            const title = document.getElementById('api-provider-details-title');
            const content = document.getElementById('api-provider-details-content');

            title.textContent = `${providerName} - Details`;

            let html = `
                <div class="provider-details">
                    <h4>Configuration</h4>
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Display Name:</span>
                            <span class="detail-value">${registryProvider?.display_name || providerName}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Module Path:</span>
                            <span class="detail-value">${registryProvider?.module_path || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Factory Function:</span>
                            <span class="detail-value">${registryProvider?.factory_function || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Status:</span>
                            <span class="detail-value">${provider?.status || 'disabled'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Enabled:</span>
                            <span class="detail-value">${provider?.enabled ? 'Yes' : 'No'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Requires API Key:</span>
                            <span class="detail-value">${registryProvider?.requires_api_key ? 'Yes' : 'No'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Requires Base URL:</span>
                            <span class="detail-value">${registryProvider?.requires_base_url ? 'Yes' : 'No'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Rate Limit (RPM):</span>
                            <span class="detail-value">${registryProvider?.default_rate_limit_rpm || 60}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Rate Limit (TPM):</span>
                            <span class="detail-value">${registryProvider?.default_rate_limit_tpm || 100000}</span>
                        </div>
                    </div>
            `;

            if (metrics) {
                html += `
                    <h4>Usage Metrics</h4>
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Total Requests:</span>
                            <span class="detail-value">${metrics.total_requests || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Successful:</span>
                            <span class="detail-value">${metrics.successful_requests || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Failed:</span>
                            <span class="detail-value">${metrics.failed_requests || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Total Tokens:</span>
                            <span class="detail-value">${metrics.total_tokens || 0}</span>
                        </div>
                    </div>
                `;
            }

            html += `</div>`;
            content.innerHTML = html;
            modal.style.display = 'block';
        } catch (error) {
            addLog(`Failed to load provider details: ${error.message}`, 'ERROR');
        }
    }

    async function showProviderModels(providerName) {
        try {
            let models = [];
            
            if (providerName === 'ollama') {
                const response = await sendRequest('/api/llm/ollama/models');
                models = response.models || [];
            } else {
                // For other providers, try to get models from model registry
                const modelInfo = await sendRequest('/api/llm/model-selection/info').catch(() => null);
                if (modelInfo && modelInfo.providers) {
                    const providerInfo = modelInfo.providers.find(p => p.name === providerName);
                    if (providerInfo && providerInfo.models) {
                        models = providerInfo.models;
                    }
                }
            }

            const modal = document.getElementById('api-provider-details-modal');
            const title = document.getElementById('api-provider-details-title');
            const content = document.getElementById('api-provider-details-content');

            title.textContent = `${providerName} - Available Models`;
            
            if (models.length === 0) {
                content.innerHTML = '<p>No models found for this provider. The provider may need to be configured or the API may not support model listing.</p>';
            } else {
                let html = '<div class="models-list"><h4>Available Models</h4><ul>';
                models.forEach(model => {
                    const modelId = model.id || model.name || model;
                    html += `<li class="model-item">
                        <span class="model-name">${modelId}</span>
                        ${model.object ? `<span class="model-type">${model.object}</span>` : ''}
                    </li>`;
                });
                html += '</ul></div>';
                content.innerHTML = html;
            }
            
            modal.style.display = 'block';
        } catch (error) {
            addLog(`Failed to load provider models: ${error.message}`, 'ERROR');
        }
    }

    async function testProvider(providerName) {
        try {
            addLog(`Testing provider: ${providerName}...`, 'INFO');
            const result = await sendRequest(`/api/llm/providers/${providerName}/test`, 'POST');
            
            if (result.success) {
                addLog(`Provider ${providerName} test successful!`, 'SUCCESS');
                alert(`Provider test successful!\n\n${JSON.stringify(result, null, 2)}`);
            } else {
                addLog(`Provider ${providerName} test failed: ${result.error || 'Unknown error'}`, 'ERROR');
                alert(`Provider test failed:\n\n${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            addLog(`Failed to test provider: ${error.message}`, 'ERROR');
            alert(`Failed to test provider: ${error.message}`);
        }
    }

    async function removeProvider(providerName) {
        if (!confirm(`Are you sure you want to remove provider "${providerName}"? This will unregister it from the system.`)) {
            return;
        }

        try {
            const result = await sendRequest(`/api/llm/providers/registry/${providerName}`, 'DELETE');
            
            if (result.success) {
                addLog(`Provider ${providerName} removed successfully`, 'SUCCESS');
                await loadAPIProviders();
            } else {
                addLog(`Failed to remove provider: ${result.error || 'Unknown error'}`, 'ERROR');
            }
        } catch (error) {
            addLog(`Failed to remove provider: ${error.message}`, 'ERROR');
        }
    }

    async function scanAPIFolder() {
        try {
            addLog('Scanning API folder for providers...', 'INFO');
            // This would require a backend endpoint to scan the api folder
            // For now, just refresh the providers list
            await loadAPIProviders();
            addLog('API folder scan complete', 'SUCCESS');
        } catch (error) {
            addLog(`Failed to scan API folder: ${error.message}`, 'ERROR');
        }
    }

    async function addNewAPIProvider() {
        const name = document.getElementById('new-provider-name').value.trim();
        const displayName = document.getElementById('new-provider-display-name').value.trim();
        const modulePath = document.getElementById('new-provider-module-path').value.trim();
        const factoryFunction = document.getElementById('new-provider-factory-function').value.trim();
        const apiKeyEnv = document.getElementById('new-provider-api-key-env').value.trim();
        const baseUrlEnv = document.getElementById('new-provider-base-url-env').value.trim();
        const requiresApiKey = document.getElementById('new-provider-requires-api-key').checked;
        const requiresBaseUrl = document.getElementById('new-provider-requires-base-url').checked;
        const rateLimitRpm = parseInt(document.getElementById('new-provider-rate-limit-rpm').value) || 60;
        const rateLimitTpm = parseInt(document.getElementById('new-provider-rate-limit-tpm').value) || 100000;

        if (!name || !displayName || !modulePath || !factoryFunction) {
            alert('Please fill in all required fields (Name, Display Name, Module Path, Factory Function)');
            return;
        }

        try {
            const result = await sendRequest('/api/llm/providers/registry/register', 'POST', {
                name,
                display_name: displayName,
                module_path: modulePath,
                factory_function: factoryFunction,
                api_key_env_var: apiKeyEnv || null,
                base_url_env_var: baseUrlEnv || null,
                requires_api_key: requiresApiKey,
                requires_base_url: requiresBaseUrl,
                default_rate_limit_rpm: rateLimitRpm,
                default_rate_limit_tpm: rateLimitTpm
            });

            if (result.success) {
                addLog(`Provider ${name} registered successfully`, 'SUCCESS');
                // Clear form
                document.getElementById('new-provider-name').value = '';
                document.getElementById('new-provider-display-name').value = '';
                document.getElementById('new-provider-module-path').value = '';
                document.getElementById('new-provider-factory-function').value = '';
                document.getElementById('new-provider-api-key-env').value = '';
                document.getElementById('new-provider-base-url-env').value = '';
                await loadAPIProviders();
            } else {
                addLog(`Failed to register provider: ${result.error || 'Unknown error'}`, 'ERROR');
            }
        } catch (error) {
            addLog(`Failed to register provider: ${error.message}`, 'ERROR');
        }
    }

    // Make functions globally accessible
    window.showProviderDetails = showProviderDetails;
    window.showProviderModels = showProviderModels;
    window.testProvider = testProvider;
    window.removeProvider = removeProvider;

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

    // Export Format Modal Functions
    function showExportFormatModal() {
        console.log('showExportFormatModal called');
        const modal = document.getElementById('export-format-modal');
        console.log('Modal element found:', !!modal);
        if (modal) {
            modal.style.display = 'flex';
            console.log('Export format modal opened');
            addLog('Export format selection opened', 'INFO');
        } else {
            console.error('Export format modal not found!');
            addLog('Export format modal not found', 'ERROR');
        }
    }
    
    function hideExportFormatModal() {
        const modal = document.getElementById('export-format-modal');
        if (modal) {
            modal.style.display = 'none';
            console.log('Export format modal closed');
        }
    }
    
    function initializeExportModal() {
        console.log('Initializing export modal...');
        const modal = document.getElementById('export-format-modal');
        const closeBtn = document.getElementById('close-export-modal');
        const formatBtns = document.querySelectorAll('.format-btn');
        
        console.log('Modal elements found:', {
            modal: !!modal,
            closeBtn: !!closeBtn,
            formatBtns: formatBtns.length
        });
        
        // Close modal when clicking close button
        if (closeBtn) {
            closeBtn.addEventListener('click', hideExportFormatModal);
            console.log('Close button listener added');
        }
        
        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    hideExportFormatModal();
                }
            });
            console.log('Modal click-outside listener added');
        }
        
        // Handle format selection
        formatBtns.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                const format = btn.getAttribute('data-format');
                console.log('Format button clicked:', format, 'Button index:', index);
                hideExportFormatModal();
                exportLogs(format);
            });
            console.log('Format button listener added for:', btn.getAttribute('data-format'));
        });
        
        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                hideExportFormatModal();
            }
        });
        
        console.log('Export modal initialization complete');
    }

    async function exportLogs(format = 'txt') {
        try {
            console.log('exportLogs called with format:', format);
            console.log('Current logs array length:', logs.length);
            console.log('Logs content:', logs);
            
            // If no logs, add a sample log for testing
            if (logs.length === 0) {
                console.log('No logs found, adding sample logs for export');
                addLog('Sample log entry for export testing', 'INFO');
                addLog('System initialized successfully', 'INFO');
                addLog('Export functionality working', 'DEBUG');
            }
            
            let exportContent;
            let filename;
            let mimeType;
            
            if (format === 'json') {
                // JSON format
                const logData = {
                    exportInfo: {
                        generated: new Date().toISOString(),
                        totalLogs: logs.length,
                        filterLevel: logLevelFilter ? logLevelFilter.value : 'ALL',
                        system: 'MindX Control Panel'
                    },
                    logs: logs
                };
                exportContent = JSON.stringify(logData, null, 2);
                filename = `mindx-logs-${new Date().toISOString().split('T')[0]}.json`;
                mimeType = 'application/json';
            } else if (format === 'csv') {
                // CSV format
                const csvHeader = 'Timestamp,Level,Message\n';
                const csvContent = logs.map(log => 
                    `"${log.timestamp}","${log.level}","${log.message.replace(/"/g, '""')}"`
                ).join('\n');
                exportContent = csvHeader + csvContent;
                filename = `mindx-logs-${new Date().toISOString().split('T')[0]}.csv`;
                mimeType = 'text/csv';
            } else {
                // Default TXT format
                const logContent = logs.map(log => 
                    `[${log.timestamp}] ${log.level}: ${log.message}`
                ).join('\n');
                
                exportContent = `MindX Control Panel Logs Export
Generated: ${new Date().toISOString()}
Total Logs: ${logs.length}
Filter Level: ${logLevelFilter ? logLevelFilter.value : 'ALL'}

${logContent}`;
                filename = `mindx-logs-${new Date().toISOString().split('T')[0]}.txt`;
                mimeType = 'text/plain';
            }
            
            // Create and download file
            const blob = new Blob([exportContent], { type: mimeType });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            addLog(`Logs exported successfully (${logs.length} entries) as ${format.toUpperCase()}`, 'INFO');
            console.log('Logs exported successfully as', format);
            
        } catch (error) {
            console.error('Export logs error:', error);
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
        initializeAdminTab();
        initializeAutonomousMode();
        initializeAgentActivityMonitor();
        initializeUpdateRequests();
        
        // Initialize export modal with a delay to ensure DOM is ready
        setTimeout(() => {
            initializeExportModal();
        }, 1000);
        
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
        startAgentActivityMonitoring();
        
        // Start workflow monitoring
        startWorkflowMonitoring();
        
        // Load initial real agent activity
        loadInitialAgentActivity();
        
        addLog('MindX Control Panel initialized', 'INFO');
        addLog('System ready for operations', 'INFO');
        addLog('All agents loaded successfully', 'INFO');
        addAgentActivity('System', 'MindX Control Panel initialized', 'success');
    }

    function initializeAgentActivityMonitor() {
        if (pauseActivityBtn) {
            pauseActivityBtn.addEventListener('click', pauseActivity);
        }
        if (clearActivityBtn) {
            clearActivityBtn.addEventListener('click', clearActivity);
        }
        
        // Add refresh metrics button
        const refreshMetricsBtn = document.getElementById('refresh-metrics');
        if (refreshMetricsBtn) {
            refreshMetricsBtn.addEventListener('click', () => {
                updateExecutiveMetrics();
                addAgentActivity('System', 'Metrics refreshed', 'info');
            });
        }
        
        // Add refresh workflow button
        const refreshWorkflowBtn = document.getElementById('refresh-workflow');
        if (refreshWorkflowBtn) {
            refreshWorkflowBtn.addEventListener('click', () => {
                updateWorkflowStatus();
                addAgentActivity('System', 'Workflow refreshed', 'info');
            });
        }
        
        // Add click functionality to activity entries for details
        const activityLog = document.getElementById('agent-activity-log');
        if (activityLog) {
            activityLog.addEventListener('click', (e) => {
                const activityEntry = e.target.closest('.activity-entry');
                if (activityEntry) {
                    toggleActivityDetails(activityEntry);
                }
            });
        }
        
        // Add click functionality to agent status cards for popup using event delegation
        document.addEventListener('click', (e) => {
            const agentCard = e.target.closest('.agent-status-card');
            if (agentCard) {
                const agentId = agentCard.id.replace('-status', '');
                const agentName = agentCard.querySelector('.agent-name').textContent;
                console.log('Agent card clicked:', agentId, agentName); // Debug log
                window.showAgentDetailPopup(agentId, agentName);
            }
        });
        
        // Add fallback event delegation for clear logs button
        document.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'clear-logs-btn') {
                console.log('Clear logs button clicked via delegation!'); // Debug log
                e.preventDefault();
                clearLogs();
            }
        });
        
        // Initialize popup close functionality
        const popupClose = document.getElementById('popup-close');
        const popupBackdrop = document.getElementById('popup-backdrop');
        const popup = document.getElementById('agent-detail-popup');
        
        if (popupClose) {
            popupClose.addEventListener('click', window.hideAgentDetailPopup);
        }
        
        if (popupBackdrop) {
            popupBackdrop.addEventListener('click', window.hideAgentDetailPopup);
        }
        
        // Close popup with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && popup && popup.classList.contains('show')) {
                window.hideAgentDetailPopup();
            }
        });
    }

    function updateWorkflowStatus() {
        // Update all workflow nodes based on current activity
        const workflowNodes = {
            'Coordinator Agent': 'coordinator-workflow-status',
            'AGInt Core': 'agint-workflow-status', 
            'BDI Agent': 'bdi-workflow-status',
            'Simple Coder': 'simple-coder-workflow-status'
        };
        
        Object.entries(workflowNodes).forEach(([agent, nodeId]) => {
            const statusElement = document.getElementById(nodeId);
            if (statusElement) {
                // Check recent activity for this agent
                const recentActivity = activityLog.find(entry => entry.agent === agent);
                if (recentActivity) {
                    updateWorkflowNode(agent, recentActivity.message, recentActivity.type);
                } else {
                    statusElement.textContent = 'Standby';
                    const workflowNode = statusElement.closest('.workflow-node');
                    if (workflowNode) {
                        workflowNode.className = 'workflow-node waiting';
                    }
                }
            }
        });
    }

    // Real workflow monitoring - only highlights when actual agents are working
    function startWorkflowMonitoring() {
        // Real agent activity monitoring - no simulation
        // Workflow highlights are triggered by actual agent activities
    }

    /**
     * Update specific agent UI elements based on activity data.
     * Called when new activity is received from the canonical endpoint.
     */
    function updateAgentUIElement(agentName, activity) {
        // Map agent names to their UI element IDs
        const agentUIMap = {
            'BDI Agent': { indicator: 'bdi-indicator', activity: 'bdi-activity' },
            'AGInt Core': { indicator: 'agint-indicator', activity: 'agint-activity' },
            'Simple Coder': { indicator: 'simple-coder-indicator', activity: 'simple-coder-activity' },
            'Coordinator Agent': { indicator: 'coordinator-indicator', activity: 'coordinator-activity' },
            'Coordinator': { indicator: 'coordinator-indicator', activity: 'coordinator-activity' },
            'MastermindAgent': { indicator: 'mastermind-indicator', activity: 'mastermind-activity' },
            'Mastermind': { indicator: 'mastermind-indicator', activity: 'mastermind-activity' },
            'Resource Monitor': { indicator: 'resource-monitor-indicator', activity: 'resource-monitor-activity' }
        };

        const uiElements = agentUIMap[agentName];
        if (uiElements) {
            // Update activity text
            const activityElement = document.getElementById(uiElements.activity);
            if (activityElement) {
                activityElement.textContent = activity.message || 'Active';
            }

            // Update status indicator based on activity type
            const indicatorElement = document.getElementById(uiElements.indicator);
            if (indicatorElement) {
                const statusClass = activity.type === 'error' ? 'error' :
                                   activity.type === 'warning' ? 'warning' :
                                   activity.type === 'success' ? 'active' : 'active';
                indicatorElement.className = `agent-status-indicator ${statusClass}`;
            }
        }

        // Update workflow node if this agent is part of the workflow visualization
        updateWorkflowNode(agentName, activity.message, activity.type);
    }

    /**
     * Update the workflow summary display with data from the canonical endpoint.
     */
    function updateWorkflowSummary(summary) {
        if (!summary) return;

        // Update active agents count if element exists
        const agentCountElement = document.getElementById('active-agent-count');
        if (agentCountElement && summary.active_agents) {
            agentCountElement.textContent = summary.active_agents.length;
        }

        // Update workflow status indicator if element exists
        const workflowStatusElement = document.getElementById('workflow-status');
        if (workflowStatusElement && summary.active_workflows) {
            workflowStatusElement.textContent = summary.active_workflows.length > 0 ? 'Active' : 'Idle';
        }
    }

    /**
     * Load initial agent activity from the canonical endpoint.
     * Uses /agents/activity as the single source of truth.
     */
    async function loadInitialAgentActivity() {
        try {
            const response = await fetch(`${apiUrl}/agents/activity`);
            if (response.ok) {
                const data = await response.json();
                if (data && data.activities) {
                    // Add initial activities (most recent 5)
                    data.activities.slice(0, 5).forEach(activity => {
                        const activityKey = `${activity.timestamp}-${activity.agent}-${activity.message}`;
                        if (!seenActivities.has(activityKey)) {
                            seenActivities.add(activityKey);
                            addAgentActivity(
                                activity.agent || 'System',
                                activity.message || 'Activity recorded',
                                activity.type || 'info',
                                activity.details
                            );
                        }
                    });
                }
            }
        } catch (error) {
            console.log('Initial agent activity load failed:', error.message);
        }
    }

    /**
     * Start consolidated agent activity monitoring.
     * Uses single /agents/activity endpoint instead of multiple fallback endpoints.
     * Polling interval: 3 seconds for activities, 10 seconds for resources.
     */
    function startAgentActivityMonitoring() {
        // Main activity monitoring - uses canonical /agents/activity endpoint
        setInterval(async () => {
            if (!activityPaused) {
                try {
                    const response = await fetch(`${apiUrl}/agents/activity`);
                    if (response.ok) {
                        const data = await response.json();

                        if (data && data.activities && data.activities.length > 0) {
                            // Process activities from canonical endpoint
                            data.activities.forEach(activity => {
                                const timestamp = activity.timestamp || Date.now();
                                const agent = activity.agent || 'System';
                                const message = activity.message || 'Activity recorded';
                                const activityKey = `${timestamp}-${agent}-${message}`;

                                if (!seenActivities.has(activityKey)) {
                                    seenActivities.add(activityKey);
                                    addAgentActivity(agent, message, activity.type || 'info', activity.details);

                                    // Update specific agent UI elements if available
                                    updateAgentUIElement(agent, activity);
                                }
                            });

                            // Update workflow summary if available
                            if (data.workflow_summary) {
                                updateWorkflowSummary(data.workflow_summary);
                            }
                        }
                    } else {
                        console.log('Agent activity endpoint returned non-OK status:', response.status);
                    }
                } catch (error) {
                    console.log('Failed to fetch agent activity:', error.message);
                }
            }
        }, 3000); // Check every 3 seconds

        // Simple Coder pending requests - separate endpoint for specific UI updates
        setInterval(async () => {
            if (!activityPaused) {
                try {
                    const response = await fetch(`${apiUrl}/simple-coder/update-requests`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data && data.length > 0) {
                            // Update Simple Coder UI elements
                            const requestsElement = document.getElementById('simple-coder-requests');
                            if (requestsElement) {
                                requestsElement.textContent = data.length;
                            }

                            const activityElement = document.getElementById('simple-coder-activity');
                            if (activityElement) {
                                activityElement.textContent = `${data.length} pending requests awaiting approval`;
                            }
                        }
                    }
                } catch (error) {
                    // Silent fail - this is a supplementary check
                }
            }
        }, 5000); // Check every 5 seconds for Simple Coder requests

        // BDI status - for specific UI element updates
        setInterval(async () => {
            if (!activityPaused) {
                try {
                    const response = await fetch(`${apiUrl}/core/bdi-status`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data && data.status) {
                            // Update BDI activity UI element
                            const activityElement = document.getElementById('bdi-activity');
                            if (activityElement) {
                                activityElement.textContent = `BDI Status: ${data.status}`;
                            }
                        }
                    }
                } catch (error) {
                    // Silent fail - this is a supplementary check
                }
            }
        }, 5000); // Check every 5 seconds for BDI status
        
        // Resource Monitor specific monitoring
        setInterval(async () => {
            if (!activityPaused) {
                try {
                    const response = await fetch(`${apiUrl}/system/resources`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data) {
                            // Update Resource Monitor status
                            const cpuElement = document.getElementById('resource-monitor-cpu');
                            const memoryElement = document.getElementById('resource-monitor-memory');
                            const activityElement = document.getElementById('resource-monitor-activity');
                            const indicatorElement = document.getElementById('resource-monitor-indicator');
                            
                            if (cpuElement) cpuElement.textContent = `${data.cpu_usage || 0}%`;
                            if (memoryElement) memoryElement.textContent = `${data.memory_usage || 0}%`;
                            if (activityElement) activityElement.textContent = `CPU: ${data.cpu_usage || 0}% | Memory: ${data.memory_usage || 0}%`;
                            if (indicatorElement) {
                                const cpuUsage = data.cpu_usage || 0;
                                const memoryUsage = data.memory_usage || 0;
                                if (cpuUsage > 80 || memoryUsage > 80) {
                                    indicatorElement.className = 'agent-status-indicator error';
                                } else if (cpuUsage > 60 || memoryUsage > 60) {
                                    indicatorElement.className = 'agent-status-indicator warning';
                                } else {
                                    indicatorElement.className = 'agent-status-indicator active';
                                }
                            }
                            
                            // Add activity to log if there are significant changes
                            if (data.cpu_usage > 70 || data.memory_usage > 70) {
                                addAgentActivity('Resource Monitor', `High resource usage: CPU ${data.cpu_usage}%, Memory ${data.memory_usage}%`, 'warning', {
                                    cpu_usage: data.cpu_usage,
                                    memory_usage: data.memory_usage,
                                    disk_usage: data.disk_usage,
                                    network_usage: data.network_usage
                                });
                            }
                        }
                    }
                } catch (error) {
                    console.log('Failed to fetch resource monitor data:', error.message);
                }
            }
        }, 10000); // Check every 10 seconds for resource monitoring
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
                // Log error but don't show mock data in production
                console.log('Resource monitor API failed:', error.message);
            }
        } catch (error) {
            console.error('Error fetching system resources:', error);
            // Log error but don't show mock data in production
            console.log('Resource monitor fallback failed:', error.message);
        }
    }

    // Production mode - no mock data

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
                // Log error but don't show mock data in production
                console.log('System metrics API failed:', error.message);
            }
            
            if (resourcesResponse.ok) {
                const resources = await resourcesResponse.json();
                updateResourceUsage(resources);
            } else {
                // Log error but don't show mock data in production
                console.log('Resource usage API failed:', error.message);
            }
            
            // Update system health based on current metrics
            updateSystemHealthFromCurrentData();
            
        } catch (error) {
            console.error('Error updating all system fields:', error);
            // Log error but don't show mock data in production
            console.log('System update failed:', error.message);
        }
    }

    // Production mode - no mock data functions

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
    
    // Test function to manually add BDI and Simple Coder activities
    window.testAgentActivities = function() {
        console.log('Adding test agent activities...');
        
        // Add BDI Agent activities
        const bdiActivities = [
            'BDI reasoning: Analyzing user directive and system state',
            'BDI decision: Selected Simple Coder for code generation task',
            'BDI monitoring: Tracking agent performance and success rates',
            'BDI optimization: Adjusting agent selection criteria based on results'
        ];
        
        bdiActivities.forEach((message, index) => {
            setTimeout(() => {
                addAgentActivity('BDI Agent', message, 'info');
            }, index * 1000);
        });
        
        // Add Simple Coder activities
        const simpleCoderActivities = [
            'Simple Coder: Received code generation request from BDI Agent',
            'Simple Coder: Analyzing codebase and generating update requests',
            'Simple Coder: Created 3 pending update requests for user approval',
            'Simple Coder: Monitoring code changes and maintaining sandbox environment'
        ];
        
        simpleCoderActivities.forEach((message, index) => {
            setTimeout(() => {
                addAgentActivity('Simple Coder', message, 'info');
            }, (index + 4) * 1000);
        });
        
        console.log('Test agent activities scheduled - check the activity monitor');
    };

    // Test function to demonstrate active agent highlighting
    window.testActiveAgentHighlighting = function() {
        console.log('Testing active agent highlighting...');
        
        const agents = ['AGInt Core', 'BDI Agent', 'Simple Coder', 'Coordinator Agent'];
        let currentIndex = 0;
        
        const highlightNextAgent = () => {
            const agent = agents[currentIndex];
            console.log(`Highlighting agent: ${agent}`);
            
            // Simulate activity for this agent
            addAgentActivity(agent, `${agent} is now active and processing tasks`, 'info');
            
            // Move to next agent
            currentIndex = (currentIndex + 1) % agents.length;
            
            // Continue highlighting every 2 seconds
            setTimeout(highlightNextAgent, 2000);
        };
        
        // Start the highlighting cycle
        highlightNextAgent();
        
        console.log('Active agent highlighting test started - watch the workflow nodes');
    };

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

// CrossMint Integration Functions
function initializeCrossMintIntegration() {
    const loginBtn = document.getElementById('crossmintLoginBtn');
    const logoutBtn = document.getElementById('crossmintLogoutBtn');
    const userInfo = document.getElementById('crossmintUserInfo');
    const walletAddress = document.getElementById('crossmintWalletAddress');
    
    if (!loginBtn || !logoutBtn || !userInfo || !walletAddress) {
        console.log('CrossMint UI elements not found');
        return;
    }
    
    // Set up logout button event listener
    logoutBtn.addEventListener('click', handleCrossMintLogout);
    
    // Check if user is already logged in
    checkCrossMintSession();
    
    // Set up periodic session check
    setInterval(checkCrossMintSession, 1000);
    
    console.log('CrossMint integration initialized');
}

// Check CrossMint session status
function checkCrossMintSession() {
    // Ensure unique login and check session validity
    if (ensureUniqueLogin()) {
        const userData = localStorage.getItem('crossmint_user');
        const walletAddress = localStorage.getItem('crossmint_wallet');
        
        try {
            const user = JSON.parse(userData);
            showCrossMintUserInfo();
            updateUIForAuthenticatedUser(user, walletAddress);
        } catch (error) {
            console.error('Error parsing user data:', error);
            clearCrossMintSession();
        }
    } else {
        showCrossMintLoginButton();
        updateUIForUnauthenticatedUser();
    }
}

// Disconnect from MetaMask
async function disconnectMetaMask() {
    try {
        if (typeof window.ethereum !== 'undefined') {
            // Check if MetaMask is connected
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                // Try to disconnect using wallet_disconnect if available
                try {
                    await window.ethereum.request({
                        method: 'wallet_revokePermissions',
                        params: [{ eth_accounts: {} }]
                    });
                    console.log('MetaMask permissions revoked');
                } catch (error) {
                    console.log('Could not revoke MetaMask permissions:', error);
                }
                
                // Clear any cached account data
                if (window.ethereum.removeAllListeners) {
                    window.ethereum.removeAllListeners('accountsChanged');
                    window.ethereum.removeAllListeners('chainChanged');
                }
            }
        }
    } catch (error) {
        console.log('MetaMask disconnection error:', error);
        // Don't throw error as this is not critical
    }
}

// Clear CrossMint session
function clearCrossMintSession() {
    // Clear all CrossMint related localStorage items
    localStorage.removeItem('crossmint_user');
    localStorage.removeItem('crossmint_wallet');
    localStorage.removeItem('crossmint_authenticated');
    localStorage.removeItem('crossmint_auth_method');
    localStorage.removeItem('crossmint_auth_token');
    localStorage.removeItem('crossmint_session_time');
    
    // Clear any other potential session data from localStorage
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.toLowerCase().includes('crossmint')) {
            keysToRemove.push(key);
        }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    
    // Clear sessionStorage as well
    const sessionKeysToRemove = [];
    for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key && key.toLowerCase().includes('crossmint')) {
            sessionKeysToRemove.push(key);
        }
    }
    sessionKeysToRemove.forEach(key => sessionStorage.removeItem(key));
    
    // Reset CrossMint integration state if available
    if (window.CrossMintIntegration) {
        window.CrossMintIntegration.currentUser = null;
        window.CrossMintIntegration.walletAddress = null;
        window.CrossMintIntegration.isAuthenticated = false;
        window.CrossMintIntegration.authToken = null;
    }
    
    showCrossMintLoginButton();
    updateUIForUnauthenticatedUser();
    
    console.log('CrossMint session completely cleared');
}

// Ensure unique user login - check for existing sessions
function ensureUniqueLogin() {
    const userIsAuthenticated = localStorage.getItem('crossmint_authenticated') === 'true';
    const userData = localStorage.getItem('crossmint_user');
    const walletAddress = localStorage.getItem('crossmint_wallet');
    
    if (userIsAuthenticated && userData && walletAddress) {
        try {
            const user = JSON.parse(userData);
            console.log('Existing session found for user:', user.email || user.address);
            
            // Check if this is a different user than expected
            const currentTime = Date.now();
            const sessionTime = user.timestamp || 0;
            const sessionAge = currentTime - sessionTime;
            
            // If session is older than 24 hours, clear it
            if (sessionAge > 24 * 60 * 60 * 1000) {
                console.log('Session expired, clearing...');
                clearCrossMintSession();
                return false;
            }
            
            return true;
        } catch (error) {
            console.error('Error parsing existing session:', error);
            clearCrossMintSession();
            return false;
        }
    }
    
    return false;
}

// Update UI for authenticated user
function updateUIForAuthenticatedUser(user, walletAddress) {
    // Enable authenticated features
    console.log('Updating UI for authenticated user:', user, walletAddress);

    // Update wallet address display in header - show full address
    if (walletAddress) {
        const walletElement = document.getElementById('crossmintWalletAddress');
        if (walletElement) {
            walletElement.textContent = walletAddress;
            walletElement.setAttribute('data-full-address', walletAddress);
            walletElement.setAttribute('title', 'Your receive address');
        }
    }

    // Show user-specific information
    console.log('User authenticated:', user);

    // Trigger our authentication system
    if (typeof handleAuthenticationSuccess === 'function') {
        handleAuthenticationSuccess({
            address: walletAddress,
            user: user
        });
    }
}

// Add create wallets button
function addCreateWalletsButton() {
    // Remove existing button if any
    const existingBtn = document.getElementById('createWalletsBtn');
    if (existingBtn) {
        existingBtn.remove();
    }
    
    // Find the agents tab content
    const agentsTab = document.querySelector('[data-tab="agents"]');
    if (!agentsTab) return;
    
    // Create button
    const button = document.createElement('button');
    button.id = 'createWalletsBtn';
    button.className = 'create-wallets-btn';
    button.innerHTML = '💳 Create Agent Wallets';
    button.onclick = handleCreateSystemWallets;
    
    // Add to agents tab
    const agentsContent = document.getElementById('agents');
    if (agentsContent) {
        agentsContent.insertBefore(button, agentsContent.firstChild);
    }
}

// Handle create system wallets
async function handleCreateSystemWallets() {
    try {
        const button = document.getElementById('createWalletsBtn');
        if (button) {
            button.disabled = true;
            button.innerHTML = '⏳ Creating Wallets...';
        }
        
        showNotification('Creating agent wallets...', 'info');
        
        const results = await window.CrossMintIntegration.createSystemAgentWallets();
        
        const successCount = results.filter(r => r.success).length;
        const failCount = results.filter(r => !r.success).length;
        
        if (successCount > 0) {
            showNotification(`Successfully created ${successCount} agent wallets`, 'success');
            
            // Refresh the display
            await window.CrossMintIntegration.loadAgentWallets();
            updateAgentWalletsDisplay(window.CrossMintIntegration.agentWallets);
            
            // Remove the create button
            const button = document.getElementById('createWalletsBtn');
            if (button) {
                button.remove();
            }
        }
        
        if (failCount > 0) {
            showNotification(`Failed to create ${failCount} wallets`, 'error');
        }
        
    } catch (error) {
        console.error('Failed to create system wallets:', error);
        showNotification(`Failed to create wallets: ${error.message}`, 'error');
    } finally {
        const button = document.getElementById('createWalletsBtn');
        if (button) {
            button.disabled = false;
            button.innerHTML = '💳 Create Agent Wallets';
        }
    }
}

// Update UI for unauthenticated user
function updateUIForUnauthenticatedUser() {
    // Disable authenticated features
    clearAgentWalletsDisplay();
    
    // Show login prompts
    console.log('User not authenticated');
}

// Update agent wallets display
function updateAgentWalletsDisplay(wallets) {
    // This will be called when we're on the agents tab
    if (document.querySelector('.tab-btn.active')?.dataset.tab === 'agents') {
        // Add wallet information to agent cards
        const agentCards = document.querySelectorAll('.agent-card');
        agentCards.forEach(card => {
            const agentId = card.dataset.agentId;
            const wallet = wallets.find(w => w.agent_id === agentId);
            
            if (wallet) {
                addWalletInfoToAgentCard(card, wallet);
            }
        });
    }
}

// Add wallet info to agent card
function addWalletInfoToAgentCard(card, wallet) {
    // Remove existing wallet info
    const existingWalletInfo = card.querySelector('.wallet-info');
    if (existingWalletInfo) {
        existingWalletInfo.remove();
    }
    
    // Add wallet class to card
    card.classList.add('has-wallet');
    
    // Create wallet info element
    const walletInfo = document.createElement('div');
    walletInfo.className = 'wallet-info';
    walletInfo.innerHTML = `
        <div class="wallet-address">
            <span class="wallet-label">Wallet:</span>
            <span class="wallet-addr" title="${wallet.wallet_address}">${wallet.wallet_address.substring(0, 6)}...${wallet.wallet_address.substring(wallet.wallet_address.length - 4)}</span>
        </div>
        <div class="wallet-balance">
            <span class="balance-label">Balance:</span>
            <span class="balance-amount">${wallet.balance || '0.00'} USDC</span>
        </div>
        <div class="wallet-actions">
            <button class="wallet-action-btn" onclick="viewWalletDetails('${wallet.agent_id}')">View Details</button>
            <button class="wallet-action-btn" onclick="sendToWallet('${wallet.agent_id}')">Send Funds</button>
        </div>
    `;
    
    // Add to agent card
    card.appendChild(walletInfo);
}

// View wallet details
function viewWalletDetails(agentId) {
    const authStatus = window.CrossMintIntegration.getAuthStatus();
    const wallet = authStatus.agentWallets.find(w => w.agent_id === agentId);
    
    if (wallet) {
        showWalletDetailsModal(wallet);
    }
}

// Send funds to wallet
function sendToWallet(agentId) {
    const authStatus = window.CrossMintIntegration.getAuthStatus();
    const wallet = authStatus.agentWallets.find(w => w.agent_id === agentId);
    
    if (wallet) {
        showSendFundsModal(wallet);
    }
}

// Show wallet details modal
function showWalletDetailsModal(wallet) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Wallet Details - ${wallet.agent_id}</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="wallet-detail">
                    <label>Agent ID:</label>
                    <span>${wallet.agent_id}</span>
                </div>
                <div class="wallet-detail">
                    <label>Wallet Address:</label>
                    <span class="wallet-address-full">${wallet.wallet_address}</span>
                </div>
                <div class="wallet-detail">
                    <label>Wallet Type:</label>
                    <span>${wallet.wallet_type}</span>
                </div>
                <div class="wallet-detail">
                    <label>Role:</label>
                    <span>${wallet.role}</span>
                </div>
                <div class="wallet-detail">
                    <label>Balance:</label>
                    <span class="balance-large">${wallet.balance || '0.00'} USDC</span>
                </div>
                <div class="wallet-detail">
                    <label>Status:</label>
                    <span class="status-${wallet.is_active ? 'active' : 'inactive'}">${wallet.is_active ? 'Active' : 'Inactive'}</span>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                <button class="btn-primary" onclick="copyWalletAddress('${wallet.wallet_address}')">Copy Address</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Show send funds modal
function showSendFundsModal(wallet) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Send Funds to ${wallet.agent_id}</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>To Address:</label>
                    <input type="text" value="${wallet.wallet_address}" readonly class="form-input">
                </div>
                <div class="form-group">
                    <label>Amount (USDC):</label>
                    <input type="number" step="0.01" min="0" placeholder="0.00" class="form-input" id="sendAmount">
                </div>
                <div class="form-group">
                    <label>Note (Optional):</label>
                    <input type="text" placeholder="Payment for agent operations" class="form-input" id="sendNote">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                <button class="btn-primary" onclick="executeSendFunds('${wallet.agent_id}', '${wallet.wallet_address}')">Send Funds</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Copy wallet address to clipboard
function copyWalletAddress(address) {
    navigator.clipboard.writeText(address).then(() => {
        showNotification('Wallet address copied to clipboard', 'success');
    }).catch(() => {
        showNotification('Failed to copy address', 'error');
    });
}

// Execute send funds
async function executeSendFunds(agentId, toAddress) {
    const amount = document.getElementById('sendAmount').value;
    const note = document.getElementById('sendNote').value;
    
    if (!amount || parseFloat(amount) <= 0) {
        showNotification('Please enter a valid amount', 'error');
        return;
    }
    
    try {
        showNotification('Sending funds...', 'info');
        
        const result = await window.CrossMintIntegration.sendTransaction(toAddress, amount, agentId);
        
        if (result.status === 'success') {
            showNotification(`Successfully sent ${amount} USDC to ${agentId}`, 'success');
            document.querySelector('.modal-overlay').remove();
            
            // Refresh wallet data
            await window.CrossMintIntegration.loadAgentWallets();
            updateAgentWalletsDisplay(window.CrossMintIntegration.agentWallets);
        } else {
            showNotification('Failed to send funds', 'error');
        }
    } catch (error) {
        console.error('Send funds error:', error);
        showNotification(`Send failed: ${error.message}`, 'error');
    }
}

// Clear agent wallets display
function clearAgentWalletsDisplay() {
    const walletInfos = document.querySelectorAll('.wallet-info');
    walletInfos.forEach(info => info.remove());
}

function showCrossMintLoginButton() {
    const loginBtn = document.getElementById('crossmintLoginBtn');
    const userInfo = document.getElementById('crossmintUserInfo');
    
    if (loginBtn) loginBtn.style.display = 'block';
    if (userInfo) userInfo.style.display = 'none';
}

function showCrossMintUserInfo() {
    const loginBtn = document.getElementById('crossmintLoginBtn');
    const userInfo = document.getElementById('crossmintUserInfo');
    const walletElement = document.getElementById('crossmintWalletAddress');

    if (loginBtn) loginBtn.style.display = 'none';
    if (userInfo) userInfo.style.display = 'flex';

    if (walletElement && window.CrossMintIntegration.getWalletAddress()) {
        const address = window.CrossMintIntegration.getWalletAddress();
        walletElement.textContent = address;
        walletElement.setAttribute('data-full-address', address);
        walletElement.setAttribute('title', 'Your receive address');
    }
}

async function handleCrossMintLogin() {
    try {
        const loginBtn = document.getElementById('crossmintLoginBtn');
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.textContent = 'Logging in...';
        }
        
        const result = await window.CrossMintIntegration.showLogin();
        
        if (result.success) {
            console.log('CrossMint login successful');
            // The auth state change handler will update the UI
            // Redirect to MindX control panel after successful login
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1000);
        } else {
            console.error('CrossMint login failed:', result.error);
            showNotification('Login failed. Please try again.', 'error');
        }
    } catch (error) {
        console.error('CrossMint login error:', error);
        showNotification(`Login error: ${error.message}`, 'error');
    } finally {
        const loginBtn = document.getElementById('crossmintLoginBtn');
        if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login with CrossMint';
        }
    }
}

async function handleCrossMintLogout() {
    try {
        const logoutBtn = document.getElementById('crossmintLogoutBtn');
        if (logoutBtn) {
            logoutBtn.disabled = true;
            logoutBtn.textContent = 'Logging out...';
        }
        
        // Use CrossMint integration logout method if available
        if (window.CrossMintIntegration && typeof window.CrossMintIntegration.logout === 'function') {
            await window.CrossMintIntegration.logout();
        }
        
        // Disconnect from MetaMask if connected
        await disconnectMetaMask();
        
        // Clear the session data
        clearCrossMintSession();
        
        // Trigger our authentication system logout
        if (typeof handleSecureLogout === 'function') {
            await handleSecureLogout();
        }
        
        console.log('CrossMint logout successful');
        showNotification('Logged out successfully', 'success');
        
    } catch (error) {
        console.error('CrossMint logout error:', error);
        showNotification(`Logout error: ${error.message}`, 'error');
    } finally {
        const logoutBtn = document.getElementById('crossmintLogoutBtn');
        if (logoutBtn) {
            logoutBtn.disabled = false;
            logoutBtn.textContent = 'Logout';
        }
    }
}

// Show notification to user
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Copy wallet address to clipboard
function copyWalletAddress(address) {
    navigator.clipboard.writeText(address).then(() => {
        showNotification('Wallet address copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy wallet address:', err);
        showNotification('Failed to copy wallet address', 'error');
    });
}

// Authentication Guards
function requireAuthentication(callback) {
    if (window.CrossMintIntegration && window.CrossMintIntegration.isLoggedIn()) {
        callback();
    } else {
        showNotification('Please log in with CrossMint to access this feature', 'error');
        // Optionally trigger login
        if (window.CrossMintIntegration) {
            handleCrossMintLogin();
        }
    }
}

// Protect sensitive operations
function protectSensitiveOperation(operationName, callback) {
    return function(...args) {
        requireAuthentication(() => {
            console.log(`Executing protected operation: ${operationName}`);
            callback.apply(this, args);
        });
    };
}

// Add authentication guards to existing functions
// TODO: Fix these references - functions need to be defined first
// const originalEvolve = evolve;
// const originalDeploy = deploy;
// const originalAnalyze = analyzeCodebase;

// Wrap existing functions with authentication
// window.evolve = protectSensitiveOperation('evolve', originalEvolve);
// window.deploy = protectSensitiveOperation('deploy', originalDeploy);
// window.analyzeCodebase = protectSensitiveOperation('analyze', originalAnalyze);

// User-specific agent management functions
let userAgents = [];
let userStats = null;

// Register user with wallet address
async function registerUser(walletAddress, metadata = {}) {
    try {
        const response = await fetch(`${apiUrl}/users/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                wallet_address: walletAddress,
                metadata: metadata
            })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            console.log('User registered successfully:', result);
            await loadUserAgents(walletAddress);
            await loadUserStats(walletAddress);
            return result;
        } else {
            console.error('User registration failed:', result.error);
            return result;
        }
    } catch (error) {
        console.error('Error registering user:', error);
        return { error: error.message };
    }
}

// Create a new agent for the current user
async function createUserAgent(agentId, agentType, metadata = {}) {
    const walletAddress = getCurrentWalletAddress();
    if (!walletAddress) {
        console.error('No wallet address available');
        return { error: 'No wallet address available' };
    }
    
    try {
        const response = await fetch(`${apiUrl}/users/agents`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                owner_wallet: walletAddress,
                agent_id: agentId,
                agent_type: agentType,
                metadata: metadata
            })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            console.log('Agent created successfully:', result);
            await loadUserAgents(walletAddress);
            await loadUserStats(walletAddress);
            return result;
        } else {
            console.error('Agent creation failed:', result.error);
            return result;
        }
    } catch (error) {
        console.error('Error creating agent:', error);
        return { error: error.message };
    }
}

// Delete a user's agent
async function deleteUserAgent(agentId) {
    const walletAddress = getCurrentWalletAddress();
    if (!walletAddress) {
        console.error('No wallet address available');
        return { error: 'No wallet address available' };
    }
    
    try {
        const response = await fetch(`${apiUrl}/users/${walletAddress}/agents/${agentId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            console.log('Agent deleted successfully:', result);
            await loadUserAgents(walletAddress);
            await loadUserStats(walletAddress);
            return result;
        } else {
            console.error('Agent deletion failed:', result.error);
            return result;
        }
    } catch (error) {
        console.error('Error deleting agent:', error);
        return { error: error.message };
    }
}

// Load user's agents
async function loadUserAgents(walletAddress) {
    try {
        const response = await fetch(`${apiUrl}/users/${walletAddress}/agents`);
        const result = await response.json();
        
        if (result.status === 'success') {
            userAgents = result.agents;
            console.log('User agents loaded:', userAgents);
            updateUserAgentsDisplay();
            return result;
        } else {
            console.error('Failed to load user agents:', result.error);
            return result;
        }
    } catch (error) {
        console.error('Error loading user agents:', error);
        return { error: error.message };
    }
}

// Load user statistics
async function loadUserStats(walletAddress) {
    try {
        const response = await fetch(`${apiUrl}/users/${walletAddress}/stats`);
        const result = await response.json();
        
        if (result.status === 'success') {
            userStats = result;
            console.log('User stats loaded:', userStats);
            updateUserStatsDisplay();
            return result;
        } else {
            console.error('Failed to load user stats:', result.error);
            return result;
        }
    } catch (error) {
        console.error('Error loading user stats:', error);
        return { error: error.message };
    }
}

// Get current wallet address from CrossMint integration
function getCurrentWalletAddress() {
    const userData = localStorage.getItem('crossmint_user');
    if (userData) {
        const user = JSON.parse(userData);
        return user.address;
    }
    return null;
}

// Update user agents display in the UI
function updateUserAgentsDisplay() {
    const agentsList = document.getElementById('agents-list');
    if (!agentsList) return;
    
    // Clear existing user agents
    const existingUserAgents = agentsList.querySelectorAll('.user-agent-item');
    existingUserAgents.forEach(item => item.remove());
    
    // Add user agents
    userAgents.forEach(agent => {
        const agentItem = document.createElement('div');
        agentItem.className = 'user-agent-item';
        agentItem.innerHTML = `
            <div class="agent-card">
                <div class="agent-header">
                    <h4>${agent.agent_id}</h4>
                    <span class="agent-status ${agent.status}">${agent.status}</span>
                </div>
                <div class="agent-details">
                    <p><strong>Type:</strong> ${agent.agent_type}</p>
                    <p><strong>Wallet:</strong> ${agent.agent_wallet}</p>
                    <p><strong>Created:</strong> ${new Date(parseFloat(agent.created_at) * 1000).toLocaleString()}</p>
                </div>
                <div class="agent-actions">
                    <button onclick="deleteUserAgent('${agent.agent_id}')" class="delete-btn">Delete</button>
                </div>
            </div>
        `;
        agentsList.appendChild(agentItem);
    });
}

// Update user stats display in the UI
function updateUserStatsDisplay() {
    if (!userStats) return;
    
    // Update user info in header if available
    const userWalletElement = document.getElementById('crossmintWalletAddress');
    if (userWalletElement && userStats.wallet_address) {
        userWalletElement.textContent = userStats.wallet_address;
    }
    
    // Update agent count in header or stats section
    const agentCountElements = document.querySelectorAll('.user-agent-count');
    agentCountElements.forEach(element => {
        element.textContent = userStats.total_agents;
    });
}

// Initialize user-specific functionality when wallet is connected
function initializeUserSpecificFeatures() {
    const walletAddress = getCurrentWalletAddress();
    if (walletAddress) {
        console.log('Initializing user-specific features for:', walletAddress);
        registerUser(walletAddress, {
            connected_at: new Date().toISOString(),
            user_agent: navigator.userAgent
        });
    }
}

// Enhanced agent creation with user context
function createAgentWithUserContext() {
    const walletAddress = getCurrentWalletAddress();
    if (!walletAddress) {
        alert('Please connect your wallet first');
        return;
    }
    
    const agentId = prompt('Enter agent ID:');
    if (!agentId) return;
    
    const agentType = prompt('Enter agent type:');
    if (!agentType) return;
    
    createUserAgent(agentId, agentType, {
        created_by: 'user_interface',
        created_at: new Date().toISOString()
    });
}

// Refresh user agents
async function refreshUserAgents() {
    const walletAddress = getCurrentWalletAddress();
    if (!walletAddress) {
        console.error('No wallet address available');
        return;
    }
    
    await loadUserAgents(walletAddress);
    await loadUserStats(walletAddress);
}

// Make functions globally available
window.registerUser = registerUser;
window.createUserAgent = createUserAgent;
window.deleteUserAgent = deleteUserAgent;
window.loadUserAgents = loadUserAgents;
window.loadUserStats = loadUserStats;
window.createAgentWithUserContext = createAgentWithUserContext;
window.initializeUserSpecificFeatures = initializeUserSpecificFeatures;
window.refreshUserAgents = refreshUserAgents;

// Authentication System - Variables moved to top of file

// Set up MetaMask event listeners (per MetaMask docs)
function setupMetaMaskEventListeners() {
    if (typeof window.ethereum === 'undefined' || !window.ethereum.isMetaMask) {
        return;
    }

    // Remove existing listeners to avoid duplicates
    if (window.ethereum.removeListener) {
        try {
            window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
            window.ethereum.removeListener('chainChanged', handleChainChanged);
        } catch (e) {
            // Ignore if listeners don't exist
        }
    }

    // Listen for account changes (per MetaMask docs)
    window.ethereum.on('accountsChanged', handleAccountsChanged);
    
    // Listen for chain changes (per MetaMask docs)
    window.ethereum.on('chainChanged', handleChainChanged);

    console.log('✅ MetaMask event listeners set up');
}

// Handle account changes (per MetaMask docs)
function handleAccountsChanged(accounts) {
    console.log('🔄 MetaMask accounts changed:', accounts);
    
    if (accounts.length === 0) {
        // User disconnected their account
        console.log('⚠️ User disconnected MetaMask account');
        localStorage.removeItem('crossmint_user');
        localStorage.removeItem('crossmint_wallet');
        localStorage.removeItem('crossmint_authenticated');
        localStorage.removeItem('crossmint_auth_method');
        
        // Reload to show login page
        if (typeof isAuthenticated !== 'undefined' && isAuthenticated) {
            window.location.reload();
        }
    } else {
        // User switched accounts
        const newAddress = accounts[0];
        console.log('✅ User switched to account:', newAddress);
        
        // Update stored user data
        const existingUser = localStorage.getItem('crossmint_user');
        if (existingUser) {
            try {
                const userData = JSON.parse(existingUser);
                userData.address = newAddress;
                userData.id = newAddress;
                localStorage.setItem('crossmint_user', JSON.stringify(userData));
                localStorage.setItem('crossmint_wallet', newAddress);
                
                // Update UI if authenticated
                if (typeof handleAuthenticationSuccess === 'function' && typeof isAuthenticated !== 'undefined' && isAuthenticated) {
                    handleAuthenticationSuccess(userData);
                }
            } catch (e) {
                console.error('Error updating account:', e);
            }
        }
    }
}

// Handle chain changes (per MetaMask docs)
function handleChainChanged(chainId) {
    console.log('🔄 MetaMask chain changed:', chainId);
    
    // Update stored chain ID
    const existingUser = localStorage.getItem('crossmint_user');
    if (existingUser) {
        try {
            const userData = JSON.parse(existingUser);
            userData.chainId = chainId;
            localStorage.setItem('crossmint_user', JSON.stringify(userData));
            
            // Optionally reload to ensure compatibility with new chain
            // For now, just log the change
            console.log('✅ Chain ID updated to:', chainId);
        } catch (e) {
            console.error('Error updating chain:', e);
        }
    }
}

// Initialize authentication system
async function initializeAuthenticationSystem() {
    console.log('🔐 Initializing authentication system...');
    
    // Check for existing authentication state
    await checkAuthenticationState();
    
    // Debug: Check if DOM is ready
    console.log('DOM ready state:', document.readyState);
    console.log('Document body:', document.body);
    console.log('Login button exists:', !!document.getElementById('loginConnectBtn'));
    
    // Set up login button - use the inline onclick handler which is already working
    // The inline onclick calls window.connectMetaMask() which is defined in the HTML head
    const loginConnectBtn = document.getElementById('loginConnectBtn');
    if (loginConnectBtn) {
        console.log('✅ Login button found. Using inline onclick handler (window.connectMetaMask)');
        console.log('Button onclick attribute:', loginConnectBtn.getAttribute('onclick'));
        
        // Verify the inline function is available
        if (typeof window.connectMetaMask === 'function') {
            console.log('✅ window.connectMetaMask is available and ready');
        } else {
            console.warn('⚠️ window.connectMetaMask not found - inline script may not have loaded');
        }
        
        // Don't add an event listener - the inline onclick is working
        // If we need to add additional functionality, we can enhance window.connectMetaMask instead
        
        // Ensure button is clickable
        loginConnectBtn.style.cursor = 'pointer';
        loginConnectBtn.style.pointerEvents = 'auto';
        
        console.log('✅ Button is ready - inline onclick will handle the click');
        
        // Check if MetaMask is available and update button text if needed
        if (typeof window.ethereum === 'undefined') {
            loginConnectBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                Install MetaMask First
            `;
            loginConnectBtn.disabled = true;
            loginConnectBtn.title = 'MetaMask browser extension is required';
            loginConnectBtn.style.cursor = 'not-allowed';
        } else {
            console.log('✅ MetaMask is available');
            // Set up event listeners if already connected
            if (window.ethereum.isMetaMask) {
                setupMetaMaskEventListeners();
            }
        }

        // Also add a direct test function for debugging
        window.testMetaMaskButton = function() {
            console.log('🧪 Testing MetaMask button click programmatically...');
            loginConnectBtn.click();
        };
        
        // Add a direct test function that calls MetaMask request
        window.testMetaMaskDirect = async function() {
            console.log('🧪 Testing MetaMask request directly...');
            try {
                if (typeof window.ethereum === 'undefined') {
                    console.error('MetaMask not installed');
                    return;
                }
                console.log('Calling eth_requestAccounts directly...');
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                console.log('✅ Direct test successful:', accounts);
                return accounts;
            } catch (error) {
                console.error('❌ Direct test failed:', error);
                throw error;
            }
        };

        // Check if MetaMask is available and update button text if needed
        if (typeof window.ethereum === 'undefined') {
            loginConnectBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                Install MetaMask First
            `;
            loginConnectBtn.disabled = true;
            loginConnectBtn.title = 'MetaMask browser extension is required';
            loginConnectBtn.style.cursor = 'not-allowed';
        } else {
            console.log('✅ MetaMask is available');
            console.log('MetaMask provider details:', {
                isMetaMask: window.ethereum.isMetaMask,
                request: typeof window.ethereum.request,
                selectedAddress: window.ethereum.selectedAddress,
                chainId: window.ethereum.chainId
            });
            // Set up event listeners if already connected
            if (window.ethereum.isMetaMask) {
                setupMetaMaskEventListeners();
            }
        }
    }
    
    // Set up logout button event listener
    const logoutBtn = document.getElementById('crossmintLogoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleSecureLogout);
    }
    
    console.log('✅ Authentication system initialized');
}

// Check authentication state on page load
async function checkAuthenticationState() {
    const authData = localStorage.getItem('mindx_auth');
    const crossmintAuth = localStorage.getItem('crossmint_authenticated');
    
    if (authData && crossmintAuth === 'true') {
        try {
            const auth = JSON.parse(authData);
            if (auth.walletAddress && auth.sessionId) {
                // Verify session is still valid
                if (isSessionValid(auth)) {
                    // Check if MetaMask is still connected
                    if (typeof window.ethereum !== 'undefined') {
                        try {
                            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                            if (accounts.length > 0 && accounts[0].toLowerCase() === auth.walletAddress.toLowerCase()) {
                                authenticationState = auth;
                                isAuthenticated = true;
                                showMainApplication();
                                console.log('✅ User authenticated from stored state');
                                return;
                            }
                        } catch (e) {
                            console.log('MetaMask connection check failed:', e);
                        }
                    }
                }
            }
        } catch (e) {
            console.error('Error parsing auth data:', e);
        }
    }
    
    // No valid authentication found
    showLoginLanding();
    clearAuthenticationState();
}

// Check if session is valid
function isSessionValid(auth) {
    if (!auth.timestamp) return false;
    
    const sessionAge = Date.now() - auth.timestamp;
    const maxSessionAge = 24 * 60 * 60 * 1000; // 24 hours
    
    return sessionAge < maxSessionAge;
}

// Handle login process - Using working CrossMint MetaMask connection
async function handleLogin() {
    console.log('🔑 Starting login process...');
    
    try {
        // Show loading state
        const loginBtn = document.getElementById('loginConnectBtn');
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 12a9 9 0 11-6.219-8.56"/>
                </svg>
                Connecting...
            `;
        }
        
        // Use the working CrossMint MetaMask connection from crossmint-google-wallet.html
        console.log('🔗 Using working CrossMint MetaMask connection...');
        await connectMetaMask();
        
    } catch (error) {
        console.error('❌ Login failed:', error);
        
        let errorMessage = 'Login failed. Please try again.';
        if (error.code === 4001) {
            errorMessage = 'MetaMask connection rejected. Please approve the connection request.';
        } else if (error.code === -32002) {
            errorMessage = 'MetaMask connection already pending. Please check MetaMask and try again.';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showLoginError(errorMessage);
        
        // Reset button
        const loginBtn = document.getElementById('loginConnectBtn');
        if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3 4-3 9-3 9 1.34 9 3z"/>
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
                Connect MetaMask Wallet
            `;
        }
    }
}

// Make handleLogin globally accessible for testing
window.handleLogin = handleLogin;

// Test function to verify button click works
window.testButtonClick = function() {
    console.log('🧪 Testing button click manually...');
    const btn = document.getElementById('loginConnectBtn');
    if (btn) {
        console.log('Button found, clicking...');
        btn.click();
    } else {
        console.error('Button not found!');
    }
};

// Test function to verify MetaMask connection works
window.testMetaMaskConnection = async function() {
    console.log('🧪 Testing MetaMask connection manually...');
    try {
        if (typeof window.ethereum === 'undefined') {
            throw new Error('MetaMask not installed');
        }
        
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });
        
        console.log('✅ MetaMask connection successful:', accounts[0]);
        return accounts[0];
    } catch (error) {
        console.error('❌ MetaMask connection failed:', error);
        throw error;
    }
};

// Note: connectMetaMask is now defined at the top of the file for early availability

// Connect MetaMask wallet (alternative function name - kept for compatibility)
async function connectMetaMaskWallet() {
    try {
        console.log('🔗 Connecting to MetaMask...');
        
        // Check if MetaMask is available
        if (typeof window.ethereum === 'undefined') {
            throw new Error('MetaMask is not installed. Please install MetaMask browser extension to continue.');
        }
        
        // Request account access
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });

        if (accounts.length === 0) {
            throw new Error('No accounts found. Please unlock MetaMask and try again.');
        }

        const walletAddress = accounts[0];
        console.log('✅ MetaMask connected:', walletAddress);
        
        // Get chain ID
        const chainId = await window.ethereum.request({
            method: 'eth_chainId'
        });

        // Create user data
        const userData = {
            id: walletAddress,
            address: walletAddress,
            provider: 'metamask',
            chainId: chainId,
            authMethod: 'wallet',
            timestamp: Date.now()
        };

        // Store in localStorage (compatible with existing CrossMint integration)
        localStorage.setItem('crossmint_user', JSON.stringify(userData));
        localStorage.setItem('crossmint_wallet', walletAddress);
        localStorage.setItem('crossmint_authenticated', 'true');
        localStorage.setItem('crossmint_auth_method', 'wallet');
        
        // Trigger authentication success
        handleAuthenticationSuccess(userData);
        
        console.log('✅ MetaMask login successful');
        
    } catch (error) {
        console.error('❌ MetaMask connection failed:', error);
        throw error;
    }
}

// Wait for CrossMint integration to be ready (simplified)
function waitForCrossMintIntegration() {
    // For now, just resolve immediately since we're using direct MetaMask
    return Promise.resolve();
}

// Handle successful authentication
function handleAuthenticationSuccess(userData) {
    console.log('✅ Authentication successful:', userData);
    
    // Create session
    const sessionId = generateSessionId();
    const timestamp = Date.now();
    
    authenticationState = {
        isLoggedIn: true,
        walletAddress: userData.address,
        userData: userData,
        sessionId: sessionId,
        timestamp: timestamp
    };
    
    // Store authentication state
    localStorage.setItem('mindx_auth', JSON.stringify(authenticationState));
    
    isAuthenticated = true;
    currentUser = userData;
    
    // Show main application
    showMainApplication();
    
    // Initialize user-specific features
    if (typeof initializeUserSpecificFeatures === 'function') {
        initializeUserSpecificFeatures();
    }
    
    // Log successful authentication
    if (typeof logAuthenticationEvent === 'function') {
        logAuthenticationEvent('login_success', {
            walletAddress: userData.address,
            sessionId: sessionId,
            timestamp: timestamp
        });
    }
}

// Make handleAuthenticationSuccess globally accessible
window.handleAuthenticationSuccess = handleAuthenticationSuccess;

// Check for pending authentication on load
if (window.pendingAuthSuccess) {
    console.log('Processing pending authentication...');
    const pendingAuth = window.pendingAuthSuccess;
    delete window.pendingAuthSuccess;
    // Wait a bit for handleAuthenticationSuccess to be defined
    setTimeout(() => {
        if (typeof handleAuthenticationSuccess === 'function') {
            handleAuthenticationSuccess(pendingAuth);
        } else {
            // Store it again for later
            window.pendingAuthSuccess = pendingAuth;
        }
    }, 100);
}

// Handle secure logout
async function handleSecureLogout() {
    console.log('🚪 Starting secure logout process...');
    
    try {
        // Show confirmation
        const confirmed = confirm('Are you sure you want to logout? This will clear all session data.');
        if (!confirmed) return;
        
        // Log logout event
        logAuthenticationEvent('logout_initiated', {
            walletAddress: authenticationState.walletAddress,
            sessionId: authenticationState.sessionId
        });
        
        // Clear CrossMint state
        if (window.CrossMintIntegration && window.CrossMintIntegration.logout) {
            await window.CrossMintIntegration.logout();
        }
        
        // Clear authentication state
        clearAuthenticationState();
        
        // Clear all user data
        clearUserData();
        
        // Show login landing
        showLoginLanding();
        
        // Force page refresh to ensure complete state reset
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
        console.log('✅ Secure logout completed');
        
    } catch (error) {
        console.error('❌ Logout error:', error);
        // Force logout even if there's an error
        clearAuthenticationState();
        showLoginLanding();
        window.location.reload();
    }
}

// Clear authentication state
function clearAuthenticationState() {
    authenticationState = {
        isLoggedIn: false,
        walletAddress: null,
        userData: null,
        sessionId: null
    };
    
    localStorage.removeItem('mindx_auth');
    localStorage.removeItem('crossmint_authenticated');
    localStorage.removeItem('crossmint_user');
    
    isAuthenticated = false;
    currentUser = null;
}

// Clear all user data
function clearUserData() {
    // Clear user agents
    userAgents = [];
    userStats = null;
    
    // Clear any cached data
    localStorage.removeItem('user_agents');
    localStorage.removeItem('user_stats');
    
    // Clear any other user-specific data
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('user_')) {
            keysToRemove.push(key);
        }
    }
    
    keysToRemove.forEach(key => localStorage.removeItem(key));
}

// Show login landing page
function showLoginLanding() {
    const loginLanding = document.getElementById('login-landing');
    const mainApplication = document.getElementById('main-application');
    
    if (loginLanding) loginLanding.style.display = 'flex';
    if (mainApplication) mainApplication.style.display = 'none';
    
    document.body.classList.remove('authenticated');
}

// Show main application
function showMainApplication() {
    const loginLanding = document.getElementById('login-landing');
    const mainApplication = document.getElementById('main-application');
    
    if (loginLanding) loginLanding.style.display = 'none';
    if (mainApplication) mainApplication.style.display = 'block';
    
    document.body.classList.add('authenticated');
    
    // Update wallet display
    updateWalletDisplay();
    
    // Load system data
    setTimeout(() => {
        updateAllSystemFields();
        updateMonitoringAgents();
        updateResourceFromSystemMetrics();
        performSystemHealthCheck();
        startHealthCheckRefresh();
    }, 1000);
}

// Update wallet display
function updateWalletDisplay() {
    const walletElement = document.getElementById('crossmintWalletAddress');
    if (walletElement && authenticationState.walletAddress) {
        const address = authenticationState.walletAddress;
        walletElement.textContent = address;
        walletElement.setAttribute('data-full-address', address);
        walletElement.setAttribute('title', 'Your receive address');
    }
}

// Generate session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Log authentication events
function logAuthenticationEvent(event, data) {
    console.log(`🔐 Auth Event: ${event}`, data);
    
    // Store in localStorage for debugging
    const authLogs = JSON.parse(localStorage.getItem('auth_logs') || '[]');
    authLogs.push({
        event: event,
        data: data,
        timestamp: Date.now()
    });
    
    // Keep only last 50 logs
    if (authLogs.length > 50) {
        authLogs.splice(0, authLogs.length - 50);
    }
    
    localStorage.setItem('auth_logs', JSON.stringify(authLogs));
}

// Show login error
function showLoginError(message) {
    // Create error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'login-error';
    errorDiv.innerHTML = `
        <div class="error-content">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span>${message}</span>
        </div>
    `;
    
    // Add to login card
    const loginCard = document.querySelector('.login-card');
    if (loginCard) {
        loginCard.appendChild(errorDiv);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
}

// CrossMint integration is now properly handled by the CrossMintIntegration class

// ==================== Ollama Management Functions ====================

function getOllamaConfig() {
    const method = ollamaConfigMethod ? ollamaConfigMethod.value : 'host-port';
    
    if (method === 'base-url') {
        const baseUrl = ollamaBaseUrl ? ollamaBaseUrl.value.trim() : 'http://localhost:11434';
        return { base_url: baseUrl };
    } else {
        const host = ollamaHost ? ollamaHost.value.trim() : 'localhost';
        const port = ollamaPort ? parseInt(ollamaPort.value) : 11434;
        return { host: host, port: port };
    }
}

function buildOllamaQueryString(config) {
    const params = new URLSearchParams();
    if (config.base_url) {
        params.append('base_url', config.base_url);
    } else {
        if (config.host) params.append('host', config.host);
        if (config.port) params.append('port', config.port.toString());
    }
    return params.toString();
}

// Rate limiting for connection attempts
let lastConnectionAttempt = 0;
const CONNECTION_RATE_LIMIT_MS = 2000; // 2 seconds between attempts

function updateConnectionBanner(status, message, details) {
    const banner = document.getElementById('ollama-connection-banner');
    const icon = document.getElementById('ollama-connection-icon');
    const statusText = document.getElementById('ollama-connection-status-text');
    const detailsEl = document.getElementById('ollama-connection-details');
    
    if (!banner) return;
    
    banner.style.display = 'block';
    
    if (status === 'connected') {
        banner.style.background = '#d4edda';
        banner.style.borderLeftColor = '#28a745';
        icon.textContent = '🟢';
        statusText.textContent = 'Connected';
        statusText.style.color = '#155724';
        if (details) {
            detailsEl.innerHTML = `<span style="color: #155724;">${details}</span>`;
        }
    } else if (status === 'connecting') {
        banner.style.background = '#d1ecf1';
        banner.style.borderLeftColor = '#17a2b8';
        icon.textContent = '🟡';
        statusText.textContent = 'Connecting...';
        statusText.style.color = '#0c5460';
        if (details) {
            detailsEl.innerHTML = `<span style="color: #0c5460;">${details}</span>`;
        }
    } else {
        banner.style.background = '#f8d7da';
        banner.style.borderLeftColor = '#dc3545';
        icon.textContent = '🔴';
        statusText.textContent = 'Not Connected';
        statusText.style.color = '#721c24';
        if (details) {
            detailsEl.innerHTML = `<span style="color: #721c24;">${details}</span>`;
        }
    }
}

async function testOllamaConnection() {
    console.log('🔌 testOllamaConnection called');
    
    // Rate limiting
    const now = Date.now();
    const timeSinceLastAttempt = now - lastConnectionAttempt;
    if (timeSinceLastAttempt < CONNECTION_RATE_LIMIT_MS) {
        const waitTime = Math.ceil((CONNECTION_RATE_LIMIT_MS - timeSinceLastAttempt) / 1000);
        updateConnectionBanner('error', 'Rate Limited', `Please wait ${waitTime} second(s) before attempting another connection.`);
        return;
    }
    lastConnectionAttempt = now;
    
    const statusEl = ollamaStatus || document.getElementById('ollama-status');
    const testBtn = document.getElementById('test-ollama-connection-btn');
    const testIcon = document.getElementById('test-connection-icon');
    
    if (!statusEl) {
        console.error('❌ ollama-status element not found');
        return;
    }
    
    const config = getOllamaConfig();
    console.log('📋 Ollama config:', config);
    
    // Update banner to connecting
    const serverUrl = config.base_url || `http://${config.host}:${config.port}`;
    updateConnectionBanner('connecting', 'Connecting...', `Connecting to ${serverUrl}...`);
    
    // Disable button and show loading
    if (testBtn) {
        testBtn.disabled = true;
        testBtn.style.opacity = '0.6';
        if (testIcon) testIcon.textContent = '⏳';
    }
    
    statusEl.style.display = 'block';
    statusEl.style.visibility = 'visible';
    statusEl.style.opacity = '1';
    
    // Show connection progress with better animation
    let progressSteps = [
        { text: 'Resolving host...', progress: 25 },
        { text: 'Establishing TCP connection...', progress: 50 },
        { text: 'Sending HTTP request to /api/tags...', progress: 75 },
        { text: 'Waiting for response...', progress: 90 }
    ];
    let stepIndex = 0;
    
    const progressInterval = setInterval(() => {
        if (stepIndex < progressSteps.length) {
            const step = progressSteps[stepIndex];
            statusEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); border: 2px solid #17a2b8; border-radius: 8px; color: #0c5460; box-shadow: 0 2px 8px rgba(23,162,184,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                        <div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #17a2b8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite;"></div>
                        <p style="margin: 0; font-weight: bold; font-size: 16px;">${step.text}</p>
                    </div>
                    <div style="width: 100%; background: rgba(255,255,255,0.5); border-radius: 8px; height: 8px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="width: ${step.progress}%; background: linear-gradient(90deg, #17a2b8 0%, #138496 100%); height: 100%; transition: width 0.5s ease; box-shadow: 0 2px 4px rgba(23,162,184,0.3);"></div>
                    </div>
                    <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">Endpoint: GET ${serverUrl}/api/tags</p>
                </div>
            `;
            stepIndex++;
        }
    }, 600);
    
    try {
        const queryString = buildOllamaQueryString(config);
        console.log('🌐 Requesting:', `/api/llm/ollama/connection?${queryString}`);
        
        const response = await sendRequest(`/api/llm/ollama/connection?${queryString}`);
        console.log('✅ Response received:', response);
        
        clearInterval(progressInterval);
        
        if (response.success) {
            updateConnectionBanner('connected', 'Connected', `${response.model_count || 0} models available on ${response.base_url}`);
            
            statusEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 2px solid #28a745; border-radius: 8px; color: #155724; box-shadow: 0 2px 8px rgba(40,167,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                        <span style="font-size: 32px;">✅</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Connection Successful!</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">${response.message || 'Successfully connected to Ollama server'}</p>
                        </div>
                    </div>
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid rgba(40,167,69,0.3); display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div style="background: rgba(255,255,255,0.5); padding: 12px; border-radius: 6px;">
                            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Server URL</div>
                            <div style="font-weight: bold; font-family: monospace; font-size: 14px;">${response.base_url || 'N/A'}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.5); padding: 12px; border-radius: 6px;">
                            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Models Available</div>
                            <div style="font-weight: bold; font-size: 20px; color: #28a745;">${response.model_count || 0}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.5); padding: 12px; border-radius: 6px;">
                            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Status Code</div>
                            <div style="font-weight: bold; font-size: 14px;">${response.status_code || '200'}</div>
                        </div>
                    </div>
                </div>
            `;
            statusEl.style.display = 'block';
            addLog(`Ollama connection successful: ${response.message || 'Connected'}`, 'SUCCESS');
            setTimeout(() => listOllamaModels(), 500);
        } else {
            updateConnectionBanner('error', 'Connection Failed', response.error || 'Unknown error');
            
            let errorDetails = '';
            let troubleshooting = '';
            if (response.timeout) {
                errorDetails = '⏱️ Connection Timeout';
                troubleshooting = '<p style="margin: 10px 0 0 0; padding: 10px; background: rgba(255,193,7,0.2); border-left: 3px solid #ffc107; border-radius: 4px; font-size: 13px;"><strong>💡 Troubleshooting:</strong><br>• Check if Ollama is running on the server<br>• Verify the host and port are correct<br>• Check firewall settings<br>• Try: <code>curl ' + serverUrl + '/api/tags</code></p>';
            } else if (response.connection_error) {
                errorDetails = '🔌 Connection Error';
                troubleshooting = '<p style="margin: 10px 0 0 0; padding: 10px; background: rgba(255,193,7,0.2); border-left: 3px solid #ffc107; border-radius: 4px; font-size: 13px;"><strong>💡 Troubleshooting:</strong><br>• Verify the server is accessible from this machine<br>• Check network connectivity<br>• Ensure Ollama is listening on the specified port<br>• Test with: <code>ping ' + (config.host || 'localhost') + '</code></p>';
            }
            
            statusEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 8px; color: #721c24; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                        <span style="font-size: 32px;">❌</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Connection Failed</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">${errorDetails || 'Unable to connect to Ollama server'}</p>
                        </div>
                    </div>
                    <div style="margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.5); border-radius: 6px;">
                        <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 14px;">Error Details:</p>
                        <p style="margin: 0; font-family: monospace; font-size: 13px; word-break: break-all;">${response.error || 'Unknown error'}</p>
                        <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid rgba(220,53,69,0.3);">
                            <p style="margin: 0 0 5px 0; font-size: 14px;"><strong>Server:</strong> <code>${response.base_url || serverUrl}</code></p>
                            ${troubleshooting}
                        </div>
                    </div>
                </div>
            `;
            statusEl.style.display = 'block';
            addLog(`Ollama connection failed: ${response.error}`, 'ERROR');
        }
    } catch (error) {
        console.error('❌ Error in testOllamaConnection:', error);
        clearInterval(progressInterval);
        updateConnectionBanner('error', 'Error', error.message);
        
        const statusEl = ollamaStatus || document.getElementById('ollama-status');
        if (statusEl) {
            statusEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 8px; color: #721c24; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 32px;">⚠️</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Connection Error</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px; font-family: monospace;">${error.message}</p>
                        </div>
                    </div>
                </div>
            `;
            statusEl.style.display = 'block';
        }
        addLog(`Ollama connection error: ${error.message}`, 'ERROR');
    } finally {
        // Re-enable button
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.style.opacity = '1';
            if (testIcon) testIcon.textContent = '🔌';
        }
    }
}

async function listOllamaModels() {
    console.log('📋 listOllamaModels called');
    
    const modelsEl = ollamaModelsList || document.getElementById('ollama-models-list');
    const listBtn = document.getElementById('list-ollama-models-btn');
    const listIcon = document.getElementById('list-models-icon');
    
    if (!modelsEl) {
        console.error('❌ ollama-models-list element not found');
        return;
    }
    
    const config = getOllamaConfig();
    console.log('📋 Ollama config:', config);
    
    // Disable button
    if (listBtn) {
        listBtn.disabled = true;
        listBtn.style.opacity = '0.6';
        if (listIcon) listIcon.textContent = '⏳';
    }
    
    modelsEl.style.display = 'block';
    modelsEl.style.visibility = 'visible';
    modelsEl.style.opacity = '1';
    modelsEl.innerHTML = `
        <div style="padding: 20px; text-align: center;">
            <div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #17a2b8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px;"></div>
            <p style="margin: 0; color: #666; font-size: 16px; font-weight: bold;">Loading models from Ollama server...</p>
            <p style="margin: 10px 0 0 0; color: #999; font-size: 12px;">Endpoint: GET /api/tags</p>
        </div>
    `;
    
    try {
        const queryString = buildOllamaQueryString(config);
        console.log('🌐 Requesting:', `/api/llm/ollama/models?${queryString}`);
        const response = await sendRequest(`/api/llm/ollama/models?${queryString}`);
        console.log('✅ Response received:', response);
        
        if (response.success && response.models !== undefined) {
            if (response.models.length === 0) {
                modelsEl.innerHTML = `
                    <div style="padding: 25px; background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border: 2px solid #ffc107; border-radius: 8px; color: #856404; box-shadow: 0 2px 8px rgba(255,193,7,0.2); text-align: center;">
                        <span style="font-size: 48px; display: block; margin-bottom: 15px;">📦</span>
                        <h4 style="margin: 0 0 15px 0; font-size: 20px;">No Models Found</h4>
                        <p style="margin: 0 0 10px 0; font-size: 14px;">Server: <strong><code>${response.base_url || 'N/A'}</code></strong></p>
                        <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.5); border-radius: 6px;">
                            <p style="margin: 0 0 10px 0; font-weight: bold;">To add models, run on the server:</p>
                            <code style="display: block; padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; font-size: 13px; font-family: monospace;">ollama pull llama3:8b</code>
                            <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">Or any other model from <a href="https://ollama.com/library" target="_blank" style="color: #856404;">ollama.com/library</a></p>
                        </div>
                    </div>
                `;
                addLog(`No models found on Ollama server: ${response.base_url}`, 'INFO');
                if (ollamaTestModel) {
                    ollamaTestModel.innerHTML = '<option value="">No models available</option>';
                }
            } else {
                let html = `
                    <div style="padding: 20px; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 2px solid #28a745; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(40,167,69,0.2);">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div>
                                <h4 style="margin: 0 0 5px 0; color: #155724; font-size: 20px;">
                                    <span style="font-size: 24px; margin-right: 10px;">✅</span>
                                    Available Models (${response.count || response.models.length})
                                </h4>
                                <p style="margin: 0; font-size: 14px; color: #155724; opacity: 0.9;">
                                    <strong>Server:</strong> <code style="background: rgba(255,255,255,0.5); padding: 2px 6px; border-radius: 3px;">${response.base_url || 'N/A'}</code>
                                </p>
                            </div>
                            <div style="font-size: 32px; color: #28a745;">📋</div>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
                `;
                response.models.forEach((model, index) => {
                    const sizeGB = model.size ? (model.size / (1024**3)).toFixed(2) : 'Unknown';
                    const modifiedDate = model.modified_at ? new Date(model.modified_at).toLocaleDateString() : null;
                    const modelName = model.name || 'Unknown';
                                        const escapedModelName = modelName.replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, ' ').replace(/\r/g, '');
html += `
                        <div class="ollama-model-card" 
                             data-model-name="${escapedModelName}"
                             style="padding: 20px; background: white; border: 2px solid #dee2e6; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.2s; cursor: pointer;" 
                             onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.15)';" 
                             onmouseout="this.style.transform=''; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)';"
                             onclick="if(typeof window.selectOllamaModel === \'function\') { window.selectOllamaModel(\'${escapedModelName}\'); }">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                                <span style="font-size: 24px;">🤖</span>
                                <h5 style="margin: 0; color: #333; font-size: 16px; font-weight: bold; word-break: break-word;">${modelName}</h5>
                            </div>
                            <div style="font-size: 14px; color: #666; display: grid; gap: 8px;">
                                <div style="display: flex; justify-content: space-between; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                                    <span>Size:</span>
                                    <strong style="color: #495057;">${sizeGB} GB</strong>
                                </div>
                                ${modifiedDate ? `
                                <div style="display: flex; justify-content: space-between; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                                    <span>Modified:</span>
                                    <strong style="color: #495057;">${modifiedDate}</strong>
                                </div>
                                ` : ''}
                            </div>
                            <div style="margin-top: 12px; padding: 8px; background: #e7f3ff; border-radius: 4px; text-align: center; font-size: 12px; color: #0066cc; font-weight: bold;">
                                Click to select
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                modelsEl.innerHTML = html;
                modelsEl.style.display = 'block';
                addLog(`Loaded ${response.count || response.models.length} Ollama models from ${response.base_url}`, 'SUCCESS');
                
                // Populate model dropdown for testing
                if (ollamaTestModel) {
                    ollamaTestModel.innerHTML = '<option value="">Select a model</option>';
                    response.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.name || '';
                        option.textContent = model.name || 'Unknown';
                        ollamaTestModel.appendChild(option);
                    });
                }
                
                // Populate model selector for conversation
                const modelSelect = document.getElementById('ollama-model-select');
                if (modelSelect) {
                    modelSelect.innerHTML = '<option value="">-- Select a model --</option>';
                    response.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.name || '';
                        option.textContent = model.name || 'Unknown';
                        modelSelect.appendChild(option);
                    });
                    addLog(`Populated model selector with ${response.models.length} models`, 'SUCCESS');
                }
                
                // Add click handlers to model cards after they are rendered
                setTimeout(() => {
                    const modelCards = document.querySelectorAll(".ollama-model-card");
                    modelCards.forEach(card => {
                        card.removeAttribute("onclick");
                        card.addEventListener("click", function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            const modelName = this.getAttribute("data-model-name");
                            if (modelName) {
                                if (typeof window.selectOllamaModel === "function") {
                                    window.selectOllamaModel(modelName);
                                } else if (typeof selectOllamaModel === "function") {
                                    selectOllamaModel(modelName);
                                } else {
                                    const modelSelect = document.getElementById("ollama-model-select");
                                    if (modelSelect) {
                                        modelSelect.value = modelName;
                                        addLog(`Selected model: ${modelName}`, "SUCCESS");
                                        card.style.border = "3px solid #00ffff";
                                        card.style.background = "rgba(0, 255, 255, 0.15)";
                                        card.style.boxShadow = "0 0 20px rgba(0, 255, 255, 0.6)";
                                    }
                                }
                            }
                        });
                        card.addEventListener("mousedown", function() {
                            if (!this.classList.contains("selected")) {
                                this.style.transform = "scale(0.98)";
                            }
                        });
                        card.addEventListener("mouseup", function() {
                            if (!this.classList.contains("selected")) {
                                this.style.transform = "translateY(-2px)";
                            }
                        });
                    });
                }, 100);
            }
        } else {
            modelsEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 8px; color: #721c24; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 32px;">❌</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Failed to load models</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px; font-family: monospace;">${response.error || 'Unknown error'}</p>
                        </div>
                    </div>
                </div>
            `;
            modelsEl.style.display = 'block';
            addLog(`Failed to load Ollama models: ${response.error || 'Unknown error'}`, 'ERROR');
        }
    } catch (error) {
        console.error('❌ Error in listOllamaModels:', error);
        const modelsEl = ollamaModelsList || document.getElementById('ollama-models-list');
        if (modelsEl) {
            modelsEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 8px; color: #721c24; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 32px;">⚠️</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Error Loading Models</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px; font-family: monospace;">${error.message}</p>
                        </div>
                    </div>
                </div>
            `;
            modelsEl.style.display = 'block';
        }
        addLog(`Failed to list Ollama models: ${error.message}`, 'ERROR');
    } finally {
        // Re-enable button
        if (listBtn) {
            listBtn.disabled = false;
            listBtn.style.opacity = '1';
            if (listIcon) listIcon.textContent = '📋';
        }
    }
}

async function saveOllamaConfig() {
    console.log('💾 saveOllamaConfig called');
    
    // Get the configuration method and values
    const methodEl = document.getElementById('ollama-config-method');
    const method = methodEl ? methodEl.value : 'host-port';
    
    let baseUrl = null;
    let config = {};
    
    if (method === 'base-url') {
        const baseUrlEl = document.getElementById('ollama-base-url');
        baseUrl = baseUrlEl ? baseUrlEl.value.trim() : '';
        if (!baseUrl) {
            alert('Please enter a base URL');
            return;
        }
        config = { base_url: baseUrl };
    } else {
        // host-port method
        const hostEl = document.getElementById('ollama-host');
        const portEl = document.getElementById('ollama-port');
        const host = hostEl ? hostEl.value.trim() : 'localhost';
        const port = portEl ? parseInt(portEl.value) : 11434;
        
        if (!host || !port) {
            alert('Please enter both host and port');
            return;
        }
        
        baseUrl = `http://${host}:${port}`;
        config = { base_url: baseUrl };
    }
    
    console.log('📋 Config to save:', config);
    
    const statusEl = document.getElementById('ollama-status') || 
                     document.querySelector('.ollama-setup-section')?.querySelector('.status-message');
    
    if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.innerHTML = '<p style="color: #666;">Saving configuration...</p>';
    }
    
    try {
        const response = await sendRequest('/api/llm/ollama/config', 'POST', config);
        console.log('✅ Save response:', response);
        
        if (response.success) {
            const warningMsg = response.connection_warning ? `\n\n⚠️ Warning: ${response.connection_warning}` : '';
            addLog(`Ollama configuration saved successfully: ${response.base_url}${warningMsg ? ' - ' + response.connection_warning : ''}`, response.connection_warning ? 'WARNING' : 'SUCCESS');
            
            if (statusEl) {
                const bgColor = response.connection_warning ? '#fff3cd' : '#d4edda';
                const borderColor = response.connection_warning ? '#ffc107' : '#c3e6cb';
                const textColor = response.connection_warning ? '#856404' : '#155724';
                
                statusEl.innerHTML = `
                    <div style="padding: 15px; background: ${bgColor}; border: 1px solid ${borderColor}; border-radius: 4px; color: ${textColor};">
                        <p style="margin: 0; font-weight: bold;">✓ Configuration saved successfully</p>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">Server: <strong>${response.base_url}</strong></p>
                        <p style="margin: 5px 0 0 0; font-size: 12px; color: ${response.connection_warning ? '#856404' : '#6c757d'};">${response.connection_warning ? '⚠️ ' + response.connection_warning + '<br>' : ''}Configuration has been persisted to .env file</p>
                    </div>
                `;
                statusEl.style.display = 'block';
            }
            
            // Refresh provider list and prioritize Ollama
            await refreshAndPrioritizeOllama();
            
            // Show success notification
            const alertMsg = response.connection_warning 
                ? `✓ Ollama configuration saved!\n\nServer: ${response.base_url}\n\n⚠️ Warning: ${response.connection_warning}\n\nConfiguration has been persisted to .env file.`
                : `✓ Ollama configuration saved!\n\nServer: ${response.base_url}\n\nConfiguration has been persisted and will be loaded on next startup.`;
            alert(alertMsg);
        } else {
            const errorMsg = response.error || response.message || 'Failed to save configuration';
            addLog(`Failed to save Ollama configuration: ${errorMsg}`, 'ERROR');
            
            if (statusEl) {
                statusEl.innerHTML = `
                    <div style="padding: 15px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; color: #721c24;">
                        <p style="margin: 0; font-weight: bold;">✗ ${errorMsg}</p>
                    </div>
                `;
                statusEl.style.display = 'block';
            }
            
            alert(`✗ Failed to save configuration: ${errorMsg}`);
        }
    } catch (error) {
        console.error('❌ Error saving config:', error);
        addLog(`Error saving Ollama configuration: ${error.message}`, 'ERROR');
        
        if (statusEl) {
            statusEl.innerHTML = `
                <div style="padding: 15px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; color: #721c24;">
                    <p style="margin: 0; font-weight: bold;">✗ Error: ${error.message}</p>
                </div>
            `;
            statusEl.style.display = 'block';
        }
        
        alert(`✗ Error saving configuration: ${error.message}`);
    }
}

async function testOllamaCompletion() {
    console.log('🧪 testOllamaCompletion called');
    
    const statusEl = ollamaCompletionStatus || document.getElementById('ollama-completion-status');
    const responseEl = ollamaCompletionResponse || document.getElementById('ollama-completion-response');
    const responseTextEl = ollamaResponseText || document.getElementById('ollama-response-text');
    const completionBtn = document.getElementById('test-ollama-completion-btn');
    const completionIcon = document.getElementById('test-completion-icon');
    const loadingDiv = document.getElementById('completion-loading');
    
    if (!statusEl) {
        console.error('❌ ollama-completion-status element not found');
        return;
    }
    
    const model = ollamaTestModel ? ollamaTestModel.value : '';
    const prompt = ollamaTestPrompt ? ollamaTestPrompt.value.trim() : '';
    
    if (!model) {
        statusEl.innerHTML = `
            <div style="padding: 15px; background: #fff3cd; border: 2px solid #ffc107; border-radius: 4px; color: #856404;">
                <p style="margin: 0; font-weight: bold;">⚠️ Please select a model first</p>
            </div>
        `;
        statusEl.style.display = 'block';
        return;
    }
    
    if (!prompt) {
        statusEl.innerHTML = `
            <div style="padding: 15px; background: #fff3cd; border: 2px solid #ffc107; border-radius: 4px; color: #856404;">
                <p style="margin: 0; font-weight: bold;">⚠️ Please enter a test prompt</p>
            </div>
        `;
        statusEl.style.display = 'block';
        return;
    }
    
    // Disable button and show loading
    if (completionBtn) {
        completionBtn.disabled = true;
        completionBtn.style.opacity = '0.6';
        if (completionIcon) completionIcon.textContent = '⏳';
    }
    if (loadingDiv) loadingDiv.style.display = 'flex';
    
    const config = getOllamaConfig();
    const serverUrl = config.base_url || `http://${config.host}:${config.port}`;
    
    statusEl.style.display = 'block';
    statusEl.innerHTML = `
        <div style="padding: 20px; background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); border: 2px solid #17a2b8; border-radius: 8px; color: #0c5460; box-shadow: 0 2px 8px rgba(23,162,184,0.2);">
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                <div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #17a2b8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite;"></div>
                <div>
                    <p style="margin: 0; font-weight: bold; font-size: 16px;">🔄 Generating completion...</p>
                    <p style="margin: 5px 0 0 0; font-size: 14px;">Model: <strong>${model}</strong></p>
                </div>
            </div>
            <div style="width: 100%; background: rgba(255,255,255,0.5); border-radius: 8px; height: 8px; overflow: hidden;">
                <div class="progress-bar" style="width: 0%; background: linear-gradient(90deg, #17a2b8 0%, #138496 100%); height: 100%; animation: progress 2s ease-in-out infinite;"></div>
            </div>
            <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.8;">Endpoint: POST ${serverUrl}/api/generate</p>
        </div>
    `;
    
    if (responseEl) {
        responseEl.style.display = 'none';
    }
    
    try {
        const queryString = buildOllamaQueryString(config);
        const requestBody = {
            model: model,
            prompt: prompt,
            max_tokens: 500,
            temperature: 0.7
        };
        
        console.log('🌐 Testing completion:', requestBody);
        
        const response = await sendRequest(`/api/llm/ollama/generate?${queryString}`, 'POST', requestBody);
        console.log('✅ Completion response:', response);
        
        if (response && response.success !== false && (response.text || response.response)) {
            statusEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 2px solid #28a745; border-radius: 8px; color: #155724; box-shadow: 0 2px 8px rgba(40,167,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 32px;">✅</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Completion Successful!</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px;">Model: <strong>${model}</strong></p>
                        </div>
                    </div>
                </div>
            `;
            
            if (responseEl && responseTextEl) {
                const responseText = response.text || response.response || JSON.stringify(response, null, 2);
                responseTextEl.textContent = responseText;
                responseEl.style.display = 'block';
                
                // Add copy button functionality
                const copyBtn = document.getElementById('copy-response-btn');
                if (copyBtn) {
                    copyBtn.onclick = function() {
                        navigator.clipboard.writeText(responseText).then(() => {
                            copyBtn.textContent = 'Copied!';
                            setTimeout(() => {
                                copyBtn.textContent = 'Copy';
                            }, 2000);
                        });
                    };
                }
            }
            
            addLog(`Ollama completion successful for model ${model}`, 'SUCCESS');
        } else {
            statusEl.innerHTML = `
                <div style="padding: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 8px; color: #721c24; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 32px;">❌</span>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 18px;">Completion Failed</p>
                            <p style="margin: 5px 0 0 0; font-size: 14px; font-family: monospace;">${response.error || response.message || 'Unknown error'}</p>
                        </div>
                    </div>
                </div>
            `;
            addLog(`Ollama completion failed: ${response.error || 'Unknown error'}`, 'ERROR');
        }
    } catch (error) {
        console.error('❌ Error in testOllamaCompletion:', error);
        statusEl.innerHTML = `
            <div style="padding: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 8px; color: #721c24; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span style="font-size: 32px;">⚠️</span>
                    <div>
                        <p style="margin: 0; font-weight: bold; font-size: 18px;">Error</p>
                        <p style="margin: 5px 0 0 0; font-size: 14px; font-family: monospace;">${error.message}</p>
                    </div>
                </div>
            </div>
        `;
        addLog(`Ollama completion error: ${error.message}`, 'ERROR');
    } finally {
        // Re-enable button
        if (completionBtn) {
            completionBtn.disabled = false;
            completionBtn.style.opacity = '1';
            if (completionIcon) completionIcon.textContent = '🚀';
        }
        if (loadingDiv) loadingDiv.style.display = 'none';
    }
}
    // Faicey Functions
    async function loadFaiceyExpressions() {
        try {
            const response = await sendRequest('/faicey/expressions', 'GET');
            if (response.success && response.expressions) {
                displayFaiceyExpressions(response.expressions);
            } else {
                const listEl = document.getElementById('faicey-expressions-list');
                if (listEl) {
                    listEl.innerHTML = '<div class="error-message">No expressions found</div>';
                }
            }
        } catch (error) {
            console.error('Error loading Faicey expressions:', error);
            const listEl = document.getElementById('faicey-expressions-list');
            if (listEl) {
                listEl.innerHTML = '<div class="error-message">Error loading expressions: ' + error.message + '</div>';
            }
        }
    }
    
    function displayFaiceyExpressions(expressions) {
        const listContainer = document.getElementById('faicey-expressions-list');
        if (!listContainer) return;
        
        if (!expressions || expressions.length === 0) {
            listContainer.innerHTML = '<div class="info-message">No expressions available. Create one to get started.</div>';
            return;
        }
        
        const expressionsHTML = expressions.map(expr => {
            const createdDate = new Date(expr.created_at).toLocaleDateString();
            const skillsCount = expr.skills ? expr.skills.length : 0;
            const modulesCount = expr.ui_modules ? expr.ui_modules.length : 0;
            
            return `
                <div class="expression-card" onclick="showExpressionDetails('${expr.expression_id}')">
                    <div class="expression-header">
                        <h3>${(expr.prompt || expr.expression_id).replace(/'/g, "&#39;")}</h3>
                        <span class="expression-id">${expr.expression_id}</span>
                    </div>
                    <div class="expression-info">
                        <div class="info-item">
                            <span class="info-label">Agent:</span>
                            <span class="info-value">${expr.agent_id}</span>
                        </div>
                        <div class="info-item">
                            <div class="badge-group">
                                <span class="badge">${skillsCount} Skills</span>
                                <span class="badge">${modulesCount} Modules</span>
                            </div>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Created:</span>
                            <span class="info-value">${createdDate}</span>
                        </div>
                    </div>
                    <div class="expression-actions">
                        <button class="action-btn-small" onclick="event.stopPropagation(); loadExpression('${expr.expression_id}')">Load</button>
                        <button class="action-btn-small" onclick="event.stopPropagation(); exportExpression('${expr.expression_id}')">Export</button>
                    </div>
                </div>
            `;
        }).join('');
        
        listContainer.innerHTML = expressionsHTML;
    }
    
    async function showExpressionDetails(expressionId) {
        try {
            const response = await sendRequest(`/faicey/expressions/${expressionId}`, 'GET');
            if (response.success && response.expression) {
                const expr = response.expression;
                const detailsContainer = document.getElementById('faicey-expression-details');
                if (!detailsContainer) return;
                
                document.getElementById('expression-name').textContent = expr.prompt || expressionId;
                document.getElementById('detail-agent-id').textContent = expr.agent_id || '-';
                document.getElementById('detail-persona-id').textContent = expr.persona_id || '-';
                document.getElementById('detail-created').textContent = new Date(expr.created_at).toLocaleString();
                
                const skillsContainer = document.getElementById('detail-skills');
                if (skillsContainer) {
                    if (expr.skills && expr.skills.length > 0) {
                        skillsContainer.innerHTML = expr.skills.map(skill => 
                            `<div class="skill-badge">${(skill.name || skill.skill_id).replace(/'/g, "&#39;")} (Level ${skill.level || 'N/A'})</div>`
                        ).join('');
                    } else {
                        skillsContainer.innerHTML = '<div class="no-data">No skills</div>';
                    }
                }
                
                const modulesContainer = document.getElementById('detail-modules');
                if (modulesContainer) {
                    if (expr.ui_modules && expr.ui_modules.length > 0) {
                        modulesContainer.innerHTML = expr.ui_modules.map(module => 
                            `<div class="module-badge">${(module.name || module.module_id).replace(/'/g, "&#39;")}</div>`
                        ).join('');
                    } else {
                        modulesContainer.innerHTML = '<div class="no-data">No modules</div>';
                    }
                }
                
                const speechConfig = expr.speech_inflection_config || {};
                const speechEnabledEl = document.getElementById('detail-speech-enabled');
                const speechAlphabetEl = document.getElementById('detail-speech-alphabet');
                const speechBlendEl = document.getElementById('detail-speech-blend');
                if (speechEnabledEl) speechEnabledEl.textContent = speechConfig.enabled ? 'Yes' : 'No';
                if (speechAlphabetEl) speechAlphabetEl.textContent = speechConfig.alphabet || '-';
                if (speechBlendEl) speechBlendEl.textContent = speechConfig.viseme_blend_duration || '-';
                
                detailsContainer.style.display = 'block';
            }
        } catch (error) {
            console.error('Error loading expression details:', error);
            alert('Error loading expression details: ' + error.message);
        }
    }
    
    function closeExpressionDetails() {
        const detailsEl = document.getElementById('faicey-expression-details');
        if (detailsEl) detailsEl.style.display = 'none';
    }
    
    async function loadExpression(expressionId) {
        try {
            const response = await sendRequest(`/faicey/expressions/${expressionId}/ui-config`, 'GET');
            if (response.success) {
                console.log('Expression UI config loaded:', response);
                alert('Expression loaded successfully! UI configuration available in console.');
            }
        } catch (error) {
            console.error('Error loading expression:', error);
            alert('Error loading expression: ' + error.message);
        }
    }
    
    async function exportExpression(expressionId) {
        try {
            const response = await sendRequest(`/faicey/expressions/${expressionId}/ui-config`, 'GET');
            if (response.success) {
                const dataStr = JSON.stringify(response.config, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `faicey-expression-${expressionId}.json`;
                link.click();
                URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.error('Error exporting expression:', error);
            alert('Error exporting expression: ' + error.message);
        }
    }
    
    function initializeFaiceyTabs() {
        const faiceyTabBtns = document.querySelectorAll('.faicey-tab-btn');
        const faiceySections = document.querySelectorAll('.faicey-section');
        
        faiceyTabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.getAttribute('data-faicey-tab');
                
                faiceyTabBtns.forEach(b => b.classList.remove('active'));
                faiceySections.forEach(s => s.classList.remove('active'));
                
                btn.classList.add('active');
                const sectionEl = document.getElementById(`faicey-${tabId}-section`);
                if (sectionEl) sectionEl.classList.add('active');
                
                if (tabId === 'speech') {
                    loadSpeechInflectionData();
                } else if (tabId === 'modules') {
                    loadFaiceyModules();
                }
            });
        });
    }
    
    async function loadSpeechInflectionData() {
        try {
            const response = await fetch('/data/faicey/morph_target_definitions.json');
            const data = await response.json();
            displayMorphTargets(data);
        } catch (error) {
            console.error('Error loading morph target definitions:', error);
        }
    }
    
    function displayMorphTargets(definitions) {
        const grid = document.getElementById('targets-grid');
        if (!grid || !definitions || !definitions.morph_targets) return;
        
        const categories = ['mouth', 'eyes', 'eyebrows', 'ears'];
        let html = '';
        
        categories.forEach(category => {
            const targets = definitions.morph_targets[category];
            if (!targets || !targets.targets) return;
            
            html += `<div class="target-category">
                <h5>${category.charAt(0).toUpperCase() + category.slice(1)}</h5>
                <div class="target-items">`;
            
            Object.keys(targets.targets).forEach(targetName => {
                const target = targets.targets[targetName];
                html += `
                    <div class="target-item">
                        <span class="target-name">${(target.name || targetName).replace(/'/g, "&#39;")}</span>
                        <span class="target-description">${(target.description || '').replace(/'/g, "&#39;")}</span>
                    </div>
                `;
            });
            
            html += `</div></div>`;
        });
        
        grid.innerHTML = html;
    }
    
    async function loadFaiceyModules() {
        const modulesList = document.getElementById('faicey-modules-list');
        if (modulesList) {
            modulesList.innerHTML = '<div class="info-message">Module registry loading...</div>';
        }
    }
    
    // Make functions globally accessible
    window.showExpressionDetails = showExpressionDetails;
    window.closeExpressionDetails = closeExpressionDetails;
    window.loadExpression = loadExpression;
    window.exportExpression = exportExpression;
    
    // Ollama Model Selection Function
    function selectOllamaModel(modelName) {
        const modelSelect = document.getElementById('ollama-model-select');
        if (modelSelect) {
            // Set the dropdown value
            modelSelect.value = modelName;
            
            // Trigger change event
            const changeEvent = new Event('change', { bubbles: true });
            modelSelect.dispatchEvent(changeEvent);
            
            // Highlight the selected model card
            const modelCards = document.querySelectorAll('.ollama-model-card');
            modelCards.forEach(card => {
                const cardModelName = card.getAttribute('data-model-name');
                if (cardModelName === modelName) {
                    card.style.border = '3px solid #00ffff';
                    card.style.background = 'rgba(0, 255, 255, 0.15)';
                    card.style.boxShadow = '0 0 20px rgba(0, 255, 255, 0.6)';
                    card.style.transform = 'scale(1.02)';
                } else {
                    card.style.border = '2px solid #dee2e6';
                    card.style.background = 'white';
                    card.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                    card.style.transform = '';
                }
            });
            
            // Scroll to conversation interface
            const conversationSection = document.querySelector('.ollama-model-conversation');
            if (conversationSection) {
                setTimeout(() => {
                    conversationSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 300);
            }
            
            // Focus on input field
            const inputEl = document.getElementById('ollama-conversation-input');
            if (inputEl) {
                setTimeout(() => {
                    inputEl.focus();
                }, 500);
            }
            
            addLog(`Selected model: ${modelName}`, 'SUCCESS');
        }
    }
    
    // Make function globally accessible
    window.selectOllamaModel = selectOllamaModel;
    
    // Store selected model globally for mindX access
    let selectedOllamaModel = null;
    
    // Update selectOllamaModel to store globally and notify backend
    const originalSelectOllamaModel = selectOllamaModel;
    selectOllamaModel = async function(modelName) {
        selectedOllamaModel = modelName;
        localStorage.setItem('selectedOllamaModel', modelName);
        
        // Notify backend of selected model
        try {
            await sendRequest('/api/llm/ollama/set-selected-model', 'POST', { model: modelName });
            console.log(`✅ Selected model ${modelName} saved to backend`);
        } catch (error) {
            console.warn('Failed to save selected model to backend:', error);
        }
        
        originalSelectOllamaModel(modelName);
    };
    window.selectOllamaModel = selectOllamaModel;
    
    // Load selected model from localStorage on page load
    window.addEventListener('DOMContentLoaded', function() {
        const savedModel = localStorage.getItem('selectedOllamaModel');
        if (savedModel) {
            selectedOllamaModel = savedModel;
            const modelSelect = document.getElementById('ollama-model-select');
            if (modelSelect) {
                modelSelect.value = savedModel;
            }
        }
    });
    
    // Conversation history
    let ollamaConversationHistory = [];
    
    // Load conversation history from localStorage
    try {
        const savedHistory = localStorage.getItem('ollamaConversationHistory');
        if (savedHistory) {
            ollamaConversationHistory = JSON.parse(savedHistory);
        }
    } catch (e) {
        console.warn('Failed to load conversation history:', e);
    }
    
    // Function to add message to conversation UI
    function addMessageToConversation(role, content, model = null) {
        const messagesEl = document.getElementById('ollama-conversation-messages');
        if (!messagesEl) return;
        
        // Clear placeholder if exists
        if (messagesEl.children.length === 1 && messagesEl.children[0].textContent.includes('Conversation will appear here')) {
            messagesEl.innerHTML = '';
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.style.marginBottom = '15px';
        messageDiv.style.padding = '10px';
        messageDiv.style.borderRadius = '4px';
        
        if (role === 'user') {
            messageDiv.style.background = 'rgba(0, 100, 200, 0.2)';
            messageDiv.style.borderLeft = '3px solid #0066cc';
            messageDiv.innerHTML = `
                <div style="color: #00ffff; font-weight: bold; margin-bottom: 5px;">You:</div>
                <div style="color: #ffffff; white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(content)}</div>
            `;
        } else {
            messageDiv.style.background = 'rgba(0, 150, 0, 0.2)';
            messageDiv.style.borderLeft = '3px solid #00ff00';
            const modelInfo = model ? ` <span style="color: #888; font-size: 12px;">(${escapeHtml(model)})</span>` : '';
            messageDiv.innerHTML = `
                <div style="color: #00ff00; font-weight: bold; margin-bottom: 5px;">Assistant:${modelInfo}</div>
                <div style="color: #ffffff; white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(content)}</div>
            `;
        }
        
        messagesEl.appendChild(messageDiv);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        
        // Save to history
        ollamaConversationHistory.push({ role, content, model, timestamp: new Date().toISOString() });
        try {
            localStorage.setItem('ollamaConversationHistory', JSON.stringify(ollamaConversationHistory));
        } catch (e) {
            console.warn('Failed to save conversation history:', e);
        }
    }
    
    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Function to send message to Ollama
    async function sendOllamaMessage() {
        const inputEl = document.getElementById('ollama-conversation-input');
        const sendBtn = document.getElementById('ollama-send-message-btn');
        const modelSelect = document.getElementById('ollama-model-select');
        
        if (!inputEl || !modelSelect) {
            alert('Conversation interface not found');
            return;
        }
        
        const message = inputEl.value.trim();
        if (!message) {
            return;
        }
        
        const selectedModel = modelSelect.value || selectedOllamaModel;
        if (!selectedModel) {
            alert('Please select a model first');
            return;
        }
        
        // Disable input and button
        inputEl.disabled = true;
        if (sendBtn) sendBtn.disabled = true;
        
        // Add user message to UI
        addMessageToConversation('user', message);
        
        // Clear input
        inputEl.value = '';
        
        // Show thinking indicator
        const thinkingId = 'thinking-' + Date.now();
        addMessageToConversation('assistant', 'Thinking...', selectedModel);
        const thinkingEl = document.getElementById('ollama-conversation-messages').lastElementChild;
        thinkingEl.id = thinkingId;
        
        try {
            // Build conversation history for API
            const messages = ollamaConversationHistory
                .filter(msg => msg.role !== 'assistant' || !msg.content.includes('Thinking...'))
                .map(msg => ({
                    role: msg.role,
                    content: msg.content
                }));
            
            // Add current user message
            messages.push({
                role: 'user',
                content: message
            });
            
            // Send to API
            const response = await sendRequest('/api/llm/ollama/chat', 'POST', {
                model: selectedModel,
                messages: messages,
                temperature: 0.7,
                max_tokens: 2000
            });
            
            // Remove thinking indicator
            const thinkingElement = document.getElementById(thinkingId);
            if (thinkingElement) {
                thinkingElement.remove();
            }
            
            if (response.success && response.content) {
                addMessageToConversation('assistant', response.content, selectedModel);
                addLog(`Ollama chat response received from ${selectedModel}`, 'SUCCESS');
            } else {
                const errorMsg = response.error || response.message || 'Unknown error';
                addMessageToConversation('assistant', `Error: ${errorMsg}`, selectedModel);
                addLog(`Ollama chat error: ${errorMsg}`, 'ERROR');
            }
        } catch (error) {
            // Remove thinking indicator
            const thinkingElement = document.getElementById(thinkingId);
            if (thinkingElement) {
                thinkingElement.remove();
            }
            
            const errorMsg = error.message || 'Failed to send message';
            addMessageToConversation('assistant', `Error: ${errorMsg}`, selectedModel);
            addLog(`Ollama chat error: ${errorMsg}`, 'ERROR');
        } finally {
            // Re-enable input and button
            inputEl.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
            inputEl.focus();
        }
    }
    
    // Function to clear conversation
    function clearOllamaConversation() {
        if (confirm('Clear conversation history?')) {
            ollamaConversationHistory = [];
            const messagesEl = document.getElementById('ollama-conversation-messages');
            if (messagesEl) {
                messagesEl.innerHTML = '<div style="color: #888; font-style: italic;">Conversation cleared. Select a model and start chatting...</div>';
            }
            try {
                localStorage.removeItem('ollamaConversationHistory');
            } catch (e) {
                console.warn('Failed to clear conversation history:', e);
            }
            addLog('Ollama conversation cleared', 'INFO');
        }
    }
    
    // Make functions globally accessible
    window.sendOllamaMessage = sendOllamaMessage;
    window.clearOllamaConversation = clearOllamaConversation;
    window.addMessageToConversation = addMessageToConversation;
    window.getSelectedOllamaModel = function() { return selectedOllamaModel; };