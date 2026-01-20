/**
 * GitHub Agent Tab Component
 * 
 * Dedicated tab for GitHub Agent operations including backup,
 * schedule management, and repository synchronization.
 * 
 * @module GitHubAgentTab
 */

class GitHubAgentTab extends TabComponent {
    constructor(config = {}) {
        super({
            id: 'github-agent',
            label: 'GitHub Agent',
            group: 'core',
            refreshInterval: 30000, // 30 seconds
            autoRefresh: true,
            ...config
        });

        this.backupHistory = [];
        this.scheduleSettings = {};
    }

    /**
     * Initialize the tab
     */
    async initialize() {
        await super.initialize();

        // Set up event listeners
        this.setupEventListeners();

        console.log('✅ GitHubAgentTab initialized');
        return true;
    }

    /**
     * Activate the tab
     */
    async onActivate() {
        await super.onActivate();

        // Load all data
        await Promise.all([
            this.loadGitHubStatus(),
            this.loadBackupsList(),
            this.loadScheduleSettings()
        ]);

        return true;
    }

    /**
     * Refresh tab data
     */
    async refresh() {
        if (!this.isActive) return;
        await this.loadGitHubStatus();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Refresh status button
        const refreshBtn = document.getElementById('github-tab-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadGitHubStatus());
        }

        // Create backup button
        const createBackupBtn = document.getElementById('github-tab-create-backup-btn');
        if (createBackupBtn) {
            createBackupBtn.addEventListener('click', () => this.createBackup());
        }

        // List backups button
        const listBackupsBtn = document.getElementById('github-tab-list-backups-btn');
        if (listBackupsBtn) {
            listBackupsBtn.addEventListener('click', () => this.loadBackupsList());
        }

        // Sync button
        const syncBtn = document.getElementById('github-tab-sync-btn');
        if (syncBtn) {
            syncBtn.addEventListener('click', () => this.syncWithGitHub());
        }

        // Schedule save buttons
        const saveDailyBtn = document.getElementById('github-tab-save-daily-btn');
        if (saveDailyBtn) {
            saveDailyBtn.addEventListener('click', () => this.saveSchedule('daily'));
        }

        const saveHourlyBtn = document.getElementById('github-tab-save-hourly-btn');
        if (saveHourlyBtn) {
            saveHourlyBtn.addEventListener('click', () => this.saveSchedule('hourly'));
        }

        const saveWeeklyBtn = document.getElementById('github-tab-save-weekly-btn');
        if (saveWeeklyBtn) {
            saveWeeklyBtn.addEventListener('click', () => this.saveSchedule('weekly'));
        }

        // Refresh schedule button
        const refreshScheduleBtn = document.getElementById('github-tab-refresh-schedule-btn');
        if (refreshScheduleBtn) {
            refreshScheduleBtn.addEventListener('click', () => this.loadScheduleSettings());
        }
    }

    /**
     * Load GitHub status
     */
    async loadGitHubStatus() {
        try {
            const status = await this.apiRequest('/github/status');
            this.updateStatusDisplay(status);
            this.setData('status', status);
        } catch (error) {
            console.error('Failed to load GitHub status:', error);
            this.updateStatusDisplay({ status: 'error', message: error.message });
        }
    }

    /**
     * Load backups list
     */
    async loadBackupsList() {
        try {
            const backups = await this.apiRequest('/github/backups');
            this.updateBackupsDisplay(backups);
            this.setData('backups', backups);
        } catch (error) {
            console.error('Failed to load backups:', error);
            this.showNotification(`Failed to load backups: ${error.message}`, 'error');
        }
    }

    /**
     * Load schedule settings
     */
    async loadScheduleSettings() {
        try {
            const schedule = await this.apiRequest('/github/schedule');
            this.scheduleSettings = schedule;
            this.updateScheduleDisplay(schedule);
            this.setData('schedule', schedule);
        } catch (error) {
            console.error('Failed to load schedule:', error);
        }
    }

