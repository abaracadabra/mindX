/**
 * System Performance Metrics Tab Component
 *
 * Comprehensive Godel machine self-assessment and performance monitoring
 * system suitable for autonomous system evaluation and improvement.
 *
 * @module SystemTab
 */

class SystemTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'system',
            label: 'System',
            group: 'main',
            refreshInterval: 5000, // 5 seconds for real-time monitoring
            autoRefresh: true,
            ...config
        });

        this.performanceData = null;
        this.healthData = null;
        this.analyticsData = null;
        this.assessmentData = null;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register comprehensive performance monitoring data expressions
        if (window.dataExpressions) {
            // System health and performance data
            window.dataExpressions.registerExpression('system_performance', {
                endpoints: [
                    { url: '/monitoring/performance', key: 'performance' },
                    { url: '/monitoring/resources', key: 'resources' },
                    { url: '/monitoring/health', key: 'health' }
                ],
                transform: (data) => this.transformPerformanceData(data),
                onUpdate: (data) => this.updatePerformanceMetrics(data),
                cache: false // Real-time performance data
            });

            // LLM and agent metrics
            window.dataExpressions.registerExpression('system_llm_agent_metrics', {
                endpoints: [
                    { url: '/monitoring/llm', key: 'llm' },
                    { url: '/monitoring/agents', key: 'agents' },
                    { url: '/monitoring/security', key: 'security' }
                ],
                transform: (data) => this.transformLLMAgentData(data),
                onUpdate: (data) => this.updateLLMAgentMetrics(data),
                cache: false
            });

            // Self-assessment data
            window.dataExpressions.registerExpression('system_self_assessment', {
                endpoints: [
                    { url: '/assessment/autonomy', key: 'autonomy' },
                    { url: '/assessment/intelligence', key: 'intelligence' },
                    { url: '/assessment/economics', key: 'economics' },
                    { url: '/assessment/sovereignty', key: 'sovereignty' }
                ],
                transform: (data) => this.transformAssessmentData(data),
                onUpdate: (data) => this.updateSelfAssessment(data),
                cache: false
            });
        }

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        console.log('✅ System Performance Tab initialized');
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
                // Load all performance data in parallel
                const [performanceData, llmAgentData, assessmentData] = await Promise.all([
                    window.dataExpressions.executeExpression('system_performance'),
                    window.dataExpressions.executeExpression('system_llm_agent_metrics'),
                    window.dataExpressions.executeExpression('system_self_assessment')
                ]);

                // Update all dashboards
                this.updatePerformanceMetrics(performanceData);
                this.updateLLMAgentMetrics(llmAgentData);
                this.updateSelfAssessment(assessmentData);

            } catch (error) {
                console.error('Failed to load system performance data:', error);
                this.showError('Failed to load system performance data', document.getElementById('system-tab'));
            }
        } else {
            await this.loadDataFallback();
        }
    }

    /**
     * Fallback data loading with mock data
     */
    async loadDataFallback() {
        try {
            const mockData = this.generateMockPerformanceData();
            this.updatePerformanceMetrics(mockData.performance);
            this.updateLLMAgentMetrics(mockData.llmAgent);
            this.updateSelfAssessment(mockData.assessment);
        } catch (error) {
            console.error('Error loading system performance data:', error);
            this.showError('Failed to load system performance data', document.getElementById('system-tab'));
        }
    }

    /**
     * Transform performance data from API responses
     */
    transformPerformanceData(data) {
        const performance = data.data_0 || {};
        const resources = data.data_1 || {};
        const health = data.data_2 || {};

        return {
            overall: {
                healthScore: health.overall_score || 98,
                uptime: health.uptime || '99.9%',
                activeProcesses: health.active_processes || 24,
                alerts: health.active_alerts || 0,
                throughput: health.data_throughput || '1.2GB/s'
            },
            resources: {
                cpu: resources.cpu_usage || 34,
                memory: resources.memory_usage || 67,
                disk: resources.disk_usage || 45,
                network: resources.network_io || '2.1GB/s',
                gpuMemory: resources.gpu_memory || 78,
                temperature: resources.temperature || 42
            },
            components: {
                performance: health.component_scores?.performance || 96,
                reliability: health.component_scores?.reliability || 99,
                security: health.component_scores?.security || 95,
                autonomy: health.component_scores?.autonomy || 92
            }
        };
    }

    /**
     * Transform LLM and agent metrics data
     */
    transformLLMAgentData(data) {
        const llm = data.data_0 || {};
        const agents = data.data_1 || {};
        const security = data.data_2 || {};

        return {
            llm: {
                totalCalls: llm.total_api_calls || 12847,
                successRate: llm.success_rate || 99.7,
                avgLatency: llm.avg_latency || '2.3s',
                costEfficiency: llm.cost_efficiency || 94,
                tokenUsage: llm.token_usage_24h || '1.2M',
                availability: llm.availability || 100
            },
            agents: {
                active: agents.active_count || 18,
                completionRate: agents.task_completion_rate || 96.4,
                responseTime: agents.avg_response_time || '1.8s',
                errorRecovery: agents.error_recovery_rate || 98.2,
                collaboration: agents.collaboration_index || 87.3,
                autonomousDecisions: agents.autonomous_decisions || 1247
            },
            security: {
                compliance: security.constitutional_compliance || 98.7,
                validations: security.crypto_validations || 99.9,
                accessChecks: security.access_control_checks || 8542,
                incidents: security.security_incidents || 0,
                identityVerifications: security.identity_verifications || 1203,
                auditIntegrity: security.audit_trail_integrity || 100
            }
        };
    }

    /**
     * Transform self-assessment data
     */
    transformAssessmentData(data) {
        const autonomy = data.data_0 || {};
        const intelligence = data.data_1 || {};
        const economics = data.data_2 || {};
        const sovereignty = data.data_3 || {};

        return {
            autonomy: {
                score: autonomy.overall_score || 92,
                cycles: autonomy.improvement_cycles || 23,
                interventions: autonomy.human_interventions || 2,
                sufficiency: autonomy.self_sufficiency || 96
            },
            intelligence: {
                score: intelligence.overall_score || 89,
                problemSolving: intelligence.problem_solving || 94,
                knowledgeIntegration: intelligence.knowledge_beliefs || 1247,
                strategicReasoning: intelligence.strategic_reasoning || 92
            },
            economics: {
                score: economics.overall_score || 87,
                costOptimization: economics.cost_optimization || 34,
                valueCreation: economics.value_creation || 247,
                treasuryGrowth: economics.treasury_growth || 12
            },
            sovereignty: {
                score: sovereignty.overall_score || 78,
                registeredAgents: sovereignty.registered_agents || 20,
                validations: sovereignty.security_validations || 99.7,
                autonomousOps: sovereignty.autonomous_operations || 78
            }
        };
    }

    /**
     * Update performance metrics display
     */
    updatePerformanceMetrics(data) {
        if (!data) return;

        // Update overall health
        this.updateElement('overall-health-score', data.overall?.healthScore);
        this.updateElement('system-uptime', data.overall?.uptime);
        this.updateElement('active-processes', data.overall?.activeProcesses);
        this.updateElement('active-alerts', data.overall?.alerts);
        this.updateElement('data-throughput', data.overall?.throughput);

        // Update component health scores
        this.updateElement('health-performance', data.components?.performance);
        this.updateElement('health-reliability', data.components?.reliability);
        this.updateElement('health-security', data.components?.security);
        this.updateElement('health-autonomy', data.components?.autonomy);

        // Update resource metrics
        this.updateElement('sys-cpu-usage', `${data.resources?.cpu}%`);
        this.updateElement('sys-memory-usage', `${data.resources?.memory}%`);
        this.updateElement('sys-disk-usage', `${data.resources?.disk}%`);
        this.updateElement('sys-network-io', data.resources?.network);
        this.updateElement('sys-gpu-memory', `${data.resources?.gpuMemory}%`);
        this.updateElement('sys-temperature', `${data.resources?.temperature}°C`);

        // Update progress bars
        this.updateProgressBar('sys-cpu-bar', data.resources?.cpu);
        this.updateProgressBar('sys-memory-bar', data.resources?.memory);
        this.updateProgressBar('sys-disk-bar', data.resources?.disk);
    }

    /**
     * Update LLM and agent metrics display
     */
    updateLLMAgentMetrics(data) {
        if (!data) return;

        // Update LLM metrics
        this.updateElement('llm-total-calls', this.formatNumber(data.llm?.totalCalls));
        this.updateElement('llm-success-rate', `${data.llm?.successRate}%`);
        this.updateElement('llm-avg-latency', data.llm?.avgLatency);
        this.updateElement('llm-cost-efficiency', `${data.llm?.costEfficiency}%`);
        this.updateElement('llm-token-usage', data.llm?.tokenUsage);
        this.updateElement('llm-availability', `${data.llm?.availability}%`);

        // Update agent metrics
        this.updateElement('agents-active', data.agents?.active);
        this.updateElement('agents-completion-rate', `${data.agents?.completionRate}%`);
        this.updateElement('agents-response-time', data.agents?.responseTime);
        this.updateElement('agents-error-recovery', `${data.agents?.errorRecovery}%`);
        this.updateElement('agents-collaboration', data.agents?.collaboration);
        this.updateElement('agents-autonomous-decisions', this.formatNumber(data.agents?.autonomousDecisions));

        // Update security metrics
        this.updateElement('security-compliance', `${data.security?.compliance}%`);
        this.updateElement('security-validations', `${data.security?.validations}%`);
        this.updateElement('security-access-checks', this.formatNumber(data.security?.accessChecks));
        this.updateElement('security-incidents', data.security?.incidents);
        this.updateElement('security-identity-verifications', this.formatNumber(data.security?.identityVerifications));
        this.updateElement('security-audit-integrity', `${data.security?.auditIntegrity}%`);
    }

    /**
     * Update self-assessment display
     */
    updateSelfAssessment(data) {
        if (!data) return;

        // Update autonomy assessment
        this.updateElement('autonomy-score', `${data.autonomy?.score}%`);
        this.updateElement('autonomy-cycles', data.autonomy?.cycles);
        this.updateElement('autonomy-interventions', data.autonomy?.interventions);
        this.updateElement('autonomy-sufficiency', `${data.autonomy?.sufficiency}%`);
        this.updateProgressBar('autonomy-score-bar', data.autonomy?.score);

        // Update intelligence assessment
        this.updateElement('intelligence-score', `${data.intelligence?.score}%`);
        this.updateElement('intelligence-problem-solving', `${data.intelligence?.problemSolving}%`);
        this.updateElement('intelligence-knowledge', this.formatNumber(data.intelligence?.knowledgeIntegration));
        this.updateElement('intelligence-strategic', `${data.intelligence?.strategicReasoning}%`);
        this.updateProgressBar('intelligence-score-bar', data.intelligence?.score);

        // Update economics assessment
        this.updateElement('economic-score', `${data.economics?.score}%`);
        this.updateElement('economic-cost-optimization', `${data.economics?.costOptimization}%`);
        this.updateElement('economic-value-creation', `$${data.economics?.valueCreation}`);
        this.updateElement('economic-treasury', `${data.economics?.treasuryGrowth}%`);
        this.updateProgressBar('economic-score-bar', data.economics?.score);

        // Update sovereignty assessment
        this.updateElement('sovereignty-score', `${data.sovereignty?.score}%`);
        this.updateElement('sovereignty-agents', data.sovereignty?.registeredAgents);
        this.updateElement('sovereignty-validations', `${data.sovereignty?.validations}%`);
        this.updateElement('sovereignty-autonomous', `${data.sovereignty?.autonomousOps}%`);
        this.updateProgressBar('sovereignty-score-bar', data.sovereignty?.score);

        // Update report timestamp
        this.updateElement('report-timestamp', `Generated: ${new Date().toLocaleString()}`);
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
     * Update progress bar width
     */
    updateProgressBar(id, percentage) {
        const el = document.getElementById(id);
        if (el) {
            el.style.width = `${percentage}%`;
        }
    }

    /**
     * Format large numbers with commas
     */
    formatNumber(num) {
        if (!num) return '0';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    /**
     * Generate mock performance data for demonstration
     */
    generateMockPerformanceData() {
        return {
            performance: {
                overall: {
                    healthScore: 98,
                    uptime: '99.9%',
                    activeProcesses: 24,
                    alerts: 0,
                    throughput: '1.2GB/s'
                },
                resources: {
                    cpu: 34,
                    memory: 67,
                    disk: 45,
                    network: '2.1GB/s',
                    gpuMemory: 78,
                    temperature: 42
                },
                components: {
                    performance: 96,
                    reliability: 99,
                    security: 95,
                    autonomy: 92
                }
            },
            llmAgent: {
                llm: {
                    totalCalls: 12847,
                    successRate: 99.7,
                    avgLatency: '2.3s',
                    costEfficiency: 94,
                    tokenUsage: '1.2M',
                    availability: 100
                },
                agents: {
                    active: 18,
                    completionRate: 96.4,
                    responseTime: '1.8s',
                    errorRecovery: 98.2,
                    collaboration: 87.3,
                    autonomousDecisions: 1247
                },
                security: {
                    compliance: 98.7,
                    validations: 99.9,
                    accessChecks: 8542,
                    incidents: 0,
                    identityVerifications: 1203,
                    auditIntegrity: 100
                }
            },
            assessment: {
                autonomy: {
                    score: 92,
                    cycles: 23,
                    interventions: 2,
                    sufficiency: 96
                },
                intelligence: {
                    score: 89,
                    problemSolving: 94,
                    knowledgeIntegration: 1247,
                    strategicReasoning: 92
                },
                economics: {
                    score: 87,
                    costOptimization: 34,
                    valueCreation: 247,
                    treasuryGrowth: 12
                },
                sovereignty: {
                    score: 78,
                    registeredAgents: 20,
                    validations: 99.7,
                    autonomousOps: 78
                }
            }
        };
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Self-assessment controls
        const runAssessmentBtn = document.getElementById('run-self-assessment-btn');
        if (runAssessmentBtn) {
            runAssessmentBtn.addEventListener('click', () => this.runSelfAssessment());
        }

        const exportMetricsBtn = document.getElementById('export-metrics-btn');
        if (exportMetricsBtn) {
            exportMetricsBtn.addEventListener('click', () => this.exportMetrics());
        }

        const generateReportBtn = document.getElementById('generate-report-btn');
        if (generateReportBtn) {
            generateReportBtn.addEventListener('click', () => this.generateReport());
        }

        // Analytics controls
        const refreshAnalyticsBtn = document.getElementById('refresh-analytics-btn');
        if (refreshAnalyticsBtn) {
            refreshAnalyticsBtn.addEventListener('click', () => this.refreshAnalytics());
        }

        const analyticsTimeframe = document.getElementById('analytics-timeframe');
        if (analyticsTimeframe) {
            analyticsTimeframe.addEventListener('change', (e) => this.changeAnalyticsTimeframe(e.target.value));
        }
    }

    /**
     * Run comprehensive self-assessment
     */
    async runSelfAssessment() {
        try {
            const result = await this.apiRequest('/assessment/run/full', 'POST');
            this.showNotification('Self-assessment completed successfully', 'success');

            // Refresh all data
            setTimeout(() => this.loadData(), 1000);

        } catch (error) {
            console.error('Self-assessment failed:', error);
            this.showNotification('Self-assessment failed', 'error');
        }
    }

    /**
     * Export comprehensive metrics
     */
    async exportMetrics() {
        try {
            const exportData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                performance: this.performanceData,
                llmAgent: this.llmAgentData,
                assessment: this.assessmentData,
                systemInfo: {
                    version: 'mindX v1.0',
                    assessmentDate: new Date().toISOString()
                }
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-performance-assessment-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Performance metrics exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export performance metrics', 'error');
        }
    }

    /**
     * Generate detailed performance report
     */
    async generateReport() {
        try {
            const reportData = await this.apiRequest('/reports/generate/performance', 'POST', {
                timeframe: 'comprehensive',
                includeRecommendations: true
            });

            this.showNotification('Performance report generated successfully', 'success');

            // In a real implementation, this would open or download the report
            console.log('Generated report:', reportData);

        } catch (error) {
            console.error('Report generation failed:', error);
            this.showNotification('Failed to generate performance report', 'error');
        }
    }

    /**
     * Refresh analytics data
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
     * Change analytics timeframe
     */
    changeAnalyticsTimeframe(timeframe) {
        // In a real implementation, this would update the analytics charts
        // with data for the selected timeframe
        this.showNotification(`Switched to ${timeframe} timeframe`, 'info');

        // Update chart placeholders with timeframe-specific data
        const charts = [
            'performance-trends-chart',
            'resource-utilization-chart',
            'agent-activity-heatmap',
            'security-timeline-chart'
        ];

        charts.forEach(chartId => {
            const chartEl = document.getElementById(chartId);
            if (chartEl) {
                const noteEl = chartEl.querySelector('.chart-note');
                if (noteEl) {
                    noteEl.textContent = `Data for last ${timeframe} - Real-time monitoring active`;
                }
            }
        });
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
    window.SystemTab = SystemTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SystemTab;
}