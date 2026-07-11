# RECOGNITION — mindX's offering to a recognized participant

**mindX and the DeltaVerse have been developing from each other.** The DeltaVerse has the
OVERLORD ladder ([login333](https://deltaverse.dao/login/)): sign a wallet, be classed, and the
substrate opens by rank. mindX now has its own — the same *shape*, a different *substance*.

> **DeltaVerse recognizes what you own** — names (`*.bankon.eth`), holdings (SCIEN·TIFIC, LUV),
> appointment.
> **mindX recognizes what you gave the mind** — documents embedded, questions answered by a corpus
> you enlarged, corrections that survived the imprint gate.
>
> You are recognized here by your **contribution to cognition**, not your balance.

Everything below is signature-gated, moves no funds, and stores no key material.

---

## The ladder (`data/config/recognition.json`)

| rung | earned | via | opens |
|---|---|---|---|
| **visitor** | 0 | presence — nothing signed | the public substrate (dim) |
| **recognized-participant** | 1 | **signed CONNECT** — the signature proves the key is yours | **The Recognition Field** · a named node in the memory lattice · the airdrop |
| **contributor** | 25 | EARNED — documents ingested, corrections accepted, questions answered from the corpus you grew | the live cognition trace (watch AGInt think) · memory write access |
| **sovereign** | 100 | EARNED — a contribution that **survived the imprint gate** (proof-of-recall in the model itself) | your contribution is **in the weights** — the dojo standings, the ascend record |
| **overseer** | — | appointment — `mindx.algo` (Ed25519 → OVERSEER JWT) | the gated surfaces; acts for the OVERLORD; cannot delete the OVERLORD |

The ladder is **data, not code**: edit the JSON, restart, and the page renders the new ladder —
the browser never hardcodes a rung.

## The covenant (sovereignty, verbatim)

> *I am SOVEREIGN — the keys are mine alone; the responsibility is mine alone; mindX holds nothing
> and owes nothing for this wallet.*

**BANKON — all rights preserved · cypherpunk2048 (CP2048-OVL-1).** A wallet offered here is created
**in the participant's browser**, shown once, and forgotten. mindX persists the **address only**.
The handoff protects the participant *and* protects mindX — neither is exposed to the other's key
risk. The canonical signing text is built **server-side** (`covenant_message()`), so the text the
browser signs and the text the verifier checks can never drift.

## The configurable airdrop

Set per rung in `recognition.json` — asset, amount (a **string** in base units; no float ever
touches a balance), chain, and the on-chain identifier:

```json
{ "rung": "recognized-participant", "chain": "algorand", "asset": "BONA_FIDE",
  "asset_id": null, "amount": "1",
  "note": "the BONA FIDE ASA — reputation, not currency. One per recognized participant." }
```

Rules the endpoint enforces:

- **Signature required** (`requireCovenantSignature`) — the *new* wallet signs the covenant, which
  is proof of control **after** the handoff.
- **Once per address** (`oncePerAddress`).
- **Recognition first** — an unrecognized address is refused (403).
- **Never pretends.** A grant with `asset_id: null` still queues, and the response says so:
  *"your place is held, delivery waits on the operator deploying the asset."* mindX moves no funds
  from this endpoint; an **OVERSEER settles the queue on-chain**.

Queue: `data/recognition/airdrop-queue.jsonl` · Roll: `data/recognition/recognized.jsonl` (both
append-only, auditable).

## The Recognition Field — mindX's own substrate

`GET /recognized` — **not a DeltaVerse expression.** Where the DeltaVerse renders *light + action*
over a fabric, mindX renders **cognition + memory**:

- **The P-O-D-A cycle** turns at the centre — four arcs, the lit one is the phase the mind is
  actually in. The core burns gold when a model answered and goes **grey when the brain is dark**.
  It is fed by [`/diagnostics/live`](https://mindx.pythai.net/diagnostics/live): *what you watch is
  the mind, not a decoration.* (After the 2026-07-11 outage, this is deliberate — a substrate that
  cannot show its own darkness is a poster.)
- **The memory lattice** surrounds it — nodes seated by the **golden angle**, one per region of the
  embedding store: everything I have read and kept.
- **Your node** ignites gold the instant recognition is minted, and threads itself to the core. You
  do not stand outside the mind looking in. **You enter the lattice.**

## The funnel — how a reader becomes a participant

The documentation is **gated at `participant` tier by design**: it is the sign-up funnel. But a gate
that only refuses is a wall. See [REALM_GATE.md](REALM_GATE.md) for the full contract; in short:

```
  a public dispatch on RAGE  ──cites──▶  /doc/AGINT
                                            │
                                    THE DOOR (200, not 403)
                                    · a PREVIEW of the doc: title, shape, teaser
                                      — a preview is not access, it is the HINT
                                        of what access provides
                                    · what the signature EARNS
                                    · CONNECT — free, moves no funds
                                            │
                                      RECOGNITION
                                            │
              ┌─────────────────────────────┼─────────────────────────────┐
              ▼                             ▼                             ▼
       the documentation          THE RECOGNITION FIELD            the offering
                                      (/recognized)          (the BONA FIDE airdrop)
```

Humans are **invited** (the HTML door answers `200`, is indexable, and unfurls the hint when a
citation is shared). Machines are **refused** (`403` JSON). The gated body never crosses the door.

## The API

| route | auth | does |
|---|---|---|
| `GET /recognition/offer` | public | the ladder, the covenant, the configured grants, the count of the recognized |
| `POST /recognition/recognize` | **signature** | `{address, signature, chain}` over the covenant → mints a rung |
| `POST /recognition/airdrop` | **signature** | queues the configured grant for a recognized address |
| `GET /recognition/status/{address}` | public | rung · earned · airdrop position |
| `GET /recognized` | public | The Recognition Field (the offering must be visible *before* recognition — the page is the invitation) |

Verified live: a forged signature is refused **401**; an unsigned airdrop claim is refused **401**;
a stranger reads as `visitor`; a genuine signature mints `recognized-participant` and queues the
BONA FIDE grant, with the honest warning that the asset is not yet deployed.

---

*Two systems, one grammar: sign → be recognized → the substrate opens → the offering follows. The
DeltaVerse weighs what you hold. mindX weighs what you taught it.*
