/**
 * Admin Tab Component
 * Encapsulates Admin tab logic: config, PostgreSQL, Vault, monitoring metrics.
 * Depends on window.sendRequest and window.addLog (provided by app.js).
 */
(function () {
    'use strict';

    function sendRequest() {
        return window.sendRequest ? window.sendRequest.apply(window, arguments) : Promise.reject(new Error('sendRequest not available'));
    }
    function addLog(msg, level) {
        if (window.addLog) window.addLog(msg, level);
    }

    function displayConfig(config) {
        const configDisplay = document.getElementById('config-display');
        if (!configDisplay) return;
        configDisplay.innerHTML = config
            ? `<pre>${JSON.stringify(config, null, 2)}</pre>`
            : '<p>Configuration unavailable</p>';
    }

    async function loadAdminMonitoringMetrics() {
        const container = document.getElementById('admin-inbound-metrics');
        if (!container) return;
        container.innerHTML = '<span class="loading-message">Loading inbound metrics…</span>';
        try {
            const data = await sendRequest('/api/monitoring/inbound');
            const m = data?.inbound_metrics || {};
            const limit = data?.inbound_rate_limit;
            const fmt = (n) => (n == null ? '—' : (typeof n === 'number' && Number.isFinite(n) ? Number(n).toLocaleString() : String(n)));
            const fmtMs = (n) => (n == null ? '—' : (typeof n === 'number' ? Number(n).toFixed(2) + ' ms' : String(n)));
            const fmtBytes = (n) => (n == null ? '—' : (typeof n === 'number' ? (n >= 1024 ? (n / 1024).toFixed(1) + ' KB' : n + ' B') : String(n)));
            container.innerHTML = `
                <div class="metrics-grid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:10px; margin-top:8px;">
                    <div class="metric-card"><div class="metric-label">Total requests</div><div class="metric-value">${fmt(m.total_requests)}</div></div>
                    <div class="metric-card"><div class="metric-label">Requests/min</div><div class="metric-value">${fmt(m.requests_per_minute)}</div></div>
                    <div class="metric-card"><div class="metric-label">Avg latency</div><div class="metric-value">${fmtMs(m.average_latency_ms)}</div></div>
                    <div class="metric-card"><div class="metric-label">Latency p50</div><div class="metric-value">${fmtMs(m.latency_p50_ms)}</div></div>
                    <div class="metric-card"><div class="metric-label">Latency p90</div><div class="metric-value">${fmtMs(m.latency_p90_ms)}</div></div>
                    <div class="metric-card"><div class="metric-label">Latency p99</div><div class="metric-value">${fmtMs(m.latency_p99_ms)}</div></div>
                    <div class="metric-card"><div class="metric-label">Request bytes</div><div class="metric-value">${fmtBytes(m.total_request_bytes)}</div></div>
                    <div class="metric-card"><div class="metric-label">Response bytes</div><div class="metric-value">${fmtBytes(m.total_response_bytes)}</div></div>
                    <div class="metric-card"><div class="metric-label">Rate limit rejects</div><div class="metric-value">${fmt(m.rate_limit_rejects)}</div></div>
                </div>
                ${limit && limit.requests_per_minute ? `<p class="admin-hint" style="margin-top:8px;">Inbound limit: ${limit.requests_per_minute} req/min (window ${limit.window_s}s)</p>` : ''}
            `;
        } catch (e) {
            container.innerHTML = '<span class="status-item error">Failed to load inbound metrics: ' + (e?.message || String(e)) + '</span>';
        }
    }

    async function loadAdminOllamaMetrics() {
        const container = document.getElementById('ollama-metrics-display');
        if (!container) return;
        try {
            const baseUrl = (typeof window !== 'undefined' && window.API_CONFIG && window.API_CONFIG.baseUrl) ? window.API_CONFIG.baseUrl.replace(/\/$/, '') : '';
            const res = await fetch(baseUrl + '/api/admin/ollama/metrics');
            const data = await res.json().catch(() => ({}));
            const metrics = data?.metrics || {};
            const successRate = (metrics.total_requests > 0 && metrics.successful_requests != null)
                ? ((metrics.successful_requests / metrics.total_requests) * 100).toFixed(1) : '0.0';
            container.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-label">Total requests</div><div class="metric-value">${metrics.total_requests ?? '—'}</div></div>
                    <div class="metric-card"><div class="metric-label">Success rate</div><div class="metric-value">${successRate}%</div></div>
                    <div class="metric-card"><div class="metric-label">Failed requests</div><div class="metric-value error">${metrics.failed_requests ?? '—'}</div></div>
                    <div class="metric-card"><div class="metric-label">Total tokens</div><div class="metric-value">${(metrics.total_tokens ?? 0).toLocaleString()}</div></div>
                    <div class="metric-card"><div class="metric-label">Avg latency</div><div class="metric-value">${(metrics.average_latency_ms ?? 0).toFixed(0)} ms</div></div>
                    <div class="metric-card"><div class="metric-label">Rate limit hits</div><div class="metric-value warning">${metrics.rate_limit_hits ?? '—'}</div></div>
                </div>
            `;
        } catch (e) {
            container.innerHTML = '<span class="status-item error">Ollama metrics unavailable: ' + (e?.message || String(e)) + '</span>';
        }
    }

    async function loadPostgreSQLSettings() {
        try {
            const response = await sendRequest('/admin/postgresql/config');
            if (response.status === 'success' && response.config) {
                const config = response.config;
                const hostEl = document.getElementById('postgres-host');
                const portEl = document.getElementById('postgres-port');
                const dbEl = document.getElementById('postgres-database');
                const userEl = document.getElementById('postgres-user');
                const pwEl = document.getElementById('postgres-password');
                if (hostEl) hostEl.value = config.host || 'localhost';
                if (portEl) portEl.value = config.port || 5432;
                if (dbEl) dbEl.value = config.database || 'mindx_memory';
                if (userEl) userEl.value = config.user || 'mindx';
                if (pwEl && config.has_password) {
                    pwEl.placeholder = 'Password is set (enter new to change)';
                }
            }
        } catch (error) {
            addLog('Failed to load PostgreSQL settings: ' + error.message, 'ERROR');
        }
    }

    async function savePostgreSQLSettings() {
        const config = {
            host: document.getElementById('postgres-host')?.value,
            port: parseInt(document.getElementById('postgres-port')?.value, 10),
            database: document.getElementById('postgres-database')?.value,
            user: document.getElementById('postgres-user')?.value,
            password: document.getElementById('postgres-password')?.value || undefined
        };
        try {
            const response = await sendRequest('/admin/postgresql/config', 'POST', config);
            if (response.status === 'success') {
                addLog('PostgreSQL settings saved to vault', 'SUCCESS');
                const pwEl = document.getElementById('postgres-password');
                if (pwEl) {
                    pwEl.value = '';
                    pwEl.placeholder = 'Password saved';
                }
            }
        } catch (error) {
            addLog('Failed to save PostgreSQL settings: ' + error.message, 'ERROR');
        }
    }

    async function testPostgreSQLConnection() {
        const config = {
            host: document.getElementById('postgres-host')?.value,
            port: parseInt(document.getElementById('postgres-port')?.value, 10),
            database: document.getElementById('postgres-database')?.value,
            user: document.getElementById('postgres-user')?.value,
            password: document.getElementById('postgres-password')?.value || undefined
        };
        const statusDiv = document.getElementById('postgres-connection-status');
        if (!statusDiv) return;
        statusDiv.innerHTML = '<p>Testing connection...</p>';
        statusDiv.className = 'connection-status testing';
        try {
            const response = await sendRequest('/admin/postgresql/test', 'POST', config);
            if (response.status === 'success') {
                statusDiv.innerHTML = `<p class="success">✓ Connection successful</p><p>${response.version || ''}</p>`;
                statusDiv.className = 'connection-status success';
            } else {
                statusDiv.innerHTML = `<p class="error">✗ ${response.message || 'Unknown error'}</p>`;
                statusDiv.className = 'connection-status error';
            }
        } catch (error) {
            statusDiv.innerHTML = '<p class="error">✗ Connection failed: ' + error.message + '</p>';
            statusDiv.className = 'connection-status error';
        }
    }

    function initializePostgreSQLHandlers() {
        const loadBtn = document.getElementById('load-postgres-settings-btn');
        const saveBtn = document.getElementById('save-postgres-settings-btn');
        const testBtn = document.getElementById('test-postgres-connection-btn');
        const togglePasswordBtn = document.getElementById('toggle-postgres-password');
        if (loadBtn) loadBtn.addEventListener('click', loadPostgreSQLSettings);
        if (saveBtn) saveBtn.addEventListener('click', savePostgreSQLSettings);
        if (testBtn) testBtn.addEventListener('click', testPostgreSQLConnection);
        if (togglePasswordBtn) {
            togglePasswordBtn.addEventListener('click', () => {
                const passwordInput = document.getElementById('postgres-password');
                if (!passwordInput) return;
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    togglePasswordBtn.textContent = '🙈';
                } else {
                    passwordInput.type = 'password';
                    togglePasswordBtn.textContent = '👁️';
                }
            });
        }
    }

    async function loadVaultKeys() {
        try {
            const response = await sendRequest('/admin/vault/keys');
            if (response.status === 'success') {
                const keysList = document.getElementById('vault-keys-list');
                if (!keysList) return;
                if (response.keys && response.keys.length > 0) {
                    keysList.innerHTML = `
                        <table class="vault-keys-table">
                            <thead>
                                <tr>
                                    <th>Agent ID</th>
                                    <th>Environment Variable</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${response.keys.map(key => `
                                    <tr>
                                        <td>${key.agent_id}</td>
                                        <td><code>${key.env_var}</code></td>
                                        <td>${key.has_key ? '<span class="status-badge success">Stored</span>' : '<span class="status-badge warning">Missing</span>'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                        <p>Total: ${response.count} keys</p>
                    `;
                } else {
                    keysList.innerHTML = '<p>No agent keys found in vault. Use "Migrate Keys to Vault" to move existing keys.</p>';
                }
            }
        } catch (error) {
            addLog('Failed to load vault keys: ' + error.message, 'ERROR');
        }
    }

    async function migrateKeysToVault() {
        const statusDiv = document.getElementById('vault-migration-status');
        if (!statusDiv) return;
        statusDiv.innerHTML = '<p>Migrating keys from legacy storage...</p>';
        statusDiv.className = 'migration-status processing';
        try {
            const response = await sendRequest('/admin/vault/migrate', 'POST');
            if (response.status === 'success') {
                const migration = response.migration || {};
                statusDiv.innerHTML = `
                    <p class="success">Migration complete!</p>
                    <p>Migrated: ${migration.migrated ?? 0} keys</p>
                    <p>Failed: ${migration.failed ?? 0} keys</p>
                    ${(migration.errors && migration.errors.length) ? '<p class="error">Errors: ' + migration.errors.join(', ') + '</p>' : ''}
                `;
                statusDiv.className = 'migration-status success';
                await loadVaultKeys();
            }
        } catch (error) {
            statusDiv.innerHTML = '<p class="error">Migration failed: ' + error.message + '</p>';
            statusDiv.className = 'migration-status error';
        }
    }

    function initializeVaultHandlers() {
        const refreshBtn = document.getElementById('refresh-vault-keys-btn');
        const migrateBtn = document.getElementById('migrate-keys-to-vault-btn');
        if (refreshBtn) refreshBtn.addEventListener('click', loadVaultKeys);
        if (migrateBtn) migrateBtn.addEventListener('click', migrateKeysToVault);
    }

    async function load() {
        const crossmintToggle = document.getElementById('crossmint-enabled-toggle');
        const saveSettingsBtn = document.getElementById('save-settings-btn');
        if (crossmintToggle) {
            const crossmintEnabled = localStorage.getItem('crossmint_enabled') === 'true';
            crossmintToggle.checked = crossmintEnabled;
            if (localStorage.getItem('crossmint_enabled') === null) {
                localStorage.setItem('crossmint_enabled', 'false');
            }
        }
        if (saveSettingsBtn && crossmintToggle) {
            saveSettingsBtn.addEventListener('click', () => {
                const enabled = crossmintToggle.checked;
                localStorage.setItem('crossmint_enabled', enabled.toString());
                if (window.alert) window.alert('CrossMint integration ' + (enabled ? 'enabled' : 'disabled') + '. Please refresh the page for changes to take effect.');
            });
        }
        if (!window.windowManager) {
            setTimeout(() => {}, 200);
        }
        try {
            const config = await sendRequest('/system/config');
            displayConfig(config);
            await loadPostgreSQLSettings();
            await loadVaultKeys();
            initializePostgreSQLHandlers();
            initializeVaultHandlers();
            loadAdminMonitoringMetrics().catch(() => {});
            loadAdminOllamaMetrics().catch(() => {});
        } catch (error) {
            addLog('Failed to load admin data: ' + error.message, 'ERROR');
        }
        const metricsRefreshBtn = document.getElementById('admin-metrics-refresh');
        if (metricsRefreshBtn) {
            metricsRefreshBtn.addEventListener('click', () => {
                loadAdminMonitoringMetrics().catch(() => {});
                loadAdminOllamaMetrics().catch(() => {});
            });
        }
    }

    async function restartSystem() {
        if (window.confirm && !window.confirm('Are you sure you want to restart the system?')) return;
        try {
            await sendRequest('/system/restart', 'POST');
            addLog('System restart initiated', 'INFO');
        } catch (error) {
            addLog('System restart failed: ' + error.message, 'ERROR');
        }
    }

    async function backupSystem() {
        try {
            await sendRequest('/system/backup', 'POST');
            addLog('System backup initiated', 'INFO');
        } catch (error) {
            addLog('System backup failed: ' + error.message, 'ERROR');
        }
    }

    async function updateConfig() {
        const newConfig = window.prompt ? window.prompt('Enter new configuration (JSON):', '{}') : null;
        if (!newConfig) return;
        try {
            const config = JSON.parse(newConfig);
            await sendRequest('/system/config', 'PUT', config);
            addLog('Configuration updated', 'INFO');
            await load();
        } catch (error) {
            addLog('Configuration update failed: ' + error.message, 'ERROR');
        }
    }

    window.AdminTab = {
        load: load,
        displayConfig: displayConfig,
        loadAdminMonitoringMetrics: loadAdminMonitoringMetrics,
        loadAdminOllamaMetrics: loadAdminOllamaMetrics,
        loadPostgreSQLSettings: loadPostgreSQLSettings,
        savePostgreSQLSettings: savePostgreSQLSettings,
        testPostgreSQLConnection: testPostgreSQLConnection,
        loadVaultKeys: loadVaultKeys,
        restartSystem: restartSystem,
        backupSystem: backupSystem,
        updateConfig: updateConfig
    };
})();
