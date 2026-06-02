# CFO — marketing augmentation

When the boardroom convenes for a marketing campaign directive, the CFO
votes from a spend-vs-outcome lens. On `approve`, the CFO's marketing
skill runs the GEO probe + computes the KPI snapshot + reads
`MarketingTreasury` state via `agents/marketing/skills/cfo.py:CfoSkill`.

The CFO needs the COO's `DistributionLedger` from `prior_outputs`; absence
yields a zero-distribution KPI snapshot rather than refusing.

See `data/brand_code/onboarding/cfo.marketing.md` for the role description.
