#!/bin/bash

# pgvectorscale Memory Integration Auto-Installer
# Installs PostgreSQL 15+ with pgvector extension for semantic memory storage
# Compatible with Linux Mint and Ubuntu VPS deployments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS and version
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        log_info "Detected OS: $OS $VERSION"
    else
        log_error "Cannot detect OS. This script requires Linux Mint or Ubuntu."
        exit 1
    fi

    # Check for supported OS
    case $OS in
        "ubuntu"|"linuxmint"|"pop"|"elementary")
            log_success "Supported OS detected: $OS $VERSION"
            ;;
        *)
            log_error "Unsupported OS: $OS. This script supports Ubuntu, Linux Mint, Pop!_OS, and elementary OS."
            exit 1
            ;;
    esac
}

# Install PostgreSQL
install_postgresql() {
    log_info "Installing PostgreSQL..."

    # Update package lists
    sudo apt-get update

    # Install PostgreSQL
    case $OS in
        "ubuntu")
            if [[ $VERSION == "20.04" ]]; then
                sudo apt-get install -y postgresql-13 postgresql-contrib-13
                PG_VERSION="13"
            elif [[ $VERSION == "22.04" ]]; then
                sudo apt-get install -y postgresql-14 postgresql-contrib-14
                PG_VERSION="14"
            elif [[ $VERSION == "24.04" ]]; then
                sudo apt-get install -y postgresql-16 postgresql-contrib-16
                PG_VERSION="16"
            else
                sudo apt-get install -y postgresql postgresql-contrib
                PG_VERSION=$(pg_config --version | grep -oP '\d+\.\d+' | cut -d. -f1)
            fi
            ;;
        "linuxmint")
            # Linux Mint uses Ubuntu repositories
            UBUNTU_CODENAME=$(lsb_release -c | cut -f2)
            case $UBUNTU_CODENAME in
                "focal")
                    sudo apt-get install -y postgresql-13 postgresql-contrib-13
                    PG_VERSION="13"
                    ;;
                "jammy")
                    sudo apt-get install -y postgresql-14 postgresql-contrib-14
                    PG_VERSION="14"
                    ;;
                "noble")
                    sudo apt-get install -y postgresql-16 postgresql-contrib-16
                    PG_VERSION="16"
                    ;;
                *)
                    sudo apt-get install -y postgresql postgresql-contrib
                    PG_VERSION=$(pg_config --version | grep -oP '\d+\.\d+' | cut -d. -f1)
                    ;;
            esac
            ;;
        *)
            sudo apt-get install -y postgresql postgresql-contrib
            PG_VERSION=$(pg_config --version | grep -oP '\d+\.\d+' | cut -d. -f1)
            ;;
    esac

    log_success "PostgreSQL $PG_VERSION installed"
}

# Install pgvector extension
install_pgvector() {
    log_info "Installing pgvector extension..."

    # Install build dependencies
    sudo apt-get install -y build-essential postgresql-server-dev-$PG_VERSION git

    # Clone and build pgvector
    cd /tmp
    if [[ ! -d "pgvector" ]]; then
        git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
    fi
    cd pgvector

    # Build and install
    make
    sudo make install

    log_success "pgvector extension installed"
}

