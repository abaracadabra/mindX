# Speech from the Throne — a verifiable chain of command

> When the board speaks, anyone can prove who signed off and in what order. A
> board statement is carried to press through a cryptographic chain of custody —
> throne (CEO) → endorsing soldiers → AuthorAgent → editor.agent → artist.agent →
> wordpress.agent — each link signed by that seat's own wallet, tamper-evident,
> and verifiable with nothing but public keys. Added 2026-06-09. Code:
> [`agents/provenance_chain.py`](../agents/provenance_chain.py), the standalone
> [`openagents/ephermaleth/`](../openagents/ephermaleth/) module, and
> [`AuthorAgent.publish_speech_from_throne`](../agents/author_agent.py).

## The idea

A published artifact should prove its own lineage. The board issues a statement;
it does not simply appear on rage.pythai.net — it travels through the chain of
command, and each seat signs its link with its wallet (EIP-191). The result is a
chain anyone can re-verify by recovering each signer. No trust required, only
public keys — the same operational-transparency discipline the
[BANKON Vault](BANKON_VAULT.md) applies to custody.

## The chain of command

| seq | role | seat (`agent_id`) | act |
|-----|------|-------------------|-----|
| 0 | throne | `ceo_agent_main` | issued |
| 1…k | soldier | endorsing soldiers (e.g. `ciso_security`, `cro_risk`) | endorsed |
| k+1 | author | `author.agent` | composed |
| k+2 | editor | `editor.agent` | edited |
| k+3 | artist | `artist.agent` | illustrated |
| k+4 | wordpress | `wordpress.agent` | published |

Each link is hash-linked to the previous (its challenge includes the prior
link's hash), so the order is tamper-evident — a link can't be moved, dropped,
or grafted from another chain. The full chain rides in the published post (a
human-readable footer + an embedded JSON block) and in WordPress meta
(`_mindx_provenance_chain`).

## ephermaleth — the agnostic module

The primitives live standalone in [`openagents/ephermaleth/`](../openagents/ephermaleth/)
(Apache-2.0), so mindX is one consumer, not the only home. Built on the
[BANKON Vault](BANKON_VAULT.md) design principles:

- **`AttestationChain`** — the hash-linked, multi-signer chain.
- **Pluggable `Signer` oracle** — the chain never holds a private key; it asks a
  signer for a signature. mindX's signer is the BANKON vault
  (`vault_creds.sign_as(agent_id, message)` → `{agent_id}:pk`).
- **Injective, namespaced challenges** — every field is percent-encoded so a
  signature is bound to exactly one (chain, seq, role, agent, act, payload, prev)
  tuple. See [`openagents/ephermaleth/AUDIT.md`](../openagents/ephermaleth/AUDIT.md).
- **`verify_chain`** — recover every signer, check the linkage + registered
  identities (from [`daio/agents/agent_map.json`](../daio/agents/agent_map.json)).
- **`VotingBooth`** — see below.
- Verify from the shell: `python -m ephermaleth verify <chain.json|post.html>`.

An identity whose key isn't enrolled yet produces an *attested-but-unsigned*
link — reported honestly, never counted as signed. Today only `wordpress.agent`
has a vault key; the board's keys live in `data/identity/.wallet_keys.env`
(`MINDX_WALLET_PK_<AGENT>`) and light up real signatures once enrolled (an
`EnvKeystoreSigner` fallback is available in ephermaleth).

## The VotingBooth — a ledger of council decisions

Every board (and other-council) decision is recorded in an append-only, fsync'd,
hash-linked ledger at `data/governance/votingbooth.jsonl`. Each record is
content-addressed, chained to the previous record, and may embed its own
attestation chain. The same booth holds the boardroom's proclamations, a war
council's rulings, and a DAIO's resolutions side by side — each independently
verifiable. `VotingBooth.verify_ledger()` re-checks the whole sequence.

A throne speech records itself in the booth automatically
(`provenance_chain.record_throne_decision`).

## Endpoints

| Path | Method | Auth | Purpose |
|------|--------|------|---------|
| `/admin/throne/speak` | POST | admin | Issue a board speech with the signed chain of command + record it in the booth. Body: `{statement, title, dek, endorsers[], status, slug, illustrate}`. |
| `/verify/provenance` | POST | public | Re-verify a chain by recovering every signer. Body: `{chain}` JSON or `{html}` (chain auto-extracted). |

## How to verify (anyone)

1. From a published post: copy its HTML, `POST /verify/provenance {"html": "…"}`,
   or run `python -m ephermaleth verify post.html --registry agent_map.json`.
2. The report lists, per link: whether the challenge reconstructs, the linkage
   holds, the signature recovers to the stated address, and that address matches
   the registered identity. `valid: true` only when all signed links recover and
   the chain is intact.

## See also

- [AuthorAgent Composition](AUTHORAGENT_COMPOSITION.md) — how the body is written.
- [BANKON Vault](BANKON_VAULT.md) — the signing oracle + design principles.
- [Boardroom](NAV.md#boardroom) — the CEO + seven soldiers who sign.
- [`openagents/ephermaleth/README.md`](../openagents/ephermaleth/README.md) — the standalone module.
