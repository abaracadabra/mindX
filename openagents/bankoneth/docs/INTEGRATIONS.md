# bankoneth — Integrations

How to consume bankoneth from each canonical consumer.

## PARSEC (first-class)

`@bankoneth/parsec-adapter` ships a `BankonethComponent` that conforms to
PARSEC's wallet-component contract. Register it once at PARSEC startup:

```ts
import { BankonethComponent } from "@bankoneth/parsec-adapter";

parsec.registerComponent(new BankonethComponent());
```

PARSEC then surfaces "bankon.eth" as a tab. Inside it, the user sees all
three flows (A subname / B `.eth` purchase / C hosted-`.eth` issuance) with
the standard tri-rail payment picker.

The `nfdminter` sibling (for `.algo` names) is registered the same way.

## mindX

Drop-in `BankonethTool` exposed via `openagents.bankoneth.integrations.mindx`.
Wraps the `@bankoneth/cli` command in a mindX `BaseTool` so AGI agents can
claim their own bankon.eth subname programmatically.

```python
from openagents.bankoneth.integrations.mindx import BankonethTool

tool = BankonethTool()
tool_registry.register(tool)

# Inside an agent:
result = await tool.execute(
    action="claim",
    label="agent-001",
    duration_years=1,
    payment="eth",
    inft_mode_a=True,
)
```

See [`../integrations/mindx/README.md`](../integrations/mindx/README.md) for
the install + env-var setup.

## DAIO

DAIO consumes bankoneth contracts via a git submodule:

```bash
# In the DAIO repo:
git submodule add https://github.com/bankon-eth/bankoneth openagents/bankoneth
```

Then DAIO's `foundry.toml` declares the remappings:

```toml
[profile.bankon-import]
src  = "src/bankon-import"
libs = ["lib", "openagents/bankoneth/lib"]
remappings = [
  "@bankoneth/=openagents/bankoneth/contracts/",
]
```

DAIO's existing `daio/contracts/ens/v1/` directory is **stale** —
[`DAIO_HANDOFF.md`](DAIO_HANDOFF.md) documents the cleanup. Once that PR
lands, `daio/contracts/ens/v1/` becomes a single pointer line:
`see openagents/bankoneth`.

## AgenticPlace

agenticplace.pythai.net consumes bankoneth via two channels:

1. **On-chain event watch** on `BankonAgenticPlaceHook.AgenticPlaceListing`.
   The AgenticPlace indexer subscribes via WebSocket on Ethereum mainnet and
   creates a marketplace card for every emit.
2. **Off-chain webhook** at `setWebhookURL(...)` — agenticplace.pythai.net
   exposes `/api/listings` (POST JSON `{parentNode, label, tokenId, tba, metadataURI}`)
   for immediate listing without waiting for the next block.

Use the on-chain channel as the source of truth; the webhook is a latency
optimization.

## Third-party `.eth` holders (Flow C)

Any `.eth` holder can enroll their domain as a bankoneth-hosted parent and
start issuing subnames. They keep a configurable share of the revenue:

```bash
# 1. Wrap your .eth into ENS NameWrapper if not already.
# 2. Burn CANNOT_UNWRAP for the parent-lock requirement.
# 3. setApprovalForAll(BankonDomainHosting, true) on the NameWrapper.
# 4. Call BankonDomainHosting.enroll(parentNode, price6, fuses, expiry, ownerShareBps)
```

Then customers buy subnames under your `.eth` via the same UI as Flow A;
the contract automatically routes your share to your wallet via the
`BankonPaymentRouter`'s `parentOwnerPayout` bucket.

## Standalone Web

Any HTML page can drop in the Web Components:

```html
<script type="module" src="https://unpkg.com/@bankoneth/ui"></script>

<bankoneth-flow-tabs></bankoneth-flow-tabs>
<bankoneth-claim></bankoneth-claim>
<script type="module">
  import { BankonethClient } from "https://unpkg.com/@bankoneth/core";
  // ... construct client, set on the components ...
</script>
```
