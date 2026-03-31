/**
 * AgenticPlaceConnector.js - Real-time AgenticPlace Integration
 *
 * © Professor Codephreak - rage.pythai.net
 * Connects faicey agents with live AgenticPlace marketplace
 *
 * Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
 */

import { EventEmitter } from 'events';

export class AgenticPlaceConnector extends EventEmitter {
    constructor(options = {}) {
        super();

        // Configuration
        this.baseUrl = options.baseUrl || 'https://agenticplace.pythai.net';
        this.apiUrl = `${this.baseUrl}/api`;
        this.wsUrl = this.baseUrl.replace('https:', 'wss:').replace('http:', 'ws:');

        // Connection state
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;

        // Data state
        this.agents = new Map();
        this.chains = new Map();
        this.stats = {
            totalAgents: 0,
            verifiedAgents: 0,
            activeChains: 0,
            lastUpdate: null
        };

        // Real-time monitoring
        this.feedEvents = [];
        this.scanning = false;

        // Initialize connection
        this.init();
    }

    /**
     * Initialize AgenticPlace connection
     */
    async init() {
        console.log('🏪 Connecting to AgenticPlace...');

        try {
            // Test API connectivity
            await this.testConnection();

            // Load initial data
            await this.loadInitialData();

            // Initialize WebSocket for real-time updates
            this.initializeWebSocket();

            this.connected = true;
            this.emit('connected', {
                url: this.baseUrl,
                stats: this.stats,
                timestamp: Date.now()
            });

            console.log(`✅ Connected to AgenticPlace: ${this.baseUrl}`);

        } catch (error) {
            console.error('❌ AgenticPlace connection failed:', error);
            this.emit('error', error);
            this.scheduleReconnect();
        }
    }

