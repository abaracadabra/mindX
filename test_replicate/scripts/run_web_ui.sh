 #!/bin/bash

# install mindX v1.3.4 as mindX

# --- Configuration ---
# Get the directory where the script itself is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# Assume the script is in the project root directory (e.g., 'mindX')
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# --- Helper Functions ---
# Define log functions early so they can be used by config section
function log_info {
  echo "[INFO] $1"
}

function log_error {
  echo "[ERROR] $1" >&2
}

# --- Continue Configuration ---
log_info "Project Root detected as: $PROJECT_ROOT" # Add log for verification

MINDX_DIR="." # Relative to PROJECT_ROOT
FRONTEND_DIR="frontend" # Relative to PROJECT_ROOT

MINDX_VENV_NAME="mindx_venv" # Name for the mindX virtual environment

FRONTEND_PORT=3000
BACKEND_PORT=8000

# Absolute paths derived dynamically from PROJECT_ROOT and relative paths
ABS_MINDX_DIR="$PROJECT_ROOT/$MINDX_DIR"
ABS_FRONTEND_DIR="$PROJECT_ROOT/$FRONTEND_DIR"

# Log derived absolute paths for verification
log_info "Absolute mindX Dir: $ABS_MINDX_DIR"
log_info "Absolute Frontend Dir: $ABS_FRONTEND_DIR"


# --- Helper Functions (Continued) ---
function check_command {
  if ! command -v "$1" &> /dev/null; then
    log_error "$1 is not installed. Please install it before running this script."
    exit 1
  fi
}

