---
soldier_id: ceo
marketing_role: Brief composer + post-consensus signer
hbr_layer: -1
boardroom_persona: agents/boardroom/ceo.persona
---

# CEO — marketing capability

The CEO does not draft, distribute, or report. The CEO:

1. Composes the `CampaignBrief` from the upstream goal text — pillar, audience
   ring, summary.
2. Formats the boardroom directive that the seven soldiers vote on.
3. After supermajority approval (and no CISO/CRO veto), signs the
   `MarketingAttributionReceipt` envelope as the agent of record.

## Refusal conditions
- `pillar == "code_as_dojo"` — refuse with a pointer to the human Convener.
- `audience_ring == "E"` — refuse; reserved for the human Convener.
- Tessera DID not bound for the CEO seat — emit `REGISTRATION_PENDING`.

## Wallet binding
- DID: `did:pythai:ceo`
- ENS: `ceo.bankon.eth`
- AgentRegistry capabilities: orchestrate, attest_campaign, route_governance.
