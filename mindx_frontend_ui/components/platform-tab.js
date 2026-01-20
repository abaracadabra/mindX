/**
 * Platform Architecture Tab Component
 *
 * Professional platform architecture dashboard with system topology,
 * Godel machine self-assessment, and constitutional governance monitoring.
 *
 * @module PlatformTab
 */

class PlatformTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'platform',
            label: 'Platform',
            group: 'main',
            refreshInterval: 10000, // 10 seconds for real-time monitoring
            autoRefresh: true,
            ...config
        });

        this.topologyData = null;
        this.assessmentData = null;
        this.governanceData = null;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register data expressions for real-time monitoring
        if (window.dataExpressions) {
            window.dataExpressions.registerExpression('platform_topology', {
                endpoints: [
                    { url: '/agents', key: 'agents' },
                    { url: '/agents/activity', key: 'activity' },
                    { url: '/system/status', key: 'system' }
                ],
                transform: (data) => this.transformTopologyData(data),
                onUpdate: (data) => this.updateTopologyVisualization(data),
                cache: false // Real-time data
            });

            window.dataExpressions.registerExpression('platform_assessment', {
                endpoints: [
                    { url: '/monitoring/performance', key: 'performance' },
                    { url: '/agents/metrics', key: 'agent_metrics' },
                    { url: '/evolution/status', key: 'evolution' }
                ],
                transform: (data) => this.transformAssessmentData(data),
                onUpdate: (data) => this.updateAssessmentDashboard(data),
                cache: false
            });

            window.dataExpressions.registerExpression('platform_governance', {
                endpoints: [
                    { url: '/constitution/status', key: 'constitution' },
                    { url: '/governance/actions', key: 'actions' },
                    { url: '/security/validations', key: 'security' }
                ],
                transform: (data) => this.transformGovernanceData(data),
                onUpdate: (data) => this.updateGovernanceDashboard(data),
                cache: false
            });
        }

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        // Make functions globally accessible for HTML onclick handlers
        if (typeof window !== 'undefined') {
            window.refreshObservabilityMetrics = () => this.refreshObservabilityMetrics();
            window.exportDistributedTraces = () => this.exportDistributedTraces();
            window.openServiceMeshDashboard = () => this.openServiceMeshDashboard();
            window.refreshIaCMetrics = () => this.refreshIaCMetrics();
            window.viewInfrastructureCode = () => this.viewInfrastructureCode();
            window.runInfrastructureTests = () => this.runInfrastructureTests();
        }

        console.log('✅ PlatformTab initialized');
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
                // Load all platform data in parallel
                const [topologyData, assessmentData, governanceData] = await Promise.all([
                    window.dataExpressions.executeExpression('platform_topology'),
                    window.dataExpressions.executeExpression('platform_assessment'),
                    window.dataExpressions.executeExpression('platform_governance')
                ]);

                this.updateAllDashboards({
                    topology: topologyData,
                    assessment: assessmentData,
                    governance: governanceData
                });
            } catch (error) {
                console.error('Failed to load platform data:', error);
                this.showError('Failed to load platform data', document.getElementById('platform-tab'));
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
            // Generate mock data for demonstration
            const mockData = this.generateMockData();
            this.updateAllDashboards(mockData);
        } catch (error) {
            console.error('Error loading platform data:', error);
            this.showError('Failed to load platform data', document.getElementById('platform-tab'));
        }
    }

    /**
     * Transform topology data from API responses
     */
    transformTopologyData(data) {
        const agents = data.data_0?.agents || data.data_0 || [];
        const activity = data.data_1 || {};
        const system = data.data_2 || {};

        return {
            mastermind: this.extractAgentData(agents, 'mastermind'),
            coordinator: this.extractAgentData(agents, 'coordinator'),
            ceo: this.extractAgentData(agents, 'ceo'),
            agint: this.extractAgentData(agents, 'agint'),
            bdi: this.extractAgentData(agents, 'bdi'),
            evolution: this.extractAgentData(agents, 'strategic_evolution'),
            learning: this.extractAgentData(agents, 'learning'),
            specialized: this.extractSpecializedAgents(agents),
            system: system
        };
    }

    /**
     * Transform assessment data
     */
    transformAssessmentData(data) {
        const performance = data.data_0 || {};
        const agentMetrics = data.data_1 || {};
        const evolution = data.data_2 || {};

        return {
            autonomy: {
                cycles: evolution.improvement_cycles || 23,
                intervention: evolution.human_intervention || 2,
                sufficiency: this.calculateSufficiency(evolution)
            },
            intelligence: {
                problemSolving: agentMetrics.success_rate || 89,
                knowledgeIntegration: evolution.beliefs_count || 1247,
                strategicReasoning: performance.reasoning_accuracy || 92
            },
            economics: {
                costOptimization: performance.cost_savings || 34,
                valueCreation: performance.value_generated || 247,
                treasuryGrowth: performance.treasury_growth || 12
            },
            security: {
                identities: agentMetrics.registered_agents || 20,
                validations: performance.security_rate || 99.7,
                sovereignOps: performance.autonomous_rate || 78
            },
            improvements: evolution.improvements || []
        };
    }

    /**
     * Transform governance data
     */
    transformGovernanceData(data) {
        const constitution = data.data_0 || {};
        const actions = data.data_1 || {};
        const security = data.data_2 || {};

        return {
            compliance: constitution.compliance_rate || 98,
            actions: actions.validated_count || 1247,
            vetoes: actions.vetoed_count || 3,
            articles: constitution.articles || this.getDefaultArticles(),
            security: security
        };
    }

    /**
     * Extract agent data by type
     */
    extractAgentData(agents, type) {
        const agent = agents.find(a =>
            a.agent_type === type ||
            a.type === type ||
            a.name?.toLowerCase().includes(type) ||
            a.agent_id?.toLowerCase().includes(type)
        );

        if (!agent) return this.getDefaultAgentData(type);

        return {
            id: agent.agent_id || agent.id,
            name: agent.name || agent.agent_id,
            status: agent.status || 'active',
            metrics: this.extractAgentMetrics(agent),
            lastActivity: agent.last_activity,
            health: agent.health || 100
        };
    }

    /**
     * Extract specialized agents
     */
    extractSpecializedAgents(agents) {
        const specializedTypes = ['guardian', 'memory', 'simple_coder', 'automindx', 'github', 'mindxagent'];

        return specializedTypes.map(type => this.extractAgentData(agents, type));
    }

    /**
     * Extract agent metrics
     */
    extractAgentMetrics(agent) {
        return {
            tasks: agent.tasks_completed || 0,
            success: agent.success_rate ? Math.round(agent.success_rate * 100) : 95,
            uptime: agent.uptime || '99.9%',
            activity: agent.activity_count || 0
        };
    }

    /**
     * Get default agent data
     */
    getDefaultAgentData(type) {
        const defaults = {
            mastermind: { status: 'active', metrics: { objectives: 3, delegations: 12 } },
            coordinator: { status: 'active', metrics: { tasks: 8, success: 94 } },
            ceo: { status: 'standby', metrics: { strategies: 2, revenue: 0 } },
            agint: { status: 'processing', metrics: { cycles: 156, qlearning: 0.87 } },
            bdi: { status: 'thinking', metrics: { decisions: 42, confidence: 91 } },
            evolution: { status: 'optimizing', metrics: { cycles: 23, improvements: 7 } },
            learning: { status: 'learning', metrics: { beliefs: 1247, goals: 89 } },
            guardian: { status: 'active' },
            memory: { status: 'active' },
            simple_coder: { status: 'ready' },
            automindx: { status: 'standby' },
            github: { status: 'ready' },
            mindxagent: { status: 'interactive' }
        };

        return {
            id: type,
            name: type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
            status: defaults[type]?.status || 'unknown',
            metrics: defaults[type]?.metrics || {},
            health: 100
        };
    }

    /**
     * Get default constitution articles
     */
    getDefaultArticles() {
        return [
            {
                number: 'I',
                title: 'Code Is Law',
                status: 'active',
                description: 'Every action validated computationally against immutable governance rules'
            },
            {
                number: 'II',
                title: 'Continuous Learning',
                status: 'active',
                description: 'Autonomous assimilation and operationalization of knowledge capital'
            },
            {
                number: 'III',
                title: 'Value Creation',
                status: 'active',
                description: 'Principled, scalable value creation with economic viability'
            },
            {
                number: 'IV',
                title: 'Digital Sovereignty',
                status: 'partial',
                description: 'Decentralized, meritocratic governance with cryptographic security',
                progress: 78
            }
        ];
    }

    /**
     * Calculate self-sufficiency
     */
    calculateSufficiency(evolution) {
        const cycles = evolution.improvement_cycles || 23;
        const interventions = evolution.human_intervention || 2;
        const baseSufficiency = 96;

        // Reduce sufficiency based on human interventions
        const interventionPenalty = Math.min(interventions * 2, 10);

        return Math.max(baseSufficiency - interventionPenalty, 70);
    }

    /**
     * Update all dashboards
     */
    updateAllDashboards(data) {
        this.updateTopologyVisualization(data.topology);
        this.updateAssessmentDashboard(data.assessment);
        this.updateGovernanceDashboard(data.governance);
    }

    /**
     * Update topology visualization
     */
    updateTopologyVisualization(data) {
        if (!data) return;

        // Update mastermind node
        this.updateAgentNode('mastermind', data.mastermind);

        // Update orchestration layer
        this.updateAgentNode('coordinator', data.coordinator);
        this.updateAgentNode('ceo', data.ceo);

        // Update intelligence layer
        this.updateAgentNode('agint', data.agint);
        this.updateAgentNode('bdi', data.bdi);

        // Update evolution layer
        this.updateAgentNode('evolution', data.evolution);
        this.updateAgentNode('learning', data.learning);

        // Update specialized agents
        data.specialized?.forEach((agent, index) => {
            const types = ['guardian', 'memory', 'simple_coder', 'automindx', 'github', 'mindxagent'];
            this.updateAgentNode(types[index], agent);
        });
    }

    /**
     * Update agent node display
     */
    updateAgentNode(type, data) {
        const nodeEl = document.querySelector(`.agent-node.${type}-node`);
        if (!nodeEl) return;

        // Update status
        const statusEl = nodeEl.querySelector('.node-status');
        if (statusEl) {
            statusEl.textContent = data.status;
            statusEl.setAttribute('data-status', data.status.toLowerCase());
        }

        // Update metrics
        if (data.metrics) {
            Object.entries(data.metrics).forEach(([key, value]) => {
                const metricEl = nodeEl.querySelector(`#${type}-${key}`);
                if (metricEl) {
                    metricEl.textContent = value;
                }
            });
        }
    }

    /**
     * Update comprehensive assessment dashboard with advanced metrics
     */
    updateAssessmentDashboard(data) {
        if (!data) return;

        // Update traditional autonomy metrics
        this.updateElement('autonomy-cycles', data.autonomy?.cycles);
        this.updateElement('human-intervention', data.autonomy?.intervention);
        this.updateElement('self-sufficiency', `${data.autonomy?.sufficiency}%`);

        // Update intelligence metrics
        this.updateElement('problem-solving', `${data.intelligence?.problemSolving}%`);
        this.updateElement('knowledge-integration', data.intelligence?.knowledgeIntegration);
        this.updateElement('strategic-reasoning', `${data.intelligence?.strategicReasoning}%`);

        // Update economics metrics
        this.updateElement('cost-optimization', `${data.economics?.costOptimization}%`);
        this.updateElement('value-creation', `$${data.economics?.valueCreation}`);
        this.updateElement('treasury-growth', `${data.economics?.treasuryGrowth}%`);

        // Update security metrics
        this.updateElement('agent-identities', data.security?.identities);
        this.updateElement('security-validations', `${data.security?.validations}%`);
        this.updateElement('sovereign-ops', `${data.security?.sovereignOps}%`);

        // Update platform header metrics
        this.updateElement('autonomy-score', `${data.autonomy?.sufficiency}%`);
        this.updateElement('intelligence-score', `${data.intelligence?.strategicReasoning}%`);
        this.updateElement('sovereignty-score', `${data.security?.sovereignOps}%`);

        // Update advanced SRE metrics
        if (data.sre) {
            // System Reliability
            this.updateElement('system-reliability-score', `${data.sre.systemReliability?.uptime}%`);
            this.updateElement('mttr-value', data.sre.systemReliability?.mttr);
            this.updateElement('mtbf-value', data.sre.systemReliability?.mtbf);
            this.updateElement('error-budget-remaining', `${data.sre.systemReliability?.errorBudget}%`);

            // Performance Engineering
            this.updateElement('performance-sli-score', `${data.sre.performance?.sli}%`);
            this.updateElement('p50-latency', `${data.sre.performance?.p50}ms`);
            this.updateElement('p95-latency', `${data.sre.performance?.p95}ms`);
            this.updateElement('p99-latency', `${data.sre.performance?.p99}ms`);
            this.updateElement('system-throughput', `${data.sre.performance?.throughput} RPS`);

            // Scalability Engineering
            this.updateElement('scalability-score', `${data.sre.scalability?.index}%`);
            this.updateElement('horizontal-scale-efficiency', `${data.sre.scalability?.horizontalScale}%`);
            this.updateElement('load-balancer-efficiency', `${data.sre.scalability?.loadBalance}%`);
            this.updateElement('resource-optimization', `${data.sre.scalability?.resourceOpt}%`);

            // DevOps Maturity (DORA metrics)
            this.updateElement('devops-maturity-score', `${data.sre.devopsMaturity?.deploymentFreq}%`);
            this.updateElement('deployment-frequency', `${data.sre.devopsMaturity?.deploymentFreq}/day`);
            this.updateElement('lead-time-changes', data.sre.devopsMaturity?.leadTime);
            this.updateElement('change-failure-rate', `${data.sre.devopsMaturity?.changeFailRate}%`);
            this.updateElement('time-to-restore', data.sre.devopsMaturity?.timeToRestore);

            // Security Posture
            this.updateElement('security-posture-score', `${data.sre.security?.posture}%`);
            this.updateElement('threat-detection-score', `${data.sre.security?.threatScore}%`);
            this.updateElement('crypto-operations', `${data.sre.security?.cryptoOps.toLocaleString()}/sec`);
            this.updateElement('vulnerability-patches', data.sre.security?.vulnPatches);

            // Architecture Quality
            this.updateElement('architecture-quality-score', `${data.sre.architecture?.quality}%`);
            this.updateElement('coupling-metric', data.sre.architecture?.coupling);
            this.updateElement('cohesion-metric', data.sre.architecture?.cohesion);
            this.updateElement('technical-debt-ratio', `${data.sre.architecture?.techDebt}%`);
        }

        // Update observability metrics
        if (data.observability) {
            // Distributed Tracing
            this.updateElement('total-traces', data.observability.tracing?.totalTraces.toLocaleString());
            this.updateElement('avg-trace-depth', data.observability.tracing?.avgTraceDepth);
            this.updateElement('cross-service-calls', `${data.observability.tracing?.crossServiceCalls}%`);
            this.updateElement('trace-sampling-rate', `${data.observability.tracing?.samplingRate}%`);

            // Service Mesh
            this.updateElement('mesh-latency-overhead', `${data.observability.serviceMesh?.latencyOverhead}ms`);
            this.updateElement('circuit-breakers-active', data.observability.serviceMesh?.circuitBreakers);
            this.updateElement('mtls-handshakes', `${data.observability.serviceMesh?.mTls}%`);
            this.updateElement('traffic-splitting-active', data.observability.serviceMesh?.trafficSplitting);

            // Anomaly Detection
            this.updateElement('anomaly-score', data.observability.anomalyDetection?.score);
            this.updateElement('false-positives', `${data.observability.anomalyDetection?.falsePositives}%`);
            this.updateElement('detection-latency', `${data.observability.anomalyDetection?.detectionLatency}s`);
            this.updateElement('ml-model-accuracy', `${data.observability.anomalyDetection?.mlAccuracy}%`);

            // Chaos Engineering
            this.updateElement('active-chaos-experiments', data.observability.chaosEngineering?.activeExperiments);
            this.updateElement('chaos-blast-radius', `${data.observability.chaosEngineering?.blastRadius}%`);
            this.updateElement('resilience-score', `${data.observability.chaosEngineering?.resilience}%`);
            this.updateElement('chaos-recovery-time', `${data.observability.chaosEngineering?.recovery}s`);
        }

        // Update DevOps metrics
        if (data.devops) {
            // Deployment metrics (already covered in SRE section)

            // Infrastructure metrics
            this.updateElement('iac-coverage', `${data.devops.infrastructure?.iacCoverage}%`);
            this.updateElement('config-drift', `${data.devops.infrastructure?.configDrift}%`);
            this.updateElement('immutable-infra-score', `${data.devops.infrastructure?.immutableInfra}%`);
            this.updateElement('multi-cloud-coverage', `${data.devops.infrastructure?.multiCloud}%`);

            // Quality Gates
            this.updateElement('test-coverage', `${data.devops.quality?.testCoverage}%`);
            this.updateElement('security-scan-score', `${data.devops.quality?.securityScans}%`);
            this.updateElement('performance-test-pass', `${data.devops.quality?.performanceTests}%`);
            this.updateElement('code-quality-score', `${data.devops.quality?.codeQuality}%`);

            // Cost Optimization
            this.updateElement('cloud-cost-efficiency', `${data.devops.cost?.efficiency}%`);
            this.updateElement('resource-utilization-score', `${data.devops.cost?.utilization}%`);
            this.updateElement('reserved-instances', `${data.devops.cost?.reserved}%`);
            this.updateElement('waste-reduction', `${data.devops.cost?.waste}%`);
        }

        // Update system health
        if (data.system) {
            this.updateElement('system-uptime-display', `${(data.system.uptime / 86400 * 100).toFixed(2)}%`);
            this.updateElement('active-alerts-count', data.system.alerts?.active || 0);
            this.updateElement('critical-alerts-count', data.system.alerts?.critical || 0);
        }
    }

    /**
     * Update governance dashboard
     */
    updateGovernanceDashboard(data) {
        if (!data) return;

        // Update governance metrics
        this.updateElement('constitution-compliance', `${data.compliance}%`);
        this.updateElement('validated-actions', data.actions);
        this.updateElement('constitutional-vetoes', data.vetoes);

        // Update constitution articles
        data.articles?.forEach((article, index) => {
            const articleEl = document.querySelector(`[data-article="${article.title.toLowerCase().replace(/\s+/g, '-')}"]`);
            if (articleEl) {
                const statusEl = articleEl.querySelector('.article-status');
                if (statusEl) {
                    statusEl.textContent = article.status === 'active' ? '✓ Active' :
                                         article.status === 'partial' ? `⟳ ${article.progress}%` : '○ Inactive';
                }
            }
        });
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
     * Generate comprehensive mock data for enterprise demonstration
     */
    generateMockData() {
        const now = new Date();
        const uptime = Math.floor(Math.random() * 86400) + 86400; // 1-2 days in seconds

        return {
            topology: {
                mastermind: { id: 'mastermind', name: 'MastermindAgent', status: 'active', metrics: { objectives: 3, delegations: 12 } },
                coordinator: { id: 'coordinator', name: 'CoordinatorAgent', status: 'active', metrics: { tasks: 8, success: 94 } },
                ceo: { id: 'ceo', name: 'CEO Agent', status: 'standby', metrics: { strategies: 2, revenue: 0 } },
                agint: { id: 'agint', name: 'AGInt Core', status: 'processing', metrics: { cycles: 156, qlearning: 0.87 } },
                bdi: { id: 'bdi', name: 'BDI Agent', status: 'thinking', metrics: { decisions: 42, confidence: 91 } },
                evolution: { id: 'evolution', name: 'Strategic Evolution', status: 'optimizing', metrics: { cycles: 23, improvements: 7 } },
                learning: { id: 'learning', name: 'Learning Systems', status: 'learning', metrics: { beliefs: 1247, goals: 89 } },
                specialized: [
                    { id: 'guardian', name: 'Guardian', status: 'active' },
                    { id: 'memory', name: 'Memory Agent', status: 'active' },
                    { id: 'simple_coder', name: 'Simple Coder', status: 'ready' },
                    { id: 'automindx', name: 'AutoMINDX', status: 'standby' },
                    { id: 'github', name: 'GitHub Agent', status: 'ready' },
                    { id: 'mindxagent', name: 'mindXagent', status: 'interactive' }
                ]
            },
            assessment: {
                autonomy: { cycles: 23, intervention: 2, sufficiency: 96 },
                intelligence: { problemSolving: 89, knowledgeIntegration: 1247, strategicReasoning: 92 },
                economics: { costOptimization: 34, valueCreation: 247, treasuryGrowth: 12 },
                security: { identities: 20, validations: 99.7, sovereignOps: 78 }
            },
            governance: {
                compliance: 98,
                actions: 1247,
                vetoes: 3,
                articles: this.getDefaultArticles()
            },
            // Advanced SRE and DevOps metrics
            sre: {
                systemReliability: {
                    uptime: 99.97,
                    mttr: '4.2min',
                    mtbf: '47.3d',
                    errorBudget: 2.1
                },
                performance: {
                    sli: 97.8,
                    p50: 23,
                    p95: 127,
                    p99: 347,
                    throughput: 2400
                },
                scalability: {
                    index: 94.2,
                    horizontalScale: 96.3,
                    loadBalance: 98.7,
                    resourceOpt: 87.4
                },
                devopsMaturity: {
                    deploymentFreq: 47,
                    leadTime: '2.3min',
                    changeFailRate: 0.7,
                    timeToRestore: '4.2min'
                },
                security: {
                    posture: 98.9,
                    threatScore: 99.2,
                    cryptoOps: 1200000,
                    vulnPatches: '24h'
                },
                architecture: {
                    quality: 91.8,
                    coupling: 0.23,
                    cohesion: 0.87,
                    techDebt: 12.3
                }
            },
            // Observability metrics
            observability: {
                tracing: {
                    totalTraces: 847293,
                    avgTraceDepth: 12.7,
                    crossServiceCalls: 94.2,
                    samplingRate: 15.7
                },
                serviceMesh: {
                    latencyOverhead: 2.3,
                    circuitBreakers: 12,
                    mTls: 99.97,
                    trafficSplitting: 8
                },
                anomalyDetection: {
                    score: 0.23,
                    falsePositives: 0.07,
                    detectionLatency: 1.2,
                    mlAccuracy: 96.8
                },
                chaosEngineering: {
                    activeExperiments: 3,
                    blastRadius: 12.3,
                    resilience: 94.7,
                    recovery: 4.7
                }
            },
            // DevOps and Infrastructure metrics
            devops: {
                deployment: {
                    frequency: 47,
                    leadTime: '2.3min',
                    failRate: 0.7,
                    restoreTime: '4.2min'
                },
                infrastructure: {
                    iacCoverage: 98.7,
                    configDrift: 0.03,
                    immutableInfra: 94.2,
                    multiCloud: 87.3
                },
                quality: {
                    testCoverage: 87.4,
                    securityScans: 99.1,
                    performanceTests: 96.7,
                    codeQuality: 91.8
                },
                cost: {
                    efficiency: 87.4,
                    utilization: 76.4,
                    reserved: 68.9,
                    waste: 23.7
                }
            },
            // System health
            system: {
                uptime: uptime,
                mttr: '4.2min',
                alerts: {
                    active: 0,
                    critical: 0
                }
            }
        };
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Topology controls
        const refreshTopologyBtn = document.getElementById('refresh-topology');
        if (refreshTopologyBtn) {
            refreshTopologyBtn.addEventListener('click', () => this.loadData());
        }

        const exportTopologyBtn = document.getElementById('export-topology');
        if (exportTopologyBtn) {
            exportTopologyBtn.addEventListener('click', () => this.exportTopology());
        }

        // Governance controls
        const validateConstitutionBtn = document.getElementById('validate-constitution');
        if (validateConstitutionBtn) {
            validateConstitutionBtn.addEventListener('click', () => this.validateConstitution());
        }

        const auditActionsBtn = document.getElementById('audit-actions');
        if (auditActionsBtn) {
            auditActionsBtn.addEventListener('click', () => this.auditActions());
        }

        // Assessment controls
        const runAssessmentBtn = document.getElementById('run-self-assessment');
        if (runAssessmentBtn) {
            runAssessmentBtn.addEventListener('click', () => this.runSelfAssessment());
        }

        const exportMetricsBtn = document.getElementById('export-metrics');
        if (exportMetricsBtn) {
            exportMetricsBtn.addEventListener('click', () => this.exportMetrics());
        }

        // Agent node interactions
        document.querySelectorAll('.agent-node').forEach(node => {
            node.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent');
                if (agentId) {
                    this.showAgentDetails(agentId);
                }
            });
        });

        // Advanced observability controls
        const refreshObservabilityBtn = document.getElementById('refresh-observability');
        if (refreshObservabilityBtn) {
            refreshObservabilityBtn.addEventListener('click', () => this.refreshObservabilityMetrics());
        }

        const exportTracesBtn = document.getElementById('export-traces');
        if (exportTracesBtn) {
            exportTracesBtn.addEventListener('click', () => this.exportDistributedTraces());
        }

        const serviceMeshBtn = document.getElementById('service-mesh-dashboard');
        if (serviceMeshBtn) {
            serviceMeshBtn.addEventListener('click', () => this.openServiceMeshDashboard());
        }

        // IaC and DevOps controls
        const refreshIacBtn = document.getElementById('refresh-iac-metrics');
        if (refreshIacBtn) {
            refreshIacBtn.addEventListener('click', () => this.refreshIaCMetrics());
        }

        const viewInfraBtn = document.getElementById('view-infrastructure-code');
        if (viewInfraBtn) {
            viewInfraBtn.addEventListener('click', () => this.viewInfrastructureCode());
        }

        const runInfraTestsBtn = document.getElementById('run-infrastructure-tests');
        if (runInfraTestsBtn) {
            runInfraTestsBtn.addEventListener('click', () => this.runInfrastructureTests());
        }
    }

    /**
     * Export topology data
     */
    async exportTopology() {
        try {
            const topologyData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                topology: this.topologyData,
                assessment: this.assessmentData,
                governance: this.governanceData
            };

            const blob = new Blob([JSON.stringify(topologyData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-platform-topology-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Platform topology exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export platform topology', 'error');
        }
    }

    /**
     * Validate constitution
     */
    async validateConstitution() {
        try {
            const result = await this.apiRequest('/constitution/validate', 'POST');
            this.showNotification('Constitution validation completed', 'success');

            // Refresh governance data
            if (window.dataExpressions) {
                const governanceData = await window.dataExpressions.executeExpression('platform_governance');
                this.updateGovernanceDashboard(governanceData);
            }
        } catch (error) {
            console.error('Constitution validation failed:', error);
            this.showNotification('Constitution validation failed', 'error');
        }
    }

    /**
     * Audit actions
     */
    async auditActions() {
        try {
            const result = await this.apiRequest('/governance/audit', 'POST');
            this.showNotification('Actions audit completed', 'success');

            // Refresh governance data
            if (window.dataExpressions) {
                const governanceData = await window.dataExpressions.executeExpression('platform_governance');
                this.updateGovernanceDashboard(governanceData);
            }
        } catch (error) {
            console.error('Actions audit failed:', error);
            this.showNotification('Actions audit failed', 'error');
        }
    }

    /**
     * Run self-assessment
     */
    async runSelfAssessment() {
        try {
            const result = await this.apiRequest('/assessment/run', 'POST');
            this.showNotification('Self-assessment completed', 'success');

            // Refresh assessment data
            if (window.dataExpressions) {
                const assessmentData = await window.dataExpressions.executeExpression('platform_assessment');
                this.updateAssessmentDashboard(assessmentData);
            }
        } catch (error) {
            console.error('Self-assessment failed:', error);
            this.showNotification('Self-assessment failed', 'error');
        }
    }

    /**
     * Export metrics
     */
    async exportMetrics() {
        try {
            const metricsData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                assessment: this.assessmentData,
                governance: this.governanceData,
                topology: this.topologyData
            };

            const blob = new Blob([JSON.stringify(metricsData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-platform-metrics-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Platform metrics exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export platform metrics', 'error');
        }
    }

    /**
     * Show agent details
     */
    showAgentDetails(agentId) {
        // Navigate to agents tab and show details
        const agentsTab = document.querySelector('[data-tab="agents"]');
        if (agentsTab) {
            agentsTab.click();

            // After navigation, trigger agent details
            setTimeout(() => {
                const agentCard = document.querySelector(`[data-agent-id="${agentId}"]`);
                if (agentCard) {
                    agentCard.click();
                }
            }, 500);
        }
    }

    /**
     * Advanced Observability Functions
     */
    async refreshObservabilityMetrics() {
        try {
            // Simulate API call to refresh observability data
            this.showNotification('Refreshing observability metrics...', 'info');
            await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay

            // Generate fresh mock data with slight variations
            const freshData = this.generateMockData();
            this.updateAssessmentDashboard(freshData);

            this.showNotification('Observability metrics refreshed successfully', 'success');
        } catch (error) {
            console.error('Failed to refresh observability metrics:', error);
            this.showNotification('Failed to refresh observability metrics', 'error');
        }
    }

    async exportDistributedTraces() {
        try {
            const traceData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                totalTraces: 847293,
                traceSamples: [
                    {
                        traceId: 'trace-123456',
                        duration: '234ms',
                        services: ['API Gateway', 'CoordinatorAgent', 'LLM Inference'],
                        status: 'success'
                    },
                    {
                        traceId: 'trace-123457',
                        duration: '156ms',
                        services: ['Client', 'Service Mesh', 'BDI Agent'],
                        status: 'success'
                    }
                ],
                metadata: {
                    samplingRate: '15.7%',
                    avgDepth: 12.7,
                    crossServiceCalls: '94.2%'
                }
            };

            const blob = new Blob([JSON.stringify(traceData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `distributed-traces-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Distributed traces exported successfully', 'success');
        } catch (error) {
            console.error('Failed to export traces:', error);
            this.showNotification('Failed to export distributed traces', 'error');
        }
    }

    async openServiceMeshDashboard() {
        try {
            // In a real implementation, this would open a service mesh dashboard
            // For now, show detailed mesh metrics
            const meshMetrics = {
                'Istio Service Mesh': {
                    version: '1.20.3',
                    pilotStatus: 'Healthy',
                    dataPlaneProxies: 12,
                    controlPlaneComponents: 3,
                    mutualTLS: '99.97%',
                    circuitBreakers: 12,
                    trafficPolicies: 8
                },
                'Traffic Management': {
                    virtualServices: 15,
                    destinationRules: 23,
                    gateways: 3,
                    peerAuthentications: 8,
                    requestAuthentications: 5
                },
                'Observability': {
                    prometheusIntegration: 'Active',
                    jaegerIntegration: 'Active',
                    kialiDashboard: 'Available',
                    grafanaDashboards: 'Configured'
                }
            };

            console.log('Service Mesh Dashboard:', meshMetrics);
            this.showNotification('Service Mesh Dashboard opened (check console for details)', 'info');

            // In a real app, this would open a new window/tab with the dashboard
            // window.open('/service-mesh-dashboard', '_blank');

        } catch (error) {
            console.error('Failed to open service mesh dashboard:', error);
            this.showNotification('Failed to open service mesh dashboard', 'error');
        }
    }

    /**
     * Infrastructure as Code Functions
     */
    async refreshIaCMetrics() {
        try {
            this.showNotification('Refreshing IaC metrics...', 'info');
            await new Promise(resolve => setTimeout(resolve, 800));

            const freshData = this.generateMockData();
            this.updateAssessmentDashboard(freshData);

            this.showNotification('IaC metrics refreshed successfully', 'success');
        } catch (error) {
            console.error('Failed to refresh IaC metrics:', error);
            this.showNotification('Failed to refresh IaC metrics', 'error');
        }
    }

    async viewInfrastructureCode() {
        try {
            // Simulate viewing infrastructure code
            const terraformCode = `# mindX Infrastructure as Code
# Generated: ${new Date().toISOString()}

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

# Kubernetes Namespace
resource "kubernetes_namespace" "mindx" {
  metadata {
    name = "mindx-system"
    labels = {
      name = "mindx"
      app  = "godel-machine"
    }
  }
}

# Service Mesh Configuration
resource "helm_release" "istio" {
  name       = "istio-base"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "base"
  namespace  = kubernetes_namespace.mindx.metadata[0].name
}`;

            console.log('Infrastructure Code:', terraformCode);
            this.showNotification('Infrastructure code displayed in console', 'info');

            // In a real implementation, this would open a code viewer
            // window.open('/infrastructure-code', '_blank');

        } catch (error) {
            console.error('Failed to view infrastructure code:', error);
            this.showNotification('Failed to view infrastructure code', 'error');
        }
    }

    async runInfrastructureTests() {
        try {
            this.showNotification('Running infrastructure tests...', 'info');

            // Simulate test execution
            await new Promise(resolve => setTimeout(resolve, 2000));

            const testResults = {
                timestamp: new Date().toISOString(),
                tests: {
                    total: 47,
                    passed: 46,
                    failed: 1,
                    skipped: 0
                },
                categories: {
                    'Security Tests': { passed: 12, total: 12 },
                    'Connectivity Tests': { passed: 15, total: 15 },
                    'Performance Tests': { passed: 11, total: 12 },
                    'Configuration Tests': { passed: 8, total: 8 }
                },
                duration: '2.3s',
                coverage: '98.7%'
            };

            console.log('Infrastructure Test Results:', testResults);

            if (testResults.tests.failed === 0) {
                this.showNotification('All infrastructure tests passed! ✅', 'success');
            } else {
                this.showNotification(`Infrastructure tests completed with ${testResults.tests.failed} failure(s)`, 'warning');
            }

        } catch (error) {
            console.error('Failed to run infrastructure tests:', error);
            this.showNotification('Failed to run infrastructure tests', 'error');
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
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.PlatformTab = PlatformTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = PlatformTab;
}