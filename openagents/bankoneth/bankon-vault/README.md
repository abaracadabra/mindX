# bankon-vault

The **BANKON Vault** — isolated under `bankoneth/bankon-vault/`, used by **bankoneth only**. Encrypted
credential storage (AES-256-GCM + HKDF-SHA512), the shadow-overlord admin/signing tier, and the cabinet,
mounted by the gate backend. No runtime dependency on mindX (the two mindX integrations are optional
`try/except` and degrade to standalone).

## Layout
```
bankon-vault/
├── bankon_vault/         importable Python package (hyphens aren't valid identifiers, so the
│   │                     folder is bankon-vault and the package is bankon_vault)
│   ├── vault.py            BankonVault — encrypt/unlock/store, machine-bound .master.key
│   ├── routes.py           /vault/credentials/*  (admin-tier gated)
│   ├── sign_routes.py      /vault/sign/*  signing oracle
│   ├── admin_routes.py     /admin/shadow/*, /cabinet/*
│   ├── shadow_overlord.py  shadow-overlord privileged ops (+ optional catalogue events)
│   ├── overseer.py · cabinet.py · credential_provider.py · __init__.py
│   ├── data/               shadow_nonces.json (runtime, GITIGNORED)
│   └── tests/              3 tests
└── vault_bankon/         the encrypted STORE — .master.key, .salt, entries.json (GITIGNORED)
```

## Wiring (production)
The gate backend (`backend/app.py`) puts `bankon-vault/` on `sys.path`, imports `from bankon_vault import …`,
and points the store at this folder:
```python
VAULT_HOME = ROOT / "bankon-vault"
sys.path.insert(0, str(VAULT_HOME))
os.environ.setdefault("BANKON_VAULT_DIR",    str(VAULT_HOME / "vault_bankon"))
os.environ.setdefault("SHADOW_NONCES_PATH",  str(VAULT_HOME / "bankon_vault" / "data" / "shadow_nonces.json"))
```
`from bankon_vault import bankon_vault_router, vault_sign_router` + the admin/cabinet routers are mounted under
the `TierGate` (admin-tier only). The store dir also resolves standalone via the package's
`__file__.parent.parent / "vault_bankon"` fallback.

```bash
pip install -r bankon-vault/bankon_vault/requirements-vault.txt
PYTHONPATH=bankon-vault python -m pytest bankon-vault/bankon_vault/tests/ -q   # 3 passed
uvicorn backend.app:app --port 8800                                            # mounts /vault/*, /cabinet/*, /admin/shadow/*
```

## Security
- **Secrets never committed.** `.gitignore` covers `bankon-vault/vault_bankon/` (`.master.key`, `.salt`,
  `entries.json`) and `bankon-vault/bankon_vault/data/` (nonces). The `.master.key` is machine-bound; the
  overseer rotation path requires `MINDX_VAULT_ALLOW_OVERSEER_ROTATION` and snapshots before destructive ops.
- **Isolated.** No hard mindX imports — `routes.py` (mindX admin middleware) and `shadow_overlord.py`
  (catalogue events) are optional; without mindX the vault runs standalone in bankoneth.
- Audit + handoff: `docs/BANKON_VAULT.md`, `docs/TIERED_LOGIN.md`.
