#!/bin/bash

# AGENTIC_MINDX_DEPLOY_V2.0.0
# Production-focused setup and (conceptual) service preparation for MindX.
# This script aims to be robust and configurable for deploying the MindX system.

# set -u # Treat unset variables as an error (can be too strict).

# --- Script Version & Defaults ---
SCRIPT_VERSION="2.0.0"
DEFAULT_PROJECT_ROOT_NAME="augmentic_mindx" # Used if deploying into a new dir
DEFAULT_VENV_NAME=".mindx_env" # Changed for clarity
DEFAULT_FRONTEND_PORT="3000"
DEFAULT_BACKEND_PORT="8000"
DEFAULT_LOG_LEVEL="INFO" # For MindX application

# --- Logging ---
# Script's own log file
SETUP_LOG_FILE="" # Will be set after PROJECT_ROOT is confirmed

function log_setup_info {
    local message="[INFO] $1"
    echo "$message"
    if [ -n "$SETUP_LOG_FILE" ]; then
        echo "[SETUP INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$SETUP_LOG_FILE"
    fi
}
function log_setup_warn {
    local message="[WARN] $1"
    echo "$message"
    if [ -n "$SETUP_LOG_FILE" ]; then
        echo "[SETUP WARN] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$SETUP_LOG_FILE"
    fi
}
function log_setup_error {
    local message="[ERROR] $1"
    echo "$message" >&2
    if [ -n "$SETUP_LOG_FILE" ]; then
        echo "[SETUP ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$SETUP_LOG_FILE"
    fi
}

# --- Initial Configuration & Argument Parsing ---
# This script can be run from anywhere. It will create/use PROJECT_ROOT.
# If PROJECT_ROOT is not specified, it defaults to a subdirectory in current dir or a specified path.

TARGET_INSTALL_DIR_ARG="" # Path where augmentic_mindx project will reside or be created
MINDX_CONFIG_FILE_ARG="" # Optional path to a pre-existing mindx_config.json
DOTENV_FILE_ARG=""      # Optional path to a pre-existing .env file
RUN_SERVICES_FLAG=false
INTERACTIVE_SETUP_FLAG=false
REPLICATE_SOURCE_FLAG=false
FRONTEND_FLAG=false

function show_help { # pragma: no cover
    echo "MindX Deployment Script v${SCRIPT_VERSION}"
    echo "Usage: $0 [options] <target_install_directory>"
    echo ""
    echo "Arguments:"
    echo "  [target_install_directory]   Optional. The root directory where the '${DEFAULT_PROJECT_ROOT_NAME}' project will be located or created."
    echo "                               If not specified, uses the current directory and enables interactive API key setup."
    echo "                               If it exists and contains MindX, it will be configured. If not, MindX structure will be created."
    echo ""
    echo "Options:"
    echo "  --config-file <path>         Path to an existing mindx_config.json to use."
    echo "  --dotenv-file <path>         Path to an existing .env file to copy into the project."
    echo "  --run                        Start MindX backend and frontend services after setup."
    echo "  --frontend                   Start MindX web interface (backend + frontend with web UI)."
    echo "  --interactive                Prompt for API keys (Gemini, Mistral AI) during setup."
    echo "  --replicate                  Copy source code to target directory (default: use existing code)."
    echo "  --venv-name <name>           Override default virtual environment name (Default: ${DEFAULT_VENV_NAME})."
    echo "  --frontend-port <port>       Override default frontend port (Default: ${DEFAULT_FRONTEND_PORT})."
    echo "  --backend-port <port>        Override default backend port (Default: ${DEFAULT_BACKEND_PORT})."
    echo "  --log-level <level>          MindX application log level (DEBUG, INFO, etc. Default: ${DEFAULT_LOG_LEVEL})."
    echo "  -h, --help                   Show this help message."
    exit 0
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --config-file) MINDX_CONFIG_FILE_ARG="$2"; shift 2;;
        --dotenv-file) DOTENV_FILE_ARG="$2"; shift 2;;
        --run) RUN_SERVICES_FLAG=true; shift 1;;
        --interactive) INTERACTIVE_SETUP_FLAG=true; shift 1;;
        --replicate) REPLICATE_SOURCE_FLAG=true; shift 1;;
        --frontend) FRONTEND_FLAG=true; shift 1;;
        --venv-name) MINDX_VENV_NAME_OVERRIDE="$2"; shift 2;;
        --frontend-port) FRONTEND_PORT_OVERRIDE="$2"; shift 2;;
        --backend-port) BACKEND_PORT_OVERRIDE="$2"; shift 2;;
        --log-level) LOG_LEVEL_OVERRIDE="$2"; shift 2;;
        -h|--help) show_help;;
        *)
            if [[ -z "$TARGET_INSTALL_DIR_ARG" ]] && [[ ! "$1" =~ ^-- ]]; then
                TARGET_INSTALL_DIR_ARG="$1"
                shift 1
            else
                log_setup_error "Unknown option or too many arguments: $1"
                show_help # Will exit
            fi
            ;;
    esac
done

if [[ -z "$TARGET_INSTALL_DIR_ARG" ]]; then
    # Use current directory as default target when no parameters provided
    TARGET_INSTALL_DIR_ARG="$(pwd)"
    log_setup_info "No target directory specified. Using current directory: $TARGET_INSTALL_DIR_ARG"
    # Enable interactive setup by default for default installation
    INTERACTIVE_SETUP_FLAG=true
    log_setup_info "Default installation mode: Interactive setup enabled for API key configuration."
fi

# Resolve and create project root
PROJECT_ROOT=$(readlink -f "$TARGET_INSTALL_DIR_ARG") # Get absolute path
if [ ! -d "$PROJECT_ROOT/$DEFAULT_PROJECT_ROOT_NAME" ]; then
    # If augmentic_mindx doesn't exist inside target, assume target IS project root.
    # Or, if target is meant to *contain* augmentic_mindx, create it.
    # For this script, let's assume TARGET_INSTALL_DIR_ARG *is* the project root.
    log_setup_info "Target directory '$PROJECT_ROOT' will be used as MindX project root."
    mkdir -p "$PROJECT_ROOT" || { log_setup_error "Failed to create project root: $PROJECT_ROOT"; exit 1; }
else
    PROJECT_ROOT="$PROJECT_ROOT/$DEFAULT_PROJECT_ROOT_NAME" # If target dir contains it
    log_setup_info "MindX project found within target directory at: $PROJECT_ROOT"
fi


# --- Setup Script Log File (now that PROJECT_ROOT is confirmed) ---
mkdir -p "$PROJECT_ROOT/data/logs" || { echo "[ERROR] Critical: Failed to create $PROJECT_ROOT/data/logs for setup log."; exit 1; }
SETUP_LOG_FILE="$PROJECT_ROOT/data/logs/mindx_deployment_setup.log"
# Redirect all stdout/stderr of this script to a tee command to capture in file and show on console
# This is complex to do for the whole script after it has started.
# Simpler: Ensure all log_setup_* functions write to file. We'll do that.
echo "--- MindX Deployment Log $(date) ---" > "$SETUP_LOG_FILE" # Initialize/clear log

