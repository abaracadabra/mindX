/**
 * Query Coordinator Tab Component
 * 
 * Dedicated tab for query coordinator interactions with Ollama integration.
 * Provides real-time query processing and Ollama conversation feedback.
 * Query results are displayed in draggable, resizable, semi-transparent windows.
 * 
 * @module QueryCoordinatorTab
 */

class QueryCoordinatorTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'query-coordinator',
            label: 'Query Coordinator',
            group: 'core',
            refreshInterval: 5000, // 5 seconds
            autoRefresh: true,
            ...config
        });

        this.ollamaMonitor = null;
        this.queryInProgress = false;
        this.queryHistory = [];
        this.queryResults = [];
        this.resultWindowIds = [];
        this.eventListenersAttached = false;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Initialize Ollama monitor for query feedback
        this.ollamaMonitor = new OllamaMonitor({
            containerId: 'query-ollama-monitor-container',
            endpoint: '/mindxagent/ollama',
            refreshInterval: 3000
        });

        console.log('✅ QueryCoordinatorTab initialized');
        return true;
    }

    /**
     * Activate the tab
     */
    async onActivate() {
        await super.onActivate();

        // Set up event listeners when tab is activated (DOM elements exist)
        this.setupEventListeners();

        // Load coordinator status
        await this.loadCoordinatorStatus();

        // Initialize Ollama monitor if container exists
        const monitorContainer = document.getElementById('query-ollama-monitor-container');
        if (monitorContainer && this.ollamaMonitor) {
            await this.ollamaMonitor.initialize();
            this.ollamaMonitor.startMonitoring();
        }

        this.registerComponent('ollamaMonitor', this.ollamaMonitor);

        // Set global reference for backlog actions
        window.queryCoordinatorTab = this;

        return true;
    }

    /**
     * Deactivate the tab
     */
    async onDeactivate() {
        // Stop Ollama monitoring
        if (this.ollamaMonitor) {
            this.ollamaMonitor.stopMonitoring();
        }

        await super.onDeactivate();
        return true;
    }

    /**
     * Refresh tab data
     */
    async refresh() {
        if (!this.isActive) return;
        await this.loadCoordinatorStatus();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Prevent duplicate listeners
        if (this.eventListenersAttached) return;

        // Query button
        const queryBtn = document.getElementById('query-tab-btn');
        if (queryBtn) {
            queryBtn.addEventListener('click', () => this.handleQuery());
        }

        // Analyze button
        const analyzeBtn = document.getElementById('query-analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this.handleAnalyze());
        }

        // Backlog button
        const backlogBtn = document.getElementById('query-backlog-btn');
        if (backlogBtn) {
            backlogBtn.addEventListener('click', () => this.loadBacklog());
        }

        // Clear results button
        const clearBtn = document.getElementById('query-clear-results-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearQueryResults());
        }

        // Enter key in query input - use keypress for better Enter detection
        const queryInput = document.getElementById('query-tab-input');
        if (queryInput) {
            // Remove any existing listeners first
            queryInput.removeEventListener('keydown', this.handleKeyDown);
            queryInput.removeEventListener('keypress', this.handleKeyPress);
            
            // Bind methods to preserve 'this' context
            this.handleKeyDown = (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleQuery();
                }
            };
            
            this.handleKeyPress = (e) => {
                if (e.key === 'Enter' || e.keyCode === 13) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleQuery();
                }
            };

            queryInput.addEventListener('keydown', this.handleKeyDown);
            queryInput.addEventListener('keypress', this.handleKeyPress);
            
            console.log('✅ Query input event listeners attached');
        }

        this.eventListenersAttached = true;
    }

    /**
     * Load coordinator status and API connections
     */
    async loadCoordinatorStatus() {
        try {
            const status = await this.apiRequest('/system/status');
            this.updateCoordinatorStatusDisplay(status);
            this.setData('coordinatorStatus', status);

            // Also load API provider status
            await this.loadAPIProviderStatus();
        } catch (error) {
            console.error('Failed to load coordinator status:', error);
        }
    }

    /**
     * Load API provider connection status
     */
    async loadAPIProviderStatus() {
        try {
            const providers = await this.apiRequest('/api/llm/providers');
            this.updateAPIProviderStatus(providers.providers || []);
        } catch (error) {
            console.error('Failed to load API provider status:', error);
        }
    }

    /**
     * Update API provider status display
     */
    updateAPIProviderStatus(providers) {
        const apiStatusEl = document.getElementById('query-api-provider-status');
        if (!apiStatusEl) return;

        const connectedProviders = providers.filter(p =>
            p.status === 'enabled' &&
            (p.api_key_set === true || p.base_url_set === true)
        );

        if (connectedProviders.length === 0) {
            apiStatusEl.innerHTML = '<div class="api-status-item offline">No API providers connected</div>';
            return;
        }

        apiStatusEl.innerHTML = connectedProviders.map(provider => `
            <div class="api-status-item online">
                <span class="provider-name">${provider.display_name || provider.name}</span>
                <span class="provider-type">${provider.provider_type || 'LLM'}</span>
            </div>
        `).join('');
    }

    /**
     * Handle query action - routes to coordinator agent with LLM inference
     */
    async handleQuery() {
        const queryInput = document.getElementById('query-tab-input');
        const query = queryInput?.value?.trim();

        if (!query) {
            this.showNotification('Please enter a query', 'warning');
            return;
        }

        // Prevent duplicate submissions
        if (this.queryInProgress) {
            console.log('Query already in progress, ignoring');
            return;
        }

        // Update UI state
        this.queryInProgress = true;
        this.updateQueryControlsState(true);

        // Add to history
        this.addToQueryHistory({
            query,
            timestamp: new Date().toISOString(),
            status: 'processing'
        });

        try {
            // Route to coordinator agent which uses LLM inference
            const result = await this.apiRequest('/coordinator/query', 'POST', { query });

            console.log('Coordinator LLM inference result:', result);

            // Extract API details if available (from coordinator's LLM handler)
            const apiDetails = result.api_details || result.metadata || {};
            const providerUsed = apiDetails.provider || apiDetails.model_provider || 'coordinator-llm';

            // Enhance result with API connection info
            const enhancedResult = {
                ...result,
                query_source: 'Coordinator Agent with LLM Inference',
                api_provider: providerUsed,
                inference_type: 'coordinator_llm',
                timestamp: new Date().toISOString()
            };

            // Update history entry
            this.updateLastHistoryEntry({ status: 'completed', result: enhancedResult });

            // Display result in draggable window with API info
            this.displayQueryResultInWindow(query, enhancedResult);

            // Also add to results list
            this.addToQueryResults(query, enhancedResult);

            this.showNotification(`Query processed via ${providerUsed}`, 'success');

            // Clear input after successful query
            if (queryInput) {
                queryInput.value = '';
            }

        } catch (error) {
            console.error('Coordinator LLM query error:', error);
            this.updateLastHistoryEntry({ status: 'failed', error: error.message });
            this.showNotification(`Query failed: ${error.message}`, 'error');
        } finally {
            this.queryInProgress = false;
            this.updateQueryControlsState(false);
        }
    }

    /**
     * Handle analyze action
     */
    async handleAnalyze() {
        const context = document.getElementById('query-analyze-context')?.value?.trim() || 'general';

        if (this.queryInProgress) return;

        this.queryInProgress = true;
        this.updateQueryControlsState(true);

        try {
            const result = await this.apiRequest('/coordinator/analyze', 'POST', { context });
            this.displayQueryResultInWindow(`System Analysis (${context})`, result);
            this.addToQueryResults(`System Analysis (${context})`, result);
            this.showNotification('Analysis completed', 'success');
        } catch (error) {
            console.error('Analysis error:', error);
            this.showNotification(`Analysis failed: ${error.message}`, 'error');
        } finally {
            this.queryInProgress = false;
            this.updateQueryControlsState(false);
        }
    }

    /**
     * Display query result in a draggable, resizable, semi-transparent window
     * @param {string} query - Original query
     * @param {Object} result - Query result
     */
    displayQueryResultInWindow(query, result) {
        // Check if window manager is available
        if (!window.windowManager) {
            console.warn('Window manager not available, falling back to inline display');
            this.addToQueryResults(query, result);
            return;
        }

        const timestamp = new Date().toLocaleString();
        const resultJson = JSON.stringify(result, null, 2);
        
        // Create formatted content for the window
        const content = `
            <div class="query-result-window-content">
                <div class="query-result-meta">
                    <div class="meta-item">
                        <span class="meta-label">Query:</span>
                        <span class="meta-value query-text">${this.escapeHtml(query)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Time:</span>
                        <span class="meta-value">${timestamp}</span>
                    </div>
                </div>
                <div class="query-result-body">
                    <div class="result-toolbar">
                        <button class="result-action-btn copy-btn" onclick="navigator.clipboard.writeText(\`${this.escapeForJs(resultJson)}\`).then(() => alert('Copied to clipboard!'))">
                            📋 Copy
                        </button>
                        <button class="result-action-btn expand-btn" onclick="this.closest('.query-result-window-content').querySelector('pre').classList.toggle('expanded')">
                            🔍 Toggle Expand
                        </button>
                    </div>
                    <pre class="result-json">${this.escapeHtml(resultJson)}</pre>
                </div>
            </div>
        `;

        // Calculate window position (cascade from previous windows)
        const windowCount = this.resultWindowIds.length;
        const baseX = 100 + (windowCount % 5) * 40;
        const baseY = 100 + (windowCount % 5) * 40;

        // Create the window using WindowManager
        const windowId = window.windowManager.createWindow({
            title: `Query Result: ${query.substring(0, 30)}${query.length > 30 ? '...' : ''}`,
            content: content,
            width: 600,
            height: 450,
            x: baseX,
            y: baseY,
            minWidth: 400,
            minHeight: 300,
            resizable: true,
            draggable: true,
            closable: true,
            maximizable: true,
            onClose: (id) => {
                // Remove from tracked windows
                const index = this.resultWindowIds.indexOf(id);
                if (index > -1) {
                    this.resultWindowIds.splice(index, 1);
                }
            }
        });

        // Track the window ID
        this.resultWindowIds.push(windowId);

        // Apply semi-transparent styling to the window
        this.applyTransparentWindowStyle(windowId);

        console.log(`✅ Query result displayed in window: ${windowId}`);
    }

    /**
     * Apply semi-transparent styling to a window
     * @param {string} windowId - Window ID
     */
    applyTransparentWindowStyle(windowId) {
        const windowEl = document.getElementById(windowId);
        if (windowEl) {
            windowEl.classList.add('query-result-window', 'semi-transparent');
        }
    }

    /**
     * Add to query results list (inline display)
     * @param {string} query - Original query
     * @param {Object} result - Query result
     */
    addToQueryResults(query, result) {
        const resultEntry = {
            query,
            result,
            timestamp: new Date().toISOString()
        };

        this.queryResults.unshift(resultEntry);
        if (this.queryResults.length > 10) {
            this.queryResults.pop();
        }

        this.updateQueryResultsDisplay();
    }

    /**
     * Load improvement backlog
     */
    async loadBacklog() {
        try {
            const backlog = await this.apiRequest('/coordinator/backlog');
            this.displayBacklog(backlog);
        } catch (error) {
            console.error('Failed to load backlog:', error);
            this.showNotification(`Failed to load backlog: ${error.message}`, 'error');
        }
    }

    /**
     * Update query controls state
     * @param {boolean} inProgress - Whether query is in progress
     */
    updateQueryControlsState(inProgress) {
        const queryBtn = document.getElementById('query-tab-btn');
        const analyzeBtn = document.getElementById('query-analyze-btn');
        const queryInput = document.getElementById('query-tab-input');

        if (queryBtn) {
            queryBtn.disabled = inProgress;
            queryBtn.textContent = inProgress ? 'Processing...' : 'Send Query';
        }

        if (analyzeBtn) {
            analyzeBtn.disabled = inProgress;
        }

        if (queryInput) {
            queryInput.disabled = inProgress;
        }
    }

    /**
     * Update coordinator status display
     * @param {Object} status - Status data
     */
    updateCoordinatorStatusDisplay(status) {
        const statusEl = document.getElementById('query-coordinator-status');
        const agentsEl = document.getElementById('query-registered-agents');
        const toolsEl = document.getElementById('query-registered-tools');
        const interactionsEl = document.getElementById('query-total-interactions');

        if (statusEl) {
            const isOnline = status.coordinator_online || status.status === 'online';
            statusEl.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
            statusEl.textContent = isOnline ? '🟢 Online' : '🔴 Offline';
        }

        if (agentsEl) {
            agentsEl.textContent = status.registered_agents || status.agents_count || '-';
        }

        if (toolsEl) {
            toolsEl.textContent = status.registered_tools || status.tools_count || '-';
        }

        if (interactionsEl) {
            interactionsEl.textContent = status.total_interactions || '-';
        }
    }

    /**
     * Update query results display (inline list)
     */
    updateQueryResultsDisplay() {
        const resultsEl = document.getElementById('query-results-display');
        if (!resultsEl) return;

        if (this.queryResults.length === 0) {
            resultsEl.innerHTML = '<div class="empty-state">No query results yet</div>';
            return;
        }

        resultsEl.innerHTML = this.queryResults.map((entry, index) => `
            <div class="query-result-entry" onclick="queryCoordinatorTab.openResultInWindow(${index})">
                <div class="result-header">
                    <span class="result-index">#${index + 1}</span>
                    <span class="result-time">${new Date(entry.timestamp).toLocaleString()}</span>
                    <span class="result-open-hint">Click to open in window</span>
                </div>
                <div class="result-query">
                    <span class="query-label">Query:</span>
                    <span class="query-text">${this.escapeHtml(entry.query)}</span>
                </div>
                <div class="result-preview">
                    <pre>${JSON.stringify(entry.result, null, 2).substring(0, 200)}${JSON.stringify(entry.result, null, 2).length > 200 ? '...' : ''}</pre>
                </div>
            </div>
        `).join('');
    }

    /**
     * Open a result from the list in a window
     * @param {number} index - Result index
     */
    openResultInWindow(index) {
        const entry = this.queryResults[index];
        if (entry) {
            this.displayQueryResultInWindow(entry.query, entry.result);
        }
    }

    /**
     * Display backlog
     * @param {Object} backlog - Backlog data
     */
    displayBacklog(backlog) {
        const backlogEl = document.getElementById('query-backlog-display');
        if (!backlogEl) return;

        // Show backlog section
        const backlogSection = document.querySelector('.backlog-section');
        if (backlogSection) {
            backlogSection.style.display = 'block';
        }

        if (!backlog || !backlog.items || backlog.items.length === 0) {
            backlogEl.innerHTML = '<div class="empty-state">No items in backlog</div>';
            return;
        }

        backlogEl.innerHTML = `
            <div class="backlog-header">
                <h4>Improvement Backlog</h4>
                <span class="backlog-count">${backlog.items.length} items</span>
            </div>
            <div class="backlog-list">
                ${backlog.items.map((item, index) => `
                    <div class="backlog-item ${item.status}">
                        <div class="item-header">
                            <span class="item-id">${item.id || index + 1}</span>
                            <span class="item-status ${item.status}">${item.status}</span>
                        </div>
                        <div class="item-content">${item.description || item.content || 'No description'}</div>
                        <div class="item-actions">
                            <button onclick="queryCoordinatorTab.approveBacklogItem('${item.id}')" class="action-btn approve">Approve</button>
                            <button onclick="queryCoordinatorTab.rejectBacklogItem('${item.id}')" class="action-btn reject">Reject</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Approve backlog item
     * @param {string} itemId - Backlog item ID
     */
    async approveBacklogItem(itemId) {
        try {
            await this.apiRequest('/coordinator/backlog/approve', 'POST', { backlog_item_id: itemId });
            this.showNotification('Item approved', 'success');
            await this.loadBacklog();
        } catch (error) {
            console.error('Failed to approve item:', error);
            this.showNotification(`Failed to approve: ${error.message}`, 'error');
        }
    }

    /**
     * Reject backlog item
     * @param {string} itemId - Backlog item ID
     */
    async rejectBacklogItem(itemId) {
        try {
            await this.apiRequest('/coordinator/backlog/reject', 'POST', { backlog_item_id: itemId });
            this.showNotification('Item rejected', 'success');
            await this.loadBacklog();
        } catch (error) {
            console.error('Failed to reject item:', error);
            this.showNotification(`Failed to reject: ${error.message}`, 'error');
        }
    }

    /**
     * Add to query history
     * @param {Object} entry - History entry
     */
    addToQueryHistory(entry) {
        this.queryHistory.unshift(entry);
        if (this.queryHistory.length > 50) {
            this.queryHistory.pop();
        }
        this.updateQueryHistoryDisplay();
    }

    /**
     * Update last history entry
     * @param {Object} updates - Updates to apply
     */
    updateLastHistoryEntry(updates) {
        if (this.queryHistory.length > 0) {
            Object.assign(this.queryHistory[0], updates);
            this.updateQueryHistoryDisplay();
        }
    }

    /**
     * Update query history display
     */
    updateQueryHistoryDisplay() {
        const historyEl = document.getElementById('query-history-list');
        if (!historyEl) return;

        if (this.queryHistory.length === 0) {
            historyEl.innerHTML = '<div class="empty-state">No query history yet</div>';
            return;
        }

        historyEl.innerHTML = this.queryHistory.slice(0, 10).map((entry, index) => `
            <div class="history-entry ${entry.status}">
                <div class="history-header">
                    <span class="history-time">${new Date(entry.timestamp).toLocaleTimeString()}</span>
                    <span class="history-status ${entry.status}">${entry.status}</span>
                </div>
                <div class="history-query">${this.escapeHtml(entry.query).substring(0, 50)}${entry.query.length > 50 ? '...' : ''}</div>
            </div>
        `).join('');
    }

    /**
     * Clear query results
     */
    clearQueryResults() {
        this.queryResults = [];
        this.updateQueryResultsDisplay();
        
        // Close all result windows
        this.resultWindowIds.forEach(windowId => {
            if (window.windowManager) {
                window.windowManager.closeWindow(windowId);
            }
        });
        this.resultWindowIds = [];
        
        this.showNotification('Results cleared', 'info');
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type
     */
    showNotification(message, type = 'info') {
        const notificationEl = document.getElementById('query-notification');
        if (notificationEl) {
            notificationEl.textContent = message;
            notificationEl.className = `notification ${type}`;
            notificationEl.style.display = 'block';

            setTimeout(() => {
                notificationEl.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Escape HTML
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape string for JavaScript template literal
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeForJs(text) {
        return text
            .replace(/\\/g, '\\\\')
            .replace(/`/g, '\\`')
            .replace(/\$/g, '\\$')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '\\r');
    }

    /**
     * Cleanup
     */
    destroy() {
        // Close all result windows
        this.resultWindowIds.forEach(windowId => {
            if (window.windowManager) {
                window.windowManager.closeWindow(windowId);
            }
        });
        this.resultWindowIds = [];

        if (this.ollamaMonitor) {
            this.ollamaMonitor.destroy();
        }
        super.destroy();
    }
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.QueryCoordinatorTab = QueryCoordinatorTab;
    // Global reference for backlog actions
    window.queryCoordinatorTab = null;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = QueryCoordinatorTab;
}
