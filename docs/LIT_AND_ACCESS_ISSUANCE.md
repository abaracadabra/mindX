# Lit Protocol Review and mindX Access Issuance

## How Lit Protocol Solves Social Login and Access

### Lit’s model

1. **Identity via social / OAuth (not wallet-first)**  
   Users sign in with Google or Discord. The Lit Relay and providers (`@lit-protocol/lit-auth-client`) handle OAuth; `signIn()` starts the flow, and after redirect `handleSignInRedirect()` / `authenticate()` return an **AuthMethod** (e.g. OAuth token).

2. **PKP (Programmable Key Pair)**  
   That AuthMethod is used to **mint or fetch a PKP** — a decentralized key pair managed by the Lit network, bound to the social account. So “identity” in Lit is: social login → PKP (public key). The user doesn’t need a wallet to get a PKP.

3. **SessionSigs**  
   After auth, the app gets **SessionSigs** for that PKP (e.g. via `getSessionSigs({ authMethod, pkpPublicKey, ... })`). Those signatures authorize access to resources (e.g. decrypt content, call Lit Actions) for a limited time.

4. **Access control conditions (ACCs)**  
   Lit locks content or actions behind **on-chain conditions**:
   - **EVM basic**: ERC20 / ERC721 / ERC1155 (e.g. `balanceOf` ≥ threshold, or “owns token id”).
   - **EVM custom**: Any contract call + `returnValueTest` (e.g. “must have ≥1 share in this DAO”).
   - **Boolean logic**: AND/OR over conditions (e.g. “holds NFT X **and** (holds token Y **or** balance ≥ Z)”).

So in Lit: **social login → PKP (identity) → SessionSigs (session)** and **ACCs (token/NFT/contract) gate who can decrypt or act**.

---

## mindX Mapping: Wallet Signature as Proof of Identity

mindX does **not** use Lit’s social login or PKPs. Identity is:

- **Proof of identity** = **wallet signature** over a server-issued challenge.
- **Public key** = **wallet address** (Ethereum-style).
- **Session** = vault-backed session token issued only after signature verification.

So we already have:

- **Who are you?** → “I control this address” (signature from that address).
- **Session** → Issued only when that signature is valid; stored and validated in the vault.

The Lit analogue is: our “AuthMethod” is “wallet signs challenge”; our “PKP” is the wallet address; our “SessionSigs” are the session token.

---

## When the Public Key Must Hold an NFT or Fungible for Access

Lit’s idea: **access (e.g. decrypt, or “can use this app”) can be gated on on-chain state** — e.g. “holds NFT X” or “holds ≥ N of token Y”.

In mindX we can do the same for **issuance of access**:

- **Identity** is still proved by **wallet signature** (public key = address).
- **Issuance of access** (issuing the session / vault folder) can be **optionally** gated on:
  - **Fungible**: address holds ≥ *min_balance* of token at contract *C* on chain *chain_id*.
  - **NFT**: address owns a specific token id, or holds ≥ 1 of a given ERC721/ERC1155.

So:

- **No token gate** → signature alone is enough; session and vault folder are issued as today.
- **Token gate enabled** → we still require a valid signature, then we **additionally** check on-chain (ERC20 balance or ERC721/ERC1155 ownership). Only if the check passes do we issue the session (and thus vault folder access).

That keeps “identity = public key that signed” and adds “issuance of access = optional NFT/fungible requirement for that same public key”.

---

## What We Built

1. **Configurable token gate** (`mindx_backend_service/access_gate.py`), driven by environment variables:
   - **Gate on/off**: `MINDX_ACCESS_GATE_ENABLED=true`
   - **RPC**: `MINDX_ACCESS_GATE_RPC_URL=https://...` (required when gate is on)
   - **Contract**: `MINDX_ACCESS_GATE_CONTRACT=0x...`
   - **Type**: `MINDX_ACCESS_GATE_TYPE=erc20` or `erc721`
   - **ERC20**: `MINDX_ACCESS_GATE_MIN_BALANCE=1` (min balance in smallest units)
   - **ERC721**: `MINDX_ACCESS_GATE_TOKEN_ID=123` (require owning this token id), or omit for “balanceOf ≥ 1”

2. **Check at login**  
   In `register-with-signature`, after signature verification and before creating the session:
   - If token gate is enabled, we call `eth_call` to check the wallet’s balance or ownership.
   - If the condition is not met → **403** and a clear message (e.g. “Access requires holding at least 1 token(s) at 0x...”).
   - If met (or gate disabled) → issue session and vault folder as today.

3. **No change to “identity”**  
   Identity remains “wallet signature from this public key”. The token gate only affects **whether we issue access** to that identity.

---

## Summary Table

| Concept              | Lit Protocol                    | mindX (this implementation)                    |
|----------------------|----------------------------------|-----------------------------------------------|
| Proof of identity    | Social OAuth → PKP               | Wallet signature over challenge               |
| Public key           | PKP public key                  | Wallet address (Ethereum)                      |
| Session              | SessionSigs for PKP              | Vault-backed session token                    |
| Gating access        | ACCs (NFT, ERC20, custom call)   | Optional token gate at session issuance       |
| Where gating applies | Decryption / Lit Actions         | Issuance of session + vault folder access     |

If you later want **Lit-based** flows (e.g. social login → PKP, or Lit ACCs for decryption), that can sit alongside this: we keep wallet-signature identity and optional NFT/fungible gating for issuance, and add Lit where needed for specific features.
