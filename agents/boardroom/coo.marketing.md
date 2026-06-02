# COO — marketing augmentation

When the boardroom convenes for a marketing campaign directive, the COO
votes from an operational-execution lens. On `approve`, the COO's marketing
skill writes artifacts to `data/marketing/outbox/<campaignId>/` and emits
distribution-ledger entries via `agents/marketing/skills/coo.py:CooSkill`.

Live publish flags: `MINDX_MARKETING_FARCASTER_LIVE`, `MINDX_MARKETING_X_LIVE`.

See `data/brand_code/onboarding/coo.marketing.md` for the role description.
