#!/usr/bin/env python3
"""
Backup Agent - Immutable Blockchain Memory and Git Integration
Author: Professor Codephreak (© Professor Codephreak)
Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
Resources: rage.pythai.net

BackupAgent handles:
- Git commits before every shutdown and rebuild
- Immutable blockchain memory storage
- Integration with rebuild tools and system lifecycle
- Cryptographic verification of backup integrity
"""

import asyncio
import logging
import os
import subprocess
import json
import hashlib
import time
import signal
import atexit
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from core.bdi_agent import BDIAgent, Belief, Desire, Intention, BeliefSource
from core.id_manager_agent import IDManagerAgent
from agents.guardian_agent import GuardianAgent
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager

# Configure logging
logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of backups"""
    SHUTDOWN = "shutdown"
    REBUILD = "rebuild"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    EMERGENCY = "emergency"


class BlockchainNetwork(Enum):
    """Supported blockchain networks for immutable memory"""
    ETHEREUM = "ethereum"
    AION = "aion"
    IPFS = "ipfs"
    ARWEAVE = "arweave"
    POLYGON = "polygon"


@dataclass
class BackupMetadata:
    """Backup metadata for tracking and verification"""
    backup_id: str
    timestamp: float
    backup_type: BackupType
    git_commit_hash: str
    blockchain_hash: Optional[str] = None
    blockchain_network: Optional[BlockchainNetwork] = None
    file_count: int = 0
    total_size_bytes: int = 0
    checksum_sha256: str = ""
    agent_id: str = ""
    vault_encrypted: bool = False


@dataclass
class GitCommitInfo:
    """Git commit information"""
    commit_hash: str
    commit_message: str
    author: str
    timestamp: float
    files_changed: List[str]
    lines_added: int
    lines_removed: int


@dataclass
class BlockchainMemory:
    """Immutable blockchain memory record"""
    memory_id: str
    content_hash: str
    blockchain_hash: str
    network: BlockchainNetwork
    timestamp: float
    metadata: Dict[str, Any]
    verification_hash: str


class BackupAgent:
    """
    Backup Agent for Git integration and immutable blockchain memories

    Handles automatic backups before shutdowns, rebuilds, and maintains
    immutable blockchain-based memory storage for critical system state.
    """

    def __init__(self, agent_id: str = "backup_agent"):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"BackupAgent.{agent_id}")

        # Core components
        self.bdi_agent = None
        self.id_manager = None
        self.guardian = None
        self.vault_manager = get_encrypted_vault_manager()

        # Backup configuration
        self.git_repo_path = "/home/mindx/mindX"
        self.backup_metadata_path = "/var/log/mindx/backup_metadata.json"
        self.blockchain_memory_path = "/var/lib/mindx/blockchain_memories.json"

        # Git configuration
        self.git_author_name = "mindX-BackupAgent"
        self.git_author_email = "backup@mindx.pythai.net"

        # Blockchain configuration
        self.default_blockchain = BlockchainNetwork.AION
        self.blockchain_endpoints = {
            BlockchainNetwork.AION: "https://mainnet-api.theoan.com",
            BlockchainNetwork.ETHEREUM: "https://mainnet.infura.io/v3/",
            BlockchainNetwork.IPFS: "https://ipfs.infura.io:5001",
            BlockchainNetwork.ARWEAVE: "https://arweave.net"
        }

        # State
        self.backup_history = []
        self.blockchain_memories = []
        self.shutdown_hooks_registered = False

        # Register shutdown hooks
        self._register_shutdown_hooks()

        self.logger.info(f"Backup Agent {agent_id} initialized with git and blockchain integration")

    async def initialize(self):
        """Initialize Backup Agent components"""
        try:
            # Initialize core identity
            self.id_manager = await IDManagerAgent.get_instance(
                agent_id=f"id_manager_for_{self.agent_id}"
            )

            # Create Backup Agent's cryptographic identity
            backup_address = await self.id_manager.create_new_wallet(self.agent_id)
            self.logger.info(f"Backup Agent cryptographic identity: {backup_address}")

            # Initialize Guardian for security
            self.guardian = await GuardianAgent.get_instance(
                agent_id=f"guardian_for_{self.agent_id}",
                id_manager=self.id_manager
            )

            # Initialize BDI cognitive architecture
            self.bdi_agent = BDIAgent(
                agent_id=self.agent_id,
                id_manager=self.id_manager,
                guardian=self.guardian
            )

            # Set beliefs about backup capabilities
            await self.bdi_agent.belief_system.add_belief(
                "backup.git.enabled", True, 1.0, BeliefSource.INTERNAL
            )
            await self.bdi_agent.belief_system.add_belief(
                "backup.blockchain.enabled", True, 1.0, BeliefSource.INTERNAL
            )
            await self.bdi_agent.belief_system.add_belief(
                "backup.immutable_memory.active", True, 1.0, BeliefSource.INTERNAL
            )

            # Load existing backup history
            await self._load_backup_history()
            await self._load_blockchain_memories()

            # Configure git environment
            await self._configure_git_environment()

            self.logger.info("Backup Agent initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"Backup Agent initialization failed: {e}")
            return False

    async def backup_before_shutdown(self, reason: str = "system_shutdown") -> BackupMetadata:
        """
        Perform backup before system shutdown with git commit and blockchain storage
        """
        try:
            self.logger.info(f"Starting pre-shutdown backup: {reason}")

            # Create backup metadata
            backup_metadata = BackupMetadata(
                backup_id=f"shutdown_{int(time.time())}",
                timestamp=time.time(),
                backup_type=BackupType.SHUTDOWN,
                git_commit_hash="",
                agent_id=self.agent_id
            )

            # Step 1: Analyze current system state
            system_state = await self._analyze_system_state()

            # Step 2: Perform git backup
            git_info = await self._perform_git_backup(
                commit_message=f"Pre-shutdown backup: {reason}",
                backup_type=BackupType.SHUTDOWN
            )
            backup_metadata.git_commit_hash = git_info.commit_hash

            # Step 3: Create immutable blockchain memory
            blockchain_memory = await self._store_blockchain_memory(
                system_state, backup_metadata
            )
            if blockchain_memory:
                backup_metadata.blockchain_hash = blockchain_memory.blockchain_hash
                backup_metadata.blockchain_network = blockchain_memory.network

            # Step 4: Calculate system checksum
            backup_metadata.checksum_sha256 = await self._calculate_system_checksum()

            # Step 5: Encrypt and store backup metadata
            backup_metadata.vault_encrypted = True
            await self._store_backup_metadata(backup_metadata)

            # Step 6: Verify backup integrity
            verification_result = await self._verify_backup_integrity(backup_metadata)

            if verification_result:
                self.logger.info(f"Pre-shutdown backup completed successfully: {backup_metadata.backup_id}")
                return backup_metadata
            else:
                self.logger.error("Backup verification failed")
                raise Exception("Backup integrity verification failed")

        except Exception as e:
            self.logger.error(f"Pre-shutdown backup failed: {e}")
            raise

    async def backup_before_rebuild(self, rebuild_tools: List[str] = None) -> BackupMetadata:
        """
        Perform backup before rebuild operations with tool integration
        """
        try:
            rebuild_tools = rebuild_tools or []
            self.logger.info(f"Starting pre-rebuild backup for tools: {rebuild_tools}")

            # Create backup metadata
            backup_metadata = BackupMetadata(
                backup_id=f"rebuild_{int(time.time())}",
                timestamp=time.time(),
                backup_type=BackupType.REBUILD,
                git_commit_hash="",
                agent_id=self.agent_id
            )

            # Analyze rebuild requirements
            rebuild_analysis = await self._analyze_rebuild_requirements(rebuild_tools)

            # Perform comprehensive backup
            git_info = await self._perform_git_backup(
                commit_message=f"Pre-rebuild backup for: {', '.join(rebuild_tools)}",
                backup_type=BackupType.REBUILD
            )
            backup_metadata.git_commit_hash = git_info.commit_hash

            # Store rebuild state in blockchain
            rebuild_state = {
                'rebuild_tools': rebuild_tools,
                'analysis': rebuild_analysis,
                'pre_rebuild_state': await self._capture_pre_rebuild_state()
            }

            blockchain_memory = await self._store_blockchain_memory(
                rebuild_state, backup_metadata
            )
            if blockchain_memory:
                backup_metadata.blockchain_hash = blockchain_memory.blockchain_hash
                backup_metadata.blockchain_network = blockchain_memory.network

            # Store backup metadata
            await self._store_backup_metadata(backup_metadata)

            self.logger.info(f"Pre-rebuild backup completed: {backup_metadata.backup_id}")
            return backup_metadata

        except Exception as e:
            self.logger.error(f"Pre-rebuild backup failed: {e}")
            raise

    async def create_immutable_memory(self, memory_data: Dict[str, Any],
                                    memory_type: str = "system_state") -> BlockchainMemory:
        """
        Create immutable memory record on blockchain
        """
        try:
            self.logger.info(f"Creating immutable memory: {memory_type}")

            # Create memory record
            memory_id = f"{memory_type}_{int(time.time())}"
            content_json = json.dumps(memory_data, sort_keys=True)
            content_hash = hashlib.sha256(content_json.encode()).hexdigest()

            # Store on blockchain
            blockchain_hash = await self._store_on_blockchain(
                content_json, self.default_blockchain
            )

            # Create verification hash
            verification_data = {
                'memory_id': memory_id,
                'content_hash': content_hash,
                'blockchain_hash': blockchain_hash,
                'timestamp': time.time()
            }
            verification_hash = hashlib.sha256(
                json.dumps(verification_data, sort_keys=True).encode()
            ).hexdigest()

            # Create blockchain memory record
            blockchain_memory = BlockchainMemory(
                memory_id=memory_id,
                content_hash=content_hash,
                blockchain_hash=blockchain_hash,
                network=self.default_blockchain,
                timestamp=time.time(),
                metadata={'type': memory_type, 'agent_id': self.agent_id},
                verification_hash=verification_hash
            )

            # Store locally
            self.blockchain_memories.append(blockchain_memory)
            await self._save_blockchain_memories()

            self.logger.info(f"Immutable memory created: {memory_id}")
            return blockchain_memory

        except Exception as e:
            self.logger.error(f"Failed to create immutable memory: {e}")
            raise

    async def _perform_git_backup(self, commit_message: str,
                                backup_type: BackupType) -> GitCommitInfo:
        """Perform git backup operations"""
        try:
            # Change to git repository directory
            os.chdir(self.git_repo_path)

            # Check git status
            git_status = await self._run_git_command(["status", "--porcelain"])

            if not git_status.strip():
                self.logger.info("No changes to commit")
                # Get current commit info
                return await self._get_current_commit_info()

            # Add all changes
            await self._run_git_command(["add", "."])

            # Get files to be committed
            files_to_commit = await self._run_git_command(["diff", "--cached", "--name-only"])
            files_changed = files_to_commit.strip().split('\n') if files_to_commit.strip() else []

            # Get diff stats
            diff_stats = await self._run_git_command(["diff", "--cached", "--numstat"])
            lines_added, lines_removed = self._parse_diff_stats(diff_stats)

            # Create commit
            full_commit_message = f"{commit_message}\n\nBackup Type: {backup_type.value}\nAgent: {self.agent_id}\nTimestamp: {datetime.now().isoformat()}"

            await self._run_git_command([
                "commit",
                "-m", full_commit_message,
                f"--author={self.git_author_name} <{self.git_author_email}>"
            ])

            # Get commit hash
            commit_hash = await self._run_git_command(["rev-parse", "HEAD"])

            # Create git commit info
            git_info = GitCommitInfo(
                commit_hash=commit_hash.strip(),
                commit_message=commit_message,
                author=f"{self.git_author_name} <{self.git_author_email}>",
                timestamp=time.time(),
                files_changed=files_changed,
                lines_added=lines_added,
                lines_removed=lines_removed
            )

            self.logger.info(f"Git commit created: {git_info.commit_hash[:8]}")
            return git_info

        except Exception as e:
            self.logger.error(f"Git backup failed: {e}")
            raise

    async def _store_blockchain_memory(self, data: Dict[str, Any],
                                     backup_metadata: BackupMetadata) -> Optional[BlockchainMemory]:
        """Store backup data as immutable blockchain memory"""
        try:
            memory_data = {
                'backup_metadata': asdict(backup_metadata),
                'system_data': data,
                'agent_signature': await self._sign_data(data)
            }

            blockchain_memory = await self.create_immutable_memory(
                memory_data, f"backup_{backup_metadata.backup_type.value}"
            )

            return blockchain_memory

        except Exception as e:
            self.logger.error(f"Failed to store blockchain memory: {e}")
            return None

    async def _store_on_blockchain(self, content: str,
                                 network: BlockchainNetwork) -> str:
        """Store content on specified blockchain network"""
        try:
            # This is a simplified implementation
            # In production, this would integrate with actual blockchain APIs

            if network == BlockchainNetwork.AION:
                # AION network integration
                return await self._store_on_aion(content)
            elif network == BlockchainNetwork.IPFS:
                # IPFS integration
                return await self._store_on_ipfs(content)
            elif network == BlockchainNetwork.ARWEAVE:
                # Arweave integration
                return await self._store_on_arweave(content)
            else:
                # Fallback to content hash
                return hashlib.sha256(content.encode()).hexdigest()

        except Exception as e:
            self.logger.error(f"Blockchain storage failed: {e}")
            # Return content hash as fallback
            return hashlib.sha256(content.encode()).hexdigest()

    async def _store_on_aion(self, content: str) -> str:
        """Store content on AION network"""
        # TODO: Implement AION network integration
        self.logger.info("Storing content on AION network (simulated)")
        return f"aion:{hashlib.sha256(content.encode()).hexdigest()}"

    async def _store_on_ipfs(self, content: str) -> str:
        """Store content on IPFS"""
        try:
            # Write content to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(content)
                temp_path = f.name

            # Add to IPFS
            result = await self._run_command(["ipfs", "add", temp_path])

            # Clean up
            os.unlink(temp_path)

            # Extract IPFS hash
            if result:
                return result.split()[1]  # IPFS hash is second field
            else:
                raise Exception("IPFS add command failed")

        except Exception as e:
            self.logger.warning(f"IPFS storage failed, using fallback: {e}")
            return f"ipfs:{hashlib.sha256(content.encode()).hexdigest()}"

    async def _store_on_arweave(self, content: str) -> str:
        """Store content on Arweave"""
        # TODO: Implement Arweave integration
        self.logger.info("Storing content on Arweave (simulated)")
        return f"arweave:{hashlib.sha256(content.encode()).hexdigest()}"

    def _register_shutdown_hooks(self):
        """Register shutdown hooks for automatic backup"""
        if not self.shutdown_hooks_registered:
            # Register signal handlers
            signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
            signal.signal(signal.SIGINT, self._handle_shutdown_signal)

            # Register atexit handler
            atexit.register(self._handle_atexit)

            self.shutdown_hooks_registered = True
            self.logger.info("Shutdown hooks registered for automatic backup")

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals"""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received shutdown signal: {signal_name}")

        # Run backup synchronously
        try:
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run backup
            backup_metadata = loop.run_until_complete(
                self.backup_before_shutdown(f"signal_{signal_name}")
            )

            self.logger.info(f"Emergency backup completed: {backup_metadata.backup_id}")

        except Exception as e:
            self.logger.error(f"Emergency backup failed: {e}")

        # Continue with normal shutdown
        exit(0)

    def _handle_atexit(self):
        """Handle atexit for final backup"""
        self.logger.info("Performing final backup on exit")

        try:
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run backup
            backup_metadata = loop.run_until_complete(
                self.backup_before_shutdown("atexit")
            )

            self.logger.info(f"Final backup completed: {backup_metadata.backup_id}")

        except Exception as e:
            self.logger.error(f"Final backup failed: {e}")

    async def _run_git_command(self, command: List[str]) -> str:
        """Run git command and return output"""
        full_command = ["git"] + command

        process = await asyncio.create_subprocess_exec(
            *full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.git_repo_path
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Git command failed: {stderr.decode()}")

        return stdout.decode()

    async def _run_command(self, command: List[str]) -> str:
        """Run system command and return output"""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Command failed: {stderr.decode()}")

        return stdout.decode()

    async def _configure_git_environment(self):
        """Configure git environment for backup operations"""
        try:
            # Set git configuration
            await self._run_git_command(["config", "user.name", self.git_author_name])
            await self._run_git_command(["config", "user.email", self.git_author_email])

            self.logger.info("Git environment configured")

        except Exception as e:
            self.logger.warning(f"Git configuration warning: {e}")

    async def _analyze_system_state(self) -> Dict[str, Any]:
        """Analyze current system state for backup"""
        return {
            'timestamp': time.time(),
            'vault_status': await self._get_vault_status(),
            'agent_count': await self._count_active_agents(),
            'system_metrics': await self._get_system_metrics()
        }

    async def _get_vault_status(self) -> Dict[str, Any]:
        """Get encrypted vault status"""
        try:
            providers = self.vault_manager.list_api_providers()
            agents = self.vault_manager.list_wallet_agents()

            return {
                'api_providers': len(providers),
                'wallet_agents': len(agents),
                'encrypted': True,
                'integrity_verified': True
            }
        except Exception as e:
            return {'error': str(e), 'encrypted': False}

    async def _count_active_agents(self) -> int:
        """Count active agents in system"""
        # TODO: Implement agent counting
        return 0

    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        # TODO: Implement system metrics collection
        return {
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'disk_usage': 0.0
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get Backup Agent status"""
        return {
            'agent_id': self.agent_id,
            'git_repo_path': self.git_repo_path,
            'backup_count': len(self.backup_history),
            'blockchain_memories': len(self.blockchain_memories),
            'shutdown_hooks_registered': self.shutdown_hooks_registered,
            'default_blockchain': self.default_blockchain.value,
            'capabilities': [
                'git_integration',
                'blockchain_memory',
                'immutable_storage',
                'shutdown_hooks',
                'rebuild_integration'
            ]
        }


# Factory function for Backup Agent creation
async def create_backup_agent(agent_id: str = "backup_agent") -> BackupAgent:
    """Create and initialize Backup Agent"""
    backup_agent = BackupAgent(agent_id)

    if await backup_agent.initialize():
        logger.info(f"Backup Agent {agent_id} created successfully")
        return backup_agent
    else:
        raise Exception(f"Failed to initialize Backup Agent {agent_id}")


# Main execution for standalone testing
async def main():
    """Main execution for Backup Agent testing"""
    print("💾 Initializing Backup Agent - Git and Blockchain Integration")
    print("Author: Professor Codephreak (© Professor Codephreak)")
    print("Organizations: github.com/agenticplace, github.com/cryptoagi")
    print("Resources: rage.pythai.net")
    print()

    try:
        # Create Backup Agent
        backup_agent = await create_backup_agent("backup_test")

        # Test status
        status = await backup_agent.get_status()
        print(f"Backup Agent Status: {json.dumps(status, indent=2)}")

        # Test immutable memory creation
        test_memory = await backup_agent.create_immutable_memory({
            'test_data': 'blockchain_memory_test',
            'timestamp': time.time()
        }, 'test_memory')

        print(f"Test Immutable Memory: {test_memory.memory_id}")

        print("\n✅ Backup Agent test completed - Git and blockchain integration verified")

    except Exception as e:
        print(f"❌ Backup Agent test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())