# Changelog — ephermaleth

All notable changes to this project. Dates are UTC.

## [0.1.0] — 2026-06-09

Initial extraction from mindX's "speech from the throne" provenance feature into
a standalone, agnostic library for possible inclusion in **bankoneth**.

### Added
- `AttestationChain` — hash-linked, multi-signer chain of custody (EIP-191).
- `verify_chain` — recover every signer, check linkage + registered identity.
- Pluggable `Signer` oracles: `NullSigner`, `KeymapSigner`, `EnvKeystoreSigner`,
  `OracleSigner` (the chain never holds a private key).
- `VotingBooth` — append-only, fsync'd, hash-linked ledger of council decisions
  (board / war council / DAIO / throne), each record content-addressed and able
  to embed its own attestation chain.
- `python -m ephermaleth verify|booth` CLI + `ephermaleth` console-script.
- README, AUDIT, SECURITY, tests (13), `py.typed`.

### Security
- Challenge strings are **injective** in their fields: every value is
  percent-encoded out of the structural separators, so a signature is bound to
  exactly one (chain, seq, role, agent, act, payload, prev) tuple — no
  separator-smuggling / signature reuse. (AUDIT finding A.)
- Voting-booth appends take a POSIX `flock` over the read-tail→append critical
  section. (AUDIT finding B.)