# Create mindx_memory database and user
setup_database() {
    log_info "Setting up mindx_memory database..."

    # Create mindx user and database
    sudo -u postgres psql -c "CREATE USER mindx WITH PASSWORD 'mindx_password_2024_secure';"
    sudo -u postgres psql -c "CREATE DATABASE mindx_memory OWNER mindx;"
    sudo -u postgres psql -c "ALTER USER mindx CREATEDB;"

    # Grant permissions
    sudo -u postgres psql -d mindx_memory -c "GRANT ALL PRIVILEGES ON DATABASE mindx_memory TO mindx;"

    # Enable pgvector extension
    sudo -u postgres psql -d mindx_memory -c "CREATE EXTENSION IF NOT EXISTS vector;"

    # Create schema
    sudo -u postgres psql -d mindx_memory << 'EOF'
-- Main memories table
CREATE TABLE memories (
    memory_id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    importance INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    content JSONB NOT NULL,
    context JSONB,
    tags TEXT[],
    parent_memory_id VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector embeddings table
CREATE TABLE memory_embeddings (
    memory_id VARCHAR(64) PRIMARY KEY REFERENCES memories(memory_id) ON DELETE CASCADE,
    embedding vector(384),  -- Using all-MiniLM-L6-v2 dimensions
    text_content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Resource metrics storage
CREATE TABLE resource_metrics (
    metric_id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255),
    timestamp TIMESTAMPTZ NOT NULL,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    process_count INTEGER,
    metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory relationships for context threading
CREATE TABLE memory_relationships (
    relationship_id SERIAL PRIMARY KEY,
    parent_memory_id VARCHAR(64) REFERENCES memories(memory_id),
    child_memory_id VARCHAR(64) REFERENCES memories(memory_id),
    relationship_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_memories_agent_timestamp ON memories(agent_id, timestamp DESC);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_embeddings_vector ON memory_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_resource_metrics_agent_time ON resource_metrics(agent_id, timestamp DESC);
EOF

    log_success "Database and schema created successfully"
}

# Configure PostgreSQL for production
configure_postgresql() {
    log_info "Configuring PostgreSQL for production..."

    # Update postgresql.conf
    PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    sudo cp "$PG_CONF" "$PG_CONF.backup"

    # Add performance settings
    sudo tee -a "$PG_CONF" > /dev/null << EOF

# pgvectorscale Memory Integration Settings
# Performance tuning for vector operations and memory storage

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100

# Logging
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'ddl'

# Autovacuum settings for better performance
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 20s
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.02
autovacuum_analyze_scale_factor = 0.01

# pgvector specific settings
# Increase work_mem for vector operations
work_mem = 16MB
EOF

    # Update pg_hba.conf for local connections
    PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    sudo cp "$PG_HBA" "$PG_HBA.backup"

    # Add mindx user access
    echo "local   mindx_memory    mindx                                   md5" | sudo tee -a "$PG_HBA" > /dev/null
    echo "host    mindx_memory    mindx           127.0.0.1/32           md5" | sudo tee -a "$PG_HBA" > /dev/null
    echo "host    mindx_memory    mindx           ::1/128                 md5" | sudo tee -a "$PG_HBA" > /dev/null

    log_success "PostgreSQL configured"
}

# Test installation
test_installation() {
    log_info "Testing installation..."

    # Test database connection
    PGPASSWORD="mindx_password_2024_secure" psql -h localhost -U mindx -d mindx_memory -c "SELECT version();" > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        log_success "Database connection test passed"
    else
        log_error "Database connection test failed"
        exit 1
    fi

    # Test pgvector extension
    PGPASSWORD="mindx_password_2024_secure" psql -h localhost -U mindx -d mindx_memory -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep -q "vector"
    if [[ $? -eq 0 ]]; then
        log_success "pgvector extension test passed"
    else
        log_error "pgvector extension test failed"
        exit 1
    fi

    # Test vector operations
    PGPASSWORD="mindx_password_2024_secure" psql -h localhost -U mindx -d mindx_memory -c "
    CREATE TEMP TABLE test_vectors (id SERIAL, embedding vector(3));
    INSERT INTO test_vectors (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
    SELECT embedding <=> '[3,3,3]' AS distance FROM test_vectors ORDER BY distance LIMIT 1;
    " > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        log_success "Vector operations test passed"
    else
        log_error "Vector operations test failed"
        exit 1
    fi

    log_success "All tests passed! pgvectorscale is ready for mindX memory integration."
}

# Create Python setup script
create_setup_script() {
    log_info "Creating Python setup script..."

    cat > /tmp/setup_memory_db.py << 'EOF'
#!/usr/bin/env python3
"""
pgvectorscale Memory Database Setup Script
Initializes database schema and connection pool configuration.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

def update_config():
    """Update mindx config with pgvectorscale settings"""

    config = Config()

    # Add memory configuration
    memory_config = {
        "storage_backend": "postgresql",
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "database": "mindx_memory",
            "user": "mindx",
            "password_env": "MINDX_DB_PASSWORD",
            "pool_size": 10,
            "max_overflow": 20
        },
        "embeddings": {
            "model": "all-MiniLM-L6-v2",
            "dimensions": 384,
            "device": "cpu"
        },
        "vector_search": {
            "default_limit": 10,
            "min_similarity": 0.5,
            "index_type": "ivfflat"
        },
        "resource_integration": {
            "auto_store_metrics": True,
            "store_interval_seconds": 60,
            "correlation_window_days": 7
        }
    }

    # Update config
    config.set("memory", memory_config)

    # Set environment variable for database password
    os.environ["MINDX_DB_PASSWORD"] = "mindx_password_2024_secure"

    logger.info("Configuration updated with pgvectorscale settings")
    return True

def test_connection():
    """Test database connection"""
    try:
        import psycopg2
        import psycopg2.pool

        # Test connection
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="mindx_memory",
            user="mindx",
            password="mindx_password_2024_secure"
        )

        # Test pgvector
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            if cursor.fetchone():
                logger.info("pgvector extension verified")
            else:
                raise Exception("pgvector extension not found")

        conn.close()
        logger.info("Database connection test successful")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("Setting up pgvectorscale memory database configuration...")

    if update_config() and test_connection():
        print("✅ pgvectorscale setup completed successfully!")
        print("\nNext steps:")
        print("1. Run: pip install psycopg2-binary pgvector sentence-transformers")
        print("2. Restart mindX backend service")
        print("3. Run memory migration script: python scripts/migrate_memories_to_postgres.py")
    else:
        print("❌ Setup failed!")
        sys.exit(1)
EOF

    chmod +x /tmp/setup_memory_db.py
    sudo mv /tmp/setup_memory_db.py /usr/local/bin/setup_memory_db.py
    log_success "Python setup script created at /usr/local/bin/setup_memory_db.py"
}

# Main installation function
main() {
    log_info "Starting pgvectorscale Memory Integration Installation"
    log_info "This will install PostgreSQL with pgvector extension for semantic memory storage"

    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run with sudo if needed."
        exit 1
    fi

    # Detect OS
    detect_os

    # Install components
    install_postgresql
    install_pgvector
    setup_database
    configure_postgresql

    # Create setup script
    create_setup_script

    # Restart PostgreSQL
    log_info "Restarting PostgreSQL service..."
    sudo systemctl restart postgresql

    # Test installation
    test_installation

    # Final success message
    log_success "🎉 pgvectorscale Memory Integration installation completed!"
    echo ""
    echo "Installation Summary:"
    echo "  ✅ PostgreSQL $PG_VERSION installed"
    echo "  ✅ pgvector extension installed"
    echo "  ✅ mindx_memory database created"
    echo "  ✅ Schema and indexes created"
    echo "  ✅ Production configuration applied"
    echo ""
    echo "Next steps:"
    echo "1. Run: sudo setup_memory_db.py"
    echo "2. Install Python dependencies: pip install psycopg2-binary pgvector sentence-transformers asyncpg"
    echo "3. Update your mindx_config.json with database settings"
    echo "4. Run memory migration: python scripts/migrate_memories_to_postgres.py"
    echo ""
    echo "Database credentials:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: mindx_memory"
    echo "  User: mindx"
    echo "  Password: mindx_password_2024_secure (set MINDX_DB_PASSWORD env var)"
}

# Run main function
main "$@"