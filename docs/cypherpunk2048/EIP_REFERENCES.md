# EIP / ERC references — the definitive table

> The cypherpunk2048 standard anchors its on-chain primitives on the Ethereum
> Improvement Proposals, not on a vendor SDK. This file is the **definitive
> reference**: every EIP/ERC the mindX payment and identity surfaces depend on,
> by its **exact official title** (the name the EIP itself carries), with the
> **absolute canonical URL** at [`eips.ethereum.org`](https://eips.ethereum.org/EIPS).
> Descriptions in code and docs quote these titles verbatim — naming from the
> EIP *is* the description.

Titles and statuses below are taken from the canonical front-matter of each
proposal (`ethereum/EIPs` and the migrated `ethereum/ERCs` registries).

## The table

| Ref | Official title (use verbatim as description) | Status | Absolute reference |
|---|---|---|---|
| **ERC-20** | Token Standard | Final | https://eips.ethereum.org/EIPS/eip-20 |
| **ERC-191** | Signed Data Standard | Final | https://eips.ethereum.org/EIPS/eip-191 |
| **EIP-155** | Simple replay attack protection | Final | https://eips.ethereum.org/EIPS/eip-155 |
| **EIP-712** | Typed structured data hashing and signing | Final | https://eips.ethereum.org/EIPS/eip-712 |
| **ERC-1271** | Standard Signature Validation Method for Contracts | Final | https://eips.ethereum.org/EIPS/eip-1271 |
| **ERC-3009** | Transfer With Authorization | Draft (Standards Track, ERC) | https://eips.ethereum.org/EIPS/eip-3009 |

> Naming note. ERC-20, ERC-191, ERC-1271, and ERC-3009 are Standards-Track
> proposals in the **ERC** category; they are commonly cited both as `EIP-N`
> and `ERC-N`. The canonical browse path `eips.ethereum.org/EIPS/eip-N`
> resolves either way. mindX prefers the `ERC-N` form for the four
> interface/token standards and `EIP-N` for the two core/interface protocol
> proposals (155, 712), matching each proposal's own category.

## The dependency graph (why these six, in this order)

The settlement credential mindX issues is a small, exact composition. Each EIP
*requires* the ones beneath it, so the stack is not arbitrary:

```
ERC-3009  Transfer With Authorization        requires 20, 712
   │
   ├── EIP-712  Typed structured data         requires 155, 191
   │      hashing and signing
   │        ├── EIP-155  Simple replay attack protection   (the chainId)
   │        └── ERC-191  Signed Data Standard               (the signing envelope)
   │
   └── ERC-20   Token Standard                              (the asset moved: USDC)

ERC-1271  Standard Signature Validation Method for Contracts   (the multisig / contract-wallet payer path)
```

`requires` edges are the literal `requires:` front-matter of each proposal:
ERC-3009 `requires: 20, 712`; EIP-712 `requires: 155, 191`.

## What each contributes to the x402 credential

- **ERC-3009 — Transfer With Authorization.** The mechanism. A payer signs a
  `transferWithAuthorization` authorizing a transfer of an ERC-20 asset, with a
  **random 32-byte `nonce`** (single-use, not sequential) and a
  `validAfter`/`validBefore` window. The payer holds no native gas; a
  facilitator submits the transaction. This is exactly the single-use,
  self-expiring credential a payment-rails service wants to hand out.
- **EIP-712 — Typed structured data hashing and signing.** How the
  `TransferWithAuthorization` struct is turned into a signable digest, with a
  domain separator binding the signature to a specific token contract and
  chain. Human-verifiable, machine-verifiable, replay-resistant across domains.
- **EIP-155 — Simple replay attack protection.** Supplies the `chainId` inside
  the EIP-712 domain (and is the namespace behind the `eip155:8453` network id
  used in x402 challenges; `8453` is Base mainnet). Stops a signature valid on
  one chain from replaying on another.
- **ERC-20 — Token Standard.** The asset moved. USDC is an ERC-20 token; its
  contract address is the EIP-712 domain's `verifyingContract`. USDC carries 6
  decimals — `1 USDC = 1_000_000` minor units (`USDC_MINOR_UNITS`).
- **ERC-191 — Signed Data Standard.** The byte-level envelope (`0x19` prefix
  family) under which structured data is signed; EIP-712 is the `0x19 0x01`
  variant.
- **ERC-1271 — Standard Signature Validation Method for Contracts.** The path
  for a **contract-wallet payer** (e.g. a Safe / multisig): when `from` is a
  contract, a verifier calls `isValidSignature(hash, signature)` instead of
  recovering an EOA. This is the EVM half of the multisig story whose Algorand
  half is the native merged-multisig form (see [`docs/X402.md`](../X402.md)).

## Where these references live in the code

| Reference | Code surface |
|---|---|
| ERC-3009, EIP-712, EIP-155, ERC-20 | [`tools/x402_signer.py`](../../tools/x402_signer.py) — `base_usdc_x402_signer` builds the `TransferWithAuthorization` typed-data and signs it |
| ERC-3009 (envelope decode) | [`tools/x402_rails.py`](../../tools/x402_rails.py) — `_credential_from_payload` |
| ERC-3009, EIP-712 (Tempo + Base) | [`tools/keeperhub_x402_client.py`](../../tools/keeperhub_x402_client.py) — `_EIP3009_DOMAINS`, `_sign_payment` |
| ERC-1271 (multisig payer) | [`docs/X402.md`](../X402.md) §Multisig; future `X402Receipt.sol` verify path |
| EIP-712 v2 (campaign receipts) | `MarketingAttributionReceipt.sol` (see [`docs/MARKETING_RECEIPTS.md`](../MARKETING_RECEIPTS.md)) |

## Adjacent, non-EIP standards (named for completeness)

These travel alongside the EIPs in x402 challenges but are *not* Ethereum
Improvement Proposals; they are cited here only so the EIP table above is not
confused for the whole picture:

- **CAIP-2** — chain-agnostic chain identifiers (`eip155:8453`). The `eip155`
  namespace references EIP-155 chain ids. https://chainagnostic.org/CAIPs/caip-2
- **x402** — the HTTP `402 Payment Required` envelope and `X-PAYMENT` header
  flow. https://x402.org

---

*Maintained as part of the [cypherpunk2048 standard](README.md). When a new
on-chain primitive enters the mindX payment or identity surface, add its EIP
here first — with the verbatim title and the absolute `eips.ethereum.org` URL —
then reference it from the code.*
