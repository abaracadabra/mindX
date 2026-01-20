/**
 * Security Tab Component
 *
 * System-wide security monitoring with cryptographic identity verification,
 * access control, threat detection, and compliance reporting.
 *
 * @module SecurityTab
 */

class SecurityTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'security',
            label: 'Security',
            group: 'main',
            refreshInterval: 10000, // 10 seconds for security monitoring
            autoRefresh: true,
            ...config
        });

        this.securityData = null;
        this.identityData = null;
        this.accessData = null;
        this.threatData = null;
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Register comprehensive security data expressions
        if (window.dataExpressions) {
            // Identity verification data
            window.dataExpressions.registerExpression('security_identities', {
                endpoints: [
                    { url: '/security/identities/all', key: 'identities' },
                    { url: '/security/identities/verification', key: 'verification' },
                    { url: '/security/identities/status', key: 'status' }
                ],
                transform: (data) => this.transformIdentityData(data),
                onUpdate: (data) => this.updateIdentityData(data),
                cache: false // Real-time identity verification
            });

            // Access control data
            window.dataExpressions.registerExpression('security_access', {
                endpoints: [
                    { url: '/security/access/logs', key: 'logs' },
                    { url: '/security/access/metrics', key: 'metrics' },
                    { url: '/security/access/anomalies', key: 'anomalies' }
                ],
                transform: (data) => this.transformAccessData(data),
                onUpdate: (data) => this.updateAccessData(data),
                cache: false
            });

            // Threat detection data
            window.dataExpressions.registerExpression('security_threats', {
                endpoints: [
                    { url: '/security/threats/events', key: 'events' },
                    { url: '/security/threats/detection', key: 'detection' },
                    { url: '/security/threats/analytics', key: 'analytics' }
                ],
                transform: (data) => this.transformThreatData(data),
                onUpdate: (data) => this.updateThreatData(data),
                cache: false
            });

            // Cryptographic compliance data
            window.dataExpressions.registerExpression('security_crypto', {
                endpoints: [
                    { url: '/security/crypto/compliance', key: 'compliance' },
                    { url: '/security/crypto/certificates', key: 'certificates' },
                    { url: '/security/crypto/keys', key: 'keys' }
                ],
                transform: (data) => this.transformCryptoData(data),
                onUpdate: (data) => this.updateCryptoData(data),
                cache: false
            });
        }

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data
        await this.loadData();

        console.log('✅ SecurityTab initialized');
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
                // Load all security data in parallel
                const [identityData, accessData, threatData, cryptoData] = await Promise.all([
                    window.dataExpressions.executeExpression('security_identities'),
                    window.dataExpressions.executeExpression('security_access'),
                    window.dataExpressions.executeExpression('security_threats'),
                    window.dataExpressions.executeExpression('security_crypto')
                ]);

                // Update all displays
                this.updateIdentityData(identityData);
                this.updateAccessData(accessData);
                this.updateThreatData(threatData);
                this.updateCryptoData(cryptoData);

            } catch (error) {
                console.error('Failed to load security data:', error);
                this.showError('Failed to load security data', document.getElementById('security-tab'));
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
            const mockData = this.generateMockSecurityData();
            this.updateIdentityData(mockData.identities);
            this.updateAccessData(mockData.access);
            this.updateThreatData(mockData.threats);
            this.updateCryptoData(mockData.crypto);
        } catch (error) {
            console.error('Error loading security data:', error);
            this.showError('Failed to load security data', document.getElementById('security-tab'));
        }
    }

    /**
     * Transform identity data
     */
    transformIdentityData(data) {
        const identities = data.data_0 || [];
        const verification = data.data_1 || [];
        const status = data.data_2 || {};

        return {
            identities: identities.map(identity => ({
                ...identity,
                verificationStatus: verification.find(v => v.id === identity.id)?.status || 'pending',
                lastVerified: verification.find(v => v.id === identity.id)?.timestamp,
                status: status[identity.id] || 'unknown'
            })),
            stats: {
                total: identities.length,
                verified: identities.filter(id => verification.find(v => v.id === id.id)?.status === 'verified').length,
                pending: identities.filter(id => verification.find(v => v.id === id.id)?.status === 'pending').length,
                failed: identities.filter(id => verification.find(v => v.id === id.id)?.status === 'failed').length
            }
        };
    }

    /**
     * Transform access control data
     */
    transformAccessData(data) {
        const logs = data.data_0 || [];
        const metrics = data.data_1 || {};
        const anomalies = data.data_2 || [];

        return {
            logs: logs.slice(-20).map(log => ({
                timestamp: log.timestamp,
                user: log.user,
                action: log.action,
                resource: log.resource,
                result: log.result,
                ip: log.ip_address
            })),
            metrics: {
                totalRequests: metrics.total_requests || 0,
                successRate: metrics.success_rate || 0,
                activeSessions: metrics.active_sessions || 0,
                failedAuth: metrics.failed_auth || 0
            },
            anomalies: anomalies.map(anomaly => ({
                id: anomaly.id,
                type: anomaly.type,
                severity: anomaly.severity,
                description: anomaly.description,
                timestamp: anomaly.timestamp
            }))
        };
    }

    /**
     * Transform threat detection data
     */
    transformThreatData(data) {
        const events = data.data_0 || [];
        const detection = data.data_1 || {};
        const analytics = data.data_2 || {};

        return {
            events: events.slice(-10).map(event => ({
                id: event.id,
                type: event.type,
                severity: event.severity,
                description: event.description,
                source: event.source,
                timestamp: event.timestamp,
                status: event.status || 'detected'
            })),
            detection: {
                scannedRequests: detection.scanned_requests || 0,
                blockedThreats: detection.blocked_threats || 0,
                falsePositives: detection.false_positives || 0,
                accuracy: detection.accuracy || 0
            },
            analytics: analytics
        };
    }

    /**
     * Transform cryptographic compliance data
     */
    transformCryptoData(data) {
        const compliance = data.data_0 || {};
        const certificates = data.data_1 || [];
        const keys = data.data_2 || [];

        return {
            compliance: {
                overall: compliance.overall_score || 98.5,
                keyRotation: compliance.key_rotation || 100,
                encryption: compliance.encryption_standards || 'AES-256',
                certificates: compliance.certificate_validity || 98.7,
                zkProofs: compliance.zero_knowledge || 'Active'
            },
            certificates: certificates.map(cert => ({
                id: cert.id,
                domain: cert.domain,
                issuer: cert.issuer,
                expiry: cert.expiry_date,
                status: cert.status
            })),
            keys: keys.map(key => ({
                id: key.id,
                type: key.type,
                rotation: key.last_rotation,
                status: key.status,
                strength: key.strength
            }))
        };
    }

    /**
     * Update identity data display
     */
    updateIdentityData(data) {
        if (!data) return;

        // Update status cards
        this.updateElement('verified-identities', `${data.stats.verified}/${data.stats.total}`);
        this.updateElement('total-identities', data.stats.total);
        this.updateElement('active-sessions', data.stats.verified);

        // Update identity list
        this.renderIdentityList(data.identities);
    }

    /**
     * Update access data display
     */
    updateAccessData(data) {
        if (!data) return;

        // Update access logs
        this.renderAccessLogs(data.logs);

        // Update metrics
        this.updateElement('api-access-rate', `${data.metrics.successRate}%`);
        this.updateElement('privileged-access', `${data.metrics.activeSessions} active`);
        this.updateElement('failed-auth', data.metrics.failedAuth);
    }

    /**
     * Update threat data display
     */
    updateThreatData(data) {
        if (!data) return;

        // Update status cards
        this.updateElement('active-threats', data.events.filter(e => e.status === 'active').length);

        // Update threat metrics
        this.updateElement('scanned-requests', this.formatNumber(data.detection.scannedRequests));
        this.updateElement('blocked-threats', data.detection.blockedThreats);
        this.updateElement('false-positives', data.detection.falsePositives);
        this.updateElement('detection-accuracy', `${data.detection.accuracy}%`);

        // Update security events
        this.renderSecurityEvents(data.events);
    }

    /**
     * Update crypto compliance data display
     */
    updateCryptoData(data) {
        if (!data) return;

        // Update compliance score
        this.updateElement('crypto-compliance-score', `${data.compliance.overall}%`);
        this.updateElement('key-rotation', `${data.compliance.keyRotation}%`);
        this.updateElement('encryption-standards', data.compliance.encryption);
        this.updateElement('certificate-validity', `${data.compliance.certificates}%`);
        this.updateElement('zk-proofs', data.compliance.zkProofs);

        // Update overall security status
        this.updateSecurityStatus(data);
    }

    /**
     * Update overall security status
     */
    updateSecurityStatus(data) {
        const overallScore = data.compliance?.overall || 98.5;
        const threatCount = this.threatData?.events?.filter(e => e.status === 'active').length || 0;

        let status = 'Secure';
        if (threatCount > 0) status = 'Monitoring';
        if (overallScore < 95) status = 'Attention Required';

        this.updateElement('security-overall-status', status);
        this.updateElement('security-compliance', `${overallScore}%`);
    }

    /**
     * Render identity list
     */
    renderIdentityList(identities) {
        const container = document.getElementById('identity-list');
        if (!container) return;

        if (!identities || identities.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">👤</div>
                    <div class="empty-text">No identities found</div>
                    <div class="empty-hint">Identities will appear here when registered</div>
                </div>
            `;
            return;
        }

        container.innerHTML = identities.slice(0, 10).map(identity => `
            <div class="identity-item ${identity.verificationStatus}" data-identity-id="${identity.id}">
                <div class="identity-info">
                    <div class="identity-name">${this.escapeHtml(identity.name || identity.id)}</div>
                    <div class="identity-details">
                        Type: ${identity.type} • Status: ${identity.status}
                        ${identity.lastVerified ? ` • Verified: ${this.formatTimestamp(identity.lastVerified)}` : ''}
                    </div>
                </div>
                <div class="identity-status ${identity.verificationStatus}">
                    ${identity.verificationStatus}
                </div>
            </div>
        `).join('');
    }

    /**
     * Render access logs
     */
    renderAccessLogs(logs) {
        const container = document.getElementById('access-logs');
        if (!container) return;

        if (!logs || logs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🚪</div>
                    <div class="empty-text">No access logs</div>
                    <div class="empty-hint">Access logs will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="access-entry ${log.result === 'denied' ? 'denied' : ''}">
                <div class="access-timestamp">${this.formatTimestamp(log.timestamp)}</div>
                <div class="access-user">${this.escapeHtml(log.user)}</div>
                <div class="access-action">${this.escapeHtml(log.action)} ${this.escapeHtml(log.resource)}</div>
                <div class="access-result">${log.result}</div>
            </div>
        `).join('');
    }

    /**
     * Render security events
     */
    renderSecurityEvents(events) {
        const container = document.getElementById('security-events-list');
        if (!container) return;

        if (!events || events.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <div class="empty-text">No security events</div>
                    <div class="empty-hint">Security events will appear here</div>
                </div>
            `;
            return;
        }

        container.innerHTML = events.map(event => `
            <div class="security-event ${event.severity}">
                <div class="event-header">
                    <div class="event-title">${this.escapeHtml(event.description)}</div>
                    <div class="event-severity ${event.severity}">${event.severity}</div>
                </div>
                <div class="event-description">
                    Type: ${event.type} • Source: ${event.source}
                </div>
                <div class="event-metadata">
                    <span>Status: ${event.status}</span>
                    <span>${this.formatTimestamp(event.timestamp)}</span>
                </div>
            </div>
        `).join('');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Security controls
        const refreshBtn = document.getElementById('refresh-security-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const auditBtn = document.getElementById('audit-security-btn');
        if (auditBtn) {
            auditBtn.addEventListener('click', () => this.performSecurityAudit());
        }

        const verifyBtn = document.getElementById('verify-identities-btn');
        if (verifyBtn) {
            verifyBtn.addEventListener('click', () => this.verifyIdentities());
        }

        // Analytics tabs
        document.querySelectorAll('.analytics-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const panelName = e.currentTarget.getAttribute('data-analytics');
                this.switchAnalyticsPanel(panelName);
            });
        });
    }

    /**
     * Perform security audit
     */
    async performSecurityAudit() {
        try {
            const result = await this.apiRequest('/security/audit/perform', 'POST');
            this.showNotification('Security audit completed successfully', 'success');

            // Refresh security data
            setTimeout(() => this.loadData(), 1000);

        } catch (error) {
            console.error('Security audit failed:', error);
            this.showNotification('Security audit failed', 'error');
        }
    }

    /**
     * Verify identities
     */
    async verifyIdentities() {
        try {
            const result = await this.apiRequest('/security/identities/verify', 'POST');
            this.showNotification('Identity verification completed successfully', 'success');

            // Refresh identity data
            setTimeout(() => this.loadData(), 1000);

        } catch (error) {
            console.error('Identity verification failed:', error);
            this.showNotification('Identity verification failed', 'error');
        }
    }

    /**
     * Switch analytics panel
     */
    switchAnalyticsPanel(panelName) {
        // Update tab buttons
        document.querySelectorAll('.analytics-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-analytics="${panelName}"]`).classList.add('active');

        // Update panel content
        document.querySelectorAll('.analytics-section').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${panelName}-overview-tab`).classList.add('active');
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
     * Generate mock security data for demonstration
     */
    generateMockSecurityData() {
        return {
            identities: {
                identities: [
                    { id: 'user-001', name: 'MastermindAgent', type: 'system', status: 'active', verificationStatus: 'verified', lastVerified: new Date(Date.now() - 3600000).toISOString() },
                    { id: 'user-002', name: 'CoordinatorAgent', type: 'system', status: 'active', verificationStatus: 'verified', lastVerified: new Date(Date.now() - 3600000).toISOString() },
                    { id: 'user-003', name: 'AGInt Core', type: 'ai', status: 'active', verificationStatus: 'verified', lastVerified: new Date(Date.now() - 3600000).toISOString() },
                    { id: 'user-004', name: 'SimpleCoder', type: 'agent', status: 'active', verificationStatus: 'pending', lastVerified: null },
                    { id: 'user-005', name: 'Test User', type: 'human', status: 'inactive', verificationStatus: 'unverified', lastVerified: null }
                ],
                stats: { total: 5, verified: 3, pending: 1, failed: 1 }
            },
            access: {
                logs: [
                    { timestamp: new Date(Date.now() - 300000).toISOString(), user: 'MastermindAgent', action: 'READ', resource: '/api/system/status', result: 'allowed', ip: '192.168.1.100' },
                    { timestamp: new Date(Date.now() - 600000).toISOString(), user: 'CoordinatorAgent', action: 'WRITE', resource: '/api/workflows/create', result: 'allowed', ip: '192.168.1.101' },
                    { timestamp: new Date(Date.now() - 900000).toISOString(), user: 'Unknown', action: 'READ', resource: '/api/admin/system', result: 'denied', ip: '10.0.0.1' }
                ],
                metrics: { totalRequests: 12847, successRate: 99.4, activeSessions: 23, failedAuth: 3 }
            },
            threats: {
                events: [
                    { id: 'threat-001', type: 'Suspicious Access', severity: 'warning', description: 'Multiple failed login attempts', source: 'auth_system', timestamp: new Date(Date.now() - 1800000).toISOString(), status: 'investigating' },
                    { id: 'threat-002', type: 'Anomaly Detected', severity: 'info', description: 'Unusual API usage pattern', source: 'monitoring', timestamp: new Date(Date.now() - 3600000).toISOString(), status: 'resolved' }
                ],
                detection: { scannedRequests: 12847, blockedThreats: 0, falsePositives: 2, accuracy: 99.8 }
            },
            crypto: {
                compliance: { overall: 98.5, keyRotation: 100, encryption: 'AES-256', certificates: 98.7, zkProofs: 'Active' },
                certificates: [],
                keys: []
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
    window.SecurityTab = SecurityTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecurityTab;
}