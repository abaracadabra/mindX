# x402 payment rails — credential issuance as a service

> *Part of the [cypherpunk2048 standard](README.md). EIP references are
> definitive and absolute — see [`EIP_REFERENCES.md`](EIP_REFERENCES.md).*

`tools/x402_rails.py` is the backing implementation for `x402rails.agent`. It
turns the signature-based signer in `tools/x402_signer.py` into a **service**: a
holder of signing wallets that issues **payment credentials** to other agents on
demand, so a consuming agent can settle an x402-gated request **without ever
holding the private key**.

This is the cleanest expression of two cypherpunk2048 rules at once — the
*no-trapdoors rule* (every settlement is signature-authorized; there is no
key-bypass path) and the *vault-as-oracle rule* (the wallet offers *use of a
key*, never the key itself).

---

## 1. What it is

The unit of exchange is a **`PaymentCredential`** — a signed, single-use
`X-PAYMENT` authorization plus the settlement metadata describing it. The
service:

1. reads an HTTP `402 Payment Required` challenge (or is handed one),
2. enforces a **per-call budget** and a **per-rail allowlist**,
3. signs an **ERC-3009 `transferWithAuthorization`** through the wallet for the
   named rail, and
4. returns the credential.

The wallet key stays inside the service; what crosses the boundary is the
signature.

```
consumer ──"a credential for this challenge"──▶  X402RailsService
                                                      │  (holds the wallets)
                                                      │  budget + allowlist gate
                                                      │  ERC-3009 / EIP-712 sign
                                                      ▼
consumer ◀──── PaymentCredential (X-PAYMENT) ────────┘   key never leaves
   │
   └── attaches credential.as_headers() to its retried request → 200
```

A consumer asks for *"a credential for this challenge"*, not for a chain — so
new rails register without touching call sites (the *substitution-readiness
rule*).

---

## 2. The EIPs it composes (naming from the EIP, verbatim)

