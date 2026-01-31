/**
 * Ollama Admin Tab Component
 * 
 * Professional admin interface for Ollama connection management, diagnostics,
 * and interaction testing. Supports multiple agents connecting to Ollama.
 */

import { TabComponent } from './tab-component.js';

export class OllamaAdminTab extends TabComponent {
    constructor() {
        super('ollama-admin');
        this.logLevel = 'INFO'; // Default log level
        this.logLimit = 100;
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.connectionStatus = null;
        this.metrics = null;
        this.logs = [];
    }

    async initialize() {
        await super.initialize();
        this.setupEventListeners();
        await this.loadInitialData();
    }

    async onActivate() {
        await super.onActivate();
        if (this.autoRefresh) {
            this.startAutoRefresh();
        }
    }

    async onDeactivate() {
        await super.onDeactivate();
        this.stopAutoRefresh();
    }

    setupEventListeners() {
        // Connection test button
        const testBtn = document.getElementById('ollama-test-connection');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testConnection());
        }

        // Send interaction button
        const sendBtn = document.getElementById('ollama-send-interaction');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendInteraction());
        }

        // Enter key for interaction input
        const inputField = document.getElementById('ollama-interaction-input');
        if (inputField) {
            inputField.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendInteraction();
                }
            });
        }

        // Log level toggle
        const logLevelSelect = document.getElementById('ollama-log-level');
        if (logLevelSelect) {
            logLevelSelect.addEventListener('change', (e) => {
                this.logLevel = e.target.value;
                this.loadDiagnostics();
            });
        }

        // Log limit selector
        const logLimitSelect = document.getElementById('ollama-log-limit');
        if (logLimitSelect) {
            logLimitSelect.addEventListener('change', (e) => {
                this.logLimit = parseInt(e.target.value);
                this.loadDiagnostics();
            });
        }

        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('ollama-auto-refresh');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.autoRefresh = e.target.checked;
                if (this.autoRefresh) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('ollama-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshAll());
        }

        // Clear logs button
        const clearLogsBtn = document.getElementById('ollama-clear-logs');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => this.clearLogsDisplay());
        }

        // Model selector
        const modelSelect = document.getElementById('ollama-model-select');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                // Model changed, update UI if needed
            });
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadConnectionStatus(),
            this.loadModels(),
            this.loadMetrics(),
            this.loadDiagnostics()
        ]);
    }

    async loadConnectionStatus() {
        try {
            const response = await this.fetchData('/api/admin/ollama/status');
            this.connectionStatus = response;
            this.updateConnectionStatus(response);
        } catch (error) {
            console.error('Error loading connection status:', error);
            this.showError('Failed to load connection status', error);
        }
    }

    async loadModels() {
        try {
            const response = await this.fetchData('/api/admin/ollama/models');
            if (response.success && response.models) {
                this.updateModelSelector(response.models);
            }
        } catch (error) {
            console.error('Error loading models:', error);
        }
    }

    async loadMetrics() {
        try {
            const response = await this.fetchData('/api/admin/ollama/metrics');
            if (response.success && response.metrics) {
                this.metrics = response.metrics;
                this.updateMetricsDisplay(response.metrics);
            }
        } catch (error) {
            console.error('Error loading metrics:', error);
        }
    }

    async loadDiagnostics() {
        try {
            const params = new URLSearchParams({
                log_level: this.logLevel,
                limit: this.logLimit.toString()
            });
            const response = await this.fetchData(`/api/admin/ollama/diagnostics?${params}`);
            if (response.success && response.logs) {
                this.logs = response.logs;
                this.updateLogsDisplay(response.logs);
            }
        } catch (error) {
            console.error('Error loading diagnostics:', error);
        }
    }

    async testConnection() {
        const testBtn = document.getElementById('ollama-test-connection');
        const originalText = testBtn?.textContent;
        if (testBtn) {
            testBtn.disabled = true;
            testBtn.textContent = 'Testing...';
        }

        try {
            const response = await this.fetchData('/api/admin/ollama/test', {
                method: 'POST',
                body: JSON.stringify({
                    try_fallback: true
                })
            });

            if (response.success) {
                this.showSuccess('Connection test completed');
                this.updateConnectionStatus(response.test_result);
                await this.loadConnectionStatus();
            } else {
                this.showError('Connection test failed', response.test_result?.error);
            }
        } catch (error) {
            this.showError('Connection test error', error);
        } finally {
            if (testBtn) {
                testBtn.disabled = false;
                testBtn.textContent = originalText || 'Test Connection';
            }
        }
    }

    async sendInteraction() {
        const inputField = document.getElementById('ollama-interaction-input');
        const modelSelect = document.getElementById('ollama-model-select');
        const responseArea = document.getElementById('ollama-response-output');
        const sendBtn = document.getElementById('ollama-send-interaction');

        if (!inputField || !modelSelect) return;

        const prompt = inputField.value.trim();
        if (!prompt) {
            this.showError('Please enter a prompt');
            return;
        }

        const model = modelSelect.value;
        const originalText = sendBtn?.textContent;

        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = 'Sending...';
        }

        if (responseArea) {
            responseArea.value = 'Processing...';
        }

        try {
            const response = await this.fetchData('/api/admin/ollama/interact', {
                method: 'POST',
                body: JSON.stringify({
                    prompt: prompt,
                    model: model,
                    use_chat: true,
                    temperature: 0.7,
                    max_tokens: 2048
                })
            });

            if (response.success) {
                if (responseArea) {
                    responseArea.value = response.response || 'No response received';
                }
                this.showSuccess('Interaction completed');
                
                // Add to interaction history
                this.addInteractionToHistory(prompt, response.response);
                
                // Refresh diagnostics to show new log entry
                await this.loadDiagnostics();
                await this.loadMetrics();
            } else {
                const errorMsg = response.error || 'Interaction failed';
                if (responseArea) {
                    responseArea.value = `Error: ${errorMsg}`;
                }
                this.showError('Interaction failed', errorMsg);
            }
        } catch (error) {
            const errorMsg = error.message || 'Failed to send interaction';
            if (responseArea) {
                responseArea.value = `Error: ${errorMsg}`;
            }
            this.showError('Interaction error', errorMsg);
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = originalText || 'Send';
            }
        }
    }

    updateConnectionStatus(status) {
        const statusContainer = document.getElementById('ollama-connection-status');
        if (!statusContainer) return;

        const isConnected = status?.success || status?.connected;
        const baseUrl = status?.base_url || this.connectionStatus?.connection?.base_url || 'Unknown';
        const modelCount = status?.model_count || this.connectionStatus?.connection?.model_count || 0;
        const usingFallback = status?.using_fallback || this.connectionStatus?.connection?.using_fallback || false;

        statusContainer.innerHTML = `
            <div class="connection-status-card ${isConnected ? 'connected' : 'disconnected'}">
                <div class="status-indicator">
                    <span class="status-dot ${isConnected ? 'active' : 'inactive'}"></span>
                    <span class="status-text">${isConnected ? 'Connected' : 'Disconnected'}</span>
                </div>
                <div class="status-details">
                    <div class="status-item">
                        <span class="status-label">Base URL:</span>
                        <span class="status-value">${baseUrl}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Models:</span>
                        <span class="status-value">${modelCount}</span>
                    </div>
                    ${usingFallback ? '<div class="status-item warning"><span class="status-label">⚠️ Using Fallback</span></div>' : ''}
                </div>
            </div>
        `;
    }

    updateModelSelector(models) {
        const modelSelect = document.getElementById('ollama-model-select');
        if (!modelSelect) return;

        const currentValue = modelSelect.value;
        modelSelect.innerHTML = '<option value="">Select Model...</option>';
        
        models.forEach(model => {
            const modelName = model.name || model;
            const option = document.createElement('option');
            option.value = modelName;
            option.textContent = modelName;
            if (modelName === currentValue) {
                option.selected = true;
            }
            modelSelect.appendChild(option);
        });
    }

    updateMetricsDisplay(metrics) {
        const metricsContainer = document.getElementById('ollama-metrics-display');
        if (!metricsContainer || !metrics) return;

        const successRate = metrics.total_requests > 0 
            ? ((metrics.successful_requests / metrics.total_requests) * 100).toFixed(1)
            : '0.0';

        metricsContainer.innerHTML = `
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value">${metrics.total_requests || 0}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Success Rate</div>
                    <div class="metric-value">${successRate}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Failed Requests</div>
                    <div class="metric-value error">${metrics.failed_requests || 0}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Tokens</div>
                    <div class="metric-value">${(metrics.total_tokens || 0).toLocaleString()}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Avg Latency</div>
                    <div class="metric-value">${(metrics.average_latency_ms || 0).toFixed(0)}ms</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Rate Limit Hits</div>
                    <div class="metric-value warning">${metrics.rate_limit_hits || 0}</div>
                </div>
            </div>
        `;
    }

    updateLogsDisplay(logs) {
        const logsContainer = document.getElementById('ollama-logs-display');
        if (!logsContainer) return;

        if (!logs || logs.length === 0) {
            logsContainer.innerHTML = '<div class="no-logs">No diagnostic logs available</div>';
            return;
        }

        const logsHTML = logs.map(log => {
            const timestamp = new Date(log.timestamp).toLocaleString();
            const logLevel = log.log_level || 'INFO';
            const eventType = log.event_type || 'unknown';
            const agentId = log.agent_id || 'unknown';
            
            return `
                <div class="log-entry log-level-${logLevel.toLowerCase()}">
                    <div class="log-header">
                        <span class="log-timestamp">${timestamp}</span>
                        <span class="log-level-badge log-level-${logLevel.toLowerCase()}">${logLevel}</span>
                        <span class="log-agent">${agentId}</span>
                        <span class="log-event">${eventType}</span>
                    </div>
                    <div class="log-content">
                        <pre>${JSON.stringify(log.data || log, null, 2)}</pre>
                    </div>
                </div>
            `;
        }).join('');

        logsContainer.innerHTML = logsHTML;
        
        // Auto-scroll to bottom
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    addInteractionToHistory(prompt, response) {
        const historyContainer = document.getElementById('ollama-interaction-history');
        if (!historyContainer) return;

        const entry = document.createElement('div');
        entry.className = 'interaction-history-entry';
        entry.innerHTML = `
            <div class="interaction-prompt">
                <strong>Prompt:</strong> ${prompt.substring(0, 100)}${prompt.length > 100 ? '...' : ''}
            </div>
            <div class="interaction-response">
                <strong>Response:</strong> ${(response || '').substring(0, 200)}${(response || '').length > 200 ? '...' : ''}
            </div>
            <div class="interaction-timestamp">${new Date().toLocaleString()}</div>
        `;
        
        historyContainer.insertBefore(entry, historyContainer.firstChild);
        
        // Limit history to 20 entries
        while (historyContainer.children.length > 20) {
            historyContainer.removeChild(historyContainer.lastChild);
        }
    }

    clearLogsDisplay() {
        const logsContainer = document.getElementById('ollama-logs-display');
        if (logsContainer) {
            logsContainer.innerHTML = '<div class="no-logs">Logs cleared</div>';
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear any existing interval
        this.refreshInterval = setInterval(() => {
            this.loadConnectionStatus();
            this.loadMetrics();
            this.loadDiagnostics();
        }, 5000); // Refresh every 5 seconds
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async refreshAll() {
        await this.loadInitialData();
        this.showSuccess('Data refreshed');
    }

    showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    showError(title, message) {
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.innerHTML = `<strong>${title}</strong><br>${message || ''}`;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }
}
