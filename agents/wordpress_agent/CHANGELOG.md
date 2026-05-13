# Changelog

All notable changes to WordPress.agent are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-05-13

### Added
- `featured_image.py` module — `FeaturedImagePicker` rotates over the
  33 assets in `/home/hacker/mindX/gfx/` based on a curated
  topic-keyword map (competition, BANKON, OpenClaw, Hermes, swarmclaw,
  THOT, machine dreaming, self-healing, …). Falls back to `doorway1.webp`
  when nothing matches.
- `attach_featured_image()` async helper that POSTs to wordpress.agent's
  `/media` endpoint and returns the WordPress `media_id` for use as
  `featured_media` on the subsequent `/publish` call.
- SEO meta namespace support in `AuthorAgent.publish_to_rage` —
  `_seo_description`, `_seo_keywords`, `_og_{title,description,image_url}`,
  `_twitter_{card,creator}`, `_schema_article_json`. Renders via the
  plugin-less PHP snippet documented in §9 of `docs/HOSTINGER_SETUP.md`.
- Auto-featured-image: `publish_to_rage` now defaults to picking a
  /gfx/ asset and attaching it when the caller doesn't supply
  `featured_media`. Upload failure is logged and non-fatal.
- `PublicationOrchestrator` (`agents/publication_orchestrator.py`) —
  improvement-event-driven publishing, debounced + jittered, with a
  6-hour rate limit and a persistent ledger at
  `data/governance/published_triggers.json`. Watches SEA campaign
  history + full-moon dream cycles.
- 34 new tests (`tests/test_featured_image_picker.py`,
  `tests/test_publication_orchestrator.py`).

### Documentation
- `docs/HOSTINGER_SETUP.md` §9 — plugin-less SEO renderer (PHP `wp_head`
  hook + `register_post_meta` block).
- `docs/HOSTINGER_SETUP.md` §10 — featured-image rotation contract.

## [0.1.0] — 2026-05-09

### Added
- Initial release of WordPress.agent.
- `WordpressAgent` class with `publish`, `upload_media`, and `health_check`.
- FastAPI server exposing `/publish`, `/media`, and `/healthz` over loopback.
- Click-based CLI with `health`, `publish`, and `media upload` subcommands.
- Containerfile (Podman) and Compose definition for VPS deployment.
- Two systemd unit variants (direct venv and Podman wrapper).
- Idempotent `install.sh` and `uninstall.sh` scripts.
- pytest test suite covering agent, server, and config.
- AgenticPlace agent manifest at `agent.manifest.json`.
- Apache 2.0 licensed under the BANKON copyright header.
