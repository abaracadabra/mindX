document.addEventListener('DOMContentLoaded', () => {
    // --- Element References ---
    const commandSelect = document.getElementById('commandSelect');
    const mindXDirectiveInput = document.getElementById('mindXDirectiveInput');
    const runCommandButton = document.getElementById('runCommandButton');
    const mindXStatus = document.getElementById('mindXStatus');
    const mindXResponseOutput = document.getElementById('mindXResponseOutput');
    const terminalLogOutput = document.getElementById('terminalLogOutput');

    // Determine backend URL - dynamically set by build script
    const backendBaseUrl = "http://localhost:8000";

    console.log(`Frontend configured to use backend at: ${backendBaseUrl}`);

    // --- Event Listener for Evolve Button ---
    runCommandButton.addEventListener('click', handleRunCommand);
    mindXDirectiveInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default form submission if inside a form
            handleRunCommand(); // Trigger evolve function on Enter key
        }
    });

    // --- Terminal Log Fetching ---
    async function fetchTerminalLogs() {
        try {
            const response = await fetch(`${backendBaseUrl}/logs/runtime`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const logs = await response.text();
            terminalLogOutput.textContent = logs;
        } catch (error) {
            terminalLogOutput.textContent = `Error fetching logs: ${error.message}`;
        }
    }

    // --- Main Command Handler ---
    async function handleRunCommand() {
        const command = commandSelect.value;
        const directive = mindXDirectiveInput.value.trim();
        
        if (!directive && !['mastermind_status', 'show_agent_registry', 'show_tool_registry', 'id_list', 'coord_backlog'].includes(command)) {
            mindXStatus.textContent = 'Please enter a directive for this command.';
            mindXStatus.className = 'status-message error';
            return;
        }

        mindXStatus.textContent = 'Processing...';
        mindXStatus.className = 'status-message loading';
        mindXResponseOutput.textContent = 'Sending request...';

        try {
            let result;
            
            switch (command) {
                case 'evolve':
                    result = await sendRequest('/commands/evolve', 'POST', { directive });
                    break;
                case 'deploy':
                    result = await sendRequest('/commands/deploy', 'POST', { directive });
                    break;
                case 'introspect':
                    result = await sendRequest('/commands/introspect', 'POST', { directive });
                    break;
                case 'mastermind_status':
                    result = await sendRequest('/status/mastermind', 'GET');
                    break;
                case 'show_agent_registry':
                    result = await sendRequest('/registry/agents', 'GET');
                    break;
                case 'show_tool_registry':
                    result = await sendRequest('/registry/tools', 'GET');
                    break;
                case 'analyze_codebase':
                    const [path, focus] = directive.split(' ', 2);
                    result = await sendRequest('/commands/analyze_codebase', 'POST', { 
                        path: path || '.', 
                        focus: focus || 'General analysis' 
                    });
                    break;
                case 'basegen':
                    result = await sendRequest('/commands/basegen', 'POST', { directive });
                    break;
                case 'id_list':
                    result = await sendRequest('/identities', 'GET');
                    break;
                case 'id_create':
                    result = await sendRequest('/identities', 'POST', { entity_id: directive });
                    break;
                case 'id_deprecate':
                    result = await sendRequest('/identities', 'DELETE', { public_address: directive });
                    break;
                case 'audit_gemini':
                    result = await sendRequest('/commands/audit_gemini', 'POST', { 
                        test_all: true, 
                        update_config: false 
                    });
                    break;
                case 'coord_query':
                    result = await sendRequest('/coordinator/query', 'POST', { query: directive });
                    break;
                case 'coord_analyze':
                    result = await sendRequest('/coordinator/analyze', 'POST', { context: directive });
                    break;
                case 'coord_improve':
                    const [componentId, context] = directive.split(' ', 2);
                    result = await sendRequest('/coordinator/improve', 'POST', { 
                        component_id: componentId || directive, 
                        context: context || 'General improvement' 
                    });
                    break;
                case 'coord_backlog':
                    result = await sendRequest('/coordinator/backlog', 'GET');
                    break;
                case 'coord_process_backlog':
                    result = await sendRequest('/coordinator/process_backlog', 'POST', {});
                    break;
                case 'coord_approve':
                    result = await sendRequest('/coordinator/approve', 'POST', { backlog_item_id: directive });
                    break;
                case 'coord_reject':
                    result = await sendRequest('/coordinator/reject', 'POST', { backlog_item_id: directive });
                    break;
                case 'agent_create':
                    const [agentType, agentId, ...configParts] = directive.split(' ');
                    result = await sendRequest('/agents', 'POST', { 
                        agent_type: agentType || 'generic',
                        agent_id: agentId || 'new_agent',
                        config: { description: configParts.join(' ') || 'Generic agent' }
                    });
                    break;
                case 'agent_delete':
                    result = await sendRequest('/agents', 'DELETE', { agent_id: directive });
                    break;
                case 'agent_list':
                    result = await sendRequest('/agents', 'GET');
                    break;
                case 'agent_evolve':
                    const [agentIdEvolve, agentDirective] = directive.split(' ', 2);
                    result = await sendRequest('/commands/agent_evolve', 'POST', { 
                        agent_id: agentIdEvolve || directive,
                        directive: agentDirective || 'General evolution'
                    });
                    break;
                case 'agent_sign':
                    const [agentIdSign, message] = directive.split(' ', 2);
                    result = await sendRequest('/commands/agent_sign', 'POST', { 
                        agent_id: agentIdSign || directive,
                        message: message || 'Default message'
                    });
                    break;
                default:
                    throw new Error(`Unknown command: ${command}`);
            }

            mindXResponseOutput.textContent = JSON.stringify(result, null, 2);
            mindXStatus.textContent = 'Command completed successfully!';
            mindXStatus.className = 'status-message success';
            
        } catch (error) {
            mindXResponseOutput.textContent = `Error: ${error.message}`;
            mindXStatus.textContent = `Command failed: ${error.message}`;
            mindXStatus.className = 'status-message error';
        }
    }

    // --- Generic Request Function ---
    async function sendRequest(endpoint, method, body) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (body && method !== 'GET') {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${backendBaseUrl}${endpoint}`, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        return await response.json();
    }

    // --- Auto-refresh logs every 5 seconds ---
    setInterval(fetchTerminalLogs, 5000);
    
    // --- Initial log fetch ---
    fetchTerminalLogs();
});