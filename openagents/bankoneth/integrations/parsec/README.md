# bankoneth — PARSEC integration notes

The PARSEC wallet ships with bankoneth as a first-class component (not an
"integration") — the actual code lives at
[`packages/parsec-adapter/`](../../packages/parsec-adapter/), exported as
`@bankoneth/parsec-adapter`. This README is the operational handshake.

## Topology

```
+-------------------+        +--------------------------+
|  PARSEC shell     |        |  @bankoneth/parsec-adapter |
|  (Tauri 2 + Lit)  |◀──────▶|  exports BankonethComponent |
+-------------------+        +--------------------------+
        ▲                                ▲
        │                                │
        │ ParsecComponentEvent           │ uses
        │                                │
        │                                ▼
        │                     +-----------------------+
        │                     |  @bankoneth/core      |
        │                     |  + @bankoneth/ui      |
        │                     +-----------------------+
```

PARSEC owns:

- The wallet shell (connect / sign / send-tx UI)
- Network / chain selection
- Transaction history
- A component slot that opens bankoneth's UI

bankoneth owns:

- The three issuance flows (A/B/C)
- The price quote + payment-rail picker
- The iNFT toggle + AgenticPlace toggle
- All contract reads + writes

## NFDminter sibling

A second component, `nfdminter`, ships alongside bankoneth in PARSEC. It
creates `.algo` names on Algorand via the NFD V3 registry (app id `760937186`).
Together: `bankoneth` (Ethereum side) + `nfdminter` (Algorand side) gives
PARSEC the cross-chain identity surface the PARSEC architecture document
calls out. The NFDminter is a separate effort; this file references it for
context only.

## License

Apache-2.0
