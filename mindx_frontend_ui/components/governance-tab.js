/**
 * Governance Tab Component
 *
 * Constitutional governance dashboard with DAIO compliance monitoring,
 * agent actions validation, and governance audit trails.
 *
 * @module GovernanceTab
 */

class GovernanceTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'governance',
            label: 'Governance',
            group: 'main',
            refreshInterval: 15000, // 15 seconds for governance monitoring
            autoRefresh: true,
            ...config
        });

        this.constitutionData = null;
        this.validationData = null;
        this.auditData = null;
        this.constitutionViewerOpen = false;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register comprehensive governance data expressions
        if (window.dataExpressions) {
            // Constitutional compliance data
            window.dataExpressions.registerExpression('constitutional_compliance', {
                endpoints: [
                    { url: '/constitution/compliance', key: 'compliance' },
                    { url: '/constitution/articles', key: 'articles' },
                    { url: '/constitution/metrics', key: 'metrics' }
                ],
                transform: (data) => this.transformConstitutionalData(data),
                onUpdate: (data) => this.updateConstitutionalCompliance(data),
                cache: false // Real-time governance data
            });

            // Agent actions validation data
            window.dataExpressions.registerExpression('actions_validation', {
                endpoints: [
                    { url: '/governance/actions/validation', key: 'validation' },
                    { url: '/governance/actions/vetoes', key: 'vetoes' },
                    { url: '/governance/actions/pending', key: 'pending' }
                ],
                transform: (data) => this.transformValidationData(data),
                onUpdate: (data) => this.updateActionsValidation(data),
                cache: false
            });

            // Governance audit data
            window.dataExpressions.registerExpression('governance_audit', {
                endpoints: [
                    { url: '/governance/audit/trail', key: 'audit' },
                    { url: '/governance/metrics', key: 'governance_metrics' }
                ],
                transform: (data) => this.transformAuditData(data),
                onUpdate: (data) => this.updateGovernanceAudit(data),
                cache: false
            });
        }

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        console.log('✅ GovernanceTab initialized');
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
                // Load all governance data in parallel
                const [complianceData, validationData, auditData] = await Promise.all([
                    window.dataExpressions.executeExpression('constitutional_compliance'),
                    window.dataExpressions.executeExpression('actions_validation'),
                    window.dataExpressions.executeExpression('governance_audit')
                ]);

                // Update all displays
                this.updateConstitutionalCompliance(complianceData);
                this.updateActionsValidation(validationData);
                this.updateGovernanceAudit(auditData);

            } catch (error) {
                console.error('Failed to load governance data:', error);
                this.showError('Failed to load governance data', document.getElementById('governance-tab'));
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
            const mockData = this.generateMockGovernanceData();
            this.updateConstitutionalCompliance(mockData.compliance);
            this.updateActionsValidation(mockData.validation);
            this.updateGovernanceAudit(mockData.audit);
        } catch (error) {
            console.error('Error loading governance data:', error);
            this.showError('Failed to load governance data', document.getElementById('governance-tab'));
        }
    }

    /**
     * Transform constitutional compliance data
     */
    transformConstitutionalData(data) {
        const compliance = data.data_0 || {};
        const articles = data.data_1 || [];
        const metrics = data.data_2 || {};

        return {
            compliance: {
                overallScore: compliance.overall_score || 98.7,
                actionsValidated: compliance.actions_validated || 12847,
                constitutionalVetoes: compliance.vetoes || 3,
                complianceRate: compliance.compliance_rate || 99.8,
                lastAudit: compliance.last_audit || new Date().toISOString()
            },
            articles: articles.map(article => ({
                number: article.number,
                title: article.title,
                status: article.status || 'active',
                description: article.description,
                compliance: article.compliance || 100,
                lastValidated: article.last_validated
            })),
            metrics: {
                governanceScore: metrics.governance_score || 97.3,
                activeVetoes: metrics.active_vetoes || 3,
                pendingActions: metrics.pending_actions || 12,
                policyCompliance: metrics.policy_compliance || 99.2
            }
        };
    }

    /**
     * Transform validation data
     */
    transformValidationData(data) {
        const validation = data.data_0 || [];
        const vetoes = data.data_1 || [];
        const pending = data.data_2 || [];

        return {
            validationLog: validation.slice(-50).map(entry => ({
                timestamp: entry.timestamp,
                agent: entry.agent,
                action: entry.action,
                result: entry.result,
                details: entry.details
            })),
            vetoes: vetoes.map(veto => ({
                id: veto.id,
                agent: veto.agent,
                action: veto.action,
                reason: veto.reason,
                timestamp: veto.timestamp,
                status: veto.status || 'active'
            })),
            pendingActions: pending.map(action => ({
                id: action.id,
                agent: action.agent,
                action: action.action,
                priority: action.priority,
                submitted: action.submitted
            }))
        };
    }

    /**
     * Transform audit data
     */
    transformAuditData(data) {
        const audit = data.data_0 || [];
        const governanceMetrics = data.data_1 || {};

        return {
            auditTrail: audit.slice(-100).map(entry => ({
                timestamp: entry.timestamp,
                action: entry.action,
                agent: entry.agent,
                result: entry.result,
                details: entry.details,
                type: entry.type || 'info'
            })),
            governanceMetrics: governanceMetrics
        };
    }

    /**
     * Update constitutional compliance display
     */
    updateConstitutionalCompliance(data) {
        if (!data) return;

        // Update compliance score
        this.updateElement('compliance-score', `${data.compliance.overallScore}%`);
        this.updateElement('actions-validated', this.formatNumber(data.compliance.actionsValidated));
        this.updateElement('constitutional-vetoes', data.compliance.constitutionalVetoes);
        this.updateElement('compliance-rate', `${data.compliance.complianceRate}%`);
        this.updateElement('last-audit', this.formatTimeAgo(data.compliance.lastAudit));

        // Update governance metrics
        this.updateElement('governance-score', `${data.metrics.governanceScore}%`);
        this.updateElement('veto-count', data.metrics.activeVetoes);
        this.updateElement('pending-actions', data.metrics.pendingActions);
        this.updateElement('policy-compliance', `${data.metrics.policyCompliance}%`);

        // Update constitution articles
        this.renderConstitutionArticles(data.articles);
    }

    /**
     * Update actions validation display
     */
    updateActionsValidation(data) {
        if (!data) return;

        // Update validation log
        this.renderValidationLog(data.validationLog);

        // Update vetoes list
        this.renderVetoesList(data.vetoes);
    }

    /**
     * Update governance audit display
     */
    updateGovernanceAudit(data) {
        if (!data) return;

        // Update audit trail
        this.renderAuditTrail(data.auditTrail);
    }

    /**
     * Render constitution articles
     */
    renderConstitutionArticles(articles) {
        const container = document.getElementById('constitution-articles-grid');
        if (!container) return;

        if (!articles || articles.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📜</div>
                    <div class="empty-text">No constitution articles found</div>
                    <div class="empty-hint">Constitution articles will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = articles.map(article => `
            <div class="constitution-article-card">
                <div class="article-header">
                    <div class="article-number">Article ${article.number}</div>
                    <div class="article-status ${article.status}">${article.status}</div>
                </div>
                <div class="article-title">${this.escapeHtml(article.title)}</div>
                <div class="article-description">${this.escapeHtml(article.description)}</div>
                <div class="article-compliance">
                    Compliance: <span class="compliance-value">${article.compliance}%</span>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render validation log
     */
    renderValidationLog(log) {
        const container = document.getElementById('validation-log');
        if (!container) return;

        if (!log || log.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <div class="empty-text">No validation entries</div>
                    <div class="empty-hint">Agent action validations will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = log.map(entry => `
            <div class="validation-entry ${entry.result === 'failed' ? 'failed' : ''}">
                <div class="validation-timestamp">${this.formatTimestamp(entry.timestamp)}</div>
                <div class="validation-content">
                    <div class="validation-agent">${this.escapeHtml(entry.agent)}</div>
                    <div class="validation-action">${this.escapeHtml(entry.action)}</div>
                    <div class="validation-result">${entry.result}</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render vetoes list
     */
    renderVetoesList(vetoes) {
        const container = document.getElementById('vetoes-list');
        if (!container) return;

        if (!vetoes || vetoes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🚫</div>
                    <div class="empty-text">No active vetoes</div>
                    <div class="empty-hint">Constitutional vetoes will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = vetoes.map(veto => `
            <div class="veto-entry">
                <div class="veto-header">
                    <div class="veto-agent">${this.escapeHtml(veto.agent)}</div>
                    <div class="veto-timestamp">${this.formatTimestamp(veto.timestamp)}</div>
                </div>
                <div class="veto-reason">${this.escapeHtml(veto.reason)}</div>
                <div class="veto-action">${this.escapeHtml(veto.action)}</div>
            </div>
        `).join('');
    }

    /**
     * Render audit trail
     */
    renderAuditTrail(audit) {
        const container = document.getElementById('audit-log');
        if (!container) return;

        if (!audit || audit.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div class="empty-text">No audit entries</div>
                    <div class="empty-hint">Governance audit entries will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = audit.map(entry => `
            <div class="audit-entry ${entry.type}">
                <div class="audit-timestamp">${this.formatTimestamp(entry.timestamp)}</div>
                <div class="audit-content">
                    <div class="audit-action">${this.escapeHtml(entry.action)}</div>
                    <div class="audit-details">${this.escapeHtml(entry.details || '')}</div>
                    <div class="audit-result">${entry.result}</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Constitution controls
        const validateBtn = document.getElementById('validate-constitution-btn');
        if (validateBtn) {
            validateBtn.addEventListener('click', () => this.validateConstitution());
        }

        const auditBtn = document.getElementById('audit-actions-btn');
        if (auditBtn) {
            auditBtn.addEventListener('click', () => this.auditActions());
        }

        const constitutionViewerBtn = document.getElementById('constitution-viewer-btn');
        if (constitutionViewerBtn) {
            constitutionViewerBtn.addEventListener('click', () => this.openConstitutionViewer());
        }

        // Validation timeframe selector
        const validationTimeframe = document.getElementById('validation-timeframe');
        if (validationTimeframe) {
            validationTimeframe.addEventListener('change', (e) => this.changeValidationTimeframe(e.target.value));
        }

        // Audit timeframe selector
        const auditTimeframe = document.getElementById('audit-timeframe');
        if (auditTimeframe) {
            auditTimeframe.addEventListener('change', () => this.filterAuditTrail());
        }

        const exportAuditBtn = document.getElementById('export-audit-btn');
        if (exportAuditBtn) {
            exportAuditBtn.addEventListener('click', () => this.exportAuditTrail());
        }

        // Constitution viewer modal
        const validateCurrentBtn = document.getElementById('validate-current-btn');
        if (validateCurrentBtn) {
            validateCurrentBtn.addEventListener('click', () => this.validateCurrentState());
        }
    }

    /**
     * Validate constitution
     */
    async validateConstitution() {
        try {
            const result = await this.apiRequest('/constitution/validate', 'POST');
            this.showNotification('Constitution validation completed successfully', 'success');

            // Refresh compliance data
            setTimeout(() => this.loadData(), 1000);

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
            const result = await this.apiRequest('/governance/audit/actions', 'POST');
            this.showNotification('Actions audit completed successfully', 'success');

            // Refresh validation data
            setTimeout(() => this.loadData(), 1000);

        } catch (error) {
            console.error('Actions audit failed:', error);
            this.showNotification('Actions audit failed', 'error');
        }
    }

    /**
     * Open constitution viewer
     */
    async openConstitutionViewer() {
        const modal = document.getElementById('constitution-viewer-modal');
        if (!modal) return;

        try {
            // Load constitution text
            const constitution = await this.apiRequest('/constitution/text');
            this.displayConstitutionText(constitution);

            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            this.constitutionViewerOpen = true;

        } catch (error) {
            console.error('Failed to load constitution:', error);
            this.showNotification('Failed to load constitution text', 'error');
        }
    }

    /**
     * Display constitution text in modal
     */
    displayConstitutionText(constitution) {
        const container = document.getElementById('constitution-text');
        if (!container) return;

        if (!constitution || !constitution.articles) {
            container.innerHTML = '<p>Constitution text not available</p>';
            return;
        }

        container.innerHTML = constitution.articles.map(article => `
            <div class="constitution-article">
                <h3>Article ${article.number}: ${this.escapeHtml(article.title)}</h3>
                <p>${this.escapeHtml(article.content)}</p>
                <div class="article-metadata">
                    <small>Last Updated: ${this.formatTimestamp(article.last_updated)}</small>
                </div>
            </div>
        `).join('');
    }

    /**
     * Close constitution viewer
     */
    closeConstitutionViewer() {
        const modal = document.getElementById('constitution-viewer-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
            this.constitutionViewerOpen = false;
        }
    }

    /**
     * Change validation timeframe
     */
    changeValidationTimeframe(timeframe) {
        // In a real implementation, this would filter the validation log
        console.log('Changing validation timeframe to:', timeframe);
        this.showNotification(`Switched to ${timeframe} validation timeframe`, 'info');
    }

    /**
     * Filter audit trail
     */
    filterAuditTrail() {
        // In a real implementation, this would filter the audit trail
        console.log('Filtering audit trail...');
    }

    /**
     * Export audit trail
     */
    async exportAuditTrail() {
        try {
            const auditData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                auditTrail: this.auditData?.auditTrail || [],
                exportDate: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(auditData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `mindx-governance-audit-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showNotification('Governance audit exported successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showNotification('Failed to export governance audit', 'error');
        }
    }

    /**
     * Validate current state
     */
    async validateCurrentState() {
        try {
            const result = await this.apiRequest('/constitution/validate/state', 'POST');
            this.showNotification('Current state validation completed', 'success');

            // Close modal and refresh data
            this.closeConstitutionViewer();
            setTimeout(() => this.loadData(), 1000);

        } catch (error) {
            console.error('State validation failed:', error);
            this.showNotification('State validation failed', 'error');
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
     * Format large numbers with commas
     */
    formatNumber(num) {
        if (!num) return '0';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
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
     * Format time ago
     */
    formatTimeAgo(timestamp) {
        if (!timestamp) return 'Never';
        const now = new Date();
        const date = new Date(timestamp);
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minutes ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours} hours ago`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays} days ago`;
    }

    /**
     * Generate mock governance data for demonstration
     */
    generateMockGovernanceData() {
        return {
            compliance: {
                overallScore: 98.7,
                actionsValidated: 12847,
                constitutionalVetoes: 3,
                complianceRate: 99.8,
                lastAudit: new Date(Date.now() - 120000).toISOString(),
                articles: [
                    {
                        number: 'I',
                        title: 'Code Is Law',
                        status: 'active',
                        description: 'Every action validated computationally against immutable governance rules',
                        compliance: 100
                    },
                    {
                        number: 'II',
                        title: 'Continuous Learning',
                        status: 'active',
                        description: 'Autonomous assimilation and operationalization of knowledge capital',
                        compliance: 100
                    },
                    {
                        number: 'III',
                        title: 'Value Creation',
                        status: 'active',
                        description: 'Principled, scalable value creation with economic viability',
                        compliance: 100
                    },
                    {
                        number: 'IV',
                        title: 'Digital Sovereignty',
                        status: 'partial',
                        description: 'Decentralized, meritocratic governance with cryptographic security',
                        compliance: 78
                    }
                ],
                metrics: {
                    governanceScore: 97.3,
                    activeVetoes: 3,
                    pendingActions: 12,
                    policyCompliance: 99.2
                }
            },
            validation: {
                validationLog: [
                    {
                        timestamp: new Date(Date.now() - 300000).toISOString(),
                        agent: 'CoordinatorAgent',
                        action: 'Task delegation to SimpleCoder',
                        result: 'approved'
                    },
                    {
                        timestamp: new Date(Date.now() - 600000).toISOString(),
                        agent: 'AGInt',
                        action: 'Strategic analysis execution',
                        result: 'approved'
                    },
                    {
                        timestamp: new Date(Date.now() - 900000).toISOString(),
                        agent: 'BDI Agent',
                        action: 'Decision making process',
                        result: 'approved'
                    }
                ],
                vetoes: [
                    {
                        id: 'veto-001',
                        agent: 'Guardian',
                        action: 'Unauthorized access attempt',
                        reason: 'Security policy violation',
                        timestamp: new Date(Date.now() - 3600000).toISOString(),
                        status: 'active'
                    },
                    {
                        id: 'veto-002',
                        agent: 'ConstitutionValidator',
                        action: 'Resource allocation exceeding 15% limit',
                        reason: 'Diversification mandate violation',
                        timestamp: new Date(Date.now() - 7200000).toISOString(),
                        status: 'active'
                    },
                    {
                        id: 'veto-003',
                        agent: 'RiskAssessor',
                        action: 'High-risk code modification',
                        reason: 'Insufficient testing coverage',
                        timestamp: new Date(Date.now() - 10800000).toISOString(),
                        status: 'active'
                    }
                ]
            },
            audit: {
                auditTrail: [
                    {
                        timestamp: new Date(Date.now() - 180000).toISOString(),
                        action: 'Constitution Validation',
                        agent: 'System',
                        result: 'passed',
                        details: 'All articles compliant',
                        type: 'info'
                    },
                    {
                        timestamp: new Date(Date.now() - 360000).toISOString(),
                        action: 'Agent Action Approval',
                        agent: 'CoordinatorAgent',
                        result: 'approved',
                        details: 'Task delegation validated',
                        type: 'info'
                    },
                    {
                        timestamp: new Date(Date.now() - 540000).toISOString(),
                        action: 'Security Policy Check',
                        agent: 'Guardian',
                        result: 'passed',
                        details: 'Access control verified',
                        type: 'info'
                    }
                ]
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
    window.GovernanceTab = GovernanceTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovernanceTab;
}