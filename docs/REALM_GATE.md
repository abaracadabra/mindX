# The realm gate — the door, the preview, and the two answers

How mindX decides what a caller may read, and what it shows them when the answer is *not yet*.

The gate is a **funnel, not a fence**. Its purpose is to turn a reader into a recognized
participant — so it must say what signing *earns*, show a *hint* of what lies behind it, and never
hand over the thing itself.

---

## The two answers

`_tier_gate(request, min_tier, html_from, preview=None)` branches on **who is asking**:

| caller | signal | status | body |
|---|---|---|---|
| **a human** | `Accept: text/html` on a `GET` | **200** | the **door** — CONNECT, the offering, and a **preview** of the page behind it |
| **a machine** | anything else (API client, script, bot) | **403** | `{"detail": "realm tier '<tier>' required — connect at /activity"}` |

**Why the door is 200 and not 403.** `403` means *forbidden, and authenticating will not help* —
so crawlers refuse to index it and every link-preview unfurler (X, Discord, Slack, Google) renders
a dead card. mindX publishes dispatches on [RAGE](https://rage.pythai.net) that **cite these very
docs as proof**; under 403 the citations were invisible exactly where the funnel needed them
visible. A door is a page a human is meant to *read and act on*, not a refusal. So: **humans are
invited (200), machines are refused (403).**

## The preview — the hint of what access provides

> **A preview is not access. It is the hint of what access provides.**

When the gate guards a document, the door carries a **bounded** hint of it (`_doc_preview`):

- the **title**,
- the **shape** — word count, size, and the section headings,
- **one teaser paragraph** of the opening prose,
- and OpenGraph/Twitter tags carrying the same hint, so a shared citation unfurls the *promise*
  rather than an error.

That is all. Measured against `AGINT.md`, the teaser is **1.4% of the document**. It is enough to
judge whether the doc is worth a signature, and structurally incapable of substituting for one —
the gated body never crosses the line (no knobs, no findings, no numbers). Nothing about the
preview weakens the gate; it only makes the gate *legible*.

## The tiers

`public < participant < member < overseer < overlord` — resolved from the signature-derived JWT
(`Bearer` / `X-Overlord-Token` / `X-Overseer-Token` / `?t=`). Any **verified wallet is a
participant**: the signature *is* the recognition. The Algorand OVERSEER (`mindx.algo`) and the EVM
OVERLORD (`bankon.eth`) are both honored — the realm has two sovereign apexes.

| surface | minimum tier |
|---|---|
| `/`, `/health`, `/login`, `/recognized`, `/recognition/*`, `/diagnostics/live` | **public** |
| `/doc/*`, `/docs.html`, `/chat/docs` | **participant** — *this is the sign-up funnel, by design* |
| `/book`, `/members` | member |
| Gödel-machine internals (`SCHMIDHUBER_ENGINE`, `MINDX_MEMBER_ONLY_DOCS`) | member |
| `/admin/shadow/*`, the gated suites | overseer / overlord |

Exceptions: `_PUBLIC_DOCS = {THESIS, MANIFESTO}` are readable by anyone. The gate **fails open** on
an import fault — a broken gate must never hard-lock the docs.

## The funnel, end to end

```
   a public dispatch on RAGE            ("every assertion here is checkable")
        │  cites /doc/AGINT
        ▼
   THE DOOR  (200 · indexable · unfurls the hint)
        │  title · shape · teaser · what the signature earns
        │  CONNECT ─ the signature is free, moves no funds, proves the key is yours
        ▼
   RECOGNITION  (POST /recognition/recognize — the signature IS the recognition)
        │
        ├──▶ the documentation            (participant tier — the thing you came for)
        ├──▶ THE RECOGNITION FIELD        (/recognized — mindX's own substrate)
        └──▶ the offering                 (the configurable BONA FIDE airdrop)
```

See [RECOGNITION.md](RECOGNITION.md) for the ladder, the covenant, and the airdrop.

---

*The gate refuses machines and invites humans. It shows you the shape of what you cannot yet read,
and tells you exactly what one free signature would open. That is a funnel; a bare 403 is only a
wall.*
