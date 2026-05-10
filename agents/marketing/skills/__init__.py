"""
agents.marketing.skills — per-soldier marketing capabilities.

Soldiers in `daio.governance.boardroom.Boardroom` are pure voters; this
package adds a layer ABOVE the boardroom that dispatches the marketing
capability for each soldier whose vote was `approve`. Soldier voting
semantics are preserved unchanged.

One skill module per role:
  ceo.py    — Brief composer + post-consensus signer
  cpo.py    — HBR L1 content drafting
  cto.py    — HBR L2 experimentation (A/B + holdouts)
  coo.py    — HBR L3 distribution (channel publishing)
  cfo.py    — HBR L4 reporting + treasury reads
  ciso.py   — Identity gate + voice violation scan (1.2× veto)
  clo.py    — Regulatory + competitor neutrality
  cro.py    — Spend risk + hard-stop (1.2× veto)

`registry.py` — single source of truth: soldier_id → skill instance.
"""

from __future__ import annotations
