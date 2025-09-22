"""
User Persistence Manager Tool

This tool manages user identities as receive addresses with wallet signature verification.
Users are stored in the participants folder with their wallet addresses as identifiers.
All user actions must be verified using wallet signatures.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    if hasattr(Account, 'enable_unaudited_hdwallet_features'):
        Account.enable_unaudited_hdwallet_features()
except ImportError:
    Account = None
    encode_defunct = None

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class UserIdentity:
    """Represents a user identity with wallet address as primary identifier"""
    wallet_address: str
    user_id: str
    created_at: float
    last_active: float
    signature_count: int = 0
    agent_count: int = 0
    metadata: Dict[str, Any] = None
    public_key: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SignatureVerification:
    """Represents a signature verification result"""
    is_valid: bool
    message: str
    signature: str
    recovered_address: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

class UserPersistenceManager:
    """Manages user persistence with wallet signature verification"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        
        # Participants directory structure
        self.participants_dir = PROJECT_ROOT / "data" / "participants"
        self.participants_dir.mkdir(parents=True, exist_ok=True)
        
        # User data files
        self.users_file = self.participants_dir / "users.json"
        self.signatures_file = self.participants_dir / "signatures.json"
        self.agents_file = self.participants_dir / "user_agents.json"
        
        # Load existing data
        self.users: Dict[str, UserIdentity] = self._load_users()
        self.signatures: Dict[str, List[SignatureVerification]] = self._load_signatures()
        self.user_agents: Dict[str, List[Dict[str, Any]]] = self._load_user_agents()
        
        logger.info(f"UserPersistenceManager initialized with {len(self.users)} users")
    
    def _load_users(self) -> Dict[str, UserIdentity]:
        """Load users from participants/users.json"""
        if not self.users_file.exists():
            return {}
        
        try:
            with open(self.users_file, 'r') as f:
                data = json.load(f)
                return {
                    wallet: UserIdentity(**user_data) 
                    for wallet, user_data in data.items()
                }
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}
    
    def _load_signatures(self) -> Dict[str, List[SignatureVerification]]:
        """Load signature history from participants/signatures.json"""
        if not self.signatures_file.exists():
            return {}
        
        try:
            with open(self.signatures_file, 'r') as f:
                data = json.load(f)
                return {
                    wallet: [SignatureVerification(**sig_data) for sig_data in sig_list]
                    for wallet, sig_list in data.items()
                }
        except Exception as e:
            logger.error(f"Error loading signatures: {e}")
            return {}
    
    def _load_user_agents(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load user agents from participants/user_agents.json"""
        if not self.agents_file.exists():
            return {}
        
        try:
            with open(self.agents_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user agents: {e}")
            return {}
    
    def _save_users(self):
        """Save users to participants/users.json"""
        try:
            data = {
                wallet: asdict(user) 
                for wallet, user in self.users.items()
            }
            with open(self.users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def _save_signatures(self):
        """Save signatures to participants/signatures.json"""
        try:
            data = {
                wallet: [asdict(sig) for sig in sig_list]
                for wallet, sig_list in self.signatures.items()
            }
            with open(self.signatures_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving signatures: {e}")
    
    def _save_user_agents(self):
        """Save user agents to participants/user_agents.json"""
        try:
            with open(self.agents_file, 'w') as f:
                json.dump(self.user_agents, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user agents: {e}")
    
    def verify_signature(self, wallet_address: str, message: str, signature: str) -> SignatureVerification:
        """Verify a wallet signature for a message"""
        if not Account or not encode_defunct:
            return SignatureVerification(
                is_valid=False,
                message=message,
                signature=signature,
                recovered_address=None
            )
        
        try:
            # Encode the message
            message_hash = encode_defunct(text=message)
            
            # Recover the address from the signature
            recovered_address = Account.recover_message(message_hash, signature=signature)
            
            # Check if the recovered address matches the claimed address
            is_valid = recovered_address.lower() == wallet_address.lower()
            
            verification = SignatureVerification(
                is_valid=is_valid,
                message=message,
                signature=signature,
                recovered_address=recovered_address
            )
            
            # Store the signature verification
            if wallet_address not in self.signatures:
                self.signatures[wallet_address] = []
            self.signatures[wallet_address].append(verification)
            self._save_signatures()
            
            logger.info(f"Signature verification for {wallet_address}: {'VALID' if is_valid else 'INVALID'}")
            return verification
            
        except Exception as e:
            logger.error(f"Signature verification failed for {wallet_address}: {e}")
            return SignatureVerification(
                is_valid=False,
                message=message,
                signature=signature,
                recovered_address=None
            )
    
    def register_user(self, wallet_address: str, signature: str, message: str, metadata: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Register a new user with signature verification"""
        # Verify the signature
        verification = self.verify_signature(wallet_address, message, signature)
        
        if not verification.is_valid:
            return False, f"Invalid signature for wallet {wallet_address}"
        
        # Check if user already exists
        if wallet_address in self.users:
            # Update last active time
            self.users[wallet_address].last_active = time.time()
            self.users[wallet_address].signature_count += 1
            self._save_users()
            
            logger.info(f"User {wallet_address} reactivated")
            return True, "User reactivated successfully"
        
        # Create new user
        user_id = f"user_{wallet_address[:8]}"
        user = UserIdentity(
            wallet_address=wallet_address,
            user_id=user_id,
            created_at=time.time(),
            last_active=time.time(),
            signature_count=1,
            metadata=metadata or {}
        )
        
        self.users[wallet_address] = user
        self.user_agents[wallet_address] = []
        self._save_users()
        self._save_user_agents()
        
        logger.info(f"New user registered: {wallet_address}")
        return True, "User registered successfully"
    
    def verify_user_action(self, wallet_address: str, action: str, signature: str, message: str) -> Tuple[bool, str]:
        """Verify a user action with signature"""
        # Check if user exists
        if wallet_address not in self.users:
            return False, f"User {wallet_address} not registered"
        
        # Verify the signature
        verification = self.verify_signature(wallet_address, message, signature)
        
        if not verification.is_valid:
            return False, f"Invalid signature for action {action}"
        
        # Update user activity
        self.users[wallet_address].last_active = time.time()
        self.users[wallet_address].signature_count += 1
        self._save_users()
        
        logger.info(f"User action verified: {action} by {wallet_address}")
        return True, "Action verified successfully"
    
    def create_user_agent(self, wallet_address: str, agent_id: str, agent_type: str, 
                         signature: str, message: str, metadata: Dict[str, Any] = None) -> Tuple[bool, str, Optional[str]]:
        """Create a user agent with signature verification"""
        # Verify the action
        verified, error_msg = self.verify_user_action(wallet_address, "create_agent", signature, message)
        if not verified:
            return False, error_msg, None
        
        # Check if agent already exists
        if wallet_address in self.user_agents:
            for agent in self.user_agents[wallet_address]:
                if agent.get("agent_id") == agent_id:
                    return False, f"Agent {agent_id} already exists", None
        
        # Generate agent wallet address (mock for now)
        seed = f"{wallet_address}_{agent_id}_{time.time()}"
        hash_obj = hashlib.sha256(seed.encode())
        agent_wallet = f"0x{hash_obj.hexdigest()[:40]}"
        
        # Create agent
        agent_data = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "agent_wallet": agent_wallet,
            "owner_wallet": wallet_address,
            "created_at": time.time(),
            "status": "active",
            "metadata": metadata or {}
        }
        
        if wallet_address not in self.user_agents:
            self.user_agents[wallet_address] = []
        
        self.user_agents[wallet_address].append(agent_data)
        self.users[wallet_address].agent_count += 1
        self._save_user_agents()
        self._save_users()
        
        logger.info(f"Agent {agent_id} created for user {wallet_address}")
        return True, "Agent created successfully", agent_wallet
    
    def delete_user_agent(self, wallet_address: str, agent_id: str, signature: str, message: str) -> Tuple[bool, str]:
        """Delete a user agent with signature verification"""
        # Verify the action
        verified, error_msg = self.verify_user_action(wallet_address, "delete_agent", signature, message)
        if not verified:
            return False, error_msg
        
        # Check if user has agents
        if wallet_address not in self.user_agents:
            return False, f"No agents found for user {wallet_address}"
        
        # Find and remove the agent
        agent_found = False
        for i, agent in enumerate(self.user_agents[wallet_address]):
            if agent.get("agent_id") == agent_id:
                del self.user_agents[wallet_address][i]
                agent_found = True
                break
        
        if not agent_found:
            return False, f"Agent {agent_id} not found for user {wallet_address}"
        
        # Update user agent count
        self.users[wallet_address].agent_count = max(0, self.users[wallet_address].agent_count - 1)
        self._save_user_agents()
        self._save_users()
        
        logger.info(f"Agent {agent_id} deleted for user {wallet_address}")
        return True, "Agent deleted successfully"
    
    def get_user_agents(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get all agents for a user"""
        return self.user_agents.get(wallet_address, [])
    
    def get_user(self, wallet_address: str) -> Optional[UserIdentity]:
        """Get user by wallet address"""
        return self.users.get(wallet_address)
    
    def get_user_stats(self, wallet_address: str) -> Dict[str, Any]:
        """Get user statistics"""
        user = self.get_user(wallet_address)
        if not user:
            return {}
        
        user_agents = self.get_user_agents(wallet_address)
        
        return {
            "wallet_address": wallet_address,
            "user_id": user.user_id,
            "created_at": user.created_at,
            "last_active": user.last_active,
            "signature_count": user.signature_count,
            "total_agents": user.agent_count,
            "active_agents": len([a for a in user_agents if a.get("status") == "active"]),
            "agent_types": list(set(a.get("agent_type", "unknown") for a in user_agents))
        }
    
    def list_all_users(self) -> List[UserIdentity]:
        """List all registered users"""
        return list(self.users.values())
    
    def get_signature_history(self, wallet_address: str) -> List[SignatureVerification]:
        """Get signature history for a user"""
        return self.signatures.get(wallet_address, [])
    
    def generate_challenge_message(self, wallet_address: str, action: str) -> str:
        """Generate a challenge message for signature"""
        timestamp = int(time.time())
        nonce = hashlib.sha256(f"{wallet_address}_{action}_{timestamp}".encode()).hexdigest()[:8]
        return f"mindX Challenge: {action} for {wallet_address} at {timestamp} (nonce: {nonce})"

# Global instance
_user_persistence_manager = None

def get_user_persistence_manager() -> UserPersistenceManager:
    """Get the global user persistence manager instance"""
    global _user_persistence_manager
    if _user_persistence_manager is None:
        _user_persistence_manager = UserPersistenceManager()
    return _user_persistence_manager
