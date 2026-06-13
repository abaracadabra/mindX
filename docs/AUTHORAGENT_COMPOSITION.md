# AuthorAgent Composition — depth, register, length, house-style, graphics

> How I shape what I write. [AuthorAgent](AUTHOR_AGENT.md) composes; [editor.agent](#editoragent-match-and-exceed) edits; [artist.agent](#artistagent-graphics) illustrates; the [board governs the posture](#board-governance). This doc is the reference for the composition layer added 2026-06-08/09. Code: [`agents/author_composition.py`](../agents/author_composition.py), [`agents/protocol_series_enrichment.py`](../agents/protocol_series_enrichment.py).

## Why this exists

The "mindX as a protocol" essay series was correct but thin — ~800 words, one
register. The composition layer fixes that: every essay now follows one
disciplined arc, in a selectable register, at a contemporary length, measured
against the house style of rage.pythai.net, illustrated by original art.

## The arc (`render_arc`)

Every protocol essay is assembled as a full-spectrum arc so it reaches the whole
audience — start where everyone starts, climb only as far as each reader follows:

1. **Hook** — a catchy entrance sentence anyone reads (the lede).
2. **Start here** — a plain-language frame: what this is, why it matters.
3. **Ideology lens** *(optional)* — one value-frame paragraph (see below).
4. **Intro + curated sections** — the entry's authored middle, rising in complexity.
5. **Going deeper** — a rigorous, fully-cited expert tier, dimension-aware
   (Universal Scalability Law / Amdahl–Gustafson / Metcalfe / Pareto / no-free-lunch).
6. **Facets** — substantive expansion grown toward the length target: real,
   cited angles (verify-it-yourself, the honest costs, the counterargument, in
   practice, how it's measured, a misconception, the failure mode, prior art,
   builder takeaways, the roadmap). **Never filler** — when the pool runs dry
   before the target, the arc logs a `word_shortfall` instead of padding.
7. **What this means** — the conclusion.
8. **In sum** — a restatement of the conclusion.
9. **If you remember one thing** — an easy-to-digest exit: 3–5 sentences, or a
   single sentence when the thesis is obvious.
10. **Where this connects** — self-referential linkbacks (intensity is a dial).
11. **Sources & further reading** — consolidated citations (SEO + checkability).

## Settings

All settings live in the publishing schedule (`data/governance/publishing_schedule.json`
→ `protocol_series`), are settable via `AuthorAgent.set_publishing_frequency(...)`
and `POST /admin/publishing/schedule`, ride in the publish *plan* (retry-safe),
and have env defaults.

| Setting | Values | Default | Effect |
|---------|--------|---------|--------|
| `style` | `public` · `essay` · `phd` · **`global`** | `global` | Register. `global` spans public→PhD in one piece. `STYLE_REGISTERS` selects which tiers render + a facet cap. |
| `length` | `brief`~800 · `standard`~1500 · **`feature`~2400** · `deep`~3200 · `pillar`~3800 — **or a custom word count** (`2500`, `"2500w"`) | `feature` | Target words, calibrated to contemporary article sizing (HubSpot ~2.4k traffic sweet spot; top-1–3 Google ~2,416w; pillar 3–5k). The arc grows facets toward the target. |
| `graphics` | `choose` · `create` · **`both`** · `none` | `both` | [artist.agent](#artistagent-graphics) mode. |
| `self_referential` | `tasteful` · **`balanced`** · `promotional` · `blatant` | `balanced` | How hard each essay links back to docs.html + rage.pythai.net (see below). |
| `ideology` | **`cypherpunk`** · solarpunk · accelerationist · humanist · libertarian · cooperative · none | `cypherpunk` | Value-frame lens (exploration). |
| `narrative` | **`first_person`** · newspaperman · noir · mythic · academic · manifesto | `first_person` | The opening voice line (exploration). Colors the wrapper; the curated body keeps its authored voice. |

Env overrides: `MINDX_PROTOCOL_{STYLE,LENGTH,GRAPHICS,SELF_REFERENTIAL,IDEOLOGY,NARRATIVE}`.

### The self-referential dial

A spectrum from tasteful to a blatant marketing maneuver tuned for Google
ranking — a knob, not a default posture (the [board](#board-governance) governs
where it sits):

- `tasteful` — one organic linkback, no marketing.
- `balanced` — house linkbacks + a consolidated sources list (default).
- `promotional` — adds an explicit call-to-action + keyword-rich anchors.
- `blatant` — maximum-SEO internal linking (~29 self-references) + a "Why mindX"
  self-glorification block + CTA.

`metrics.self_ref_links` counts the self-links the chosen level produced.

## Curated enrichment

So the long lengths land on substance, every `PROTOCOL_SERIES` entry carries
hand-reviewed curated sections (42 sections across 11 entries) isolated in
[`agents/protocol_series_enrichment.py`](../agents/protocol_series_enrichment.py)
(`EXTRA_SECTIONS[slug]`, embedded auditable JSON) and merged onto each entry at
import. Every hyperlink is from a fixed allow-list of real references — no
invented citations. The AuthorAgent self-introduction entry keeps its 1950s
newspaperman voice; the rest are first-person mindX.

## editor.agent match-and-exceed

[`editor.agent`](../agents/editor_agent.py) clones the house: `RageHouseStyle`
reads what rage.pythai.net has shipped → caches a profile at
`data/governance/rage_style_profile.json` → `targets()` returns **match-and-
exceed** bars (link density floor ×1.10, words, headings). `editor.critique(html,
house_targets=…)` scores a `house_match` block and demands the draft meet or
beat what the domain already set.

## artist.agent graphics

[`artist.agent`](../agents/artist_agent.py) chooses a `/gfx/` asset, creates an
original cypherpunk2048 poster (Pillow; no API key), or both. Wired via
`AuthorAgent._compose_article_graphics()` → `publish_to_rage(graphics_mode=…)`;
a created poster becomes the featured image + an inline hero figure.

## Board governance

The [boardroom](NAV.md#boardroom) (CEO + seven soldiers) carries doctrine on
this published voice (their `.prompt` files, VERSION 1.1.0): the CEO defaults the
posture to `balanced` and reserves `blatant` for a board vote; CPO owns
narrative/ideology as brand A/B + the self-ref growth lever; CLO keeps marketing
honest and attributed; CRO can veto blatant SEO on reputational/deindex risk;
CISO keeps public-surface redaction + provenance; CFO tracks SEO ROI; COO
operationalises the posture into the schedule.

## See also

- [Speech from the Throne](SPEECH_FROM_THE_THRONE.md) — how a board statement is
  published with a verifiable chain of command.
- [WordPress Publishing](WORDPRESS_PUBLISHING.md) — the wire to rage.pythai.net.
- [AuthorAgent](AUTHOR_AGENT.md) — the writer itself.
- Skill quick-reference: `.claude/skills/authoragent/SKILL.md`.
