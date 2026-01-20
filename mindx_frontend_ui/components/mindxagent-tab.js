/**
 * mindXagent Tab Component
 * 
 * Specialized tab component for mindXagent monitoring and control.
 * Includes enhanced Ollama interaction monitoring.
 * 
 * @module MindXagentTab
 */

class MindXagentTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'mindxagent',
            label: 'mindXagent',
            group: 'core',
            refreshInterval: 3000, // 3 seconds
            autoRefresh: true,
            ...config
        });

        this.ollamaMonitor = null;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Initialize Ollama monitor
        this.ollamaMonitor = new OllamaMonitor({
            containerId: 'mindxagent-ollama-monitor-container',
            endpoint: '/mindxagent/ollama',
            refreshInterval: 2000
        });

        await this.ollamaMonitor.initialize();
        this.registerComponent('ollamaMonitor', this.ollamaMonitor);

        // Set up event listeners
        this.setupEventListeners();

        console.log('✅ MindXagentTab initialized');
        return true;
    }

    /**
     * Activate the tab
     */
    async onActivate() {
        await super.onActivate();

        // Load all data
        await Promise.all([
            this.loadStatus(),
            this.loadOllamaStatus(),
            this.loadConversation(),
            this.loadThinking(),
            this.loadActions()
        ]);

        // Start Ollama monitoring
        if (this.ollamaMonitor) {
            this.ollamaMonitor.startMonitoring();
        }

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

        await Promise.all([
            this.loadStatus(),
            this.loadOllamaStatus(),
            this.loadConversation()
        ]);
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-mindxagent-status-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refresh());
        }

        // Settings save button
        const saveBtn = document.getElementById('save-mindxagent-settings-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSettings());
        }

        // Conversation controls
        const refreshConvBtn = document.getElementById('refresh-ollama-conversation-btn');
        if (refreshConvBtn) {
            refreshConvBtn.addEventListener('click', () => this.loadConversation());
        }

        const clearConvBtn = document.getElementById('clear-ollama-conversation-btn');
        if (clearConvBtn) {
            clearConvBtn.addEventListener('click', () => this.clearConversation());
        }
    }

    /**
     * Load mindXagent status
     */
    async loadStatus() {
        try {
            const status = await this.apiRequest('/mindxagent/status');
            this.updateStatusDisplay(status);
            this.setData('status', status);
        } catch (error) {
            console.error('Failed to load mindXagent status:', error);
            this.showError('Failed to load status', document.getElementById('mindxagent-status-display'));
        }
    }

    /**
     * Load Ollama status
     */
    async loadOllamaStatus() {
        try {
            const ollamaStatus = await this.apiRequest('/mindxagent/ollama/status');
            this.updateOllamaStatusDisplay(ollamaStatus);
            this.setData('ollamaStatus', ollamaStatus);
        } catch (error) {
            console.error('Failed to load Ollama status:', error);
            // Don't show error if Ollama is not configured
            if (!error.message.includes('not initialized')) {
                console.warn('Ollama status unavailable');
            }
        }
    }

    /**
     * Load conversation
     */
    async loadConversation(conversationId = null) {
        try {
            const url = conversationId
                ? `/mindxagent/ollama/conversation?conversation_id=${encodeURIComponent(conversationId)}&limit=100`
                : '/mindxagent/ollama/conversation?limit=100';
            
            const conversation = await this.apiRequest(url);
            this.updateConversationDisplay(conversation);
            this.setData('conversation', conversation);
        } catch (error) {
            console.error('Failed to load conversation:', error);
            const displayEl = document.getElementById('mindxagent-ollama-conversation-display');
            if (displayEl) {
                displayEl.innerHTML = `
                    <div style="text-align: center; color: #ff0000; padding: 40px;">
                        <div style="font-size: 24px; margin-bottom: 10px;">❌</div>
                        <div>Failed to load conversation</div>
                        <div style="font-size: 11px; margin-top: 10px; color: #666;">${error.message}</div>
                    </div>
                `;
            }
        }
    }

    /**
     * Load thinking process
     */
    async loadThinking() {
        try {
            const result = await this.apiRequest('/mindxagent/thinking?limit=100');
            this.updateThinkingDisplay(result);
            this.setData('thinking', result);
        } catch (error) {
            console.error('Failed to load thinking:', error);
        }
    }

    /**
     * Load actions
     */
    async loadActions() {
        try {
            const result = await this.apiRequest('/mindxagent/actions?limit=50');
            this.updateActionsDisplay(result);
            this.setData('actions', result);
        } catch (error) {
            console.error('Failed to load actions:', error);
        }
    }

    /**
     * Clear conversation
     */
    async clearConversation() {
        try {
            await this.apiRequest('/mindxagent/ollama/conversation/clear', 'POST', {});
            await this.loadConversation();
        } catch (error) {
            console.error('Failed to clear conversation:', error);
            alert('Failed to clear conversation: ' + error.message);
        }
    }

    /**
     * Save settings
     */
    async saveSettings() {
        try {
            const settings = {
                autonomous_mode_enabled: document.getElementById('mindxagent-autonomous-enabled')?.checked || false,
                show_thinking_process: document.getElementById('mindxagent-show-thinking')?.checked || false,
                show_action_choices: document.getElementById('mindxagent-show-actions')?.checked || false,
                auto_apply_safe_improvements: document.getElementById('mindxagent-auto-apply')?.checked || false,
                model_selection_strategy: document.getElementById('mindxagent-model-strategy')?.value || 'best_for_task',
                improvement_cycle_interval: parseInt(document.getElementById('mindxagent-cycle-interval')?.value || '300')
            };

            await this.apiRequest('/mindxagent/settings', 'POST', settings);
            await this.loadStatus();
            console.log('✅ Settings saved');
        } catch (error) {
            console.error('Failed to save settings:', error);
            alert('Failed to save settings: ' + error.message);
        }
    }

    /**
     * Update status display
     * @param {Object} status - Status data
     */
    updateStatusDisplay(status) {
        // Core status
        const autonomousEl = document.getElementById('mindxagent-autonomous-status');
        const runningEl = document.getElementById('mindxagent-running-status');
        const modelEl = document.getElementById('mindxagent-model');
        const providerEl = document.getElementById('mindxagent-provider');

        if (autonomousEl) {
            autonomousEl.textContent = status.autonomous_mode ? '🟢 Enabled' : '🔴 Disabled';
            autonomousEl.className = `status-value status-badge ${status.autonomous_mode ? 'enabled' : 'disabled'}`;
        }
        if (runningEl) {
            runningEl.textContent = status.running ? '🟢 Running' : '🔴 Stopped';
            runningEl.className = `status-value status-badge ${status.running ? 'running' : 'stopped'}`;
        }
        if (modelEl) modelEl.textContent = status.model || '-';
        if (providerEl) providerEl.textContent = status.provider || '-';

        // Activity metrics
        const thinkingCountEl = document.getElementById('mindxagent-thinking-count');
        const actionsCountEl = document.getElementById('mindxagent-actions-count');
        const improvementsCountEl = document.getElementById('mindxagent-improvements-count');
        const activeAgentsEl = document.getElementById('mindxagent-active-agents');

        if (thinkingCountEl) thinkingCountEl.textContent = status.thinking_count || 0;
        if (actionsCountEl) actionsCountEl.textContent = status.actions_count || 0;
        if (improvementsCountEl) improvementsCountEl.textContent = status.improvements_count || 0;
        if (activeAgentsEl) activeAgentsEl.textContent = status.active_agents || 0;
    }

    /**
     * Update Ollama status display
     * @param {Object} ollamaStatus - Ollama status data
     */
    updateOllamaStatusDisplay(ollamaStatus) {
        const connectedEl = document.getElementById('mindxagent-ollama-connected');
        const urlEl = document.getElementById('mindxagent-ollama-url');
        const modelsCountEl = document.getElementById('mindxagent-ollama-models-count');
        const currentModelEl = document.getElementById('mindxagent-ollama-current-model');
        const conversationsEl = document.getElementById('mindxagent-ollama-conversations');

        if (connectedEl) {
            connectedEl.textContent = ollamaStatus.connected ? '🟢 Connected' : '🔴 Disconnected';
            connectedEl.style.color = ollamaStatus.connected ? '#00ff00' : '#ff0000';
        }
        if (urlEl) urlEl.textContent = ollamaStatus.base_url || '-';
        if (modelsCountEl) modelsCountEl.textContent = ollamaStatus.models_count || 0;
        if (currentModelEl) currentModelEl.textContent = ollamaStatus.current_model || '-';
        if (conversationsEl) conversationsEl.textContent = ollamaStatus.conversation_count || 0;
    }

    /**
     * Update conversation display
     * @param {Object} conversation - Conversation data
     */
    updateConversationDisplay(conversation) {
        // Use existing function from app.js if available
        if (typeof updateMindXagentOllamaConversationDisplay === 'function') {
            updateMindXagentOllamaConversationDisplay(conversation);
        } else {
            // Fallback implementation
            const displayEl = document.getElementById('mindxagent-ollama-conversation-display');
            if (!displayEl) return;

            if (!conversation.success || !conversation.messages || conversation.messages.length === 0) {
                displayEl.innerHTML = '<div class="empty-state">No conversation history</div>';
                return;
            }

            // Simple display
            displayEl.innerHTML = conversation.messages.map((msg, index) => {
                const role = msg.role || 'unknown';
                const content = msg.content || msg.message || '';
                return `
                    <div class="conversation-message ${role}">
                        <strong>${role}:</strong> ${content.substring(0, 200)}${content.length > 200 ? '...' : ''}
                    </div>
                `;
            }).join('');
        }
    }

    /**
     * Update thinking display
     * @param {Object} result - Thinking data
     */
    updateThinkingDisplay(result) {
        const displayEl = document.getElementById('mindxagent-thinking-display');
        if (!displayEl) return;

        if (!result.thinking || result.thinking.length === 0) {
            displayEl.innerHTML = '<p style="color: #888; font-style: italic;">No thinking steps yet</p>';
            return;
        }

        displayEl.innerHTML = result.thinking.map((step, index) => `
            <div class="thinking-step">
                <div class="thinking-step-header">
                    <span class="step-number">#${index + 1}</span>
                    <span class="step-timestamp">${step.timestamp ? new Date(step.timestamp).toLocaleString() : ''}</span>
                </div>
                <div class="thinking-step-content">${step.content || step.message || ''}</div>
            </div>
        `).join('');
    }

    /**
     * Update actions display
     * @param {Object} result - Actions data
     */
    updateActionsDisplay(result) {
        const displayEl = document.getElementById('mindxagent-actions-display');
        if (!displayEl) return;

        if (!result.actions || result.actions.length === 0) {
            displayEl.innerHTML = '<p style="color: #888; font-style: italic;">No actions yet</p>';
            return;
        }

        displayEl.innerHTML = result.actions.map((action, index) => `
            <div class="action-item">
                <div class="action-header">
                    <span class="action-number">#${index + 1}</span>
                    <span class="action-type">${action.type || 'unknown'}</span>
                    <span class="action-timestamp">${action.timestamp ? new Date(action.timestamp).toLocaleString() : ''}</span>
                </div>
                <div class="action-content">${action.description || action.content || ''}</div>
            </div>
        `).join('');
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.ollamaMonitor) {
            this.ollamaMonitor.destroy();
        }
        super.destroy();
    }
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.MindXagentTab = MindXagentTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = MindXagentTab;
}
