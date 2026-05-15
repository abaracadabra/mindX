# vendor/

Vendored upstream source pinned via git submodules. Phase 1.2 introduces one entry:

- `netdata/` — `github.com/netdata/netdata`, pinned to a tagged release.

## Why submodules and not literal source copy

Phase 1.2 chose "fork + integrate source" for netdata. Literal source copy of ~600 K LOC of C into this repo's git history is unmanageable. The submodule pattern instead gives us:

1. **Version pin** — `git submodule status` reports the exact upstream SHA + tag.
2. **License trail** — upstream LICENSE files live where they came from; no risk of stripping them.
3. **Patch staging** — `vendor/netdata/patches/` (created when first needed) holds any local diffs we apply at build time. Empty until we move from official container to from-source build.
4. **Build escape hatch** — if Phase 1.3 needs custom builds, the source is already pinned at the right SHA.
5. **Diff-able upstream** — `git submodule update` bumps the pin; the regression surface is one SHA bump, not a 600 K LOC sweep.

## How the runtime relates

The Phase 1.2 deployment runs the **official container image** `docker.io/netdata/netdata:v2.5.0` (see `mindx_observability/podman_quadlets/netdata.container`). The container is pinned to **the same version** as the submodule. We don't compile from the submodule today — it's there for:

- Auditing what code is running ("what does the official v2.5.0 actually contain?")
- License/copyright source of truth
- Ability to switch to from-source build without restructuring

## Bumping the pin (procedure)

```bash
cd mindx_observability/vendor/netdata
git fetch --tags
git checkout vX.Y.Z                # the new tag
cd ../..

# Update the container tag in the Quadlet to match
sed -i 's|netdata:vX\.OLD\.Z|netdata:vX.Y.Z|' mindx_observability/podman_quadlets/netdata.container

# Re-lint
bash mindx_observability/scripts/lint.sh

# Commit submodule pin + Quadlet bump together
git add mindx_observability/vendor/netdata mindx_observability/podman_quadlets/netdata.container
git commit -m "obs: bump netdata pin to vX.Y.Z"
```

## License (CRITICAL — see docs/netdata_license.md)

- **netdata Agent** (collection, storage, alerts, exports): **GPL-3+**. OK at network boundary (container).
- **netdata UI**: **proprietary closed-source**. Self-hosted free tier permitted; cannot modify or redistribute.

If the UI license ever becomes blocking, mitigation = swap to `glances` (LGPL-3) or build a custom UI on netdata Agent's REST API (`/api/v1/data?chart=...` stays GPL-3).
