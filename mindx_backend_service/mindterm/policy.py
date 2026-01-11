from __future__ import annotations

import re
from .models import RiskDecision

HIGH_RISK_PATTERNS = [
    (re.compile(r"\brm\s+-rf\b"), "Destructive delete (rm -rf)."),
    (re.compile(r"\bmkfs(\.| )"), "Filesystem format (mkfs)."),
    (re.compile(r"\bdd\s+if="), "Raw disk write/read (dd)."),
    (re.compile(r"\bshutdown\b|\breboot\b"), "System power control."),
    (re.compile(r"\bchmod\s+\+s\b"), "Setuid bit escalation."),
    (re.compile(r"\bchown\s+root\b"), "Privilege ownership change."),
    (re.compile(r"\bcurl\b.*\|\s*(sh|bash)\b"), "Pipe remote script to shell."),
    (re.compile(r"\bwget\b.*\|\s*(sh|bash)\b"), "Pipe remote script to shell."),
    (re.compile(r"\b:\(\)\s*\{\s*:\s*\|\s*:\s*;\s*\}\s*;\s*:\b"), "Fork bomb."),
]

MED_RISK_PATTERNS = [
    (re.compile(r"\bsudo\b"), "Privilege escalation (sudo)."),
    (re.compile(r"\bapt(-get)?\s+(install|remove|purge)\b"), "System package modification."),
    (re.compile(r"\bsystemctl\b"), "Service management."),
    (re.compile(r"\biptables\b|\bufw\b"), "Firewall modification."),
]

def assess_command(command_line: str) -> RiskDecision:
    cmd = (command_line or "").strip()
    if not cmd:
        return RiskDecision(level="low", reason="Empty input.", requires_confirm=False)

    for pat, why in HIGH_RISK_PATTERNS:
        if pat.search(cmd):
            return RiskDecision(level="high", reason=why, requires_confirm=True)

    for pat, why in MED_RISK_PATTERNS:
        if pat.search(cmd):
            return RiskDecision(level="medium", reason=why, requires_confirm=True)

    return RiskDecision(level="low", reason="No risky patterns detected.", requires_confirm=False)

