/**
 * Ollama Admin Tab Component
 * 
 * Professional admin interface for Ollama connection management, diagnostics,
 * and interaction testing. Supports multiple agents connecting to Ollama.
 * Loaded as classic script; Test Connection is wired in app.js for reliable feedback.
 */

class OllamaAdminTab extends TabComponent {
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

    /**
     * Base URL for API requests (mindX backend). Uses same config as rest of app.
     */
    getApiBaseUrl() {
        if (typeof window !== 'undefined' && window.API_CONFIG && window.API_CONFIG.baseUrl) {
            return window.API_CONFIG.baseUrl.replace(/\/$/, '');
        }
        return '';
    }

    /**
     * Fetch from admin Ollama API (backend at API_CONFIG.baseUrl).
     * @param {string} endpoint - e.g. '/api/admin/ollama/status'
     * @param {{ method?: string, body?: string }} options - method and body for POST
     * @returns {Promise<object>} parsed JSON
     */
    async fetchData(endpoint, options = {}) {
        const baseUrl = this.getApiBaseUrl();
        const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
        const fetchOptions = {
            method: options.method || 'GET',
            headers: { 'Content-Type': 'application/json' }
        };
        if (options.body && fetchOptions.method !== 'GET') {
            fetchOptions.body = options.body;
        }
        const response = await fetch(url, fetchOptions);
        if (!response.ok) {
            const text = await response.text();
            let detail = text;
            try {
                const j = JSON.parse(text);
                detail = j.detail || j.error || text;
            } catch (_) {}
            throw new Error(`Ollama admin API error: ${response.status} - ${detail}`);
        }
        return response.json();
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
        // Test Connection is wired in app.js (testOllamaConnectionAdmin) so it always gives feedback

        // Send interaction button (admin panel uses ollama-admin-* IDs)
        const sendBtn = document.getElementById('ollama-admin-send') || document.getElementById('ollama-send-interaction');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendInteraction());
        }

        // Reload models
        const reloadModelsBtn = document.getElementById('ollama-admin-reload-models');
        if (reloadModelsBtn) {
            reloadModelsBtn.addEventListener('click', () => this.loadModels());
        }

        // Enter key for interaction input
        const inputField = document.getElementById('ollama-admin-input') || document.getElementById('ollama-interaction-input');
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

        // Model selector (admin panel)
        const modelSelect = document.getElementById('ollama-admin-model-select') || document.getElementById('ollama-model-select');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                const opt = modelSelect.options[modelSelect.selectedIndex];
                if (opt && opt.value) this.showSuccess(`Model: ${opt.textContent}`);
            });
        }

        // Settings: save
        const settingsSaveBtn = document.getElementById('ollama-settings-save');
        if (settingsSaveBtn) {
            settingsSaveBtn.addEventListener('click', () => this.saveOllamaSettings());
        }
        // Settings: refresh model list now (manual)
        const settingsRefreshModelsBtn = document.getElementById('ollama-settings-refresh-models');
        if (settingsRefreshModelsBtn) {
            settingsRefreshModelsBtn.addEventListener('click', () => this.refreshOllamaModelsNow());
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadConnectionStatus(),
            this.loadModels(),
            this.loadMetrics(),
            this.loadDiagnostics(),
            this.loadOllamaSettings()
        ]);
    }

    async loadConnectionStatus() {
        try {
            const response = await this.fetchData('/api/admin/ollama/status');
            this.connectionStatus = response;
            this.updateConnectionStatus(response);
        } catch (error) {
            console.error('Error loading connection status:', error);
            this.connectionStatus = null;
            this.updateConnectionStatus({
                success: false,
                base_url: this.getApiBaseUrl() || 'Backend',
                error: error.message || 'Backend unreachable'
            });
            this.showError('Failed to load connection status', error.message || error);
        }
    }

    async loadModels() {
        const modelSelect = document.getElementById('ollama-admin-model-select') || document.getElementById('ollama-model-select');
        if (modelSelect) {
            modelSelect.innerHTML = '<option value="">Loading...</option>';
            modelSelect.disabled = true;
        }
        try {
            const response = await this.fetchData('/api/admin/ollama/models');
            if (response.success && response.models && response.models.length > 0) {
                this.updateModelSelector(response.models);
                this.showSuccess(`Loaded ${response.models.length} model(s)`);
            } else {
                this.updateModelSelector([]);
                this.showError('No models', 'Ollama returned no models. Test connection and ensure at least one model is pulled (e.g. ollama pull llama3.2).');
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.updateModelSelector([]);
            this.showError('Load models failed', error.message || String(error));
        } finally {
            if (modelSelect) modelSelect.disabled = false;
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

    setOllamaSettingsStatus(message, isError = false) {
        const el = document.getElementById('ollama-settings-status');
        if (!el) return;
        el.textContent = message || '';
        el.className = 'ollama-settings-status' + (isError ? ' error' : '');
    }

    async loadOllamaSettings() {
        try {
            const response = await this.fetchData('/mindxagent/ollama/settings');
            if (!response.success) {
                this.setOllamaSettingsStatus('Settings unavailable', true);
                return;
            }
            const rpmInput = document.getElementById('ollama-settings-calls-per-minute');
            const intervalSelect = document.getElementById('ollama-settings-model-update-interval');
            if (rpmInput && response.calls_per_minute != null) {
                rpmInput.value = response.calls_per_minute;
            }
            if (intervalSelect && response.model_discovery_interval_seconds != null) {
                const val = String(response.model_discovery_interval_seconds);
                if (intervalSelect.querySelector(`option[value="${val}"]`)) {
                    intervalSelect.value = val;
                } else {
                    intervalSelect.value = val;
                    const opt = document.createElement('option');
                    opt.value = val;
                    opt.textContent = `${val}s`;
                    intervalSelect.appendChild(opt);
                    intervalSelect.value = val;
                }
            }
            const lastDiscovery = response.last_model_discovery;
            const lastStr = lastDiscovery ? new Date(lastDiscovery * 1000).toLocaleString() : 'Never';
            this.setOllamaSettingsStatus(`Model list: ${response.models_count || 0} models; last updated ${lastStr}`);
        } catch (error) {
            if (error.message && (error.message.includes('503') || error.message.includes('not available'))) {
                this.setOllamaSettingsStatus('mindXagent Ollama not available. Start mindX to use these settings.', true);
            } else {
                this.setOllamaSettingsStatus('Failed to load settings: ' + (error.message || error), true);
            }
            console.warn('Ollama settings load failed:', error);
        }
    }

    async saveOllamaSettings() {
        const rpmInput = document.getElementById('ollama-settings-calls-per-minute');
        const intervalSelect = document.getElementById('ollama-settings-model-update-interval');
        const payload = {};
        if (rpmInput && rpmInput.value !== '') {
            const rpm = parseInt(rpmInput.value, 10);
            if (!isNaN(rpm) && rpm >= 1 && rpm <= 10000) payload.calls_per_minute = rpm;
        }
        if (intervalSelect && intervalSelect.value !== '') {
            payload.model_discovery_interval_seconds = parseInt(intervalSelect.value, 10);
        }
        if (Object.keys(payload).length === 0) {
            this.setOllamaSettingsStatus('No changes to save.');
            return;
        }
        this.setOllamaSettingsStatus('Saving…');
        try {
            const response = await this.fetchData('/mindxagent/ollama/settings', {
                method: 'PATCH',
                body: JSON.stringify(payload)
            });
            if (response.success) {
                this.setOllamaSettingsStatus('Settings saved.');
                this.showSuccess('Ollama settings saved');
            } else {
                this.setOllamaSettingsStatus('Save failed', true);
            }
        } catch (error) {
            this.setOllamaSettingsStatus('Save failed: ' + (error.message || error), true);
            this.showError('Save failed', error.message || String(error));
        }
    }

    async refreshOllamaModelsNow() {
        this.setOllamaSettingsStatus('Refreshing model list…');
        try {
            const response = await this.fetchData('/mindxagent/ollama/models/refresh', { method: 'POST' });
            if (response.success) {
                this.setOllamaSettingsStatus(`Model list refreshed: ${response.models_count || 0} models.`);
                this.showSuccess('Model list refreshed');
                await this.loadModels();
            } else {
                this.setOllamaSettingsStatus('Refresh failed', true);
            }
        } catch (error) {
            this.setOllamaSettingsStatus('Refresh failed: ' + (error.message || error), true);
            this.showError('Refresh failed', error.message || String(error));
        }
    }

    async testConnection() {
        const testBtn = document.getElementById('ollama-test-connection');
        const originalText = testBtn?.textContent;
        if (testBtn) {
            testBtn.disabled = true;
            testBtn.textContent = 'Testing…';
        }
        // Show "Testing…" in the status card immediately so user sees feedback
        this.updateConnectionStatus({ testing: true, message: 'Testing connection…' });

        try {
            const response = await this.fetchData('/api/admin/ollama/test', {
                method: 'POST',
                body: JSON.stringify({
                    try_fallback: true
                })
            });

            const result = response.test_result;
            this.updateConnectionStatus(result);

            if (result && result.success) {
                this.showSuccess(`Connected · ${result.model_count ?? 0} model(s) available`);
                await this.loadConnectionStatus();
            } else {
                const err = (result && (result.error || result.message)) || 'Connection failed';
                this.showError('Connection test failed', err);
            }
        } catch (error) {
            const errMsg = error && (error.message || String(error));
            this.updateConnectionStatus({ success: false, error: errMsg });
            this.showError('Connection test error', errMsg);
        } finally {
            if (testBtn) {
                testBtn.disabled = false;
                testBtn.textContent = originalText || 'Test Connection';
            }
        }
    }

    async sendInteraction() {
        const inputField = document.getElementById('ollama-admin-input') || document.getElementById('ollama-interaction-input');
        const modelSelect = document.getElementById('ollama-admin-model-select') || document.getElementById('ollama-model-select');
        const responseArea = document.getElementById('ollama-admin-response') || document.getElementById('ollama-response-output');
        const sendBtn = document.getElementById('ollama-admin-send') || document.getElementById('ollama-send-interaction');

        if (!inputField || !modelSelect) return;

        const prompt = inputField.value.trim();
        if (!prompt) {
            this.showError('Prompt required', 'Enter a prompt in the text area.');
            return;
        }

        const model = modelSelect.value;
        if (!model) {
            this.showError('Model required', 'Select a model from the dropdown. Use "Reload models" if the list is empty.');
            return;
        }

        const originalText = sendBtn?.textContent;

        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = 'Sending...';
        }

        if (responseArea) {
            responseArea.value = 'Sending to Ollama...';
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

            const responseText = response.response ?? response.message?.content ?? (response.message && typeof response.message === 'object' ? response.message.content : null) ?? 'No response received';
            if (response.success && (responseText && !String(responseText).trim().startsWith('Error:'))) {
                if (responseArea) {
                    responseArea.value = String(responseText).trim();
                }
                this.showSuccess('Response received');
                this.addInteractionToHistory(prompt, responseText);
                await this.loadDiagnostics();
                await this.loadMetrics();
            } else {
                const errorMsg = response.error || responseText || 'Interaction failed';
                if (responseArea) {
                    responseArea.value = `Error: ${errorMsg}`;
                }
                this.showError('Interaction failed', errorMsg);
            }
        } catch (error) {
            const errorMsg = error.message || 'Failed to send (check backend and Ollama).';
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

        const escapeHtml = (s) => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        const isTesting = status?.testing === true;
        const conn = status?.connection || {};
        const isConnected = !isTesting && (status?.success ?? status?.connected ?? conn?.connected ?? false);
        const baseUrl = status?.base_url ?? conn?.base_url ?? this.connectionStatus?.connection?.base_url ?? '—';
        const primaryUrl = status?.primary_url ?? conn?.primary_url ?? this.connectionStatus?.connection?.primary_url ?? '10.0.0.155:18080';
        const fallbackUrl = status?.fallback_url ?? conn?.fallback_url ?? this.connectionStatus?.connection?.fallback_url ?? 'localhost:11434';
        const modelCount = status?.model_count ?? conn?.model_count ?? this.connectionStatus?.connection?.model_count ?? 0;
        const usingFallback = status?.using_fallback ?? conn?.using_fallback ?? this.connectionStatus?.connection?.using_fallback ?? false;

        const errorHtml = status?.error ? `<div class="status-item error"><span class="status-label">Error:</span><span class="status-value">${escapeHtml(String(status.error))}</span></div>` : '';
        const messageHtml = status?.message ? `<div class="status-item"><span class="status-label">Message:</span><span class="status-value">${escapeHtml(String(status.message))}</span></div>` : '';

        let cardClass = 'connection-status-card ';
        let dotClass = 'status-dot ';
        let statusText = 'Disconnected';
        if (isTesting) {
            cardClass += 'testing';
            dotClass += 'testing';
            statusText = 'Testing…';
        } else {
            cardClass += isConnected ? 'connected' : 'disconnected';
            dotClass += isConnected ? 'active' : 'inactive';
            statusText = isConnected ? 'Connected' : 'Disconnected';
        }
        const primaryDisplay = escapeHtml(String(primaryUrl).replace(/^https?:\/\//, ''));
        const fallbackDisplay = escapeHtml(String(fallbackUrl).replace(/^https?:\/\//, ''));
        const baseDisplay = escapeHtml(String(baseUrl).replace(/^https?:\/\//, ''));
        const requestSent = status?.request_sent ?? conn?.request_sent ?? '';
        const responseStatus = status?.response_status ?? conn?.response_status ?? status?.status_code ?? '';
        const responsePreview = status?.response_preview ?? conn?.response_preview ?? '';
        const primaryRequest = status?.primary_request_sent ?? conn?.primary_request_sent ?? '';
        const primaryResponse = status?.primary_response_preview ?? conn?.primary_response_preview ?? '';
        const primaryRespStatus = status?.primary_response_status ?? conn?.primary_response_status ?? '';
        const requestBlock = requestSent ? `<div class="status-item request-response"><span class="status-label">Request:</span><span class="status-value mono">${escapeHtml(requestSent)}</span></div>` : '';
        const responseBlock = (responseStatus !== '' || responsePreview) ? `<div class="status-item request-response"><span class="status-label">Response:</span><span class="status-value mono">${responseStatus !== '' ? escapeHtml(String(responseStatus)) + ' — ' : ''}${escapeHtml(String(responsePreview))}</span></div>` : '';
        const primaryBlock = (primaryRequest || primaryResponse) ? `<div class="status-item request-response primary-attempt"><span class="status-label">Primary attempt:</span><span class="status-value mono">${escapeHtml(primaryRequest || '—')} → ${primaryRespStatus !== '' ? primaryRespStatus + ' ' : ''}${escapeHtml(String(primaryResponse))}</span></div>` : '';

        statusContainer.innerHTML = `
            <div class="${cardClass}">
                <div class="status-indicator">
                    <span class="${dotClass}"></span>
                    <span class="status-text">${statusText}</span>
                </div>
                <div class="status-details">
                    <div class="status-item">
                        <span class="status-label">Primary (try first):</span>
                        <span class="status-value">${primaryDisplay}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Fallback (localhost):</span>
                        <span class="status-value">${fallbackDisplay}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">${status?.error ? 'Backend' : 'Connected at'} URL:</span>
                        <span class="status-value">${baseDisplay}</span>
                    </div>
                    ${!isTesting ? `<div class="status-item"><span class="status-label">Models:</span><span class="status-value">${modelCount}</span></div>` : ''}
                    ${usingFallback ? '<div class="status-item warning"><span class="status-label">⚠️ Using Fallback</span></div>' : ''}
                    ${primaryBlock}
                    ${requestBlock}
                    ${responseBlock}
                    ${messageHtml}
                    ${errorHtml}
                </div>
            </div>
        `;
    }

    updateModelSelector(models) {
        const modelSelect = document.getElementById('ollama-admin-model-select') || document.getElementById('ollama-model-select');
        if (!modelSelect) return;

        const currentValue = modelSelect.value;
        modelSelect.innerHTML = '<option value="">Select model...</option>';
        if (!models || models.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'No models – Test connection & Reload models';
            opt.disabled = true;
            modelSelect.appendChild(opt);
            return;
        }
        models.forEach(model => {
            const modelName = typeof model === 'string' ? model : (model.name || model.model || String(model));
            if (!modelName) return;
            const option = document.createElement('option');
            option.value = modelName;
            option.textContent = modelName;
            if (modelName === currentValue) option.selected = true;
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
        const historyContainer = document.getElementById('ollama-admin-history') || document.getElementById('ollama-interaction-history');
        if (!historyContainer) return;

        const esc = (s) => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        const p = esc(prompt).substring(0, 120) + (prompt.length > 120 ? '...' : '');
        const r = esc(String(response || '')).substring(0, 200) + ((response || '').length > 200 ? '...' : '');

        const entry = document.createElement('div');
        entry.className = 'interaction-history-entry';
        entry.innerHTML = `
            <div class="interaction-prompt"><strong>Prompt:</strong> ${p}</div>
            <div class="interaction-response"><strong>Response:</strong> ${r}</div>
            <div class="interaction-timestamp">${new Date().toLocaleString()}</div>
        `;
        historyContainer.insertBefore(entry, historyContainer.firstChild);

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

if (typeof window !== 'undefined') {
    window.OllamaAdminTab = OllamaAdminTab;
}
