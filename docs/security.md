# MindX Security Model

This document outlines the core security principles and components of the MindX system, focusing on identity management and secure key handling.

## 1. Core Principles

-   **Deterministic Identities:** Agents should have stable, persistent identities. An agent's key should not be regenerated every time the system starts.
-   **Centralized Key Storage:** Private keys are sensitive and should be stored in a single, secure, and isolated location.
-   **Brokered Access:** No agent can get a Mastermind-verified public key without going through the `GuardianAgent`. Access must be arbitrated by a trusted security agent.
-   **Separation of Concerns:** The agent responsible for managing keys (`IDManagerAgent`) should be distinct from the agent that brokers access to them (`GuardianAgent`).

## 2. Components

### `IDManagerAgent` - The Ledger

-   **Role:** Acts as a pure, centralized ledger for cryptographic keys.
-   **Storage:** Manages a single, central key store at `data/identity/.wallet_keys.env`. This file is created with restrictive permissions.
-   **Key Naming:** Keys are stored deterministically based on the `entity_id` (e.g., `MINDX_WALLET_PK_MASTERMIND_PRIME`).
-   **Primary Method (`get_or_create_wallet`):** This is the main entry point for identity creation. It first checks if a key for the given `entity_id` already exists. If it does, it returns the existing identity. If not, it creates, stores, and returns a new one. This prevents key duplication.
-   **Belief System Integration:** To provide a fast, two-way lookup between an `entity_id` and its `public_address`, the `IDManagerAgent` records this mapping in the shared `BeliefSystem` upon key creation.

### `GuardianAgent` - The Broker

-   **Role:** Acts as the gatekeeper for all access to sensitive private keys.
-   **Challenge-Response:** Implements a challenge-response protocol to verify the identity of any agent requesting a private key.
    1.  An agent requests a challenge for its `entity_id`.
    2.  The `GuardianAgent` generates and stores a unique, temporary token.
    3.  The requesting agent must sign this token with its private key.
    4.  The `GuardianAgent` uses `IDManagerAgent.verify_signature` to confirm the signature is valid for the public key associated with that `entity_id`.
-   **Key Release:** Only if the signature is verified does the `GuardianAgent` call the privileged `id_manager.get_private_key_for_guardian()` method to retrieve and return the private key.

## 3. Future Direction: Google Secret Manager

While the current `.env` file approach is secure for local development, the long-term vision for a production-grade MindX system involves migrating all secret management to a dedicated service like **Google Secret Manager**.

This would involve:
-   Creating a new `GoogleSecretManagerHandler` that would replace the file-based `dotenv` calls in the `IDManagerAgent`.
-   Storing agent private keys as named secrets in the cloud.
-   Granting the service account running the MindX application the necessary IAM permissions to access these secrets.

This change will provide a more robust, auditable, and scalable security model suitable for production deployments, but is not yet implemented.