    /**
     * Create backup
     */
    async createBackup() {
        const reasonInput = document.getElementById('github-tab-backup-reason');
        const typeSelect = document.getElementById('github-tab-backup-type');

        const reason = reasonInput?.value?.trim() || 'Manual backup';
        const backupType = typeSelect?.value || 'manual';

        const createBtn = document.getElementById('github-tab-create-backup-btn');
        if (createBtn) {
            createBtn.disabled = true;
            createBtn.textContent = 'Creating...';
        }

        try {
            const result = await this.apiRequest('/github/backup', 'POST', {
                reason,
                backup_type: backupType
            });

            this.showNotification('Backup created successfully', 'success');
            
            // Clear input
            if (reasonInput) reasonInput.value = '';

            // Refresh backups list
            await this.loadBackupsList();

        } catch (error) {
            console.error('Failed to create backup:', error);
            this.showNotification(`Failed to create backup: ${error.message}`, 'error');
        } finally {
            if (createBtn) {
                createBtn.disabled = false;
                createBtn.textContent = 'Create Backup';
            }
        }
    }

    /**
     * Sync with GitHub
     */
    async syncWithGitHub() {
        const syncBtn = document.getElementById('github-tab-sync-btn');
        if (syncBtn) {
            syncBtn.disabled = true;
            syncBtn.textContent = 'Syncing...';
        }

        try {
            const result = await this.apiRequest('/github/sync', 'POST', {});
            this.showNotification('Sync completed successfully', 'success');
            await this.loadGitHubStatus();
        } catch (error) {
            console.error('Failed to sync:', error);
            this.showNotification(`Failed to sync: ${error.message}`, 'error');
        } finally {
            if (syncBtn) {
                syncBtn.disabled = false;
                syncBtn.textContent = 'Sync with GitHub';
            }
        }
    }

    /**
     * Save schedule
     * @param {string} scheduleType - Schedule type (daily, hourly, weekly)
     */
    async saveSchedule(scheduleType) {
        let scheduleData = {};

        switch (scheduleType) {
            case 'daily':
                scheduleData = {
                    daily_enabled: document.getElementById('github-tab-daily-enabled')?.checked || false,
                    daily_time: document.getElementById('github-tab-daily-time')?.value || '02:00'
                };
                break;
            case 'hourly':
                scheduleData = {
                    hourly_enabled: document.getElementById('github-tab-hourly-enabled')?.checked || false
                };
                break;
            case 'weekly':
                scheduleData = {
                    weekly_enabled: document.getElementById('github-tab-weekly-enabled')?.checked || false,
                    weekly_day: document.getElementById('github-tab-weekly-day')?.value || 'sunday',
                    weekly_time: document.getElementById('github-tab-weekly-time')?.value || '03:00'
                };
                break;
        }

        try {
            await this.apiRequest('/github/schedule', 'POST', scheduleData);
            this.showNotification(`${scheduleType} schedule saved`, 'success');
            await this.loadScheduleSettings();
        } catch (error) {
            console.error('Failed to save schedule:', error);
            this.showNotification(`Failed to save schedule: ${error.message}`, 'error');
        }
    }

