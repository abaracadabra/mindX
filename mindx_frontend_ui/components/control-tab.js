/**
 * Control Tab Component
 * 
 * Home/return tab for mindX control interface.
 * 
 * @module ControlTab
 */

class ControlTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'control',
            label: 'Control',
            group: 'main',
            refreshInterval: 10000, // 10 seconds
            autoRefresh: false,
            ...config
        });
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register data expression
        if (window.dataExpressions) {
            window.dataExpressions.registerExpression('control', {
                endpoints: [
                    { url: '/system/status', key: 'systemStatus' },
                    { url: '/github/status', key: 'githubStatus' },
                    { url: '/simple-coder/update-requests', key: 'updateRequests' }
                ],
                transform: (data) => ({
                    system: data.data_0,
                    github: data.data_1,
                    updates: data.data_2 || []
                }),
                onUpdate: (data) => this.updateDisplay(data),
                cache: true
            });
        }

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        console.log('✅ ControlTab initialized');
        return true;
    }

    /**
     * Activate the tab
     */
    async onActivate() {
        await super.onActivate();
        await this.loadData();
        return true;
    }

    /**
     * Load tab data
     */
    async loadData() {
        if (window.dataExpressions) {
            try {
                const data = await window.dataExpressions.executeExpression('control');
                if (data) {
                    this.updateDisplay(data);
                }
            } catch (error) {
                console.error('Failed to load control tab data:', error);
                this.showError('Failed to load data', document.getElementById('control-tab'));
            }
        } else {
            // Fallback to direct API calls
            await this.loadDataFallback();
        }
    }

    /**
     * Fallback data loading
     */
    async loadDataFallback() {
        try {
            // Load system status
            const systemStatus = await this.apiRequest('/system/status');
            this.updateSystemStatus(systemStatus);

            // Load GitHub status
            try {
                const githubStatus = await this.apiRequest('/github/status');
                this.updateGitHubStatus(githubStatus);
            } catch (error) {
                console.warn('GitHub status not available:', error);
            }

            // Load update requests
            try {
                const updates = await this.apiRequest('/simple-coder/update-requests');
                this.updateUpdateRequests(updates || []);
            } catch (error) {
                console.warn('Update requests not available:', error);
            }
        } catch (error) {
            console.error('Error loading control tab data:', error);
        }
    }

    /**
     * Update display with data
     * @param {Object} data - Data object
     */
    updateDisplay(data) {
        if (data.system) {
            this.updateSystemStatus(data.system);
        }
        if (data.github) {
            this.updateGitHubStatus(data.github);
        }
        if (data.updates) {
            this.updateUpdateRequests(data.updates);
        }
    }

    /**
     * Update system status display
     * @param {Object} status - System status
     */
    updateSystemStatus(status) {
        // System status is already displayed in header, but we can add more details
        console.log('System status:', status);
    }

    /**
     * Update GitHub status display
     * @param {Object} status - GitHub status
     */
    updateGitHubStatus(status) {
        const displayEl = document.getElementById('github-status-display');
        if (!displayEl) return;

        if (status && status.status) {
            displayEl.innerHTML = `
                <div class="status-item">
                    <span class="status-label">Status:</span>
                    <span class="status-value ${status.status === 'connected' ? 'success' : 'error'}">${status.status}</span>
                </div>
                ${status.repository ? `
                    <div class="status-item">
                        <span class="status-label">Repository:</span>
                        <span class="status-value">${status.repository}</span>
                    </div>
                ` : ''}
                ${status.last_backup ? `
                    <div class="status-item">
                        <span class="status-label">Last Backup:</span>
                        <span class="status-value">${new Date(status.last_backup).toLocaleString()}</span>
                    </div>
                ` : ''}
            `;
        } else {
            displayEl.innerHTML = '<p>GitHub agent not configured</p>';
        }
    }

    /**
     * Update update requests display
     * @param {Array} requests - Update requests
     */
    updateUpdateRequests(requests) {
        const container = document.getElementById('update-requests-container');
        if (!container) return;

        if (!requests || requests.length === 0) {
            container.innerHTML = '<p style="color: #888; padding: 20px; text-align: center;">No pending update requests</p>';
            return;
        }

        container.innerHTML = requests.map((request, index) => `
            <div class="update-request" data-request-id="${request.request_id}">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <input type="checkbox" class="update-checkbox" data-request-id="${request.request_id}" style="margin-right: 10px;">
                    <h4 style="margin: 0; flex: 1;">Update Request ${index + 1}: ${request.request_id}</h4>
                    <span class="status-badge ${request.status}">${request.status}</span>
                </div>
                <p><strong>Original File:</strong> ${request.original_file || 'N/A'}</p>
                <p><strong>Sandbox File:</strong> ${request.sandbox_file || 'N/A'}</p>
                <p><strong>Cycle:</strong> ${request.cycle || 'N/A'}</p>
                <p><strong>Changes:</strong> ${request.changes ? request.changes.length : 0} modifications</p>
                <p><strong>Timestamp:</strong> ${request.timestamp ? new Date(request.timestamp).toLocaleString() : 'N/A'}</p>
                <div style="margin-top: 10px;">
                    <button onclick="approveUpdate('${request.request_id}')" class="action-btn success">Approve</button>
                    <button onclick="rejectUpdate('${request.request_id}')" class="action-btn danger">Reject</button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Section tabs
        const sectionTabs = document.querySelectorAll('[data-section]');
        sectionTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const section = tab.getAttribute('data-section');
                this.switchSection(section);
            });
        });

        // Refresh buttons
        const refreshBtn = document.getElementById('refresh-github-status-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const refreshUpdatesBtn = document.getElementById('refresh-updates-btn');
        if (refreshUpdatesBtn) {
            refreshUpdatesBtn.addEventListener('click', () => this.loadData());
        }

        // Evolve button
        const evolveBtn = document.getElementById('evolve-btn');
        if (evolveBtn) {
            evolveBtn.addEventListener('click', () => this.handleEvolve());
        }

        // Query button
        const queryBtn = document.getElementById('query-btn');
        if (queryBtn) {
            queryBtn.addEventListener('click', () => this.handleQuery());
        }
    }

    /**
     * Switch section
     * @param {string} sectionId - Section ID
     */
    switchSection(sectionId) {
        // Update tab buttons
        document.querySelectorAll('[data-section]').forEach(btn => {
            btn.classList.remove('active');
        });
        const activeBtn = document.querySelector(`[data-section="${sectionId}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        // Update section content
        document.querySelectorAll('.section-content').forEach(section => {
            section.classList.remove('active');
        });
        const activeSection = document.getElementById(`${sectionId}-section`);
        if (activeSection) activeSection.classList.add('active');
    }

    /**
     * Handle evolve action
     */
    async handleEvolve() {
        const directive = document.getElementById('evolve-directive')?.value;
        if (!directive) {
            alert('Please enter a directive');
            return;
        }

        const maxCycles = parseInt(document.getElementById('cycle-count')?.value || '8');
        const autonomous = document.getElementById('evolve-autonomous-mode')?.checked || false;

        try {
            const result = await this.apiRequest('/directive', 'POST', {
                directive,
                max_cycles: maxCycles,
                autonomous_mode: autonomous
            });
            console.log('Evolve result:', result);
            alert('Evolution started successfully');
        } catch (error) {
            console.error('Evolve error:', error);
            alert('Failed to start evolution: ' + error.message);
        }
    }

    /**
     * Handle query action
     */
    async handleQuery() {
        const query = document.getElementById('query-input')?.value;
        if (!query) {
            alert('Please enter a query');
            return;
        }

        try {
            const result = await this.apiRequest('/coordinator/query', 'POST', { query });
            console.log('Query result:', result);
            // Display result in query section
            const querySection = document.getElementById('query-section');
            if (querySection) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'query-result';
                resultDiv.innerHTML = `<pre>${JSON.stringify(result, null, 2)}</pre>`;
                querySection.appendChild(resultDiv);
            }
        } catch (error) {
            console.error('Query error:', error);
            alert('Failed to send query: ' + error.message);
        }
    }
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.ControlTab = ControlTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ControlTab;
}
