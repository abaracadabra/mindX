# netdata license — CRITICAL FLAG

mindX uses Apache-2.0 as its sovereignty baseline and flags components with other licenses for explicit review (per `docs/publications/pdf/mindX Observability Stack_ Production-Grade Self-Hosted Blueprint.pdf` page 1). netdata is one such component, with a **mixed license split** that warrants documentation.

## The split

| Component | License | mindX usage status |
|---|---|---|
| **netdata Agent** (collection daemon, dbengine storage, alerts, exports, REST API) | **GPL-3+** | ✅ OK at network boundary |
| **netdata UI** (web dashboard frontend served at `:19999`) | **proprietary closed-source** | ✅ OK for self-hosted, free tier; no modification or redistribution |
| **netdata Cloud** (SaaS aggregator) | proprietary | ❌ NOT USED — `NETDATA_DISABLE_CLOUD=1` set in Quadlet |

## Why this is OK for mindX

1. **No derivative work.** mindX does not link netdata's code into its Python codebase. The netdata daemon runs as a separate process inside a container, reverse-proxied by Apache. This matches the "AGPL/GPL components used unmodified at network boundary" precedent the upstream blueprint sanctions for Grafana (AGPL-3) and Loki (AGPL-3) in Phase 1.

2. **No redistribution.** mindX runs the official upstream container image `docker.io/netdata/netdata:v2.5.0`. We don't ship netdata's binaries or source ourselves. The submodule at `vendor/netdata/` exists for auditability, not redistribution.

3. **Self-hosted free tier.** netdata's UI license explicitly permits self-hosted use; mindX is the user, not a reseller. No payment owed.

4. **No modification.** We do not modify netdata's source. The `vendor/netdata/patches/` directory exists for future use; it is empty today. The Phase 1.2 container build uses the upstream image as-is.

## What would block this

If any of the following becomes true in the future, the netdata path needs to be re-evaluated:

- netdata Agent relicensed away from GPL-3 (e.g. SSPL, BUSL).
- netdata UI license changes to forbid self-hosted use without a contract.
- mindX wants to redistribute netdata as part of its own package (e.g. `mindx_observability/` becomes a downloadable bundle including netdata binaries).
- mindX wants to modify netdata's source and ship the modifications.

## Mitigation paths if blocked

In rank order:

1. **glances** (LGPL-3.0, fully OSS) — Python TUI + REST API at `:61208`. Same role (always-on lightweight monitoring), heavier RAM (~100 MB vs netdata's 200 MB), no real-time per-second charts as polished. github.com/nicolargo/glances.

2. **Custom UI over netdata Agent's REST API** — the Agent stays GPL-3 regardless of UI license shifts. mindX could ship its own dashboard (HTML+JS) hitting `http://localhost:19999/api/v1/data?chart=...` and bypassing the proprietary UI entirely. The Agent's REST surface is documented at `learn.netdata.cloud/docs/agent/web/api/queries`.

3. **OpenObserve** (Apache-2.0) — heavier (single binary + ClickHouse), but full sovereignty. Designed as a Grafana+Loki+Tempo replacement. Considerably bigger lift than option 1 or 2.

4. **Roll back to Phase 1.1** — Prometheus + Grafana stay; netdata removed. Loss = real-time charts; gain = no proprietary UI dependency. Phase 1.1's Grafana is AGPL-3 (which we already accepted at the same network-boundary precedent), so this is a strictly-OSS fallback.

## Tracking

- Pinned version: see `vendor/netdata/` (submodule HEAD) and `podman_quadlets/netdata.container` (image tag).
- When bumping the pin (see `vendor/README.md`), re-verify upstream license files haven't changed by checking `vendor/netdata/LICENSE` and the `web/gui/` directory's licensing header.
- Any change to the license picture triggers a review against this document.

## Compliance trail

The blueprint PDF's Phase 1.2 (in `/home/hacker/.claude/plans/breezy-strolling-anchor.md`) explicitly captures this license review. Future operators reading the Quadlet should understand: **this is a deliberate, scoped exception to mindX's Apache-2.0 sovereignty rule, with a documented mitigation path.**
