/**
 * mindX Tab Configuration
 *
 * Centralized configuration for all tabs in mindX UI.
 * Easy to extend for new agents, tools, and addons.
 *
 * Tab-as-extension contract:
 * 1. Add a button with data-tab="my-tab" and a panel with id="my-tab-tab" in app.html (or inject via script).
 * 2. Register the tab: either add an entry to TabConfig.main/core/tools/addons and call TabConfig.registerAllTabs(),
 *    or call tabRegistry.registerTab({ id, label, group, onActivate, onDeactivate }) directly.
 * 3. Optionally add a script (e.g. components/my-tab.js) that provides the onActivate logic or exposes a facade (e.g. window.MyTab.load()).
 * Convention: Tab content panels use id="${tabId}-tab" so the registry can show/hide them without extra config.
 *
 * @module TabConfig
 */

const TabConfig = {
    // Main tabs (component = TabComponent class name, or legacyLoader = window function name, or facade)
    main: [
        { id: 'control', label: 'Control', group: 'main', priority: 100, component: 'ControlTab' },
        { id: 'platform', label: 'Platform', group: 'main', priority: 95, component: 'PlatformTab' },
        { id: 'agents', label: 'Agents', group: 'main', priority: 90, component: 'AgentsTab' },
        { id: 'workflow', label: 'Workflow', group: 'main', priority: 88, component: 'WorkflowTab' },
        { id: 'governance', label: 'Governance', group: 'main', priority: 86, component: 'GovernanceTab' },
        { id: 'knowledge', label: 'Knowledge', group: 'main', priority: 84, component: 'KnowledgeTab' },
        { id: 'economy', label: 'Economy', group: 'main', priority: 82, component: 'EconomyTab' },
        { id: 'security', label: 'Security', group: 'main', priority: 80, component: 'SecurityTab' },
        { id: 'system', label: 'System', group: 'main', priority: 78, component: 'SystemTab' },
        { id: 'usage', label: 'Usage', group: 'main', priority: 70, legacyLoader: 'loadUsage' },
        { id: 'logs', label: 'Logs', group: 'main', priority: 60, legacyLoader: 'loadLogs' },
        { id: 'api', label: 'API', group: 'main', priority: 50, legacyLoader: 'loadAPIData' },
        { id: 'faicey', label: 'Faicey', group: 'main', priority: 40, legacyLoader: 'loadFaiceyAndInit' },
        { id: 'admin', label: 'Admin', group: 'main', priority: 30, facade: 'AdminTab', facadeMethod: 'load' },
        { id: 'ollama', label: 'Ollama', group: 'main', priority: 25, facade: 'OllamaTab', facadeMethod: 'onActivate' }
    ],

    // Core tabs: component when class exists, legacyLoader for app.js loaders
    core: [
        { id: 'core', label: 'Core Systems', group: 'core', priority: 100, legacyLoader: 'loadCoreSystems' },
        { id: 'evolution', label: 'Evolution', group: 'core', priority: 90, legacyLoader: 'loadEvolution' },
        { id: 'learning', label: 'Learning', group: 'core', priority: 80, legacyLoader: 'loadLearning' },
        { id: 'orchestration', label: 'Orchestration', group: 'core', priority: 70, legacyLoader: 'loadOrchestration' },
        {
            id: 'evolve-codebase',
            label: 'Evolve Codebase',
            group: 'core',
            priority: 65,
            component: 'EvolveCodebaseTab',
            refreshInterval: 5000,
            autoRefresh: true,
            components: {
                ollamaMonitor: {
                    type: 'OllamaMonitor',
                    config: {
                        containerId: 'evolve-ollama-monitor-container',
                        endpoint: '/mindxagent/ollama',
                        refreshInterval: 3000
                    }
                }
            }
        },
        {
            id: 'query-coordinator',
            label: 'Query Coordinator',
            group: 'core',
            priority: 60,
            component: 'QueryCoordinatorTab',
            refreshInterval: 5000,
            autoRefresh: true,
            components: {
                ollamaMonitor: {
                    type: 'OllamaMonitor',
                    config: {
                        containerId: 'query-ollama-monitor-container',
                        endpoint: '/mindxagent/ollama',
                        refreshInterval: 3000
                    }
                }
            }
        },
        {
            id: 'mindxagent',
            label: 'mindXagent',
            group: 'core',
            priority: 55,
            component: 'MindXagentTab',
            refreshInterval: 3000,
            autoRefresh: true,
            components: {
                ollamaMonitor: {
                    type: 'OllamaMonitor',
                    config: {
                        containerId: 'mindxagent-ollama-monitor-container',
                        endpoint: '/mindxagent/ollama',
                        refreshInterval: 2000
                    }
                }
            }
        },
        {
            id: 'github-agent',
            label: 'GitHub Agent',
            group: 'core',
            priority: 50,
            component: 'GitHubAgentTab',
            refreshInterval: 30000,
            autoRefresh: true
        }
    ],

    // Tool tabs (for future expansion)
    tools: [
        // Example:
        // {
        //     id: 'github-tool',
        //     label: 'GitHub Tool',
        //     group: 'tools',
        //     priority: 50,
        //     component: 'GitHubToolTab'
        // }
    ],

    // Addon tabs (for future expansion)
    addons: [
        // Example:
        // {
        //     id: 'custom-addon',
        //     label: 'Custom Addon',
        //     group: 'addons',
        //     priority: 50,
        //     component: 'CustomAddonTab'
        // }
    ],

    /**
     * Get core tabs sorted by priority (descending)
     * @returns {Array} Sorted core tabs
     */
    getSortedCoreTabs() {
        return [...this.core].sort((a, b) => b.priority - a.priority);
    },

    /**
     * Register all tabs with the tab registry
     */
    registerAllTabs() {
        if (!window.tabRegistry) {
            console.error('❌ TabRegistry not available');
            return false;
        }

        const allTabs = [
            ...this.main,
            ...this.getSortedCoreTabs(),
            ...this.tools,
            ...this.addons
        ];

        allTabs.forEach(tabConfig => {
            const onActivate = async (tab) => {
                if (tabConfig.component && window[tabConfig.component]) {
                    const ComponentClass = window[tabConfig.component];
                    const component = new ComponentClass(tabConfig);
                    await component.initialize();
                    await component.onActivate();
                    tab.componentInstance = component;
                    if (tabConfig.id === 'query-coordinator') {
                        window.queryCoordinatorTab = component;
                    }
                } else if (tabConfig.facade && tabConfig.facadeMethod && window[tabConfig.facade]) {
                    const fn = window[tabConfig.facade][tabConfig.facadeMethod];
                    if (typeof fn === 'function') {
                        await Promise.resolve(fn.call(window[tabConfig.facade]));
                    }
                } else if (tabConfig.legacyLoader && typeof window[tabConfig.legacyLoader] === 'function') {
                    await Promise.resolve(window[tabConfig.legacyLoader]());
                } else if (tabConfig.id === 'mindxagent') {
                    if (typeof window.loadMindXagentStatus === 'function') await window.loadMindXagentStatus();
                    if (typeof window.loadMindXagentOllamaStatus === 'function') await window.loadMindXagentOllamaStatus();
                    if (typeof window.loadMindXagentOllamaConversation === 'function') await window.loadMindXagentOllamaConversation();
                }
            };

            // Create deactivation callback
            const onDeactivate = async (tab) => {
                if (tab.componentInstance) {
                    await tab.componentInstance.onDeactivate();
                }
            };

            // Register tab
            window.tabRegistry.registerTab({
                id: tabConfig.id,
                label: tabConfig.label,
                group: tabConfig.group,
                onActivate,
                onDeactivate,
                refreshInterval: tabConfig.refreshInterval || null,
                components: tabConfig.components || {},
                priority: tabConfig.priority || 50
            });
        });

        console.log(`✅ Registered ${allTabs.length} tabs`);
        return true;
    },

    /**
     * Add a new tab dynamically
     * @param {Object} tabConfig - Tab configuration
     */
    addTab(tabConfig) {
        // Add to appropriate group
        const group = tabConfig.group || 'main';
        if (!this[group]) {
            this[group] = [];
        }
        this[group].push(tabConfig);

        // Register with tab registry
        if (window.tabRegistry) {
            const onActivate = async (tab) => {
                if (tabConfig.component && window[tabConfig.component]) {
                    const ComponentClass = window[tabConfig.component];
                    const component = new ComponentClass(tabConfig);
                    await component.initialize();
                    await component.onActivate();
                    tab.componentInstance = component;
                }
            };

            const onDeactivate = async (tab) => {
                if (tab.componentInstance) {
                    await tab.componentInstance.onDeactivate();
                }
            };

            window.tabRegistry.registerTab({
                id: tabConfig.id,
                label: tabConfig.label,
                group: tabConfig.group,
                onActivate,
                onDeactivate,
                refreshInterval: tabConfig.refreshInterval || null,
                components: tabConfig.components || {},
                priority: tabConfig.priority || 50
            });
        }

        console.log(`✅ Added new tab: ${tabConfig.id}`);
        return true;
    }
};

// Export for module systems
if (typeof window !== 'undefined') {
    window.TabConfig = TabConfig;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabConfig;
}
