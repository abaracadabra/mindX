# ╔══════════════════════════════════════════════════════════════════╗
# ║  Credential Provider — Bridge between BANKON Vault and mindX   ║
# ║  Loads encrypted API keys into environment at service startup   ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
from pathlib import Path
from typing import Dict, Optional

from mindx_backend_service.bankon_vault.vault import BankonVault

# Provider ID → environment variable mapping
PROVIDER_ENV_MAP = {
    # Google Gemini
    "gemini_api_key": "GEMINI_API_KEY",
    # Groq
    "groq_api_key": "GROQ_API_KEY",
    # OpenAI
    "openai_api_key": "OPENAI_API_KEY",
    # Anthropic
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    # Mistral
    "mistral_api_key": "MISTRAL_API_KEY",
    # Together AI
    "together_api_key": "TOGETHER_API_KEY",
    # vLLM (production inference server)
    "vllm_base_url": "VLLM_BASE_URL",
    "vllm_api_key": "VLLM_API_KEY",
    # Ollama (base URL, not a secret but configurable)
    "ollama_base_url": "MINDX_LLM__OLLAMA__BASE_URL",
    # Ollama Cloud (Bearer token used by both the mindX backend and the
    # local Ollama daemon when proxying *:cloud model calls to ollama.com)
    "ollama_api_key": "OLLAMA_API_KEY",
    # Replicate
    "replicate_api_key": "REPLICATE_API_TOKEN",
    # Stability AI
    "stability_api_key": "STABILITY_API_KEY",
    # Cohere
    "cohere_api_key": "COHERE_API_KEY",
    # Perplexity
    "perplexity_api_key": "PERPLEXITY_API_KEY",
    # DeepSeek
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    # Fireworks AI
    "fireworks_api_key": "FIREWORKS_API_KEY",
    # OpenRouter — universal LLM backplane (free + paid catalogue, OpenAI-compatible)
    "openrouter_api_key": "OPENROUTER_API_KEY",
    # mindX service API keys (for Bearer auth)
    "mindx_api_keys": "MINDX_SECURITY_API_KEYS",
    # Admin wallet addresses
    "mindx_admin_addresses": "MINDX_SECURITY_ADMIN_ADDRESSES",
    # IPFS storage providers — for memory offload (plan: whispering-floating-merkle.md)
    "lighthouse_api_key": "LIGHTHOUSE_API_KEY",
    "nftstorage_api_key": "NFTSTORAGE_API_KEY",
    # Chain RPC URLs for memory anchoring (ARC + Polygon)
    "arc_rpc_url": "ARC_RPC_URL",
    "polygon_rpc_url": "POLYGON_RPC_URL",
    # Treasury wallet — funds agent gas for chain anchoring
    "memory_anchor_treasury_pk": "MEMORY_ANCHOR_TREASURY_PK",
    # Uniswap Trading API (https://trade-api.gateway.uniswap.org/v1/*)
    "uniswap_trade_api_key": "UNISWAP_TRADE_API_KEY",
}


class CredentialProvider:
    """
    Loads credentials from BANKON Vault into process environment.

    On startup:
      1. Opens vault with key file (automated) or passphrase (interactive)
      2. Reads each stored credential
      3. Injects into os.environ for the LLM factory and auth middleware
      4. Locks vault (keys zeroized from memory)
    """

    def __init__(self, vault: Optional[BankonVault] = None):
        self.vault = vault or BankonVault()
        self._loaded_keys: list[str] = []

    def load_from_vault(self, key_file: Optional[Path] = None) -> Dict[str, bool]:
        """
        Load all provider credentials from vault into environment.

        Returns dict of {provider_id: loaded_successfully}
        """
        # Unlock vault
        if not self.vault.is_unlocked():
            self.vault.unlock_with_key_file(key_file)

        results = {}
        for vault_id, env_var in PROVIDER_ENV_MAP.items():
            value = self.vault.retrieve(vault_id)
            if value:
                os.environ[env_var] = value
                self._loaded_keys.append(env_var)
                results[vault_id] = True
            else:
                results[vault_id] = False

        # Lock vault after loading — keys only live in os.environ now
        self.vault.lock()

        return results

    def get_loaded_providers(self) -> list[str]:
        """Return list of env vars that were loaded from vault."""
        return list(self._loaded_keys)

    def store_credential(self, vault_id: str, value: str,
                         key_file: Optional[Path] = None) -> bool:
        """Store a credential in the vault."""
        if vault_id not in PROVIDER_ENV_MAP:
            raise ValueError(
                f"Unknown provider: {vault_id}. "
                f"Valid: {', '.join(sorted(PROVIDER_ENV_MAP.keys()))}"
            )

        if not self.vault.is_unlocked():
            self.vault.unlock_with_key_file(key_file)

        result = self.vault.store(vault_id, value, context="provider")
        self.vault.lock()
        return result

    def remove_credential(self, vault_id: str,
                          key_file: Optional[Path] = None) -> bool:
        """Remove a credential from the vault."""
        if not self.vault.is_unlocked():
            self.vault.unlock_with_key_file(key_file)

        result = self.vault.delete(vault_id)
        self.vault.lock()
        return result

    def list_credentials(self, key_file: Optional[Path] = None) -> list[dict]:
        """List stored credentials (IDs only, no secrets)."""
        if not self.vault.is_unlocked():
            self.vault.unlock_with_key_file(key_file)

        entries = self.vault.list_entries()
        self.vault.lock()
        return entries
