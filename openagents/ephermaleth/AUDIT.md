# ephermaleth — audit notes

Standalone audit of the attestation-chain + voting-booth library. This file is
itself operational transparency: the threat model and what was checked are
public, like the rubric of the thing it secures.

## Threat model

A published artifact (e.g. a "speech from the throne") carries a chain of
signatures asserting *who issued, wrote, edited, illustrated, and published it,
in that order*. An adversary controls the published bytes and wants to:

1. **Forge a link** — claim a seat signed when it did not.
2. **Reuse a signature** — lift a valid signature onto a different statement,
   seat, position, or chain.
3. **Reorder / splice** — move links, drop one, or graft links from another chain.
4. **Tamper a payload** — change what a seat supposedly attested.
5. **Tamper the ledger** — rewrite or reorder recorded council decisions.

The defender has only public keys and this code.

## Findings & resolutions

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| A | **Challenge canonicalization was ambiguous.** The signed message interpolated field values between ` | ` / `=` separators unencoded, so an identity like `"ceo | act=hijacked"` could smuggle structure across separators and make `build_challenge` non-injective — a single signature could satisfy two different field-tuples (signature reuse, finding #2). | **High** | `build_challenge` now percent-encodes the structural chars (`% | = \s`) out of every field (`_enc`), making the field-tuple → signed-string mapping injective. Verified by `test_challenge_is_injective_*` and `test_injection_link_does_not_reuse_a_signature`. |
| B | **Concurrent booth writers could collide.** `record()` read the tail and appended without a lock; two writers could compute the same `seq`/`prev` and interleave. | Medium | `record()` now holds a POSIX `flock` over the read-tail→append critical section (no-op fallback where `fcntl` is absent). |
| C | `from_dict` passed unknown keys straight into `ChainLink(**l)` → crash on a forward-compatible/extra field. | Low | Filters to declared dataclass fields. |
| D | No way to verify offline. | Low (usability) | Added `python -m ephermaleth verify <chain|html>` / `booth <jsonl>` CLI + console-script, exit-coded for CI. |

## What the verifier proves (and does not)

`verify_chain` proves, per link: the challenge reconstructs byte-for-byte from
the stored fields (so #4 tampering is caught), the prev/`link_hash` linkage is
intact (so #3 reorder/splice is caught), every *signed* link recovers to its
stated address (so #1 forgery is caught), and — when a `registry` is supplied —
that address is the *registered* identity (so a self-consistent throwaway key
can't impersonate a seat). Finding A closes #2. The booth's `verify_ledger`
extends #3/#4 to the record sequence (content hash + prev linkage per record).

It does **not** prove: that an unsigned ("attested") link's seat agrees — those
are reported, never counted as signed; that the *content* behind a payload hash
is what a human would call true — only that every seat signed the same hash;
nor liveness/availability (this is integrity, not consensus).

## Crypto

EIP-191 `personal_sign` via `eth_account` (optional dep). Signatures are
recovered, never trusted. ECDSA `s`-malleability is irrelevant: the exact
signature bytes are stored and re-recovered, and `link_hash` binds them. No
private key ever enters this library — signing is delegated to a `Signer` oracle.

## Tests

`python -m pytest tests/ -q` — 13 tests: full-chain verify, ordering/recovery,
tamper (payload/signature/linkage), registry mismatch, attest-only (NullSigner),
EnvKeystoreSigner, booth append/verify/tamper, **canonicalization injectivity**,
**injection-reuse rejection**, and the **CLI**.
