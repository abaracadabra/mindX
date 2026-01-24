#!/usr/bin/env python3
"""
Memory Migration Script
Migrates existing JSON memory files to PostgreSQL with pgvector for semantic search.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import setup_logging, get_logger
from agents.memory_agent import MemoryType, MemoryImportance

setup_logging()
logger = get_logger(__name__)

class MemoryMigrator:
    """Migrates memory files to PostgreSQL with embeddings"""

    def __init__(self):
        self.config = Config()
        self.memory_dir = PROJECT_ROOT / "data" / "memory"
        self.db_config = None
        self.connection_pool = None

        # Set up database password
        os.environ["MINDX_DB_PASSWORD"] = "mindx_password_2024_secure"

    async def setup_database(self):
        """Set up database connection"""
        try:
            import psycopg2
            import psycopg2.pool
            from pgvector.psycopg2 import register_vector

            # Database configuration
            self.db_config = {
                "host": "localhost",
                "port": 5432,
                "database": "mindx_memory",
                "user": "mindx",
                "password": "mindx_password_2024_secure"
            }

            # Create connection pool
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **self.db_config
            )

            # Test connection and register vector extension
            conn = self.connection_pool.getconn()
            register_vector(conn)
            self.connection_pool.putconn(conn)

            logger.info("Database connection established")
            return True

        except ImportError as e:
            logger.error(f"Missing required packages: {e}")
            logger.error("Install with: pip install psycopg2-binary pgvector sentence-transformers")
            return False
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            return False

    async def setup_embeddings(self):
        """Set up sentence transformer for embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded")
            return True
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            return False
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return False

    def find_memory_files(self) -> List[Path]:
        """Find all memory JSON files"""
        memory_files = []

        # Check both STM and LTM directories
        for memory_type in ["stm", "ltm"]:
            type_dir = self.memory_dir / memory_type
            if type_dir.exists():
                # Find all JSON files recursively
                for json_file in type_dir.rglob("*.json"):
                    memory_files.append(json_file)

        logger.info(f"Found {len(memory_files)} memory files")
        return memory_files

    def parse_memory_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse a memory JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different memory file formats
            memories = []

            if isinstance(data, list):
                memories = data
            elif isinstance(data, dict):
                # Single memory object
                memories = [data]
            else:
                logger.warning(f"Unexpected data format in {file_path}")
                return []

            # Validate and clean memory records
            valid_memories = []
            for memory in memories:
                if self.validate_memory_record(memory):
                    # Add metadata
                    memory['_source_file'] = str(file_path.relative_to(PROJECT_ROOT))
                    memory['_migrated_at'] = datetime.now().isoformat()
                    valid_memories.append(memory)

            return valid_memories

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []

    def validate_memory_record(self, memory: Dict[str, Any]) -> bool:
        """Validate memory record structure"""
        required_fields = ['agent_id', 'memory_type', 'timestamp', 'content']

        for field in required_fields:
            if field not in memory:
                logger.warning(f"Memory record missing required field: {field}")
                return False

        # Validate memory type
        if memory['memory_type'] not in [mt.value for mt in MemoryType]:
            logger.warning(f"Invalid memory type: {memory['memory_type']}")
            return False

        return True

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        try:
            if not hasattr(self, 'embedding_model'):
                return None

            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def extract_text_for_embedding(self, memory: Dict[str, Any]) -> str:
        """Extract text content for embedding generation"""
        content = memory.get('content', {})

        # Combine different content fields
        text_parts = []

        if isinstance(content, dict):
            # Extract meaningful text from content
            for key, value in content.items():
                if isinstance(value, str) and len(value.strip()) > 0:
                    text_parts.append(f"{key}: {value}")
                elif isinstance(value, (int, float)):
                    text_parts.append(f"{key}: {value}")
        elif isinstance(content, str):
            text_parts.append(content)

        # Add context if available
        context = memory.get('context')
        if context and isinstance(context, str):
            text_parts.append(f"context: {context}")

        # Add tags if available
        tags = memory.get('tags', [])
        if tags:
            text_parts.append(f"tags: {', '.join(tags)}")

        return " | ".join(text_parts)

    async def migrate_memory_record(self, memory: Dict[str, Any]) -> bool:
        """Migrate a single memory record to PostgreSQL"""
        try:
            conn = self.connection_pool.getconn()

            # Generate memory ID if not present
            memory_id = memory.get('memory_id')
            if not memory_id:
                import uuid
                memory_id = str(uuid.uuid4())
                memory['memory_id'] = memory_id

            # Prepare data for insertion
            agent_id = memory['agent_id']
            memory_type = memory['memory_type']
            importance = memory.get('importance', MemoryImportance.MEDIUM.value)
            timestamp = memory['timestamp']
            content = json.dumps(memory['content'])
            context = json.dumps(memory.get('context')) if memory.get('context') else None
            tags = memory.get('tags', [])

            # Insert memory record
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO memories (
                        memory_id, agent_id, memory_type, importance,
                        timestamp, content, context, tags
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (memory_id) DO NOTHING
                """, (
                    memory_id, agent_id, memory_type, importance,
                    timestamp, content, context, tags
                ))

                # Generate and store embedding
                text_content = self.extract_text_for_embedding(memory)
                if text_content.strip():
                    embedding = self.generate_embedding(text_content)
                    if embedding:
                        cursor.execute("""
                            INSERT INTO memory_embeddings (
                                memory_id, embedding, text_content
                            ) VALUES (%s, %s, %s)
                            ON CONFLICT (memory_id) DO NOTHING
                        """, (memory_id, embedding, text_content))

            conn.commit()
            self.connection_pool.putconn(conn)
            return True

        except Exception as e:
            logger.error(f"Failed to migrate memory record: {e}")
            if conn:
                self.connection_pool.putconn(conn)
            return False

    async def migrate_all_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate all memory files to PostgreSQL"""
        logger.info("Starting memory migration...")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made to database")

        # Setup
        if not await self.setup_database():
            return {"success": False, "error": "Database setup failed"}

        if not await self.setup_embeddings():
            return {"success": False, "error": "Embedding setup failed"}

        # Find memory files
        memory_files = self.find_memory_files()
        if not memory_files:
            return {"success": False, "error": "No memory files found"}

        # Migrate memories
        total_memories = 0
        migrated_memories = 0
        failed_memories = 0

        for file_path in memory_files:
            logger.info(f"Processing {file_path}")

            memories = self.parse_memory_file(file_path)
            total_memories += len(memories)

            for memory in memories:
                if dry_run:
                    logger.info(f"DRY RUN: Would migrate memory {memory.get('memory_id', 'unknown')}")
                    migrated_memories += 1
                else:
                    if await self.migrate_memory_record(memory):
                        migrated_memories += 1
                    else:
                        failed_memories += 1

        # Clean up
        if self.connection_pool:
            self.connection_pool.closeall()

        result = {
            "success": True,
            "total_files": len(memory_files),
            "total_memories": total_memories,
            "migrated_memories": migrated_memories,
            "failed_memories": failed_memories,
            "dry_run": dry_run
        }

        logger.info(f"Migration completed: {result}")
        return result

async def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate mindX memories to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    migrator = MemoryMigrator()
    result = await migrator.migrate_all_memories(dry_run=args.dry_run)

    if result["success"]:
        print("✅ Memory migration completed successfully!")
        print(f"Files processed: {result['total_files']}")
        print(f"Memories found: {result['total_memories']}")
        print(f"Memories migrated: {result['migrated_memories']}")
        if result['failed_memories'] > 0:
            print(f"Memories failed: {result['failed_memories']}")

        if result.get('dry_run'):
            print("\nThis was a dry run. Run without --dry-run to perform actual migration.")
    else:
        print(f"❌ Migration failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())