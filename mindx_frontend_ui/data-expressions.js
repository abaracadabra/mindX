/**
 * mindX Data Expressions System
 * 
 * Modular data fetching and expression system for all tabs.
 * Each tab can define its data requirements declaratively.
 * 
 * @module DataExpressions
 */

class DataExpressions {
    constructor() {
        this.expressions = new Map();
        this.cache = new Map();
        this.cacheTimeout = 5000; // 5 seconds default cache
        this.baseURL = window.location.origin.replace(':3000', ':8000');
        
        console.log('📊 DataExpressions initialized');
    }

    /**
     * Register a data expression for a tab
     * @param {string} tabId - Tab ID
     * @param {Object} expression - Data expression configuration
     */
    registerExpression(tabId, expression) {
        const exprConfig = {
            tabId,
            endpoints: expression.endpoints || [],
            transform: expression.transform || ((data) => data),
            cache: expression.cache !== undefined ? expression.cache : true,
            refreshInterval: expression.refreshInterval || null,
            onUpdate: expression.onUpdate || null,
            ...expression
        };

        this.expressions.set(tabId, exprConfig);
        console.log(`✅ Data expression registered for tab: ${tabId}`);
    }

    /**
     * Execute data expression for a tab
     * @param {string} tabId - Tab ID
     * @returns {Promise<Object>} Resolved data
     */
    async executeExpression(tabId) {
        const expression = this.expressions.get(tabId);
        if (!expression) {
            console.warn(`⚠️ No expression found for tab: ${tabId}`);
            return null;
        }

        // Check cache
        if (expression.cache) {
            const cached = this.cache.get(tabId);
            if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
                console.log(`📦 Using cached data for ${tabId}`);
                return cached.data;
            }
        }

        try {
            // Fetch data from all endpoints
            const promises = expression.endpoints.map(endpoint => 
                this.fetchData(endpoint.url, endpoint.method || 'GET', endpoint.body)
            );

            const results = await Promise.all(promises);
            
            // Combine results
            const combinedData = {};
            expression.endpoints.forEach((endpoint, index) => {
                const key = endpoint.key || `data_${index}`;
                combinedData[key] = results[index];
            });

            // Transform data
            const transformedData = expression.transform(combinedData);

            // Cache if enabled
            if (expression.cache) {
                this.cache.set(tabId, {
                    data: transformedData,
                    timestamp: Date.now()
                });
            }

            // Call update callback
            if (expression.onUpdate) {
                expression.onUpdate(transformedData);
            }

            return transformedData;
        } catch (error) {
            console.error(`❌ Error executing expression for ${tabId}:`, error);
            throw error;
        }
    }

    /**
     * Fetch data from API
     * @param {string} endpoint - API endpoint
     * @param {string} method - HTTP method
     * @param {Object} body - Request body
     * @returns {Promise<Object>} Response data
     */
    async fetchData(endpoint, method = 'GET', body = null) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
        
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Clear cache for a tab
     * @param {string} tabId - Tab ID
     */
    clearCache(tabId) {
        this.cache.delete(tabId);
        console.log(`🗑️ Cache cleared for ${tabId}`);
    }

    /**
     * Clear all cache
     */
    clearAllCache() {
        this.cache.clear();
        console.log('🗑️ All cache cleared');
    }
}

// Create global instance
window.dataExpressions = new DataExpressions();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataExpressions;
}
