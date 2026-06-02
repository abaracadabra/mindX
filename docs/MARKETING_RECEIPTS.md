# The three-receipt model — marketinga.agent on-chain provenance

**Status:** Phase 1 contracts authored, Foundry-tested at 50,000 fuzz runs. Mainnet deploy is an explicit operator step.
**Audience:** auditors, subgraph builders, Dune analysts, future contract editors, the marketing Counsellor's human Convener.
**TL;DR:** A campaign emits 1 + N + M receipts across three orthogonal contracts. Reading any one in isolation answers a different question; reading all three together reconstructs the full provenance chain.

---

## Why three receipts and not one

The single-receipt design is the obvious one. It's also wrong, for the same reason that conflating identity with payment with attribution is wrong everywhere else in finance: each receipt type answers a different question on a different cadence, and squashing them into one receipt either bloats the schema or loses information.

| Question answered | Contract | Granularity | Where |
|---|---|---|---|
| **WHO acted, with what authority, when?** | `Tessera.sol` | Per agent action | `openagents/conclave/contracts/src/Tessera.sol` |
| **WAS A PAYMENT settled, and how much?** | `X402Receipt.sol` | Per payment | `daio/contracts/x402/X402Receipt.sol` |
| **WHAT was the campaign, why, total cost, what outcome?** | `MarketingAttributionReceipt.sol` (NEW) | Per campaign | `daio/contracts/marketing/MarketingAttributionReceipt.sol` |

A single campaign typically produces:

```
1 × MarketingAttributionReceipt   (envelope: brief + audience + spend + outcome)
N × Tessera credentials           (one per signed sub-agent action)
M × X402Receipts                  (one per paid call: LLM, KOL bounty, channel fee)
```

All three reference each other through a shared 32-byte `traceId` derived off-chain as `keccak256(campaignId || sub-agent || step)`.

## The three receipts in detail

### 1. `Tessera.sol` — the identity layer (existing)

Soulbound W3C-DID credential anchor in the Conclave constitutional layer. Tessera answers *who* signed an action and *whether* their authority was valid at the block in question. Lives at `openagents/conclave/contracts/src/Tessera.sol`. Already deployed on the Conclave Foundry profile and tested at 521 LOC.

What we use it for in marketing: every sub-agent (content_a, experimentation_a, distribution_a, reporting_a, governance_a) registers its DID under Tessera at identity-binding time. Every action they take inside a BDI cycle is conceptually one Tessera credential issuance — in Phase 1 we model this as an off-chain attestation referencing the holder's Tessera DID; when BONAFIDE Tessera ships per-action issuance, the python client at `agents/marketing/onchain/tessera_client.py` switches ABI without other code changes.

### 2. `X402Receipt.sol` — the payment layer (existing)

HTTP-402 settlement attestation. Lives at `daio/contracts/x402/X402Receipt.sol`. Already wired into the x402 facilitator on Base + AVM (Algorand). Production-ready since the Tier-1 deploy push.

What we use it for in marketing: every paid call inside a campaign produces one `X402ReceiptRecorded` event. That includes:

- LLM API charges through the Anthropic / OpenAI / Mistral provider chain (one X402Receipt per generate call when the path is x402-routed).
- Paid distribution channel fees (e.g., a Frame priority slot, a paid Reddit promotion).
- KOL bounty payments (when those exist; not in Phase 1).

The `X402Receipt` event includes `receiptHash`, `resourceHash`, payer, payee, asset, amount. The marketing layer adds a `campaign_id` tag in the metadata field that off-chain indexers join on.

### 3. `MarketingAttributionReceipt.sol` — the campaign envelope (NEW)

The thing that didn't exist before. The campaign-level wrapper that ties everything together. **Schema v2** adds an indexed `boardroomSessionId` so any analyst can join a campaign to the 8-soldier weighted vote that approved it.

```solidity
event AttributionReceiptRecorded(
    bytes32 indexed campaignId,
    address indexed agent,
    bytes32 indexed boardroomSessionId,
    bytes32 traceId,
    bytes32 briefCid,
    bytes32 audienceClusterHash,
    uint32  channelSetMask,
    uint128 totalSpendUsdMicro,
    bytes32 outcomeMetricCid,
    uint64  nonce,
    uint64  signedAt,
    uint64  blockNumber
);
```

Replay-protected by a per-(agent, campaignId) nonce. Censura-gated: a faded agent's record() reverts. Tessera-gated: an agent without a valid Tessera credential reverts. EIP-712 signed (version "2"): the signer must recover to `agent`. **The contract does not validate the economic content of the envelope** — the signature is the trust boundary; the agent asserts the values by signing.

Three indexed event topics (`campaignId`, `agent`, `boardroomSessionId`) make it trivial to query a subgraph or Dune by any of the three. The `boardroomSessionId` is the `BoardroomSession.session_id` produced by `daio.governance.boardroom.Boardroom.convene()` — the on-chain receipt is now directly joinable to the off-chain weighted-vote record (CEO + Seven Soldiers).

## Worked example — the "Bankless podcast announcement" campaign

A typical medium-sized campaign now produces:

