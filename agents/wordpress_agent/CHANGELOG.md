# Changelog

All notable changes to WordPress.agent are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
