/**
 * Agents Tab Component
 * 
 * Detailed agent cards with iNFT/dNFT minting capabilities.
 * Focus on agent details including skills, capabilities, and metadata.
 * 
 * @module AgentsTab
 */

class AgentsTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'agents',
            label: 'Agents',
            group: 'main',
            refreshInterval: 15000, // 15 seconds
            autoRefresh: true,
            ...config
        });

        this.agents = [];
        this.selectedAgents = new Set();
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register data expression
        if (window.dataExpressions) {
            window.dataExpressions.registerExpression('agents', {
                endpoints: [
                    { url: '/agents', key: 'agents' },
                    { url: '/registry/agents', key: 'registry' },
                    { url: '/agents/activity', key: 'activity' }
                ],
                transform: (data) => ({
                    agents: data.data_0?.agents || data.data_0 || [],
                    registry: data.data_1 || {},
                    activity: data.data_2 || {}
                }),
                onUpdate: (data) => this.updateAgentsDisplay(data),
                cache: true
            });
        }

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        console.log('✅ AgentsTab initialized');
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
                const data = await window.dataExpressions.executeExpression('agents');
                if (data) {
                    this.updateAgentsDisplay(data);
                }
            } catch (error) {
                console.error('Failed to load agents tab data:', error);
                this.showError('Failed to load agents data', document.getElementById('agents-tab'));
            }
        } else {
            await this.loadDataFallback();
        }
    }

    /**
     * Fallback data loading
     */
    async loadDataFallback() {
        try {
            const agents = await this.apiRequest('/agents');
            const registry = await this.apiRequest('/registry/agents');
            
            this.updateAgentsDisplay({
                agents: agents?.agents || agents || [],
                registry: registry || {},
                activity: {}
            });
        } catch (error) {
            console.error('Error loading agents:', error);
            this.showError('Failed to load agents', document.getElementById('agents-tab'));
        }
    }

    /**
     * Update agents display
     * @param {Object} data - Agents data
     */
    updateAgentsDisplay(data) {
        this.agents = data.agents || [];
        this.renderAgentCards(this.agents, data.registry, data.activity);
    }

    /**
     * Render agent cards
     * @param {Array} agents - Agents list
     * @param {Object} registry - Agent registry
     * @param {Object} activity - Activity data
     */
    renderAgentCards(agents, registry = {}, activity = {}) {
        const container = document.getElementById('agents-list-container') || 
                         document.getElementById('agents-tab');
        
        if (!container) {
            console.error('Agents container not found');
            return;
        }

        // Create container if it doesn't exist
        let listContainer = document.getElementById('agents-list-container');
        if (!listContainer) {
            listContainer = document.createElement('div');
            listContainer.id = 'agents-list-container';
            listContainer.className = 'agents-grid';
            container.appendChild(listContainer);
        }

        if (!agents || agents.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🤖</div>
                    <div class="empty-text">No agents found</div>
                    <div class="empty-hint">Agents will appear here when registered</div>
                </div>
            `;
            return;
        }

        // Get activity data per agent
        const agentActivity = {};
        if (activity.activities) {
            activity.activities.forEach(act => {
                if (!agentActivity[act.agent]) {
                    agentActivity[act.agent] = [];
                }
                agentActivity[act.agent].push(act);
            });
        }

        listContainer.innerHTML = agents.map(agent => 
            this.createAgentCard(agent, registry[agent.agent_id] || {}, agentActivity[agent.agent_id] || [])
        ).join('');

        // Re-attach event listeners
        this.attachCardEventListeners();
    }

    /**
     * Create agent card HTML
     * @param {Object} agent - Agent data
     * @param {Object} registry - Registry data
     * @param {Array} activities - Activity data
     * @returns {string} HTML string
     */
    createAgentCard(agent, registry = {}, activities = []) {
        const agentId = agent.agent_id || agent.id || 'unknown';
        const agentName = agent.name || agent.agent_id || 'Unknown Agent';
        const agentType = agent.type || agent.agent_type || 'unknown';
        const status = agent.status || 'unknown';
        const description = agent.description || registry.description || 'No description available';
        
        // Extract skills and capabilities
        const skills = this.extractSkills(agent, registry);
        const capabilities = this.extractCapabilities(agent, registry);
        const metadata = this.extractMetadata(agent, registry);
        
        // Recent activity
        const recentActivity = activities.slice(0, 3);
        const lastActivity = activities.length > 0 ? activities[0] : null;

        return `
            <div class="agent-card" data-agent-id="${agentId}">
                <div class="agent-card-header">
                    <div class="agent-card-title">
                        <h3 class="agent-name">${this.escapeHtml(agentName)}</h3>
                        <span class="agent-type-badge ${agentType}">${agentType}</span>
                    </div>
                    <div class="agent-card-actions">
                        <button class="agent-action-btn mint-btn" data-agent-id="${agentId}" title="Mint as iNFT/dNFT">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                                <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
                            </svg>
                            Mint
                        </button>
                        <button class="agent-action-btn details-btn" data-agent-id="${agentId}" title="View Details">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <path d="M12 16v-4M12 8h.01"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="agent-card-body">
                    <div class="agent-status-section">
                        <div class="status-indicator ${status}"></div>
                        <span class="status-text">${status}</span>
                        ${lastActivity ? `
                            <span class="last-activity">Last active: ${this.formatTimestamp(lastActivity.timestamp)}</span>
                        ` : ''}
                    </div>

                    <div class="agent-description">
                        ${this.escapeHtml(description)}
                    </div>

                    ${skills.length > 0 ? `
                        <div class="agent-skills-section">
                            <h4 class="section-title">Skills</h4>
                            <div class="skills-list">
                                ${skills.map(skill => `
                                    <span class="skill-badge" data-skill="${skill.name}">
                                        ${this.escapeHtml(skill.name)}
                                        ${skill.level ? `<span class="skill-level">${skill.level}</span>` : ''}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${capabilities.length > 0 ? `
                        <div class="agent-capabilities-section">
                            <h4 class="section-title">Capabilities</h4>
                            <div class="capabilities-list">
                                ${capabilities.map(cap => `
                                    <div class="capability-item">
                                        <span class="capability-icon">${cap.icon || '⚡'}</span>
                                        <span class="capability-name">${this.escapeHtml(cap.name)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${metadata.stats ? `
                        <div class="agent-stats-section">
                            <h4 class="section-title">Statistics</h4>
                            <div class="stats-grid">
                                ${Object.entries(metadata.stats).map(([key, value]) => `
                                    <div class="stat-item">
                                        <span class="stat-label">${key}</span>
                                        <span class="stat-value">${value}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${recentActivity.length > 0 ? `
                        <div class="agent-activity-section">
                            <h4 class="section-title">Recent Activity</h4>
                            <div class="activity-list">
                                ${recentActivity.map(act => `
                                    <div class="activity-item ${act.type}">
                                        <span class="activity-time">${this.formatTimestamp(act.timestamp)}</span>
                                        <span class="activity-message">${this.escapeHtml(act.message || '')}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>

                <div class="agent-card-footer">
                    <div class="agent-metadata">
                        <span class="metadata-item">ID: ${agentId}</span>
                        ${metadata.created ? `<span class="metadata-item">Created: ${this.formatTimestamp(metadata.created)}</span>` : ''}
                    </div>
                    <div class="agent-card-controls">
                        <button class="agent-control-btn select-btn" data-agent-id="${agentId}">Select</button>
                        <button class="agent-control-btn view-btn" data-agent-id="${agentId}">View</button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Extract skills from agent data
     * @param {Object} agent - Agent data
     * @param {Object} registry - Registry data
     * @returns {Array} Skills array
     */
    extractSkills(agent, registry) {
        const skills = [];

        // Check various possible locations for skills
        if (agent.skills) {
            if (Array.isArray(agent.skills)) {
                skills.push(...agent.skills);
            } else if (typeof agent.skills === 'object') {
                skills.push(...Object.entries(agent.skills).map(([name, level]) => ({ name, level })));
            }
        }

        if (registry.skills) {
            if (Array.isArray(registry.skills)) {
                skills.push(...registry.skills);
            }
        }

        if (agent.capabilities) {
            skills.push(...agent.capabilities.map(cap => ({ name: cap, level: 'proficient' })));
        }

        // Extract from tools if available
        if (agent.tools) {
            agent.tools.forEach(tool => {
                skills.push({ name: tool, level: 'expert' });
            });
        }

        // Deduplicate
        const uniqueSkills = [];
        const seen = new Set();
        skills.forEach(skill => {
            const name = typeof skill === 'string' ? skill : skill.name;
            if (!seen.has(name)) {
                seen.add(name);
                uniqueSkills.push(typeof skill === 'string' ? { name: skill } : skill);
            }
        });

        return uniqueSkills;
    }

    /**
     * Extract capabilities from agent data
     * @param {Object} agent - Agent data
     * @param {Object} registry - Registry data
     * @returns {Array} Capabilities array
     */
    extractCapabilities(agent, registry) {
        const capabilities = [];

        if (agent.capabilities) {
            if (Array.isArray(agent.capabilities)) {
                capabilities.push(...agent.capabilities.map(cap => ({ name: cap })));
            }
        }

        if (registry.capabilities) {
            if (Array.isArray(registry.capabilities)) {
                capabilities.push(...registry.capabilities);
            }
        }

        // Map common agent types to capabilities
        const typeCapabilities = {
            'coordinator': [{ name: 'Task Orchestration', icon: '🎯' }, { name: 'Resource Management', icon: '📊' }],
            'memory': [{ name: 'Memory Management', icon: '🧠' }, { name: 'Context Retrieval', icon: '🔍' }],
            'guardian': [{ name: 'Security', icon: '🛡️' }, { name: 'Access Control', icon: '🔐' }],
            'mastermind': [{ name: 'Strategic Planning', icon: '🧩' }, { name: 'Code Generation', icon: '💻' }]
        };

        if (typeCapabilities[agent.type || agent.agent_type]) {
            capabilities.push(...typeCapabilities[agent.type || agent.agent_type]);
        }

        return capabilities;
    }

    /**
     * Extract metadata from agent data
     * @param {Object} agent - Agent data
     * @param {Object} registry - Registry data
     * @returns {Object} Metadata object
     */
    extractMetadata(agent, registry) {
        return {
            created: agent.created_at || agent.registered_at || registry.created_at,
            updated: agent.updated_at || registry.updated_at,
            stats: {
                'Tasks Completed': agent.tasks_completed || 0,
                'Success Rate': agent.success_rate ? `${(agent.success_rate * 100).toFixed(1)}%` : 'N/A',
                'Uptime': agent.uptime || 'N/A'
            },
            ...(agent.metadata || registry.metadata || {})
        };
    }

    /**
     * Attach event listeners to cards
     */
    attachCardEventListeners() {
        // Mint buttons
        document.querySelectorAll('.mint-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.handleMint(agentId);
            });
        });

        // Details buttons
        document.querySelectorAll('.details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.showAgentDetails(agentId);
            });
        });

        // Select buttons
        document.querySelectorAll('.select-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.toggleAgentSelection(agentId);
            });
        });

        // View buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.showAgentDetails(agentId);
            });
        });
    }

    /**
     * Handle mint action
     * @param {string} agentId - Agent ID
     */
    async handleMint(agentId) {
        const agent = this.agents.find(a => (a.agent_id || a.id) === agentId);
        if (!agent) {
            alert('Agent not found');
            return;
        }

        // Show minting dialog
        const mintType = confirm('Mint as iNFT (Interactive NFT) or dNFT (Dynamic NFT)?\n\nOK for iNFT, Cancel for dNFT');
        
        try {
            // Prepare minting data
            const mintData = {
                agent_id: agentId,
                agent_name: agent.name || agent.agent_id,
                agent_type: agent.type || agent.agent_type,
                skills: this.extractSkills(agent),
                capabilities: this.extractCapabilities(agent),
                metadata: this.extractMetadata(agent),
                nft_type: mintType ? 'iNFT' : 'dNFT'
            };

            // Call minting endpoint (if available)
            const result = await this.apiRequest('/agents/mint', 'POST', mintData);
            alert(`Agent ${agentId} minted successfully as ${mintData.nft_type}!`);
            console.log('Minting result:', result);
        } catch (error) {
            console.error('Minting error:', error);
            // For now, just show the data that would be minted
            alert(`Minting data prepared for ${agentId}:\n\n${JSON.stringify(mintData, null, 2)}`);
        }
    }

    /**
     * Show agent details
     * @param {string} agentId - Agent ID
     */
    showAgentDetails(agentId) {
        const agent = this.agents.find(a => (a.agent_id || a.id) === agentId);
        if (!agent) {
            alert('Agent not found');
            return;
        }

        // Create modal or navigate to details view
        const details = {
            ...agent,
            skills: this.extractSkills(agent),
            capabilities: this.extractCapabilities(agent),
            metadata: this.extractMetadata(agent)
        };

        console.log('Agent details:', details);
        // TODO: Open modal or navigate to detailed view
        alert(`Agent Details:\n\n${JSON.stringify(details, null, 2)}`);
    }

    /**
     * Toggle agent selection
     * @param {string} agentId - Agent ID
     */
    toggleAgentSelection(agentId) {
        if (this.selectedAgents.has(agentId)) {
            this.selectedAgents.delete(agentId);
        } else {
            this.selectedAgents.add(agentId);
        }

        // Update UI
        const card = document.querySelector(`[data-agent-id="${agentId}"]`);
        if (card) {
            if (this.selectedAgents.has(agentId)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        }
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-agents-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        // Create agent button
        const createBtn = document.getElementById('create-agent-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                // Navigate to agent creation
                console.log('Create agent clicked');
            });
        }
    }

    /**
     * Format timestamp
     * @param {number|string} timestamp - Timestamp
     * @returns {string} Formatted timestamp
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp);
        return date.toLocaleString();
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
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.AgentsTab = AgentsTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgentsTab;
}
