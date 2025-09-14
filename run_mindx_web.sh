#!/bin/bash

# MindX Web UI Runner
# This script starts both the backend API and frontend web interface

echo "🧠 Starting MindX Web Interface..."
echo "=================================="

# Get the directory where the script is located
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_DIR="$SCRIPT_DIR/mindx_backend_service"
FRONTEND_DIR="$SCRIPT_DIR/mindx_frontend_ui"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        print_warning "Killing existing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
        sleep 2
    fi
}

# Check if required directories exist
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    print_error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Check if required files exist
if [ ! -f "$BACKEND_DIR/main_service.py" ]; then
    print_error "Backend service file not found: $BACKEND_DIR/main_service.py"
    exit 1
fi

if [ ! -f "$FRONTEND_DIR/server.js" ]; then
    print_error "Frontend server file not found: $FRONTEND_DIR/server.js"
    exit 1
fi

# Kill any existing processes on our ports
print_status "Checking for existing processes..."
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# Start backend
print_status "Starting MindX Backend API on port $BACKEND_PORT..."
cd "$BACKEND_DIR"
python3 main_service.py &
BACKEND_PID=$!

# Wait for backend to start
print_status "Waiting for backend to initialize..."
sleep 5

# Check if backend is running
if ! check_port $BACKEND_PORT; then
    print_error "Backend failed to start on port $BACKEND_PORT"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

print_success "Backend started successfully (PID: $BACKEND_PID)"

# Start frontend
print_status "Starting MindX Frontend on port $FRONTEND_PORT..."
cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    npm install --silent
fi

# Start frontend server
node server.js &
FRONTEND_PID=$!

# Wait for frontend to start
print_status "Waiting for frontend to initialize..."
sleep 3

# Check if frontend is running
if ! check_port $FRONTEND_PORT; then
    print_error "Frontend failed to start on port $FRONTEND_PORT"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 1
fi

print_success "Frontend started successfully (PID: $FRONTEND_PID)"

# Display access information
echo ""
echo "🎉 MindX Web Interface is now running!"
echo "======================================"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend API: http://localhost:$BACKEND_PORT"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Function to cleanup on exit
cleanup() {
    print_status "Shutting down MindX Web Interface..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    print_success "Shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait
