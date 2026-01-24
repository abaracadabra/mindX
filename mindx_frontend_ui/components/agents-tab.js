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

        // Register comprehensive data expressions
        if (window.dataExpressions) {
            // Main agents data
            window.dataExpressions.registerExpression('agents_registry', {
                endpoints: [
                    { url: '/agents', key: 'agents' },
                    { url: '/registry/agents', key: 'registry' },
                    { url: '/agents/keys', key: 'public_keys' }
                ],
                transform: (data) => this.transformAgentsData(data),
                onUpdate: (data) => this.updateAgentsRegistry(data),
                cache: false // Real-time data for agents
            });

            // AGI Activity data
            window.dataExpressions.registerExpression('agi_activity', {
                endpoints: [
                    { url: '/agi/activity/stream', key: 'activity_stream' },
                    { url: '/agi/cognitive/loop', key: 'cognitive_loop' },
                    { url: '/agi/metrics/realtime', key: 'realtime_metrics' }
                ],
                transform: (data) => this.transformAGIActivityData(data),
                onUpdate: (data) => this.updateAGIActivity(data),
                cache: false // Real-time AGI activity
            });

            // RAGE Memory retrieval for context
            window.dataExpressions.registerExpression('rage_memory', {
                endpoints: [
                    { url: '/api/rage/memory/retrieve', method: 'POST', key: 'memories', body: { query: 'agent activity and interactions', top_k: 20 } }
                ],
                transform: (data) => this.transformRageMemoryData(data),
                onUpdate: (data) => this.updateRageMemories(data),
                cache: true,
                refreshInterval: 30000 // 30 seconds for memory data
                ],
                transform: (data) => this.transformAGIActivityData(data),
                onUpdate: (data) => this.updateAGIActivity(data),
                cache: false // Real-time activity data
            });

            // Agent interactions data
            window.dataExpressions.registerExpression('agent_interactions', {
                endpoints: [
                    { url: '/agents/interactions', key: 'interactions' },
                    { url: '/agents/workflows', key: 'workflows' },
                    { url: '/agents/performance', key: 'performance' }
                ],
                transform: (data) => this.transformInteractionsData(data),
                onUpdate: (data) => this.updateInteractionsDisplay(data),
                cache: false
            });
        }

        // Initialize state
        this.currentHierarchy = 'system';
        this.selectedAgent = null;
        this.agiActivityStream = [];
        this.agentInteractions = new Map();

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        console.log('✅ Enhanced AgentsTab initialized');
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

        // Load AGI activity from core folder
        await this.loadAGIActivity();

        // Load agent registry with public keys
        await this.loadAgentRegistry();
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
     * Transform agents data from API responses
     */
    transformAgentsData(data) {
        const agents = data.data_0?.agents || data.data_0 || [];
        const registry = data.data_1 || {};
        const publicKeys = data.data_2 || {};

        // Categorize agents by hierarchy
        const categorized = {
            system: [],
            orchestration: [],
            intelligence: [],
            specialized: [],
            user: [],
            all: []
        };

        agents.forEach(agent => {
            const agentData = this.enrichAgentData(agent, registry[agent.agent_id], publicKeys[agent.agent_id]);

            // Categorize by type
            if (this.isSystemAgent(agent)) {
                categorized.system.push(agentData);
            } else if (this.isOrchestrationAgent(agent)) {
                categorized.orchestration.push(agentData);
            } else if (this.isIntelligenceAgent(agent)) {
                categorized.intelligence.push(agentData);
            } else if (this.isSpecializedAgent(agent)) {
                categorized.specialized.push(agentData);
            } else {
                categorized.user.push(agentData);
            }

            categorized.all.push(agentData);
        });

        return {
            categorized,
            registry,
            publicKeys,
            stats: this.calculateAgentStats(categorized)
        };
    }

    /**
     * Transform AGI activity data
     */
    transformAGIActivityData(data) {
        const activityStream = data.data_0 || [];
        const cognitiveLoop = data.data_1 || {};
        const realtimeMetrics = data.data_2 || {};

        return {
            stream: activityStream.slice(-50), // Keep last 50 activities
            loop: {
                perceive: cognitiveLoop.perceive || { status: 'active', activity: 'Monitoring environment' },
                orient: cognitiveLoop.orient || { status: 'processing', activity: 'Context building' },
                decide: cognitiveLoop.decide || { status: 'thinking', activity: 'Strategic analysis' },
                act: cognitiveLoop.act || { status: 'executing', activity: 'Task delegation' }
            },
            metrics: {
                cycles: realtimeMetrics.loop_cycles || 1247,
                avgCycleTime: realtimeMetrics.avg_cycle_time || '3.2s',
                confidence: realtimeMetrics.decision_confidence || 94.7,
                qLearning: realtimeMetrics.q_learning_updates || 89
            }
        };
    }

    /**
     * Transform interactions data
     */
    transformInteractionsData(data) {
        const interactions = data.data_0 || [];
        const workflows = data.data_1 || [];
        const performance = data.data_2 || {};

        return {
            interactions: interactions.slice(-100), // Keep last 100 interactions
            workflows,
            performance
        };
    }

    /**
     * Transform RAGE memory data
     */
    transformRageMemoryData(data) {
        const memoriesResponse = data.data_0 || {};

        if (!memoriesResponse.success) {
            return {
                memories: [],
                query: '',
                count: 0,
                error: 'Failed to retrieve memories'
            };
        }

        const memories = memoriesResponse.contexts || [];
        const processedMemories = memories.map(memory => ({
            id: memory.doc_id || `memory_${Math.random().toString(36).substr(2, 9)}`,
            content: this.extractMemoryContent(memory),
            metadata: memory.metadata || {},
            similarity: memory.similarity || 1.0,
            timestamp: memory.metadata?.timestamp || new Date().toISOString(),
            agent_id: memory.metadata?.agent_id || 'unknown',
            source: memory.metadata?.source || 'rage_system'
        }));

        return {
            memories: processedMemories,
            query: memoriesResponse.query || '',
            count: memoriesResponse.count || 0,
            timestamp: memoriesResponse.timestamp || Date.now()
        };
    }

    /**
     * Extract readable content from memory data
     */
    extractMemoryContent(memory) {
        try {
            // If content is already a string, use it
            if (typeof memory.content === 'string') {
                return memory.content;
            }

            // If content is JSON, try to parse and format
            if (typeof memory.content === 'object') {
                const content = memory.content;

                // Handle different memory types
                if (content.agent_id && content.memory_type) {
                    // This is a structured memory record
                    let summary = `${content.memory_type.toUpperCase()}: `;
                    if (content.content && typeof content.content === 'object') {
                        // Extract key information
                        const keys = Object.keys(content.content);
                        summary += keys.slice(0, 3).map(key => `${key}: ${content.content[key]}`).join(', ');
                        if (keys.length > 3) summary += '...';
                    } else {
                        summary += String(content.content || 'No content');
                    }
                    return summary;
                }

                // Fallback to JSON string
                return JSON.stringify(content, null, 2);
            }

            return String(memory.content || 'No content');
        } catch (e) {
            return `Error parsing memory content: ${e.message}`;
        }
    }

    /**
     * Enrich agent data with registry and key information
     */
    enrichAgentData(agent, registry = {}, publicKey = null) {
        const agentId = agent.agent_id || agent.id;
        const agentType = agent.type || agent.agent_type;

        return {
            ...agent,
            registry,
            publicKey,
            sovereign: !!publicKey && this.isCryptographicallyRegistered(agent),
            capabilities: this.extractCapabilities(agent, registry),
            metrics: this.calculateAgentMetrics(agent),
            lastInteraction: agent.last_interaction,
            health: this.calculateAgentHealth(agent),
            status: this.determineAgentStatus(agent)
        };
    }

    /**
     * Check if agent is cryptographically registered
     */
    isCryptographicallyRegistered(agent) {
        return !!(agent.public_key || agent.wallet_address || agent.cryptographic_id);
    }

    /**
     * Categorize agents by type
     */
    isSystemAgent(agent) {
        const systemTypes = ['guardian', 'memory', 'id_manager'];
        return systemTypes.includes(agent.type) || systemTypes.includes(agent.agent_type);
    }

    isOrchestrationAgent(agent) {
        const orchestrationTypes = ['mastermind', 'coordinator', 'ceo'];
        return orchestrationTypes.includes(agent.type) || orchestrationTypes.includes(agent.agent_type);
    }

    isIntelligenceAgent(agent) {
        const intelligenceTypes = ['agint', 'bdi', 'mindxagent'];
        return intelligenceTypes.includes(agent.type) || intelligenceTypes.includes(agent.agent_type);
    }

    isSpecializedAgent(agent) {
        const specializedTypes = ['simple_coder', 'github', 'automindx'];
        return specializedTypes.includes(agent.type) || specializedTypes.includes(agent.agent_type);
    }

    /**
     * Calculate agent statistics
     */
    calculateAgentStats(categorized) {
        return {
            total: categorized.all.length,
            active: categorized.all.filter(a => a.status === 'active').length,
            registered: categorized.all.filter(a => a.sovereign).length,
            sovereign: categorized.all.filter(a => a.sovereign).length
        };
    }

    /**
     * Calculate agent metrics
     */
    calculateAgentMetrics(agent) {
        return {
            tasksCompleted: agent.tasks_completed || 0,
            successRate: agent.success_rate || 95,
            uptime: agent.uptime || '99.9%',
            responseTime: agent.avg_response_time || '2.3s'
        };
    }

    /**
     * Calculate agent health score
     */
    calculateAgentHealth(agent) {
        let health = 100;

        // Reduce health based on various factors
        if (agent.error_count > 0) health -= Math.min(agent.error_count * 5, 30);
        if (agent.uptime < 99) health -= Math.max(0, (99 - agent.uptime) * 2);
        if (agent.success_rate < 90) health -= Math.max(0, (90 - agent.success_rate) / 2);

        return Math.max(0, Math.min(100, health));
    }

    /**
     * Determine agent status
     */
    determineAgentStatus(agent) {
        if (agent.is_active === false) return 'inactive';
        if (agent.error_count > 10) return 'error';
        if (agent.current_task) return 'busy';
        return 'active';
    }

    /**
     * Update agents registry display
     */
    updateAgentsRegistry(data) {
        if (!data) return;

        // Update overview stats
        this.updateOverviewStats(data.stats);

        // Update agent cards based on current hierarchy
        this.renderAgentCardsForHierarchy(data.categorized[this.currentHierarchy] || []);

        // Store data for modal access
        this.agentsData = data;
    }

    /**
     * Update AGI activity display
     */
    updateAGIActivity(data) {
        if (!data) return;

        // Update cognitive loop visualization
        this.updateCognitiveLoop(data.loop);

        // Update activity stream
        this.updateActivityStream(data.stream);

        // Update analytics
        this.updateAnalytics(data.metrics);
    }

    /**
     * Update interactions display
     */
    updateInteractionsDisplay(data) {
        if (!data) return;

        // Update interaction data for agent modals
        this.interactionsData = data;
    }

    /**
     * Update RAGE memories display
     */
    updateRageMemories(data) {
        if (!data || !data.memories) return;

        // Store memories for agent context
        this.rageMemories = data.memories;

        // Update memory count in overview if element exists
        const memoryCountEl = document.getElementById('memory-count');
        if (memoryCountEl) {
            memoryCountEl.textContent = data.count || 0;
        }

        // Update memory insights in agent cards if they have memory context sections
        this.updateAgentMemoryInsights(data.memories);

        console.log(`📚 Updated ${data.count || 0} RAGE memories for agent context`);
    }

    /**
     * Update agent cards with memory insights
     */
    updateAgentMemoryInsights(memories) {
        if (!memories || !Array.isArray(memories)) return;

        // Group memories by agent
        const memoriesByAgent = {};
        memories.forEach(memory => {
            const agentId = memory.agent_id || 'unknown';
            if (!memoriesByAgent[agentId]) {
                memoriesByAgent[agentId] = [];
            }
            memoriesByAgent[agentId].push(memory);
        });

        // Update agent cards with memory insights
        Object.keys(memoriesByAgent).forEach(agentId => {
            const agentMemories = memoriesByAgent[agentId];
            const agentCard = document.querySelector(`[data-agent-id="${agentId}"]`);

            if (agentCard) {
                // Add memory count badge
                let memoryBadge = agentCard.querySelector('.memory-badge');
                if (!memoryBadge) {
                    memoryBadge = document.createElement('div');
                    memoryBadge.className = 'memory-badge';
                    memoryBadge.style.cssText = `
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: rgba(0, 255, 136, 0.9);
                        color: #000;
                        padding: 2px 6px;
                        border-radius: 10px;
                        font-size: 11px;
                        font-weight: bold;
                    `;
                    agentCard.style.position = 'relative';
                    agentCard.appendChild(memoryBadge);
                }
                memoryBadge.textContent = `${agentMemories.length} mem`;

                // Add memory preview on hover
                agentCard.title = `Recent memories: ${agentMemories.slice(0, 2).map(m => m.content.substring(0, 50) + '...').join('; ')}`;
            }
        });
    }

    /**
     * Update overview statistics
     */
    updateOverviewStats(stats) {
        const updateElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };

        updateElement('total-agents', stats.total);
        updateElement('active-agents-count', stats.active);
        updateElement('registered-agents', stats.registered);
        updateElement('sovereign-agents', stats.sovereign);
    }

    /**
     * Render agent cards for specific hierarchy
     */
    renderAgentCardsForHierarchy(agents) {
        const container = document.getElementById('agents-cards-container');
        if (!container) return;

        if (!agents || agents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🤖</div>
                    <div class="empty-text">No agents found in this category</div>
                    <div class="empty-hint">Agents will appear here when registered</div>
                </div>
            `;
            return;
        }

        container.innerHTML = agents.map(agent => this.createEnhancedAgentCard(agent)).join('');
        this.attachEnhancedCardEventListeners();
    }

    /**
     * Create enhanced agent card HTML
     */
    createEnhancedAgentCard(agent) {
        const agentId = agent.agent_id || agent.id;
        const agentName = agent.name || agentId;
        const status = agent.status || 'unknown';
        const sovereign = agent.sovereign;

        return `
            <div class="agent-card" data-agent-id="${agentId}">
                <div class="agent-header">
                    <div class="agent-identity">
                        <div class="agent-avatar">${this.getAgentAvatar(agent)}</div>
                        <div class="agent-info">
                            <div class="agent-name">${this.escapeHtml(agentName)}</div>
                            <div class="agent-id">${agentId}</div>
                            ${sovereign ? `
                                <div class="public-key-badge">
                                    <span class="key-icon">🔑</span>
                                    <span class="key-status">Sovereign</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>

                <div class="agent-status-section">
                    <div class="status-indicator ${status}"></div>
                    <span class="status-text">${status}</span>
                    ${agent.lastInteraction ? `
                        <span class="last-activity">Last active: ${this.formatTimestamp(agent.lastInteraction)}</span>
                    ` : ''}
                </div>

                <div class="agent-capabilities">
                    <div class="capability-tags">
                        ${agent.capabilities?.slice(0, 3).map(cap => `
                            <span class="capability-tag">${this.escapeHtml(cap.name || cap)}</span>
                        `).join('') || ''}
                    </div>
                </div>

                <div class="agent-metrics">
                    <div class="metric-item">
                        <div class="metric-value">${agent.metrics?.tasksCompleted || 0}</div>
                        <div class="metric-label">Tasks</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">${agent.metrics?.successRate || 0}%</div>
                        <div class="metric-label">Success</div>
                    </div>
                </div>

                <div class="agent-card-footer">
                    <div class="registration-date">
                        Registered: ${this.formatTimestamp(agent.created_at || agent.registered_at)}
                    </div>
                    <div class="card-actions">
                        <button class="card-action-btn primary" data-action="details" data-agent-id="${agentId}">Details</button>
                        <button class="card-action-btn secondary" data-action="interact" data-agent-id="${agentId}">Interact</button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get agent avatar based on type
     */
    getAgentAvatar(agent) {
        const typeIcons = {
            mastermind: '👑',
            coordinator: '🎯',
            ceo: '💼',
            agint: '🧠',
            bdi: '⚡',
            guardian: '🛡️',
            memory: '🧠',
            simple_coder: '💻',
            automindx: '🎭',
            github: '📦',
            mindxagent: '🤖'
        };

        const agentType = agent.type || agent.agent_type;
        return typeIcons[agentType] || '🤖';
    }

    /**
     * Attach enhanced card event listeners
     */
    attachEnhancedCardEventListeners() {
        // Card click for details
        document.querySelectorAll('.agent-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.card-action-btn')) {
                    const agentId = card.getAttribute('data-agent-id');
                    this.showAgentDetailsModal(agentId);
                }
            });
        });

        // Action buttons
        document.querySelectorAll('.card-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.getAttribute('data-action');
                const agentId = btn.getAttribute('data-agent-id');

                if (action === 'details') {
                    this.showAgentDetailsModal(agentId);
                } else if (action === 'interact') {
                    this.interactWithAgent(agentId);
                }
            });
        });
    }

    /**
     * Update cognitive loop visualization
     */
    updateCognitiveLoop(loopData) {
        Object.entries(loopData).forEach(([phase, data]) => {
            const nodeEl = document.getElementById(`${phase}-node`);
            if (nodeEl) {
                const statusEl = nodeEl.querySelector('.node-status');
                const activityEl = nodeEl.querySelector('.node-activity');

                if (statusEl) statusEl.textContent = data.status;
                if (activityEl) activityEl.textContent = data.activity;

                // Update CSS classes
                nodeEl.className = `loop-node ${phase}`;
                if (data.status) {
                    nodeEl.classList.add(data.status.toLowerCase());
                }
            }
        });
    }

    /**
     * Update activity stream
     */
    updateActivityStream(activities) {
        const streamEl = document.getElementById('activity-stream');
        if (!streamEl) return;

        if (!activities || activities.length === 0) {
            streamEl.innerHTML = `
                <div class="activity-placeholder">
                    <div class="placeholder-icon">🔄</div>
                    <div class="placeholder-text">AGI activity will appear here in real-time</div>
                </div>
            `;
            return;
        }

        streamEl.innerHTML = activities.slice(-20).map(activity => `
            <div class="activity-item ${activity.type || ''}">
                <div class="activity-timestamp">${this.formatTimestamp(activity.timestamp)}</div>
                <div class="activity-content">
                    <div class="activity-type">${activity.phase || activity.type || 'ACTIVITY'}</div>
                    <div class="activity-message">${this.escapeHtml(activity.message || activity.description || '')}</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Update analytics dashboard
     */
    updateAnalytics(metrics) {
        const updateElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };

        updateElement('loop-cycles', metrics.cycles);
        updateElement('avg-cycle-time', metrics.avgCycleTime);
        updateElement('decision-confidence', `${metrics.confidence}%`);
        updateElement('q-learning-updates', metrics.qLearning);

        // Update chart placeholders with mock data
        this.updateAnalyticsCharts(metrics);
    }

    /**
     * Update analytics charts (placeholder implementation)
     */
    updateAnalyticsCharts(metrics) {
        // In a real implementation, this would update actual charts
        // For now, just update the placeholder text
        const charts = ['reasoning-chart', 'decision-chart', 'learning-chart', 'autonomy-chart'];
        charts.forEach(chartId => {
            const chartEl = document.getElementById(chartId);
            if (chartEl) {
                chartEl.innerHTML = `
                    <div style="text-align: center; color: var(--text-secondary); font-size: var(--font-sm);">
                        📊 Real-time data visualization<br>
                        <small>Last updated: ${new Date().toLocaleTimeString()}</small>
                    </div>
                `;
            }
        });
    }

    /**
     * Show agent details modal
     */
    showAgentDetailsModal(agentId) {
        const agent = this.agentsData?.categorized?.all?.find(a => (a.agent_id || a.id) === agentId);
        if (!agent) return;

        const modal = document.getElementById('agent-details-modal');
        if (!modal) return;

        // Populate modal with agent data
        this.populateAgentModal(agent);

        // Show modal
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    /**
     * Populate agent modal with data
     */
    populateAgentModal(agent) {
        // Basic info
        document.getElementById('modal-agent-avatar').textContent = this.getAgentAvatar(agent);
        document.getElementById('modal-agent-name').textContent = agent.name || agent.agent_id;
        document.getElementById('modal-agent-id').textContent = `ID: ${agent.agent_id || agent.id}`;

        // Public key indicator
        const keyIndicator = document.getElementById('modal-public-key');
        if (keyIndicator) {
            if (agent.sovereign) {
                keyIndicator.style.display = 'flex';
            } else {
                keyIndicator.style.display = 'none';
            }
        }

        // Status and health
        document.getElementById('modal-status').textContent = agent.status;
        document.getElementById('modal-health').textContent = `${agent.health}%`;
        document.getElementById('modal-uptime').textContent = agent.metrics?.uptime || 'N/A';

        // Capabilities
        const capabilitiesEl = document.getElementById('modal-capabilities');
        if (capabilitiesEl && agent.capabilities) {
            capabilitiesEl.innerHTML = agent.capabilities.map(cap => `
                <span class="capability-item">${this.escapeHtml(cap.name || cap)}</span>
            `).join('');
        }

        // Identity info
        document.getElementById('modal-wallet').textContent = agent.publicKey || agent.wallet_address || 'Not registered';
        document.getElementById('modal-sovereignty').textContent = agent.sovereign ? 'High' : 'Standard';
        document.getElementById('modal-last-audit').textContent = this.formatTimestamp(agent.last_audit || agent.updated_at);

        // Performance metrics
        document.getElementById('perf-tasks').textContent = agent.metrics?.tasksCompleted || 0;
        document.getElementById('perf-success').textContent = `${agent.metrics?.successRate || 0}%`;
        document.getElementById('perf-response').textContent = agent.metrics?.responseTime || 'N/A';
    }

    /**
     * Interact with agent
     */
    async interactWithAgent(agentId) {
        try {
            const result = await this.apiRequest(`/agents/${agentId}/interact`, 'POST', {
                action: 'greet',
                message: 'Hello from the mindX interface'
            });

            this.showNotification(`Interaction with ${agentId} completed`, 'success');
        } catch (error) {
            console.error('Agent interaction failed:', error);
            this.showNotification('Agent interaction failed', 'error');
        }
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
        // Hierarchy navigation tabs
        document.querySelectorAll('.hierarchy-tab-btn').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const hierarchy = e.currentTarget.getAttribute('data-hierarchy');
                this.switchHierarchy(hierarchy);
            });
        });

        // Control buttons
        const refreshBtn = document.getElementById('refresh-agents-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const createBtn = document.getElementById('create-agent-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.createNewAgent());
        }

        const exportBtn = document.getElementById('export-agents-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportAgentsRegistry());
        }

        // AGIVITY controls
        const pauseActivityBtn = document.getElementById('pause-activity');
        if (pauseActivityBtn) {
            pauseActivityBtn.addEventListener('click', () => this.toggleActivityMonitoring());
        }

        const clearActivityBtn = document.getElementById('clear-activity');
        if (clearActivityBtn) {
            clearActivityBtn.addEventListener('click', () => this.clearActivityStream());
        }

        const refreshMetricsBtn = document.getElementById('refresh-metrics');
        if (refreshMetricsBtn) {
            refreshMetricsBtn.addEventListener('click', () => this.loadData());
        }

        // Modal controls
        this.setupModalEventListeners();

        // AGI insights controls
        const generateInsightsBtn = document.getElementById('generate-insights');
        if (generateInsightsBtn) {
            generateInsightsBtn.addEventListener('click', () => this.generateAGIInsights());
        }

        const clearInsightsBtn = document.getElementById('clear-insights');
        if (clearInsightsBtn) {
            clearInsightsBtn.addEventListener('click', () => this.clearAGIInsights());
        }
    }

    /**
     * Set up modal event listeners
     */
    setupModalEventListeners() {
        // Close modal on overlay click
        const modal = document.getElementById('agent-details-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeAgentDetailsModal();
                }
            });
        }

        // Modal tab switching
        document.querySelectorAll('.details-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.getAttribute('data-tab');
                this.switchModalTab(tabName);
            });
        });

        // Modal action buttons
        const editBtn = document.getElementById('modal-edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.editAgent());
        }

        const deleteBtn = document.getElementById('modal-delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteAgent());
        }
    }

    /**
     * Switch hierarchy view
     */
    switchHierarchy(hierarchy) {
        this.currentHierarchy = hierarchy;

        // Update tab UI
        document.querySelectorAll('.hierarchy-tab-btn').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-hierarchy="${hierarchy}"]`).classList.add('active');

        // Re-render agents for this hierarchy
        if (this.agentsData?.categorized?.[hierarchy]) {
            this.renderAgentCardsForHierarchy(this.agentsData.categorized[hierarchy]);
        }
    }

    /**
     * Create new agent
     */
    async createNewAgent() {
        try {
            // Navigate to agent creation workflow
            const result = await this.apiRequest('/agents/create', 'POST', {
                template: 'user_agent',
                sovereignty: true
            });

            this.showNotification('Agent creation initiated', 'success');
            setTimeout(() => this.loadData(), 2000); // Refresh after creation
        } catch (error) {
            console.error('Agent creation failed:', error);
            this.showNotification('Agent creation failed', 'error');
        }
    }

    /**
     * Export agents registry
     */
    async exportAgentsRegistry() {
        try {
            const exportData = {
                timestamp: new Date().toISOString(),
                registry: this.agentsData,
                version: '1.0'
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-agents-registry-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Agent registry exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export agent registry', 'error');
        }
    }

    /**
     * Toggle activity monitoring
     */
    toggleActivityMonitoring() {
        const btn = document.getElementById('pause-activity');
        if (!btn) return;

        const isPaused = btn.textContent.includes('Resume');
        btn.innerHTML = isPaused ?
            `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
            </svg> Pause` :
            `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5,3 19,12 5,21 5,3"></polygon>
            </svg> Resume`;

        // In a real implementation, this would pause/resume the monitoring
        this.showNotification(isPaused ? 'Activity monitoring resumed' : 'Activity monitoring paused', 'info');
    }

    /**
     * Clear activity stream
     */
    clearActivityStream() {
        const streamEl = document.getElementById('activity-stream');
        if (streamEl) {
            streamEl.innerHTML = `
                <div class="activity-placeholder">
                    <div class="placeholder-icon">🔄</div>
                    <div class="placeholder-text">Activity stream cleared</div>
                </div>
            `;
        }
        this.showNotification('Activity stream cleared', 'info');
    }

    /**
     * Generate AGI insights
     */
    async generateAGIInsights() {
        try {
            const insights = await this.apiRequest('/agi/insights/generate', 'POST');
            this.displayAGIInsights(insights);
            this.showNotification('AGI insights generated', 'success');
        } catch (error) {
            console.error('Insights generation failed:', error);
            this.showNotification('Failed to generate AGI insights', 'error');
        }
    }

    /**
     * Display AGI insights
     */
    displayAGIInsights(insights) {
        const container = document.getElementById('insights-container');
        if (!container) return;

        const insightsHtml = (insights || []).map(insight => `
            <div class="insight-item">
                <div class="insight-timestamp">${this.formatTimestamp(insight.timestamp)}</div>
                <div class="insight-content">${this.escapeHtml(insight.content || insight.message)}</div>
            </div>
        `).join('');

        container.innerHTML = insightsHtml || `
            <div class="insight-placeholder">
                <div class="placeholder-icon">💭</div>
                <div class="placeholder-text">AGI insights will be generated based on cognitive activity patterns</div>
            </div>
        `;
    }

    /**
     * Clear AGI insights
     */
    clearAGIInsights() {
        const container = document.getElementById('insights-container');
        if (container) {
            container.innerHTML = `
                <div class="insight-placeholder">
                    <div class="placeholder-icon">💭</div>
                    <div class="placeholder-text">AGI insights cleared</div>
                </div>
            `;
        }
        this.showNotification('AGI insights cleared', 'info');
    }

    /**
     * Close agent details modal
     */
    closeAgentDetailsModal() {
        const modal = document.getElementById('agent-details-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    /**
     * Switch modal tab
     */
    switchModalTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.details-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.details-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab-content`).classList.add('active');
    }

    /**
     * Edit agent (placeholder)
     */
    editAgent() {
        this.showNotification('Agent editing not yet implemented', 'warning');
    }

    /**
     * Delete agent (placeholder)
     */
    deleteAgent() {
        if (confirm('Are you sure you want to delete this agent? This action cannot be undone.')) {
            this.showNotification('Agent deletion not yet implemented', 'warning');
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '600',
            zIndex: '10000',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            backdropFilter: 'blur(10px)'
        });

        // Set background color based on type
        const colors = {
            success: 'rgba(0, 255, 136, 0.9)',
            error: 'rgba(255, 100, 100, 0.9)',
            warning: 'rgba(255, 193, 7, 0.9)',
            info: 'rgba(0, 123, 255, 0.9)'
        };
        notification.style.background = colors[type] || colors.info;

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    /**
     * Load AGI activity (legacy method for backward compatibility)
     */
    async loadAGIActivity() {
        // This method is now handled by the data expressions in loadData()
        console.log('AGI activity loading handled by data expressions');
    }

    /**
     * Load agent registry (legacy method for backward compatibility)
     */
    async loadAgentRegistry() {
        // This method is now handled by the data expressions in loadData()
        console.log('Agent registry loading handled by data expressions');
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
