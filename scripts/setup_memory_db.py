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