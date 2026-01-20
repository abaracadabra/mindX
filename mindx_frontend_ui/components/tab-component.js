/**
 * Base Tab Component
 * 
 * Base class for creating modular, extensible tab components.
 * Provides common functionality for all tabs in mindX.
 * 
 * @module TabComponent
 */

class TabComponent {
    constructor(config = {}) {
        this.config = {
            id: config.id || 'unknown',
            label: config.label || 'Unknown Tab',
            group: config.group || 'main',
            refreshInterval: config.refreshInterval || null,
            autoRefresh: config.autoRefresh || false,
            ...config
        };

        this.isActive = false;
        this.refreshIntervalId = null;
        this.components = new Map();
        this.data = {};

        console.log(`📑 TabComponent created: ${this.config.id}`);
    }

    /**
     * Initialize the tab component
     * Override in subclasses
     */
    async initialize() {
        console.log(`✅ TabComponent initialized: ${this.config.id}`);
        return true;
    }

    /**
     * Activate the tab
     * Override in subclasses
     */
    async onActivate() {
        this.isActive = true;
        console.log(`🟢 Tab activated: ${this.config.id}`);

        // Start auto-refresh if enabled
        if (this.config.autoRefresh && this.config.refreshInterval) {
            this.startAutoRefresh();
        }

        return true;
    }

    /**
     * Deactivate the tab
     * Override in subclasses
     */
    async onDeactivate() {
        this.isActive = false;
        console.log(`🔴 Tab deactivated: ${this.config.id}`);

        // Stop auto-refresh
        this.stopAutoRefresh();

        return true;
    }

    /**
     * Refresh tab data
     * Override in subclasses
     */
    async refresh() {
        console.log(`🔄 Refreshing tab: ${this.config.id}`);
        return true;
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        if (this.refreshIntervalId) {
            return; // Already running
        }

        if (!this.config.refreshInterval) {
            console.warn(`⚠️ No refresh interval configured for ${this.config.id}`);
            return;
        }

        this.refreshIntervalId = setInterval(async () => {
            if (this.isActive) {
                await this.refresh();
            }
        }, this.config.refreshInterval);

        console.log(`🔄 Auto-refresh started for ${this.config.id}`);
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
            this.refreshIntervalId = null;
            console.log(`⏹️ Auto-refresh stopped for ${this.config.id}`);
        }
    }

    /**
     * Register a sub-component
     * @param {string} componentId - Component ID
     * @param {Object} component - Component instance
     */
    registerComponent(componentId, component) {
        this.components.set(componentId, component);
        console.log(`✅ Component registered: ${this.config.id}.${componentId}`);
    }

    /**
     * Get a sub-component
     * @param {string} componentId - Component ID
     * @returns {Object|null} Component instance
     */
    getComponent(componentId) {
        return this.components.get(componentId) || null;
    }

    /**
     * Update tab data
     * @param {string} key - Data key
     * @param {*} value - Data value
     */
    setData(key, value) {
        this.data[key] = value;
    }

    /**
     * Get tab data
     * @param {string} key - Data key
     * @returns {*} Data value
     */
    getData(key) {
        return this.data[key];
    }

    /**
     * Make API request
     * @param {string} endpoint - API endpoint
     * @param {string} method - HTTP method
     * @param {Object} body - Request body
     * @returns {Promise} Response data
     */
    async apiRequest(endpoint, method = 'GET', body = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            if (body) {
                options.body = JSON.stringify(body);
            }

            const response = await fetch(endpoint, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`❌ API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message
     * @param {HTMLElement} container - Container element
     */
    showError(message, container = null) {
        const errorHtml = `
            <div class="error-message">
                <div class="error-icon">❌</div>
                <div class="error-text">${message}</div>
            </div>
        `;

        if (container) {
            container.innerHTML = errorHtml;
        } else {
            console.error(`❌ ${this.config.id}: ${message}`);
        }
    }

    /**
     * Show loading state
     * @param {HTMLElement} container - Container element
     */
    showLoading(container = null) {
        const loadingHtml = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <div class="loading-text">Loading...</div>
            </div>
        `;

        if (container) {
            container.innerHTML = loadingHtml;
        }
    }

    /**
     * Cleanup
     */
    destroy() {
        this.stopAutoRefresh();
        this.components.clear();
        this.data = {};
        console.log(`🧹 TabComponent destroyed: ${this.config.id}`);
    }
}

// Export for module systems
if (typeof window !== 'undefined') {
    window.TabComponent = TabComponent;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabComponent;
}
