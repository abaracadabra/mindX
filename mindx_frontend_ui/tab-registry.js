/**
 * mindX Tab Registry System
 * 
 * Modular, extensible tab management system for mindX UI.
 * Supports dynamic tab registration, component-based architecture,
 * and scalable expansion for agents, tools, and addons.
 * 
 * @module TabRegistry
 */

class TabRegistry {
    constructor() {
        this.tabs = new Map();
        this.tabGroups = new Map();
        this.activeTab = null;
        this.refreshIntervals = new Map();
        this.tabComponents = new Map();
        
        console.log('📋 TabRegistry initialized');
    }

    /**
     * Register a new tab
     * @param {Object} config - Tab configuration
     * @param {string} config.id - Unique tab identifier
     * @param {string} config.label - Display label
     * @param {string} config.group - Tab group (e.g., 'main', 'core', 'tools')
     * @param {Function} config.onActivate - Callback when tab is activated
     * @param {Function} config.onDeactivate - Callback when tab is deactivated
     * @param {number} config.refreshInterval - Auto-refresh interval in ms (optional)
     * @param {Object} config.components - Component configuration (optional)
     */
    registerTab(config) {
        const {
            id,
            label,
            group = 'main',
            onActivate = null,
            onDeactivate = null,
            refreshInterval = null,
            components = {},
            priority = 100
        } = config;

        if (!id || !label) {
            console.error('❌ Tab registration failed: id and label are required');
            return false;
        }

        if (this.tabs.has(id)) {
            console.warn(`⚠️ Tab ${id} already registered, updating...`);
        }

        const tabConfig = {
            id,
            label,
            group,
            onActivate,
            onDeactivate,
            refreshInterval,
            components,
            priority,
            registeredAt: Date.now()
        };

        this.tabs.set(id, tabConfig);

        // Register in group
        if (!this.tabGroups.has(group)) {
            this.tabGroups.set(group, []);
        }
        this.tabGroups.get(group).push(id);
        this.tabGroups.get(group).sort((a, b) => {
            const tabA = this.tabs.get(a);
            const tabB = this.tabs.get(b);
            return (tabB?.priority || 100) - (tabA?.priority || 100);
        });

        console.log(`✅ Tab registered: ${id} (group: ${group})`);
        return true;
    }

    /**
     * Register a tab component
     * @param {string} tabId - Tab ID
     * @param {string} componentId - Component ID
     * @param {Object} component - Component configuration
     */
    registerComponent(tabId, componentId, component) {
        if (!this.tabs.has(tabId)) {
            console.error(`❌ Cannot register component: Tab ${tabId} not found`);
            return false;
        }

        const tab = this.tabs.get(tabId);
        if (!tab.components) {
            tab.components = {};
        }

        tab.components[componentId] = {
            ...component,
            registeredAt: Date.now()
        };

        console.log(`✅ Component registered: ${tabId}.${componentId}`);
        return true;
    }

    /**
     * Activate a tab
     * @param {string} tabId - Tab ID
     */
    async activateTab(tabId) {
        if (!this.tabs.has(tabId)) {
            console.error(`❌ Tab ${tabId} not found`);
            return false;
        }

        // Deactivate current tab
        if (this.activeTab && this.activeTab !== tabId) {
            await this.deactivateTab(this.activeTab);
        }

        const tab = this.tabs.get(tabId);
        this.activeTab = tabId;

        // Update UI
        this.updateTabUI(tabId, true);

        // Call activation callback
        if (tab.onActivate) {
            try {
                await tab.onActivate(tab);
            } catch (error) {
                console.error(`❌ Error in tab activation callback for ${tabId}:`, error);
            }
        }

        // Start auto-refresh if configured
        if (tab.refreshInterval) {
            this.startAutoRefresh(tabId, tab.refreshInterval);
        }

        console.log(`✅ Tab activated: ${tabId}`);
        return true;
    }