    /**
     * Update status display
     * @param {Object} status - Status data
     */
    updateStatusDisplay(status) {
        const statusEl = document.getElementById('github-tab-status-display');
        if (!statusEl) return;

        const isConnected = status.status === 'connected' || status.connected;
        const statusClass = isConnected ? 'connected' : 'disconnected';

        statusEl.innerHTML = `
            <div class="github-status-grid">
                <div class="status-item">
                    <span class="status-label">Connection:</span>
                    <span class="status-value ${statusClass}">
                        ${isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                    </span>
                </div>
                ${status.repository ? `
                    <div class="status-item">
                        <span class="status-label">Repository:</span>
                        <span class="status-value">
                            <a href="https://github.com/${status.repository}" target="_blank" rel="noopener">
                                ${status.repository}
                            </a>
                        </span>
                    </div>
                ` : ''}
                ${status.branch ? `
                    <div class="status-item">
                        <span class="status-label">Branch:</span>
                        <span class="status-value">${status.branch}</span>
                    </div>
                ` : ''}
                ${status.last_backup ? `
                    <div class="status-item">
                        <span class="status-label">Last Backup:</span>
                        <span class="status-value">${new Date(status.last_backup).toLocaleString()}</span>
                    </div>
                ` : ''}
                ${status.last_sync ? `
                    <div class="status-item">
                        <span class="status-label">Last Sync:</span>
                        <span class="status-value">${new Date(status.last_sync).toLocaleString()}</span>
                    </div>
                ` : ''}
                ${status.total_backups !== undefined ? `
                    <div class="status-item">
                        <span class="status-label">Total Backups:</span>
                        <span class="status-value">${status.total_backups}</span>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Update backups display
     * @param {Object} backups - Backups data
     */
    updateBackupsDisplay(backups) {
        const backupsEl = document.getElementById('github-tab-backups-list');
        if (!backupsEl) return;

        const backupsList = backups.backups || backups || [];

        if (backupsList.length === 0) {
            backupsEl.innerHTML = '<div class="empty-state">No backups found</div>';
            return;
        }

        backupsEl.innerHTML = backupsList.slice(0, 20).map((backup, index) => `
            <div class="backup-entry">
                <div class="backup-header">
                    <span class="backup-index">#${index + 1}</span>
                    <span class="backup-type ${backup.type || 'manual'}">${backup.type || 'manual'}</span>
                    <span class="backup-time">${new Date(backup.timestamp || backup.created_at).toLocaleString()}</span>
                </div>
                ${backup.reason ? `<div class="backup-reason">${backup.reason}</div>` : ''}
                ${backup.commit_hash ? `
                    <div class="backup-commit">
                        <span class="commit-label">Commit:</span>
                        <span class="commit-hash">${backup.commit_hash.substring(0, 8)}</span>
                    </div>
                ` : ''}
                ${backup.size ? `
                    <div class="backup-size">Size: ${this.formatBytes(backup.size)}</div>
                ` : ''}
            </div>
        `).join('');
    }

    /**
     * Update schedule display
     * @param {Object} schedule - Schedule data
     */
    updateScheduleDisplay(schedule) {
        // Daily schedule
        const dailyEnabled = document.getElementById('github-tab-daily-enabled');
        const dailyTime = document.getElementById('github-tab-daily-time');
        if (dailyEnabled) dailyEnabled.checked = schedule.daily_enabled || false;
        if (dailyTime) dailyTime.value = schedule.daily_time || '02:00';

        // Hourly schedule
        const hourlyEnabled = document.getElementById('github-tab-hourly-enabled');
        if (hourlyEnabled) hourlyEnabled.checked = schedule.hourly_enabled || false;

        // Weekly schedule
        const weeklyEnabled = document.getElementById('github-tab-weekly-enabled');
        const weeklyDay = document.getElementById('github-tab-weekly-day');
        const weeklyTime = document.getElementById('github-tab-weekly-time');
        if (weeklyEnabled) weeklyEnabled.checked = schedule.weekly_enabled || false;
        if (weeklyDay) weeklyDay.value = schedule.weekly_day || 'sunday';
        if (weeklyTime) weeklyTime.value = schedule.weekly_time || '03:00';

        // Shutdown backup
        const shutdownEnabled = document.getElementById('github-tab-shutdown-enabled');
        if (shutdownEnabled) shutdownEnabled.checked = schedule.shutdown_backup_enabled !== false;
    }

    /**
     * Format bytes to human readable
     * @param {number} bytes - Bytes
     * @returns {string} Formatted string
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type
     */
    showNotification(message, type = 'info') {
        const notificationEl = document.getElementById('github-notification');
        if (notificationEl) {
            notificationEl.textContent = message;
            notificationEl.className = `notification ${type}`;
            notificationEl.style.display = 'block';

            setTimeout(() => {
                notificationEl.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Cleanup
     */
    destroy() {
        super.destroy();
    }
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.GitHubAgentTab = GitHubAgentTab;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GitHubAgentTab;
}
