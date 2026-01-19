# settings.py
# SettingsManager wrapper for mindX configuration system

import os
from typing import Any, Optional

class SettingsManager:
    """
    Settings manager that wraps the mindX Config system.
    Provides a simple interface compatible with chatter.py and other systems.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Import Config from utils
        try:
            from utils.config import Config
            self.config = Config()
        except ImportError:
            self.config = None
        
        self._initialized = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.
        
        Args:
            key: Setting key (supports dot notation like 'ollama.base_url')
            default: Default value if key not found
        
        Returns:
            Setting value or default
        """
        # First try environment variable (highest priority)
        env_key = key.upper().replace('.', '_')
        env_value = os.getenv(env_key) or os.getenv(f"MINDX_{env_key}")
        if env_value:
            # Try to convert to appropriate type
            if env_value.lower() in ('true', 'false'):
                return env_value.lower() == 'true'
            try:
                if '.' in env_value:
                    return float(env_value)
                return int(env_value)
            except ValueError:
                return env_value
        
        # Then try config system
        if self.config:
            try:
                value = self.config.get(key, default)
                if value is not None:
                    return value
            except Exception:
                pass
        
        return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set a setting value (if config supports it).
        
        Args:
            key: Setting key
            value: Setting value
        
        Returns:
            True if successful, False otherwise
        """
        if self.config and hasattr(self.config, 'set'):
            try:
                self.config.set(key, value)
                return True
            except Exception:
                pass
        return False
