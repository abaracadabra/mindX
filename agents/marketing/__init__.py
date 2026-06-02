"""
agents.marketing — autonomous marketing Counsellor cabinet for the
PYTHAI / DELTAVERSE / BANKON umbrella.

One orchestrator (MarketingaAgent) plus five sub-agents (content,
experimentation, distribution, reporting, governance) corresponding to
the four HBR layers (Taite/Winsor/Fernandez 2026) plus a constitutional
governance layer.

Receipts:
  Tessera                       (Conclave)         — WHO/WHEN  (per action)
  X402Receipt                   (existing x402)    — WAS-PAID  (per payment)
  MarketingAttributionReceipt   (NEW, this pkg)    — WHAT/WHY  (per campaign)
  MarketingTreasury             (NEW, this pkg)    — buyback/burn router

See docs/MARKETING_RECEIPTS.md for the three-receipt model.
See data/brand_code/onboarding/*.md for per-agent role descriptions.
"""

from __future__ import annotations