log_setup_info "MindX Deployment Script v${SCRIPT_VERSION}"
log_setup_info "Final Project Root: $PROJECT_ROOT"

# --- Override Defaults with CLI Args / Env Vars ---
MINDX_VENV_NAME="${MINDX_VENV_NAME_OVERRIDE:-${MINDX_VENV_NAME:-$DEFAULT_VENV_NAME}}"
FRONTEND_PORT_EFFECTIVE="${FRONTEND_PORT_OVERRIDE:-${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}}"
BACKEND_PORT_EFFECTIVE="${BACKEND_PORT_OVERRIDE:-${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}}"
MINDX_APP_LOG_LEVEL="${LOG_LEVEL_OVERRIDE:-${MINDX_LOG_LEVEL:-$DEFAULT_LOG_LEVEL}}" # For app, not this script

# --- Derived Paths (Absolute) ---
MINDX_VENV_PATH_ABS="$PROJECT_ROOT/$MINDX_VENV_NAME"
MINDX_BACKEND_SERVICE_DIR_ABS="$PROJECT_ROOT/mindx_backend_service" # Keep service separate from 'mindx' package
MINDX_FRONTEND_UI_DIR_ABS="$PROJECT_ROOT/mindx_frontend_ui"
MINDX_DATA_DIR_ABS="$PROJECT_ROOT/data"
MINDX_LOGS_DIR_ABS="$MINDX_DATA_DIR_ABS/logs" # For application logs
MINDX_PIDS_DIR_ABS="$MINDX_DATA_DIR_ABS/pids"
MINDX_CONFIG_DIR_ABS="$MINDX_DATA_DIR_ABS/config"


MINDX_BACKEND_APP_LOG_FILE="$MINDX_LOGS_DIR_ABS/mindx_coordinator_service.log"
MINDX_FRONTEND_APP_LOG_FILE="$MINDX_LOGS_DIR_ABS/mindx_frontend_service.log"
BACKEND_PID_FILE="$MINDX_PIDS_DIR_ABS/mindx_backend.pid"
FRONTEND_PID_FILE="$MINDX_PIDS_DIR_ABS/mindx_frontend.pid"

# --- Helper Functions (Continued) ---
function create_or_overwrite_file { # pragma: no cover
    local file_path_abs="$1"; local content="$2"; local perms="${3:-644}" # Default to 644 for non-sensitive files
    local dir_path_abs; dir_path_abs=$(dirname "$file_path_abs")
    if ! mkdir -p "$dir_path_abs"; then log_setup_error "Failed to create directory: $dir_path_abs"; exit 1; fi
    log_setup_info "Creating/Overwriting file: $file_path_abs with permissions $perms"
    # Write content first
    if [ -n "$content" ]; then
        if ! printf '%s\n' "$content" > "$file_path_abs"; then log_setup_error "Failed write to: $file_path_abs"; exit 1; fi
    else
        if ! > "$file_path_abs"; then log_setup_error "Failed create empty: $file_path_abs"; exit 1; fi
    fi
    # Set permissions
    if ! chmod "$perms" "$file_path_abs"; then log_setup_warning "Failed to set permissions $perms for $file_path_abs"; fi
}

function create_or_overwrite_file_secure { # pragma: no cover
    local file_path_abs="$1"; local content="$2"; local perms="${3:-600}" # Default to 600 for sensitive files
    local dir_path_abs; dir_path_abs=$(dirname "$file_path_abs")
    if ! mkdir -p "$dir_path_abs"; then log_setup_error "Failed to create directory: $dir_path_abs"; exit 1; fi
    log_setup_info "Creating/Overwriting file: $file_path_abs with permissions $perms"
    # Write content first
    if [ -n "$content" ]; then
        if ! printf '%s\n' "$content" > "$file_path_abs"; then log_setup_error "Failed write to: $file_path_abs"; exit 1; fi
    else
        if ! > "$file_path_abs"; then log_setup_error "Failed create empty: $file_path_abs"; exit 1; fi
    fi
    # Set permissions
    if ! chmod "$perms" "$file_path_abs"; then log_setup_warning "Failed to set permissions $perms for $file_path_abs"; fi
}

function check_command_presence { # pragma: no cover
  if ! command -v "$1" &> /dev/null; then
    log_setup_error "'$1' is not installed or not in PATH. Please install it."
    # Add more specific help for missing commands if possible
    exit 1
  fi
}

function check_python_venv_command { # pragma: no cover
  # Assumes venv is active when called
  local cmd_to_check="$1"; local install_package_name="$2"
  install_package_name="${install_package_name:-$cmd_to_check}"
  if ! command -v "$cmd_to_check" &> /dev/null; then
    log_setup_warn "'$cmd_to_check' not found in venv. Attempting install: '$install_package_name'..."
    if ! python -m pip install "$install_package_name" -q; then log_setup_error "Failed to install '$install_package_name'."; return 1; fi
    log_setup_info "'$install_package_name' installed in venv."
    if ! command -v "$cmd_to_check" &> /dev/null; then log_setup_error "'$cmd_to_check' still not found."; return 1; fi
  fi
  log_setup_info "'$cmd_to_check' confirmed in venv."
  return 0
}

function copy_mindx_source_code {
    log_setup_info "Copying MindX source code to deployment directory..."
    
    # List of source directories to copy
    local source_dirs=("agents" "api" "core" "evolution" "learning" "llm" "monitoring" "orchestration" "scripts" "tools" "utils" "requirements.txt")
    
    for item in "${source_dirs[@]}"; do
        if [ -e "$item" ]; then
            log_setup_info "Copying: $item"
            cp -r "$item" "$PROJECT_ROOT/"
        else
            log_setup_warn "Source not found, skipping: $item"
        fi
    done
    
    log_setup_info "Source code copy complete."
}