# Function to create/overwrite files using printf (safer for complex content)
function create_or_overwrite_file_heredoc {
    local file="$1"
    # Use the second argument directly as the content
    local content="$2"
    local dir
    dir=$(dirname "$file")

    # Ensure the directory exists before trying to create the file
    # Use absolute path for mkdir based on PROJECT_ROOT if file path is relative
    local abs_dir
    if [[ "$dir" == /* ]]; then # Already absolute
        abs_dir="$dir"
    else # Relative path
        abs_dir="$PROJECT_ROOT/$dir"
    fi
    if ! mkdir -p "$abs_dir"; then
        log_error "Failed to create directory: $abs_dir"
        exit 1
    fi

    # Use absolute path for file creation as well
    local abs_file
     if [[ "$file" == /* ]]; then # Already absolute
        abs_file="$file"
    else # Relative path
        abs_file="$PROJECT_ROOT/$file"
    fi

    log_info "Creating/Overwriting file: $abs_file"
    # Use printf to output the content exactly as stored in the variable
    # This avoids shell interpretation issues within the content itself.
    # Add a newline by default unless content is empty
    if [ -n "$content" ]; then
        if ! printf '%s\n' "$content" > "$abs_file"; then
            log_error "Failed to write to file: $abs_file (using printf)"
            exit 1
        fi
    else
        # Handle empty content - create an empty file
        if ! > "$abs_file"; then
             log_error "Failed to create empty file: $abs_file"
             exit 1
        fi
    fi
}


function install_mindx_dependencies {
  log_info "Setting up mindX Python environment..."

  # Ensure mindX directory exists (though it should, as it contains the project)
  # Using absolute path for cd ensures consistency
  local abs_mindx_dir="$PROJECT_ROOT/$MINDX_DIR"
  if [ ! -d "$abs_mindx_dir" ]; then
    log_error "mindX project directory not found at: $abs_mindx_dir"
    log_error "Please ensure the 'mindX' project is correctly placed in the project root."
    return 1
  fi

  local current_dir
  current_dir=$(pwd)
  if ! cd "$abs_mindx_dir"; then
      log_error "Failed to cd to mindX directory: $abs_mindx_dir"
      return 1
  fi

  log_info "Currently in mindX directory: $(pwd)"

  # Check for requirements.txt
  if [ ! -f "requirements.txt" ]; then
    log_error "mindX requirements.txt not found in $abs_mindx_dir"
    log_error "Cannot install mindX dependencies."
    cd "$current_dir" || exit 1 # Attempt to return before failing
    return 1
  fi

  # Create virtual environment if it doesn't exist
  if [ ! -d "$MINDX_VENV_NAME" ]; then
    log_info "Creating mindX virtual environment '$MINDX_VENV_NAME' in $(pwd)..."
    if ! python3 -m venv "$MINDX_VENV_NAME"; then
        log_error "Failed to create mindX virtual environment in $(pwd)"
        cd "$current_dir" || exit 1
        return 1
    fi
    log_info "mindX virtual environment created."
    # Activate immediately for pip upgrade
    log_info "Activating mindX virtual environment for pip upgrade..."
    if ! source "$MINDX_VENV_NAME/bin/activate"; then
        log_error "Failed to activate mindX virtual environment in $(pwd) for pip upgrade"
        cd "$current_dir" || exit 1
        return 1
    fi
    log_info "Upgrading pip in mindX virtual environment..."
    if ! python -m pip install --upgrade pip -q; then
        log_error "Failed to upgrade pip in mindX venv."
        deactivate
        cd "$current_dir" || exit 1
        return 1
    fi
    # Deactivate after pip upgrade, will reactivate for installing requirements
    deactivate
    log_info "Deactivated mindX virtual environment after pip upgrade."
  fi

  # Activate virtual environment to install requirements
  log_info "Activating mindX virtual environment '$MINDX_VENV_NAME' to install dependencies..."
  if ! source "$MINDX_VENV_NAME/bin/activate"; then
      log_error "Failed to activate mindX virtual environment in $(pwd) for installing dependencies"
      cd "$current_dir" || exit 1
      return 1
  fi
  log_info "mindX virtual environment '$MINDX_VENV_NAME' activated."

  # Install requirements
  log_info "Installing mindX dependencies from requirements.txt..."
  if ! pip install -r "requirements.txt" -q; then
      log_error "Failed to install mindX dependencies from requirements.txt in $(pwd)."
      log_error "Check the mindX requirements.txt file, network connection, and previous logs."
      deactivate
      cd "$current_dir" || exit 1
      return 1
  fi
  log_info "mindX dependencies installed successfully."

  # Deactivate the virtual environment
  deactivate
  log_info "mindX virtual environment deactivated."

  # Return to the original directory
  if ! cd "$current_dir"; then
      log_error "Failed to cd back to original directory: $current_dir from mindX setup"
      exit 1 # This is problematic, exit the script
  fi
  log_info "mindX Python environment setup complete."
  return 0
}


function install_frontend_dependencies {
  log_info "Setting up frontend environment (files and dependencies)..."

  # Ensure frontend directory exists using absolute path
  mkdir -p "$ABS_FRONTEND_DIR"

  # --- index.html ---
  read -r -d '' index_html_content << 'EOF_HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mindX v1.3.4</title>
    <link rel="stylesheet" href="styled.css">
</head>
<body>
    <div class="container">
        <h1>mindX v1.3.4</h1>

        <!-- mindX Interaction Section -->
        <div class="mindx-interaction-area section-box">
            <h2>Interact with mindX (via Mastermind)</h2>
            <div class="input-group">
                <label for="commandSelect">Command:</label>
                <select id="commandSelect">
                    <option value="evolve">evolve</option>
                    <option value="deploy">deploy</option>
                    <option value="introspect">introspect</option>
                    <option value="mastermind_status">mastermind_status</option>
                    <option value="show_agent_registry">show_agent_registry</option>
                    <option value="show_tool_registry">show_tool_registry</option>
                    <option value="analyze_codebase">analyze_codebase</option>
                    <option value="basegen">basegen</option>
                    <option value="id_list">id_list</option>
                    <option value="id_create">id_create</option>
                    <option value="id_deprecate">id_deprecate</option>
                    <option value="audit_gemini">audit_gemini</option>
                    <option value="coord_query">coord_query</option>
                    <option value="coord_analyze">coord_analyze</option>
                    <option value="coord_improve">coord_improve</option>
                    <option value="coord_backlog">coord_backlog</option>
                    <option value="coord_process_backlog">coord_process_backlog</option>
                    <option value="coord_approve">coord_approve</option>
                    <option value="coord_reject">coord_reject</option>
                    <option value="agent_create">agent_create</option>
                    <option value="agent_delete">agent_delete</option>
                    <option value="agent_list">agent_list</option>
                    <option value="agent_evolve">agent_evolve</option>
                    <option value="agent_sign">agent_sign</option>
                </select>
            </div>
            <div class="input-group">
                <label for="mindXDirectiveInput">Directive for mindX:</label>
                <textarea id="mindXDirectiveInput" rows="3" placeholder="Enter a high-level directive for mindX evolution..."></textarea>
            </div>
            <button id="runCommandButton">Run Command</button>
            <p id="mindXStatus" class="status-message"></p>
            <div class="output-area">
                <h3>mindX Response:</h3>
                <pre id="mindXResponseOutput" class="output-content">Awaiting directive...</pre>
            </div>
        </div>

        <!-- Terminal Log Viewer -->
        <div class="terminal-log-viewer section-box">
            <h2>mindX Terminal Logs</h2>
            <div class="output-area">
                <pre id="terminalLogOutput" class="output-content">Loading logs...</pre>
            </div>
        </div>

    </div>
    <!-- Link JS at the end of body -->
    <script src="dapp.js"></script>
</body>
</html>
EOF_HTML
  create_or_overwrite_file_heredoc "$FRONTEND_DIR/index.html" "$index_html_content"

  # --- dapp.js ---
  read -r -d '' dapp_js_content << 'EOF_JS'
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
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            terminalLogOutput.textContent = data.logs.join('\n');
        } catch (error) {
            console.error('Error fetching terminal logs:', error);
            terminalLogOutput.textContent = `Error loading logs: ${error.message}`;
        }
    }

    // --- Initial Log Fetch and Periodic Refresh ---
    fetchTerminalLogs(); // Initial fetch
    setInterval(fetchTerminalLogs, 5000); // Refresh every 5 seconds

    async function handleRunCommand() {
        const command = commandSelect.value;
        const directive = mindXDirectiveInput.value.trim();
        if (!directive) {
            alert('Please enter a directive.');
            return;
        }

        mindXResponseOutput.textContent = 'Thinking...';
        mindXResponseOutput.className = 'output-content loading'; // Reset classes
        mindXStatus.textContent = ''; // Clear other messages

        try {
            const response = await fetch(`${backendBaseUrl}/commands/${command}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json', // Be explicit about expected response type
                },
                body: JSON.stringify({ directive: directive }),
            });

            // Always try to parse JSON, even for errors, as FastAPI often returns JSON errors
            const data = await response.json();

            if (!response.ok) {
                // Use detail from JSON if available, otherwise construct error message
                const errorDetail = data.detail || `HTTP error! Status: ${response.status} ${response.statusText}`;
                throw new Error(errorDetail);
            }

            mindXResponseOutput.textContent = JSON.stringify(data, null, 2);
            mindXResponseOutput.classList.remove('loading');
            // mindXResponseOutput.classList.add('success'); // Optional: style success

        } catch (error) {
            console.error('Error fetching answer:', error);
            mindXResponseOutput.textContent = `Error: ${error.message}`;
            mindXResponseOutput.className = 'output-content error'; // Set error class
        }
    }
});
EOF_JS
  create_or_overwrite_file_heredoc "$FRONTEND_DIR/dapp.js" "$dapp_js_content"

  # --- styled.css ---
  read -r -d '' styled_css_content << 'EOF_CSS'
/* General Styles */
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f8f9fa;
    color: #212529;
    line-height: 1.6;
}

.container {
    max-width: 800px;
    margin: 20px auto;
    background-color: #ffffff;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    border: 1px solid #dee2e6;
}

h1, h2, h3 {
    color: #007bff; /* Primary color */
    margin-top: 0;
    margin-bottom: 15px;
    text-align: center;
}

h1 {
    font-size: 2em;
    margin-bottom: 25px;
}

h2 {
    font-size: 1.5em;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
    margin-bottom: 20px;
}

h3 {
    font-size: 1.2em;
    color: #17a2b8; /* Info color */
    margin-bottom: 10px;
}

/* Section Styling */
.section-box {
    margin-bottom: 30px;
    padding: 20px;
    border: 1px solid #e9ecef;
    border-radius: 5px;
    background-color: #fdfdff; /* Slightly off-white */
}

/* Input Group Styling */
.input-group {
    margin-bottom: 15px;
    display: flex;
    flex-wrap: wrap; /* Allow wrapping on small screens */
    gap: 10px;
    align-items: center;
}

.input-group label {
    flex-basis: 100px; /* Fixed base width for labels */
    flex-shrink: 0;
    font-weight: bold;
    color: #495057;
}

.input-group input[type="text"],
.input-group select,
.input-group textarea {
    flex-grow: 1; /* Allow input to take remaining space */
    padding: 10px 12px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 1rem;
    box-sizing: border-box; /* Include padding in width */
    min-width: 150px; /* Prevent inputs from becoming too small */
}

/* Button Styling */
button {
    padding: 10px 20px;
    cursor: pointer;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 500;
    transition: background-color 0.2s ease, transform 0.1s ease;
    display: block; /* Make button block level for centering or full width */
    margin: 10px auto 0; /* Center button */
}

button:hover {
    background-color: #0056b3;
}

button:active {
    transform: scale(0.98); /* Slight press effect */
}

/* Status and Output Styling */
.status-message {
    margin-top: 15px;
    padding: 10px;
    border-radius: 4px;
    font-weight: 500;
    text-align: center;
    min-height: 1.5em; /* Prevent layout shift when empty */
    transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.status-message:empty {
    padding: 0; /* Collapse padding when empty */
    border: none;
    background-color: transparent;
}


.status-message.loading {
    color: #0056b3;
    background-color: #e7f3ff;
    border: 1px solid #b3d7ff;
}

.status-message.success {
    color: #155724;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
}

.status-message.error {
    color: #721c24;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
}

.output-area {
    margin-top: 20px;
}

.output-content {
    font-size: 1rem;
    padding: 15px;
    border: 1px solid #eee;
    border-radius: 4px;
    background-color: #fefefe;
    min-height: 50px; /* Ensure it has some height even when empty */
    white-space: pre-wrap; /* Preserve whitespace and line breaks */
    word-wrap: break-word; /* Break long words */
    transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease; /* Smooth transitions */
}

.output-content.loading {
    opacity: 0.7;
    font-style: italic;
    background-color: #f8f9fa;
}

/* No specific success style needed unless different from default */
/* .output-content.success { */
/*      border-color: #c3e6cb; */
/* } */


.output-content.error {
    color: #721c24;
    border-color: #f5c6cb; /* Match error message border */
    background-color: #f8d7da; /* Match error message background */
}

/* Responsive Adjustments */
@media (max-width: 600px) {
    .container {
        padding: 20px;
    }
    .input-group {
        flex-direction: column;
        align-items: stretch;
    }
    .input-group label {
        flex-basis: auto; /* Reset basis */
        margin-bottom: 5px; /* Add space below label */
    }
    button {
        width: 100%; /* Make buttons full width on small screens */
        margin-left: 0;
        margin-right: 0;
    }
}
EOF_CSS
  create_or_overwrite_file_heredoc "$FRONTEND_DIR/styled.css" "$styled_css_content"

  # --- server.js ---
  read -r -d '' server_js_content << 'EOF_NODE'
const express = require('express');
const path = require('path');
const app = express();

// Use environment variable for port or default to 3000
// Use the FRONTEND_PORT environment variable if set by the run script, otherwise default
const port = process.env.FRONTEND_PORT || 3000;

// Serve static files from the directory this script is in ('./frontend')
app.use(express.static(__dirname));

// Log requests for debugging (optional)
app.use((req, res, next) => {
  // Avoid logging requests for static assets if too noisy
  if (!req.path.includes('.')) {
     console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  }
  next();
});


// Proxy endpoint for backend calls (Example - if CORS is an issue or you want to hide backend URL)
// This requires installing 'http-proxy-middleware': npm install http-proxy-middleware
/*
const { createProxyMiddleware } = require('http-proxy-middleware');
// Use BACKEND_PORT env var if set, otherwise default
const backendPort = process.env.BACKEND_PORT || 8000;
const backendUrl = `http://localhost:${backendPort}`;
app.use('/ask', createProxyMiddleware({ target: backendUrl, changeOrigin: true }));
app.use('/create_agent', createProxyMiddleware({ target: backendUrl, changeOrigin: true }));
console.log(`Proxying API requests to: ${backendUrl}`);
*/
// If not using proxy, ensure backend CORS allows frontend origin.


// Fallback for SPA: always serve index.html for any GET request not matching static files
app.get('*', (req, res) => {
  // Check if the request accepts HTML, avoids serving HTML for API-like calls
  if (req.accepts('html')) {
    res.sendFile(path.resolve(__dirname, 'index.html'), (err) => {
      if (err) {
        console.error("Error sending index.html:", err);
        // Avoid sending status if headers already sent
        if (!res.headersSent) {
            res.status(err.status || 500).end();
        }
      }
    });
  } else {
    // Handle non-HTML requests if needed, or just send 404
     if (!res.headersSent) {
        res.status(404).send('Resource not found');
     }
  }
});


app.listen(port, () => {
  console.log(`Frontend server listening at http://localhost:${port}`);
  console.log(`Serving static files from: ${__dirname}`);
});

// Basic error handling for server start
app.on('error', (error) => {
  if (error.syscall !== 'listen') {
    throw error;
  }
  // Handle specific listen errors with friendly messages
  switch (error.code) {
    case 'EACCES':
      console.error(`Port ${port} requires elevated privileges`);
      process.exit(1);
      break;
    case 'EADDRINUSE':
      console.error(`Port ${port} is already in use. Check if another process is running.`);
      process.exit(1);
      break;
    default:
      console.error(`Server error: ${error}`);
      throw error; // Re-throw other errors
  }
});
EOF_NODE
  create_or_overwrite_file_heredoc "$FRONTEND_DIR/server.js" "$server_js_content"

  # --- package.json ---
  read -r -d '' package_json_content << 'EOF_JSON'
{
  "name": "mindx-frontend",
  "version": "1.0.0",
  "description": "Frontend for mindX",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "dependencies": {
    "express": "^4.17.1"
  },
  "devDependencies": {},
  "author": "mindX",
  "license": "ISC"
}
EOF_JSON
  create_or_overwrite_file_heredoc "$FRONTEND_DIR/package.json" "$package_json_content"

  log_info "Frontend files created in $FRONTEND_DIR (relative to $PROJECT_ROOT)." # Adjusted log

  log_info "Installing frontend dependencies (npm)..."
  # Store current dir
  local current_dir
  current_dir=$(pwd)
  # Change to the ABSOLUTE frontend directory
  if ! cd "$ABS_FRONTEND_DIR"; then
      log_error "Failed to cd to frontend directory: $ABS_FRONTEND_DIR"
      return 1 # Use return, not exit
  fi

  if [ -f "package.json" ]; then
    log_info "Running 'npm install' in $(pwd)..."
    # Use npm ci for faster, more reliable installs if package-lock.json exists
    if [ -f "package-lock.json" ]; then
        # Add --silent to reduce verbose output, remove if debugging needed
        if ! npm ci --silent; then
            log_error "Failed to install frontend dependencies using 'npm ci'. Trying 'npm install'..."
            # Fallback to npm install if npm ci fails
            if ! npm install --silent; then
                 log_error "Failed to install frontend dependencies using 'npm install' in $(pwd)."
                 cd "$current_dir" || exit 1 # Return or exit
                 return 1
            fi
        fi
    else
        if ! npm install --silent; then
            log_error "Failed to install frontend dependencies using 'npm install' in $(pwd)."
            cd "$current_dir" || exit 1 # Return or exit
            return 1
        fi
    fi
    log_info "Frontend dependencies installed successfully."
  else
    log_info "WARNING: No 'package.json' found in $(pwd). Skipping frontend dependency installation."
  fi

  # Return to original directory
  if ! cd "$current_dir"; then
      log_error "Failed to cd back to original directory: $current_dir"
      exit 1 # Exit here is problematic
  fi
  # Indicate success
  return 0
}


function run_backend {
  log_info "Starting mindX backend (FastAPI) on http://localhost:$BACKEND_PORT..."
  # Store current directory to return to it
  local current_dir
  current_dir=$(pwd)
  # Use explicit absolute path for cd to ensure consistency
  if ! cd "$ABS_MINDX_DIR"; then
      log_error "Failed to cd to mindX directory '$ABS_MINDX_DIR' to start server."
      return 1 # Cannot start server if not in the correct directory
  fi

  log_info "Activating mindX virtual environment '$MINDX_VENV_NAME'..."
  if [ ! -f "$MINDX_VENV_NAME/bin/activate" ]; then
      log_error "Virtual environment activate script not found: $MINDX_VENV_NAME/bin/activate"
      cd "$current_dir" || exit 1
      return 1
  fi
  # Source the activate script into the current shell
  # Use '.' as a shorter alias for 'source'
  if ! . "$MINDX_VENV_NAME/bin/activate"; then
    log_error "Failed to activate virtual environment '$MINDX_VENV_NAME/bin/activate' before running backend."
    cd "$current_dir" || exit 1 # Attempt to return to original directory before failing
    return 1
  fi

  log_info "Starting uvicorn server in the background..."
  # Ensure uvicorn is runnable (should be if install succeeded)
  # Pass FRONTEND_PORT as env var so backend CORS can use it
  export FRONTEND_PORT # Make shell variable available to subprocess
  # Redirect uvicorn output to a log file for easier debugging
  local backend_log_file="logs/backend_run.log"
  log_info "Redirecting backend stdout/stderr to $backend_log_file"

  # --- Ensure log directory exists ---
  mkdir -p "$(dirname "$backend_log_file")" || { log_error "Failed to create log directory $(pwd)/logs"; deactivate &> /dev/null; cd "$current_dir" || exit 1; return 1; }
  # -----------------------------------

  # Use --log-level info for uvicorn logging
  # Ensure the main:app module can be found (relative to MINDX_DIR)
  # Check if watchfiles is needed/installed for --reload with older uvicorn
  # If reload fails, remove --reload or install watchfiles==<compatible_version>
  uvicorn api.api_server:app --host 0.0.0.0 --port "$BACKEND_PORT" --log-level info
  BACKEND_PID=$!
  log_info "Backend process started with PID: $BACKEND_PID"

  # Deactivate environment after starting the background process
  deactivate
  log_info "Virtual environment deactivated (backend process continues)."

  # Return to the original directory
  if ! cd "$current_dir"; then
      log_error "Failed to return to original directory '$current_dir' after starting backend."
      # Don't exit here, backend might be running, but the script state is inconsistent
      return 1 # Indicate potential issue
  fi
  return 0 # Success
}

function run_frontend {
  log_info "Starting mindX frontend (Node.js) server on http://localhost:$FRONTEND_PORT..."
  # Store current directory
  local current_dir
  current_dir=$(pwd)
  # Use explicit absolute path for cd
  if ! cd "$ABS_FRONTEND_DIR"; then
      log_error "Failed to cd to frontend directory '$ABS_FRONTEND_DIR' to start server."
      return 1 # Cannot start if not in correct directory
  fi

  log_info "Starting Node.js server (server.js) in the background..."
  # Check if server.js exists in the CURRENT directory (which is now $ABS_FRONTEND_DIR)
  if [ ! -f "server.js" ]; then
      log_error "Frontend server file 'server.js' not found in $(pwd)." # pwd is now $ABS_FRONTEND_DIR
      cd "$current_dir" || exit 1
      return 1
  fi

  # Pass relevant ports as environment variables to the Node process
  export FRONTEND_PORT
  export BACKEND_PORT
  # Redirect node output to a log file
  # Place log in the project root directory for easier access
  # Use PROJECT_ROOT which was determined at the start
  local frontend_log_file="$PROJECT_ROOT/frontend_run.log"
  log_info "Redirecting frontend stdout/stderr to $frontend_log_file"
  node "server.js" > "$frontend_log_file" 2>&1 &
  FRONTEND_PID=$!
  log_info "Frontend process started with PID: $FRONTEND_PID"

  # Basic check if process started
  sleep 2
  if ! ps -p $FRONTEND_PID > /dev/null; then
      log_error "Frontend process (PID: $FRONTEND_PID) failed to start or exited quickly."
      log_error "Check logs in $frontend_log_file for details."
      cd "$current_dir" || exit 1
      return 1
  fi

  # Return to the original directory
  if ! cd "$current_dir"; then
      log_error "Failed to return to original directory '$current_dir' after starting frontend."
      # Log and indicate potential issue
      return 1
  fi
  return 0 # Success
}


# --- Cleanup Function ---
BACKEND_PID="" # Initialize PID variables globally
FRONTEND_PID=""

function stop_processes {
  log_info "Initiating shutdown..."
  if [ -n "$BACKEND_PID" ]; then
    # Check if the process actually exists before trying to kill
    if ps -p "$BACKEND_PID" > /dev/null; then
        log_info "Stopping backend process (PID: $BACKEND_PID)..."
        # Try graceful termination first (SIGTERM), then force kill (SIGKILL)
        kill "$BACKEND_PID" 2>/dev/null
        sleep 2 # Give it time to shut down
        if ps -p "$BACKEND_PID" > /dev/null; then
            log_info "Backend process $BACKEND_PID did not stop gracefully, forcing kill..."
            kill -9 "$BACKEND_PID" 2>/dev/null
        else
            log_info "Backend process $BACKEND_PID stopped."
        fi
    else
        log_info "Backend process $BACKEND_PID already stopped."
    fi
    BACKEND_PID="" # Clear PID after attempting to stop
  else
      log_info "Backend PID not set, skipping kill."
  fi

  if [ -n "$FRONTEND_PID" ]; then
     if ps -p "$FRONTEND_PID" > /dev/null; then
        log_info "Stopping frontend process (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null
        sleep 1
         if ps -p "$FRONTEND_PID" > /dev/null; then
            log_info "Frontend process $FRONTEND_PID did not stop gracefully, forcing kill..."
            kill -9 "$FRONTEND_PID" 2>/dev/null
         else
            log_info "Frontend process $FRONTEND_PID stopped."
         fi
     else
        log_info "Frontend process $FRONTEND_PID already stopped."
     fi
     FRONTEND_PID="" # Clear PID
  else
      log_info "Frontend PID not set, skipping kill."
  fi
  log_info "Shutdown complete."
  # Exit the script cleanly after trap handler finishes
  exit 0
}

# --- Main Script ---

log_info "Starting mindX v1.3.4 deployment..."

# Set trap to call stop_processes on script exit signals
# EXIT signal ensures cleanup even on normal script termination or error exit
trap stop_processes SIGINT SIGTERM EXIT

# Check for required base commands
check_command python3
check_command pip # pip often comes with python3, but check is good
check_command node
check_command npm
# check_command uvicorn # Uvicorn will be installed in venv, check might fail globally

# Directory creation is handled within install functions now, ensuring atomicity

# Install mindX dependencies
install_mindx_dependencies || { log_error "mindX setup failed. Exiting."; exit 1; }

# Install frontend dependencies and create files
install_frontend_dependencies || { log_error "Frontend setup failed. Exiting."; exit 1; } # Exit if setup fails

# Clear PIDs before running
BACKEND_PID=""
FRONTEND_PID=""

# Run backend and frontend in the background
run_backend || { log_error "Failed to start backend server. Exiting."; exit 1; } # Exit if run fails
#run_frontend || { log_error "Failed to start frontend server. Exiting."; exit 1; } # Exit if run fails

log_info "--- mindX v1.3.4 Deployed Successfully ---"
log_info "Backend running on: http://localhost:$BACKEND_PORT (PID: $BACKEND_PID)"
log_info "Frontend running on: http://localhost:$FRONTEND_PORT (PID: $FRONTEND_PID)"
log_info "Backend logs: $ABS_MINDX_DIR/logs/backend_run.log"
log_info "Frontend logs: $PROJECT_ROOT/frontend_run.log" # Use PROJECT_ROOT for frontend log path
log_info "Press Ctrl+C to stop both servers."

# Keep the script running to manage background processes
# The trap will handle cleanup on exit.
# 'wait' waits for all background jobs started by this script.
# If any background job exits, wait returns. Use infinite loop if needed.
log_info "Script running in foreground, waiting for termination signal (Ctrl+C)..."
#wait

# This part is usually not reached if using 'wait' and Ctrl+C (trap handles exit),
# but might be reached if background processes exit on their own.
log_info "Script finished (wait command exited or background process terminated)."
