# Quantum readiness — EVM is Tier-A (crypto-agile, PQ-ready)

This module conforms to **[CP2048-QR-1](https://github.com/cypherpunk2048)** at **Tier-A** — *honestly
labeled*. It is **not** post-quantum today, and nothing here should be read as claiming so.

## Self-certification (per CP2048-QR §6)

| Property | This module (EVM) |
|---|---|
| **Tier** | **Tier-A** — crypto-agile, post-quantum-**upgrade-ready** |
| **Signatures today** | secp256k1 ECDSA (EIP-712 vouchers, EIP-191 challenges, ERC-1271) — **Shor-breakable** |
| **Symmetric / hash** | AES-256-GCM, SHA-256 — Grover-survivable (conforming unchanged) |
| **Custody** | client-side wallet keys; no server custody of user signing keys |
| **PQC swap path** | pluggable verifier + account abstraction (below) |

## Why Tier-A and not Tier-Q

EVM cannot run native post-quantum signatures today; secp256k1 is hard-wired at the protocol level. The
post-quantum path on Ethereum is **account abstraction** (ERC-4337 → EIP-7702 → native AA **EIP-8141**,
under consideration for the Hegotá fork) giving accounts *signature agility* to adopt Falcon/ML-DSA;
the EF Post-Quantum program targets core PQC infrastructure ~2029.

## The swap point (already built)

The canonical iNFT verifies transfer proofs through a **pluggable** verifier:
`contracts/inft7857/bankon_inft_oracle.sol` implements `IERC7857DataVerifier` with an explicit
`OracleType { TEE, ZKP }` enum, and the iNFT only ever calls `verifier()`. A future
`bankon_inft_oracle_pqc` (Falcon/ML-DSA verification, or a STARK proof-of-Falcon to bound gas) drops in
behind the same interface with **no change to the iNFT, registrar, or TBA**. That is exactly what
"crypto-agile" requires — the scheme is a module, not a hard-wire.

Value-bearing state leans on **hash-based commitments** (SHA-256 Merkle roots, content addressing),
which are Grover-survivable, and **MAY anchor** to Algorand's Falcon **state proofs** over the x402
rail for cross-chain post-quantum finality without on-chain EVM PQC.

## The flagship is elsewhere

Genuine Tier-Q (quantum-native) lives on the **Algorand track via PARSEC** — Falcon per-connection
client-side keypairs anchored to Algorand state proofs — **not** in this EVM/ETHGlobal submission. See
`RAILS.md` in the standard. For judges and integrators: this module is *PQ-ready*, never *PQ-today*.
