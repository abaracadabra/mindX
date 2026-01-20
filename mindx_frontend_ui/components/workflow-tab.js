/**
 * Workflow Tab Component
 *
 * Interactive agent workflow visualization with real-time task delegation,
 * agent interactions, and process flow monitoring.
 *
 * @module WorkflowTab
 */

class WorkflowTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'workflow',
            label: 'Workflow',
            group: 'main',
            refreshInterval: 3000, // 3 seconds for real-time workflow updates
            autoRefresh: true,
            ...config
        });

        this.workflowData = null;
        this.currentWorkflowType = 'strategic';
        this.canvas = null;
        this.nodes = new Map();
        this.connections = [];
        this.selectedWorkflow = null;
        this.zoomLevel = 1;
        this.animationsEnabled = true;
        this.detailLevel = 'medium';
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register comprehensive workflow data expressions
        if (window.dataExpressions) {
            // Active workflows data
            window.dataExpressions.registerExpression('active_workflows', {
                endpoints: [
                    { url: '/workflows/active', key: 'active' },
                    { url: '/workflows/stats', key: 'stats' },
                    { url: '/workflows/tasks', key: 'tasks' }
                ],
                transform: (data) => this.transformActiveWorkflows(data),
                onUpdate: (data) => this.updateActiveWorkflows(data),
                cache: false // Real-time workflow data
            });

            // Workflow history data
            window.dataExpressions.registerExpression('workflow_history', {
                endpoints: [
                    { url: '/workflows/history', key: 'history' },
                    { url: '/workflows/performance', key: 'performance' }
                ],
                transform: (data) => this.transformWorkflowHistory(data),
                onUpdate: (data) => this.updateWorkflowHistory(data),
                cache: false
            });

            // Workflow analytics data
            window.dataExpressions.registerExpression('workflow_analytics', {
                endpoints: [
                    { url: '/workflows/analytics/throughput', key: 'throughput' },
                    { url: '/workflows/analytics/utilization', key: 'utilization' },
                    { url: '/workflows/analytics/success', key: 'success' },
                    { url: '/workflows/analytics/delegation', key: 'delegation' }
                ],
                transform: (data) => this.transformWorkflowAnalytics(data),
                onUpdate: (data) => this.updateWorkflowAnalytics(data),
                cache: false
            });
        }

        // Set up state
        this.canvas = document.getElementById('workflow-canvas');

        // Set up event listeners
        this.setupEventListeners();

        // Initialize canvas
        this.initializeCanvas();

        // Load initial data
        await this.loadData();

        console.log('✅ WorkflowTab initialized');
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
                // Load all workflow data in parallel
                const [activeData, historyData, analyticsData] = await Promise.all([
                    window.dataExpressions.executeExpression('active_workflows'),
                    window.dataExpressions.executeExpression('workflow_history'),
                    window.dataExpressions.executeExpression('workflow_analytics')
                ]);

                // Update all displays
                this.updateActiveWorkflows(activeData);
                this.updateWorkflowHistory(historyData);
                this.updateWorkflowAnalytics(analyticsData);

                // Update workflow visualization
                this.updateWorkflowVisualization();

            } catch (error) {
                console.error('Failed to load workflow data:', error);
                this.showError('Failed to load workflow data', document.getElementById('workflow-tab'));
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
            const mockData = this.generateMockWorkflowData();
            this.updateActiveWorkflows(mockData.active);
            this.updateWorkflowHistory(mockData.history);
            this.updateWorkflowAnalytics(mockData.analytics);
            this.updateWorkflowVisualization();
        } catch (error) {
            console.error('Error loading workflow data:', error);
            this.showError('Failed to load workflow data', document.getElementById('workflow-tab'));
        }
    }

    /**
     * Transform active workflows data
     */
    transformActiveWorkflows(data) {
        const active = data.data_0 || [];
        const stats = data.data_1 || {};
        const tasks = data.data_2 || [];

        return {
            workflows: active.map(workflow => this.enrichWorkflowData(workflow, tasks)),
            stats: {
                activeCount: stats.active_workflows || 0,
                completedToday: stats.completed_today || 0,
                delegationEfficiency: stats.delegation_efficiency || 0,
                successRate: stats.success_rate || 0
            }
        };
    }

    /**
     * Transform workflow history data
     */
    transformWorkflowHistory(data) {
        const history = data.data_0 || [];
        const performance = data.data_1 || {};

        return {
            history: history.map(item => ({
                ...item,
                duration: this.calculateDuration(item.start_time, item.end_time),
                formattedStart: this.formatTimestamp(item.start_time),
                formattedEnd: this.formatTimestamp(item.end_time)
            })),
            performance: {
                avgDuration: performance.avg_duration || 0,
                completionSpeed: performance.completion_speed || 0,
                responseLatency: performance.response_latency || 0,
                errorRate: performance.error_rate || 0,
                resourceEfficiency: performance.resource_efficiency || 0,
                scalabilityIndex: performance.scalability_index || 0
            }
        };
    }

    /**
     * Transform workflow analytics data
     */
    transformWorkflowAnalytics(data) {
        return {
            throughput: data.data_0 || [],
            utilization: data.data_1 || [],
            success: data.data_2 || [],
            delegation: data.data_3 || []
        };
    }

    /**
     * Enrich workflow data with additional information
     */
    enrichWorkflowData(workflow, tasks) {
        const workflowTasks = tasks.filter(task => task.workflow_id === workflow.id);
        const progress = workflowTasks.length > 0 ?
            (workflowTasks.filter(t => t.status === 'completed').length / workflowTasks.length) * 100 : 0;

        return {
            ...workflow,
            tasks: workflowTasks,
            progress: progress,
            status: this.determineWorkflowStatus(workflow, workflowTasks),
            duration: this.calculateDuration(workflow.start_time, new Date()),
            agentCount: new Set(workflowTasks.map(t => t.assigned_agent)).size,
            taskCount: workflowTasks.length,
            completedTasks: workflowTasks.filter(t => t.status === 'completed').length
        };
    }

    /**
     * Determine workflow status
     */
    determineWorkflowStatus(workflow, tasks) {
        if (workflow.status) return workflow.status;

        if (tasks.some(t => t.status === 'failed')) return 'failed';
        if (tasks.every(t => t.status === 'completed')) return 'completed';
        if (tasks.some(t => t.status === 'in_progress')) return 'active';
        return 'pending';
    }

    /**
     * Calculate duration between timestamps
     */
    calculateDuration(start, end) {
        if (!start) return 0;
        const startTime = new Date(start).getTime();
        const endTime = end ? new Date(end).getTime() : Date.now();
        return Math.max(0, endTime - startTime);
    }

    /**
     * Update active workflows display
     */
    updateActiveWorkflows(data) {
        if (!data) return;

        // Update statistics
        this.updateElement('active-workflows-count', data.stats.activeCount);
        this.updateElement('completed-tasks-count', data.stats.completedToday);
        this.updateElement('delegation-efficiency', `${data.stats.delegationEfficiency}%`);
        this.updateElement('workflow-success-rate', `${data.stats.successRate}%`);

        // Update workflows list
        this.renderActiveWorkflows(data.workflows);
    }

    /**
     * Update workflow history display
     */
    updateWorkflowHistory(data) {
        if (!data) return;

        // Update performance metrics
        this.updateElement('avg-workflow-duration', this.formatDuration(data.performance.avgDuration));
        this.updateElement('task-completion-speed', `${data.performance.completionSpeed} tasks/min`);
        this.updateElement('agent-response-latency', `${data.performance.responseLatency}ms`);
        this.updateElement('workflow-error-rate', `${data.performance.errorRate}%`);
        this.updateElement('resource-efficiency', `${data.performance.resourceEfficiency}%`);
        this.updateElement('scalability-index', data.performance.scalabilityIndex.toFixed(1));

        // Update history list
        this.renderWorkflowHistory(data.history);
    }

    /**
     * Update workflow analytics display
     */
    updateWorkflowAnalytics(data) {
        if (!data) return;

        // Update chart placeholders with data
        this.updateAnalyticsCharts(data);
    }

    /**
     * Update workflow visualization
     */
    updateWorkflowVisualization() {
        if (!this.canvas) return;

        // Clear existing visualization
        this.clearCanvas();

        // Generate workflow data based on current type
        const workflowData = this.generateWorkflowData(this.currentWorkflowType);

        // Render nodes and connections
        this.renderWorkflowNodes(workflowData.nodes);
        this.renderWorkflowConnections(workflowData.connections);

        // Apply zoom and positioning
        this.applyCanvasTransform();
    }

    /**
     * Render active workflows list
     */
    renderActiveWorkflows(workflows) {
        const container = document.getElementById('active-workflows-list');
        if (!container) return;

        if (!workflows || workflows.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔄</div>
                    <div class="empty-text">No active workflows</div>
                    <div class="empty-hint">Active workflows will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = workflows.map(workflow => `
            <div class="workflow-item" data-workflow-id="${workflow.id}">
                <div class="workflow-item-header">
                    <div>
                        <div class="workflow-item-title">${this.escapeHtml(workflow.name)}</div>
                        <div class="workflow-item-id">${workflow.id}</div>
                    </div>
                    <div class="workflow-item-status ${workflow.status}">
                        ${workflow.status}
                    </div>
                </div>

                <div class="workflow-item-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${workflow.progress}%"></div>
                    </div>
                    <div class="progress-text">${workflow.completedTasks}/${workflow.taskCount} tasks</div>
                </div>

                <div class="workflow-item-meta">
                    <span>Agents: ${workflow.agentCount}</span>
                    <span>Duration: ${this.formatDuration(workflow.duration)}</span>
                    <span>Type: ${workflow.type}</span>
                </div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.workflow-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const workflowId = e.currentTarget.getAttribute('data-workflow-id');
                this.selectWorkflow(workflowId);
            });
        });
    }

    /**
     * Render workflow history
     */
    renderWorkflowHistory(history) {
        const container = document.getElementById('workflow-history-list');
        if (!container) return;

        if (!history || history.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📚</div>
                    <div class="empty-text">No workflow history</div>
                    <div class="empty-hint">Completed workflows will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = history.map(item => `
            <div class="workflow-item" data-workflow-id="${item.id}">
                <div class="workflow-item-header">
                    <div>
                        <div class="workflow-item-title">${this.escapeHtml(item.name)}</div>
                        <div class="workflow-item-id">${item.id}</div>
                    </div>
                    <div class="workflow-item-status ${item.status}">
                        ${item.status}
                    </div>
                </div>

                <div class="workflow-item-meta">
                    <span>Started: ${item.formattedStart}</span>
                    <span>Duration: ${this.formatDuration(item.duration)}</span>
                    <span>Tasks: ${item.task_count || 0}</span>
                    <span>Type: ${item.type}</span>
                </div>
            </div>
        `).join('');
    }

    /**
     * Update analytics charts (placeholder implementation)
     */
    updateAnalyticsCharts(data) {
        // In a real implementation, this would update actual charts
        const charts = [
            'throughput-chart',
            'utilization-chart',
            'success-rates-chart',
            'delegation-chart'
        ];

        const chartData = {
            'throughput-chart': 'Workflow throughput trends',
            'utilization-chart': 'Agent utilization patterns',
            'success-rates-chart': 'Task success rate analytics',
            'delegation-chart': 'Delegation pattern analysis'
        };

        charts.forEach(chartId => {
            const chartEl = document.getElementById(chartId);
            if (chartEl) {
                chartEl.innerHTML = `
                    <div style="text-align: center; color: var(--text-secondary);">
                        📊 ${chartData[chartId]}<br>
                        <small>Real-time data streaming active</small>
                    </div>
                `;
            }
        });
    }

    /**
     * Generate workflow data for visualization
     */
    generateWorkflowData(type) {
        // Generate different layouts based on workflow type
        const layouts = {
            strategic: this.generateStrategicWorkflow(),
            operational: this.generateOperationalWorkflow(),
            evolutionary: this.generateEvolutionaryWorkflow(),
            all: this.generateAllWorkflows()
        };

        return layouts[type] || layouts.strategic;
    }

    /**
     * Generate strategic workflow layout
     */
    generateStrategicWorkflow() {
        return {
            nodes: [
                { id: 'mastermind', type: 'agent', label: 'MastermindAgent', x: 400, y: 100, status: 'active' },
                { id: 'strategy-1', type: 'task', label: 'Strategic Analysis', x: 200, y: 250, status: 'completed' },
                { id: 'strategy-2', type: 'task', label: 'Goal Planning', x: 400, y: 250, status: 'active' },
                { id: 'strategy-3', type: 'task', label: 'Resource Allocation', x: 600, y: 250, status: 'pending' },
                { id: 'coordinator', type: 'agent', label: 'CoordinatorAgent', x: 400, y: 400, status: 'active' },
                { id: 'execution-1', type: 'task', label: 'Task Delegation', x: 200, y: 550, status: 'active' },
                { id: 'execution-2', type: 'task', label: 'Progress Monitoring', x: 400, y: 550, status: 'pending' },
                { id: 'execution-3', type: 'task', label: 'Result Aggregation', x: 600, y: 550, status: 'pending' }
            ],
            connections: [
                { from: 'mastermind', to: 'strategy-1', type: 'delegation' },
                { from: 'mastermind', to: 'strategy-2', type: 'delegation' },
                { from: 'mastermind', to: 'strategy-3', type: 'delegation' },
                { from: 'strategy-1', to: 'coordinator', type: 'completion' },
                { from: 'strategy-2', to: 'coordinator', type: 'completion' },
                { from: 'strategy-3', to: 'coordinator', type: 'completion' },
                { from: 'coordinator', to: 'execution-1', type: 'delegation' },
                { from: 'coordinator', to: 'execution-2', type: 'delegation' },
                { from: 'coordinator', to: 'execution-3', type: 'delegation' }
            ]
        };
    }

    /**
     * Generate operational workflow layout
     */
    generateOperationalWorkflow() {
        return {
            nodes: [
                { id: 'coordinator', type: 'agent', label: 'CoordinatorAgent', x: 400, y: 100, status: 'active' },
                { id: 'task-1', type: 'task', label: 'Code Analysis', x: 150, y: 250, status: 'completed' },
                { id: 'task-2', type: 'task', label: 'Documentation', x: 300, y: 250, status: 'active' },
                { id: 'task-3', type: 'task', label: 'Testing', x: 450, y: 250, status: 'pending' },
                { id: 'task-4', type: 'task', label: 'Optimization', x: 600, y: 250, status: 'pending' },
                { id: 'simple-coder', type: 'agent', label: 'SimpleCoder', x: 200, y: 400, status: 'active' },
                { id: 'analyzer', type: 'agent', label: 'Analyzer', x: 400, y: 400, status: 'busy' },
                { id: 'validator', type: 'agent', label: 'Validator', x: 600, y: 400, status: 'ready' }
            ],
            connections: [
                { from: 'coordinator', to: 'task-1', type: 'delegation' },
                { from: 'coordinator', to: 'task-2', type: 'delegation' },
                { from: 'coordinator', to: 'task-3', type: 'delegation' },
                { from: 'coordinator', to: 'task-4', type: 'delegation' },
                { from: 'task-1', to: 'simple-coder', type: 'assignment' },
                { from: 'task-2', to: 'analyzer', type: 'assignment' },
                { from: 'task-3', to: 'validator', type: 'assignment' },
                { from: 'task-4', to: 'simple-coder', type: 'assignment' }
            ]
        };
    }

    /**
     * Generate evolutionary workflow layout
     */
    generateEvolutionaryWorkflow() {
        return {
            nodes: [
                { id: 'sea', type: 'agent', label: 'StrategicEvolutionAgent', x: 400, y: 100, status: 'active' },
                { id: 'blueprint', type: 'task', label: 'System Analysis', x: 200, y: 250, status: 'completed' },
                { id: 'audit', type: 'task', label: 'Performance Audit', x: 400, y: 250, status: 'active' },
                { id: 'improvement', type: 'task', label: 'Improvement Planning', x: 600, y: 250, status: 'pending' },
                { id: 'self-improve', type: 'agent', label: 'SelfImproveAgent', x: 400, y: 400, status: 'ready' },
                { id: 'code-change', type: 'task', label: 'Code Modification', x: 200, y: 550, status: 'pending' },
                { id: 'validation', type: 'task', label: 'Change Validation', x: 400, y: 550, status: 'pending' },
                { id: 'deployment', type: 'task', label: 'Safe Deployment', x: 600, y: 550, status: 'pending' }
            ],
            connections: [
                { from: 'sea', to: 'blueprint', type: 'delegation' },
                { from: 'sea', to: 'audit', type: 'delegation' },
                { from: 'sea', to: 'improvement', type: 'delegation' },
                { from: 'blueprint', to: 'self-improve', type: 'completion' },
                { from: 'audit', to: 'self-improve', type: 'completion' },
                { from: 'improvement', to: 'self-improve', type: 'completion' },
                { from: 'self-improve', to: 'code-change', type: 'delegation' },
                { from: 'self-improve', to: 'validation', type: 'delegation' },
                { from: 'self-improve', to: 'deployment', type: 'delegation' }
            ]
        };
    }

    /**
     * Generate all workflows combined layout
     */
    generateAllWorkflows() {
        return {
            nodes: [
                // Strategic layer
                { id: 'mastermind', type: 'agent', label: 'MastermindAgent', x: 400, y: 50, status: 'active' },
                { id: 'coordinator', type: 'agent', label: 'CoordinatorAgent', x: 400, y: 150, status: 'active' },

                // Operational layer
                { id: 'simple-coder', type: 'agent', label: 'SimpleCoder', x: 150, y: 300, status: 'active' },
                { id: 'analyzer', type: 'agent', label: 'Analyzer', x: 300, y: 300, status: 'busy' },
                { id: 'validator', type: 'agent', label: 'Validator', x: 500, y: 300, status: 'ready' },
                { id: 'github', type: 'agent', label: 'GitHub Agent', x: 650, y: 300, status: 'ready' },

                // Evolutionary layer
                { id: 'sea', type: 'agent', label: 'StrategicEvolutionAgent', x: 400, y: 450, status: 'active' },
                { id: 'self-improve', type: 'agent', label: 'SelfImproveAgent', x: 400, y: 550, status: 'ready' },

                // Tasks
                { id: 'task-analysis', type: 'task', label: 'Analysis', x: 200, y: 200, status: 'completed' },
                { id: 'task-coding', type: 'task', label: 'Coding', x: 150, y: 400, status: 'active' },
                { id: 'task-testing', type: 'task', label: 'Testing', x: 300, y: 400, status: 'pending' },
                { id: 'task-evolution', type: 'task', label: 'Evolution', x: 500, y: 400, status: 'pending' }
            ],
            connections: [
                { from: 'mastermind', to: 'coordinator', type: 'delegation' },
                { from: 'coordinator', to: 'task-analysis', type: 'delegation' },
                { from: 'task-analysis', to: 'simple-coder', type: 'assignment' },
                { from: 'task-analysis', to: 'analyzer', type: 'assignment' },
                { from: 'coordinator', to: 'task-coding', type: 'delegation' },
                { from: 'coordinator', to: 'task-testing', type: 'delegation' },
                { from: 'coordinator', to: 'task-evolution', type: 'delegation' },
                { from: 'task-coding', to: 'simple-coder', type: 'assignment' },
                { from: 'task-testing', to: 'validator', type: 'assignment' },
                { from: 'task-evolution', to: 'sea', type: 'assignment' },
                { from: 'sea', to: 'self-improve', type: 'delegation' }
            ]
        };
    }

    /**
     * Render workflow nodes on canvas
     */
    renderWorkflowNodes(nodes) {
        if (!this.canvas) return;

        nodes.forEach(node => {
            const nodeEl = document.createElement('div');
            nodeEl.className = `workflow-node ${node.type}-node ${node.status}`;
            nodeEl.style.left = `${node.x}px`;
            nodeEl.style.top = `${node.y}px`;
            nodeEl.setAttribute('data-node-id', node.id);

            nodeEl.innerHTML = `
                <div class="node-label">${node.label}</div>
                <div class="node-status">${node.status}</div>
            `;

            // Add click handler
            nodeEl.addEventListener('click', () => this.selectNode(node.id));

            this.canvas.appendChild(nodeEl);
            this.nodes.set(node.id, { ...node, element: nodeEl });
        });
    }

    /**
     * Render workflow connections
     */
    renderWorkflowConnections(connections) {
        if (!this.canvas) return;

        connections.forEach(connection => {
            const fromNode = this.nodes.get(connection.from);
            const toNode = this.nodes.get(connection.to);

            if (!fromNode || !toNode) return;

            const fromRect = fromNode.element.getBoundingClientRect();
            const toRect = toNode.element.getBoundingClientRect();
            const canvasRect = this.canvas.getBoundingClientRect();

            const x1 = fromRect.left + fromRect.width / 2 - canvasRect.left;
            const y1 = fromRect.top + fromRect.height / 2 - canvasRect.top;
            const x2 = toRect.left + toRect.width / 2 - canvasRect.left;
            const y2 = toRect.top + toRect.height / 2 - canvasRect.top;

            // Create SVG connection
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.className = 'workflow-connection';
            svg.style.position = 'absolute';
            svg.style.left = '0';
            svg.style.top = '0';
            svg.style.width = '100%';
            svg.style.height = '100%';
            svg.style.pointerEvents = 'none';
            svg.style.zIndex = '1';

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.className = 'connection-line';
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);

            svg.appendChild(line);
            this.canvas.appendChild(svg);
        });
    }

    /**
     * Clear canvas
     */
    clearCanvas() {
        if (!this.canvas) return;

        // Remove all nodes and connections
        this.canvas.querySelectorAll('.workflow-node, .workflow-connection').forEach(el => {
            el.remove();
        });

        this.nodes.clear();
        this.connections = [];
    }

    /**
     * Apply canvas transform (zoom and pan)
     */
    applyCanvasTransform() {
        if (!this.canvas) return;

        this.canvas.style.transform = `scale(${this.zoomLevel})`;
        this.canvas.style.transformOrigin = 'center center';
    }

    /**
     * Select workflow type
     */
    selectWorkflowType(type) {
        this.currentWorkflowType = type;

        // Update UI
        document.querySelectorAll('.workflow-type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-workflow-type="${type}"]`).classList.add('active');

        // Update visualization
        this.updateWorkflowVisualization();
    }

    /**
     * Select workflow
     */
    selectWorkflow(workflowId) {
        this.selectedWorkflow = workflowId;
        // In a real implementation, this would highlight the selected workflow
        // and show detailed information
        console.log('Selected workflow:', workflowId);
    }

    /**
     * Select node
     */
    selectNode(nodeId) {
        const node = this.nodes.get(nodeId);
        if (node) {
            console.log('Selected node:', node);
            // In a real implementation, this would show node details
        }
    }

    /**
     * Initialize canvas interactions
     */
    initializeCanvas() {
        if (!this.canvas) return;

        // Add pan and zoom functionality
        let isDragging = false;
        let startX, startY;

        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
        });

        this.canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            // Pan functionality (placeholder)
            console.log('Panning:', deltaX, deltaY);
        });

        this.canvas.addEventListener('mouseup', () => {
            isDragging = false;
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomLevel *= zoomFactor;
            this.zoomLevel = Math.max(0.1, Math.min(3, this.zoomLevel));
            this.applyCanvasTransform();
        });
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Workflow type selection
        document.querySelectorAll('.workflow-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = e.currentTarget.getAttribute('data-workflow-type');
                this.selectWorkflowType(type);
            });
        });

        // Control buttons
        const refreshBtn = document.getElementById('refresh-workflows-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const exportBtn = document.getElementById('export-workflow-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportWorkflows());
        }

        // Visualization controls
        const zoomInBtn = document.getElementById('zoom-in-btn');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => {
                this.zoomLevel *= 1.2;
                this.zoomLevel = Math.min(3, this.zoomLevel);
                this.applyCanvasTransform();
            });
        }

        const zoomOutBtn = document.getElementById('zoom-out-btn');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => {
                this.zoomLevel *= 0.8;
                this.zoomLevel = Math.max(0.1, this.zoomLevel);
                this.applyCanvasTransform();
            });
        }

        const fitViewBtn = document.getElementById('fit-view-btn');
        if (fitViewBtn) {
            fitViewBtn.addEventListener('click', () => {
                this.zoomLevel = 1;
                this.applyCanvasTransform();
            });
        }

        const toggleAnimationsBtn = document.getElementById('toggle-animations-btn');
        if (toggleAnimationsBtn) {
            toggleAnimationsBtn.addEventListener('click', () => {
                this.animationsEnabled = !this.animationsEnabled;
                toggleAnimationsBtn.textContent = this.animationsEnabled ? '🎬 Animations' : '🎭 Static';
            });
        }

        // Detail level selector
        const detailLevelSelect = document.getElementById('workflow-detail-level');
        if (detailLevelSelect) {
            detailLevelSelect.addEventListener('change', (e) => {
                this.detailLevel = e.target.value;
                this.updateWorkflowVisualization();
            });
        }

        // Panel tab switching
        document.querySelectorAll('.panel-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const panelName = e.currentTarget.getAttribute('data-panel');
                this.switchPanel(panelName);
            });
        });

        // History filters
        const historyTimeframe = document.getElementById('history-timeframe');
        if (historyTimeframe) {
            historyTimeframe.addEventListener('change', () => this.filterWorkflowHistory());
        }

        const historyStatus = document.getElementById('history-status');
        if (historyStatus) {
            historyStatus.addEventListener('change', () => this.filterWorkflowHistory());
        }

        const historySearch = document.getElementById('history-search');
        if (historySearch) {
            historySearch.addEventListener('input', () => this.filterWorkflowHistory());
        }

        // Analytics timeframe
        const analyticsTimeframe = document.getElementById('analytics-timeframe');
        if (analyticsTimeframe) {
            analyticsTimeframe.addEventListener('change', () => this.refreshAnalytics());
        }

        const refreshAnalyticsBtn = document.getElementById('refresh-analytics-btn');
        if (refreshAnalyticsBtn) {
            refreshAnalyticsBtn.addEventListener('click', () => this.refreshAnalytics());
        }
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
        document.getElementById(`${panelName}-workflows-panel`).classList.add('active');
    }

    /**
     * Filter workflow history
     */
    filterWorkflowHistory() {
        // In a real implementation, this would filter the history list
        console.log('Filtering workflow history...');
    }

    /**
     * Refresh analytics
     */
    async refreshAnalytics() {
        try {
            await this.loadData();
            this.showNotification('Analytics refreshed successfully', 'success');
        } catch (error) {
            console.error('Analytics refresh failed:', error);
            this.showNotification('Failed to refresh analytics', 'error');
        }
    }

    /**
     * Export workflows
     */
    async exportWorkflows() {
        try {
            const exportData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                currentType: this.currentWorkflowType,
                activeWorkflows: this.workflowData?.active?.workflows || [],
                workflowHistory: this.workflowData?.history?.history || [],
                analytics: this.workflowData?.analytics || {}
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-workflows-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Workflows exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export workflows', 'error');
        }
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
     * Format duration in milliseconds to human readable
     */
    formatDuration(ms) {
        if (!ms || ms === 0) return '0s';

        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) return `${hours}h ${minutes % 60}m`;
        if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
        return `${seconds}s`;
    }

    /**
     * Generate mock workflow data for demonstration
     */
    generateMockWorkflowData() {
        return {
            active: {
                workflows: [
                    {
                        id: 'wf-001',
                        name: 'Strategic Code Analysis',
                        type: 'strategic',
                        status: 'active',
                        progress: 65,
                        tasks: 8,
                        completedTasks: 5,
                        agentCount: 3,
                        duration: 45000
                    },
                    {
                        id: 'wf-002',
                        name: 'Documentation Generation',
                        type: 'operational',
                        status: 'pending',
                        progress: 20,
                        tasks: 12,
                        completedTasks: 2,
                        agentCount: 2,
                        duration: 12000
                    }
                ],
                stats: {
                    activeCount: 2,
                    completedToday: 7,
                    delegationEfficiency: 87,
                    successRate: 94
                }
            },
            history: {
                history: [
                    {
                        id: 'wf-his-001',
                        name: 'Performance Optimization',
                        status: 'completed',
                        type: 'evolutionary',
                        start_time: new Date(Date.now() - 3600000).toISOString(),
                        end_time: new Date(Date.now() - 1800000).toISOString(),
                        task_count: 15
                    }
                ],
                performance: {
                    avgDuration: 240000,
                    completionSpeed: 2.5,
                    responseLatency: 150,
                    errorRate: 2.1,
                    resourceEfficiency: 89,
                    scalabilityIndex: 7.8
                }
            },
            analytics: {
                throughput: [],
                utilization: [],
                success: [],
                delegation: []
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
    window.WorkflowTab = WorkflowTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = WorkflowTab;
}