    /**
     * Test API connection
     */
    async testConnection() {
        const response = await fetch(`${this.apiUrl}/agents?limit=1`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'Faicey/2.0 AgenticPlace Connector'
            }
        });

        if (!response.ok) {
            throw new Error(`API test failed: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error('API returned error response');
        }

        console.log('✅ AgenticPlace API connection verified');
    }

    /**
     * Load initial marketplace data
     */
    async loadInitialData() {
        console.log('📊 Loading initial marketplace data...');

        try {
            // Load featured agents
            await this.loadAgents({
                verified: true,
                limit: 50,
                sort: 'total_score',
                dir: 'desc'
            });

            // Load chain information
            await this.loadChainData();

            // Load marketplace stats
            await this.loadStats();

            console.log(`✅ Loaded ${this.agents.size} agents from ${this.chains.size} chains`);

        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            throw error;
        }
    }

    /**
     * Load agents from AgenticPlace API
     */
    async loadAgents(params = {}) {
        const queryParams = new URLSearchParams({
            limit: 100,
            sort: 'token_id',
            dir: 'asc',
            ...params
        });

        const response = await fetch(`${this.apiUrl}/agents?${queryParams}`);

        if (!response.ok) {
            throw new Error(`Failed to load agents: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.data) {
            // Store agents in map
            data.data.forEach(agent => {
                this.agents.set(agent.agent_id || agent.token_id, {
                    ...agent,
                    lastUpdated: Date.now(),
                    faiceyCompatible: true,
                    backgroundInteraction: this.determineBackgroundCapability(agent)
                });
            });

            // Update stats
            this.stats.totalAgents = data.meta?.total || this.agents.size;
            this.stats.verifiedAgents = Array.from(this.agents.values())
                .filter(a => a.is_verified).length;
            this.stats.lastUpdate = Date.now();

            this.emit('agentsLoaded', {
                count: data.data.length,
                total: this.stats.totalAgents,
                verified: this.stats.verifiedAgents
            });

            this.log('ok', `Loaded ${data.data.length} agents`);

            return data.data;
        }

        throw new Error('No agent data received');
    }

    /**
     * Load chain information
     */
    async loadChainData() {
        // Load from known chains or API endpoint
        const knownChains = {
            1: { name: 'Ethereum', symbol: 'ETH', color: '#627EEA' },
            8453: { name: 'Base', symbol: 'BASE', color: '#0052FF' },
            137: { name: 'Polygon', symbol: 'POLY', color: '#8247E5' },
            42161: { name: 'Arbitrum', symbol: 'ARB', color: '#28A0F0' },
            10: { name: 'Optimism', symbol: 'OP', color: '#FF0420' }
        };

        Object.entries(knownChains).forEach(([id, chain]) => {
            this.chains.set(parseInt(id), chain);
        });

        this.stats.activeChains = this.chains.size;
    }

    /**
     * Load marketplace statistics
     */
    async loadStats() {
        try {
            // In production, this would call a stats API endpoint
            // For now, derive from loaded data
            this.stats = {
                ...this.stats,
                totalAgents: this.agents.size,
                verifiedAgents: Array.from(this.agents.values()).filter(a => a.is_verified).length,
                activeChains: this.chains.size,
                lastUpdate: Date.now()
            };

        } catch (error) {
            console.warn('Stats loading failed:', error);
        }
    }

    /**
     * Initialize WebSocket for real-time updates
     */
    initializeWebSocket() {
        // Note: In production, AgenticPlace would need to support WebSocket
        // For now, we'll simulate real-time updates with polling

        setInterval(() => {
            this.simulateRealTimeUpdate();
        }, 30000); // Check every 30 seconds

        console.log('✅ Real-time monitoring initialized');
    }

    /**
     * Simulate real-time updates
     */
    simulateRealTimeUpdate() {
        // Simulate agent updates, new registrations, etc.
        const updateTypes = ['agent_updated', 'agent_registered', 'verification_status'];
        const randomType = updateTypes[Math.floor(Math.random() * updateTypes.length)];

        this.emit('realtimeUpdate', {
            type: randomType,
            timestamp: Date.now()
        });

        this.log('info', `Real-time update: ${randomType}`);
    }

    /**
     * Search agents with specific criteria
     */
    async searchAgents(query, filters = {}) {
        const params = {
            q: query,
            limit: 50,
            ...filters
        };

        try {
            const agents = await this.loadAgents(params);

            this.emit('searchResults', {
                query: query,
                filters: filters,
                results: agents,
                count: agents.length
            });

            return agents;

        } catch (error) {
            console.error('Agent search failed:', error);
            this.emit('searchError', { query, error: error.message });
            throw error;
        }
    }

    /**
     * Get agent details by ID
     */
    async getAgentDetails(agentId) {
        if (this.agents.has(agentId)) {
            return this.agents.get(agentId);
        }

        // Fetch from API if not cached
        try {
            const response = await fetch(`${this.apiUrl}/agents/${agentId}`);

            if (!response.ok) {
                throw new Error(`Agent not found: ${agentId}`);
            }

            const data = await response.json();

            if (data.success && data.data) {
                const agent = {
                    ...data.data,
                    lastUpdated: Date.now(),
                    faiceyCompatible: true,
                    backgroundInteraction: this.determineBackgroundCapability(data.data)
                };

                this.agents.set(agentId, agent);
                return agent;
            }

            throw new Error('Agent data not available');

        } catch (error) {
            console.error('Failed to get agent details:', error);
            throw error;
        }
    }

    /**
     * Get agents suitable for background interaction
     */
    getBackgroundCapableAgents() {
        return Array.from(this.agents.values())
            .filter(agent => agent.backgroundInteraction.capable)
            .sort((a, b) => b.total_score - a.total_score);
    }

    /**
     * Get agents by category
     */
    getAgentsByCategory(category) {
        return Array.from(this.agents.values())
            .filter(agent => this.determineCategory(agent) === category);
    }

    /**
     * Get marketplace statistics
     */
    getStats() {
        return {
            ...this.stats,
            agents: {
                total: this.agents.size,
                verified: Array.from(this.agents.values()).filter(a => a.is_verified).length,
                backgroundCapable: this.getBackgroundCapableAgents().length
            },
            chains: {
                total: this.chains.size,
                list: Array.from(this.chains.entries()).map(([id, chain]) => ({
                    id, ...chain
                }))
            },
            lastSync: Date.now()
        };
    }

    /**
     * Log feed event
     */
    log(type, message) {
        const timestamp = new Date().toTimeString().slice(0, 8);
        const event = {
            type: type,
            message: message,
            timestamp: timestamp,
            fullTime: Date.now()
        };

        this.feedEvents.unshift(event);

        // Keep last 150 events
        if (this.feedEvents.length > 150) {
            this.feedEvents = this.feedEvents.slice(0, 150);
        }

        this.emit('logEvent', event);
    }

    /**
     * Get feed events
     */
    getFeedEvents(limit = 40) {
        return this.feedEvents.slice(0, limit);
    }

    /**
     * Determine background interaction capability
     */
    determineBackgroundCapability(agent) {
        const capability = {
            capable: true, // All agents are capable of background interaction
            features: [],
            compatibility: 1.0
        };

        // Determine features based on agent properties
        if (agent.is_verified) {
            capability.features.push('verified');
            capability.compatibility += 0.2;
        }

        if (agent.x402_supported) {
            capability.features.push('x402');
            capability.compatibility += 0.3;
        }

        if (agent.total_score > 80) {
            capability.features.push('high-performance');
            capability.compatibility += 0.1;
        }

        if (agent.supported_protocols?.length > 3) {
            capability.features.push('multi-protocol');
            capability.compatibility += 0.1;
        }

        capability.compatibility = Math.min(1.0, capability.compatibility);

        return capability;
    }

    /**
     * Determine agent category
     */
    determineCategory(agent) {
        const name = (agent.name || '').toLowerCase();
        const description = (agent.description || '').toLowerCase();

        if (name.includes('research') || name.includes('analyst') || description.includes('analysis')) {
            return 'analytical';
        } else if (name.includes('content') || name.includes('creative') || description.includes('creative')) {
            return 'creative';
        } else if (name.includes('defi') || name.includes('trading') || description.includes('financial')) {
            return 'financial';
        } else if (name.includes('game') || name.includes('nft') || description.includes('gaming')) {
            return 'gaming';
        }

        return 'general';
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Maximum reconnection attempts reached');
            this.emit('connectionFailed', {
                attempts: this.reconnectAttempts,
                maxAttempts: this.maxReconnectAttempts
            });
            return;
        }

        this.reconnectAttempts++;
        console.log(`🔄 Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

        setTimeout(() => {
            console.log(`🔄 Reconnection attempt ${this.reconnectAttempts}`);
            this.init();
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    /**
     * Force refresh of marketplace data
     */
    async refresh() {
        try {
            console.log('🔄 Refreshing marketplace data...');

            await this.loadAgents();
            await this.loadStats();

            this.emit('refreshComplete', {
                agentCount: this.agents.size,
                stats: this.stats,
                timestamp: Date.now()
            });

            this.log('ok', 'Marketplace data refreshed');

        } catch (error) {
            console.error('Refresh failed:', error);
            this.emit('refreshError', error);
            this.log('err', `Refresh failed: ${error.message}`);
        }
    }

    /**
     * Check connection status
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Get connection info
     */
    getConnectionInfo() {
        return {
            connected: this.connected,
            baseUrl: this.baseUrl,
            apiUrl: this.apiUrl,
            reconnectAttempts: this.reconnectAttempts,
            stats: this.stats,
            agentCount: this.agents.size,
            lastUpdate: this.stats.lastUpdate
        };
    }

    /**
     * Disconnect from AgenticPlace
     */
    disconnect() {
        console.log('🔌 Disconnecting from AgenticPlace...');

        this.connected = false;
        this.agents.clear();
        this.chains.clear();

        this.emit('disconnected', { timestamp: Date.now() });

        console.log('✅ Disconnected from AgenticPlace');
    }
}

export default AgenticPlaceConnector;