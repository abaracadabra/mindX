/**
 * mindX Tab Configuration
 * 
 * Centralized configuration for all tabs in mindX UI.
 * Easy to extend for new agents, tools, and addons.
 * 
 * @module TabConfig
 */

const TabConfig = {
    // Main tabs
    main: [
        {
            id: 'control',
            label: 'Control',
            group: 'main',
            priority: 100,
            component: 'ControlTab'
        },
        {
            id: 'agents',
            label: 'Agents',
            group: 'main',
            priority: 90,
            component: 'AgentsTab'
        },
        {
            id: 'system',
            label: 'System',
            group: 'main',
            priority: 80
        },
        {
            id: 'usage',
            label: 'Usage',
            group: 'main',
            priority: 70
        },
        {
            id: 'logs',
            label: 'Logs',
            group: 'main',
            priority: 60
        },
        {
            id: 'api',
            label: 'API',
            group: 'main',
            priority: 50
        },
        {
            id: 'faicey',
            label: 'Faicey',
            group: 'main',
            priority: 40
        },
        {
            id: 'admin',
            label: 'Admin',
            group: 'main',
            priority: 30
        }
    ],

    // Core component tabs - ordered by priority (higher = first)
    // New order: Core Systems, Evolution, Learning, Orchestration, Evolve Codebase, Query Coordinator, mindXagent, GitHub Agent
    core: [
        {
            id: 'core',
            label: 'Core Systems',
            group: 'core',
            priority: 100,
            component: 'CoreSystemsTab'
        },
        {
            id: 'evolution',
            label: 'Evolution',
            group: 'core',
            priority: 90,
            component: 'EvolutionTab'
        },
        {
            id: 'learning',
            label: 'Learning',
            group: 'core',
            priority: 80,
            component: 'LearningTab'
        },
        {
            id: 'orchestration',
            label: 'Orchestration',
            group: 'core',
            priority: 70,
            component: 'OrchestrationTab'
        },
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
            // Create activation callback
            const onActivate = async (tab) => {
                // If component class exists, instantiate it
                if (tabConfig.component && window[tabConfig.component]) {
                    const ComponentClass = window[tabConfig.component];
                    const component = new ComponentClass(tabConfig);
                    await component.initialize();
                    await component.onActivate();
                    
                    // Store component instance
                    tab.componentInstance = component;
                    
                    // Global reference for certain tabs
                    if (tabConfig.id === 'query-coordinator') {
                        window.queryCoordinatorTab = component;
                    }
                } else {
                    // Fallback to existing functions
                    if (tabConfig.id === 'mindxagent') {
                        // Use existing mindXagent functions
                        if (typeof loadMindXagentStatus === 'function') {
                            await loadMindXagentStatus();
                        }
                        if (typeof loadMindXagentOllamaStatus === 'function') {
                            await loadMindXagentOllamaStatus();
                        }
                        if (typeof loadMindXagentOllamaConversation === 'function') {
                            await loadMindXagentOllamaConversation();
                        }
                    }
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
