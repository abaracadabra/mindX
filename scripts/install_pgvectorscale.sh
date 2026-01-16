#!/bin/bash
# Auto-installer for PostgreSQL with pgvector extension
# Supports Linux Mint and Ubuntu
# For mindX v3 production setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        log_info "Detected OS: $OS $VERSION"
    else
        log_error "Cannot detect OS. This script requires Linux Mint or Ubuntu."
        exit 1
    fi
    
    # Check if it's Ubuntu or Linux Mint
    if [[ "$OS" != "ubuntu" && "$OS" != "linuxmint" ]]; then
        log_warn "OS $OS may not be fully supported. Proceeding anyway..."
    fi
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "Please do not run this script as root. It will use sudo when needed."
        exit 1
    fi
}

# Update package lists
update_packages() {
    log_info "Updating package lists..."
    sudo apt-get update -qq
}

# Install PostgreSQL
install_postgresql() {
    log_info "Checking PostgreSQL installation..."
    
    if command -v psql &> /dev/null; then
        PSQL_VERSION=$(psql --version | grep -oP '\d+' | head -1)
        log_info "PostgreSQL $PSQL_VERSION is already installed"
        
        if [ "$PSQL_VERSION" -lt 14 ]; then
            log_warn "PostgreSQL version $PSQL_VERSION is below recommended version 14"
            log_info "Installing PostgreSQL 15..."
            install_postgresql_15
        else
            log_info "PostgreSQL version is sufficient"
            return 0
        fi
    else
        log_info "PostgreSQL not found. Installing PostgreSQL 15..."
        install_postgresql_15
    fi
}

install_postgresql_15() {
    # Add PostgreSQL APT repository
    log_info "Adding PostgreSQL APT repository..."
    sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
    
    update_packages
    
    # Install PostgreSQL 15 and development packages
    log_info "Installing PostgreSQL 15..."
    sudo apt-get install -y postgresql-15 postgresql-contrib-15 postgresql-server-dev-15
    
    # Start and enable PostgreSQL
    log_info "Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    log_info "PostgreSQL 15 installed successfully"
}

# Install pgvector extension
install_pgvector() {
    log_info "Checking pgvector installation..."
    
    # Check if pgvector is already installed
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw mindx_memory 2>/dev/null; then
        if sudo -u postgres psql -d mindx_memory -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
            log_info "pgvector extension is already installed"
            return 0
        fi
    fi
    
    log_info "Installing pgvector extension..."
    
    # Install build dependencies
    log_info "Installing build dependencies..."
    sudo apt-get install -y build-essential git
    
    # Clone pgvector repository
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    log_info "Cloning pgvector repository..."
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
    cd pgvector
    
    # Build and install
    log_info "Building pgvector..."
    make
    
    log_info "Installing pgvector..."
    sudo make install
    
    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"
    
    log_info "pgvector extension installed successfully"
}

# Create database and user
setup_database() {
    log_info "Setting up mindX memory database..."
    
    # Generate random password if not set
    if [ -z "$MINDX_DB_PASSWORD" ]; then
        MINDX_DB_PASSWORD=$(openssl rand -base64 32)
        log_info "Generated database password (save this!): $MINDX_DB_PASSWORD"
        echo "MINDX_DB_PASSWORD=$MINDX_DB_PASSWORD" | tee -a ~/.env.mindx_db
        log_info "Password saved to ~/.env.mindx_db"
    fi
    
    # Create database user
    log_info "Creating database user 'mindx'..."
    sudo -u postgres psql -c "CREATE USER mindx WITH PASSWORD '$MINDX_DB_PASSWORD';" 2>/dev/null || log_warn "User 'mindx' may already exist"
    
    # Create database
    log_info "Creating database 'mindx_memory'..."
    sudo -u postgres psql -c "CREATE DATABASE mindx_memory OWNER mindx;" 2>/dev/null || log_warn "Database 'mindx_memory' may already exist"
    
    # Grant privileges
    log_info "Granting privileges..."
    sudo -u postgres psql -d mindx_memory -c "GRANT ALL PRIVILEGES ON DATABASE mindx_memory TO mindx;"
    sudo -u postgres psql -d mindx_memory -c "ALTER USER mindx CREATEDB;"
    
    # Enable pgvector extension
    log_info "Enabling pgvector extension..."
    sudo -u postgres psql -d mindx_memory -c "CREATE EXTENSION IF NOT EXISTS vector;"
    
    log_info "Database setup completed"
}

# Test installation
test_installation() {
    log_info "Testing installation..."
    
    # Test PostgreSQL connection
    if sudo -u postgres psql -d mindx_memory -c "SELECT version();" > /dev/null 2>&1; then
        log_info "✓ PostgreSQL connection successful"
    else
        log_error "✗ PostgreSQL connection failed"
        return 1
    fi
    
    # Test pgvector extension
    if sudo -u postgres psql -d mindx_memory -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
        log_info "✓ pgvector extension is enabled"
    else
        log_error "✗ pgvector extension not found"
        return 1
    fi
    
    # Test vector operations
    if sudo -u postgres psql -d mindx_memory -c "SELECT '[1,2,3]'::vector;" > /dev/null 2>&1; then
        log_info "✓ Vector operations working"
    else
        log_error "✗ Vector operations failed"
        return 1
    fi
    
    log_info "All tests passed!"
    return 0
}

# Print connection info
print_connection_info() {
    log_info "Installation Summary:"
    echo ""
    echo "Database: mindx_memory"
    echo "User: mindx"
    echo "Host: localhost"
    echo "Port: 5432"
    echo ""
    if [ -f ~/.env.mindx_db ]; then
        log_info "Password saved in: ~/.env.mindx_db"
        echo "To use the password, add this to your .env file:"
        cat ~/.env.mindx_db
    fi
    echo ""
    log_info "Connection string:"
    echo "postgresql://mindx:PASSWORD@localhost:5432/mindx_memory"
    echo ""
    log_info "Next steps:"
    echo "1. Run: python scripts/setup_memory_db.py"
    echo "2. Update data/config/mindx_config.json with database settings"
    echo "3. Set MINDX_DB_PASSWORD environment variable"
}

# Main execution
main() {
    log_info "Starting pgvectorscale installation for mindX..."
    echo ""
    
    check_root
    detect_os
    update_packages
    install_postgresql
    install_pgvector
    setup_database
    
    if test_installation; then
        log_info "Installation completed successfully!"
        print_connection_info
    else
        log_error "Installation completed with errors. Please check the output above."
        exit 1
    fi
}

# Run main function
main