# --- Create Base Project Structure if not exists ---
function ensure_mindx_structure {
    log_setup_info "Ensuring MindX base directory structure exists at $PROJECT_ROOT..."
    mkdir -p "$PROJECT_ROOT/mindx/core"
    mkdir -p "$PROJECT_ROOT/mindx/orchestration"
    mkdir -p "$PROJECT_ROOT/mindx/learning"
    mkdir -p "$PROJECT_ROOT/mindx/monitoring"
    mkdir -p "$PROJECT_ROOT/mindx/llm"
    mkdir -p "$PROJECT_ROOT/mindx/utils"
    mkdir -p "$PROJECT_ROOT/mindx/tools" # For BaseGenAgent etc.
    mkdir -p "$PROJECT_ROOT/mindx/docs"   # Stub dir
    mkdir -p "$PROJECT_ROOT/scripts"
    mkdir -p "$MINDX_DATA_DIR_ABS" # Central data directory
    mkdir -p "$MINDX_LOGS_DIR_ABS"
    mkdir -p "$MINDX_PIDS_DIR_ABS"
    mkdir -p "$MINDX_CONFIG_DIR_ABS" # For basegen_config.json etc.

    # Create minimal __init__.py files to make them packages
    find "$PROJECT_ROOT/mindx" -type d -exec touch {}/__init__.py \;
    touch "$PROJECT_ROOT/scripts/__init__.py" # If scripts are also to be importable

    # Only copy source code if --replicate flag is used
    if [[ "$REPLICATE_SOURCE_FLAG" == true ]]; then
    copy_mindx_source_code
    else
        log_setup_info "Skipping source code replication (use --replicate to copy source files)."
    fi

    # Check if core MindX source files (e.g. coordinator, sia) exist.
    # If not, this script cannot proceed with actually *running* MindX.
    # For a true "installer", it would fetch/copy these files.
    # For this script, we assume they are already part of the $PROJECT_ROOT (e.g. git cloned).
    if [ ! -f "$PROJECT_ROOT/orchestration/coordinator_agent.py" ]; then
        log_setup_warn "Core MindX agent source files (coordinator_agent.py) not found in $PROJECT_ROOT/orchestration/..."
        log_setup_warn "This script primarily sets up the environment and services for an EXISTING MindX codebase."
        log_setup_warn "If you intended to deploy MindX code, ensure it's present in $PROJECT_ROOT first."
        # Optionally, exit here if code is mandatory:
        log_setup_error "MindX source code not found. Deployment cannot continue."
        exit 1
    fi
    log_setup_info "MindX base directory structure ensured."
}


# --- Configuration File Management ---
# --- Interactive API Key Collection ---
function prompt_for_api_keys {
    local gemini_key=""
    local mistral_key=""
    
    if [[ "$INTERACTIVE_SETUP_FLAG" == true ]]; then
        log_setup_info "Interactive setup enabled. Collecting API keys..."
        
        # Prompt for Gemini API key
        echo ""
        echo "=== API Key Configuration ==="
        echo "Enter your API keys (press Enter to skip and leave empty):"
        echo ""
        
        read -p "Gemini API Key (from https://aistudio.google.com/app/apikey): " gemini_key
        if [[ -n "$gemini_key" ]]; then
            log_setup_info "Gemini API key provided."
        else
            log_setup_info "No Gemini API key provided, leaving empty."
            gemini_key=""
        fi
        
        echo ""
        read -p "Mistral AI API Key (from https://console.mistral.ai/): " mistral_key
        if [[ -n "$mistral_key" ]]; then
            log_setup_info "Mistral AI API key provided."
        else
            log_setup_info "No Mistral AI API key provided, leaving empty."
            mistral_key=""
        fi
        
        echo ""
        log_setup_info "API key collection complete."
    else
        # Non-interactive mode - use defaults
        gemini_key="YOUR_GEMINI_API_KEY_HERE"
        mistral_key="YOUR_MISTRAL_API_KEY_HERE"
    fi
    
    # Export for use in .env generation
    export GEMINI_API_KEY_VAL="$gemini_key"
    export MISTRAL_API_KEY_VAL="$mistral_key"
}

function setup_dotenv_file {
    local target_dotenv_path="$PROJECT_ROOT/.env"
    if [ -f "$target_dotenv_path" ] && [ -z "$DOTENV_FILE_ARG" ]; then
        log_setup_info ".env file already exists at $target_dotenv_path. Skipping creation unless --dotenv-file is used to overwrite."
        return 0
    fi
    
    # Check if .env file exists and prompt for API keys if not
    if [ ! -f "$target_dotenv_path" ]; then
        log_setup_info "No .env file found. Will prompt for API keys during setup."
        # Force interactive mode for missing .env file
        INTERACTIVE_SETUP_FLAG=true
    fi

    local env_content_source_path=""
    if [ -n "$DOTENV_FILE_ARG" ]; then
        if [ -f "$DOTENV_FILE_ARG" ]; then
            env_content_source_path="$DOTENV_FILE_ARG"
            log_setup_info "Using provided .env file: $env_content_source_path"
        else
            log_setup_error "Provided --dotenv-file '$DOTENV_FILE_ARG' not found. Using default content."
        fi
    fi

    if [ -n "$env_content_source_path" ]; then
        cp "$env_content_source_path" "$target_dotenv_path" || { log_setup_error "Failed to copy provided .env file."; exit 1; }
        chmod 600 "$target_dotenv_path" # Secure permissions for .env
    else
        log_setup_info "No .env file provided or found. Creating a default .env at $target_dotenv_path"
        
        # Collect API keys interactively if needed
        prompt_for_api_keys
        
        local gemini_api_key_val="${GEMINI_API_KEY_VAL:-}"
        local mistral_api_key_val="${MISTRAL_API_KEY_VAL:-}"

        # Generate .env content with proper handling of empty API keys
        local default_env_content=""
        default_env_content+="# MindX System Environment Configuration (.env)\n"
        default_env_content+="# This file is loaded by mindx.utils.Config\n\n"
        default_env_content+="# --- General Logging Level ---\n"
        default_env_content+="MINDX_LOG_LEVEL=\"${MINDX_APP_LOG_LEVEL}\"\n\n"
        default_env_content+="# --- LLM Provider Selection ---\n"
        default_env_content+="# Options: 'gemini', 'mistral', 'ollama', 'openai'\n"
        default_env_content+="MINDX_LLM__DEFAULT_PROVIDER=\"gemini\"\n\n"
        default_env_content+="# --- Ollama Configuration (if using Ollama) ---\n"
        default_env_content+="# MINDX_LLM__OLLAMA__BASE_URL=\"http://localhost:11434\" # Default, uncomment to override\n\n"
        default_env_content+="# --- Gemini Specific Configuration ---\n"
        default_env_content+="# IMPORTANT: Get your API key from Google AI Studio (https://aistudio.google.com/app/apikey)\n"
        default_env_content+="# This key will be used if MINDX_LLM__GEMINI__API_KEY is not set directly below.\n"
        
        if [[ -n "$gemini_api_key_val" ]]; then
            default_env_content+="GEMINI_API_KEY=\"${gemini_api_key_val}\"\n"
            default_env_content+="MINDX_LLM__GEMINI__API_KEY=\"${gemini_api_key_val}\"\n"
        else
            default_env_content+="# GEMINI_API_KEY=\"\"\n"
            default_env_content+="# MINDX_LLM__GEMINI__API_KEY=\"\"\n"
        fi
        
        default_env_content+="MINDX_LLM__GEMINI__DEFAULT_MODEL=\"gemini-1.5-flash-latest\"\n"
        default_env_content+="MINDX_LLM__GEMINI__DEFAULT_MODEL_FOR_CODING=\"gemini-1.5-pro-latest\" # Or flash for cost/speed\n"
        default_env_content+="MINDX_LLM__GEMINI__DEFAULT_MODEL_FOR_REASONING=\"gemini-1.5-pro-latest\"\n\n"
        default_env_content+="# --- Mistral AI Specific Configuration ---\n"
        default_env_content+="# IMPORTANT: Get your API key from Mistral AI Console (https://console.mistral.ai/)\n"
        default_env_content+="# This key will be used if MISTRAL_API_KEY is not set directly below.\n"
        
        if [[ -n "$mistral_api_key_val" ]]; then
            default_env_content+="MISTRAL_API_KEY=\"${mistral_api_key_val}\"\n"
            default_env_content+="MINDX_LLM__MISTRAL__API_KEY=\"${mistral_api_key_val}\"\n"
        else
            default_env_content+="# MISTRAL_API_KEY=\"\"\n"
            default_env_content+="# MINDX_LLM__MISTRAL__API_KEY=\"\"\n"
        fi
        
        default_env_content+="MINDX_LLM__MISTRAL__DEFAULT_MODEL=\"mistral-large-latest\"\n"
        default_env_content+="MINDX_LLM__MISTRAL__DEFAULT_MODEL_FOR_CODING=\"codestral-latest\"\n"
        default_env_content+="MINDX_LLM__MISTRAL__DEFAULT_MODEL_FOR_REASONING=\"mistral-large-latest\"\n\n"
        default_env_content+="# --- OpenAI Configuration (if using OpenAI) ---\n"
        default_env_content+="# OPENAI_API_KEY=\"your-openai-api-key-here\"\n"
        default_env_content+="# MINDX_LLM__OPENAI__API_KEY=\"your-openai-api-key-here\"\n"
        default_env_content+="# MINDX_LLM__OPENAI__DEFAULT_MODEL=\"gpt-4o\"\n\n"
        default_env_content+="# --- Web Search Configuration ---\n"
        default_env_content+="# GOOGLE_SEARCH_API_KEY=\"your-google-search-api-key\"\n"
        default_env_content+="# GOOGLE_SEARCH_ENGINE_ID=\"your-search-engine-id\"\n\n"
        default_env_content+="# --- Database Configuration ---\n"
        default_env_content+="MINDX_DB__URL=\"sqlite:///data/mindx.db\"\n\n"
        default_env_content+="# --- Performance Configuration ---\n"
        default_env_content+="MINDX_MAX_CONCURRENT_TASKS=\"3\"\n"
        default_env_content+="MINDX_TASK_TIMEOUT_SECONDS=\"300\"\n"

        # Write the dynamically generated .env content
        printf '%b' "$default_env_content" > "$target_dotenv_path" || { log_setup_error "Failed to write .env file."; exit 1; }
        chmod 600 "$target_dotenv_path" # Secure permissions for .env
    fi
    log_setup_info ".env file configured at $target_dotenv_path"
}

