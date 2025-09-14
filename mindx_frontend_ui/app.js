document.addEventListener('DOMContentLoaded', () => {
    const backendPort = window.MINDX_BACKEND_PORT || '8000';
    const apiUrl = `http://localhost:${backendPort}`;
    const statusLight = document.getElementById('status-light');
    const evolveBtn = document.getElementById('evolve-btn');
    const queryBtn = document.getElementById('query-btn');
    const evolveDirectiveInput = document.getElementById('evolve-directive');
    const queryInput = document.getElementById('query-input');
    const responseOutput = document.getElementById('response-output');

    async function checkBackendStatus() {
        try {
            const response = await fetch(`${apiUrl}/`);
            if (response.ok) {
                statusLight.className = 'status-light-green';
                statusLight.title = 'Connected';
            } else {
                throw new Error('Backend not ready');
            }
        } catch (error) {
            statusLight.className = 'status-light-red';
            statusLight.title = `Disconnected: ${error.message}`;
        }
    }

    async function sendRequest(endpoint, method, body) {
        responseOutput.textContent = 'Sending request...';
        try {
            const response = await fetch(`${apiUrl}${endpoint}`, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const result = await response.json();
            responseOutput.textContent = JSON.stringify(result, null, 2);
        } catch (error) {
            responseOutput.textContent = `Error: ${error.message}`;
        }
    }

    evolveBtn.addEventListener('click', () => {
        const directive = evolveDirectiveInput.value.trim();
        if (directive) {
            sendRequest('/commands/evolve', 'POST', { directive });
        } else {
            responseOutput.textContent = 'Please enter a directive.';
        }
    });

    queryBtn.addEventListener('click', () => {
        const query = queryInput.value.trim();
        if (query) {
            sendRequest('/coordinator/query', 'POST', { query });
        } else {
            responseOutput.textContent = 'Please enter a query.';
        }
    });

    checkBackendStatus();
    setInterval(checkBackendStatus, 10000); // Check status every 10 seconds
});