    /**
     * Deactivate a tab
     * @param {string} tabId - Tab ID
     */
    async deactivateTab(tabId) {
        if (!this.tabs.has(tabId)) {
            return false;
        }

        const tab = this.tabs.get(tabId);

        // Stop auto-refresh
        this.stopAutoRefresh(tabId);

        // Call deactivation callback
        if (tab.onDeactivate) {
            try {
                await tab.onDeactivate(tab);
            } catch (error) {
                console.error(`❌ Error in tab deactivation callback for ${tabId}:`, error);
            }
        }

        // Update UI
        this.updateTabUI(tabId, false);

        if (this.activeTab === tabId) {
            this.activeTab = null;
        }

        console.log(`✅ Tab deactivated: ${tabId}`);
        return true;
    }

    /**
     * Update tab UI elements
     * @param {string} tabId - Tab ID
     * @param {boolean} active - Whether tab should be active
     */
    updateTabUI(tabId, active) {
        // Update button
        const button = document.querySelector(`[data-tab="${tabId}"]`);
        if (button) {
            if (active) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        }

        // Update content
        const content = document.getElementById(`${tabId}-tab`);
        if (content) {
            if (active) {
                content.classList.add('active');
                content.style.display = 'block';
                content.style.visibility = 'visible';
                content.style.opacity = '1';
            } else {
                content.classList.remove('active');
                content.style.display = 'none';
                content.style.visibility = 'hidden';
                content.style.opacity = '0';
            }
        }
    }

    /**
     * Start auto-refresh for a tab
     * @param {string} tabId - Tab ID
     * @param {number} interval - Refresh interval in ms
     */
    startAutoRefresh(tabId, interval) {
        this.stopAutoRefresh(tabId);

        const intervalId = setInterval(async () => {
            const tab = this.tabs.get(tabId);
            if (tab && tab.onActivate) {
                try {
                    await tab.onActivate(tab);
                } catch (error) {
                    console.error(`❌ Error in auto-refresh for ${tabId}:`, error);
                }
            }
        }, interval);

        this.refreshIntervals.set(tabId, intervalId);
        console.log(`🔄 Auto-refresh started for ${tabId} (${interval}ms)`);
    }

    /**
     * Stop auto-refresh for a tab
     * @param {string} tabId - Tab ID
     */
    stopAutoRefresh(tabId) {
        const intervalId = this.refreshIntervals.get(tabId);
        if (intervalId) {
            clearInterval(intervalId);
            this.refreshIntervals.delete(tabId);
            console.log(`⏹️ Auto-refresh stopped for ${tabId}`);
        }
    }

    /**
     * Get tab configuration
     * @param {string} tabId - Tab ID
     * @returns {Object|null} Tab configuration
     */
    getTab(tabId) {
        return this.tabs.get(tabId) || null;
    }

    /**
     * Get all tabs in a group
     * @param {string} group - Group name
     * @returns {Array} Array of tab IDs
     */
    getTabsInGroup(group) {
        return this.tabGroups.get(group) || [];
    }

    /**
     * Get all registered tabs
     * @returns {Array} Array of tab configurations
     */
    getAllTabs() {
        return Array.from(this.tabs.values());
    }

    /**
     * Unregister a tab
     * @param {string} tabId - Tab ID
     */
    unregisterTab(tabId) {
        if (this.activeTab === tabId) {
            this.deactivateTab(tabId);
        }

        this.stopAutoRefresh(tabId);
        this.tabs.delete(tabId);

        // Remove from groups
        for (const [group, tabs] of this.tabGroups.entries()) {
            const index = tabs.indexOf(tabId);
            if (index > -1) {
                tabs.splice(index, 1);
            }
        }

        console.log(`🗑️ Tab unregistered: ${tabId}`);
        return true;
    }
}

// Create global instance
window.tabRegistry = new TabRegistry();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabRegistry;
}
