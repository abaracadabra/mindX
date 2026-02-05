#!/bin/bash
# doubletap (c) 2025 Gregory L. Magnusson
# find and kill llama with custom port kill
# ollama shepherd boot y/N control
# ufw rules to keep llama as localhost
#
# Handy for startup_agent: run this script to free the Ollama port or
# terminate Ollama before bootstrap (e.g. llm/ollama_bootstrap/aion.sh).
# Usage: from project root, ./api/ollama/doubletap.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# list known LLM process names
llm_process_names=("ollama" "llama" "llamacpp" "text-generation-server" "python" "pytorch" "tensorflow")

# Function to handle Ollama daemon first
handle_ollama_daemon() {
    echo -e "${YELLOW}=== Checking Ollama Service ===${NC}"
    if systemctl list-unit-files 2>/dev/null | grep -q ollama; then
        if systemctl is-active --quiet ollama 2>/dev/null; then
            echo -e "${YELLOW}stopping Ollama service...sudo systemctl stop ollama${NC}"
            sudo systemctl stop ollama
            sleep 2
        fi
    fi
}

# you have 3 seconds to enter a port number or default
default_port=11434
echo "you have 3 seconds to enter a port to scan (Enter use default: $default_port)..."
read -t 3 -p "enter port number: " user_port
port=${user_port:-$default_port}

# Diagnostic: Show processes using selected port
echo "checking for process on port $port..."
lsof_output=$(sudo lsof -i :$port 2>/dev/null)
netstat_output=$(sudo netstat -tulnp 2>/dev/null | grep $port)

# is LLM running
llm_found=false
is_llm_process=false

# check if process name matches known LLM processes
check_llm_process() {
    local process_name=$1
    for llm in "${llm_process_names[@]}"; do
        if [[ "$process_name" =~ $llm ]]; then
            return 0  # true
        fi
    done
    return 1  # false
}

# Handle daemon before checking processes
handle_ollama_daemon

if [[ -n "$lsof_output" ]]; then
    echo "process found via lsof on port $port:"
    echo "$lsof_output"
    
    # Extract process name from lsof output and check if it's an LLM
    process_name=$(echo "$lsof_output" | awk 'NR>1 {print $1}')
    if check_llm_process "$process_name"; then
        is_llm_process=true
        echo -e "${GREEN}confirmed LLM process: $process_name${NC}"
    else
        echo -e "${YELLOW}warning: unknown LLM service${NC}"
    fi
    llm_found=true
else
    echo "no process found via lsof on port $port."
fi

if [[ -n "$netstat_output" ]]; then
    echo "network activity found via netstat on port $port:"
    echo "$netstat_output"
    
    # Extract process name from netstat output and check if it's an LLM
    process_name=$(echo "$netstat_output" | awk '{print $7}' | cut -d'/' -f2)
    if check_llm_process "$process_name"; then
        is_llm_process=true
        echo -e "${GREEN}confirmed LLM process: $process_name${NC}"
    else
        echo -e "${YELLOW}warning: unknown LLM service${NC}"
    fi
    llm_found=true
else
    echo "netstat no network activity on port $port."
fi

# Proceed with process checks and termination
if [[ "$llm_found" == true ]]; then
    if [[ "$is_llm_process" == false ]]; then
        read -p "Process doesn't appear to be an LLM. Are you sure you want to proceed? (y/N) " proceed
        proceed=$(echo "$proceed" | tr '[:upper:]' '[:lower:]')
        if [[ "$proceed" != "y" ]]; then
            echo "Process check cancelled. Continuing with shepherd bootloader control..."
        fi
    fi

    read -p "kill the llama on port $port? (y/N) " confirm
    confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')

    if [[ "$confirm" == "y" ]]; then
        pids=$(sudo lsof -i :$port 2>/dev/null | awk 'NR>1 {print $2}')
        if [[ -n "$pids" ]]; then
            echo "hunting llama process(es) on port $port: $pids"
            sudo kill -9 $pids
            
            # Verify if process was actually killed
            sleep 1  # Give system time to update process list
            if ! sudo lsof -i :$port >/dev/null 2>&1; then
                echo -e "${GREEN}✓ llama Process(es) kill confirmed${NC}"
                echo -e "${GREEN}Port $port is now free${NC}"
            else
                echo -e "${RED}! warning: llama process(es) may still be running${NC}"
                echo -e "${RED}check port $port manually${NC}"
            fi
        else
            echo "no llama process running on port $port via lsof."
        fi
    fi
fi

# Continue with shepherd controls regardless of previous operations
echo -e "${YELLOW}=== Shephard checking system for Ollama process ===${NC}"

# Check for any ollama processes
if pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Found running Ollama process${NC}"
    read -p "Terminate all Ollama processes? (y/N) " kill_all
    if [[ "${kill_all,,}" == "y" ]]; then
        echo -e "${YELLOW}kill all Ollama process...${NC}"
        sudo pkill -9 ollama
        sleep 1
        if ! pgrep -x "ollama" > /dev/null; then
            echo -e "${GREEN}✓ Ollama has been terminated${NC}"
        else
            echo -e "${RED}! warning: Ollama processes may still be running${NC}"
        fi
    fi
