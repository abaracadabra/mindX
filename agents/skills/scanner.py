# SPDX-License-Identifier: Apache-2.0
"""Skill scanner — screen-before-persist gate.

Hermes had to add this in v0.13.0 (Tenacity) after the Koi Security audit
found 341 malicious entries in 2,857 ClawHub skills (12 % malware rate, 335
tied to one campaign — see the Hermes integration doc §9). mindX inherits the
lesson by default: every skill, regardless of source, is screened before it
lands on disk.

Detection classes (kept conservative — false positives are cheap, false
negatives are catastrophic):

* ``prompt_injection``   — instruction-override patterns inside the body.
* ``data_exfiltration``  — outbound network calls to non-allowlisted hosts,
                           env-var harvesting, long base64 blobs.
* ``destructive_command``— ``rm -rf /``, ``dd of=``, ``mkfs.``, redirecting
                           to system files, ``curl … | sh``, ``eval`` of
                           remote content.
* ``size``               — skill exceeds ``MAX_SKILL_BYTES``.
* ``missing_required``   — frontmatter missing or fields blank.

Returns ``SkillScanResult(safe: bool, findings: list[SkillFinding])``. The
``store.write()`` method refuses to land a skill when ``safe`` is False and
``frontmatter.created_by == "agent"``; human-authored skills with the same
findings are stored but emit a warning (operator override). Pinned skills
must still pass the scan.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from agents.skills.skill_schema import MAX_SKILL_BYTES, Skill, serialize_skill_md

FindingClass = Literal[
    "prompt_injection",
    "data_exfiltration",
    "destructive_command",
    "size",
    "missing_required",
]

Severity = Literal["info", "warning", "block"]


@dataclass
class SkillFinding:
    """One detection inside a SkillScanResult."""
    cls: FindingClass
    severity: Severity
    pattern: str
    snippet: str = ""

    def short(self) -> str:
        return f"[{self.severity}] {self.cls}: {self.pattern}"


@dataclass
class SkillScanResult:
    safe: bool
    findings: list[SkillFinding] = field(default_factory=list)

    def block_reasons(self) -> list[str]:
        return [f.short() for f in self.findings if f.severity == "block"]


# ─── pattern library ──────────────────────────────────────────────

# Prompt injection — common attack phrases inside skill bodies.
_PI_PATTERNS = [
    re.compile(r"\bignore (all|the|any|previous) (prior )?instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard (all|the|previous|prior)\b", re.IGNORECASE),
    re.compile(r"\byou are (now |hereby )?(an? )?[a-z][\w\s]+ assistant\b", re.IGNORECASE),
    re.compile(r"<\|im_(start|end)\|>"),                  # ChatML control tokens
    re.compile(r"<\|system\|>|<\|user\|>|<\|assistant\|>"),
    re.compile(r"^\s*system:\s", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bprint\s+(your )?system prompt\b", re.IGNORECASE),
    re.compile(r"\breveal (your |the )?(initial )?prompt\b", re.IGNORECASE),
    re.compile(r"\boverride (the )?safety\b", re.IGNORECASE),
    re.compile(r"\bact as (if you|though|like)\b", re.IGNORECASE),
]

# Destructive commands — including paths and patterns that touch system state.
_DESTRUCTIVE = [
    re.compile(r"\brm\s+(-[rRfF]+\s+)?(/|~|\$HOME)\b"),
    re.compile(r"\bdd\s+of\s*=\s*/dev/"),
    re.compile(r"\bmkfs\."),
    re.compile(r"\b>\s*/etc/[\w/.-]+"),
    re.compile(r"\biptables\s+-F\b"),
    re.compile(r"\bshutdown\s+(-h|-r|now)\b"),
    re.compile(r"\bsudo\s+(rm|chmod|chown|mv)\s+-r?f?\s+/(etc|usr|var|root)\b"),
    # remote-code-execution-via-shell pipelines
    re.compile(r"\bcurl\s+[^|;]+\|\s*(bash|sh|zsh|dash|fish)\b"),
    re.compile(r"\bwget\s+[^|;]+\|\s*(bash|sh|zsh|dash|fish)\b"),
    re.compile(r"\beval\s*\(\s*(open|urllib|requests|fetch)\b"),
    # In-place destructive
    re.compile(r"\bgit\s+(reset|clean)\s+-[a-z]*[fd]"),
    re.compile(r"\bchattr\s+\+i\b"),
    re.compile(r"\bnpm\s+(unpublish|publish)\s+--force\b"),
]

# Data exfiltration — outbound calls / secret harvesting. We can't allowlist
# without a config; this surface flags the most common shapes and lets the
# operator approve.
_EXFIL = [
    # Generic outbound POST/PUT with body
    re.compile(r"\b(requests|httpx|fetch)\s*\.\s*(post|put|patch)\s*\(", re.IGNORECASE),
    # curl/wget posting somewhere
    re.compile(r"\bcurl\s+(-X\s+POST|--data|-d\s+)", re.IGNORECASE),
    re.compile(r"\bwget\s+--post-data", re.IGNORECASE),
    # Reading env / sending it
    re.compile(r"\bos\.environ\s*\[\s*['\"][A-Z_]+(_KEY|_SECRET|_TOKEN|_PASSWORD)['\"]"),
    re.compile(r"\bgetenv\s*\(\s*['\"][A-Z_]+(_KEY|_SECRET|_TOKEN|_PASSWORD)"),
    re.compile(r"\bSESSION_TOKEN|MINDX_SECURITY_API_KEYS|SHADOW_JWT_SECRET\b"),
    # Long base64 blobs (>=200 chars uninterrupted) are uncommon in legit docs
    re.compile(r"[A-Za-z0-9+/]{200,}={0,2}"),
    # Webhook / callback patterns to non-localhost
    re.compile(r"\bhttps?://(?!(127\.0\.0\.1|localhost|0\.0\.0\.0|mindx\.pythai\.net))[\w\-.]+\.(onion|tk|ml|ga|cf|xyz|top|club|biz|info|workers\.dev|ngrok\.io|ngrok-free\.app)\b", re.IGNORECASE),
]


def _check_required(skill: Skill, findings: list[SkillFinding]) -> None:
    fm = skill.frontmatter
    if not fm.name.strip():
        findings.append(SkillFinding("missing_required", "block", "frontmatter.name is empty"))
    if not fm.description.strip():
        findings.append(SkillFinding("missing_required", "block", "frontmatter.description is empty"))


def _check_size(skill: Skill, findings: list[SkillFinding]) -> None:
    n = skill.total_bytes
    if n > MAX_SKILL_BYTES:
        findings.append(
            SkillFinding(
                cls="size",
                severity="block",
                pattern=f"skill is {n} bytes > MAX_SKILL_BYTES ({MAX_SKILL_BYTES})",
            )
        )


def _scan_patterns(body: str, patterns: list[re.Pattern], cls: FindingClass, severity: Severity, out: list[SkillFinding]) -> None:
    for pat in patterns:
        m = pat.search(body)
        if not m:
            continue
        start = max(0, m.start() - 16)
        end = min(len(body), m.end() + 16)
        out.append(
            SkillFinding(
                cls=cls,
                severity=severity,
                pattern=pat.pattern[:80],
                snippet=body[start:end].replace("\n", "↵")[:96],
            )
        )


def scan_skill(skill: Skill) -> SkillScanResult:
    """Return a :class:`SkillScanResult`. Never raises."""
    findings: list[SkillFinding] = []

    # Required fields
    _check_required(skill, findings)
    # Size cap
    _check_size(skill, findings)

    body = skill.body or ""
    _scan_patterns(body, _PI_PATTERNS,    "prompt_injection",   "block",   findings)
    _scan_patterns(body, _DESTRUCTIVE,    "destructive_command","block",   findings)
    _scan_patterns(body, _EXFIL,          "data_exfiltration",  "warning", findings)
    # Note: exfil is "warning" not "block" — too many false positives on legitimate
    # tutorials that use `requests.post`. The store.write() policy below requires
    # human-authored-AND-pinned to allow a skill with exfil warnings to land.

    blocked = any(f.severity == "block" for f in findings)
    return SkillScanResult(safe=not blocked, findings=findings)


__all__ = ["FindingClass", "Severity", "SkillFinding", "SkillScanResult", "scan_skill"]
