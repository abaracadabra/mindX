# Security policy — ephermaleth

## What this library is for

Proving *who signed what, in what order* — an integrity primitive, not a secrets
store and not a consensus engine. It holds **public** material only (signatures,
addresses, hashes). Private keys live in your `Signer` (a vault, an HSM, a
keymap), never here.

## Guarantees

- **Integrity, not confidentiality.** Chains and ledgers are meant to be read.
- **Verify with public keys only.** No trust in the publisher is required —
  `verify_chain` / `verify_ledger` recover every signer and re-check every hash.
- **Injective signing.** A signature is bound to exactly one field-tuple; the
  challenge cannot be made ambiguous by crafted identities (see [AUDIT.md](AUDIT.md)).
- **Honest about gaps.** An identity without a key produces an *attested-but-
  unsigned* link — reported, never silently counted as signed.

## Using it safely

- **Always pass a `registry`** (`{agent_id: address}`) when you know the
  identities. Without it, a verifier confirms a link is self-consistent but not
  that the signer is the *right* seat.
- **Treat a payload hash as a commitment, not a truth oracle.** The chain proves
  every seat signed the same bytes; it does not judge those bytes.
- **Keep the `Signer` boundary tight.** The oracle is the only place a key is
  touched; do not log it, and re-lock/zeroize on the vault side after signing.

## Reporting

This is a cypherpunk2048 / BANKON module — source is public, fork it, and open an
issue or PR at <https://github.com/cypherpunk2048>. Coordinated disclosure
preferred for anything that breaks the injectivity or recovery guarantees above.
