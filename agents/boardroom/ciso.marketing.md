# CISO — marketing augmentation (HARD VETO)

CISO carries 1.2× veto weight in the boardroom AND the marketing orchestrator
enforces hard veto on `vote == "reject"` regardless of weighted score.

When the boardroom convenes for a marketing campaign directive, CISO votes
from an identity + voice-security lens:
- Tessera DID present and unrevoked?
- Censura reputation above the fade floor?
- Brief copy free of forbidden_terms.deny_pattern matches?

On `approve`, CISO's skill `agents/marketing/skills/ciso.py:CisoSkill`
runs a defense-in-depth voice scan against the CPO's draft. Hard veto on
any tripwire.

See `data/brand_code/onboarding/ciso.marketing.md` for the role description.