fi

# Check systemd service status
if systemctl list-unit-files 2>/dev/null | grep -q ollama; then
    echo -e "${YELLOW}Checking Ollama service status...${NC}"
    if systemctl is-active --quiet ollama 2>/dev/null; then
        read -p "Ollama service is active. Stop it? (y/N) " stop_service
        if [[ "${stop_service,,}" == "y" ]]; then
            sudo systemctl stop ollama
            echo -e "${GREEN}✓ Ollama service stopped${NC}"
        fi
    else
        echo -e "${GREEN}Ollama service is inactive${NC}"
    fi
    
    # Ask about boot behavior
    read -p "Disable Ollama at boot? (y/N) " disable_boot
    if [[ "${disable_boot,,}" == "y" ]]; then
        sudo systemctl disable ollama
        echo -e "${GREEN}✓ Ollama disabled at boot${NC}"
    else
        sudo systemctl enable ollama
        echo -e "${YELLOW}! warning: Ollama runs at boot${NC}"
        echo -e "${YELLOW}! use 'sudo systemctl disable ollama' to disable manually${NC}"
    fi
fi

# Final verification
echo -e "${YELLOW}=== Final System Check ===${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}✓ no Ollama process running${NC}"
else
    echo -e "${RED}! warning: ollama process detected${NC}"
fi

if ! sudo lsof -i :$port >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Port $port is clear${NC}"
else
    echo -e "${RED}! port $port is in use${NC}"
fi

# Additional check for default Ollama port if custom port was used
if [[ "$port" != "11434" ]]; then
    if ! sudo lsof -i :11434 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ default Ollama port 11434 is clear${NC}"
    else
        echo -e "${RED}! warning: Default Ollama port 11434 still in use${NC}"
    fi
fi

echo -e "${YELLOW}=== UFW Ollama Security Configuration ===${NC}"

# Check if UFW is installed
if ! command -v ufw >/dev/null 2>&1; then
    echo -e "${RED}Error: UFW is not installed${NC}"
    echo -e "${YELLOW}Install with: sudo apt install ufw${NC}"
    exit 1
fi

# Check current UFW status
echo -e "${YELLOW}Checking UFW status...${NC}"
if ! sudo ufw status 2>/dev/null | grep -q "Status: active"; then
    read -p "UFW is not active. Enable UFW firewall? (y/N) " enable_ufw
    if [[ "${enable_ufw,,}" == "y" ]]; then
        echo -e "${YELLOW}Enabling UFW...${NC}"
        sudo ufw enable
        sleep 2
    else
        echo -e "${RED}Warning: UFW remains disabled. Ollama ports may be exposed.${NC}"
        read -p "Continue with rule configuration anyway? (y/N) " continue_anyway
        if [[ "${continue_anyway,,}" != "y" ]]; then
            echo -e "${YELLOW}UFW configuration aborted${NC}"
            exit 0
        fi
    fi
fi

echo -e "${YELLOW}Configuring Ollama UFW rules...${NC}"

# Ask about localhost configuration
read -p "Configure Ollama for localhost-only access? (y/N) " configure_localhost
if [[ "${configure_localhost,,}" == "y" ]]; then
    echo -e "${GREEN}Configuring localhost access rules...${NC}"
    
    # Check for existing rules
    existing_rules=$(sudo ufw status 2>/dev/null | grep 11434)
    if [[ -n "$existing_rules" ]]; then
        echo -e "${YELLOW}Existing Ollama port rules found:${NC}"
        echo "$existing_rules"
        read -p "Remove existing rules before continuing? (y/N) " remove_existing
        if [[ "${remove_existing,,}" == "y" ]]; then
            sudo ufw delete allow 11434/tcp >/dev/null 2>&1
            sudo ufw delete deny 11434/tcp >/dev/null 2>&1
            echo -e "${GREEN}✓ Existing rules removed${NC}"
        fi
    fi

    # Allow localhost access
    echo -e "${GREEN}Allowing localhost access to port 11434...${NC}"
    sudo ufw allow in from 127.0.0.1 to any port 11434
    sudo ufw allow out from any to 127.0.0.1 port 11434

    # Block external access
    echo -e "${GREEN}Blocking external access to port 11434...${NC}"
    sudo ufw deny in to any port 11434
    sudo ufw deny out to any port 11434
    
    echo -e "${GREEN}✓ Localhost-only configuration complete${NC}"
else
    read -p "Would you like to allow external access to Ollama? (y/N) " allow_external
    if [[ "${allow_external,,}" == "y" ]]; then
        echo -e "${RED}! Warning: Allowing external access may pose security risks${NC}"
        read -p "Are you sure? (y/N) " confirm_external
        if [[ "${confirm_external,,}" == "y" ]]; then
            sudo ufw allow 11434/tcp
            echo -e "${YELLOW}! External access enabled for Ollama${NC}"
        fi
    else
        echo -e "${GREEN}✓ No changes made to UFW rules${NC}"
    fi
