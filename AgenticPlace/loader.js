
// This script facilitates application startup. 
// As per GenAI guidelines, API key lifecycle and environment variables 
// are managed externally to the application code.

async function initializeSystem() {
    try {
        // Proceed to main application entry point
        await import('./index.tsx');
    } catch (error) {
        console.error('Fatal Initialization Error:', error);
        const root = document.getElementById('root');
        if (root) {
            root.innerHTML = `
                <div style="font-family: 'Inter', sans-serif; color: #ff3333; padding: 2rem; background: #1a0000; border: 1px solid #ff3333; border-radius: 8px; margin: 2rem;">
                    <h2 style="margin-top: 0;">System Load Failure</h2>
                    <p>The neural orchestrator could not be initialized: ${error.message}</p>
                </div>
            `;
        }
    }
}

// Start initialization
initializeSystem();
