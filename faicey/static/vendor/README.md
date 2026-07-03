# static/vendor — locally served engine + three.js (no CDN)

These files are **generated artifacts** copied from the canonical FaceRig engine by
`faicey/scripts/sync-engine.mjs` (runs on `npm run sync-engine`, and automatically on
`prestart`/`preserve`). They are committed so faicey runs standalone, with no CDN and no
runtime dependency on `node_modules`.

| File | Source | Purpose |
|------|--------|---------|
| `faicey-engine.js` | `facerig/dist-lib/faicey-engine.js` | canonical wireframe engine (three.js inlined) — the FACE renderer + `faceFromFacets` |
| `three.module.js` | `facerig/vendor/three/build/` | three.js 0.182 ESM (browser import map target) |
| `three.core.js` | `facerig/vendor/three/build/` | three.module.js re-exports from this sibling — required |
| `jsm/controls/OrbitControls.js` | `facerig/vendor/three/examples/jsm/` | vendored addon |

## Do not hand-edit

Regenerate instead:

```bash
cd ../facerig && npm run build:lib     # rebuild the engine bundle
cd ../faicey  && npm run sync-engine   # re-copy artifacts here
```

Served at `/static/vendor/*` and consumed via an import map in the FACE pages
(`src/faice/service.js`, `server.js`). Single source of truth for three.js is
`facerig/vendor/three` — see its `VENDOR.md`.