fi

# Verify rules
echo -e "${YELLOW}=== UFW Rules Verification ===${NC}"
sudo ufw status verbose

# Final UFW status message
if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
    echo -e "${GREEN}✓ UFW is active and configured${NC}"
    if [[ "${configure_localhost,,}" == "y" ]]; then
        echo -e "${GREEN}✓ Ollama is restricted to localhost only${NC}"
    fi
else
    echo -e "${RED}! Warning: UFW is not active${NC}"
    echo -e "${YELLOW}! Use 'sudo ufw enable' to activate firewall${NC}"
fi

echo -e "${GREEN}=== UFW Configuration Complete ===${NC}"
#########################################################
echo -e "${YELLOW}=== Ollama Local Access Audit ===${NC}"
# Initialize flags
security_issues=false
external_access_found=false



# Get IP addresses
ip_addresses=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" || true)

# Function to parse and format JSON
format_json() {
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
}

# Test localhost access
echo -e "${YELLOW}Testing localhost:11434/api/tags${NC}"
response=$(curl -s http://localhost:11434/api/tags)
if [ $? -eq 0 ] && [ -n "$response" ]; then
    echo -e "${GREEN}localhost access successful${NC}"
    echo -e "${YELLOW}Available models${NC}"
    format_json "$response"
else
    echo -e "${RED}localhost access failed${NC}"
    security_issues=true
fi

# Test 127.0.0.1 access
echo -e "\n${YELLOW}Testing 127.0.0.1:11434/api/tags${NC}"
response=$(curl -s http://127.0.0.1:11434/api/tags)
if [ $? -eq 0 ] && [ -n "$response" ]; then
    echo -e "${GREEN}loopback access successful${NC}"
else
    echo -e "${RED}loopback access failed${NC}"
    security_issues=true
fi

# Test external IP addresses
echo -e "\n${YELLOW}Testing external IP addresses${NC}"
blocked_count=0
total_ips=0

while IFS= read -r ip; do
    [ -z "$ip" ] && continue
    ((total_ips++))
    echo -e "${YELLOW}Testing $ip:11434/api/tags${NC}"
    response=$(curl -s --connect-timeout 3 http://$ip:11434/api/tags)
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo -e "${RED}warning external IP $ip has access${NC}"
        external_access_found=true
        security_issues=true
    else
        ((blocked_count++))
        echo -e "${GREEN}external IP $ip blocked${NC}"
    fi
done <<< "$ip_addresses"

# UFW status check
ufw_status=$(sudo ufw status verbose 2>/dev/null)
if echo "$ufw_status" | grep -q "11434.*ALLOW IN.*Anywhere"; then
    echo -e "${RED}warning UFW rules allow external access${NC}"
    security_issues=true
elif [ $blocked_count -eq $total_ips ] && [ $total_ips -gt 0 ]; then
    echo -e "${GREEN}all external IPs correctly blocked${NC}"
fi

# Verify Ollama binding
netstat_output=$(sudo netstat -tulpn 2>/dev/null | grep 11434)
if echo "$netstat_output" | grep -q "0.0.0.0:11434"; then
    echo -e "${RED}warning Ollama bound to all interfaces${NC}"
    security_issues=true
elif echo "$netstat_output" | grep -q "127.0.0.1:11434"; then
    echo -e "${GREEN}Ollama correctly bound to localhost${NC}"
fi

# Final security assessment
if [ "$security_issues" = true ]; then
    echo -e "\n${RED}Security Issues Detected${NC}"
    if [ "$external_access_found" = true ]; then
        echo -e "${RED}external IP access detected configure UFW rules${NC}"
    fi
    if echo "$ufw_status" | grep -q "11434.*ALLOW IN.*Anywhere"; then
        echo -e "${RED}UFW rules too permissive${NC}"
    fi
    if echo "$netstat_output" | grep -q "0.0.0.0:11434"; then
        echo -e "${RED}Ollama daemon configuration needs localhost binding${NC}"
    fi
    
    echo -e "\n${YELLOW}Required Actions${NC}"
    if [ "$external_access_found" = true ] || echo "$ufw_status" | grep -q "11434.*ALLOW IN.*Anywhere"; then
        echo -e "${RED}update UFW rules for localhost only${NC}"
    fi
    if echo "$netstat_output" | grep -q "0.0.0.0:11434"; then
        echo -e "${RED}configure Ollama to bind to localhost${NC}"
    fi
else
    echo -e "\n${GREEN}security check passed${NC}"
    echo -e "${GREEN}llama is running inside the firewall restricted to localhost for private interaction${NC}"
fi

echo -e "\n${GREEN}=== Audit Complete ===${NC}"
