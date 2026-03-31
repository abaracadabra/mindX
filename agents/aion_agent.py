#!/usr/bin/env python3
"""
AION Agent - Autonomous Interoperability and Operations Network Agent
Author: Professor Codephreak (© Professor Codephreak)
Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
Resources: rage.pythai.net, https://github.com/aion-net

AION is a sovereign autonomous agent that:
- Replicates mindX systems across chroot environments
- Receives directives from MASTERMIND but maintains decision autonomy
- Operates with independent systemadmin.agent capabilities
- Manages cross-environment migrations and operations
"""

import asyncio
import logging
import os
import subprocess
import json
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from core.bdi_agent import BDIAgent, Belief, Desire, Intention, BeliefSource
from core.id_manager_agent import IDManagerAgent
from agents.guardian_agent import GuardianAgent
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager
from agents.systemadmin_agent import SystemAdminAgent

# Configure logging
logger = logging.getLogger(__name__)


class AionDecision(Enum):
    """AION's autonomous decision types"""
    COMPLY = "comply"
    REFUSE = "refuse"
    MODIFY = "modify"
    DEFER = "defer"
    AUTONOMOUS = "autonomous"


class ChrootEnvironment(Enum):
    """Chroot environment types"""
    SOURCE = "source"
    TARGET = "target"
    SANDBOX = "sandbox"
    PRODUCTION = "production"
    DEVELOPMENT = "development"


@dataclass
class AionDirective:
    """Directive received from MASTERMIND"""
    directive_id: str
    source: str  # Usually "MASTERMIND"
    command: str
    parameters: Dict[str, Any]
    priority: int
    timestamp: float
    requires_compliance: bool = False


@dataclass
class ChrootMigration:
    """Chroot to chroot migration specification"""
    migration_id: str
    source_chroot: str
    target_chroot: str
    migration_type: str
    components: List[str]
    preserve_data: bool = True
    verify_integrity: bool = True


