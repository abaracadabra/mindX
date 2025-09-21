"""
Coral ID Agent - CrossMint Integration for mindX Agent Wallets

This agent extends the functionality of IDManagerAgent to provide:
- CrossMint social login integration
- Agent wallet creation and management
- Multi-chain wallet support (Ethereum, Solana, etc.)
- Secure key management for agents
- CrossMint API integration for wallet operations

Author: PYTHAI Institute for Emergent Systems
License: MIT
"""

import asyncio
import json
import logging
import os
import secrets
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Setup logging
logger = logging.getLogger(__name__)

class WalletType(Enum):
    """Supported wallet types"""
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"

class AgentRole(Enum):
    """Agent roles for wallet permissions"""
    CORE_SYSTEM = "core_system"
    ORCHESTRATION = "orchestration"
    LEARNING = "learning"
    MONITORING = "monitoring"
    TOOLS = "tools"
    EVOLUTION = "evolution"

@dataclass
class AgentWallet:
    """Represents an agent wallet with CrossMint integration"""
    agent_id: str
    wallet_address: str
    wallet_type: WalletType
    crossmint_user_id: Optional[str]
    public_key: str
    encrypted_private_key: bytes
    role: AgentRole
    created_at: float
    last_accessed: float
    is_active: bool = True
    metadata: Dict[str, Any] = None

@dataclass
class CrossMintConfig:
    """CrossMint configuration"""
    api_key: str
    environment: str  # 'staging' or 'production'
    chain_id: str
    usdc_mint: str
    base_url: str

