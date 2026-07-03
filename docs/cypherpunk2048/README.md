# cypherpunk2048 — the standard, as mindX implements it

> The canonical public reference for the standard lives at
> [`github.com/cypherpunk2048`](https://github.com/cypherpunk2048). This
> directory is the **in-repo reference layer**: it ties the standard's four
> rules to the concrete mindX code that upholds them, and anchors every on-chain
> primitive on its **definitive EIP** — by exact title, at its absolute
> [`eips.ethereum.org`](https://eips.ethereum.org/EIPS) URL.

For the standard in mindX's own voice — what it codifies, why BANKON adopts it,
why mindX runs on it, why AgenticPlace publishes it — read the essay at
[`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md).
This README is the **implementer's** entry point.

---

## The four rules (one line each)

The standard composes four primitives. Each names a rule:

1. **substitution-readiness** — anchor on a hash *family*, not a hash function;
   a curve/primitive swap is a config change, not a migration.
2. **no-trapdoors** — if a feature works *without* the signature, the feature is
   wrong. No key-recovery bypass, no soft-delete that survives the crypto delete.
3. **vault-as-oracle** — secrets live in exactly one place; access is mediated
   and logged; the vault offers *signing* and *unwrapping*, never *exfiltration*.
4. **attribution** — if you cannot prove who did it, you cannot prove it
   happened. Every consequential action carries an EIP-191 / EIP-712 signature.

---

## The definitive EIP layer

cypherpunk2048 takes its on-chain primitives from the **Ethereum Improvement
Proposals**, by exact title, at absolute URLs — never from a vendor SDK. The
full table (titles verbatim, statuses, dependency graph) is
[`EIP_REFERENCES.md`](EIP_REFERENCES.md). The six load-bearing references:

| Ref | Title | Reference |
|---|---|---|
| ERC-20 | Token Standard | https://eips.ethereum.org/EIPS/eip-20 |
| ERC-191 | Signed Data Standard | https://eips.ethereum.org/EIPS/eip-191 |
| EIP-155 | Simple replay attack protection | https://eips.ethereum.org/EIPS/eip-155 |
| EIP-712 | Typed structured data hashing and signing | https://eips.ethereum.org/EIPS/eip-712 |
| ERC-1271 | Standard Signature Validation Method for Contracts | https://eips.ethereum.org/EIPS/eip-1271 |
| ERC-3009 | Transfer With Authorization | https://eips.ethereum.org/EIPS/eip-3009 |

---

## Reference implementations in this directory

| Doc | What it documents | Code |
|---|---|---|
| [`x402_rails.md`](x402_rails.md) | **x402 payment rails** — keyless credential issuance as a service; the cleanest expression of *no-trapdoors* + *vault-as-oracle* | [`tools/x402_rails.py`](../../tools/x402_rails.py), [`tools/x402_signer.py`](../../tools/x402_signer.py), [`tools/cmc_client.py`](../../tools/cmc_client.py), [`agents/x402rails.agent`](../../agents/x402rails.agent) |
| [`EIP_REFERENCES.md`](EIP_REFERENCES.md) | the definitive EIP/ERC table + dependency graph | — |

---

## How to add a conforming primitive

1. **Find the EIP first.** Add it to [`EIP_REFERENCES.md`](EIP_REFERENCES.md)
   with its verbatim title and absolute `eips.ethereum.org` URL. Naming from the
   EIP *is* the description — do not paraphrase the title.
2. **Compose, don't invent.** Reuse the existing auth primitives (vault signing,
   EIP-712 envelopes, the rails service) rather than minting a new one. The
   canonical reuse points are listed in the
   [standard essay](../publications/cypherpunk2048_standard.md#pattern-composition-one-wallet-many-surfaces).
3. **Check it against the four rules.** Every new doc here ends with a
   conformance table mapping the feature to substitution-readiness /
   no-trapdoors / vault-as-oracle / attribution (see
   [`x402_rails.md` §6](x402_rails.md#6-cypherpunk2048-conformance)).
4. **Cross-reference.** Link the code, link the EIPs, link back here. Then update
   [`docs/NAV.md`](../NAV.md).

---

## Related

- [`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md) — the standard, in mindX's voice
- [`docs/X402.md`](../X402.md) — the canonical mindX x402 reference
- [`docs/services/x402_as_a_service.md`](../services/x402_as_a_service.md) — x402 server side
- [`docs/BANKON_VAULT.md`](../BANKON_VAULT.md) — the vault that makes *vault-as-oracle* real
- [`docs/ATTRIBUTION.md`](../ATTRIBUTION.md) — the cypherpunk intellectual lineage
- [`github.com/cypherpunk2048`](https://github.com/cypherpunk2048) — the canonical public reference