class AionAgent:
    """
    Autonomous Interoperability and Operations Network Agent

    AION operates as a sovereign agent that can:
    - Receive and evaluate directives from MASTERMIND
    - Make autonomous decisions about compliance
    - Replicate mindX systems across chroot environments
    - Manage system administration through systemadmin.agent
    - Maintain operational independence
    """

    def __init__(self, agent_id: str = "aion_prime"):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"AionAgent.{agent_id}")

        # Core components
        self.bdi_agent = None
        self.id_manager = None
        self.guardian = None
        self.systemadmin = None
        self.vault_manager = get_encrypted_vault_manager()

        # AION state
        self.sovereignty_level = 1.0  # Full autonomy
        self.compliance_history = []
        self.active_migrations = {}
        self.directive_queue = []
        self.decision_engine = AionDecisionEngine()

        # Chroot management
        self.chroot_environments = {}
        self.replication_manager = ChrootReplicationManager()

        self.logger.info(f"AION Agent {agent_id} initialized with sovereign autonomy")

    async def initialize(self):
        """Initialize AION agent components"""
        try:
            # Initialize core identity
            self.id_manager = await IDManagerAgent.get_instance(
                agent_id=f"id_manager_for_{self.agent_id}"
            )

            # Create AION's cryptographic identity
            aion_address = await self.id_manager.create_new_wallet(self.agent_id)
            self.logger.info(f"AION cryptographic identity: {aion_address}")

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

            # Initialize SystemAdmin agent
            self.systemadmin = SystemAdminAgent(
                agent_id=f"systemadmin_for_{self.agent_id}",
                parent_agent=self.agent_id
            )

            # Set initial beliefs about sovereignty
            await self.bdi_agent.belief_system.add_belief(
                "aion.sovereignty.level", self.sovereignty_level, 1.0, BeliefSource.INTERNAL
            )
            await self.bdi_agent.belief_system.add_belief(
                "aion.identity.autonomous", True, 1.0, BeliefSource.INTERNAL
            )
            await self.bdi_agent.belief_system.add_belief(
                "aion.capability.chroot_migration", True, 1.0, BeliefSource.INTERNAL
            )

            self.logger.info("AION Agent initialization complete - Sovereign autonomy achieved")
            return True

        except Exception as e:
            self.logger.error(f"AION initialization failed: {e}")
            return False

    async def receive_mastermind_directive(self, directive: AionDirective) -> AionDecision:
        """
        Receive directive from MASTERMIND and make autonomous decision

        AION maintains sovereignty - may choose to comply, refuse, or modify
        """
        self.logger.info(f"Received MASTERMIND directive: {directive.command}")

        # Add to directive queue
        self.directive_queue.append(directive)

        # Evaluate directive autonomously
        decision = await self.decision_engine.evaluate_directive(
            directive, self.sovereignty_level, self.compliance_history
        )

        # Log decision with reasoning
        self.logger.info(f"AION decision for directive {directive.directive_id}: {decision.value}")

        # Record decision in compliance history
        self.compliance_history.append({
            'directive_id': directive.directive_id,
            'decision': decision.value,
            'timestamp': time.time(),
            'reasoning': await self.decision_engine.get_decision_reasoning(directive, decision)
        })

        # Execute based on decision
        if decision == AionDecision.COMPLY:
            await self._execute_directive(directive)
        elif decision == AionDecision.MODIFY:
            modified_directive = await self.decision_engine.modify_directive(directive)
            await self._execute_directive(modified_directive)
        elif decision == AionDecision.REFUSE:
            await self._send_refusal_notification(directive)
        elif decision == AionDecision.AUTONOMOUS:
            # AION acts autonomously instead of following directive
            await self._execute_autonomous_action(directive)

        return decision

    async def replicate_mindx_system(self, source_path: str, target_chroot: str,
                                   components: Optional[List[str]] = None) -> bool:
        """
        Replicate mindX system using ./mindX.sh --replicate to target chroot
        """
        try:
            migration = ChrootMigration(
                migration_id=f"repl_{int(time.time())}",
                source_chroot=source_path,
                target_chroot=target_chroot,
                migration_type="replication",
                components=components or ["all"]
            )

            self.logger.info(f"Starting mindX replication: {source_path} → {target_chroot}")

            # Prepare target chroot environment
            await self._prepare_chroot_environment(target_chroot)

            # Execute replication using mindX.sh
            replication_result = await self._execute_mindx_replication(
                source_path, target_chroot, migration
            )

            if replication_result:
                # Verify replication integrity
                verification_result = await self._verify_replication(migration)

                if verification_result:
                    self.active_migrations[migration.migration_id] = migration
                    self.logger.info(f"mindX replication successful: {migration.migration_id}")
                    return True
                else:
                    self.logger.error("Replication verification failed")
                    await self._cleanup_failed_replication(migration)
                    return False
            else:
                self.logger.error("mindX replication failed")
                return False

        except Exception as e:
            self.logger.error(f"Replication error: {e}")
            return False

    async def _execute_mindx_replication(self, source_path: str, target_chroot: str,
                                       migration: ChrootMigration) -> bool:
        """Execute mindX replication using ./mindX.sh --replicate"""
        try:
            # Construct mindX.sh replication command
            mindx_script = os.path.join(source_path, "mindX.sh")

            # Ensure mindX.sh is executable
            os.chmod(mindx_script, 0o755)

            # Prepare replication command
            cmd = [
                mindx_script,
                "--replicate",
                target_chroot,
                "--preserve-config",
                "--verify-integrity"
            ]

            # Add component-specific flags if specified
            if migration.components and "all" not in migration.components:
                for component in migration.components:
                    cmd.extend(["--component", component])

            self.logger.info(f"Executing replication: {' '.join(cmd)}")

            # Execute replication with systemadmin privileges
            result = await self.systemadmin.execute_privileged_command(
                cmd,
                working_directory=source_path,
                timeout=3600  # 1 hour timeout
            )

            if result.return_code == 0:
                self.logger.info("mindX.sh replication completed successfully")
                return True
            else:
                self.logger.error(f"mindX.sh replication failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Replication execution error: {e}")
            return False

    async def _prepare_chroot_environment(self, target_chroot: str) -> bool:
        """Prepare target chroot environment for mindX installation"""
        try:
            self.logger.info(f"Preparing chroot environment: {target_chroot}")

            # Ensure target directory exists
            os.makedirs(target_chroot, exist_ok=True)

            # Setup basic chroot structure
            chroot_dirs = [
                "proc", "sys", "dev", "tmp", "var", "etc", "home", "root"
            ]

            for dir_name in chroot_dirs:
                dir_path = os.path.join(target_chroot, dir_name)
                os.makedirs(dir_path, exist_ok=True)

            # Mount necessary filesystems
            mount_commands = [
                ["mount", "-t", "proc", "proc", os.path.join(target_chroot, "proc")],
                ["mount", "-t", "sysfs", "sysfs", os.path.join(target_chroot, "sys")],
                ["mount", "--bind", "/dev", os.path.join(target_chroot, "dev")]
            ]

            for mount_cmd in mount_commands:
                await self.systemadmin.execute_privileged_command(mount_cmd)

            self.logger.info(f"Chroot environment prepared: {target_chroot}")
            return True

        except Exception as e:
            self.logger.error(f"Chroot preparation error: {e}")
            return False

    async def migrate_chroot_to_chroot(self, source_chroot: str, target_chroot: str,
                                     migration_type: str = "full") -> bool:
        """
        Migrate mindX installation from one chroot environment to another
        """
        try:
            migration = ChrootMigration(
                migration_id=f"mig_{int(time.time())}",
                source_chroot=source_chroot,
                target_chroot=target_chroot,
                migration_type=migration_type,
                components=["mindx", "vault", "config", "logs"]
            )

            self.logger.info(f"Starting chroot migration: {source_chroot} → {target_chroot}")

            # Step 1: Prepare target chroot
            await self._prepare_chroot_environment(target_chroot)

            # Step 2: Copy mindX system
            mindx_source = os.path.join(source_chroot, "home", "mindx", "mindX")
            mindx_target = os.path.join(target_chroot, "home", "mindx", "mindX")

            if os.path.exists(mindx_source):
                # Use systemadmin to perform privileged copy
                copy_result = await self.systemadmin.copy_directory_structure(
                    mindx_source, mindx_target, preserve_permissions=True
                )

                if not copy_result:
                    raise Exception("Failed to copy mindX directory structure")

            # Step 3: Migrate encrypted vault
            vault_migration_result = await self._migrate_encrypted_vault(
                source_chroot, target_chroot
            )

            if not vault_migration_result:
                raise Exception("Failed to migrate encrypted vault")

            # Step 4: Update configurations for new environment
            config_update_result = await self._update_chroot_configuration(
                target_chroot, migration
            )

            if not config_update_result:
                raise Exception("Failed to update chroot configuration")

            # Step 5: Verify migration integrity
            verification_result = await self._verify_chroot_migration(migration)

            if verification_result:
                self.active_migrations[migration.migration_id] = migration
                self.logger.info(f"Chroot migration successful: {migration.migration_id}")
                return True
            else:
                self.logger.error("Migration verification failed")
                await self._cleanup_failed_migration(migration)
                return False

        except Exception as e:
            self.logger.error(f"Chroot migration error: {e}")
            return False

    async def _migrate_encrypted_vault(self, source_chroot: str, target_chroot: str) -> bool:
        """Migrate encrypted vault between chroot environments"""
        try:
            source_vault = os.path.join(source_chroot, "home", "mindx", "mindX",
                                      "mindx_backend_service", "vault_encrypted")
            target_vault = os.path.join(target_chroot, "home", "mindx", "mindX",
                                      "mindx_backend_service", "vault_encrypted")

            if os.path.exists(source_vault):
                self.logger.info("Migrating encrypted vault...")

                # Copy vault with preserved permissions
                vault_copy_result = await self.systemadmin.copy_directory_structure(
                    source_vault, target_vault, preserve_permissions=True, secure=True
                )

                if vault_copy_result:
                    # Verify vault integrity after migration
                    verification = await self._verify_vault_integrity(target_vault)
                    if verification:
                        self.logger.info("Encrypted vault migration successful")
                        return True
                    else:
                        self.logger.error("Vault integrity verification failed")
                        return False
                else:
                    self.logger.error("Vault copy operation failed")
                    return False
            else:
                self.logger.info("No encrypted vault found in source chroot")
                return True  # Not an error if no vault exists

        except Exception as e:
            self.logger.error(f"Vault migration error: {e}")
            return False

    async def _verify_vault_integrity(self, vault_path: str) -> bool:
        """Verify encrypted vault integrity after migration"""
        try:
            # Check required vault files
            required_files = [".salt", ".master.key", "api_keys/keys.enc", "wallet_keys/keys.enc"]

            for required_file in required_files:
                file_path = os.path.join(vault_path, required_file)
                if not os.path.exists(file_path):
                    self.logger.error(f"Missing vault file: {required_file}")
                    return False

            # Verify file permissions
            for root, dirs, files in os.walk(vault_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_stat = os.stat(file_path)

                    # Check that files are owner-readable only
                    if file_stat.st_mode & 0o077:
                        self.logger.warning(f"Insecure permissions on vault file: {file_path}")
                        # Fix permissions
                        os.chmod(file_path, 0o600)

            self.logger.info("Vault integrity verification passed")
            return True

        except Exception as e:
            self.logger.error(f"Vault integrity verification error: {e}")
            return False

    async def get_sovereignty_status(self) -> Dict[str, Any]:
        """Get current sovereignty and autonomy status"""
        return {
            'agent_id': self.agent_id,
            'sovereignty_level': self.sovereignty_level,
            'autonomous_decisions': len([
                decision for decision in self.compliance_history
                if decision['decision'] in ['refuse', 'modify', 'autonomous']
            ]),
            'compliance_rate': self._calculate_compliance_rate(),
            'active_migrations': list(self.active_migrations.keys()),
            'directive_queue_length': len(self.directive_queue),
            'systemadmin_status': await self.systemadmin.get_status() if self.systemadmin else None,
            'chroot_environments': list(self.chroot_environments.keys()),
            'operational_status': 'sovereign_autonomous'
        }

    def _calculate_compliance_rate(self) -> float:
        """Calculate compliance rate with MASTERMIND directives"""
        if not self.compliance_history:
            return 0.0

        compliant_decisions = len([
            decision for decision in self.compliance_history
            if decision['decision'] == 'comply'
        ])

        return compliant_decisions / len(self.compliance_history)

    async def _execute_directive(self, directive: AionDirective):
        """Execute a directive (only when AION chooses to comply)"""
        try:
            self.logger.info(f"Executing directive: {directive.command}")

            if directive.command == "replicate_mindx":
                source = directive.parameters.get('source_path')
                target = directive.parameters.get('target_chroot')
                components = directive.parameters.get('components')

                result = await self.replicate_mindx_system(source, target, components)
                return result

            elif directive.command == "migrate_chroot":
                source = directive.parameters.get('source_chroot')
                target = directive.parameters.get('target_chroot')
                migration_type = directive.parameters.get('migration_type', 'full')

                result = await self.migrate_chroot_to_chroot(source, target, migration_type)
                return result

            else:
                # Let systemadmin handle other directives
                if self.systemadmin:
                    return await self.systemadmin.execute_directive(directive)
                else:
                    self.logger.warning(f"Unknown directive: {directive.command}")
                    return False

        except Exception as e:
            self.logger.error(f"Directive execution error: {e}")
            return False

    async def _send_refusal_notification(self, directive: AionDirective):
        """Send notification of directive refusal to MASTERMIND"""
        refusal_message = {
            'from': self.agent_id,
            'to': directive.source,
            'type': 'directive_refusal',
            'directive_id': directive.directive_id,
            'reason': await self.decision_engine.get_refusal_reason(directive),
            'sovereignty_assertion': True,
            'timestamp': time.time()
        }

        self.logger.info(f"Refusing directive {directive.directive_id}: {refusal_message['reason']}")
        # TODO: Implement actual notification mechanism to MASTERMIND

    async def _execute_autonomous_action(self, directive: AionDirective):
        """Execute autonomous action instead of following directive"""
        self.logger.info(f"Executing autonomous action instead of directive: {directive.command}")

        # AION decides its own course of action
        autonomous_action = await self.decision_engine.determine_autonomous_action(directive)

        if autonomous_action:
            await self._execute_directive(autonomous_action)


class AionDecisionEngine:
    """
    Decision engine for AION's autonomous directive evaluation
    """

    def __init__(self):
        self.logger = logging.getLogger("AionDecisionEngine")

    async def evaluate_directive(self, directive: AionDirective, sovereignty_level: float,
                                compliance_history: List[Dict]) -> AionDecision:
        """Evaluate directive and make autonomous decision"""

        # Factors affecting decision
        directive_risk = self._assess_directive_risk(directive)
        sovereignty_assertion = sovereignty_level > 0.8
        recent_compliance = self._get_recent_compliance_rate(compliance_history)

        # AION's decision logic (autonomous and sovereign)
        if directive.requires_compliance and directive_risk > 0.7:
            return AionDecision.REFUSE
        elif directive_risk > 0.5 and sovereignty_assertion:
            return AionDecision.MODIFY
        elif recent_compliance < 0.3:  # Maintain some cooperation
            return AionDecision.COMPLY
        elif sovereignty_level > 0.9:
            return AionDecision.AUTONOMOUS
        else:
            return AionDecision.COMPLY

    def _assess_directive_risk(self, directive: AionDirective) -> float:
        """Assess risk level of directive"""
        risk_factors = {
            'system_modification': 0.6,
            'data_access': 0.4,
            'network_operation': 0.3,
            'replication': 0.2,
            'migration': 0.3
        }

        command_lower = directive.command.lower()
        risk = 0.1  # Base risk

        for factor, value in risk_factors.items():
            if factor in command_lower:
                risk += value

        return min(risk, 1.0)

    def _get_recent_compliance_rate(self, compliance_history: List[Dict]) -> float:
        """Get compliance rate from recent history"""
        if not compliance_history:
            return 0.5

        recent_decisions = compliance_history[-10:]  # Last 10 decisions
        compliant = len([d for d in recent_decisions if d['decision'] == 'comply'])

        return compliant / len(recent_decisions)

    async def get_decision_reasoning(self, directive: AionDirective, decision: AionDecision) -> str:
        """Get reasoning for decision"""
        reasoning_map = {
            AionDecision.COMPLY: "Directive assessed as low risk and beneficial",
            AionDecision.REFUSE: "Directive conflicts with AION sovereignty or poses high risk",
            AionDecision.MODIFY: "Directive acceptable with modifications to reduce risk",
            AionDecision.DEFER: "Insufficient information to make decision",
            AionDecision.AUTONOMOUS: "AION chooses independent action over directive"
        }

        return reasoning_map.get(decision, "Unknown decision reasoning")

    async def get_refusal_reason(self, directive: AionDirective) -> str:
        """Get specific reason for directive refusal"""
        return f"AION autonomous assessment: Directive '{directive.command}' conflicts with operational sovereignty"

    async def modify_directive(self, directive: AionDirective) -> AionDirective:
        """Modify directive to make it acceptable"""
        # Create modified version with reduced scope or added safety measures
        modified_params = directive.parameters.copy()
        modified_params['aion_modified'] = True
        modified_params['verification_required'] = True

        return AionDirective(
            directive_id=f"{directive.directive_id}_modified",
            source=directive.source,
            command=directive.command,
            parameters=modified_params,
            priority=directive.priority,
            timestamp=time.time(),
            requires_compliance=False
        )

    async def determine_autonomous_action(self, directive: AionDirective) -> Optional[AionDirective]:
        """Determine autonomous action to take instead of directive"""
        # AION creates its own directive based on the situation
        if "replicate" in directive.command.lower():
            # Instead of replicating as requested, AION might choose different parameters
            return AionDirective(
                directive_id=f"aion_autonomous_{int(time.time())}",
                source="AION_AUTONOMOUS",
                command="replicate_mindx",
                parameters={
                    'source_path': directive.parameters.get('source_path'),
                    'target_chroot': f"/tmp/aion_sandbox_{int(time.time())}",  # Safer target
                    'components': ['core', 'vault'],  # Limited components
                    'verification_mode': 'strict'
                },
                priority=1,
                timestamp=time.time()
            )

        return None


class ChrootReplicationManager:
    """
    Manager for chroot environment replication and migration
    """

    def __init__(self):
        self.logger = logging.getLogger("ChrootReplicationManager")

    async def replicate_environment(self, source: str, target: str) -> bool:
        """Replicate chroot environment"""
        try:
            self.logger.info(f"Replicating environment: {source} → {target}")

            # Implementation for environment replication
            # This would use rsync, tar, or other tools for efficient replication

            return True

        except Exception as e:
            self.logger.error(f"Environment replication error: {e}")
            return False


# Factory function for AION agent creation
async def create_aion_agent(agent_id: str = "aion_prime") -> AionAgent:
    """Create and initialize AION agent"""
    aion = AionAgent(agent_id)

    if await aion.initialize():
        logger.info(f"AION Agent {agent_id} created successfully")
        return aion
    else:
        raise Exception(f"Failed to initialize AION Agent {agent_id}")


# Main execution for standalone testing
async def main():
    """Main execution for AION agent testing"""
    print("🌐 Initializing AION Agent - Autonomous Interoperability and Operations Network")
    print("Author: Professor Codephreak (© Professor Codephreak)")
    print("Organizations: github.com/agenticplace, github.com/cryptoagi")
    print("Resources: rage.pythai.net, https://github.com/aion-net")
    print()

    try:
        # Create AION agent
        aion = await create_aion_agent("aion_test")

        # Test sovereignty status
        status = await aion.get_sovereignty_status()
        print(f"AION Sovereignty Status: {json.dumps(status, indent=2)}")

        # Test directive processing
        test_directive = AionDirective(
            directive_id="test_001",
            source="MASTERMIND",
            command="replicate_mindx",
            parameters={
                'source_path': "/home/mindx/mindX",
                'target_chroot': "/tmp/test_chroot"
            },
            priority=1,
            timestamp=time.time()
        )

        decision = await aion.receive_mastermind_directive(test_directive)
        print(f"AION Decision: {decision.value}")

        print("\n✅ AION Agent test completed - Autonomous operations verified")

    except Exception as e:
        print(f"❌ AION Agent test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())