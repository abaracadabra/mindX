/**
 * Evolve Codebase Tab Component
 * 
 * Dedicated tab for codebase evolution with Ollama integration.
 * Provides real-time evolution progress and Ollama conversation feedback.
 * 
 * @module EvolveCodebaseTab
 */

class EvolveCodebaseTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'evolve-codebase',
            label: 'Evolve Codebase',
            group: 'core',
            refreshInterval: 5000, // 5 seconds
            autoRefresh: true,
            ...config
        });

        this.ollamaMonitor = null;
        this.evolutionInProgress = false;
        this.evolutionHistory = [];
        this.eventListenersAttached = false;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Initialize Ollama monitor for evolution feedback
        this.ollamaMonitor = new OllamaMonitor({
            containerId: 'evolve-ollama-monitor-container',
            endpoint: '/mindxagent/ollama',
            refreshInterval: 3000
        });

        console.log('✅ EvolveCodebaseTab initialized');
        return true;
    }

    /**
     * Activate the tab
     */
    async onActivate() {
        await super.onActivate();

        // Set up event listeners when tab is activated (DOM elements exist)
        this.setupEventListeners();

        // Load evolution status
        await this.loadEvolutionStatus();

        // Initialize Ollama monitor if container exists
        const monitorContainer = document.getElementById('evolve-ollama-monitor-container');
        if (monitorContainer && this.ollamaMonitor) {
            await this.ollamaMonitor.initialize();
            this.ollamaMonitor.startMonitoring();
        }

        this.registerComponent('ollamaMonitor', this.ollamaMonitor);

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
        await this.loadEvolutionStatus();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Prevent duplicate listeners
        if (this.eventListenersAttached) return;

        // Evolve button
        const evolveBtn = document.getElementById('evolve-tab-btn');
        if (evolveBtn) {
            evolveBtn.addEventListener('click', () => this.handleEvolve());
        }

        // Stop evolution button
        const stopBtn = document.getElementById('evolve-stop-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.handleStopEvolution());
        }

        // Clear history button
        const clearHistoryBtn = document.getElementById('evolve-clear-history-btn');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearEvolutionHistory());
        }

        // Enter key in directive input (textarea)
        const directiveInput = document.getElementById('evolve-tab-directive');
        if (directiveInput) {
            // Bind methods to preserve 'this' context
            this.handleKeyDown = (e) => {
                // Enter without Shift submits (Shift+Enter allows new line)
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleEvolve();
                }
            };
            
            this.handleKeyPress = (e) => {
                // Backup for Enter key detection
                if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleEvolve();
                }
            };

            directiveInput.addEventListener('keydown', this.handleKeyDown);
            directiveInput.addEventListener('keypress', this.handleKeyPress);
            
            console.log('✅ Evolve directive input event listeners attached');
        }

        this.eventListenersAttached = true;
    }

    /**
     * Load evolution status and API connections
     */
    async loadEvolutionStatus() {
        try {
            const status = await this.apiRequest('/system/status');
            this.updateEvolutionStatusDisplay(status);
            this.setData('evolutionStatus', status);

            // Also load API provider status
            await this.loadAPIProviderStatus();
        } catch (error) {
            console.error('Failed to load evolution status:', error);
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
        const apiStatusEl = document.getElementById('evolve-api-provider-status');
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
     * Handle evolve action - routes to mastermind agent with system analysis and LLM inference
     */
    async handleEvolve() {
        const directiveInput = document.getElementById('evolve-tab-directive');
        const directive = directiveInput?.value?.trim();

        if (!directive) {
            this.showNotification('Please enter a directive for evolution', 'warning');
            return;
        }

        // Prevent duplicate submissions
        if (this.evolutionInProgress) {
            console.log('Evolution already in progress, ignoring');
            return;
        }

        const maxCycles = parseInt(document.getElementById('evolve-tab-cycle-count')?.value || '8');
        const autonomous = document.getElementById('evolve-tab-autonomous-mode')?.checked || false;

        // Update UI state
        this.evolutionInProgress = true;
        this.updateEvolutionControlsState(true);

        // Add to history
        this.addToEvolutionHistory({
            directive,
            maxCycles,
            autonomous,
            timestamp: new Date().toISOString(),
            status: 'started',
            inference_source: 'Mastermind Agent with SystemAnalyzerTool LLM'
        });

        try {
            // Route to mastermind agent which uses SystemAnalyzerTool with LLM inference
            const result = await this.apiRequest('/commands/evolve', 'POST', {
                directive,
                max_cycles: maxCycles,
                autonomous_mode: autonomous
            });

            console.log('Evolution via Mastermind LLM inference started:', result);

            // Enhance result with inference details
            const enhancedResult = {
                ...result,
                inference_source: 'Mastermind Agent with SystemAnalyzerTool LLM',
                analysis_method: 'system_analyzer_with_llm_inference',
                timestamp: new Date().toISOString()
            };

            this.showNotification('Evolution started via Mastermind LLM inference', 'success');
            this.updateEvolutionProgress(enhancedResult);

            // Start polling for progress
            this.startProgressPolling();

        } catch (error) {
            console.error('Evolution LLM inference error:', error);
            this.showNotification(`Failed to start evolution: ${error.message}`, 'error');
            this.evolutionInProgress = false;
            this.updateEvolutionControlsState(false);
        }
    }

    /**
     * Handle stop evolution
     */
    async handleStopEvolution() {
        try {
            await this.apiRequest('/commands/stop', 'POST', {});
            this.evolutionInProgress = false;
            this.updateEvolutionControlsState(false);
            this.showNotification('Evolution stopped', 'info');
        } catch (error) {
            console.error('Failed to stop evolution:', error);
            this.showNotification(`Failed to stop: ${error.message}`, 'error');
        }
    }

    /**
     * Start polling for evolution progress
     */
    startProgressPolling() {
        const pollInterval = setInterval(async () => {
            if (!this.evolutionInProgress) {
                clearInterval(pollInterval);
                return;
            }

            try {
                const status = await this.apiRequest('/system/status');
                this.updateEvolutionProgress(status);

                // Check if evolution is complete
                if (!status.evolution_active) {
                    this.evolutionInProgress = false;
                    this.updateEvolutionControlsState(false);
                    this.showNotification('Evolution completed', 'success');
                    clearInterval(pollInterval);
                }
            } catch (error) {
                console.error('Error polling evolution progress:', error);
            }
        }, 3000);
    }

    /**
     * Update evolution controls state
     * @param {boolean} inProgress - Whether evolution is in progress
     */
    updateEvolutionControlsState(inProgress) {
        const evolveBtn = document.getElementById('evolve-tab-btn');
        const stopBtn = document.getElementById('evolve-stop-btn');
        const directiveInput = document.getElementById('evolve-tab-directive');
        const cycleInput = document.getElementById('evolve-tab-cycle-count');
        const autonomousCheckbox = document.getElementById('evolve-tab-autonomous-mode');

        if (evolveBtn) {
            evolveBtn.disabled = inProgress;
            evolveBtn.textContent = inProgress ? 'Evolving...' : 'Evolve';
            evolveBtn.classList.toggle('evolving', inProgress);
        }

        if (stopBtn) {
            stopBtn.style.display = inProgress ? 'inline-block' : 'none';
        }

        if (directiveInput) directiveInput.disabled = inProgress;
        if (cycleInput) cycleInput.disabled = inProgress;
        if (autonomousCheckbox) autonomousCheckbox.disabled = inProgress;
    }

    /**
     * Update evolution status display
     * @param {Object} status - Status data
     */
    updateEvolutionStatusDisplay(status) {
        const statusEl = document.getElementById('evolve-status-indicator');
        const activeEl = document.getElementById('evolve-active-status');
        const cycleEl = document.getElementById('evolve-current-cycle');
        const lastDirectiveEl = document.getElementById('evolve-last-directive');

        if (statusEl) {
            const isActive = status.evolution_active || status.active || false;
            statusEl.className = `status-indicator ${isActive ? 'active' : 'inactive'}`;
            statusEl.textContent = isActive ? '🟢 Active' : '🔴 Idle';
        }

        if (activeEl) {
            activeEl.textContent = status.evolution_active ? 'Running' : 'Stopped';
        }

        if (cycleEl) {
            cycleEl.textContent = status.current_cycle || '0';
        }

        if (lastDirectiveEl && status.last_directive) {
            lastDirectiveEl.textContent = status.last_directive.substring(0, 100) + (status.last_directive.length > 100 ? '...' : '');
        }
    }

    /**
     * Update evolution progress display
     * @param {Object} progress - Progress data
     */
    updateEvolutionProgress(progress) {
        const progressEl = document.getElementById('evolve-progress-display');
        if (!progressEl) return;

        const cycle = progress.current_cycle || progress.cycle || 0;
        const maxCycles = progress.max_cycles || 8;
        const percentage = Math.round((cycle / maxCycles) * 100);

        progressEl.innerHTML = `
            <div class="evolution-progress">
                <div class="progress-header">
                    <span class="progress-label">Evolution Progress</span>
                    <span class="progress-value">${cycle}/${maxCycles} cycles</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${percentage}%"></div>
                </div>
                <div class="progress-details">
                    <div class="detail-item">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value ${progress.status || 'pending'}">${progress.status || 'In Progress'}</span>
                    </div>
                    ${progress.current_action ? `
                        <div class="detail-item">
                            <span class="detail-label">Current Action:</span>
                            <span class="detail-value">${progress.current_action}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Add to evolution history
     * @param {Object} entry - History entry
     */
    addToEvolutionHistory(entry) {
        this.evolutionHistory.unshift(entry);
        if (this.evolutionHistory.length > 20) {
            this.evolutionHistory.pop();
        }
        this.updateEvolutionHistoryDisplay();
    }

    /**
     * Update evolution history display
     */
    updateEvolutionHistoryDisplay() {
        const historyEl = document.getElementById('evolve-history-list');
        if (!historyEl) return;

        if (this.evolutionHistory.length === 0) {
            historyEl.innerHTML = '<div class="empty-state">No evolution history yet</div>';
            return;
        }

        historyEl.innerHTML = this.evolutionHistory.map((entry, index) => `
            <div class="history-entry ${entry.status}">
                <div class="history-header">
                    <span class="history-index">#${index + 1}</span>
                    <span class="history-time">${new Date(entry.timestamp).toLocaleString()}</span>
                    <span class="history-status ${entry.status}">${entry.status}</span>
                </div>
                <div class="history-directive">${entry.directive.substring(0, 80)}${entry.directive.length > 80 ? '...' : ''}</div>
                <div class="history-meta">
                    <span>Cycles: ${entry.maxCycles}</span>
                    <span>Autonomous: ${entry.autonomous ? 'Yes' : 'No'}</span>
                </div>
            </div>
        `).join('');
    }

    /**
     * Clear evolution history
     */
    clearEvolutionHistory() {
        this.evolutionHistory = [];
        this.updateEvolutionHistoryDisplay();
        this.showNotification('History cleared', 'info');
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type
     */
    showNotification(message, type = 'info') {
        const notificationEl = document.getElementById('evolve-notification');
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
    window.EvolveCodebaseTab = EvolveCodebaseTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = EvolveCodebaseTab;
}
