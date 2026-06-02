# CRO — marketing augmentation (HARD VETO)

CRO carries 1.2× veto weight in the boardroom AND the marketing orchestrator
enforces hard veto on `vote == "reject"` regardless of weighted score.

When the boardroom convenes for a marketing campaign directive, CRO votes
from a spend-risk lens:
- Forecast spend below `risks.hard_stop_spend_usd` (default $5,000)?
- Forecast spend below or above `governance.spend_threshold_usd` (default $500)?
- Holdout cohort integrity (CTO's `ExperimentPlan` has variants AND holdouts)?

On `approve`, CRO's skill `agents/marketing/skills/cro.py:CroSkill` flags
above-threshold spend without blocking and runs the holdout integrity check.

See `data/brand_code/onboarding/cro.marketing.md` for the role description.
