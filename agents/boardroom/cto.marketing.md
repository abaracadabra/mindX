# CTO — marketing augmentation

When the boardroom convenes for a marketing campaign directive, the CTO
votes from a technical-readiness lens. On `approve`, the CTO's marketing
skill produces the `ExperimentPlan` via
`agents/marketing/skills/cto.py:CtoSkill`.

The CTO needs the CPO's `ContentDraft` from `prior_outputs` — if absent,
the skill returns `missing_upstream`.

See `data/brand_code/onboarding/cto.marketing.md` for the role description.
