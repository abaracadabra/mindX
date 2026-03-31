# MindX Security Model

**Status:** ✅ **Production Ready** - Enterprise deployment with encrypted vault security
**Last Updated:** March 2026
**Version:** 4.0 (AES-256 Encrypted Vault)

This document outlines the **production-ready security architecture** of the MindX system, featuring **AES-256 encrypted vault storage**, advanced authentication, and enterprise-grade security controls.

## 1. 🔒 Production Security Principles

-   **🔐 Encrypted Storage:** All sensitive data stored with AES-256-GCM encryption and PBKDF2 key derivation (100,000 iterations)
-   **Deterministic Identities:** Agents have stable, persistent identities with encrypted storage preventing key regeneration
-   **Centralized Encrypted Vault:** Private keys stored in AES-256 encrypted vault with master key protection
-   **Multi-Layer Authentication:** Advanced rate limiting, session management, and cryptographic challenge-response
-   **Brokered Access:** All sensitive operations require GuardianAgent authentication with encrypted authorization
-   **Zero Trust Architecture:** No component trusts any other without cryptographic verification
-   **Separation of Concerns:** Distinct agents for identity management, access brokering, and security validation

## 2. Components

### 🔐 `EncryptedVaultManager` - The Secure Ledger

-   **Role:** Acts as the production-grade encrypted storage system for all sensitive data
-   **Storage:** Manages AES-256 encrypted vault at `mindx_backend_service/vault_encrypted/` with master key protection
-   **Encryption:** All data encrypted with AES-256-GCM with PBKDF2 key derivation (100,000 iterations) and unique salt
-   **Key Storage:** Wallet private keys stored in `vault_encrypted/wallet_keys/keys.enc` with authenticated encryption
-   **API Keys:** All API keys encrypted and stored in `vault_encrypted/api_keys/keys.enc` with secure access
-   **Migration Support:** Automatic migration from legacy `.env` files to encrypted storage with verification

### 🆔 `IDManagerAgent` - The Identity Manager

-   **Role:** Acts as the interface layer between agents and the encrypted vault
-   **Integration:** Uses `EncryptedVaultManager` for all sensitive data operations with encrypted lookup
-   **Key Naming:** Supports both legacy environment variable format and new encrypted vault entity IDs
-   **Primary Method (`get_or_create_wallet`):** Creates identities with encrypted storage and verification
-   **Belief System Integration:** Fast lookup cache with encrypted backend storage for security

### `GuardianAgent` - The Broker

-   **Role:** Acts as the gatekeeper for all access to sensitive private keys.
-   **Challenge-Response:** Implements a challenge-response protocol to verify the identity of any agent requesting a private key.
    1.  An agent requests a challenge for its `entity_id`.
    2.  The `GuardianAgent` generates and stores a unique, temporary token.
    3.  The requesting agent must sign this token with its private key.
    4.  The `GuardianAgent` uses `IDManagerAgent.verify_signature` to confirm the signature is valid for the public key associated with that `entity_id`.
-   **Key Release:** Only if the signature is verified does the `GuardianAgent` call the privileged `id_manager.get_private_key_for_guardian()` method to retrieve and return the private key.

## 3. ✅ Production Security Implementation: AES-256 Encrypted Vault

The production-grade security system has been **fully implemented and deployed** with enterprise-level encryption and security controls.

### 🔒 **Implemented Features:**
-   **AES-256-GCM Encryption:** All sensitive data encrypted with authenticated encryption
-   **PBKDF2 Key Derivation:** 100,000 iterations with unique salt for maximum security
-   **Master Key Protection:** Encryption keys secured with additional key derivation layer
-   **Automatic Migration:** Seamless transition from legacy `.env` files to encrypted storage
-   **Zero Downtime Deployment:** Production systems can migrate without service interruption

### 🛡️ **Advanced Security Features:**
-   **Rate Limiting:** Multi-algorithm rate limiting with client reputation tracking
-   **Security Middleware:** Real-time threat detection and automated response
-   **Session Management:** Secure session handling with encrypted token storage
-   **Access Control:** Fine-grained permissions with encrypted authorization
-   **Audit Logging:** Complete security operation trails with encrypted log storage

### 🚀 **Future Enhancements:**
-   **Hardware Security Modules (HSM):** Integration with dedicated cryptographic hardware
-   **Multi-Factor Authentication:** Additional authentication layers for critical operations
-   **Zero-Knowledge Proofs:** Advanced cryptographic protocols for enhanced privacy
-   **Quantum-Resistant Cryptography:** Future-proofing against quantum computing threats

## 4. Dependabot / dependency vulnerabilities

- **qs (npm), high – arrayLimit bypass DoS**  
  Dependabot reported `qs` &lt; 6.14.1 (used transitively by Express/body-parser) as vulnerable to memory-exhaustion DoS via bracket notation. **Remediation:** Added `"overrides": { "qs": ">=6.14.1" }` in `mindx_frontend_ui/package.json` and `mindx_frontend_ui_backup/package.json`, then ran `npm install`. Lockfiles now resolve `qs` to 6.14.1; `npm audit` reports 0 vulnerabilities. (Date: 2026-02-07.)
