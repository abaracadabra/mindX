/**
 * Ollama Interaction Monitor Component
 * 
 * Real-time monitoring component for Ollama interactions in mindXagent.
 * Provides connection status, conversation tracking, and performance metrics.
 * 
 * @module OllamaMonitor
 */

class OllamaMonitor {
    constructor(config = {}) {
        this.config = {
            refreshInterval: config.refreshInterval || 2000, // 2 seconds default
            endpoint: config.endpoint || '/mindxagent/ollama',
            containerId: config.containerId || 'ollama-monitor-container',
            ...config
        };

        this.isMonitoring = false;
        this.monitorInterval = null;
        this.connectionHistory = [];
        this.metrics = {
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            averageLatency: 0,
            lastCheck: null
        };

        console.log('🔍 OllamaMonitor initialized');
    }

    /**
     * Initialize the monitor UI
     */
    async initialize() {
        const container = document.getElementById(this.config.containerId);
        if (!container) {
            console.error(`❌ Container ${this.config.containerId} not found`);
            return false;
        }

        // Create monitor UI structure
        this.createMonitorUI(container);
        
        // Load initial data
        await this.refresh();

        console.log('✅ OllamaMonitor initialized');
        return true;
    }

    /**
     * Create monitor UI structure
     * @param {HTMLElement} container - Container element
     */
    createMonitorUI(container) {
        container.innerHTML = `
            <div class="ollama-monitor">
                <div class="monitor-header">
                    <h3>🔍 Ollama Interaction Monitor</h3>
                    <div class="monitor-controls">
                        <button id="ollama-monitor-start-btn" class="monitor-btn start">Start Monitor</button>
                        <button id="ollama-monitor-stop-btn" class="monitor-btn stop" style="display: none;">Stop Monitor</button>
                        <button id="ollama-monitor-refresh-btn" class="monitor-btn refresh">🔄 Refresh</button>
                    </div>
                </div>

                <div class="monitor-status-grid">
                    <div class="status-card connection">
                        <div class="status-label">Connection</div>
                        <div id="ollama-monitor-connection" class="status-value">-</div>
                        <div id="ollama-monitor-connection-indicator" class="status-indicator"></div>
                    </div>
                    <div class="status-card url">
                        <div class="status-label">Server URL</div>
                        <div id="ollama-monitor-url" class="status-value">-</div>
                    </div>
                    <div class="status-card models">
                        <div class="status-label">Available Models</div>
                        <div id="ollama-monitor-models-count" class="status-value">-</div>
                    </div>
                    <div class="status-card current-model">
                        <div class="status-label">Current Model</div>
                        <div id="ollama-monitor-current-model" class="status-value">-</div>
                    </div>
                    <div class="status-card conversations">
                        <div class="status-label">Active Conversations</div>
                        <div id="ollama-monitor-conversations" class="status-value">-</div>
                    </div>
                    <div class="status-card latency">
                        <div class="status-label">Avg Latency</div>
                        <div id="ollama-monitor-latency" class="status-value">-</div>
                    </div>
                </div>

                <div class="monitor-metrics">
                    <h4>Performance Metrics</h4>
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <div class="metric-label">Total Requests</div>
                            <div id="ollama-monitor-total-requests" class="metric-value">0</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Success Rate</div>
                            <div id="ollama-monitor-success-rate" class="metric-value">-</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Failed Requests</div>
                            <div id="ollama-monitor-failed-requests" class="metric-value">0</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Last Check</div>
                            <div id="ollama-monitor-last-check" class="metric-value">-</div>
                        </div>
                    </div>
                </div>

                <div class="monitor-conversation-preview">
                    <h4>Recent Interactions</h4>
                    <div id="ollama-monitor-recent-interactions" class="interactions-list">
                        <div class="empty-state">No interactions yet</div>
                    </div>
                </div>

                <div class="monitor-log">
                    <h4>Connection Log</h4>
                    <div id="ollama-monitor-log" class="log-content">
                        <div class="log-entry">Monitor ready</div>
                    </div>
                </div>
            </div>
        `;

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const startBtn = document.getElementById('ollama-monitor-start-btn');
        const stopBtn = document.getElementById('ollama-monitor-stop-btn');
        const refreshBtn = document.getElementById('ollama-monitor-refresh-btn');

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startMonitoring());
        }

        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopMonitoring());
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refresh());
        }
    }

    /**
     * Start monitoring
     */
    startMonitoring() {
        if (this.isMonitoring) {
            return;
        }

        this.isMonitoring = true;
        this.monitorInterval = setInterval(() => this.refresh(), this.config.refreshInterval);

        // Update UI
        const startBtn = document.getElementById('ollama-monitor-start-btn');
        const stopBtn = document.getElementById('ollama-monitor-stop-btn');
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'inline-block';

        this.addLog('Monitoring started', 'info');
        console.log('🟢 Ollama monitoring started');
    }

    /**
     * Stop monitoring
     */
    stopMonitoring() {
        if (!this.isMonitoring) {
            return;
        }

        this.isMonitoring = false;
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
        }

        // Update UI
        const startBtn = document.getElementById('ollama-monitor-start-btn');
        const stopBtn = document.getElementById('ollama-monitor-stop-btn');
        if (startBtn) startBtn.style.display = 'inline-block';
        if (stopBtn) stopBtn.style.display = 'none';

        this.addLog('Monitoring stopped', 'info');
        console.log('🔴 Ollama monitoring stopped');
    }

    /**
     * Refresh monitor data
     */
    async refresh() {
        const startTime = Date.now();

        try {
            // Fetch status
            const statusResponse = await fetch(`${this.config.endpoint}/status`);
            const status = await statusResponse.json();

            // Fetch conversation
            const conversationResponse = await fetch(`${this.config.endpoint}/conversation?limit=10`);
            const conversation = await conversationResponse.json();

            // Update metrics
            const latency = Date.now() - startTime;
            this.updateMetrics(latency, statusResponse.ok);

            // Update UI
            this.updateStatusDisplay(status);
            this.updateConversationPreview(conversation);
            this.updateMetricsDisplay();

            this.metrics.lastCheck = new Date();
            this.addLog('Data refreshed successfully', 'success');

        } catch (error) {
            console.error('❌ Error refreshing Ollama monitor:', error);
            this.updateMetrics(Date.now() - startTime, false);
            this.addLog(`Error: ${error.message}`, 'error');
        }
    }

    /**
     * Update status display
     * @param {Object} status - Status data
     */
    updateStatusDisplay(status) {
        const connectionEl = document.getElementById('ollama-monitor-connection');
        const indicatorEl = document.getElementById('ollama-monitor-connection-indicator');
        const urlEl = document.getElementById('ollama-monitor-url');
        const modelsCountEl = document.getElementById('ollama-monitor-models-count');
        const currentModelEl = document.getElementById('ollama-monitor-current-model');
        const conversationsEl = document.getElementById('ollama-monitor-conversations');
        const latencyEl = document.getElementById('ollama-monitor-latency');

        if (connectionEl) {
            connectionEl.textContent = status.connected ? '🟢 Connected' : '🔴 Disconnected';
        }

        if (indicatorEl) {
            indicatorEl.className = `status-indicator ${status.connected ? 'connected' : 'disconnected'}`;
        }

        if (urlEl) urlEl.textContent = status.base_url || '-';
        if (modelsCountEl) modelsCountEl.textContent = status.models_count || 0;
        if (currentModelEl) currentModelEl.textContent = status.current_model || '-';
        if (conversationsEl) conversationsEl.textContent = status.conversation_count || 0;
        if (latencyEl) latencyEl.textContent = `${this.metrics.averageLatency}ms`;
    }

    /**
     * Update conversation preview
     * @param {Object} conversation - Conversation data
     */
    updateConversationPreview(conversation) {
        const interactionsEl = document.getElementById('ollama-monitor-recent-interactions');
        if (!interactionsEl) return;

        if (!conversation.success || !conversation.messages || conversation.messages.length === 0) {
            interactionsEl.innerHTML = '<div class="empty-state">No recent interactions</div>';
            return;
        }

        const recentMessages = conversation.messages.slice(-5).reverse();
        interactionsEl.innerHTML = recentMessages.map((msg, index) => {
            const role = msg.role || 'unknown';
            const content = msg.content || msg.message || '';
            const timestamp = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : '';

            return `
                <div class="interaction-item ${role}">
                    <div class="interaction-header">
                        <span class="interaction-role">${role === 'user' ? '🤖 mindXagent' : '💬 Ollama'}</span>
                        <span class="interaction-time">${timestamp}</span>
                    </div>
                    <div class="interaction-content">${this.truncateText(content, 100)}</div>
                </div>
            `;
        }).join('');
    }

    /**
     * Update metrics display
     */
    updateMetricsDisplay() {
        const totalEl = document.getElementById('ollama-monitor-total-requests');
        const successRateEl = document.getElementById('ollama-monitor-success-rate');
        const failedEl = document.getElementById('ollama-monitor-failed-requests');
        const lastCheckEl = document.getElementById('ollama-monitor-last-check');

        if (totalEl) totalEl.textContent = this.metrics.totalRequests;
        
        const successRate = this.metrics.totalRequests > 0
            ? ((this.metrics.successfulRequests / this.metrics.totalRequests) * 100).toFixed(1)
            : 0;
        if (successRateEl) successRateEl.textContent = `${successRate}%`;

        if (failedEl) failedEl.textContent = this.metrics.failedRequests;
        if (lastCheckEl) {
            lastCheckEl.textContent = this.metrics.lastCheck
                ? this.metrics.lastCheck.toLocaleTimeString()
                : '-';
        }
    }

    /**
     * Update metrics
     * @param {number} latency - Request latency
     * @param {boolean} success - Whether request was successful
     */
    updateMetrics(latency, success) {
        this.metrics.totalRequests++;
        if (success) {
            this.metrics.successfulRequests++;
        } else {
            this.metrics.failedRequests++;
        }

        // Calculate average latency
        const totalLatency = this.metrics.averageLatency * (this.metrics.totalRequests - 1) + latency;
        this.metrics.averageLatency = Math.round(totalLatency / this.metrics.totalRequests);

        // Store in history (keep last 100)
        this.connectionHistory.push({
            timestamp: Date.now(),
            latency,
            success
        });
        if (this.connectionHistory.length > 100) {
            this.connectionHistory.shift();
        }
    }

    /**
     * Add log entry
     * @param {string} message - Log message
     * @param {string} type - Log type (info, success, error, warning)
     */
    addLog(message, type = 'info') {
        const logEl = document.getElementById('ollama-monitor-log');
        if (!logEl) return;

        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `<span class="log-time">${timestamp}</span> <span class="log-message">${message}</span>`;

        logEl.insertBefore(logEntry, logEl.firstChild);

        // Keep only last 50 entries
        while (logEl.children.length > 50) {
            logEl.removeChild(logEl.lastChild);
        }
    }

    /**
     * Truncate text
     * @param {string} text - Text to truncate
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated text
     */
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Cleanup
     */
    destroy() {
        this.stopMonitoring();
        console.log('🧹 OllamaMonitor destroyed');
    }
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.OllamaMonitor = OllamaMonitor;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = OllamaMonitor;
}