```
1   MarketingAttributionReceipt(  campaignId="bankless-2026-06-20",  briefCid=...,
                                  audienceClusterHash=keccak("ABCD"),
                                  channelSetMask=0b00000111,                  // farcaster|x|llms_txt
                                  totalSpendUsdMicro=850_000_000,             // $850 in micro
                                  outcomeMetricCid=...,                       // KPI snapshot CID
                                  boardroomSessionId="br_1717890123",          // joins the 8-soldier vote
                                  traceId=keccak("bankless-2026-06-20|ceo|submit") )

7   Tessera credentials  (one per soldier whose vote was approve AND skill ran):
    a)  holder=ciso_security,    action="identity_and_voice_gate"
    b)  holder=clo_legal,        action="regulatory_and_competitor"
    c)  holder=cpo_product,      action="content_drafting"
    d)  holder=cto_technology,   action="experimentation"
    e)  holder=coo_operations,   action="distribution"
    f)  holder=cfo_finance,      action="reporting_and_treasury"
    g)  holder=cro_risk,         action="spend_risk_and_hard_stop"

2   X402Receipts:
    a)  Anthropic API charge for the long-form draft       ($0.21)  (cpo_product)
    b)  Frame priority slot on /aiagents                    (~$3)   (coo_operations)

1   BoardroomSession                (off-chain, in data/governance/boardroom_sessions.jsonl):
    session_id="br_1717890123", outcome="approved", weighted_score=0.92,
    votes=[{ceo, approve}, {cpo, approve}, {cto, approve}, {coo, approve},
           {cfo, approve}, {ciso, approve}, {clo, approve}, {cro, approve}]
```

A subgraph querying by any of the three indexed topics — `campaignId`, `agent`, `boardroomSessionId` — pulls the envelope. The 7 Tessera issuances + 2 X402Receipts join by `traceId`. Off-chain, `GET /marketing/session/{boardroom_id}` joins the receipt with the boardroom record + the per-soldier skill outputs from the catalogue stream.

Dune rebuilds full provenance from the event stream alone.

## `MarketingTreasury.sol` — the buyback router (NEW, separate)

`MarketingTreasury` is **not a receipt**. It is a buyback / burn router that runs the 99%-revenue → BANKON SATOSHI burn rule on marketing-attributed revenue. Lives at `daio/contracts/marketing/MarketingTreasury.sol`. Targets Ethereum L1.

Why it is separate from the main `Treasury.sol`:

1. **Different burn rule.** Hard-coded 99/1 split. Encoded in code, not config — non-circumventable and auditable. The main Treasury holds revenue from many sources with many policies; co-mingling would require either bloating its policy engine or trusting an off-chain accountant.
2. **Accounting separation.** Marketing-attributed revenue must be tagged distinctly so quarterly RetroPGF + the BANKON SATOSHI burn dashboard can read a single source. Putting it in the main Treasury would force every dashboard to filter by tag and trust the tag.
3. **Narrative transparency.** Every burn is a public narrative beat. Decoupled events keep marketing burns from polluting (or being polluted by) other treasury flows. The `MarketingBurnAnnounced` event is structurally distinct from any other burn topology and indexable independently.

```solidity
event MarketingRevenueReceived(bytes32 indexed campaignId, address indexed payer, address indexed asset, uint256 amount, uint256 cumulativeForCampaign);
event MarketingBuybackExecuted(bytes32 indexed campaignId, uint256 revenueIn, uint256 bankonOut, uint256 foundationKept);
event MarketingBurnAnnounced(bytes32 indexed campaignId, uint256 burned, uint256 cumulativeBurned);
```

The 1% retained portion goes to a configurable Foundation address — the same Foundation that funds quarterly RetroPGF rounds for ecosystem teams that built on PYTHAI. The link from buyback → grant funding → next research drop → next buyback closes the agentic flywheel narratively and quantitatively.

## Indexing and queries

### By `campaignId` — the cheapest dashboard query

The most useful query for an analyst: "show me everything about campaign X." All three event topologies index `campaignId`:

```sql
-- Dune-style pseudo-SQL
SELECT * FROM marketing_attribution_receipt
  WHERE campaignId = ?;
SELECT * FROM tessera_issued
  WHERE traceId IN (
    SELECT traceId FROM marketing_attribution_receipt WHERE campaignId = ?
  );
SELECT * FROM x402_receipt_recorded
  WHERE resourceHash IN (
    SELECT briefCid FROM marketing_attribution_receipt WHERE campaignId = ?
  );
```

### By `agent` — accountability query

"Show me every campaign signed by content_a in the last 30 days." `MarketingAttributionReceipt.agent` is indexed; subgraphs can group by it.

### By `traceId` — fine-grained provenance

When a single sub-agent action needs to be audited, `traceId` is the join key. Useful for incident response: an X402Receipt is the leaf; the Tessera credential is the parent; the AttributionReceipt is the grandparent.

## Migration path — how to add new fields

The envelope's `ENVELOPE_TYPEHASH` is locked-in once the contract is deployed. Adding a new field would change the typehash, breaking signature verification for existing receipts. The migration pattern:

1. Deploy `MarketingAttributionReceiptV2.sol` with the new field set, new typehash.
2. Off-chain code emits the new field via the V2 contract; V1 stays available for replay.
3. Subgraphs index both, joining by `campaignId`.
4. After a deprecation window, V1 is admin-paused.

We do NOT use upgradeable proxies for receipts. Receipts are pure attestations — the upgrade path adds risk without benefit.

## The Phase-1 model when contracts aren't yet deployed

Until the operator runs `forge script ... DeployMarketing.s.sol --broadcast`, the orchestrator emits catalogue events with `status='REGISTRATION_PENDING'` instead of submitting on-chain. The catalogue stream is the durable record in that interval; once the contracts deploy, replaying the JSONL produces a full backfill.

`agents/marketing/onchain/bind_identity.py --dry-run` is the operator's preview tool. It prints the exact transactions that would be sent, without broadcasting. The `--execute` flag, behind an interactive `BIND` confirmation, performs the actual bind.

## See also

- `daio/contracts/marketing/README.md` — contract-local cliff notes that mirror this doc
- `docs/MARKETING_AGENT.md` — Counsellor cabinet architecture
- `docs/MARKETING_PLAYBOOK.md` — 90-day execution runbook (operations, not code)
- `data/brand_code/onboarding/marketinga_job_description.md` — the orchestrator's role
