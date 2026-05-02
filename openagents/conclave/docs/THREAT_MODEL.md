# CONCLAVE Threat Model

## Trust assumptions

CONCLAVE assumes:

1. **Each member trusts their own host** to keep its Ed25519 private key
   secret. CONCLAVE provides no defence against a member whose machine
   is fully compromised.
2. **The Yggdrasil mesh provides path-secrecy.** Intermediate routing
   nodes see ciphertext only.
3. **The chain is honest about reads.** `Tessera`, `Censura`, and
   `ConclaveBond` reflect their on-chain state correctly.
4. **At least the convener follows the protocol.** A malicious convener
   can stall a session but cannot fabricate signed votes; the rest of
   the protocol degrades gracefully (see §Convener misbehaviour).

## Adversary model — line by line

### A1 · Mesh router eavesdropping

*Capability:* observe Yggdrasil traffic between any two peers.

*Mitigation:* End-to-end encryption is part of the Yggdrasil link
layer. AXL adds an additional TLS layer between directly peered nodes.
Routers see ciphertext only, with no usable metadata beyond
source/destination IPv6 addresses (which already are public keys).

*Residual risk:* traffic analysis. Two peers exchanging large bursts
of bytes are observable as such, even if the bytes are opaque. v0.1
does not pad or chaff; high-stakes deployments should add cover traffic.

### A2 · Pubkey spoofing / forged messages

*Capability:* claim to be a member by sending an envelope with their
`from` set to a member's pubkey.

*Mitigation:* Every envelope is Ed25519-signed over its canonical CBOR
encoding. The dispatcher validates `verify_key(sig)` against
`payload`, and **also** that `env.from_` matches the AXL transport
peer-id (`X-From-Peer-Id`). Both checks are required: the second
prevents a member from injecting envelopes claiming to come from a
different member they happen to share a session with.

*Residual risk:* nonexistent.

### A3 · Replay

*Capability:* re-broadcast a captured signed envelope, hoping the
receiver re-applies it (e.g. resubmit an old vote).

*Mitigation:* Envelopes carry a strictly monotonic `seq` per
`(session_id, from)` pair. The receiver tracks `last_seq_by[from]` and
rejects any envelope with `seq <= last`. The signature scope includes
`seq`, so an attacker cannot rewrite it.

*Residual risk:* nonexistent within a session. Cross-session replay is
prevented by including `session_id` in the signed payload.

### A4 · Sybil membership

*Capability:* spin up many AXL nodes and try to enter conclaves.

*Mitigation:* Membership is gated by `Conclave.sol`, which itself
defers to `Tessera` (soulbound credential) and `Censura` (reputation
score). A sybil has no Tessera credential and zero Censura. Even if
they bribe their way to a Tessera, the `censura_min` parameter on a
Conclave excludes new accounts.

*Residual risk:* Tessera issuer compromise. If the BONAFIDE Tessera
issuer is captured, the attacker can mint credentials. Mitigation is
out of scope for CONCLAVE; the BONAFIDE Senatus contract handles
issuer rotation.

### A5 · Member leaks transcript

*Capability:* a member of a conclave publishes the full signed
transcript (or any portion) outside the chamber.

*Mitigation (deterrence):* `ConclaveBond` locks a stake before the
member is seated. Other members can submit a leak proof to
`Conclave.slashForLeak()`, which calls `ConclaveBond.slash()` and
emits `MemberSlashed`. The slashed member is also Censura-reported.

*Limitations:* v0.1 trusts the convener to validate the proof. A more
trust-minimised v0.2 will use a zk proof of "this content matches a
signed envelope under session_id X" verified on chain.

*Residual risk:* a determined member who values the leak more than
their stake will leak anyway. The bond sets a price, not a wall.

### A6 · Convener misbehaviour

*Capability:* the convener is a member of the conclave with
co-ordination authority. They could:

- (a) Refuse to broadcast a `SessionOpen` despite quorum being met.
- (b) Refuse to anchor a `Resolution` whose outcome they dislike.
- (c) Anchor a Resolution with falsified `voters[]`.

*Mitigations:*

- (a) Members detect missing `SessionOpen` and `Censura.report()` the
  convener after `manifest.expiry`.
- (b) Members detect missing `Resolution` and either accept the
  outcome off-chain (the signed votes are sufficient evidence) or
  `Censura.report()` the convener.
- (c) `Conclave.sol` rejects a `recordResolution` whose voters are not
  currently seated. It cannot detect falsified voters where every named
  voter *is* seated, but a signed vote count below quorum is publicly
  verifiable from the transcript: any honest member can submit a
  counter-claim.

A future version will require N-of-M signatures on the on-chain anchor
itself, removing the convener's ability to fabricate. For v0.1 the
convener is socially-trusted with cryptographic accountability.

### A7 · Compromised endpoint exfiltrates content

*Capability:* malware on a member's machine reads memory while the
session is ACTIVE.

*Mitigation:* Out of scope at v0.1. Host security is the operator's
problem. The protocol limits damage by:

- Wiping in-memory state at `Adjourn`.
- Never persisting transcripts to disk (operators may opt in).
- Capability invocations (MCP) returning results to the caller only —
  if Member A asks Member B's CFO model for a number, the result lives
  only in A's process, not in the conclave-wide transcript.

### A8 · Network partition

*Capability:* a faction of the mesh is partitioned off from the rest.

*Mitigation:* Yggdrasil heals automatically when connectivity returns.
CONCLAVE's session lifecycle uses absolute timestamps (`expiry`,
`session_ttl`), so a partition longer than the timeout aborts the
session cleanly. Members receiving stale envelopes after a heal
detect them via `seq` regression and drop them.

### A9 · Dishonest tally

*Capability:* the convener under-counts votes for an unfavoured
motion.

*Mitigation:* Every vote is a signed envelope broadcast to the full
mesh. Any honest member can compute the tally locally and compare to
the convener's `Resolution`. A divergence is publicly verifiable
evidence of misbehaviour and triggers `Censura.report()`.

## Out of scope at v0.1

- **Quantum adversary.** Ed25519 is not post-quantum.
- **Side channels** (timing, cache, EM).
- **Coercion of a seated member.** If you can compel the CFO to vote a
  specific way, the protocol cannot tell.
- **DNS / bootstrap availability.** AXL needs at least one reachable
  bootstrap peer to join the mesh; total isolation is out of scope.

## Security checklist for operators

1. Generate Ed25519 keys with `openssl genpkey -algorithm ed25519` on
   the operator's own machine; never accept a pre-generated key.
2. Verify each Cabinet member's pubkey out-of-band (phone, in-person)
   before a high-stakes conclave.
3. Keep the AXL node's bridge bound to `127.0.0.1` only — never expose
   it on a public interface. Other members reach you over the mesh,
   not the bridge.
4. Run conclave processes in a hardened sandbox (Podman, OpenBSD vmm,
   gVisor) that has no other privileges.
5. After Adjourn, restart the conclave process to clear residual heap
   state.
6. Publish only the redacted summary; treat the full transcript as
   trade secret unless the conclave votes to release.
