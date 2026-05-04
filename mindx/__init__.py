"""mindx — namespace package for mindX core capabilities.

Per the user-locked Agnostic Modules Principle (memory, 2026-04-28), submodules
under this namespace ship as agnostic peers — mindX's autonomous loop is the
first consumer, not the exclusive home. Other systems (audit, dashboards,
external operators) are expected to import these without entanglement.

Current submodules:
- mindx.self.aware       — read-only signal aggregation (no decision logic)
- mindx.self.improve     — self-improvement primitives
- mindx.self.improve.model_selector — self-aware model choice for self-improvement

Plan: /home/hacker/.claude/plans/nested-juggling-melody.md
"""