function setup_mindx_config_json { # pragma: no cover
    local target_config_path="$MINDX_CONFIG_DIR_ABS/mindx_config.json" # Centralized location
    if [ -f "$target_config_path" ] && [ -z "$MINDX_CONFIG_FILE_ARG" ]; then
        log_setup_info "mindx_config.json already exists at $target_config_path. Skipping."
        return 0
    fi

    if [ -n "$MINDX_CONFIG_FILE_ARG" ]; then
        if [ -f "$MINDX_CONFIG_FILE_ARG" ]; then
            cp "$MINDX_CONFIG_FILE_ARG" "$target_config_path" || { log_setup_error "Failed to copy provided mindx_config.json."; exit 1; }
            log_setup_info "Used provided mindx_config.json: $MINDX_CONFIG_FILE_ARG"
        else
            log_setup_error "Provided --config-file '$MINDX_CONFIG_FILE_ARG' not found. Using default content."
            # Fall through to create default
        fi
    fi
    
    if [ ! -f "$target_config_path" ]; then # Create default if still not present
        log_setup_info "Creating default mindx_config.json at $target_config_path"
        # This default JSON complements .env; .env/environment vars will override these.
        read -r -d '' default_json_config_content << 'EOF_DEFAULT_JSON_CONFIG'
{
  "system": {
    "version": "0.4.0",
    "name": "MindX Self-Improving System (Augmentic)"
  },
  "logging": {
    "uvicorn_level": "info" 
  },
  "llm": {
    "providers": {
      "ollama": {"enabled": true},
      "gemini": {"enabled": true},
      "mistral": {"enabled": true}
    }
  },
  "self_improvement_agent": {
    "analysis": {
      "max_code_chars": 70000,
      "max_description_tokens": 350
    },
    "implementation": {
      "max_code_gen_tokens": 12000,
      "temperature": 0.05
    },
    "evaluation": {
      "max_chars_for_critique": 4000,
      "max_critique_tokens": 300
    }
  },
  "coordinator": {
    "autonomous_improvement": {
      "critical_components": [
        "mindx.learning.self_improve_agent",
        "mindx.orchestration.coordinator_agent",
        "mindx.utils.config"
      ]
    }
  },
  "tools": {
    "note_taking": {
        "enabled": true,
        "notes_dir_relative_to_project": "data/bdi_agent_notes" 
    },
    "summarization": {
        "enabled": true,
        "max_input_chars": 30000
        # LLM for summarization tool can be configured here too, e.g.
        # "llm": {"provider": "ollama", "model": "mistral"}
    },
    "web_search": {
        "enabled": true, # Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env
        "timeout_seconds": 20.0
        # API keys should be in .env, not here
    }
  }
}
EOF_DEFAULT_JSON_CONFIG
        create_or_overwrite_file_secure "$target_config_path" "$default_json_config_content" "644" # Readable by all
    fi
    log_setup_info "mindx_config.json configured at $target_config_path"
}


# --- Python Virtual Environment Setup (Simplified - Main one done by setup_mindx_deps) ---
# Individual service venv setup removed as main project venv is now primary.

