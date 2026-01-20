/**
 * Knowledge Tab Component
 *
 * Interactive knowledge graph visualization showing beliefs, goals,
 * and strategic evolution relationships in the mindX system.
 *
 * @module KnowledgeTab
 */

class KnowledgeTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'knowledge',
            label: 'Knowledge',
            group: 'main',
            refreshInterval: 30000, // 30 seconds for knowledge updates
            autoRefresh: true,
            ...config
        });

        this.knowledgeData = null;
        this.graphData = null;
        this.selectedNode = null;
        this.currentGraphType = 'comprehensive';
        this.canvas = null;
        this.nodes = new Map();
        this.edges = [];
        this.simulation = null;
        this.zoom = null;
        this.physicsEnabled = true;
        this.layoutType = 'force';
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register comprehensive knowledge data expressions
        if (window.dataExpressions) {
            // Beliefs data
            window.dataExpressions.registerExpression('knowledge_beliefs', {
                endpoints: [
                    { url: '/beliefs/all', key: 'beliefs' },
                    { url: '/beliefs/relationships', key: 'relationships' },
                    { url: '/beliefs/confidence', key: 'confidence' }
                ],
                transform: (data) => this.transformBeliefsData(data),
                onUpdate: (data) => this.updateBeliefsData(data),
                cache: false
            });

            // Goals data
            window.dataExpressions.registerExpression('knowledge_goals', {
                endpoints: [
                    { url: '/goals/active', key: 'goals' },
                    { url: '/goals/hierarchy', key: 'hierarchy' },
                    { url: '/goals/dependencies', key: 'dependencies' }
                ],
                transform: (data) => this.transformGoalsData(data),
                onUpdate: (data) => this.updateGoalsData(data),
                cache: false
            });

            // Strategic evolution data
            window.dataExpressions.registerExpression('knowledge_strategies', {
                endpoints: [
                    { url: '/strategies/active', key: 'strategies' },
                    { url: '/evolution/timeline', key: 'timeline' },
                    { url: '/evolution/insights', key: 'insights' }
                ],
                transform: (data) => this.transformStrategiesData(data),
                onUpdate: (data) => this.updateStrategiesData(data),
                cache: false
            });
        }

        // Set up state
        this.canvas = document.getElementById('knowledge-graph-canvas');

        // Set up event listeners
        this.setupEventListeners();

        // Initialize graph
        this.initializeGraph();

        // Load initial data
        await this.loadData();

        console.log('✅ KnowledgeTab initialized');
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
                // Load all knowledge data in parallel
                const [beliefsData, goalsData, strategiesData] = await Promise.all([
                    window.dataExpressions.executeExpression('knowledge_beliefs'),
                    window.dataExpressions.executeExpression('knowledge_goals'),
                    window.dataExpressions.executeExpression('knowledge_strategies')
                ]);

                // Update all data stores
                this.updateBeliefsData(beliefsData);
                this.updateGoalsData(goalsData);
                this.updateStrategiesData(strategiesData);

                // Update graph visualization
                this.updateGraphVisualization();

            } catch (error) {
                console.error('Failed to load knowledge data:', error);
                this.showError('Failed to load knowledge data', document.getElementById('knowledge-tab'));
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
            const mockData = this.generateMockKnowledgeData();
            this.updateBeliefsData(mockData.beliefs);
            this.updateGoalsData(mockData.goals);
            this.updateStrategiesData(mockData.strategies);
            this.updateGraphVisualization();
        } catch (error) {
            console.error('Error loading knowledge data:', error);
            this.showError('Failed to load knowledge data', document.getElementById('knowledge-tab'));
        }
    }

    /**
     * Transform beliefs data
     */
    transformBeliefsData(data) {
        const beliefs = data.data_0 || [];
        const relationships = data.data_1 || [];
        const confidence = data.data_2 || {};

        return {
            beliefs: beliefs.map(belief => ({
                ...belief,
                confidence: confidence[belief.id] || 0.5,
                confidenceLevel: this.getConfidenceLevel(confidence[belief.id] || 0.5),
                lastUpdated: belief.last_updated,
                source: belief.source || 'unknown'
            })),
            relationships: relationships.map(rel => ({
                ...rel,
                type: rel.type || 'supports',
                strength: rel.strength || 0.5
            })),
            stats: {
                total: beliefs.length,
                highConfidence: beliefs.filter(b => (confidence[b.id] || 0) > 0.8).length,
                recent: beliefs.filter(b => this.isRecent(b.last_updated)).length
            }
        };
    }

    /**
     * Transform goals data
     */
    transformGoalsData(data) {
        const goals = data.data_0 || [];
        const hierarchy = data.data_1 || [];
        const dependencies = data.data_2 || [];

        return {
            goals: goals.map(goal => ({
                ...goal,
                status: goal.status || 'active',
                priority: goal.priority || 'medium',
                progress: goal.progress || 0,
                dependencies: dependencies.filter(d => d.goal_id === goal.id)
            })),
            hierarchy,
            stats: {
                active: goals.filter(g => g.status === 'active').length,
                completed: goals.filter(g => g.status === 'completed').length,
                priority: goals.filter(g => g.priority === 'high').length
            }
        };
    }

    /**
     * Transform strategies data
     */
    transformStrategiesData(data) {
        const strategies = data.data_0 || [];
        const timeline = data.data_1 || [];
        const insights = data.data_2 || [];

        return {
            strategies: strategies.map(strategy => ({
                ...strategy,
                status: strategy.status || 'active',
                successRate: strategy.success_rate || 0,
                evolutionCycles: strategy.evolution_cycles || 0
            })),
            timeline,
            insights,
            stats: {
                active: strategies.filter(s => s.status === 'active').length,
                cycles: strategies.reduce((sum, s) => sum + (s.evolution_cycles || 0), 0),
                success: strategies.length > 0 ?
                    strategies.reduce((sum, s) => sum + (s.success_rate || 0), 0) / strategies.length : 0
            }
        };
    }

    /**
     * Get confidence level string
     */
    getConfidenceLevel(confidence) {
        if (confidence > 0.8) return 'high';
        if (confidence > 0.5) return 'medium';
        return 'low';
    }

    /**
     * Check if timestamp is recent (within last 24 hours)
     */
    isRecent(timestamp) {
        if (!timestamp) return false;
        const now = new Date();
        const date = new Date(timestamp);
        const diffMs = now - date;
        return diffMs < 24 * 60 * 60 * 1000; // 24 hours
    }

    /**
     * Update beliefs data
     */
    updateBeliefsData(data) {
        if (!data) return;
        this.beliefsData = data;

        // Update stats
        this.updateElement('total-beliefs', data.stats.total);
        this.updateElement('beliefs-total', data.stats.total);
        this.updateElement('beliefs-high-confidence', data.stats.highConfidence);
        this.updateElement('beliefs-recent', data.stats.recent);

        // Update beliefs list
        this.renderBeliefsList(data.beliefs);
    }

    /**
     * Update goals data
     */
    updateGoalsData(data) {
        if (!data) return;
        this.goalsData = data;

        // Update stats
        this.updateElement('active-goals', data.stats.active);
        this.updateElement('goals-active', data.stats.active);
        this.updateElement('goals-completed', data.stats.completed);
        this.updateElement('goals-priority', data.stats.priority);

        // Update goals hierarchy
        this.renderGoalsHierarchy(data.goals, data.hierarchy);
    }

    /**
     * Update strategies data
     */
    updateStrategiesData(data) {
        if (!data) return;
        this.strategiesData = data;

        // Update stats
        this.updateElement('strategic-plans', data.stats.active);
        this.updateElement('strategies-active', data.stats.active);
        this.updateElement('evolution-cycles', data.stats.cycles);
        this.updateElement('evolution-success', `${(data.stats.success * 100).toFixed(1)}%`);

        // Update evolution timeline
        this.renderEvolutionTimeline(data.timeline);
    }

    /**
     * Update graph visualization
     */
    updateGraphVisualization() {
        // Generate graph data based on current type
        this.graphData = this.generateGraphData(this.currentGraphType);

        // Render graph
        this.renderGraph(this.graphData);
    }

    /**
     * Generate graph data for visualization
     */
    generateGraphData(type) {
        const nodes = [];
        const edges = [];

        switch (type) {
            case 'comprehensive':
                return this.generateComprehensiveGraph();
            case 'beliefs':
                return this.generateBeliefsGraph();
            case 'goals':
                return this.generateGoalsGraph();
            case 'strategic':
                return this.generateStrategicGraph();
            default:
                return this.generateComprehensiveGraph();
        }
    }

    /**
     * Generate comprehensive graph (all knowledge types)
     */
    generateComprehensiveGraph() {
        const nodes = [];
        const edges = [];

        // Add beliefs
        if (this.beliefsData?.beliefs) {
            this.beliefsData.beliefs.forEach(belief => {
                nodes.push({
                    id: `belief-${belief.id}`,
                    type: 'belief',
                    label: belief.content?.substring(0, 30) + '...' || belief.id,
                    data: belief,
                    size: Math.max(20, belief.confidence * 40)
                });
            });
        }

        // Add goals
        if (this.goalsData?.goals) {
            this.goalsData.goals.forEach(goal => {
                nodes.push({
                    id: `goal-${goal.id}`,
                    type: 'goal',
                    label: goal.title?.substring(0, 30) + '...' || goal.id,
                    data: goal,
                    size: Math.max(20, goal.priority === 'high' ? 35 : goal.priority === 'medium' ? 25 : 20)
                });
            });
        }

        // Add strategies
        if (this.strategiesData?.strategies) {
            this.strategiesData.strategies.forEach(strategy => {
                nodes.push({
                    id: `strategy-${strategy.id}`,
                    type: 'strategy',
                    label: strategy.name?.substring(0, 30) + '...' || strategy.id,
                    data: strategy,
                    size: Math.max(20, strategy.success_rate * 40)
                });
            });
        }

        // Add relationships
        if (this.beliefsData?.relationships) {
            this.beliefsData.relationships.forEach(rel => {
                edges.push({
                    source: `belief-${rel.from_id}`,
                    target: `belief-${rel.to_id}`,
                    type: rel.type,
                    strength: rel.strength
                });
            });
        }

        // Add goal dependencies
        if (this.goalsData?.goals) {
            this.goalsData.goals.forEach(goal => {
                goal.dependencies?.forEach(dep => {
                    edges.push({
                        source: `goal-${goal.id}`,
                        target: `goal-${dep.depends_on_id}`,
                        type: 'depends_on',
                        strength: 0.8
                    });
                });
            });
        }

        return { nodes, edges };
    }

    /**
     * Generate beliefs-only graph
     */
    generateBeliefsGraph() {
        const nodes = [];
        const edges = [];

        if (this.beliefsData?.beliefs) {
            this.beliefsData.beliefs.forEach(belief => {
                nodes.push({
                    id: `belief-${belief.id}`,
                    type: 'belief',
                    label: belief.content?.substring(0, 40) + '...' || belief.id,
                    data: belief,
                    size: Math.max(25, belief.confidence * 50)
                });
            });
        }

        if (this.beliefsData?.relationships) {
            this.beliefsData.relationships.forEach(rel => {
                edges.push({
                    source: `belief-${rel.from_id}`,
                    target: `belief-${rel.to_id}`,
                    type: rel.type,
                    strength: rel.strength
                });
            });
        }

        return { nodes, edges };
    }

    /**
     * Generate goals-only graph
     */
    generateGoalsGraph() {
        const nodes = [];
        const edges = [];

        if (this.goalsData?.goals) {
            this.goalsData.goals.forEach(goal => {
                nodes.push({
                    id: `goal-${goal.id}`,
                    type: 'goal',
                    label: goal.title?.substring(0, 40) + '...' || goal.id,
                    data: goal,
                    size: Math.max(25, goal.priority === 'high' ? 45 : goal.priority === 'medium' ? 35 : 25)
                });
            });
        }

        // Add goal hierarchy edges
        if (this.goalsData?.hierarchy) {
            this.goalsData.hierarchy.forEach(h => {
                edges.push({
                    source: `goal-${h.parent_id}`,
                    target: `goal-${h.child_id}`,
                    type: 'hierarchy',
                    strength: 0.9
                });
            });
        }

        // Add dependencies
        if (this.goalsData?.goals) {
            this.goalsData.goals.forEach(goal => {
                goal.dependencies?.forEach(dep => {
                    edges.push({
                        source: `goal-${goal.id}`,
                        target: `goal-${dep.depends_on_id}`,
                        type: 'depends_on',
                        strength: 0.7
                    });
                });
            });
        }

        return { nodes, edges };
    }

    /**
     * Generate strategic evolution graph
     */
    generateStrategicGraph() {
        const nodes = [];
        const edges = [];

        if (this.strategiesData?.strategies) {
            this.strategiesData.strategies.forEach(strategy => {
                nodes.push({
                    id: `strategy-${strategy.id}`,
                    type: 'strategy',
                    label: strategy.name?.substring(0, 40) + '...' || strategy.id,
                    data: strategy,
                    size: Math.max(30, strategy.success_rate * 50)
                });
            });
        }

        // Add evolution path edges
        if (this.strategiesData?.timeline) {
            this.strategiesData.timeline.forEach((item, index) => {
                if (index > 0) {
                    edges.push({
                        source: `strategy-${this.strategiesData.timeline[index - 1].strategy_id}`,
                        target: `strategy-${item.strategy_id}`,
                        type: 'evolution',
                        strength: 0.8
                    });
                }
            });
        }

        return { nodes, edges };
    }

    /**
     * Render graph using D3.js (simplified implementation)
     */
    renderGraph(data) {
        if (!this.canvas || !data) return;

        // Clear existing graph
        this.clearGraph();

        // Create SVG
        const svg = d3.select(this.canvas)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', '0 0 800 600');

        // Create zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                svg.select('.graph-content').attr('transform', event.transform);
            });

        svg.call(this.zoom);

        // Create main group
        const g = svg.append('g').attr('class', 'graph-content');

        // Create force simulation
        this.simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.edges).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(400, 300))
            .force('collision', d3.forceCollide().radius(d => d.size + 5));

        // Create edges
        const edges = g.append('g')
            .attr('class', 'edges')
            .selectAll('line')
            .data(data.edges)
            .enter().append('line')
            .attr('class', d => `edge ${d.type}`)
            .attr('stroke', d => this.getEdgeColor(d.type))
            .attr('stroke-width', d => Math.max(1, d.strength * 3));

        // Create nodes
        const nodes = g.append('g')
            .attr('class', 'nodes')
            .selectAll('circle')
            .data(data.nodes)
            .enter().append('circle')
            .attr('class', d => `node ${d.type}`)
            .attr('r', d => d.size)
            .attr('fill', d => this.getNodeColor(d.type))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active) this.simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }))
            .on('click', (event, d) => this.selectGraphNode(d));

        // Add labels
        const labels = g.append('g')
            .attr('class', 'labels')
            .selectAll('text')
            .data(data.nodes)
            .enter().append('text')
            .attr('class', 'node-label')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('fill', '#fff')
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .text(d => d.label);

        // Update positions on simulation tick
        this.simulation.on('tick', () => {
            edges
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            nodes
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            labels
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        // Store references
        this.nodes = nodes;
        this.edges = edges;
        this.nodeLabels = labels;
    }

    /**
     * Get node color based on type
     */
    getNodeColor(type) {
        const colors = {
            belief: '#00ff88',
            goal: '#ffc107',
            strategy: '#8a2be2'
        };
        return colors[type] || '#00bfff';
    }

    /**
     * Get edge color based on type
     */
    getEdgeColor(type) {
        const colors = {
            supports: '#00ff88',
            contradicts: '#ff4444',
            depends_on: '#ffc107',
            hierarchy: '#00bfff',
            evolution: '#8a2be2'
        };
        return colors[type] || '#666';
    }

    /**
     * Select graph node
     */
    selectGraphNode(node) {
        // Update selected node
        this.selectedNode = node;

        // Update UI
        this.nodes.attr('stroke-width', d => d.id === node.id ? 4 : 2);
        this.renderSelectedNodeDetails(node);
    }

    /**
     * Render selected node details
     */
    renderSelectedNodeDetails(node) {
        const container = document.getElementById('selected-node-info');

        let detailsHtml = `
            <div class="node-details">
                <div class="node-header">
                    <div>
                        <div class="node-title">${this.escapeHtml(node.label)}</div>
                        <div class="node-type">${node.type}</div>
                    </div>
                </div>
                <div class="node-properties">
        `;

        // Add type-specific properties
        if (node.type === 'belief') {
            detailsHtml += `
                <div class="node-property">
                    <div class="property-label">Confidence</div>
                    <div class="property-value">${(node.data.confidence * 100).toFixed(1)}%</div>
                </div>
                <div class="node-property">
                    <div class="property-label">Source</div>
                    <div class="property-value">${node.data.source}</div>
                </div>
                <div class="node-property">
                    <div class="property-label">Last Updated</div>
                    <div class="property-value">${this.formatTimestamp(node.data.lastUpdated)}</div>
                </div>
            `;
        } else if (node.type === 'goal') {
            detailsHtml += `
                <div class="node-property">
                    <div class="property-label">Status</div>
                    <div class="property-value">${node.data.status}</div>
                </div>
                <div class="node-property">
                    <div class="property-label">Priority</div>
                    <div class="property-value">${node.data.priority}</div>
                </div>
                <div class="node-property">
                    <div class="property-label">Progress</div>
                    <div class="property-value">${node.data.progress}%</div>
                </div>
            `;
        } else if (node.type === 'strategy') {
            detailsHtml += `
                <div class="node-property">
                    <div class="property-label">Success Rate</div>
                    <div class="property-value">${(node.data.successRate * 100).toFixed(1)}%</div>
                </div>
                <div class="node-property">
                    <div class="property-label">Evolution Cycles</div>
                    <div class="property-value">${node.data.evolutionCycles}</div>
                </div>
                <div class="node-property">
                    <div class="property-label">Status</div>
                    <div class="property-value">${node.data.status}</div>
                </div>
            `;
        }

        detailsHtml += `
                </div>
                <div class="node-relationships">
                    <h4>Relationships</h4>
                    <div class="relationship-list">
                        <!-- Relationships will be populated dynamically -->
                        <div class="relationship-item">
                            <span>Connected to ${this.getConnectedNodes(node).length} other nodes</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = detailsHtml;
    }

    /**
     * Get connected nodes for a given node
     */
    getConnectedNodes(node) {
        if (!this.graphData?.edges) return [];

        return this.graphData.edges
            .filter(edge => edge.source.id === node.id || edge.target.id === node.id)
            .map(edge => edge.source.id === node.id ? edge.target : edge.source);
    }

    /**
     * Render beliefs list
     */
    renderBeliefsList(beliefs) {
        const container = document.getElementById('beliefs-list');
        if (!container) return;

        container.innerHTML = beliefs.slice(0, 20).map(belief => `
            <div class="belief-item ${belief.confidenceLevel}-confidence" data-belief-id="${belief.id}">
                <div class="item-header">
                    <div class="item-title">${this.escapeHtml(belief.content?.substring(0, 100) || belief.id)}</div>
                    <div class="item-meta">${(belief.confidence * 100).toFixed(1)}% confidence</div>
                </div>
                <div class="item-content">
                    Source: ${belief.source} | Updated: ${this.formatTimestamp(belief.lastUpdated)}
                </div>
            </div>
        `).join('');
    }

    /**
     * Render goals hierarchy
     */
    renderGoalsHierarchy(goals, hierarchy) {
        const container = document.getElementById('goals-hierarchy');
        if (!container) return;

        container.innerHTML = goals.slice(0, 15).map(goal => `
            <div class="goal-item ${goal.status}" data-goal-id="${goal.id}">
                <div class="item-header">
                    <div class="item-title">${this.escapeHtml(goal.title)}</div>
                    <div class="item-meta">${goal.priority} priority</div>
                </div>
                <div class="item-content">
                    Status: ${goal.status} | Progress: ${goal.progress}%
                    ${goal.dependencies?.length ? ` | Dependencies: ${goal.dependencies.length}` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Render evolution timeline
     */
    renderEvolutionTimeline(timeline) {
        const container = document.getElementById('evolution-timeline');
        if (!container) return;

        container.innerHTML = (timeline || []).slice(0, 10).map(item => `
            <div class="evolution-item ${item.success ? 'success' : 'failed'}" data-evolution-id="${item.id}">
                <div class="item-header">
                    <div class="item-title">${this.escapeHtml(item.description)}</div>
                    <div class="item-meta">${this.formatTimestamp(item.timestamp)}</div>
                </div>
                <div class="item-content">
                    ${item.details || 'Evolution step completed'}
                </div>
            </div>
        `).join('');
    }

    /**
     * Clear graph
     */
    clearGraph() {
        if (this.canvas) {
            d3.select(this.canvas).selectAll('*').remove();
        }
        if (this.simulation) {
            this.simulation.stop();
        }
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Graph type selection
        document.querySelectorAll('.graph-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = e.currentTarget.getAttribute('data-graph-type');
                this.selectGraphType(type);
            });
        });

        // Control buttons
        const refreshBtn = document.getElementById('refresh-knowledge-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const exportBtn = document.getElementById('export-knowledge-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportKnowledgeGraph());
        }

        // Graph controls
        const zoomInBtn = document.getElementById('zoom-in-graph');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.zoomGraph(1.2));
        }

        const zoomOutBtn = document.getElementById('zoom-out-graph');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.zoomGraph(0.8));
        }

        const fitViewBtn = document.getElementById('fit-graph-view');
        if (fitViewBtn) {
            fitViewBtn.addEventListener('click', () => this.fitGraphView());
        }

        const togglePhysicsBtn = document.getElementById('toggle-physics');
        if (togglePhysicsBtn) {
            togglePhysicsBtn.addEventListener('click', () => this.togglePhysics());
        }

        const layoutSelect = document.getElementById('graph-layout');
        if (layoutSelect) {
            layoutSelect.addEventListener('change', (e) => this.changeLayout(e.target.value));
        }

        // Panel tab switching
        document.querySelectorAll('.panel-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const panelName = e.currentTarget.getAttribute('data-panel');
                this.switchPanel(panelName);
            });
        });

        // Insights controls
        const generateInsightsBtn = document.getElementById('generate-insights-btn');
        if (generateInsightsBtn) {
            generateInsightsBtn.addEventListener('click', () => this.generateInsights());
        }

        const clearInsightsBtn = document.getElementById('clear-insights-btn');
        if (clearInsightsBtn) {
            clearInsightsBtn.addEventListener('click', () => this.clearInsights());
        }
    }

    /**
     * Select graph type
     */
    selectGraphType(type) {
        this.currentGraphType = type;

        // Update UI
        document.querySelectorAll('.graph-type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-graph-type="${type}"]`).classList.add('active');

        // Update visualization
        this.updateGraphVisualization();
    }

    /**
     * Zoom graph
     */
    zoomGraph(factor) {
        if (this.zoom && this.canvas) {
            d3.select(this.canvas).transition().call(
                this.zoom.scaleBy, factor
            );
        }
    }

    /**
     * Fit graph view
     */
    fitGraphView() {
        if (this.zoom && this.canvas) {
            const svg = d3.select(this.canvas).select('svg');
            const bounds = svg.node().getBBox();
            const fullWidth = 800;
            const fullHeight = 600;
            const midX = bounds.x + bounds.width / 2;
            const midY = bounds.y + bounds.height / 2;

            const scale = 0.8 / Math.max(bounds.width / fullWidth, bounds.height / fullHeight);
            const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

            svg.transition().call(
                this.zoom.transform,
                d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
            );
        }
    }

    /**
     * Toggle physics
     */
    togglePhysics() {
        this.physicsEnabled = !this.physicsEnabled;
        if (this.simulation) {
            if (this.physicsEnabled) {
                this.simulation.alpha(0.3).restart();
            } else {
                this.simulation.stop();
            }
        }
    }

    /**
     * Change layout
     */
    changeLayout(layoutType) {
        this.layoutType = layoutType;
        // In a full implementation, this would change the force layout
        console.log('Layout changed to:', layoutType);
    }

    /**
     * Switch panel
     */
    switchPanel(panelName) {
        // Update tab buttons
        document.querySelectorAll('.panel-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-panel="${panelName}"]`).classList.add('active');

        // Update panel content
        document.querySelectorAll('.panel-section').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${panelName}-panel`).classList.add('active');
    }

    /**
     * Generate insights
     */
    async generateInsights() {
        try {
            const insights = await this.apiRequest('/knowledge/insights/generate', 'POST', {
                graphType: this.currentGraphType,
                nodeCount: this.graphData?.nodes?.length || 0,
                edgeCount: this.graphData?.edges?.length || 0
            });

            this.displayKnowledgeInsights(insights);
            this.showNotification('Knowledge insights generated successfully', 'success');
        } catch (error) {
            console.error('Insights generation failed:', error);
            this.showNotification('Failed to generate knowledge insights', 'error');
        }
    }

    /**
     * Display knowledge insights
     */
    displayKnowledgeInsights(insights) {
        const container = document.getElementById('knowledge-insights-container');
        if (!container) return;

        const insightsHtml = (insights || []).map(insight => `
            <div class="knowledge-insight">
                <div class="insight-timestamp">${this.formatTimestamp(insight.timestamp)}</div>
                <div class="insight-content">${this.escapeHtml(insight.content || insight.insight)}</div>
            </div>
        `).join('');

        container.innerHTML = insightsHtml || `
            <div class="insight-placeholder">
                <div class="placeholder-icon">💭</div>
                <div class="placeholder-text">Knowledge insights will be generated based on graph analysis</div>
            </div>
        `;
    }

    /**
     * Clear insights
     */
    clearInsights() {
        const container = document.getElementById('knowledge-insights-container');
        if (container) {
            container.innerHTML = `
                <div class="insight-placeholder">
                    <div class="placeholder-icon">💭</div>
                    <div class="placeholder-text">Knowledge insights cleared</div>
                </div>
            `;
        }
        this.showNotification('Knowledge insights cleared', 'info');
    }

    /**
     * Export knowledge graph
     */
    async exportKnowledgeGraph() {
        try {
            const exportData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                graphType: this.currentGraphType,
                nodes: this.graphData?.nodes || [],
                edges: this.graphData?.edges || [],
                beliefs: this.beliefsData,
                goals: this.goalsData,
                strategies: this.strategiesData
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-knowledge-graph-${this.currentGraphType}-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Knowledge graph exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export knowledge graph', 'error');
        }
    }

    /**
     * Initialize graph (placeholder for D3.js setup)
     */
    initializeGraph() {
        // This would set up D3.js in a full implementation
        console.log('Graph initialization placeholder');
    }

    /**
     * Update element text content
     */
    updateElement(id, value) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    }

    /**
     * Format timestamp to human readable
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleString();
    }

    /**
     * Generate mock knowledge data for demonstration
     */
    generateMockKnowledgeData() {
        return {
            beliefs: {
                beliefs: [
                    {
                        id: 'belief-1',
                        content: 'Self-improvement through iteration is fundamental to intelligence',
                        confidence: 0.95,
                        confidenceLevel: 'high',
                        source: 'core_system',
                        lastUpdated: new Date(Date.now() - 3600000).toISOString()
                    },
                    {
                        id: 'belief-2',
                        content: 'Multi-agent systems provide better problem-solving capabilities',
                        confidence: 0.87,
                        confidenceLevel: 'high',
                        source: 'research',
                        lastUpdated: new Date(Date.now() - 7200000).toISOString()
                    },
                    {
                        id: 'belief-3',
                        content: 'Economic viability is essential for autonomous systems',
                        confidence: 0.78,
                        confidenceLevel: 'medium',
                        source: 'business_analysis',
                        lastUpdated: new Date(Date.now() - 10800000).toISOString()
                    }
                ],
                relationships: [
                    { from_id: 'belief-1', to_id: 'belief-2', type: 'supports', strength: 0.8 },
                    { from_id: 'belief-2', to_id: 'belief-3', type: 'supports', strength: 0.6 }
                ],
                stats: { total: 3, highConfidence: 2, recent: 1 }
            },
            goals: {
                goals: [
                    {
                        id: 'goal-1',
                        title: 'Achieve autonomous operation for 24 hours',
                        status: 'active',
                        priority: 'high',
                        progress: 75
                    },
                    {
                        id: 'goal-2',
                        title: 'Implement self-improvement cycle',
                        status: 'completed',
                        priority: 'high',
                        progress: 100
                    },
                    {
                        id: 'goal-3',
                        title: 'Establish economic viability',
                        status: 'active',
                        priority: 'medium',
                        progress: 45
                    }
                ],
                hierarchy: [],
                stats: { active: 2, completed: 1, priority: 2 }
            },
            strategies: {
                strategies: [
                    {
                        id: 'strategy-1',
                        name: 'Strategic Evolution Pipeline',
                        status: 'active',
                        successRate: 0.89,
                        evolutionCycles: 23
                    },
                    {
                        id: 'strategy-2',
                        name: 'Multi-Agent Orchestration',
                        status: 'active',
                        successRate: 0.94,
                        evolutionCycles: 18
                    }
                ],
                timeline: [
                    {
                        id: 'evolution-1',
                        description: 'Implemented BDI cognitive architecture',
                        timestamp: new Date(Date.now() - 86400000).toISOString(),
                        success: true
                    },
                    {
                        id: 'evolution-2',
                        description: 'Added constitutional governance',
                        timestamp: new Date(Date.now() - 43200000).toISOString(),
                        success: true
                    }
                ],
                insights: [],
                stats: { active: 2, cycles: 41, success: 0.915 }
            }
        };
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
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.KnowledgeTab = KnowledgeTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = KnowledgeTab;
}