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
        this.interactionHistory = [];
        this.memoryLogs = [];
        this.processTraceEntries = [];
        this.godelChoices = [];
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

        // Load all data (including startup flow, logging from memory_agent)
        await Promise.all([
            this.loadStatus(),
            this.loadOllamaStatus(),
            this.loadStartup(),
            this.loadConversation(),
            this.loadThinking(),
            this.loadActions(),
            this.loadMemoryLogs(),
            this.loadProcessTrace(),
            this.loadGodelChoices()
        ]);

        // Start Ollama monitoring
        if (this.ollamaMonitor) {
            this.ollamaMonitor.startMonitoring();
        }

        // Initialize prompt status
        this.updatePromptStatus('Ready to inject prompt', 'ready');

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
            this.loadStartup(),
            this.loadConversation(),
            this.loadProcessTrace(),
            this.loadGodelChoices()
        ]);
    }

    /**
     * Load startup flow (startup_agent → mindXagent → Ollama)
     */
    async loadStartup() {
        try {
            const data = await this.apiRequest('/mindxagent/startup');
            this.updateStartupDisplay(data);
        } catch (error) {
            console.error('Failed to load startup flow:', error);
        }
    }

    /**
     * Update startup flow display (uses app.js updateMindXagentStartupDisplay if available)
     */
    updateStartupDisplay(data) {
        if (typeof updateMindXagentStartupDisplay === 'function') {
            updateMindXagentStartupDisplay(data);
        } else {
            const stepsEl = document.getElementById('mindxagent-startup-steps');
            if (stepsEl && data && data.success && data.startup_sequence && data.startup_sequence.length) {
                stepsEl.innerHTML = '<h4>Steps</h4><ul>' + data.startup_sequence.map(s => {
                    const status = s.status === 'completed' ? '✅' : s.status === 'skipped' ? '⏭' : '⏳';
                    return `<li>${status} ${s.name || ''}</li>`;
                }).join('') + '</ul>';
            }
        }
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

        // Interactive prompt controls
        const promptInput = document.getElementById('mindxagent-prompt-input');
        if (promptInput) {
            // Enter key handler for prompt input
            promptInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendPromptToMindXagent();
                }
            });
        }

        const sendPromptBtn = document.getElementById('mindxagent-send-prompt-btn');
        if (sendPromptBtn) {
            sendPromptBtn.addEventListener('click', () => this.sendPromptToMindXagent());
        }

        const clearPromptBtn = document.getElementById('mindxagent-clear-prompt-btn');
        if (clearPromptBtn) {
            clearPromptBtn.addEventListener('click', () => this.clearPromptInput());
        }

        // Memory logs controls
        const refreshMemoryBtn = document.getElementById('refresh-memory-logs-btn');
        if (refreshMemoryBtn) {
            refreshMemoryBtn.addEventListener('click', () => this.loadMemoryLogs());
        }

        const clearMemoryBtn = document.getElementById('clear-memory-logs-btn');
        if (clearMemoryBtn) {
            clearMemoryBtn.addEventListener('click', () => this.clearMemoryLogs());
        }

        // Logging (memory_agent) controls
        const refreshProcessTraceBtn = document.getElementById('refresh-mindxagent-process-trace-btn');
        if (refreshProcessTraceBtn) {
            refreshProcessTraceBtn.addEventListener('click', () => this.loadProcessTrace());
        }
        const refreshGodelBtn = document.getElementById('refresh-mindxagent-godel-choices-btn');
        if (refreshGodelBtn) {
            refreshGodelBtn.addEventListener('click', () => this.loadGodelChoices());
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
     * Send prompt to mindXagent for injection into Ollama conversation
     */
    async sendPromptToMindXagent() {
        const promptInput = document.getElementById('mindxagent-prompt-input');
        const statusEl = document.getElementById('mindxagent-prompt-status');
        const sendBtn = document.getElementById('mindxagent-send-prompt-btn');

        const prompt = promptInput?.value?.trim();
        if (!prompt) {
            this.updatePromptStatus('Please enter a prompt', 'warning');
            return;
        }

        // Update UI state
        this.updatePromptStatus('Sending prompt to mindXagent...', 'processing');
        if (sendBtn) sendBtn.disabled = true;
        if (promptInput) promptInput.disabled = true;

        try {
            // Send prompt to mindXagent
            const result = await this.apiRequest('/mindxagent/interact', 'POST', {
                prompt: prompt,
                source: 'ui_interaction',
                timestamp: new Date().toISOString()
            });

            // Log interaction to memory
            await this.logInteractionToMemory({
                type: 'prompt_injection',
                prompt: prompt,
                response: result.response || 'No response',
                timestamp: new Date().toISOString(),
                mindxagent_response: result
            });

            // Add to interaction history
            this.addToInteractionHistory({
                prompt: prompt,
                response: result.response || 'No response',
                timestamp: new Date().toISOString(),
                success: result.success !== false
            });

            // Clear input on success
            if (promptInput) promptInput.value = '';

            this.updatePromptStatus('Prompt injected successfully!', 'success');

            // Refresh conversation and memory logs
            await Promise.all([
                this.loadConversation(),
                this.loadMemoryLogs()
            ]);

        } catch (error) {
            console.error('Failed to send prompt to mindXagent:', error);
            this.updatePromptStatus(`Failed to inject prompt: ${error.message}`, 'error');

            // Log failed interaction
            this.addToInteractionHistory({
                prompt: prompt,
                error: error.message,
                timestamp: new Date().toISOString(),
                success: false
            });
        } finally {
            // Reset UI state
            if (sendBtn) sendBtn.disabled = false;
            if (promptInput) promptInput.disabled = false;
        }
    }

    /**
     * Clear prompt input field
     */
    clearPromptInput() {
        const promptInput = document.getElementById('mindxagent-prompt-input');
        if (promptInput) {
            promptInput.value = '';
            this.updatePromptStatus('Ready to inject prompt', 'ready');
        }
    }

    /**
     * Update prompt status display
     */
    updatePromptStatus(message, type = 'info') {
        const statusEl = document.getElementById('mindxagent-prompt-status');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `prompt-status-text status-${type}`;
        }
    }

    /**
     * Add interaction to history
     */
    addToInteractionHistory(interaction) {
        this.interactionHistory.unshift(interaction);
        if (this.interactionHistory.length > 50) {
            this.interactionHistory.pop();
        }
        this.updateInteractionHistoryDisplay();
    }

    /**
     * Update interaction history display
     */
    updateInteractionHistoryDisplay() {
        const container = document.getElementById('mindxagent-interaction-history');
        if (!container) return;

        if (this.interactionHistory.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📝</div>
                    <div class="empty-text">No prompt injections yet</div>
                    <div class="empty-hint">Use the input field above to inject prompts into mindXagent</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.interactionHistory.map((interaction, index) => `
            <div class="interaction-entry ${interaction.success ? 'success' : 'error'}">
                <div class="interaction-header">
                    <span class="interaction-index">#${index + 1}</span>
                    <span class="interaction-timestamp">${new Date(interaction.timestamp).toLocaleString()}</span>
                    <span class="interaction-status ${interaction.success ? 'success' : 'error'}">
                        ${interaction.success ? '✅ Success' : '❌ Failed'}
                    </span>
                </div>
                <div class="interaction-content">
                    <div class="interaction-prompt">
                        <strong>Prompt:</strong> ${this.escapeHtml(interaction.prompt)}
                    </div>
                    ${interaction.response ? `
                        <div class="interaction-response">
                            <strong>mindXagent Response:</strong> ${this.escapeHtml(interaction.response)}
                        </div>
                    ` : ''}
                    ${interaction.error ? `
                        <div class="interaction-error">
                            <strong>Error:</strong> ${this.escapeHtml(interaction.error)}
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Load process trace (memory_agent log_process → process_trace.jsonl)
     */
    async loadProcessTrace() {
        try {
            const result = await this.apiRequest('/mindxagent/logs/process?limit=80');
            this.processTraceEntries = result.entries || [];
            this.updateProcessTraceDisplay();
        } catch (error) {
            console.error('Failed to load process trace:', error);
            this.updateProcessTraceDisplay(true);
        }
    }

    /**
     * Update process trace display
     */
    updateProcessTraceDisplay(isError = false) {
        const container = document.getElementById('mindxagent-process-trace');
        if (!container) return;

        if (isError) {
            container.innerHTML = '<div class="empty-state">Failed to load process trace</div>';
            return;
        }
        const entries = this.processTraceEntries || [];
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-text">No process trace entries</div>
                    <div class="empty-hint">Written by memory_agent.log_process() under data/memory/agent_workspaces</div>
                </div>
            `;
            return;
        }

        container.innerHTML = entries.map((e, i) => {
            const ts = e.timestamp_utc || e.timestamp || '';
            const name = e.process_name || '';
            const meta = e.metadata || {};
            const data = e.process_data || e.data || {};
            const preview = typeof data === 'object' ? JSON.stringify(data).slice(0, 120) : String(data).slice(0, 120);
            return `
                <div class="process-trace-entry">
                    <div class="log-header">
                        <span class="log-timestamp">${ts ? new Date(ts).toLocaleString() : '-'}</span>
                        <span class="log-type">${this.escapeHtml(name)}</span>
                        ${meta.agent_id ? `<span class="log-meta">${this.escapeHtml(meta.agent_id)}</span>` : ''}
                    </div>
                    <div class="log-content">${this.escapeHtml(preview)}${(typeof data === 'object' ? JSON.stringify(data).length : String(data).length) > 120 ? '…' : ''}</div>
                </div>
            `;
        }).join('');
    }

    /**
     * Load Gödel choices for mindx_meta_agent
     */
    async loadGodelChoices() {
        try {
            const result = await this.apiRequest('/godel/choices?limit=50&source_agent=mindx_meta_agent');
            this.godelChoices = result.choices || [];
            this.updateGodelChoicesDisplay();
        } catch (error) {
            console.error('Failed to load Gödel choices:', error);
            this.updateGodelChoicesDisplay(true);
        }
    }

    /**
     * Update Gödel choices display
     */
    updateGodelChoicesDisplay(isError = false) {
        const container = document.getElementById('mindxagent-godel-choices');
        if (!container) return;

        if (isError) {
            container.innerHTML = '<div class="empty-state">Failed to load Gödel choices</div>';
            return;
        }
        const choices = this.godelChoices || [];
        if (choices.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-text">No Gödel choices for mindx_meta_agent</div>
                    <div class="empty-hint">From data/logs/godel_choices.jsonl</div>
                </div>
            `;
            return;
        }

        container.innerHTML = choices.map((c, i) => {
            const ts = c.timestamp_utc || c.timestamp || '';
            const source = c.source_agent || '';
            const kind = c.choice_type || c.event || 'choice';
            const rationale = c.rationale || c.reason || '';
            const outcome = c.outcome || c.result || '';
            const opt = c.chosen_option || c.option || '';
            return `
                <div class="godel-choice-entry">
                    <div class="log-header">
                        <span class="log-timestamp">${ts ? new Date(ts).toLocaleString() : '-'}</span>
                        <span class="log-type">${this.escapeHtml(kind)}</span>
                        ${source ? `<span class="log-meta">${this.escapeHtml(source)}</span>` : ''}
                    </div>
                    ${opt ? `<div class="log-content"><strong>Chosen:</strong> ${this.escapeHtml(String(opt).slice(0, 80))}${String(opt).length > 80 ? '…' : ''}</div>` : ''}
                    ${rationale ? `<div class="log-content"><strong>Rationale:</strong> ${this.escapeHtml(String(rationale).slice(0, 100))}${String(rationale).length > 100 ? '…' : ''}</div>` : ''}
                    ${outcome ? `<div class="log-content"><strong>Outcome:</strong> ${this.escapeHtml(String(outcome).slice(0, 80))}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    /**
     * Load memory logs (STM / timestamped memory from memory_agent)
     */
    async loadMemoryLogs() {
        try {
            const result = await this.apiRequest('/mindxagent/memory/logs?limit=50');
            this.memoryLogs = result.logs || [];
            this.updateMemoryLogsDisplay();
        } catch (error) {
            console.error('Failed to load memory logs:', error);
            this.memoryLogs = [];
            this.updateMemoryLogsDisplay();
        }
    }

    /**
     * Update memory logs display (API: timestamp ISO, memory_type, content_preview, tags, file)
     */
    updateMemoryLogsDisplay() {
        const container = document.getElementById('mindxagent-memory-logs');
        if (!container) return;

        if (!this.memoryLogs || this.memoryLogs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🧠</div>
                    <div class="empty-text">No memory logs yet</div>
                    <div class="empty-hint">Memory events from data/memory/stm will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.memoryLogs.map(log => {
            const ts = log.timestamp;
            const dateStr = ts ? (typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)).toLocaleString() : '-';
            const type = log.memory_type || log.type || 'memory';
            const content = log.content_preview || log.content || log.message || '';
            const tags = Array.isArray(log.tags) ? log.tags.join(', ') : '';
            return `
                <div class="memory-log-entry">
                    <div class="log-header">
                        <span class="log-timestamp">${dateStr}</span>
                        <span class="log-type">${this.escapeHtml(type)}</span>
                        ${tags ? `<span class="log-meta">${this.escapeHtml(tags)}</span>` : ''}
                    </div>
                    <div class="log-content">${this.escapeHtml(content)}</div>
                </div>
            `;
        }).join('');
    }

    /**
     * Clear memory logs
     */
    async clearMemoryLogs() {
        try {
            await this.apiRequest('/mindxagent/memory/logs/clear', 'POST', {});
            this.memoryLogs = [];
            this.updateMemoryLogsDisplay();
            console.log('✅ Memory logs cleared');
        } catch (error) {
            console.error('Failed to clear memory logs:', error);
            alert('Failed to clear memory logs: ' + error.message);
        }
    }

    /**
     * Log interaction to memory
     */
    async logInteractionToMemory(interactionData) {
        try {
            await this.apiRequest('/mindxagent/memory/log', 'POST', {
                type: 'ui_interaction',
                content: interactionData,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            console.warn('Failed to log interaction to memory:', error);
            // Don't show error to user as this is secondary functionality
        }
    }

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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

        // Activity metrics (from actual GET /mindxagent/status)
        const thinkingCountEl = document.getElementById('mindxagent-thinking-count');
        const actionsCountEl = document.getElementById('mindxagent-actions-count');
        const improvementsCountEl = document.getElementById('mindxagent-improvements-count');
        const activeAgentsEl = document.getElementById('mindxagent-active-agents');

        const thinkingCount = status.thinking_steps_count ?? status.thinking_count ?? 0;
        const actionsCount = status.action_choices_count ?? status.actions_count ?? 0;
        const improvementsCount = status.improvement_opportunities_count ?? status.improvements_count ?? 0;
        const activeAgents = (status.agent_knowledge && status.agent_knowledge.active_agents) ?? status.active_agents ?? 0;

        if (thinkingCountEl) thinkingCountEl.textContent = thinkingCount;
        if (actionsCountEl) actionsCountEl.textContent = actionsCount;
        if (improvementsCountEl) improvementsCountEl.textContent = improvementsCount;
        if (activeAgentsEl) activeAgentsEl.textContent = activeAgents;

        // Recent Action Choices (from actual status.recent_actions)
        const recentActionsEl = document.getElementById('mindxagent-recent-actions');
        if (recentActionsEl) {
            const recent = status.recent_actions || [];
            if (recent.length > 0) {
                recentActionsEl.innerHTML = recent.map((action) => {
                    const time = action.timestamp ? new Date(action.timestamp * 1000).toLocaleString() : '-';
                    return `
                        <div class="recent-item">
                            <div class="recent-item-header">
                                <div class="recent-item-title">${this.escapeHtml(action.context || 'Unknown')}</div>
                                <div class="recent-item-time">${time}</div>
                            </div>
                            <div class="recent-item-content">Selected: ${this.escapeHtml(action.selected || 'None')}</div>
                            <div class="recent-item-meta">Options: ${action.options_count ?? 0}</div>
                        </div>
                    `;
                }).join('');
            } else {
                recentActionsEl.innerHTML = '<div class="empty-state">No recent actions (from live mindXagent)</div>';
            }
        }

        // Recent Thinking Steps (from actual status.recent_thinking)
        const recentThinkingEl = document.getElementById('mindxagent-recent-thinking');
        if (recentThinkingEl) {
            const recent = status.recent_thinking || [];
            if (recent.length > 0) {
                recentThinkingEl.innerHTML = recent.map((thinking) => {
                    const time = thinking.timestamp ? new Date(thinking.timestamp * 1000).toLocaleString() : '-';
                    return `
                        <div class="recent-item">
                            <div class="recent-item-header">
                                <div class="recent-item-title">${this.escapeHtml(thinking.step || 'Unknown')}</div>
                                <div class="recent-item-time">${time}</div>
                            </div>
                            <div class="recent-item-content">${this.escapeHtml(thinking.thought_preview || '')}</div>
                        </div>
                    `;
                }).join('');
            } else {
                recentThinkingEl.innerHTML = '<div class="empty-state">No recent thinking steps (from live mindXagent)</div>';
            }
        }

        // Improvement Opportunities (from actual status.improvement_opportunities)
        const improvementsEl = document.getElementById('mindxagent-improvements');
        if (improvementsEl) {
            const opps = status.improvement_opportunities || [];
            if (opps.length > 0) {
                improvementsEl.innerHTML = opps.map((opp) => {
                    const type = opp.type || opp.opportunity || 'Unknown';
                    const desc = opp.description || (typeof opp.opportunity === 'string' ? opp.opportunity : '') || '';
                    const priority = opp.priority || '';
                    return `
                        <div class="recent-item">
                            <div class="recent-item-header">
                                <div class="recent-item-title">${this.escapeHtml(type)}</div>
                                ${priority ? `<span class="status-badge">${this.escapeHtml(priority)}</span>` : ''}
                            </div>
                            <div class="recent-item-content">${this.escapeHtml(desc)}</div>
                        </div>
                    `;
                }).join('');
            } else {
                improvementsEl.innerHTML = '<div class="empty-state">No improvement opportunities (from live mindXagent)</div>';
            }
        }
    }

    /**
     * Update Ollama status display
     * @param {Object} ollamaStatus - Ollama status data
     */
    updateOllamaStatusDisplay(ollamaStatus) {
        if (!ollamaStatus) return;
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
        const modelsCount = ollamaStatus.models_count ?? (Array.isArray(ollamaStatus.available_models) ? ollamaStatus.available_models.length : 0);
        if (modelsCountEl) modelsCountEl.textContent = modelsCount;
        if (currentModelEl) currentModelEl.textContent = ollamaStatus.current_model || '-';
        if (conversationsEl) conversationsEl.textContent = ollamaStatus.conversation_count ?? 0;
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
     * Update thinking display (from actual GET /mindxagent/thinking → thinking_process)
     */
    updateThinkingDisplay(result) {
        const displayEl = document.getElementById('mindxagent-thinking-display');
        if (!displayEl) return;

        const steps = result.thinking_process || result.thinking || [];
        if (steps.length === 0) {
            displayEl.innerHTML = '<p style="color: #888; font-style: italic;">No thinking steps yet (from GET /mindxagent/thinking)</p>';
            return;
        }

        displayEl.innerHTML = steps.map((step, index) => {
            const ts = step.timestamp ? (typeof step.timestamp === 'number' ? new Date(step.timestamp * 1000) : new Date(step.timestamp)).toLocaleString() : '';
            const content = step.thought || step.content || step.message || '';
            return `
                <div class="thinking-step">
                    <div class="thinking-step-header">
                        <span class="step-number">#${index + 1}</span>
                        <span class="step-timestamp">${ts}</span>
                    </div>
                    <div class="thinking-step-content">${this.escapeHtml(content)}</div>
                </div>
            `;
        }).join('');
    }

    /**
     * Update actions display (from actual GET /mindxagent/actions → action_choices)
     */
    updateActionsDisplay(result) {
        const displayEl = document.getElementById('mindxagent-actions-display');
        if (!displayEl) return;

        const actions = result.action_choices || result.actions || [];
        if (actions.length === 0) {
            displayEl.innerHTML = '<p style="color: #888; font-style: italic;">No actions yet (from GET /mindxagent/actions)</p>';
            return;
        }

        displayEl.innerHTML = actions.map((action, index) => {
            const ts = action.timestamp ? (typeof action.timestamp === 'number' ? new Date(action.timestamp * 1000) : new Date(action.timestamp)).toLocaleString() : '';
            const selected = action.selected && (typeof action.selected === 'object' ? action.selected.goal : action.selected) || action.description || action.content || '';
            const ctx = action.context || action.type || 'action';
            return `
                <div class="action-item">
                    <div class="action-header">
                        <span class="action-number">#${index + 1}</span>
                        <span class="action-type">${this.escapeHtml(ctx)}</span>
                        <span class="action-timestamp">${ts}</span>
                    </div>
                    <div class="action-content">${this.escapeHtml(selected)}</div>
                </div>
            `;
        }).join('');
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
