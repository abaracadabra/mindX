# Faice — the FACE of an AI service

Faice renders an mindX agent's identity — its **seven facets** — as a wireframe FACE, serves
it over an HTTP API, and gates it behind **x402 payment rails** where **reputation is privilege**.

```
.model · .agent · .prompt · .persona · .skill · .attribute · .reputation   ──►   a FACE
```

## The three peers

| Package | Concern | Entry |
|---------|---------|-------|
| [`facerig`](../facerig) | **renders** — canonical wireframe engine + `faceFromFacets()` | `facerig/src/lib/faicey` |
| **`faicey`** | **serves** — the FACE-as-a-service API + x402 gate | `faicey/src/faice` |
| [`voaice`](../voaice) | **speaks** — spectrometer, frequency, oscilloscope, TTS | `voaice/` |

Face and voice are independent: either runs without the other.

## Run it

```bash
cd ../facerig && npm install && npm run build:lib   # build the canonical engine bundle
cd ../faicey  && npm run serve                       # sync-engine runs automatically, then serves
curl http://localhost:8080/api/faice                 # self-describing service manifest
```

`FAICE_X402_TEST_MODE=1 npm run serve` accepts any `X-PAYMENT` envelope for local testing.

## The API

| Endpoint | Access | Returns |
|----------|--------|---------|
| `GET /api/faice` | free | service manifest (facets, rule, rails, agents) — the ingestion surface |
| `GET /api/faice/:agent/quote` | free | privilege verdict + price |
| `GET /api/faice/:agent` | privilege or x402 | FACE descriptor JSON |
| `GET /faice/:agent` | privilege or x402 | rendered wireframe FACE page |

Full reference, the facet→visual mapping, the 402 envelope and configuration live in
**[`src/faice/README.md`](./src/faice/README.md)** (service) and
**[`../facerig/src/lib/faicey/README.md`](../facerig/src/lib/faicey/README.md)** (engine).

## FACE as privilege

A gated FACE is served free when the agent's reputation **rank ≥ `expert`** (or it is BONA
FIDE) — privilege earned by standing. Otherwise it is a cost-bearing resource: settle on an
x402 rail (`base` / `tempo` / `algorand-mainnet`, inherited from mindX's
`data/config/x402_pricing.json`) and present `X-PAYMENT`, or raise the agent's reputation.

This is the reputation bypass mindX's x402 design reserves, realised here for the FACE.
