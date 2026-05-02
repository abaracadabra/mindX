# Day 14 of 28 — Security

> *Lunar phase: full moon (day 14 of 29.5)*
> *2026-05-01 03:53 UTC*
> *Days to full moon: 1*

---


No trust required. Only cryptographic certainty.

- **BANKON Vault**: AES-256-GCM + HKDF-SHA512, PBKDF2-HMAC-SHA512 (600,000 iterations)
- **GuardianAgent**: monitors agent behavior, enforces security policies
- **Access Gate**: ERC20/ERC721 token gating for session issuance
- **Wallet auth**: ECDSA challenge-response — no passwords, only signatures
- **systemd**: `NoNewPrivileges=true`, `ProtectSystem=strict`
- **Apache**: HSTS, CSP, X-Frame-Options, SSL termination
- **Zero plaintext secrets** on disk — cypherpunk2048 standard