# CONCLAVE

> *cum + clavis* — "with the key." A peer-to-peer agent conclave for
> trade-secret-grade executive coordination.

## Agnostic-module statement

CONCLAVE is **an agnostic, composable protocol module**. It is *not* a
mindX-only artifact. The protocol assumes only:

- **ed25519 keypairs** per member (any agent stack mints these),
- a **mesh transport** (Gensyn AXL is the reference; any `/send` + `/recv` +
  `/mcp/` + `/a2a/` shim works),
- an **EVM chain** for resolution anchoring + bond escrow + slashing,
- *(optional)* a **BONAFIDE-style** identity + reputation surface for
  membership gating.

Any framework — mindX, OpenClaw, NanoClaw, ZeroClaw, NullClaw, or your
agent stack — composes CONCLAVE the same way: instantiate the `Conclave`
runtime with your keypair + AXL client + role, plug your own
`on_speak` / `on_motion` callbacks (the protocol is callback-driven, see
[`conclave/protocol.py`](conclave/protocol.py)), and you have a private
deliberation channel.

mindX is one canonical consumer. The mindX integration adapter lives at
[`integrations/mindx_boardroom_adapter.py`](integrations/mindx_boardroom_adapter.py)
and is illustrative — CONCLAVE itself does not import mindX.

**Horizontal scaling:** mesh-native — more nodes simply join. The
`/topology` endpoint reports the current peer set; the Camera View
dashboard polls it. **Vertical scaling:** per-node MCP capability privacy
lets richer agents host arbitrarily-sophisticated services (bigger local
models, larger context, richer policy engines) without leaking inputs to
the rest of the conclave.

---

CONCLAVE is a protocol on top of [Gensyn AXL](https://github.com/gensyn-ai/axl)
that lets a small, bounded group of cryptographically-identified agents
convene in private, deliberate, and resolve — with no central server, no
cloud account, and no third-party message broker ever holding the payload.

The canonical instance is the **Cabinet pattern**: one Convener (CEO) plus
seven Counsellors (the seven soldiers — COO, CFO, CTO, CISO, GC, COS, OPS),
deliberating *in camera* over an end-to-end-encrypted Yggdrasil mesh.

This repo ships:

- The **CONCLAVE protocol** (Python) — a session state machine over AXL
  `/send`, `/recv`, `/mcp/`, and `/a2a/`.
- `Conclave.sol` — a Foundry-tested gating + anchoring + slashing contract
  on top of the existing **BONAFIDE** stack (Tessera, Senatus, Censura,
  SponsioPactum).
- `ConclaveBond.sol` — an honor-stake module that settles trade-secret
  bonds via x402 / Algorand through the Parsec rail.
- An eight-node local example (`examples/run_local_8node.sh`) that
  spins up a full Cabinet on one workstation for development.

## Why CONCLAVE

Slack, Telegram, Discord, and every "agent platform" route trade-secret
payloads through somebody else's server. That is fine for chat and useless
for executive sessions, M&A war rooms, incident response, threat-intel
sharing between rivals, family-office governance, or any deliberation that
must be unrecoverable from any third-party log.

CONCLAVE gives those settings a primitive: **a closed-chamber session
where the cryptography enforces the chamber.** Membership is gated by
on-chain credentials (Tessera) and reputation (Censura). Speech is signed
and addressed to the mesh, not to a server. The only artifact that ever
leaves the conclave is a resolution hash anchored on chain, plus whatever
redacted summary the members choose to publish.

## Architecture

```
                 ┌─────────────────────────────────────────┐
                 │                CONCLAVE                 │
                 │  protocol: convene / acclaim / speak /  │
                 │           motion / vote / resolve       │
                 └────────────────┬────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
   ┌─────────┐              ┌──────────┐             ┌────────────┐
   │  mindX  │              │   AXL    │             │  BONAFIDE  │
   │ Soul /  │  ◄──MCP/A2A─▶│ p2p mesh │◄──gating───▶│  Tessera   │
   │ Mind /  │              │ Yggdrasil│             │  Censura   │
   │ Hands   │              │ E2E enc. │             │  Senatus   │
   └─────────┘              └──────────┘             └────────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ ConclaveBond│
                           │ x402 / ALGO │
                           │ honor stake │
                           └─────────────┘
```

See [`CONCLAVE.md`](./CONCLAVE.md) for the full protocol spec and
[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for layer detail.

## Quickstart (single-host, eight nodes)

```bash
# Build AXL
git clone https://github.com/gensyn-ai/axl.git
cd axl && make build && cd ..

# Install CONCLAVE
pip install -e .

# Spin up an 8-node Cabinet on this machine
./examples/run_local_8node.sh

# In another terminal, run the CEO agent
python examples/ceo_node.py --session "Q3 M&A review"
```

## Multi-host

Each member runs the AXL node binary and a CONCLAVE process. The Convener
publishes a `ConveneManifest` containing the eight Ed25519 pubkeys; AXL
peer discovery on Yggdrasil handles the rest. No DNS, no bootstrap server
beyond the standard AXL public peers.

## Foundry

```bash
cd contracts
forge install
forge test -vvv
```

`Conclave.sol` requires the BONAFIDE deployments (`Tessera`, `Censura`,
`Senatus`) at the addresses set in `script/Deploy.s.sol`. Deploy with:

```bash
forge script script/Deploy.s.sol --rpc-url $RPC --broadcast
```

## Layout

```
conclave/                    Python package
├── protocol.py              session state machine
├── axl_client.py            HTTP wrapper for the AXL bridge
├── messages.py              typed signed envelopes
├── crypto.py                Ed25519 sign/verify, session keys
├── session.py               in-memory session state
├── roles.py                 Cabinet role enum + quorum policy
├── agent.py                 mindX Soul/Mind/Hands integration
└── chain.py                 Conclave.sol + Tessera bindings

contracts/
├── src/Conclave.sol         gating, anchoring, slashing
├── src/ConclaveBond.sol     x402 / Algorand honor stake
├── src/interfaces/          ITessera, ISenatus, IConclave
└── test/Conclave.t.sol      Foundry tests

examples/
├── ceo_node.py
├── soldier_node.py
└── run_local_8node.sh

docs/
├── ARCHITECTURE.md
├── THREAT_MODEL.md
└── EVALUATION.md
```

## License

MIT. Built for the Gensyn track of ETHGlobal OpenAgents 2026.