Every credential is, by the books — **all references absolute at
[`eips.ethereum.org/EIPS`](https://eips.ethereum.org/EIPS)**:

| Ref | Title (verbatim) | Role in the credential |
|---|---|---|
| [ERC-3009](https://eips.ethereum.org/EIPS/eip-3009) | Transfer With Authorization | the signed `transferWithAuthorization` mechanism; random single-use `nonce`, `validAfter`/`validBefore` window |
| [EIP-712](https://eips.ethereum.org/EIPS/eip-712) | Typed structured data hashing and signing | how the `TransferWithAuthorization` struct is hashed and signed |
| [EIP-155](https://eips.ethereum.org/EIPS/eip-155) | Simple replay attack protection | the `chainId` in the EIP-712 domain / the `eip155:8453` network id |
| [ERC-20](https://eips.ethereum.org/EIPS/eip-20) | Token Standard | the asset moved (USDC; 6 decimals → `USDC_MINOR_UNITS = 1_000_000`) |
| [ERC-191](https://eips.ethereum.org/EIPS/eip-191) | Signed Data Standard | the byte-level signing envelope EIP-712 specialises |
| [ERC-1271](https://eips.ethereum.org/EIPS/eip-1271) | Standard Signature Validation Method for Contracts | the contract-wallet / multisig payer verification path |

The dependency graph (`ERC-3009 → {ERC-20, EIP-712}`, `EIP-712 → {EIP-155,
ERC-191}`) and what each contributes are spelled out in
[`EIP_REFERENCES.md`](EIP_REFERENCES.md).

---

## 3. The pieces

| File | Role |
|---|---|
| [`tools/x402_rails.py`](../../tools/x402_rails.py) | `X402RailsService` — holds wallets, issues `PaymentCredential`s, keeps a ledger |
| [`tools/x402_signer.py`](../../tools/x402_signer.py) | `base_usdc_x402_signer` — the built-in Base rail; ERC-3009 / EIP-712 signing; budget decline |
| [`tools/cmc_client.py`](../../tools/cmc_client.py) | `decode_payment_challenge` — format-tolerant 402 decoder; `X402_BASE_URL` |
| [`agents/x402rails.agent`](../../agents/x402rails.agent) | the agent card describing the service |

A **rail** is a `(network, wallet)` settlement leg. The Base-USDC rail is built
in and lazy — the service can be constructed and advertised *before* a wallet
key is configured; the key is only required at the first issuance on that rail.

---

## 4. Usage

### 4.1 Issue a credential, settle yourself

```python
from tools.x402_rails import X402RailsService

# Default per-call ceiling 0.05 USDC; pass a logger for an audit line per issue.
rails = X402RailsService(max_amount_usdc=0.05, logger=print)

# Hand it a decoded challenge (e.g. from cmc_client.decode_payment_challenge):
credential = rails.issue_from_challenge(challenge)

# Attach and resend your own request:
import httpx
resp = httpx.get(url, headers=credential.as_headers())
```

`credential.to_dict()` is the JSON wire form an agent receives — self-auditing:
`rail`, `network`, `asset`, `amount_usdc`, `payer`, `recipient`, `expires_at`,
`nonce`, `issued_at`.

### 4.2 Probe a URL, then settle in one call

```python
rails = X402RailsService()

# Issue only (does not pay):
cred = rails.issue_for_url("/examples/weather", {"city": "lisbon"})

# Or the full 402 → sign → resend cycle, end to end:
data = rails.settle("/examples/weather", {"city": "lisbon"})
```

`issue_for_url` / `settle` use `X402_BASE_URL` for relative URLs; pass an
`httpx.Client` (`http=`) to reuse a session or target another host.

### 4.3 Register another rail (substitution-readiness)

```python
from tools.x402_avm_client import X402AvmClient  # Algorand leg

rails.register_rail(
    "algorand",
    signer=avm_signer,                       # callable(challenge) -> X-PAYMENT
    networks=("algorand-mainnet",),
    max_amount_usdc=0.05,
)
# Call sites are unchanged — issue_from_challenge now routes algorand challenges here.
```

### 4.4 Advertise + audit

```python
rails.describe()   # agent-card-style: offered rails, networks, default ceiling
rails.ledger       # the audit trail of credentials issued this session
```

---

## 5. Interaction model (who talks to whom)

```
┌──────────────────┐   "credential for     ┌─────────────────────┐
│  Consumer agent  │    this challenge"     │  X402RailsService   │
│  (BDI / marketing│ ─────────────────────▶ │  tools/x402_rails   │
│   onchain / AP2) │                        │  ┌───────────────┐  │
│                  │ ◀───PaymentCredential──│  │ base rail     │  │
└────────┬─────────┘   (X-PAYMENT, no key)  │  │ x402_signer   │──┼─▶ BANKON Vault
         │                                  │  └───────────────┘  │   (key never
         │ attaches headers, resends        │  ┌───────────────┐  │    leaves)
         ▼                                  │  │ algorand rail │  │
   x402-gated endpoint ──── 200 ───────────▶│  │ x402_avm (opt)│  │
   (mindx.pythai.net,                       │  └───────────────┘  │
    AgenticPlace, …)                        └─────────────────────┘
```

- **Consumers** — BDI agents, the marketing on-chain clients
  ([`agents/marketing/onchain/x402_receipt_client.py`](../../agents/marketing/onchain/x402_receipt_client.py)),
  AgenticPlace marketplace legs. They hold **no keys**.
- **Companions** — [`tools/x402_avm_client.py`](../../tools/x402_avm_client.py)
  (Algorand), [`tools/keeperhub_x402_client.py`](../../tools/keeperhub_x402_client.py)
  (Base/Tempo EIP-3009). These are *self-signing clients*; the rails service is
  the *credential issuer* that lets a keyless consumer settle.
- **Vault** — `tools/x402_signer.py` resolves the Base key from an explicit
  argument, then `BASE_X402_PRIVATE_KEY`, then the BANKON vault deposit
  `base_x402_private_key`. It is read into a closure and **never returned**.

The server side of the same protocol (mindX *charging* for its endpoints, the
triple-rail envelope, the facilitator, the receipt anchor) is specified in
[`docs/services/x402_as_a_service.md`](../services/x402_as_a_service.md) and
[`docs/X402.md`](../X402.md). The rails service is the **client side**, packaged
as a keyless service.

---

## 6. cypherpunk2048 conformance

| Rule | How `x402_rails` upholds it |
|---|---|
| **no-trapdoors** | Every settlement is a wallet signature. There is no path to settle without one; an over-budget challenge is **declined**, not coerced. |
| **vault-as-oracle** | The key lives in exactly one place (vault / env deposit), is mediated by `x402_signer`, and is never exfiltrated. The service offers *use of a key*, not the key. |
| **attribution** | Each issued credential is a self-auditing record (`payer`, `recipient`, `amount`, `nonce`, `expires_at`, `issued_at`) and lands in the session ledger. |
| **substitution-readiness** | Rails register by name; consumers ask for a credential for a challenge, never for a chain. Adding the Algorand leg touches no call site. |

These four rules are the standard's primitives, defined in
[`README.md`](README.md) and the canonical essay
[`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md).

---

## 7. Configuration

| Setting | Where | Meaning |
|---|---|---|
| `base_x402_private_key` | BANKON Vault (preferred) | Base USDC signing wallet for the built-in rail |
| `BASE_X402_PRIVATE_KEY` | env (fallback) | Same key as an environment deposit |
| `MINDX_X402_BASE_URL` | env | Default base URL for relative URLs in `issue_for_url` / `settle` |
| `max_amount_usdc` | constructor arg | Default per-call ceiling (whole USDC); per-rail override on `register_rail` |

Required Python deps (already in [`requirements.txt`](../../requirements.txt)):
`httpx>=0.28.1`, `eth-account>=0.13.0`.

---

## 8. References

- [`README.md`](README.md) — the cypherpunk2048 standard index
- [`EIP_REFERENCES.md`](EIP_REFERENCES.md) — definitive EIP/ERC table (absolute URLs)
- [`docs/services/x402_as_a_service.md`](../services/x402_as_a_service.md) — server side of x402 in mindX
- [`docs/X402.md`](../X402.md) — the canonical mindX x402 reference (triple-rail, receipts, multisig)
- [`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md) — the standard, in mindX's voice
- [x402.org](https://x402.org) — the HTTP 402 wire standard
- [`eips.ethereum.org/EIPS`](https://eips.ethereum.org/EIPS) — the definitive EIP registry
