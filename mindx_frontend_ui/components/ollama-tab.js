/**
 * Ollama Tab Component
 * Dedicated menu tab for Ollama connection, diagnostics, and interaction testing.
 * Reuses OllamaAdminTab and app.js init/model loading; orchestration lives here.
 */
(function () {
    'use strict';

    function onActivate() {
        if (typeof window.initializeOllamaAdminTab === 'function') {
            window.initializeOllamaAdminTab();
        }
        if (typeof window.loadOllamaAdminModels === 'function') {
            window.loadOllamaAdminModels().catch(function () {});
        }
        if (window.AdminTab && typeof window.AdminTab.loadAdminOllamaMetrics === 'function') {
            window.AdminTab.loadAdminOllamaMetrics().catch(function () {});
        }
    }

    window.OllamaTab = {
        onActivate: onActivate
    };
})();