# --- Backend Service Setup ---
# (setup_backend_service from previous version - mostly file creation)
# (It assumes Python dependencies are already handled by the main venv)
function setup_backend_service { # pragma: no cover
  log_setup_info "Setting up MindX Backend Service files in '$MINDX_BACKEND_SERVICE_DIR_ABS'..."
  mkdir -p "$MINDX_BACKEND_SERVICE_DIR_ABS"
  # FastAPI main application (main_service.py)
  # Content is the FULL main_service.py from previous response (the one with API endpoints)
  # For brevity, I'm using a placeholder here. In the actual script, paste the full content.
  # **IMPORTANT**: Replace the line above with the actual heredoc or cat of the full backend_main_service.py content
  # from the previous response if you don't have a template file. Example:
  # read -r -d '' backend_main_py_content << 'EOF_BACKEND_MAIN_SERVICE_TEMPLATE_CONTENT'
  # # ... (Full backend_main_service.py content from previous response here) ...
  # EOF_BACKEND_MAIN_SERVICE_TEMPLATE_CONTENT
  # For this script to be self-contained without external templates:
  read -r -d '' backend_main_py_content <<'EOF_BACKEND_API'
# mindx/scripts/api_server.py

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Add project root to path to allow imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from agents.memory_agent import MemoryAgent
from agents.guardian_agent import GuardianAgent
from core.id_manager_agent import IDManagerAgent
from core.belief_system import BeliefSystem
from llm.model_registry import get_model_registry_async
from utils.config import Config
from api.command_handler import CommandHandler
from utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# --- Pydantic Models for API Request/Response Validation ---

class DirectivePayload(BaseModel):
    directive: str

class AnalyzeCodebasePayload(BaseModel):
    path: str
    focus: str

class IdCreatePayload(BaseModel):
    entity_id: str

class IdDeprecatePayload(BaseModel):
    public_address: str
    entity_id_hint: Optional[str] = None

class AuditGeminiPayload(BaseModel):
    test_all: bool = False
    update_config: bool = False

class CoordQueryPayload(BaseModel):
    query: str

class CoordAnalyzePayload(BaseModel):
    context: Optional[str] = None

class CoordImprovePayload(BaseModel):
    component_id: str
    context: Optional[str] = None

class CoordBacklogIdPayload(BaseModel):
    backlog_item_id: str

class AgentCreatePayload(BaseModel):
    agent_type: str
    agent_id: str
    config: Dict[str, Any]

class AgentDeletePayload(BaseModel):
    agent_id: str

class AgentEvolvePayload(BaseModel):
    agent_id: str
    directive: str

class AgentSignPayload(BaseModel):
    agent_id: str
    message: str

# --- FastAPI Application ---

app = FastAPI(
    title="mindX API",
    description="API for interacting with the mindX Augmentic Intelligence system.",
    version="1.3.4",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

command_handler: Optional[CommandHandler] = None

@app.on_event("startup")
async def startup_event():
    """Initializes all necessary mindX components on application startup."""
    global command_handler
    logger.info("FastAPI server starting up... Initializing mindX agents.")
    try:
        app_config = Config()
        memory_agent = MemoryAgent(config=app_config)
        belief_system = BeliefSystem()
        id_manager = await IDManagerAgent.get_instance(config_override=app_config, belief_system=belief_system)
        guardian_agent = await GuardianAgent.get_instance(id_manager=id_manager, config_override=app_config)
        model_registry = await get_model_registry_async(config=app_config)
        
        coordinator_instance = await get_coordinator_agent_mindx_async(
            config_override=app_config,
            memory_agent=memory_agent,
            belief_system=belief_system
        )
        if not coordinator_instance:
            raise RuntimeError("Failed to initialize CoordinatorAgent.")

        mastermind_instance = await MastermindAgent.get_instance(
            config_override=app_config,
            coordinator_agent_instance=coordinator_instance,
            memory_agent=memory_agent,
            guardian_agent=guardian_agent,
            model_registry=model_registry
        )
        
        command_handler = CommandHandler(mastermind_instance)
        logger.info("mindX components initialized successfully. API is ready.")
    except Exception as e:
        logger.critical(f"Failed to initialize mindX components during startup: {e}", exc_info=True)
        command_handler = None

# --- API Endpoints ---

@app.post("/commands/evolve", summary="Evolve mindX codebase")
async def evolve(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_evolve(payload.directive)

@app.post("/commands/deploy", summary="Deploy a new agent")
async def deploy(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_deploy(payload.directive)

@app.post("/commands/introspect", summary="Generate a new persona")
async def introspect(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_introspect(payload.directive)

@app.get("/status/mastermind", summary="Get Mastermind status")
async def mastermind_status():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_mastermind_status()

@app.get("/registry/agents", summary="Show agent registry")
async def show_agent_registry():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_show_agent_registry()

@app.get("/registry/tools", summary="Show tool registry")
async def show_tool_registry():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_show_tool_registry()

@app.post("/commands/analyze_codebase", summary="Analyze a codebase")
async def analyze_codebase(payload: AnalyzeCodebasePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_analyze_codebase(payload.path, payload.focus)

@app.post("/commands/basegen", summary="Generate Markdown documentation")
async def basegen(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_basegen(payload.directive)

@app.get("/identities", summary="List all identities")
async def id_list():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_id_list()

@app.post("/identities", summary="Create a new identity")
async def id_create(payload: IdCreatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_id_create(payload.entity_id)

@app.delete("/identities", summary="Deprecate an identity")
async def id_deprecate(payload: IdDeprecatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_id_deprecate(payload.public_address, payload.entity_id_hint)

@app.post("/commands/audit_gemini", summary="Audit Gemini models")
async def audit_gemini(payload: AuditGeminiPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_audit_gemini(payload.test_all, payload.update_config)

@app.post("/coordinator/query", summary="Query the Coordinator")
async def coord_query(payload: CoordQueryPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_query(payload.query)

@app.post("/coordinator/analyze", summary="Trigger system analysis")
async def coord_analyze(payload: CoordAnalyzePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_analyze(payload.context)

@app.post("/coordinator/improve", summary="Request a component improvement")
async def coord_improve(payload: CoordImprovePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_improve(payload.component_id, payload.context)

@app.get("/coordinator/backlog", summary="Get the improvement backlog")
async def coord_backlog():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_backlog()

@app.post("/coordinator/backlog/process", summary="Process a backlog item")
async def coord_process_backlog():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_process_backlog()

@app.post("/coordinator/backlog/approve", summary="Approve a backlog item")
async def coord_approve(payload: CoordBacklogIdPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_approve(payload.backlog_item_id)

@app.post("/coordinator/backlog/reject", summary="Reject a backlog item")
async def coord_reject(payload: CoordBacklogIdPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_reject(payload.backlog_item_id)

@app.post("/agents", summary="Create a new agent")
async def agent_create(payload: AgentCreatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_create(payload.agent_type, payload.agent_id, payload.config)

@app.delete("/agents/{agent_id}", summary="Delete an agent")
async def agent_delete(agent_id: str):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_delete(agent_id)

@app.get("/agents", summary="List all registered agents")
async def agent_list():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_list()

@app.post("/agents/{agent_id}/evolve", summary="Evolve a specific agent")
async def agent_evolve(agent_id: str, payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_evolve(agent_id, payload.directive)

@app.post("/agents/{agent_id}/sign", summary="Sign a message with an agent's identity")
async def agent_sign(agent_id: str, payload: AgentSignPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_sign(agent_id, payload.message)

@app.get("/logs/runtime", summary="Get runtime logs")
async def get_runtime_logs():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_get_runtime_logs()

@app.get("/", summary="Root endpoint")
async def root():
    return {"message": "Welcome to the mindX API. See /docs for details."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF_BACKEND_API
  create_or_overwrite_file "$MINDX_BACKEND_SERVICE_DIR_ABS/main_service.py" "$backend_main_py_content"
  log_setup_info "MindX Backend Service main_service.py created."
}


# --- Frontend UI Setup ---
# (setup_frontend_ui from previous version - file creation)
# (It assumes Node.js/npm dependencies will be installed if needed)
function setup_frontend_ui { # pragma: no cover
  log_setup_info "Setting up MindX Frontend UI files in '$MINDX_FRONTEND_UI_DIR_ABS'..."
  mkdir -p "$MINDX_FRONTEND_UI_DIR_ABS"

  # --- index.html ---
  read -r -d '' index_html_content <<EOF_INDEX_HTML
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MindX Control Panel</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>MindX Control Panel</h1>
            <div id="status-light" class="status-light-red" title="Disconnected"></div>
        </header>
        <main>
            <div class="control-section">
                <h2>Evolve Codebase</h2>
                <textarea id="evolve-directive" placeholder="Enter a high-level directive for evolution..."></textarea>
                <button id="evolve-btn">Send Directive</button>
            </div>
            <div class="control-section">
                <h2>Query Coordinator</h2>
                <input type="text" id="query-input" placeholder="Enter your query...">
                <button id="query-btn">Send Query</button>
            </div>
            <div class="response-section">
                <h2>Response</h2>
                <pre id="response-output">Awaiting command...</pre>
            </div>
        </main>
    </div>
    <script>
        window.MINDX_BACKEND_PORT = "${BACKEND_PORT_EFFECTIVE}";
    </script>
    <script src="app.js"></script>
</body>
</html>
EOF_INDEX_HTML
  create_or_overwrite_file "$MINDX_FRONTEND_UI_DIR_ABS/index.html" "$index_html_content"

  # --- styles.css ---
  read -r -d '' styles_css_content <<'EOF_STYLES_CSS'
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #f0f2f5;
    color: #333;
    margin: 0;
    padding: 20px;
}
.container { max-width: 800px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }
h1, h2 { color: #1c1e21; }
h1 { font-size: 1.8em; }
h2 { font-size: 1.2em; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 20px;}
.control-section, .response-section { margin-bottom: 20px; }
textarea, input[type="text"] {
    width: 100%;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 1em;
    margin-bottom: 10px;
    box-sizing: border-box;
}
textarea { min-height: 80px; resize: vertical; }
button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 10px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1em;
    transition: background-color 0.2s;
}
button:hover { background-color: #0056b3; }
pre {
    background-color: #282c34;
    color: #abb2bf;
    padding: 15px;
    border-radius: 4px;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: 'Courier New', Courier, monospace;
}
.status-light-red { width: 20px; height: 20px; background-color: #dc3545; border-radius: 50%; }
.status-light-green { width: 20px; height: 20px; background-color: #28a745; border-radius: 50%; }
EOF_STYLES_CSS
  create_or_overwrite_file "$MINDX_FRONTEND_UI_DIR_ABS/styles.css" "$styles_css_content"

  # --- app.js ---
  read -r -d '' app_js_content <<'EOF_APP_JS'
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
EOF_APP_JS
  create_or_overwrite_file "$MINDX_FRONTEND_UI_DIR_ABS/app.js" "$app_js_content"

  # --- package.json ---
  read -r -d '' package_json_content <<'EOF_PACKAGE_JSON'
{
  "name": "mindx-frontend",
  "version": "1.0.0",
  "description": "Frontend for MindX Control Panel",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
EOF_PACKAGE_JSON
  create_or_overwrite_file "$MINDX_FRONTEND_UI_DIR_ABS/package.json" "$package_json_content"

  # --- server.js ---
  read -r -d '' server_js_content <<'EOF_SERVER_JS'
const express = require('express');
const path = require('path');
const app = express();
const port = process.env.FRONTEND_PORT || 3000;

app.use(express.static(__dirname));

app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'index.html'));
});

app.listen(port, '0.0.0.0', () => {
  console.log(`MindX Frontend running on http://localhost:${port}`);
});
EOF_SERVER_JS
  create_or_overwrite_file "$MINDX_FRONTEND_UI_DIR_ABS/server.js" "$server_js_content"

  log_setup_info "MindX Frontend UI files created. Installing dependencies..."
  local current_dir_for_npm; current_dir_for_npm=$(pwd)
  cd "$MINDX_FRONTEND_UI_DIR_ABS" || { log_setup_error "Failed to cd to frontend dir for npm install."; return 1; }
  if [ -f "package.json" ]; then
    log_setup_info "Running 'npm install' for frontend..."
    npm install --silent >> "$MINDX_FRONTEND_APP_LOG_FILE" 2>&1 || { log_setup_error "npm install failed for frontend. Check $MINDX_FRONTEND_APP_LOG_FILE."; cd "$current_dir_for_npm" || exit 1; return 1; }
    log_setup_info "Frontend dependencies installed."
  fi
  cd "$current_dir_for_npm" || { log_setup_error "Failed to cd back after npm install."; exit 1; }
  return 0
}

# --- Web Frontend Functions ---
function check_port {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

function kill_port {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        log_setup_warn "Killing existing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
        sleep 2
    fi
}

function start_web_frontend {
    log_setup_info "🧠 Starting MindX Web Interface..."
    log_setup_info "=================================="
    
    # Check if required directories exist
    if [ ! -d "$MINDX_BACKEND_SERVICE_DIR_ABS" ]; then
        log_setup_error "Backend directory not found: $MINDX_BACKEND_SERVICE_DIR_ABS"
        return 1
    fi

    if [ ! -d "$MINDX_FRONTEND_UI_DIR_ABS" ]; then
        log_setup_error "Frontend directory not found: $MINDX_FRONTEND_UI_DIR_ABS"
        return 1
    fi

    # Check if required files exist
    if [ ! -f "$MINDX_BACKEND_SERVICE_DIR_ABS/main_service.py" ]; then
        log_setup_error "Backend service file not found: $MINDX_BACKEND_SERVICE_DIR_ABS/main_service.py"
        return 1
    fi

    if [ ! -f "$MINDX_FRONTEND_UI_DIR_ABS/server.js" ]; then
        log_setup_error "Frontend server file not found: $MINDX_FRONTEND_UI_DIR_ABS/server.js"
        return 1
    fi

    # Kill any existing processes on our ports
    log_setup_info "Checking for existing processes..."
    kill_port $BACKEND_PORT_EFFECTIVE
    kill_port $FRONTEND_PORT_EFFECTIVE

    # Start backend
    log_setup_info "Starting MindX Backend API on port $BACKEND_PORT_EFFECTIVE..."
    cd "$PROJECT_ROOT"
    VENV_PYTHON="$MINDX_VENV_PATH_ABS/bin/python"
    $VENV_PYTHON -m uvicorn api.api_server:app --host 0.0.0.0 --port $BACKEND_PORT_EFFECTIVE &
    BACKEND_PID=$!

    # Wait for backend to start
    log_setup_info "Waiting for backend to initialize..."
    sleep 5

    # Check if backend is running
    if ! check_port $BACKEND_PORT_EFFECTIVE; then
        log_setup_error "Backend failed to start on port $BACKEND_PORT_EFFECTIVE"
        kill $BACKEND_PID 2>/dev/null
        return 1
    fi

    log_setup_info "Backend started successfully (PID: $BACKEND_PID)"

    # Start frontend
    log_setup_info "Starting MindX Frontend on port $FRONTEND_PORT_EFFECTIVE..."
    cd "$MINDX_FRONTEND_UI_DIR_ABS"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log_setup_info "Installing frontend dependencies..."
        npm install --silent
    fi

    # Start frontend server
    FRONTEND_PORT=$FRONTEND_PORT_EFFECTIVE BACKEND_PORT=$BACKEND_PORT_EFFECTIVE node server.js &
    FRONTEND_PID=$!

    # Wait for frontend to start
    log_setup_info "Waiting for frontend to initialize..."
    sleep 3

    # Check if frontend is running
    if ! check_port $FRONTEND_PORT_EFFECTIVE; then
        log_setup_error "Frontend failed to start on port $FRONTEND_PORT_EFFECTIVE"
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
        return 1
    fi

    log_setup_info "Frontend started successfully (PID: $FRONTEND_PID)"

    # Display access information
    echo ""
    echo "🎉 MindX Web Interface is now running!"
    echo "======================================"
    echo "Frontend: http://localhost:$FRONTEND_PORT_EFFECTIVE"
    echo "Backend API: http://localhost:$BACKEND_PORT_EFFECTIVE"
    echo ""
    echo "Press Ctrl+C to stop both services"
    echo ""

    # Function to cleanup on exit
    cleanup_web_frontend() {
        log_setup_info "Shutting down MindX Web Interface..."
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
        log_setup_info "Shutdown complete"
        exit 0
    }

    # Set up signal handlers
    trap cleanup_web_frontend SIGINT SIGTERM

    # Wait for user to stop
    wait
}

# --- Service Start/Stop Functions (Conceptual for systemd/supervisor) ---
# These functions would generate service unit files or supervisor config files.
# For direct backgrounding, we use simpler start/stop.

function start_mindx_service { # pragma: no cover
    local service_name="$1" # "backend" or "frontend"
    local exec_command="$2"
    local pid_file="$3"
    local log_file="$4"
    local service_dir="$5" # Directory to cd into before running

    if [ -f "$pid_file" ] && ps -p "$(cat "$pid_file")" > /dev/null; then
        log_setup_info "Service '$service_name' already running (PID: $(cat "$pid_file"))."
        return 0
    fi

    log_setup_info "Starting MindX Service '$service_name'..."
    mkdir -p "$(dirname "$pid_file")" "$(dirname "$log_file")" # Ensure dirs

    local current_dir_svc_start; current_dir_svc_start=$(pwd)
    cd "$service_dir" || { log_setup_error "Failed to cd to $service_dir for $service_name"; return 1; }

    # Use nohup to detach, redirect output, and run in background
    # The command needs to be constructed carefully.
    # Example for backend: nohup $venv_python main_service.py >> $log_file 2>&1 &
    # Example for frontend: nohup node server_static.js >> $log_file 2>&1 &
    nohup $exec_command >> "$log_file" 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"
    
    cd "$current_dir_svc_start" || exit 1 # Should not fail

    log_setup_info "MindX Service '$service_name' process initiated with PID: $pid."
    log_setup_info "Allowing a few seconds for '$service_name' to stabilize..."
    sleep 5 
    if ! ps -p "$pid" > /dev/null; then # pragma: no cover
        log_setup_error "Service '$service_name' (PID $pid) failed to stay running. Check logs: $log_file"
        rm -f "$pid_file"
        return 1
    fi
    log_setup_info "Service '$service_name' appears to be running."
    return 0
}

function stop_mindx_service { # pragma: no cover
    local pid_file="$1"; local service_name="$2"
    # (Same robust stop_service logic from previous script version)
    if [ -f "$pid_file" ]; then
        local pid_val; pid_val=$(cat "$pid_file");
        if [ -n "$pid_val" ] && ps -p "$pid_val" > /dev/null; then
            log_setup_info "Stopping $service_name (PID: $pid_val)..."; kill -TERM "$pid_val" &>/dev/null; sleep 2;
            if ps -p "$pid_val" > /dev/null; then log_setup_warn "$service_name (PID $pid_val) TERM fail, sending KILL..."; kill -KILL "$pid_val" &>/dev/null; sleep 1; fi
            if ps -p "$pid_val" > /dev/null; then log_setup_error "$service_name (PID $pid_val) FAILED TO STOP."
            else log_setup_info "$service_name stopped."
            fi
        else log_setup_info "$service_name (PID: $pid_val from file) already stopped or PID invalid."
        fi; rm -f "$pid_file" # Clean up PID file
    else log_setup_info "$service_name PID file '$pid_file' not found (might be first run or already cleaned)."
    fi
}

# --- Cleanup Function for traps ---
function cleanup_on_exit_final { # pragma: no cover
    log_setup_info "--- MindX Deployment Script Exiting: Initiating Final Cleanup ---"
    stop_mindx_service "$FRONTEND_PID_FILE" "MindX Frontend UI"
    stop_mindx_service "$BACKEND_PID_FILE" "MindX Backend Service"
    
    # Deactivate venv only if this script sourced it and it's still active.
    # This can be unreliable in traps. Best effort.
    if [[ -n "$VIRTUAL_ENV" ]] && [[ "$VIRTUAL_ENV" == "$MINDX_VENV_PATH_ABS" ]]; then
        log_setup_info "Attempting to deactivate MindX virtual environment from trap..."
        deactivate || log_setup_warn "Deactivate command failed or venv not active in this trap's shell context."
    fi
    log_setup_info "Cleanup attempt complete. MindX services signaled to stop."
    log_setup_info ">>> Augmentic MindX Deployment Script Terminated <<<"
    # Do not exit here if called by trap on EXIT, it causes recursion.
    # If called by SIGINT/SIGTERM, exit 0 makes sure the script exits cleanly after trap.
    if [[ "$_TRAP_SIGNAL" != "EXIT" ]]; then
        exit 0
    fi
}
# Store signal for trap handler
_TRAP_SIGNAL=""
function trap_handler_proxy { # pragma: no cover
    _TRAP_SIGNAL="$1" # Store the signal name
    cleanup_on_exit_final # Call the actual cleanup
}
trap 'trap_handler_proxy "SIGINT"' SIGINT
trap 'trap_handler_proxy "SIGTERM"' SIGTERM
trap 'cleanup_on_exit_final' EXIT


# --- Main Execution Flow ---
log_setup_info ">>> Starting Augmentic MindX Deployment Script (v${SCRIPT_VERSION}) <<<"
log_setup_info "Target Project Root: $PROJECT_ROOT"
log_setup_info "Application Log Level will be set to: $MINDX_APP_LOG_LEVEL"

# Create base directories
ensure_mindx_structure # Creates mindx package structure, data, logs, pids, config dirs

# Configure .env and mindx_config.json
setup_dotenv_file # Handles .env based on args or defaults
setup_mindx_config_json # Handles mindx_config.json

# --- Python Virtual Environment and Dependencies ---
function setup_virtual_environment_and_mindx_deps {
    log_setup_info "Setting up Python virtual environment at $MINDX_VENV_PATH_ABS..."
    check_command_presence "python3.11"

    if [ ! -d "$MINDX_VENV_PATH_ABS" ]; then
        log_setup_info "No existing venv found. Creating new one with Python 3.11..."
        if ! python3.11 -m venv "$MINDX_VENV_PATH_ABS"; then
            log_setup_error "Failed to create Python virtual environment with Python 3.11."
            return 1
        fi
    else
        log_setup_info "Existing virtual environment found."
    fi

    # Activate the virtual environment for this function's scope
    # shellcheck source=/dev/null
    if ! source "$MINDX_VENV_PATH_ABS/bin/activate"; then
        log_setup_error "Failed to activate Python virtual environment."
        return 1
    fi
    log_setup_info "Virtual environment activated."

    # Upgrade pip
    log_setup_info "Upgrading pip..."
    python -m pip install --upgrade pip -q || { log_setup_error "Failed to upgrade pip."; deactivate; return 1; }

    # Install dependencies from requirements.txt
    local requirements_file="$PROJECT_ROOT/requirements.txt"
    if [ -f "$requirements_file" ]; then
        log_setup_info "Installing dependencies from $requirements_file..."
        if ! python -m pip install -r "$requirements_file"; then
            log_setup_error "Failed to install dependencies from $requirements_file."
            deactivate
            return 1
        fi
        log_setup_info "Python dependencies installed successfully."
    else
        log_setup_warn "requirements.txt not found at $requirements_file. Skipping dependency installation."
    fi

    # Deactivate after finishing
    deactivate
    log_setup_info "Virtual environment setup complete."
    return 0
}

# Setup Python Environment
setup_virtual_environment_and_mindx_deps || { log_setup_error "Python environment setup failed. Exiting."; exit 1; }
# Venv is kept active for now. Service start functions will manage their own context.

# Deactivate main script's venv sourcing if any, services run in their own context
function deactivate_venv_if_active { # Helper for cleanup before exit
    if [[ -n "$VIRTUAL_ENV" ]] && [[ "$VIRTUAL_ENV" == "$MINDX_VENV_PATH_ABS" ]]; then
        log_setup_info "Deactivating main script's venv sourcing..."
        deactivate || log_setup_warn "Deactivate command failed in main script scope."
    fi
}

# Setup Backend and Frontend files (code generation within this script)
setup_backend_service || { log_setup_error "Backend Service file setup failed. Exiting."; deactivate_venv_if_active; exit 1; }
setup_frontend_ui || { log_setup_error "Frontend UI file setup failed. Exiting."; deactivate_venv_if_active; exit 1; }

deactivate_venv_if_active

if [[ "$FRONTEND_FLAG" == true ]]; then
    log_setup_info "--- Starting MindX Web Interface ---"
    start_web_frontend || { log_setup_error "MindX Web Interface failed to start. Exiting."; exit 1; }
elif [[ "$RUN_SERVICES_FLAG" == true ]]; then
    log_setup_info "--- Starting MindX Services (Backend & Frontend) ---"
    
    # Backend command construction
    # The backend's main_service.py now calls uvicorn.run itself.
    # We need to ensure it uses the venv's python.
    VENV_PYTHON="$MINDX_VENV_PATH_ABS/bin/python"
    BACKEND_EXEC_COMMAND="$VENV_PYTHON -m uvicorn api.api_server:app --host 0.0.0.0 --port $BACKEND_PORT_EFFECTIVE"

    start_mindx_service "MindX Backend Service" "$BACKEND_EXEC_COMMAND" "$BACKEND_PID_FILE" "$MINDX_BACKEND_APP_LOG_FILE" "$PROJECT_ROOT" || \
        { log_setup_error "MindX Backend Service failed to start. Check logs. Exiting."; exit 1; }

    # Frontend command construction
    # Node doesn't need venv, but ensure node and server.js are found
    NODE_EXEC_COMMAND="node server.js" # server.js is in MINDX_FRONTEND_UI_DIR_ABS
    start_mindx_service "MindX Frontend UI" "$NODE_EXEC_COMMAND" "$FRONTEND_PID_FILE" "$MINDX_FRONTEND_APP_LOG_FILE" "$MINDX_FRONTEND_UI_DIR_ABS" || \
        { log_setup_error "MindX Frontend UI failed to start. Check logs. Exiting."; exit 1; }

    log_setup_info ">>> Augmentic MindX System Services Started <<<"
    log_setup_info "  Backend API: http://localhost:$BACKEND_PORT_EFFECTIVE (and on 0.0.0.0)"
    log_setup_info "  Backend Logs: tail -f $MINDX_BACKEND_APP_LOG_FILE"
    log_setup_info "  Frontend UI: http://localhost:$FRONTEND_PORT_EFFECTIVE"
    log_setup_info "  Frontend Logs: tail -f $MINDX_FRONTEND_APP_LOG_FILE"
    log_setup_info ">>> Press Ctrl+C to stop all services and exit this script. <<<"

    log_setup_info "Deployment script running in foreground, monitoring services via 'wait'."
    wait # Wait for background jobs started by this script's shell
    log_setup_info "Deployment script 'wait' command finished or interrupted."
else
    log_setup_info "MindX setup complete. Services not started."
    log_setup_info "To start services manually:"
    log_setup_info "  Web Interface: ./mindX.sh --frontend"
    log_setup_info "  Services Only: ./mindX.sh --run"
    log_setup_info "  Backend Only: cd $MINDX_BACKEND_SERVICE_DIR_ABS && $MINDX_VENV_PATH_ABS/bin/python main_service.py"
    log_setup_info "  Frontend Only: cd $MINDX_FRONTEND_UI_DIR_ABS && node server.js"
fi

# Cleanup will be called by the EXIT trap automatically.
# No explicit call to cleanup_on_exit_final neededs r here.