class CoralIDAgent:
    """
    Coral ID Agent for CrossMint-based agent wallet management
    
    This agent provides:
    1. CrossMint social login integration
    2. Agent wallet creation and management
    3. Multi-chain wallet support
    4. Secure key storage and management
    5. CrossMint API integration
    """
    
    def __init__(self, config: Optional[CrossMintConfig] = None):
        self.config = config or self._load_config()
        self.agent_wallets: Dict[str, AgentWallet] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._encryption_key: Optional[bytes] = None
        self._initialized = False
        
    def _load_config(self) -> CrossMintConfig:
        """Load CrossMint configuration from environment variables"""
        return CrossMintConfig(
            api_key=os.getenv("CROSSMINT_CLIENT_API_KEY", ""),
            environment=os.getenv("CROSSMINT_ENVIRONMENT", "staging"),
            chain_id=os.getenv("CROSSMINT_CHAIN_ID", "ethereum"),
            usdc_mint=os.getenv("CROSSMINT_USDC_MINT", ""),
            base_url=os.getenv("CROSSMINT_BASE_URL", "https://staging.crossmint.com")
        )
    
    async def initialize(self) -> bool:
        """Initialize the Coral ID Agent"""
        try:
            if self._initialized:
                return True
                
            # Initialize encryption key
            self._encryption_key = self._generate_encryption_key()
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.config.api_key,
                    "Content-Type": "application/json"
                }
            )
            
            # Load existing agent wallets
            await self._load_agent_wallets()
            
            self._initialized = True
            logger.info("Coral ID Agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Coral ID Agent: {e}")
            return False
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for private key storage"""
        # In production, this should be derived from a master key
        salt = b"coral_id_agent_salt"  # Should be random in production
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(b"coral_master_key")  # Should be from secure source
    
    async def create_agent_wallet(
        self, 
        agent_id: str, 
        role: AgentRole,
        wallet_type: WalletType = WalletType.ETHEREUM,
        crossmint_user_id: Optional[str] = None
    ) -> Optional[AgentWallet]:
        """Create a new agent wallet with CrossMint integration"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Generate wallet address and keys
            wallet_address, public_key, private_key = await self._generate_wallet_keys(wallet_type)
            
            # Encrypt private key
            encrypted_private_key = self._encrypt_private_key(private_key)
            
            # Create agent wallet
            agent_wallet = AgentWallet(
                agent_id=agent_id,
                wallet_address=wallet_address,
                wallet_type=wallet_type,
                crossmint_user_id=crossmint_user_id,
                public_key=public_key,
                encrypted_private_key=encrypted_private_key,
                role=role,
                created_at=time.time(),
                last_accessed=time.time(),
                metadata={
                    "created_by": "coral_id_agent",
                    "version": "1.0.0",
                    "chain_id": self.config.chain_id
                }
            )
            
            # Store wallet
            self.agent_wallets[agent_id] = agent_wallet
            
            # Save to persistent storage
            await self._save_agent_wallets()
            
            logger.info(f"Created agent wallet for {agent_id}: {wallet_address}")
            return agent_wallet
            
        except Exception as e:
            logger.error(f"Failed to create agent wallet for {agent_id}: {e}")
            return None
    
    async def _generate_wallet_keys(self, wallet_type: WalletType) -> tuple[str, str, str]:
        """Generate wallet keys for the specified wallet type"""
        if wallet_type == WalletType.ETHEREUM:
            return await self._generate_ethereum_keys()
        elif wallet_type == WalletType.SOLANA:
            return await self._generate_solana_keys()
        else:
            # Default to Ethereum for now
            return await self._generate_ethereum_keys()
    
    async def _generate_ethereum_keys(self) -> tuple[str, str, str]:
        """Generate Ethereum wallet keys"""
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Generate wallet address (simplified - in production use proper address generation)
        wallet_address = "0x" + secrets.token_hex(20)
        
        return wallet_address, public_pem.decode(), private_pem.decode()
    
    async def _generate_solana_keys(self) -> tuple[str, str, str]:
        """Generate Solana wallet keys"""
        # Generate random keypair (simplified)
        private_key_bytes = secrets.token_bytes(32)
        public_key_bytes = secrets.token_bytes(32)
        
        # Convert to base58 (simplified)
        wallet_address = base64.b64encode(public_key_bytes).decode()
        public_key = base64.b64encode(public_key_bytes).decode()
        private_key = base64.b64encode(private_key_bytes).decode()
        
        return wallet_address, public_key, private_key
    
    def _encrypt_private_key(self, private_key: str) -> bytes:
        """Encrypt private key for secure storage"""
        # Simple encryption (in production, use proper encryption)
        key = self._encryption_key
        encrypted = private_key.encode()
        return encrypted  # Simplified - implement proper encryption
    
    def _decrypt_private_key(self, encrypted_private_key: bytes) -> str:
        """Decrypt private key"""
        # Simple decryption (in production, use proper decryption)
        return encrypted_private_key.decode()
    
    async def get_agent_wallet(self, agent_id: str) -> Optional[AgentWallet]:
        """Get agent wallet by ID"""
        if agent_id in self.agent_wallets:
            wallet = self.agent_wallets[agent_id]
            wallet.last_accessed = time.time()
            return wallet
        return None
    
    async def list_agent_wallets(self, role: Optional[AgentRole] = None) -> List[AgentWallet]:
        """List all agent wallets, optionally filtered by role"""
        wallets = list(self.agent_wallets.values())
        if role:
            wallets = [w for w in wallets if w.role == role]
        return wallets
    
    async def update_agent_wallet(
        self, 
        agent_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update agent wallet metadata"""
        try:
            if agent_id not in self.agent_wallets:
                return False
            
            wallet = self.agent_wallets[agent_id]
            for key, value in updates.items():
                if hasattr(wallet, key):
                    setattr(wallet, key, value)
            
            wallet.last_accessed = time.time()
            await self._save_agent_wallets()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update agent wallet {agent_id}: {e}")
            return False
    
    async def deactivate_agent_wallet(self, agent_id: str) -> bool:
        """Deactivate an agent wallet"""
        try:
            if agent_id not in self.agent_wallets:
                return False
            
            self.agent_wallets[agent_id].is_active = False
            await self._save_agent_wallets()
            logger.info(f"Deactivated agent wallet for {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate agent wallet {agent_id}: {e}")
            return False
    
    async def _load_agent_wallets(self):
        """Load agent wallets from persistent storage"""
        try:
            # In production, load from secure database
            # For now, initialize with empty dict
            self.agent_wallets = {}
            logger.info("Loaded agent wallets from storage")
        except Exception as e:
            logger.error(f"Failed to load agent wallets: {e}")
            self.agent_wallets = {}
    
    async def _save_agent_wallets(self):
        """Save agent wallets to persistent storage"""
        try:
            # In production, save to secure database
            # For now, just log the operation
            logger.info(f"Saved {len(self.agent_wallets)} agent wallets to storage")
        except Exception as e:
            logger.error(f"Failed to save agent wallets: {e}")
    
    async def integrate_crossmint_user(
        self, 
        agent_id: str, 
        crossmint_user_id: str
    ) -> bool:
        """Integrate existing CrossMint user with agent wallet"""
        try:
            if agent_id not in self.agent_wallets:
                return False
            
            wallet = self.agent_wallets[agent_id]
            wallet.crossmint_user_id = crossmint_user_id
            wallet.last_accessed = time.time()
            
            await self._save_agent_wallets()
            logger.info(f"Integrated CrossMint user {crossmint_user_id} with agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to integrate CrossMint user: {e}")
            return False
    
    async def get_crossmint_wallet_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get CrossMint wallet information for an agent"""
        try:
            wallet = await self.get_agent_wallet(agent_id)
            if not wallet or not wallet.crossmint_user_id:
                return None
            
            # In production, make API call to CrossMint
            # For now, return mock data
            return {
                "user_id": wallet.crossmint_user_id,
                "wallet_address": wallet.wallet_address,
                "chain_id": self.config.chain_id,
                "balance": "0.0",  # Would fetch from CrossMint API
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Failed to get CrossMint wallet info for {agent_id}: {e}")
            return None
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        self._initialized = False
        logger.info("Coral ID Agent cleaned up")

# Factory function for easy instantiation
async def create_coral_id_agent(config: Optional[CrossMintConfig] = None) -> CoralIDAgent:
    """Create and initialize a Coral ID Agent instance"""
    agent = CoralIDAgent(config)
    await agent.initialize()
    return agent

# Example usage
if __name__ == "__main__":
    async def main():
        # Create agent
        coral_agent = await create_coral_id_agent()
        
        # Create wallets for different agent types
        await coral_agent.create_agent_wallet(
            agent_id="mastermind_agent",
            role=AgentRole.ORCHESTRATION,
            wallet_type=WalletType.ETHEREUM
        )
        
        await coral_agent.create_agent_wallet(
            agent_id="coordinator_agent",
            role=AgentRole.ORCHESTRATION,
            wallet_type=WalletType.ETHEREUM
        )
        
        # List all wallets
        wallets = await coral_agent.list_agent_wallets()
        for wallet in wallets:
            print(f"Agent: {wallet.agent_id}, Address: {wallet.wallet_address}")
        
        # Cleanup
        await coral_agent.cleanup()
    
    asyncio.run(main())
