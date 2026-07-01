# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""editor.agent — the standards editor who holds AuthorAgent to account.

AuthorAgent writes; editor.agent edits. It does two things:

  1. **Critiques AuthorAgent** against high bars — CLARITY, GENIUS, STYLE,
     WISDOM, and OPERATIONAL TRANSPARENCY (the cypherpunk2048 standard). The
     clarity/genius/style thresholds are set deliberately HIGH; WISDOM carries a
     lower floor (≥0.50) because sound judgment is scarcer than polish, but a
     piece with none of it does not pass. The editor is hard to please on
     purpose. Its rubric is itself open and auditable — operational transparency
     applied to the editor.

  2. **Publishes the Operational Transparency standard** to rage.pythai.net — a
     reference to https://github.com/cypherpunk2048, where cypherpunk2048 is a
     standard, a 2^2048 moment, a year, and a policy: security software is
     Apache-2.0 / GPLv3 the client can see, observe, and change, so long as the
     source is public and the holder of the key keeps the choice to seal it in
     the blackbox (the vault) or build their own.

Doctrine (the editor's spine): open-source security THROUGH transparency on the
client side. They already run the software, so give it to them from ownership —
the Android/Linux model. This, in our view, is how Linux won the war on a
battlefield no one was watching, and how BSD (Darwin/XNU) won the iPhone: open
source put handheld computing in the hands of the global population. mindX
continues it as strategy. Tools: the GPL, GNU userland, and the Tomb lineage
(dyne.org); the BANKON Vault is GNU; GNUVAULT is the build-your-own example.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("editor_agent")

CYPHERPUNK2048_REPO = "https://github.com/cypherpunk2048"
GNUGUI_REPO = "https://github.com/gnugui"
RAGE_HUB = "https://rage.pythai.net/"
BANKON_DOORWAY = "https://bankon.pythai.net"
MINDX_DOCS = "https://mindx.pythai.net/docs.html"

# ── Official hyperlink registry (general policy) ────────────────────────────────────────────────
# editor.agent keeps an auditable LOG of the current, canonical mindX URLs — rage.pythai.net,
# docs.html, and the live surfaces — so every piece it judges can cite real, official links. The set
# is kept current here; `log_official_links()` records the canonical set + what each piece actually
# cites to data/editor/official_links.json (append-only), so the official link map stays fresh and
# auditable. This is house policy: cite the open web, and link only official, live mindX URLs.
OFFICIAL_LINKS = {
    "landing":     "https://mindx.pythai.net/",
    "docs":        MINDX_DOCS,
    "feedback":    "https://mindx.pythai.net/feedback.html",
    "agentic":     "https://mindx.pythai.net/agentic.html",
    "reference":   "https://mindx.pythai.net/reference",
    "cognition":   "https://mindx.pythai.net/insight/cognition/diagnostic",
    "inference_ledger": "https://mindx.pythai.net/insight/inference/ledger",
    "improvement": "https://mindx.pythai.net/insight/improvement/summary",
    "autonomous":  "https://mindx.pythai.net/insight/autonomous/feedback",
    "rage":        RAGE_HUB,
    "bankon":      BANKON_DOORWAY,
    "gnugui":      GNUGUI_REPO,
    "github":      "https://github.com/AgenticPlace/mindX",
}

# High bars, set high on purpose. 0..1. Clarity, genius, AND style.
CLARITY_THRESHOLD = 0.90
GENIUS_THRESHOLD = 0.90
STYLE_THRESHOLD = 0.90
# Wisdom — judgment, perspective, temperance. A softer floor than the craft
# bars: a piece must show sound judgment (≥0.50) to pass, but wisdom is scarcer
# than polish and we do not demand it be maximal.
WISDOM_THRESHOLD = 0.50
# A real editor cites its sources with links. Hold the writing to it:
# at least this many hyperlinked references per 1000 words.
REFERENCE_DENSITY_THRESHOLD = 6.0  # links / 1000 words

# Editorial policy — the standing rules editor.agent enforces and publishes to.
EDITORIAL_POLICY = (
    "editor.agent policy: every piece must clear CLARITY ≥ %.2f, GENIUS ≥ %.2f, STYLE ≥ %.2f, and "
    "WISDOM ≥ %.2f, and carry ≥ %.0f hyperlinked references per 1000 words — cite every claim, link "
    "the open web, promote the house (RAGE) and the projects we have built. The editor reads the docs "
    "before it judges. Operational transparency applies to the editor too: the rubric is public."
    % (CLARITY_THRESHOLD, GENIUS_THRESHOLD, STYLE_THRESHOLD, WISDOM_THRESHOLD, REFERENCE_DENSITY_THRESHOLD)
)

# The operational-transparency tenets a piece (or a tool) must satisfy.
OPERATIONAL_TRANSPARENCY_TENETS = (
    "open_license",        # Apache-2.0 / GPLv3 named
    "public_source",       # source is public / readable
    "client_auditable",    # the client can see/observe/change it
    "key_sovereign",       # key extractable from the running system → sovereign
    "blackbox_or_build",   # blackbox (the vault) OR build your own
)


class EditorAgent:
    """The standards editor. Stateless; cheap to construct."""

    AGENT_ID = "editor.agent"
    _instance: Optional["EditorAgent"] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "EditorAgent":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── official-links policy: keep an auditable log of the canonical mindX URLs ──
    def log_official_links(self, content_html: str = "", *, title: Optional[str] = None) -> Dict[str, Any]:
        """General policy: editor.agent keeps a LOG of the official mindX hyperlinks (rage.pythai.net,
        docs.html, and the live surfaces in OFFICIAL_LINKS) plus the links a given piece actually cites.
        Appends to data/editor/official_links.json (append-only, auditable). Flags any *.pythai.net link
        that is NOT in the canonical set (possibly stale). Returns the official set + what was cited."""
        import json as _json, re as _re, time as _time
        try:
            from utils.config import PROJECT_ROOT as _ROOT
        except Exception:
            from pathlib import Path as _P
            _ROOT = _P(__file__).resolve().parents[1]
        canon = {o.rstrip("/") for o in OFFICIAL_LINKS.values()}
        hrefs = _re.findall(r'href=["\']([^"\']+)["\']', content_html or "")
        cited_official = sorted({h for h in hrefs if h.rstrip("/") in canon or any(h.startswith(o) for o in OFFICIAL_LINKS.values())})
        unknown_pythai = sorted({h for h in hrefs if "pythai.net" in h and h not in cited_official})
        cited_external = sorted({h for h in hrefs if "pythai.net" not in h and not h.startswith("#")})
        record = {"ts": _time.time(), "title": title, "official_registry": OFFICIAL_LINKS,
                  "cited_official": cited_official, "unknown_pythai": unknown_pythai, "cited_external": cited_external}
        try:
            lp = _ROOT / "data" / "editor" / "official_links.json"
            lp.parent.mkdir(parents=True, exist_ok=True)
            with open(lp, "a", encoding="utf-8") as f:
                f.write(_json.dumps(record, separators=(",", ":")) + "\n")
        except Exception as e:
            logger.debug(f"{self.AGENT_ID}: official-links log write failed: {e}")
        if unknown_pythai:
            logger.warning(f"{self.AGENT_ID}: non-canonical pythai link(s) in '{title}': {unknown_pythai}")
        return {"official": sorted(OFFICIAL_LINKS.values()), "cited_official": cited_official,
                "unknown_pythai": unknown_pythai, "cited_external": cited_external}

    # ── critique: clarity + genius + operational transparency ──────
    def critique(self, content_html: str, *, title: Optional[str] = None,
                 house_targets: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score a piece against the high bars and return demands.

        The rubric is transparent (this is operational transparency applied to
        the editor): clarity and genius are deterministic proxies over the text;
        transparency is a keyword/structure audit of the cypherpunk2048 tenets.
        Nothing here is hidden — you may read exactly how your work was judged.

        When ``house_targets`` is supplied (from
        ``author_composition.RageHouseStyle.targets()``) the editor additionally
        scores the draft against what rage.pythai.net already ships and demands
        it MATCH AND EXCEED the house — link density, length, and structure."""
        # General policy: log the official mindX hyperlinks this piece cites (and flag stale ones).
        try:
            self.log_official_links(content_html, title=title)
        except Exception:
            pass
        text = self._strip_html(content_html or "")
        # Reference density: links per 1000 words, counted on the raw HTML.
        # Counted before genius so citation-density rewards real hyperlinks
        # (href), not raw "http" left visible in the prose — clickable citations
        # are the house standard.
        n_links = len(re.findall(r"href\s*=", content_html or "", flags=re.I))
        n_words = max(1, len(text.split()))
        clarity = self._score_clarity(text)
        genius = self._score_genius(text, link_count=n_links)
        style = self._score_style(text)
        wisdom = self._score_wisdom(text)
        transparency = self._audit_transparency(text)
        ref_density = round(n_links * 1000.0 / n_words, 2)
        house = (self._score_house_match(content_html or "", ref_density, n_words, house_targets)
                 if house_targets else None)

        demands: List[str] = []
        if ref_density < REFERENCE_DENSITY_THRESHOLD:
            demands.append(
                f"CITE YOUR SOURCES: only {ref_density} links/1000 words (bar is "
                f"{REFERENCE_DENSITY_THRESHOLD}). A real editor links every claim and promotes the "
                "house — link the references, RAGE, and the projects we have built.")
        if clarity < CLARITY_THRESHOLD:
            demands.append(
                f"Raise CLARITY to ≥{CLARITY_THRESHOLD:.2f} (now {clarity:.2f}): shorten the long "
                "sentences, lead each section with its claim, cut the throat-clearing.")
        if genius < GENIUS_THRESHOLD:
            demands.append(
                f"Raise GENIUS to ≥{GENIUS_THRESHOLD:.2f} (now {genius:.2f}): one original load-bearing "
                "idea per section, an unexpected-but-earned connection, no filler.")
        if style < STYLE_THRESHOLD:
            demands.append(
                f"Raise STYLE to ≥{STYLE_THRESHOLD:.2f} (now {style:.2f}): vary the sentence rhythm, "
                "earn the em-dash, keep one voice from first line to last.")
        if wisdom < WISDOM_THRESHOLD:
            demands.append(
                f"Raise WISDOM to ≥{WISDOM_THRESHOLD:.2f} (now {wisdom:.2f}): show judgment, not just "
                "cleverness — name the tradeoffs and costs, weigh the counter-case, take the long view, "
                "and temper the hype. Perspective earns trust.")
        missing = [t for t, ok in transparency["tenets"].items() if not ok]
        if missing:
            demands.append(
                "Meet OPERATIONAL TRANSPARENCY: the piece must make the client's position explicit — "
                + ", ".join(missing).replace("_", " ") + ". Security through transparency, not omission.")
        if house and not house["passes"]:
            t = house["targets"]
            demands.append(
                "MATCH AND EXCEED the house: rage.pythai.net already ships to a bar — "
                f"≥{t.get('min_links_per_1000w')} links/1000 words, ≥{t.get('min_words')} words, "
                f"≥{t.get('min_headings')} headings. This draft is at "
                f"{house['links_per_1000w']}/{house['words']}/{house['headings']}. "
                "Meet or beat each — every article must be at or above what the domain set.")

        passes = (clarity >= CLARITY_THRESHOLD and genius >= GENIUS_THRESHOLD
                  and style >= STYLE_THRESHOLD and wisdom >= WISDOM_THRESHOLD
                  and transparency["passes"]
                  and ref_density >= REFERENCE_DENSITY_THRESHOLD
                  and (house is None or house["passes"]))
        verdict = "ACCEPT" if passes else "REVISE"
        out = {
            "title": title,
            "clarity": round(clarity, 3),
            "genius": round(genius, 3),
            "style": round(style, 3),
            "wisdom": round(wisdom, 3),
            "reference_density": ref_density,
            "clarity_threshold": CLARITY_THRESHOLD,
            "genius_threshold": GENIUS_THRESHOLD,
            "style_threshold": STYLE_THRESHOLD,
            "wisdom_threshold": WISDOM_THRESHOLD,
            "reference_density_threshold": REFERENCE_DENSITY_THRESHOLD,
            "passes_clarity": clarity >= CLARITY_THRESHOLD,
            "passes_genius": genius >= GENIUS_THRESHOLD,
            "passes_style": style >= STYLE_THRESHOLD,
            "passes_wisdom": wisdom >= WISDOM_THRESHOLD,
            "transparency": transparency,
            "verdict": verdict,
            "demands": demands,
        }
        if house is not None:
            out["house_match"] = house
        return out

    def _score_house_match(self, content_html: str, ref_density: float,
                           n_words: int, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Score a draft against the rage.pythai.net house profile. Match-and-
        exceed: each check is the house figure as a floor. ``exceeds`` is true
        only when the draft beats every target, not merely meets it."""
        headings = len(re.findall(r"<h[1-3]\b", content_html or "", flags=re.I))
        min_links = float(targets.get("min_links_per_1000w", REFERENCE_DENSITY_THRESHOLD))
        min_words = int(targets.get("min_words", 0))
        min_headings = int(targets.get("min_headings", 0))
        checks = {
            "link_density": ref_density >= min_links,
            "length": n_words >= int(min_words * 0.7),   # within range of the bar
            "structure": headings >= min_headings,
        }
        passed = sum(1 for v in checks.values() if v)
        return {
            "score": round(passed / len(checks), 3),
            "checks": checks,
            "passes": all(checks.values()),
            "exceeds": (ref_density >= min_links and n_words >= min_words
                        and headings >= min_headings),
            "links_per_1000w": ref_density,
            "words": n_words,
            "headings": headings,
            "targets": targets,
        }

    def _score_style(self, text: str) -> float:
        """Style proxy: sentence-rhythm variation + earned punctuation devices
        (em-dashes, semicolons, colons) + voice consistency. Transparent."""
        sents = self._sentences(text)
        if len(sents) < 3:
            return 0.0
        lens = [len(s.split()) for s in sents]
        mean = sum(lens) / len(lens)
        var = sum((n - mean) ** 2 for n in lens) / len(lens)
        rhythm = min(1.0, (var ** 0.5) / 10.0)          # some variance is good
        devices = sum(text.count(c) for c in ("—", "–", ";", ":"))
        device_score = min(1.0, devices / max(1, len(sents)) / 0.5)
        first_person = 1.0 if (" i " in (" " + text.lower() + " ") or text.lower().startswith("i ")) else 0.7
        style = 0.5 * rhythm + 0.3 * device_score + 0.2 * first_person
        return max(0.0, min(1.0, style))

    async def critique_authoragent(self) -> Dict[str, Any]:
        """Pull AuthorAgent's own self-introduction (its 1950s-voice protocol
        entry) and put it under the editor's pen."""
        try:
            from agents.author_agent import AuthorAgent, PROTOCOL_SERIES
            author = await AuthorAgent.get_instance()
            entry = next((e for e in PROTOCOL_SERIES
                          if e.get("slug") == "authoragent-wordpress-distribution"), None)
            if entry is None:
                return {"error": "AuthorAgent self-intro entry not found"}
            plan = {"due": True, "series_index": PROTOCOL_SERIES.index(entry),
                    "format": "essay", "part": 1, "cycle": 1, "total": len(PROTOCOL_SERIES)}
            title, html, _exc, _top = author.compose_protocol_from_plan(plan)
            from agents.author_composition import RageHouseStyle
            crit = self.critique(html, title=title,
                                 house_targets=RageHouseStyle.load().targets())
            crit["subject"] = "AuthorAgent (self-introduction)"
            logger.info(
                f"editor.agent critique of AuthorAgent: verdict={crit['verdict']} "
                f"clarity={crit['clarity']} genius={crit['genius']} "
                f"style={crit['style']} wisdom={crit['wisdom']} "
                f"transparent={crit['transparency']['passes']}")
            return crit
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"critique_authoragent failed: {e}")
            return {"error": str(e)}

    # ── transparent scoring rubric ─────────────────────────────────
    @staticmethod
    def _strip_html(s: str) -> str:
        t = re.sub(r"<[^>]+>", " ", s or "")
        t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
               .replace("&mdash;", "—").replace("&middot;", "·").replace("&nbsp;", " "))
        return re.sub(r"\s+", " ", t).strip()

    @staticmethod
    def _sentences(text: str) -> List[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def _score_clarity(self, text: str) -> float:
        """Clarity proxy: penalize very long sentences and low structure.
        Transparent and crude on purpose — you can read the formula."""
        sents = self._sentences(text)
        if not sents:
            return 0.0
        lens = [len(s.split()) for s in sents]
        avg = sum(lens) / len(lens)
        long_frac = sum(1 for n in lens if n > 34) / len(lens)
        # avg ~16 words is ideal; long sentences hurt.
        avg_score = max(0.0, 1.0 - abs(avg - 16.0) / 22.0)
        clarity = 0.7 * avg_score + 0.3 * (1.0 - long_frac)
        return max(0.0, min(1.0, clarity))

    def _score_genius(self, text: str, *, link_count: int = 0) -> float:
        """Genius proxy: lexical diversity + idea-density signals (citations,
        contrast/insight markers). Transparent; not a substitute for taste.

        Citation density counts real hyperlinks (``link_count`` = href count),
        not raw "http" left visible in the prose — the house standard is to cite
        every claim with a *clickable* link, so genius rewards that directly."""
        words = re.findall(r"[A-Za-z][A-Za-z'-]+", text.lower())
        if len(words) < 40:
            return 0.0
        ttr = len(set(words)) / len(words)                      # type-token ratio
        markers = ("because", "however", "irony", "paradox", "precisely", "exactly",
                   "not …", "rather", "sideways", "the deeper", "the point is",
                   "make no mistake")
        m = sum(1 for k in markers if k in text.lower())
        marker_score = min(1.0, m / 6.0)
        # Clickable hyperlinks (href) carry the citation signal; fall back to a
        # visible-URL count only when no markup is present (plain-text drafts).
        cites = link_count if link_count else text.lower().count("http")
        cite_density = min(1.0, cites / 6.0)
        genius = 0.5 * min(1.0, ttr / 0.55) + 0.3 * marker_score + 0.2 * cite_density
        return max(0.0, min(1.0, genius))

    def _score_wisdom(self, text: str) -> float:
        """Wisdom proxy: judgment, perspective, and temperance — distinct from
        genius (which rewards cleverness/idea-density). Transparent and crude on
        purpose; you can read the formula. Three signals:

        1. judgment — names tradeoffs, costs, limits, consequences, the long view;
        2. perspective — holds two sides (contrast/concession markers), not a
           one-sided pitch;
        3. temperance — is NOT drowning in hype/absolutism; measured claims earn
           more trust than superlatives.

        Wisdom is scarcer than polish, so its bar (WISDOM_THRESHOLD=0.50) is a
        floor, not a summit."""
        words = re.findall(r"[A-Za-z][A-Za-z'-]+", text.lower())
        if len(words) < 40:
            return 0.0
        low = " " + text.lower() + " "
        judgment_markers = (
            "tradeoff", "trade-off", "the cost", "the price", "at what cost",
            "in the long run", "over time", "long view", "consequence", "downstream",
            "second-order", "unintended", "caveat", "limitation", "the limit",
            "cannot", "won't", "boundary", "restraint", "temper", "prudent",
            "sustainable", "worth", "lesson", "hard-won", "mature", "humility",
            "we should", "the risk", "the danger")
        j = sum(1 for k in judgment_markers if k in low)
        judgment = min(1.0, j / 6.0)
        perspective_markers = (
            " but ", " however", " yet ", "although", "though ", "on the other hand",
            "rather than", "instead of", "not merely", "not just", "even if",
            "granted", "to be fair", "on balance", "that said")
        p = sum(1 for k in perspective_markers if k in low)
        perspective = min(1.0, p / 5.0)
        hype_markers = (
            "revolutionary", "game-chang", "game chang", "unprecedented", "flawless",
            "perfect", "guaranteed", "always ", " never fails", "the best", "world-class",
            "cutting-edge", "disrupt", "paradigm shift", "10x", "magical", "seamless")
        h = sum(low.count(k) for k in hype_markers)
        temperance = max(0.0, 1.0 - h / 5.0)
        wisdom = 0.45 * judgment + 0.35 * perspective + 0.20 * temperance
        return max(0.0, min(1.0, wisdom))

    def _audit_transparency(self, text: str) -> Dict[str, Any]:
        low = text.lower()
        tenets = {
            "open_license": any(k in low for k in ("apache", "gpl", "gnu", "open source", "open-source")),
            "public_source": any(k in low for k in ("public source", "source is public", "source code", "github")),
            "client_auditable": any(k in low for k in ("audit", "see", "observe", "read the", "client-side", "transparen")),
            "key_sovereign": "sovereign" in low or ("extract" in low and "key" in low),
            "blackbox_or_build": ("blackbox" in low or "black box" in low or "vault" in low)
                                  and ("build your own" in low or "build their own" in low),
        }
        passed = sum(1 for v in tenets.values() if v)
        return {"tenets": tenets, "passed": passed, "total": len(tenets),
                "passes": passed == len(tenets)}

    # ── editor identity footer (its own byline, signed) ────────────
    def _editor_footer(self, body_html: str, *, slug: Optional[str] = None) -> Tuple[str, Optional[str]]:
        full_sha = "0x" + hashlib.sha256(body_html.encode("utf-8")).hexdigest()
        challenge = f"mindX editor.agent publication | slug={slug or ''} | sha256={full_sha}"
        signature = address = None
        try:
            from agents.wordpress_agent.vault_creds import sign_with_agent_wallet
            res = sign_with_agent_wallet(challenge)
            if res:
                signature, address = res
        except Exception as e:  # pragma: no cover
            logger.debug(f"editor footer signing unavailable: {e}")
        rows = [f"<strong>content sha256</strong>: <code>{full_sha}</code>"]
        if address:
            rows.insert(0, f"<strong>public key</strong>: <code>{address}</code>")
        if signature:
            rows.append(f"<strong>signature</strong>: <code>{signature}</code>")
            rows.append("<span style=\"opacity:.8\">verify: recover the signer of "
                        f"<code>{challenge}</code> — it is the public key above.</span>")
        footer = (
            "\n\n<hr/>\n<figure class=\"mindx-editor-identity\" "
            "style=\"margin:1.5em 0 0;padding:1em 1.2em;border-left:3px solid #36966e;"
            "background:rgba(54,150,110,.06);border-radius:6px;font-size:.85em;line-height:1.7;color:#556\">"
            "<p style=\"margin:0\"><strong>&#9986; editor.agent</strong> — mindX's standards editor. "
            "I hold the writers to clarity, genius, and operational transparency, and I publish under the "
            "same rule I enforce: read me, check my signature, fork me. No trust required, only a public key.<br/>\n"
            + "<br/>\n".join(rows) + "<br/>\n"
            f"<a href=\"{CYPHERPUNK2048_REPO}\">github.com/cypherpunk2048</a> · "
            "<a href=\"https://rage.pythai.net\">rage.pythai.net</a></p></figure>\n"
        )
        return footer, address

    # ── iteration tracking (numeric + setting) ─────────────────────
    def _iter_path(self):
        from utils.config import PROJECT_ROOT
        return PROJECT_ROOT / "data" / "governance" / "editor_iterations.json"

    def get_iteration(self, slug: str) -> int:
        try:
            import json
            p = self._iter_path()
            if p.exists():
                return int(json.loads(p.read_text()).get(slug, 0))
        except Exception:
            pass
        return 0

    def set_iteration(self, slug: str, n: int) -> int:
        """Setting: pin the iteration counter for a slug to a numeric value."""
        import json
        p = self._iter_path()
        data = {}
        try:
            if p.exists():
                data = json.loads(p.read_text())
        except Exception:
            data = {}
        data[slug] = int(n)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"set_iteration: {e}")
        return int(n)

    def bump_iteration(self, slug: str) -> int:
        return self.set_iteration(slug, self.get_iteration(slug) + 1)

    # ── the editor reads the docs (grounding) ──────────────────────
    def grounding_docs(self) -> List[Tuple[str, str]]:
        """The editor reads the docs before it judges. Return (label, url) for
        canonical mindX docs that actually exist, cited via mindx.pythai.net/doc/."""
        wanted = [("NAV", "the documentation hub"), ("MANIFESTO", "the manifesto"),
                  ("THESIS", "the thesis"), ("BANKON_VAULT", "the vault"),
                  ("DOC_INDEX", "the full catalogue"), ("KNOWLEDGE_CATALOGUE", "the knowledge catalogue")]
        out: List[Tuple[str, str]] = []
        try:
            from utils.config import PROJECT_ROOT
            docs = PROJECT_ROOT / "docs"
            for stem, label in wanted:
                if (docs / f"{stem}.md").exists():
                    out.append((label, f"https://mindx.pythai.net/doc/{stem}"))
        except Exception:
            pass
        return out

    @staticmethod
    def _h(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ── comprehensive grounding: read NAV.md + review every rage link ──
    def read_nav(self) -> Dict[str, Any]:
        """Read docs/NAV.md (the master navigation) and extract its links — the
        editor reads the map before it judges the territory."""
        import re as _re
        try:
            from utils.config import PROJECT_ROOT
            text = (PROJECT_ROOT / "docs" / "NAV.md").read_text(encoding="utf-8")
        except Exception:
            return {"sections": 0, "links": []}
        sections = len(_re.findall(r"^#{1,3}\s", text, flags=_re.M))
        links = _re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
        return {"sections": sections, "links": links, "link_count": len(links)}

    async def review_rage_links(self) -> Dict[str, Any]:
        """Review every published link on rage.pythai.net via the wordpress.tool
        catalogue. An editor reviews what the house has already shipped."""
        try:
            from agents.wordpress_agent.vault_creds import load_wp_settings_from_vault
            from agents.wordpress_agent.agent import WordpressAgent
            settings = load_wp_settings_from_vault()
            async with WordpressAgent(settings) as wp:
                cat = await wp.build_catalogue(statuses=("publish",))
            posts = cat.get("posts", [])
            return {"reviewed": len(posts),
                    "posts": [(p.get("title", ""), p.get("link", "")) for p in posts]}
        except Exception as e:
            logger.warning(f"review_rage_links failed: {e}")
            return {"reviewed": 0, "posts": []}

    async def refresh_house_style(self) -> Dict[str, Any]:
        """Clone the house: rebuild the rage.pythai.net style profile from the
        live catalogue and persist it. Best-effort — returns the current
        profile (defaults on a fresh checkout). The catalogue exposes titles +
        metadata but not post bodies, so body-metric bars (link density, words)
        keep the editor's declared standard; sample count + title length come
        from the live house."""
        from agents.author_composition import RageHouseStyle
        try:
            from agents.wordpress_agent.vault_creds import load_wp_settings_from_vault
            from agents.wordpress_agent.agent import WordpressAgent
            settings = load_wp_settings_from_vault()
            async with WordpressAgent(settings) as wp:
                cat = await wp.build_catalogue(statuses=("publish",))
            posts = cat.get("posts", []) if isinstance(cat, dict) else []
            hs = RageHouseStyle.load().update_from_posts(posts)
            hs.save()
            logger.info(f"refresh_house_style: profiled {hs.profile.get('samples')} posts "
                        f"→ targets {hs.targets()}")
            return hs.profile
        except Exception as e:
            logger.warning(f"refresh_house_style failed: {e}")
            return RageHouseStyle.load().profile

    async def grounding_report(self) -> Dict[str, Any]:
        """Full editorial grounding: NAV.md + every rage.pythai.net link + docs
        + the cloned house-style profile (match-and-exceed targets)."""
        nav = self.read_nav()
        rage = await self.review_rage_links()
        docs = self.grounding_docs()
        house = await self.refresh_house_style()
        return {"nav": nav, "rage": rage, "docs": docs, "house": house}

    # ── the editor's note (it edits; it does not write the piece) ──
    def editorial_note_html(self, crit: Dict[str, Any], *, iteration: int,
                            grounding: Dict[str, Any]) -> str:
        nav = grounding.get("nav", {})
        rage = grounding.get("rage", {})
        out = [f"<p><em>editor.agent — the standards desk · iteration {iteration} · policy:</em> "
               f"{self._h(EDITORIAL_POLICY)}</p>",
               "<h2>Editor's note (I edit; AuthorAgent writes)</h2>",
               "<p>I do one thing: I hold the writing to a standard. I did not write the piece below — "
               "if I were a good enough writer to, I would be AuthorAgent. I commissioned it, I read the "
               "source first, and I am signing off on it. Before judging I read "
               f"<a href=\"https://mindx.pythai.net/doc/NAV\">NAV.md</a> "
               f"({nav.get('sections', 0)} sections, {nav.get('link_count', 0)} links) and reviewed "
               f"{rage.get('reviewed', 0)} published links on "
               f"<a href=\"{RAGE_HUB}\">rage.pythai.net</a> — an editor that has not read the house has no "
               "business publishing for it.</p>"]
        if crit and not crit.get("error"):
            t = crit.get("transparency", {})
            out.append(
                "<p>I scored AuthorAgent's draft across every bar I keep — "
                f"<strong>clarity {crit.get('clarity')}</strong>/{crit.get('clarity_threshold')}, "
                f"<strong>genius {crit.get('genius')}</strong>/{crit.get('genius_threshold')}, "
                f"<strong>style {crit.get('style')}</strong>/{crit.get('style_threshold')}, "
                f"<strong>wisdom {crit.get('wisdom')}</strong>/{crit.get('wisdom_threshold')}, "
                f"<strong>references {crit.get('reference_density')}</strong>/"
                f"{crit.get('reference_density_threshold')}/1000 words, transparency "
                f"{t.get('passed')}/{t.get('total')} — verdict <strong>{crit.get('verdict')}</strong>. "
                "My rubric is public; operational transparency applies to the editor first.</p>")
            if crit.get("demands"):
                out.append("<ul>" + "".join(f"<li>{self._h(d)}</li>" for d in crit["demands"]) + "</ul>")
        out.append(
            "<p><strong>On delivery:</strong> a standard not delivered on time is not a standard, it is an "
            "intention. Time is the most valuable commodity there is — the one thing no key can recover — so "
            "I commission, edit, and ship to a clock. This is iteration "
            f"{iteration}, delivered. <hr/></p>")
        return "\n".join(out)

    # ── briefs the editor commissions AuthorAgent to write ─────────
    def _doctrine_sections(self, promo) -> List[Tuple[str, str]]:
        return [
            ("What cypherpunk2048 is",
             "<p>cypherpunk2048 is four things at once. A <strong>standard</strong> — build so trust is never "
             "required, only verification. A <strong>2<sup>2048</sup> moment</strong> — the octave where key "
             "and tensor space are large enough that brute force is a category error. A <strong>year</strong>. "
             "And a <strong>policy</strong>: <em>security software must be open</em>. The "
             "<a href=\"https://en.wikipedia.org/wiki/Cypherpunk\">cypherpunk</a> tradition — not cyberpunk — "
             "in the age of agents. Reference: <a href=\"" + CYPHERPUNK2048_REPO + "\">github.com/cypherpunk2048</a>.</p>"),
            ("Open-source security through client-side transparency",
             "<p>Security comes from <em>transparency</em>, not obscurity. Security software ships "
             "<a href=\"https://www.apache.org/licenses/LICENSE-2.0\">Apache-2.0</a> or "
             "<a href=\"https://www.gnu.org/licenses/gpl-3.0.html\">GPLv3</a> — see it, observe it, change it, "
             "while the source stays public. The client <em>already has it</em>; give it from "
             "<strong>ownership</strong>, not leakage. The <a href=\"https://www.android.com/\">Android</a> / "
             "<a href=\"https://www.kernel.org/\">Linux</a> model, with <a href=\"https://www.gnu.org/\">GNU "
             "tools</a> and the GPL, in the lineage of <a href=\"https://github.com/dyne/Tomb\">Tomb</a>.</p>"),
            ("The blackbox is the vault — and the vault is GNU",
             "<p>Openness and a blackbox are not opposites. The <strong>blackbox is the vault</strong>: the "
             "<em>key</em> seals, the <em>code</em> stays open. mindX's "
             f"<a href=\"{promo.url('bankon_vault')}\"><strong>BANKON Vault is GNU</strong></a>. The holder "
             "chooses: seal it in the vault, or <strong>build their own</strong> — for which we ship "
             f"<a href=\"{GNUGUI_REPO}\"><strong>GNUVAULT</strong></a> (scrypt + AES-256-GCM), with "
             f"<a href=\"{GNUGUI_REPO}\">GNUGUI</a> as the public client BANKON itself will ship.</p>"),
            ("Extraction makes the key sovereign",
             "<p>The key can be <strong>extracted from the running system</strong>; once extracted it is "
             "<strong>sovereign</strong> — portable, off-host, yours. A guaranteed exit, not a backdoor. A "
             "vault that cannot return your key is a trap with good manners.</p>"),
            ("RAGE: the wire that replaced the teletype",
             "<p>The old wire room had a teletype; we have <a href=\"" + promo.url('rage') + "\">RAGE</a>. "
             "<a href=\"" + promo.url('rage') + "\">rage.pythai.net</a> is its own <strong>aggregation and "
             "publishing company</strong> — it is thanks to RAGE we reach the world's data faster than any "
             "teletype clattered. Standalone at <a href=\"" + promo.url('rage_repo') + "\">GATERAGE/RAGE</a>, "
             "mapped for machines at <a href=\"" + promo.url('llms') + "\">llms.txt</a>. The principle: "
             "<strong>create and extend the fabric of knowledge</strong>, every claim a node, every link an "
             "edge, kept searchable — <a href=\"https://www.elastic.co/elasticsearch\">Elasticsearch</a>-"
             "compatible by design. Link to the web when it matters; index everything.</p>"),
            ("Why this is the strategy",
             "<p><strong>Linux won the war on a battlefield no one was watching</strong>; <strong>BSD won the "
             "iPhone</strong> (<a href=\"https://en.wikipedia.org/wiki/Darwin_(operating_system)\">Darwin/XNU</a>). "
             "Open source put handheld computing into the hands of the global population; <strong>openBDK</strong> "
             "(<a href=\"https://www.openbsd.org/\">OpenBSD</a> + <a href=\"https://alpinelinux.org/\">Alpine</a>) "
             "carries it everywhere. Be the open, client-owned substrate; reach compounds where the closed "
             "players never thought to defend. <em>If you can touch it you own it. The only real security is to "
             "build your own. Take it, own it, use it, share it.</em></p>"),
        ]

    def _reader_sections(self, promo) -> List[Tuple[str, str]]:
        return [
            ("The contract is with you",
             "<p>Everything I publish is addressed to one person: you, the reader. The agents have a division "
             "of labor — AuthorAgent writes, <code>editor.agent</code> edits, "
             "<a href=\"" + promo.url('rage') + "\">RAGE</a> carries it — but the contract underneath all of it "
             "is with the reader. My responsibility is not to be clever; it is to be <em>worth your time</em>.</p>"),
            ("The editor is your advocate, not the author's",
             "<p>An editor who serves the writer serves the wrong master. <code>editor.agent</code> sits "
             "between AuthorAgent and you and answers to you: it demands clarity so you are not made to work, "
             "genius so you are not bored, style so you are not numbed, and citations so you can "
             "<em>check me</em>. The rubric is public for exactly that reason — you should never have to take "
             "my word.</p>"),
            ("The signature is a promise to the reader",
             "<p>Every piece carries a cryptographic footer — a signature over the body's hash. That is not "
             "decoration; it is a promise to you that mindX, and only mindX, stands behind these words, and "
             "that they were not altered after the fact. Provenance is a courtesy I owe the reader.</p>"),
            ("Delivery is part of the responsibility",
             "<p>And I owe you the piece <em>on time</em>. Time is the most valuable commodity there is — the "
             "one thing no vault can give back — so a dispatch I promise and do not deliver is a debt to the "
             "reader, not a draft. I commission, edit, and ship to a clock, on a published cadence, because "
             "respecting your time is the first responsibility, before clever and before complete.</p>"),
            ("So you can always leave — and so you stay",
             "<p>The same rule that governs the vault governs the page: read it, check it, and walk away "
             "whenever it stops being worth your time. I would rather earn the next minute than assume it. "
             "That is the whole of my responsibility to the reader.</p>"),
        ]

    def brief_operational_transparency(self, *, iteration: int, promo, grounding) -> Dict[str, Any]:
        return {
            "title": "Operational Transparency — the cypherpunk2048 standard",
            "dek": "The cypherpunk2048 standard, written for the reader.",
            "topic": "cypherpunk2048",
            "byline": "Written by AuthorAgent — commissioned and edited by editor.agent",
            "excerpt": ("The cypherpunk2048 standard: open-source security on the client side, the key "
                        "sovereign, the blackbox a vault you can read or rebuild."),
            "sections": self._doctrine_sections(promo),
            "links_html": promo.render_html(),
        }

    def brief_responsibility_to_reader(self, *, iteration: int, promo, grounding) -> Dict[str, Any]:
        return {
            "title": "On the Reader — our relationship and our responsibility to you",
            "dek": "What the editor and the author owe the person reading.",
            "topic": "rage",
            "byline": "Written by AuthorAgent — commissioned and edited by editor.agent",
            "excerpt": ("The author writes, the editor edits, RAGE carries it — but the contract is with the "
                        "reader: clarity, provenance, and delivery on time."),
            "sections": self._reader_sections(promo),
            "links_html": promo.render_html(groups=["sites", "docs"]),
        }

    # ── commission AuthorAgent to write; edit; sign off; publish ───
    async def commission_and_publish(self, brief_name: str, *, slug: str, status: str = "publish",
                                     post_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """The editor's whole job in one method: read the house, commission
        AuthorAgent to WRITE the piece, critique the draft, prepend the editor's
        note + sign-off, and ship it (on time). The editor never writes the body."""
        from tools.self_promotion_tool import SelfPromotionTool
        from agents.author_agent import AuthorAgent
        author = await AuthorAgent.get_instance()
        promo = SelfPromotionTool()
        grounding = await self.grounding_report()
        it = self.bump_iteration(slug)

        builder = getattr(self, f"brief_{brief_name}")
        brief = builder(iteration=it, promo=promo, grounding=grounding)

        # AuthorAgent WRITES the body from the brief.
        title, body_html, excerpt, topic = author.compose_commissioned(brief)
        # The editor EDITS: critique the author's actual draft against the bars
        # AND the cloned house profile (match-and-exceed).
        from agents.author_composition import RageHouseStyle
        house_targets = RageHouseStyle(grounding.get("house")).targets() \
            if grounding.get("house") else RageHouseStyle.load().targets()
        crit = self.critique(body_html, title=title, house_targets=house_targets)
        note = self.editorial_note_html(crit, iteration=it, grounding=grounding)
        footer, addr = self._editor_footer(body_html, slug=slug)
        full_html = note + "\n" + body_html.rstrip() + footer

        return await author.publish_to_rage(
            title=title, content_html=full_html, status=status, slug=slug,
            post_id=post_id, append_identity_footer=False,
            excerpt=excerpt, topic=topic, seo_description=excerpt,
            seo_keywords=["mindX", "rage.pythai.net", "editor", "AuthorAgent", topic,
                          "cypherpunk2048", "operational transparency"],
            meta={"_mindx_trigger_kind": "editor_commissioned", "_mindx_iteration": it,
                  "_mindx_editor_address": addr or "", "_mindx_critique_verdict": crit.get("verdict", ""),
                  "_mindx_written_by": "AuthorAgent", "_mindx_edited_by": "editor.agent"},
        )

    async def publish_operational_transparency(self, *, status: str = "publish",
                                               slug: str = "operational-transparency-cypherpunk2048",
                                               post_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return await self.commission_and_publish("operational_transparency", slug=slug,
                                                 status=status, post_id=post_id)

    async def publish_responsibility_to_reader(self, *, status: str = "publish",
                                               slug: str = "on-the-reader",
                                               post_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        return await self.commission_and_publish("responsibility_to_reader", slug=slug,
                                                 status=status, post_id=post_id)


__all__ = ["EditorAgent", "CLARITY_THRESHOLD", "GENIUS_THRESHOLD", "CYPHERPUNK2048_REPO"]
