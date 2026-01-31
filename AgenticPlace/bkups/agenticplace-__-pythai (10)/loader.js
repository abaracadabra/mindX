
// This script loads environment variables from a .env file
// before starting the main application. It acts as a lightweight 
// browser-side equivalent to the 'dotenv' package.

const root = document.getElementById('root');

const renderError = (title, message) => {
    root.innerHTML = `
        <div style="
            font-family: 'Inter', sans-serif;
            color: #ff3333;
            background-color: #1a0000;
            border: 1px solid #ff3333;
            border-radius: 8px;
            padding: 2rem;
            margin: 2rem;
            text-align: left;
            max-width: 600px;
            line-height: 1.6;
        ">
            <h2 style="margin-top: 0; border-bottom: 1px solid #330000; padding-bottom: 0.5rem;">${title}</h2>
            <p>${message}</p>
            <p>Please create or update your <code>.env</code> file in the project root:</p>
            <pre style="
                background-color: #111;
                padding: 1rem;
                border-radius: 4px;
                white-space: pre-wrap;
                word-wrap: break-word;
                color: #00ff00;
                border: 1px solid #222;
            ">API_KEY=YOUR_GEMINI_API_KEY_HERE</pre>
            <p style="font-size: 0.85rem; color: #888;">
                You can obtain a key from the <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: #4444ff;">Google AI Studio</a>.
            </p>
        </div>
    `;
};

async function loadEnvAndStartApp() {
    try {
        // Attempt to fetch the .env file
        const response = await fetch('/.env');
        const env = { ...window.process?.env };

        if (response.ok) {
            const text = await response.text();
            // Parse the .env content (handling Unix/Windows line endings)
            text.split(/\r?\n/).forEach(line => {
                const trimmedLine = line.trim();
                // Skip empty lines and comments
                if (trimmedLine && !trimmedLine.startsWith('#')) {
                    const firstEqual = trimmedLine.indexOf('=');
                    if (firstEqual !== -1) {
                        const key = trimmedLine.substring(0, firstEqual).trim();
                        let value = trimmedLine.substring(firstEqual + 1).trim();
                        
                        // Handle quoted values (single or double quotes)
                        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
                            value = value.substring(1, value.length - 1);
                        }
                        
                        if (key) {
                            env[key] = value;
                        }
                    }
                }
            });
        } else {
            console.warn('.env file not found or inaccessible. Relying on pre-configured environment.');
        }
        
        // Polyfill process.env for the browser environment
        window.process = {
            ...window.process,
            env: env,
        };

        // Validate essential connector: API_KEY
        const apiKey = window.process.env.API_KEY;
        if (!apiKey || apiKey === 'YOUR_GEMINI_API_KEY_HERE') {
            renderError(
                'Critical Configuration Missing',
                'The <code>API_KEY</code> is required for PYTHAI to establish a cognitive link with the Gemini neural substrate.'
            );
            return;
        }

        // Successfully loaded environment; proceed to main application
        await import('./index.tsx');

    } catch (error) {
        console.error('Fatal Initialization Error:', error);
        renderError(
             'System Load Failure',
            `The terminal could not be initialized due to a configuration error: ${error.message}`
        );
    }
}

// Kickstart the environment loading process
loadEnvAndStartApp();
