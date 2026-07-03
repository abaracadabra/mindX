# ephermaleth

**Verifiable chains of command, and a voting booth for councils.**

`ephermaleth` is a small, agnostic protocol-enhancement library. It does two
things, both with nothing but public-key cryptography and an append-only file:

1. **`AttestationChain`** — a hash-linked, multi-signer chain of custody. Each
   link is signed by a *different* identity's wallet (EIP-191). The chain is
   tamper-evident; anyone can verify the lineage by recovering each signer. Use
   it for a *speech from the throne* carried through a chain of command
   (issuer → author → editor → artist → publisher), a multi-party approval, or
   any provenance trail where "who signed off, in what order" must be provable.

2. **`VotingBooth`** — an append-only, hash-linked ledger that stores the
   decisions of a board and other councils (a war council, a DAIO, a conclave).
   Each record is content-addressed and chained to the previous one, and may
   embed its own `AttestationChain`. The whole booth re-verifies in one call.

It imports no application code. Bring your own **signer** (a wallet keymap, an
env keystore, or a vault/HSM oracle) and an optional **registry**
(`{agent_id: address}`) for identity checks.

## Design principles (from the BANKON Vault)

- **The root of trust is a Protocol, swappable.** The chain calls a pluggable
  `Signer(agent_id, message) -> (signature, address) | None`. Swap a keymap for
  a vault oracle for an HSM without touching the chain.
- **Keys never enter ephermaleth.** It holds signatures and public addresses
  only — the signing oracle returns a signature, never a key (the vault's
  `/vault/sign` model).
- **Domain separation.** Every challenge string is namespaced + versioned
  (`ephermaleth/v1 | chain=… | seq=… | …`), like an HKDF `info`, so a signature
  for one chain can't be replayed into another.
- **Append-only, fsync'd, tamper-evident.** The voting booth is a hash-linked
  ledger outside any secret store — each record carries the prior record's hash.
- **Verify with public keys only — no trust required.** Operational transparency:
  an *attested-but-unsigned* link (an identity whose key isn't enrolled yet) is
  reported, never hidden, and never silently passed as signed.
- **Sovereign & open.** Apache-2.0; no required dependency on any one wallet,
  vault, or chain. `eth_account`/`web3` are optional — without them, chains
  degrade to attest-only and still verify their linkage.

## Quickstart

```python
from ephermaleth import (AttestationChain, KeymapSigner, verify_chain,
                         VotingBooth, sha256_hex)
from eth_account import Account

keys = {
    "ceo":       Account.from_key("0x" + "11"*32),
    "author":    Account.from_key("0x" + "22"*32),
    "editor":    Account.from_key("0x" + "33"*32),
    "publisher": Account.from_key("0x" + "44"*32),
}
signer = KeymapSigner({k: a.key.hex() for k, a in keys.items()})
registry = {k: a.address for k, a in keys.items()}

# A speech from the throne, carried through a chain of command.
chain = AttestationChain.anchored("The board has spoken.", ts=1780000000,
                                  signer=signer, registry=registry)
chain.add_link("throne", "ceo", "issued", sha256_hex("The board has spoken."))
chain.add_link("author", "author", "composed", sha256_hex("…the article body…"))
chain.add_link("editor", "editor", "edited", sha256_hex("…the article body…"))
chain.add_link("publisher", "publisher", "published", sha256_hex("…the article body…"))

report = verify_chain(chain.to_dict(), registry)
assert report["valid"] and report["signed_links"] == 4

# Record the decision in the booth.
booth = VotingBooth("data/votingbooth.jsonl")
booth.record(council="boardroom", subject="On the matter of the voice",
             decision="passed", ts=1780000000, chain=chain.to_dict(),
             tally={"for": 6, "against": 1, "quorum": True})
assert booth.verify_ledger(registry)["valid"]
```

## Signers

| Signer | Use |
|--------|-----|
| `NullSigner()` | attest-only chains (no keys) |
| `KeymapSigner({id: pk})` | in-memory keys (tests, airgap) |
| `EnvKeystoreSigner(env, prefix="MINDX_WALLET_PK_")` | env-style keystore (`MINDX_WALLET_PK_CEO_AGENT_MAIN`) |
| `OracleSigner(fn)` | delegate to a vault / HSM / remote `/vault/sign` (production) |

## Status

`0.1.0` — extracted from mindX's "speech from the throne" provenance feature for
possible inclusion in **bankoneth**. Agnostic by construction; mindX is one
consumer.

Apache-2.0 · cypherpunk2048 — *take it, own it, use it, share it.*
