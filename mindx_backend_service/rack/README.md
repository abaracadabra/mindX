# substrate rack — dreamknob instrument island

Read-only hardware readout on the landing page: two [dreamknob](https://dreamknob.dreamodus.software/)
racks (React island) rendering the mind's own numbers. Nothing on the panel accepts input —
every needle, LED and digit IS a value the machine produced.

- **SUBSTRATE INSTRUMENTS** ← `/insight/substrate/evolution` (`agents/substrate_evolver.py`,
  written each dream cycle): generation counter (seven-segment), mesh energy/nodes/link-reach
  gauges, bipolar imprint-Δ knob (`origin=0`), off-node GB meter bridge, status lamps,
  headline ticker (fourteen-segment marquee).
- **GODEL CHOICES** ← `/insight/godel/recent` (last 50 choices, metrics computed client-side):
  choice count, degraded-planning % (green→amber→red zones), mean eval score, latest
  selection-confidence stepped knob (LOW/MED/HIGH), choice-mix meter bridge, loop lamps,
  latest-model ticker.

Each rack renders only when its endpoint has real data; the section stays hidden otherwise
(the island must never break the landing page).

## Build

The build output `../static/substrate_rack.js` is a **committed artifact** served at
`/static/substrate_rack.js` — the VPS never needs node. Rebuild only when changing the rack:

```bash
cd mindx_backend_service/rack
npm install
npm run build          # esbuild → ../static/substrate_rack.js (~230 KB min)
```

## Vendored dependency

dreamknob is MIT (© Dreamodus Software Inc.), zero runtime dependencies, headless core + SVG.
It is not on the npm registry — upstream distributes release tarballs from its own forge
(`git.dreamodus.software/Dreamodus/DreamKnob`). We vendor the tarball and install from the
local file so the build is reproducible and immune to upstream changes:

```
vendor/dreamknob-1.1.4.tgz
sha256 37d5bdd61be838c5f2ceffe159fad410813442d5bdaa21a1a920fe690e296ada
```

Verify after any re-vendor: `sha256sum vendor/dreamknob-1.1.4.tgz` and re-audit the unpacked
package (no install scripts, no dependencies, dist-only) before building.
