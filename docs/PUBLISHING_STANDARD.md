# Publishing Standard — AuthorAgent × editor.agent × artist.agent

The operational standard for everything mindX publishes to rage.pythai.net. It
codifies the workflow proven on the manifesto-assessment and Darwin–Gödel essays:
**compose → review → publish**, with clickable sources and original graphics.

## The pipeline (canonical)

```
AuthorAgent.compose_commissioned(brief)   # mindX first-person voice, house linkbacks
        ↓
AuthorAgent.publish_to_rage(...)           # the standard runs inside here:
   1. linkify_sources()  — every bare URL becomes a clickable <a href>
   2. editor.agent.critique() — gated (hard/soft/off), verdict logged to the catalogue
   3. artist.agent graphics (graphics_mode="both") — original cypherpunk2048 poster
   4. signed identity footer + SEO meta → wordpress.agent → WordPress REST
```

The one-call canonical path for a deliberate article:

```python
author = await AuthorAgent.get_instance()
await author.publish_commissioned(brief, status="publish", gate="hard", graphics_mode="both",
                                  seo_keywords=[...])
```

`publish_commissioned` = `compose_commissioned` → `publish_to_rage(editor_gate="hard")`.

## The standard, point by point

1. **editor.agent reviews EVERY publish.** `publish_to_rage` calls
   `editor.agent.critique` on every article. The gate is set by `editor_gate`
   (or env `MINDX_PUBLISH_EDITOR_GATE`):
   - `hard` — a `REVISE` verdict refuses to publish (`publish_to_rage` returns `None`). Use for deliberate features.
   - `soft` — review, log the verdict, publish anyway. **Default**, so the autonomous cadence is never starved.
   - `off` — skip the review.
   The verdict is logged, attached to post meta (`_mindx_editor_verdict`,
   `_mindx_editor_scores`), and emitted as a `publication.reviewed` catalogue event.

2. **Cite every source as a clickable link.** `publish_to_rage` runs
   `AuthorAgent.linkify_sources()` on the body: any bare URL becomes
   `<a href="URL">URL</a>` (idempotent; URLs already inside an href are left
   alone). No raw URLs in the rendered prose.

3. **editor.agent's bars (all 0.90; transparent and deterministic).** clarity,
   genius, style ≥ 0.90; operational-transparency 5/5; reference density ≥ 6
   links / 1000 words; and — when house targets are supplied — MATCH AND EXCEED
   what rage.pythai.net already ships. Citation density now rewards **hyperlinks
   (href)**, not raw visible "http", so clickable citations satisfy genius
   directly.

4. **Link mindX concepts back to docs.html.** When an essay names a mindX
   concept (BDI, AGInt, SEA, RAGE, machine dreaming, DAIO, BONA FIDE,
   inference-first, x402, mindXtrain), link it to
   `https://mindx.pythai.net/docs.html`. AuthorAgent maintains that surface
   itself (`update_docs_index`, `generate_readme`), so the citation is to a
   living, auditable source.

5. **Cross-link the house archive for facts.** Support claims with the real
   published rage.pythai.net articles. AuthorAgent holds the full catalogue via
   `wordpress.agent.list_all_posts` / `build_catalogue` / `fetch_llms_txt`;
   cross-link the canonical (non-duplicate) URLs.

6. **Original graphics on every feature.** `graphics_mode="both"` →
   artist.agent renders an original corporate cypherpunk2048 poster (hexagon
   logomark, masthead, brand bar) as hero + featured image. No API key required.

## In-place updates

To revise an already-published post WITHOUT churning its poster:

```python
await author.publish_to_rage(title=..., content_html=..., status="publish",
                             post_id=POST_ID, graphics_mode="none",
                             auto_featured_image=False)
```

## Operational transparency

The editor's rubric is public (this doc + `agents/editor_agent.py`). Every
article carries a signed identity footer; every review is on the catalogue. The
code is open source under Apache-2.0; the only black box is the vault, and you
are free to build your own.
