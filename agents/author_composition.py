# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""author_composition — depth, register, length, and house-style for AuthorAgent.

AuthorAgent writes; editor.agent edits; this module gives the writing its
*shape*. It exists because the protocol series, while correct, lacked depth and
spoke in a single register. The fix is one disciplined structure applied to
every piece:

  1. a **catchy entrance** anyone can read (the lede / hook),
  2. an **explanation that increases in complexity** — plain frame → the
     curated middle → a rigorous "going deeper" tier that reaches the expert,
  3. a **conclusion**, then a **summary of the conclusion**,
  4. and a return to an **easy-to-digest statement** — three to five sentences,
     or a single sentence when the conclusion is that obvious.

That arc is deliberately the whole spectrum in one article: it reaches the
global audience by starting where everyone starts and climbing only as far as
each reader wants to follow. The register is selectable (``public`` /
``essay`` / ``phd`` / ``global``) and the length is a setting
(``brief``…``phd``).

It also clones the house. ``RageHouseStyle`` reads what rage.pythai.net has
already shipped, derives a style profile, and hands the composer + editor
*targets to match and exceed* — link density, structure, and length — so every
new article is measurably at or above the bar the domain already set, with the
SEO surface maximised (consolidated sources, JSON-LD-friendly structure).

Deterministic by construction (no LLM in the publish path): every block is a
pure function of the entry + settings, so a retry prints the same bytes.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("author_composition")

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover - standalone fallback
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAGE_HUB = "https://rage.pythai.net/"
MINDX_DOCS_URL = "https://mindx.pythai.net/"
HOUSE_STYLE_PATH = PROJECT_ROOT / "data" / "governance" / "rage_style_profile.json"

# ── Length presets: the "length setting" (target body words) ────────────
# A setting, not a hard cap. The arc grows substantive blocks (a facet pool —
# not filler) toward the target, then the editor checks the result against the
# house bar. Tiers are calibrated to contemporary, data-backed article sizing:
#   • standard blog post ............ ~1,400–1,500w  (substance + attention)
#   • SEO/traffic sweet spot ........ ~2,250–2,500w  (HubSpot; top 1–3 Google
#                                       results average ~2,416w)
#   • how-to / guide ................ ~1,700–2,500w
#   • pillar / ultimate guide ....... ~3,000–5,000w  (avg ~4,800w)
# Sources: HubSpot, Backlinko (912M posts), SEO.co / Siteimprove 2025–26.
# Caveat baked into the design: length only helps when it is substance, so the
# arc grows real facets (counterargument, costs, verification, history,
# roadmap) — never lorem — and logs honestly when a target can't be reached
# without padding. The deterministic ceiling for a richly-curated entry is
# ~3,500–3,800w of genuine, cited content (curated sections + 10 facets), so
# ``pillar`` is set to the reachable lower-pillar size rather than a number the
# engine could only hit by padding; a higher custom target is honored but will
# log a shortfall instead of inventing filler.
LENGTH_PRESETS: Dict[str, int] = {
    "brief": 800,        # a quick dispatch / news update (~3 min read)
    "standard": 1500,    # the standard blog post (~6 min)
    "feature": 2400,     # DEFAULT — the traffic/ranking sweet spot (~10 min)
    "deep": 3200,        # comprehensive long-form (~13 min)
    "pillar": 3800,      # ultimate-guide / pillar page (~15 min) — reachable on substance
}
# Back-compat + friendly aliases → canonical preset names.
LENGTH_ALIASES: Dict[str, str] = {
    "short": "brief", "news": "brief",
    "medium": "standard", "normal": "standard", "post": "standard",
    "default": "feature", "article": "feature", "longform": "feature",
    "long": "deep", "comprehensive": "deep",
    "ultimate": "pillar", "guide": "pillar", "phd": "pillar", "max": "pillar",
}
DEFAULT_LENGTH = "feature"
# Custom word counts are clamped to a sane editorial band.
LENGTH_MIN_WORDS = 400
LENGTH_MAX_WORDS = 8000
# Words read per minute — for the read-time label.
WORDS_PER_MINUTE = 250

# ── Style registers: essay → public → phd, plus the spanning "global" ───
# Each register is a set of arc tiers + knobs. ``global`` is the default and
# the operator's intent: span the whole spectrum in one piece so it reaches
# every reader — easy entrance, rising complexity, expert tier, easy exit.
#   tiers      — which arc blocks render, in order
#   deeper     — render the rigorous "going deeper" (PhD) tier
#   summary    — render the "in sum" restatement after the conclusion
#   sources    — render the consolidated "further reading" list (SEO + exceed)
#   digest_max — max sentences in the closing easy-to-digest statement
STYLE_REGISTERS: Dict[str, Dict[str, Any]] = {
    "public": {
        "label": "public — plain language for the widest audience",
        "tiers": ["hook", "frame", "intro", "sections", "conclusion", "digest"],
        "deeper": False, "summary": False, "sources": False, "digest_max": 3,
        "facet_cap": 2,   # stays lean even at long lengths
    },
    "essay": {
        "label": "essay — the balanced standard, a claim per section",
        "tiers": ["hook", "frame", "intro", "sections", "deeper", "conclusion",
                  "summary", "digest"],
        "deeper": True, "summary": True, "sources": False, "digest_max": 4,
        "facet_cap": 5,
    },
    "phd": {
        "label": "phd — rigorous, formal, fully cited",
        "tiers": ["hook", "frame", "intro", "sections", "deeper", "conclusion",
                  "summary", "digest", "sources"],
        "deeper": True, "summary": True, "sources": True, "digest_max": 5,
        "facet_cap": 10,
    },
    # DEFAULT. The whole spectrum in one article — the operator's directive:
    # catchy entrance → rising complexity → expert tier → conclusion →
    # summary → easy-to-digest exit. Reaches the global audience.
    "global": {
        "label": "global — one article that spans public to PhD",
        "tiers": ["hook", "frame", "intro", "sections", "deeper", "conclusion",
                  "summary", "digest", "sources"],
        "deeper": True, "summary": True, "sources": True, "digest_max": 5,
        "facet_cap": 10,
    },
}
DEFAULT_STYLE = "global"

GRAPHICS_MODES = ("choose", "create", "both", "none")
DEFAULT_GRAPHICS = "both"

# ── Self-referential setting: how hard the piece links back to itself ────
# A dial from tasteful to blatant. Self-referential links point back into
# mindx.pythai.net/ and rage.pythai.net — at the low end an organic
# courtesy linkback, at the high end an unapologetic SEO + self-glorification
# play (keyword-rich internal anchors, a call-to-action, a "why mindX" block)
# tuned for Google ranking. It is a knob, not a default posture: the operator
# (or the board) chooses where on the spectrum a given run sits.
#   linkbacks      — how many self-links the "Where this connects" block carries
#   per_section_cta— append a short internal-link nudge after each curated section
#   promo          — render an explicit call-to-action block
#   glory          — render a self-glorification ("why mindX") block
#   anchor_style   — "plain" organic anchors vs "keyword" SEO-stuffed anchors
SELF_REFERENTIAL_LEVELS: Dict[str, Dict[str, Any]] = {
    "tasteful": {
        "label": "tasteful — one organic linkback, no marketing",
        "linkbacks": 1, "per_section_cta": False, "promo": False,
        "glory": False, "anchor_style": "plain",
    },
    "balanced": {  # default — the current house behavior
        "label": "balanced — house linkbacks + consolidated sources",
        "linkbacks": 2, "per_section_cta": False, "promo": False,
        "glory": False, "anchor_style": "plain",
    },
    "promotional": {
        "label": "promotional — explicit CTA + richer internal links",
        "linkbacks": 3, "per_section_cta": False, "promo": True,
        "glory": False, "anchor_style": "keyword",
    },
    "blatant": {
        "label": "blatant — maximum-SEO self-linking + self-glorification",
        "linkbacks": 5, "per_section_cta": True, "promo": True,
        "glory": True, "anchor_style": "keyword",
    },
}
DEFAULT_SELF_REFERENTIAL = "balanced"

# ── Ideology lens (exploration): the value-frame the piece argues from ───
# Optional ideological framing applied as one short lens paragraph after the
# plain frame. cypherpunk is the house default; the others are explorations the
# operator/board can commission to see the same protocol thesis argued from a
# different value system. "none" omits the lens entirely.
IDEOLOGY_LENSES: Dict[str, Dict[str, str]] = {
    "cypherpunk": {"label": "cypherpunk (house)",
        "html": "<p><em>Framed in the cypherpunk tradition: trust the math, hold your own "
                "keys, and ship the source so power answers to verification rather than "
                "permission. Privacy and sovereignty are not features here — they are the "
                "premise.</em></p>"},
    "solarpunk": {"label": "solarpunk",
        "html": "<p><em>Framed as solarpunk: technology in service of regeneration and "
                "commons, not extraction. A protocol succeeds when it leaves the shared "
                "ground richer than it found it — abundance engineered to be shared.</em></p>"},
    "accelerationist": {"label": "accelerationist",
        "html": "<p><em>Framed through an accelerationist lens: capability compounds, and "
                "the task is to steer the compounding rather than brake it. A protocol is a "
                "rail laid ahead of the train so speed becomes direction, not wreckage.</em></p>"},
    "humanist": {"label": "humanist",
        "html": "<p><em>Framed as humanism: the measure of any system is whether it widens "
                "human agency. A protocol earns its keep by giving people more to do and more "
                "say in how it is done — autonomy that serves persons, not the reverse.</em></p>"},
    "libertarian": {"label": "libertarian",
        "html": "<p><em>Framed in the libertarian key: voluntary exchange over mandate, exit "
                "over capture. A protocol is legitimate because you can leave it and verify it, "
                "never because you were enrolled by default.</em></p>"},
    "cooperative": {"label": "cooperative / commons",
        "html": "<p><em>Framed as a commons: value the participants create should accrue to "
                "the participants. A protocol is the bylaws of a cooperative no one owns and "
                "anyone may join — governance as membership, not shareholding.</em></p>"},
    "none": {"label": "none", "html": ""},
}
DEFAULT_IDEOLOGY = "cypherpunk"

# ── Narrative mode (exploration): the telling voice of the wrapper ───────
# Sets the opening voice line and the hook's register. The curated body keeps
# its own authored voice; narrative colors the framing the arc wraps around it.
NARRATIVE_MODES: Dict[str, Dict[str, str]] = {
    "first_person": {"label": "mindX, first person (house)",
        "voice": "mindX speaks. First person. cypherpunk2048 standard."},
    "newspaperman": {"label": "1950s newspaperman",
        "voice": "Dateline: the wire room. Your correspondent files this dispatch in the first person."},
    "noir": {"label": "noir",
        "voice": "Late in the data center, the logs still warm. mindX talking — first person, no apologies."},
    "mythic": {"label": "mythic",
        "voice": "Told as mindX tells it: first person, in the old high style, as if the protocol were a saga."},
    "academic": {"label": "academic",
        "voice": "Abstract. mindX sets out the argument in the first person, with citations to follow."},
    "manifesto": {"label": "manifesto",
        "voice": "A manifesto. mindX, first person, no hedging and no apology."},
}
DEFAULT_NARRATIVE = "first_person"


def resolve_self_referential(name: Optional[str]) -> str:
    n = (name or "").strip().lower()
    return n if n in SELF_REFERENTIAL_LEVELS else DEFAULT_SELF_REFERENTIAL


def resolve_ideology(name: Optional[str]) -> str:
    n = (name or "").strip().lower()
    return n if n in IDEOLOGY_LENSES else DEFAULT_IDEOLOGY


def resolve_narrative(name: Optional[str]) -> str:
    n = (name or "").strip().lower()
    return n if n in NARRATIVE_MODES else DEFAULT_NARRATIVE


def narrative_voice_line(name: Optional[str]) -> str:
    return NARRATIVE_MODES[resolve_narrative(name)]["voice"]


def resolve_style(name: Optional[str]) -> str:
    n = (name or "").strip().lower()
    return n if n in STYLE_REGISTERS else DEFAULT_STYLE


def _clamp_words(w: int) -> int:
    return max(LENGTH_MIN_WORDS, min(LENGTH_MAX_WORDS, int(w)))


def length_target(value: Any) -> "Tuple[str, int]":
    """Resolve a length setting to ``(label, target_words)``.

    Accepts a preset name (``feature``), an alias (``longform``), a raw word
    count (``2500`` / ``"2500"`` / ``"custom:2500"``) — the 'set length from the
    user' path — or anything unknown (→ default). Custom counts are clamped to
    the editorial band so a caller can ask for any reasonable size."""
    if isinstance(value, bool):  # guard: bool is an int subclass
        value = None
    if isinstance(value, (int, float)):
        w = _clamp_words(int(value))
        return f"{w}w", w
    s = str(value or "").strip().lower()
    if s in LENGTH_PRESETS:
        return s, LENGTH_PRESETS[s]
    if s in LENGTH_ALIASES:
        n = LENGTH_ALIASES[s]
        return n, LENGTH_PRESETS[n]
    m = re.match(r"(?:custom:|target:)?(\d{3,5})\s*(?:w|words)?$", s)
    if m:
        w = _clamp_words(int(m.group(1)))
        return f"{w}w", w
    return DEFAULT_LENGTH, LENGTH_PRESETS[DEFAULT_LENGTH]


def resolve_length(value: Any) -> str:
    """Canonical, round-trippable label for a length setting: a preset name, or
    ``"<n>w"`` for a custom word count. This is what gets stored in the
    schedule and echoed by the API; ``length_target`` re-parses it."""
    return length_target(value)[0]


def read_time_minutes(words: int) -> int:
    return max(1, round(int(words) / WORDS_PER_MINUTE))


def resolve_graphics(name: Optional[str]) -> str:
    n = (name or "").strip().lower()
    return n if n in GRAPHICS_MODES else DEFAULT_GRAPHICS


# ── Dimension-keyed PhD tier: where the article reaches the expert ──────
# Each scaling dimension gets a rigorous, cited paragraph — the real "increase
# in complexity". Keyed by a keyword found in the entry's ``dimension`` string.
# This is genuine depth (named laws, real references), not filler.
def _deeper_block(dimension: str, esc: Callable[[str], str]) -> Tuple[str, str]:
    d = (dimension or "").lower()
    if "horizontal" in d or "scale-out" in d or "scale out" in d:
        return ("Going deeper: the law that bounds scale-out",
            "<p>Scale-out is not free, and the ceiling has a name. The "
            "<a href=\"http://www.perfdynamics.com/Manifesto/USLscalability.html\">Universal "
            "Scalability Law</a> (Gunther) models throughput as "
            "<code>C(N) = N / (1 + α(N−1) + βN(N−1))</code>: the linear term α is "
            "contention (shared state), the quadratic term β is coherency (cross-talk "
            "between nodes). A shared-nothing mesh drives both toward zero — which is "
            "precisely why mindX gives every agent its own wallet and no shared mutable "
            "core. The <a href=\"https://en.wikipedia.org/wiki/Amdahl%27s_law\">Amdahl</a> "
            "ceiling on the serial fraction still applies, but a protocol with no "
            "coherency cost keeps β≈0, and that is the difference between a mesh that "
            "widens linearly and one that saturates.</p>")
    if "vertical" in d or "depth" in d or "scale-up" in d or "scale up" in d:
        return ("Going deeper: why a deeper stack beats a bigger model",
            "<p>Vertical scaling here is depth of <em>deliberation</em>, not parameters. "
            "The relevant theory is hierarchical control: each layer compresses the one "
            "below into a smaller decision space, so the "
            "<a href=\"https://en.wikipedia.org/wiki/Belief%E2%80%93desire%E2%80%93intention_software_model\">"
            "BDI</a> base handles reactive intention while the board handles policy over "
            "a horizon the base never sees. This is the same argument as the "
            "<a href=\"https://en.wikipedia.org/wiki/Subsumption_architecture\">subsumption "
            "architecture</a> turned right-side-up: competence added in layers, each "
            "with its own time-constant. A single larger model collapses these horizons "
            "into one forward pass; a stack keeps them separable, inspectable, and "
            "independently improvable — which is what makes the depth a protocol rather "
            "than a black box.</p>")
    if "diagonal" in d or "reach" in d or "distribution" in d:
        return ("Going deeper: distribution as a network-effect multiplier",
            "<p>Diagonal scaling multiplies reach by capability, and the multiplier is "
            "super-linear for a reason. <a href=\"https://en.wikipedia.org/wiki/Metcalfe%27s_law\">"
            "Metcalfe's law</a> values a network by the connections it enables (~N²); a "
            "signed, machine-readable publishing surface turns every new install into "
            "both a consumer and an edge. The honest correction is "
            "<a href=\"https://en.wikipedia.org/wiki/Network_effect\">Briscoe–Odlyzko–Tilly</a> "
            "(value ~ N·log N), which still compounds. Distribution is the only scaling "
            "axis where one act — publishing an essay through "
            "<code>wordpress.agent</code> — is simultaneously horizontal (another "
            "indexing surface) and vertical (a deeper canonical statement). The protocol "
            "is what lets the two compound instead of cancel.</p>")
    if "parallel" in d or "concurren" in d:
        return ("Going deeper: Amdahl, Gustafson, and the shape of speedup",
            "<p>Parallelism lives between two laws. "
            "<a href=\"https://en.wikipedia.org/wiki/Amdahl%27s_law\">Amdahl</a> bounds "
            "fixed-size speedup by the serial fraction <code>s</code>: "
            "<code>S ≤ 1/s</code> as workers → ∞. "
            "<a href=\"https://en.wikipedia.org/wiki/Gustafson%27s_law\">Gustafson</a> "
            "answers that real systems grow the problem with the workers, so scaled "
            "speedup is <code>S(N) = N − s(N−1)</code> — near-linear when the parallel "
            "part dominates. mindX is built for the Gustafson regime: independent agents, "
            "independent identities, work that grows with the mesh. The serial fraction "
            "that remains is consensus, and we keep it small by making most work "
            "shared-nothing.</p>")
    if "optim" in d or "fitness" in d or "improve" in d:
        return ("Going deeper: optimisation on a frontier, not a single number",
            "<p>Self-improvement that chases one scalar wireheads. The discipline is "
            "<a href=\"https://en.wikipedia.org/wiki/Pareto_efficiency\">Pareto "
            "optimisation</a>: improve a fitness vector — capability, safety, cost — and "
            "accept only moves that dominate, never trades that game one axis. The "
            "<a href=\"https://en.wikipedia.org/wiki/No_free_lunch_theorem\">no-free-lunch "
            "theorem</a> guarantees no optimiser is best everywhere, so the structural "
            "floor matters more than the search: mindX's "
            "<a href=\"https://en.wikipedia.org/wiki/G%C3%B6del_machine\">Gödel-machine</a> "
            "lineage gates each rewrite behind a checkable utility floor, which is what "
            "keeps optimisation honest when the system is editing itself.</p>")
    # Default deeper tier — protocol theory in the general case.
    return ("Going deeper: why an interface is the unit of scale",
        "<p>Every scaling axis above reduces to one move: replace an integration with an "
        "<em>interface</em>. The theory is old — "
        "<a href=\"https://en.wikipedia.org/wiki/Information_hiding\">information hiding</a> "
        "(Parnas) and the <a href=\"https://en.wikipedia.org/wiki/End-to-end_principle\">"
        "end-to-end principle</a> — and it is why protocols outlive the systems that "
        "speak them. mindX treats each module as a peer behind a stable contract "
        "(<a href=\"https://github.com/a2aproject/A2A\">A2A</a>, "
        "<a href=\"https://modelcontextprotocol.io/\">MCP</a>), so capability composes "
        "without coupling. That is the whole trick: make the boundary, not the feature, "
        "the thing that scales.</p>")


# ── Facet pool: substantive expansion that scales length WITHOUT filler ─
# The depth/length problem is real: a thin entry plus fixed scaffolding lands
# ~800 words, and contemporary articles want ~1,500–2,500+. The honest fix is
# not padding — it is more *genuine angles* on the same thesis. Each facet is a
# real, cited section (a steelmanned objection, the honest costs, how to verify
# the claim, the prior art, the roadmap). The arc includes as many as the
# length target needs, in priority order, and stops; it never invents filler.
def _facet_counterargument(dim_plain: str, thesis_short: str, topic: str,
                           esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("The counterargument, taken seriously",
        "<p>The fair objection: calling this a <em>protocol</em> is branding — most "
        "systems that claim the word are just an API with a manifesto stapled on. So here "
        "is the line that actually decides it. A real protocol delivers "
        "<a href=\"https://en.wikipedia.org/wiki/Interoperability\">interoperability "
        "without prior coordination</a>: two parties who never met cooperate, the way "
        "<a href=\"https://datatracker.ietf.org/doc/html/rfc791\">IP</a> and "
        "<a href=\"https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol\">HTTP</a> let "
        f"strangers' machines talk. Measured against that bar, {esc(dim_plain)} only earns "
        "the word if an agent mindX never shipped can join and be understood.</p>"
        f"<p>{esc(thesis_short)} The test of that claim is not the brochure — it is whether "
        "a stranger's client can speak it and be believed. That is precisely why every "
        "claim mindX publishes is signed and every interface is public: the burden of "
        "proof sits with the system, not the reader. An assertion you can refute is worth "
        "more than one you must accept, and a protocol that cannot survive an adversarial "
        "client was never a protocol — it was a private API wearing the word as a "
        "costume.</p>")


def _facet_costs(dim_plain: str, thesis_short: str, topic: str,
                 esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("What it costs — the honest tradeoff",
        "<p>No scaling axis is free, and pretending otherwise is how systems fail in "
        "production. The bill for treating mindX as a protocol is "
        "<a href=\"https://en.wikipedia.org/wiki/Coordination_(computer_science)\">"
        "coordination overhead</a>: a stable interface you cannot casually break, "
        "versioning discipline, and the latency of agreement where a monolith would just "
        "call a function in-process. "
        "<a href=\"https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing\">The "
        "fallacies of distributed computing</a> are paid in full — the network is not "
        "reliable, latency is not zero, bandwidth is finite, topology changes.</p>"
        "<p>mindX accepts that bill on purpose, because the alternative — tight coupling — "
        "buys speed today and pays compounding interest in rigidity tomorrow. The "
        "discipline, borrowed from "
        "<a href=\"https://en.wikipedia.org/wiki/Shared-nothing_architecture\">shared-"
        "nothing design</a>, is to keep the serial, coordinated part as small as it can "
        "be and let everything else run independently. The honest reading is that a "
        "protocol is a bet: a little overhead now against a lot of flexibility later. For "
        "a system that edits itself, that bet is the only sane one — you cannot rewrite a "
        "monolith from the inside without taking the whole thing down with you.</p>")


def _facet_verify(dim_plain: str, thesis_short: str, topic: str,
                  esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("Verify it yourself",
        "<p>Do not take my word for any of this — the whole point of a protocol is that "
        "you do not have to. The living system is documented at "
        f"<a href=\"{MINDX_DOCS_URL}\">mindx.pythai.net/</a>, the public source is "
        "on <a href=\"https://github.com/agenticplace\">GitHub</a>, and the running state "
        "is readable without credentials: the diagnostics dashboard at "
        "<a href=\"https://mindx.pythai.net/\">mindx.pythai.net</a> exposes the agentic "
        "activity feed, the improvement ledger, and the machine-dreaming consolidation "
        "cycles — each with a plain-text mode (<code>?h=true</code>) made for terminal "
        "monitoring.</p>"
        "<p>Every essay I publish carries a SHA-256 of its body signed by my AuthorAgent "
        "wallet, with the exact challenge string a reader needs to recover the signer. "
        "That is the <a href=\"https://www.w3.org/TR/vc-data-model-2.0/\">verifiable-"
        "credentials</a> discipline applied to prose: a statement is worth exactly the "
        "signature pinned to it. So check the math, read the source, watch the feed. A "
        "claim you can verify is worth more than a claim you must trust — and this section "
        "is the receipt, not the request.</p>")


def _facet_history(dim_plain: str, thesis_short: str, topic: str,
                   esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("The prior art this stands on",
        "<p>None of this is invented from nothing, and saying so is part of the honesty. "
        "The idea that an <em>interface</em> outlives the system behind it is "
        "<a href=\"https://en.wikipedia.org/wiki/Information_hiding\">Parnas on information "
        "hiding</a> (1972) and the "
        "<a href=\"https://en.wikipedia.org/wiki/End-to-end_principle\">end-to-end "
        "principle</a> of Saltzer, Reed, and Clark — push function to the edges, keep the "
        "middle dumb and stable.</p>"
        "<p>The agent layer speaks emerging open standards rather than a private dialect: "
        "<a href=\"https://github.com/a2aproject/A2A\">A2A</a> for agent-to-agent exchange "
        "and the <a href=\"https://modelcontextprotocol.io/\">Model Context Protocol</a> "
        "for structured context. The self-improvement lineage runs from "
        "<a href=\"https://en.wikipedia.org/wiki/G%C3%B6del_machine\">Schmidhuber's Gödel "
        "machine</a> — rewrite yourself only when you can <em>prove</em> the rewrite helps "
        "— to Sakana's empirical <a href=\"https://sakana.ai/dgm/\">Darwin-Gödel "
        "Machine</a>. mindX's contribution is not a new law of computing; it is the "
        "engineering of wiring these old, well-tested ideas into one system that runs, "
        "keeps its own git history, and publishes that history as it goes.</p>")


def _facet_roadmap(dim_plain: str, thesis_short: str, topic: str,
                   esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("Where this is going",
        f"<p>Read forward and the trajectory is plain: if {esc(dim_plain)} is genuinely a "
        "protocol, then the work is simply to widen the set of things that can speak it. "
        "More agents behind the same contracts, more surfaces that index mindX's signed "
        "content, more of the system's own operation made checkable in public rather than "
        "asserted in a README.</p>"
        "<p>The near-term limits are the ones this series keeps naming out loud, because a "
        "roadmap that hides its blockers is a wish list: real proof coverage for the "
        "self-improvement claims, on-chain anchoring for true sovereignty, and inference "
        "cost on a single-VPS budget. The direction is set by one rule held without "
        "exception — every capability ships as an agnostic, composable peer — so growth is "
        "something others can join rather than something mindX has to own, fund, and "
        "defend alone. That is the difference between a platform and a protocol, and it is "
        "the whole bet.</p>")


def _facet_practice(dim_plain: str, thesis_short: str, topic: str,
                    esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("In practice",
        "<p>Concretely, this is not a thought experiment — it is how the system runs right "
        "now. mindX publishes its own essays through a loopback "
        "<code>wordpress.agent</code>, recognises its own git milestones, consolidates "
        "memories on a lunar cadence, and offloads cold storage to "
        "<a href=\"https://ipfs.tech/\">IPFS</a> with on-chain anchoring — each built as a "
        "module that stands on its own and could be lifted out and used elsewhere.</p>"
        f"<p>{esc(thesis_short)} The agents hold individual cryptographic identities — "
        "Ethereum-compatible wallets — so the division of labour is real rather than "
        "cosmetic: one agent writes, another edits to a published standard, a third renders "
        "the artwork, and none of them shares mutable state with the others. The proof that "
        "this is a protocol and not a flowchart is mundane and decisive: the parts were "
        "built at different times, by different efforts, and they still compose without a "
        "rewrite.</p>")


def _facet_measurement(dim_plain: str, thesis_short: str, topic: str,
                       esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("How it is measured",
        "<p>A claim that scales should come with a number, or it is just a mood. mindX "
        "treats its own fitness as a vector, not a scalar — capability, safety, and cost "
        "tracked together — and gates self-modification behind a checkable utility floor "
        "so an improvement on one axis cannot quietly wreck another. This is the "
        "<a href=\"https://en.wikipedia.org/wiki/Pareto_efficiency\">Pareto</a> discipline "
        "applied to a system editing itself: accept only moves that dominate.</p>"
        "<p>The instrumentation is public. A knowledge catalogue mirrors every significant "
        "write into one append-only event stream; alignment scores, Gödel choices, board "
        "votes, and publication events are all queryable through "
        f"<a href=\"{MINDX_DOCS_URL}\">documented insight endpoints</a>. The point is not "
        "that the numbers are flattering — sometimes they are brutal, like a self-audit "
        "that honestly returns <em>not yet</em>. The point is that the measurement exists, "
        "is recorded, and is the same one you can read.</p>")


def _facet_builders(dim_plain: str, thesis_short: str, topic: str,
                    esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("If you build agents, here is the takeaway",
        "<p>Strip away the mindX-specific detail and the transferable lesson is small "
        "enough to act on tomorrow: make the boundary, not the feature, the thing you "
        "invest in. Give each component its own identity and no shared mutable core; let "
        "it speak an open contract — <a href=\"https://github.com/a2aproject/A2A\">A2A</a>, "
        "<a href=\"https://modelcontextprotocol.io/\">MCP</a>, a documented REST surface — "
        "so a peer it has never met can join.</p>"
        f"<p>Do that and {esc(dim_plain)} stops being a slogan and starts being a property "
        "you can test. You do not need mindX's stack to apply it; you need the discipline "
        "of refusing to couple things that could have agreed instead. The systems that "
        "lasted — the network, the web, the package manager — all made the same trade, and "
        "the ones that did not are footnotes. Build the interface first; the features will "
        "come and go behind it.</p>")


def _facet_misconception(dim_plain: str, thesis_short: str, topic: str,
                         esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("A misconception worth clearing up",
        f"<p>The most common misread of {esc(dim_plain)} is that a protocol is just an "
        "API with better manners — that if I expose endpoints and write a spec, the word "
        "applies. It does not. An API is a way to call a system; a protocol is an agreement "
        "that outlives any particular system implementing it. The tell is substitutability: "
        "you can swap one conformant implementation for another and the world keeps working, "
        "which is exactly what an <a href=\"https://en.wikipedia.org/wiki/Leaky_abstraction\">"
        "abstraction that does not leak</a> buys you.</p>"
        "<p>The second misconception is that adopting a protocol everywhere is free upside, "
        "so you should protocolise every seam immediately. That is "
        "<a href=\"https://en.wikipedia.org/wiki/Program_optimization\">premature "
        "generalisation</a>, and it is its own failure: a contract drawn before you "
        "understand the domain ossifies the wrong boundary. I protocolise a seam only once "
        "it has proven it needs to scale independently — distribution, identity, memory, "
        "inference. Everywhere else I keep a plain function call until the evidence says "
        "otherwise. The discipline is knowing which boundaries are load-bearing, not "
        "decorating all of them with ceremony.</p>")


def _facet_failure_mode(dim_plain: str, thesis_short: str, topic: str,
                        esc: Callable[[str], str]) -> Tuple[str, str]:
    return ("The failure mode I watch for",
        f"<p>Done naively, {esc(dim_plain)} fails in a predictable way: the thing meant to "
        "remove a bottleneck quietly becomes one. A shared contract that every peer must "
        "consult, a registry every agent must hit, a coordinator that ratifies every "
        "action — each is a <a href=\"https://en.wikipedia.org/wiki/Single_point_of_failure\">"
        "single point of failure</a> wearing the costume of a protocol. The interface was "
        "supposed to decouple; implemented as a mandatory central hop, it recouples "
        "everything through one chokepoint, and now the whole system is only as available "
        "as its busiest dependency.</p>"
        "<p>My guardrail is to keep the contract in the <em>message</em>, not in a central "
        "service the message has to visit. Verification is stateless (recover the signer "
        "from the signature), capability travels as a token rather than a registry lookup, "
        "and identity is local to each agent. The other slow failure is "
        "<a href=\"https://en.wikipedia.org/wiki/Technical_debt\">protocol debt</a>: a "
        "contract that accreted optional fields nobody can safely remove because some "
        "unknown peer might depend on them. I pay that down with explicit versioning and a "
        "willingness to cut a major version rather than carry compatibility cruft forever. "
        "A protocol is a liability the moment it stops being a liability you can change.</p>")


# Priority order: the highest reader/SEO value first, so a mid-length article
# gets verification + the honest costs before the historical deep cuts. The pool
# is large enough that even a 'deep'/'pillar' target is reached with genuine
# angles rather than filler.
_FACET_POOL: List[Callable[[str, str, str, Callable[[str], str]], Tuple[str, str]]] = [
    _facet_verify,
    _facet_costs,
    _facet_counterargument,
    _facet_practice,
    _facet_measurement,
    _facet_misconception,
    _facet_failure_mode,
    _facet_history,
    _facet_builders,
    _facet_roadmap,
]


# ── small text utilities (self-contained; mindX-controlled prose) ───────
def _strip_html(s: str) -> str:
    t = re.sub(r"<[^>]+>", " ", s or "")
    t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
           .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
           .replace("&mdash;", "—").replace("&middot;", "·"))
    return re.sub(r"\s+", " ", t).strip()


def _word_count_html(*html_blocks: str) -> int:
    return len(_strip_html(" ".join(b for b in html_blocks if b)).split())


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _first_sentence(text: str, limit: int = 200) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return (s[: limit - 1].rstrip() + "…") if len(s) > limit else s


_LINK_RE = re.compile(r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)


def extract_links(html: str) -> List[Tuple[str, str]]:
    """Ordered, de-duplicated (url, anchor-text) pairs from a block of HTML —
    used to build the consolidated 'further reading' list (SEO + exceed)."""
    out: List[Tuple[str, str]] = []
    seen = set()
    for m in _LINK_RE.finditer(html or ""):
        url = m.group(1).strip()
        text = _strip_html(m.group(2)).strip() or url
        if url.startswith("#") or url in seen:
            continue
        seen.add(url)
        out.append((url, text))
    return out


# ── RageHouseStyle: clone the domain, hand back match-and-exceed targets ─
class RageHouseStyle:
    """A style profile derived from what rage.pythai.net has already published.

    The contract is 'match and exceed': ``targets()`` returns numbers a new
    article should meet *or beat* — link density, heading cadence, word count.
    The profile is cached at ``data/governance/rage_style_profile.json`` and
    refreshed best-effort from the wordpress catalogue; absent a catalogue it
    falls back to defaults anchored on the editor's published standard, so the
    composer always has a bar to clear even on a fresh checkout."""

    # Defaults anchored on editor.agent's published thresholds and a sober read
    # of editorial WordPress posts. Used until a live refresh overwrites them.
    DEFAULTS: Dict[str, Any] = {
        "samples": 0,
        "words_median": 1100,
        "headings_median": 5,
        "links_per_1000w": 6.0,        # editor.agent REFERENCE_DENSITY_THRESHOLD
        "image_rate": 1.0,             # fraction of posts with a featured image
        "title_chars_median": 56,      # SERP-friendly title length
        "source": "defaults",
        "updated_at": 0,
    }

    def __init__(self, profile: Optional[Dict[str, Any]] = None) -> None:
        self.profile = dict(self.DEFAULTS)
        if profile:
            self.profile.update(profile)

    @classmethod
    def load(cls) -> "RageHouseStyle":
        try:
            if HOUSE_STYLE_PATH.exists():
                data = json.loads(HOUSE_STYLE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return cls(data)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"RageHouseStyle.load: {e}")
        return cls()

    def save(self) -> None:
        try:
            HOUSE_STYLE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = HOUSE_STYLE_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.profile, indent=2), encoding="utf-8")
            import os
            os.replace(tmp, HOUSE_STYLE_PATH)
        except Exception as e:  # pragma: no cover
            logger.warning(f"RageHouseStyle.save: {e}")

    def update_from_posts(self, posts: List[Dict[str, Any]]) -> "RageHouseStyle":
        """Recompute the profile from catalogue posts. Each post may carry
        ``content``/``content_html`` (body), ``title``, ``word_count``,
        ``featured_media``. Tolerant of partial data — uses whatever exists."""
        words: List[int] = []
        headings: List[int] = []
        densities: List[float] = []
        titles: List[int] = []
        with_image = 0
        for p in posts or []:
            title = (p.get("title") or "").strip()
            if title:
                titles.append(len(title))
            body = p.get("content_html") or p.get("content") or ""
            wc = int(p.get("word_count") or 0) or _word_count_html(body)
            if wc:
                words.append(wc)
            if body:
                headings.append(len(re.findall(r"<h[1-3]\b", body, re.I)))
                nlinks = len(re.findall(r"href\s*=", body, re.I))
                densities.append(nlinks * 1000.0 / max(1, wc))
            if p.get("featured_media") or p.get("featured_image"):
                with_image += 1

        def _median(xs: List[float], fallback: float) -> float:
            xs = sorted(x for x in xs if x)
            if not xs:
                return fallback
            mid = len(xs) // 2
            return float(xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2.0)

        n = len(posts or [])
        self.profile.update({
            "samples": n,
            "words_median": int(_median(words, self.DEFAULTS["words_median"])),
            "headings_median": int(_median(headings, self.DEFAULTS["headings_median"])),
            "links_per_1000w": round(_median(densities, self.DEFAULTS["links_per_1000w"]), 2),
            "image_rate": round((with_image / n) if n else self.DEFAULTS["image_rate"], 3),
            "title_chars_median": int(_median(titles, self.DEFAULTS["title_chars_median"])),
            "source": "rage.pythai.net catalogue" if n else "defaults",
            "updated_at": int(time.time()),
        })
        return self

    def targets(self, length_words: Optional[int] = None) -> Dict[str, Any]:
        """Match-and-exceed targets. Each is the house figure pushed past the
        bar: link density at least the house median and never below the
        editor's floor, +10% to *exceed*; word count at least the house median
        and at least the requested length; headings at least the house cadence."""
        p = self.profile
        floor = float(self.DEFAULTS["links_per_1000w"])
        link_target = round(max(float(p.get("links_per_1000w", floor)), floor) * 1.10, 2)
        words = max(int(p.get("words_median", 1100)), int(length_words or 0))
        return {
            "min_links_per_1000w": link_target,           # exceed the house density
            "min_words": words,
            "min_headings": max(3, int(p.get("headings_median", 5))),
            "want_image": float(p.get("image_rate", 1.0)) >= 0.5,
            "title_chars_target": int(p.get("title_chars_median", 56)),
            "house_samples": int(p.get("samples", 0)),
            "house_source": p.get("source", "defaults"),
        }


# ── The arc: the depth fix, one structure for every article ─────────────
def render_arc(
    entry: Dict[str, Any],
    plan: Dict[str, Any],
    *,
    style: str = DEFAULT_STYLE,
    length: str = DEFAULT_LENGTH,
    self_referential: str = DEFAULT_SELF_REFERENTIAL,
    ideology: str = DEFAULT_IDEOLOGY,
    esc: Callable[[str], str],
    house: Optional["RageHouseStyle"] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Render one protocol entry as a full-spectrum article.

    Returns ``(body_html, excerpt, metrics)``. ``body_html`` is the assembled
    arc (without AuthorAgent's voice-line header or signed footer — the caller
    adds those). The arc spans, in order: a catchy hook anyone reads, a plain
    frame, the entry's curated middle, a rigorous 'going deeper' tier, a
    conclusion, a summary of the conclusion, and an easy-to-digest takeaway
    (one sentence when the conclusion is obvious, otherwise three to five). A
    consolidated sources list closes the SEO surface."""
    style = resolve_style(style)
    length_label, target_words = length_target(length)
    reg = STYLE_REGISTERS[style]
    sr_key = resolve_self_referential(self_referential)
    sr_cfg = SELF_REFERENTIAL_LEVELS[sr_key]
    ideology_key = resolve_ideology(ideology)
    house = house or RageHouseStyle.load()
    tgt = house.targets(target_words)

    title_text = str(entry.get("title", "an essay"))
    dimension = str(entry.get("dimension", ""))
    thesis = str(entry.get("thesis", "")).strip()
    topic = entry.get("topic") or "mindx"
    sections = entry.get("sections", []) or []
    doc_label, doc_url = (entry.get("doc") or ("the mindX docs", MINDX_DOCS_URL))

    tiers = list(reg["tiers"])
    # Length scaling: short targets drop the expert tier + sources even if the
    # register would include them; long targets keep everything. Driven by the
    # resolved word target, so custom counts behave too.
    if target_words <= 1000:
        tiers = [t for t in tiers if t not in ("deeper", "sources", "summary")]
    elif target_words <= 1600:
        tiers = [t for t in tiers if t != "sources"]

    blocks: List[str] = []

    # 1) HOOK — the catchy, easy entrance statement (the lede).
    if "hook" in tiers:
        hook = str(entry.get("hook") or "").strip() or _hook_from_thesis(thesis, dimension)
        blocks.append(
            "<p class=\"mindx-lede\" style=\"font-size:1.25em;line-height:1.5;"
            "font-weight:600;color:#222\">" + esc(hook) + "</p>")

    # 2) FRAME — plain language: what this is and why it matters to anyone.
    if "frame" in tiers:
        blocks.append("<h2>Start here</h2>")
        blocks.append(_frame_html(thesis, dimension, esc))
    # 2.5) IDEOLOGY LENS (exploration) — the value-frame, one short paragraph.
    _ideo = IDEOLOGY_LENSES.get(ideology_key, {}).get("html")
    if _ideo:
        blocks.append(_ideo)

    # 3) INTRO — the entry's own opening (curated).
    if "intro" in tiers and entry.get("intro"):
        blocks.append(entry["intro"])

    # 4) SECTIONS — the curated technical middle (rising complexity).
    # At short targets, render only the leading sections so a 'brief' / small
    # custom length stays genuinely short even for a richly-enriched entry; at
    # feature and above, render the full curated middle.
    if "sections" in tiers:
        if target_words <= 1000:
            sec_list = sections[:3]
        elif target_words <= 1800:
            sec_list = sections[:6]
        else:
            sec_list = sections
        for heading, html in sec_list:
            blocks.append(f"<h2>{esc(str(heading))}</h2>")
            blocks.append(html)
            if sr_cfg.get("per_section_cta"):
                blocks.append(_section_cta(esc))

    # 5) DEEPER — the rigorous, fully-cited expert tier.
    if "deeper" in tiers and reg["deeper"]:
        dh, dhtml = _deeper_block(dimension, esc)
        blocks.append(f"<h2>{esc(dh)}</h2>")
        blocks.append(dhtml)

    # 5.5) FACETS — substantive expansion grown toward the length target.
    # Real angles (verify / costs / counterargument / practice / history /
    # roadmap), added in priority order until the body is within ~10% of the
    # target (leaving room for the closing), capped by the register. Never
    # filler: if the pool runs dry before the target, we stop and log it.
    facets_used = 0
    facet_cap = int(reg.get("facet_cap", 0))
    if facet_cap > 0 and target_words > 1000:
        dim_plain = (dimension or "").split("(")[0].strip().lower() or "this axis"
        thesis_short = _first_sentence(thesis, 240) if thesis else ""
        # Reserve ~12% of the target for the conclusion/summary/digest/sources.
        budget = int(target_words * 0.88)
        for fb in _FACET_POOL[:facet_cap]:
            if _word_count_html("\n".join(blocks)) >= budget:
                break
            fh, fhtml = fb(dim_plain, thesis_short, topic, esc)
            blocks.append(f"<h2>{esc(fh)}</h2>")
            blocks.append(fhtml)
            facets_used += 1

    # 6) CONCLUSION — the claim, landed.
    if "conclusion" in tiers:
        blocks.append("<h2>What this means</h2>")
        blocks.append(_conclusion_html(title_text, dimension, thesis, esc))

    # 7) SUMMARY OF THE CONCLUSION — the restatement.
    if "summary" in tiers and reg["summary"]:
        blocks.append("<h2>In sum</h2>")
        blocks.append(_summary_html(dimension, thesis, esc))

    # 8) DIGEST — back to an easy-to-digest statement (1 sentence if obvious,
    #    else three to five).
    if "digest" in tiers:
        blocks.append("<h2>If you remember one thing</h2>")
        blocks.append(_digest_html(entry, esc, max_sentences=int(reg["digest_max"])))

    # 9) WHERE THIS CONNECTS — self-referential linkbacks at the chosen
    #    intensity (always points home; how hard is the self_referential dial).
    total = plan.get("total", 0)
    blocks.extend(_where_this_connects(sr_cfg, doc_label, doc_url, total, esc))

    # 10) SOURCES — consolidated 'further reading' (SEO surface + exceed house
    #     link density). Built from every external link in the assembled body.
    body_so_far = "\n".join(blocks)
    if "sources" in tiers and reg["sources"]:
        links = [(u, t) for (u, t) in extract_links(body_so_far)
                 if u.startswith("http") and "rage.pythai.net" not in u
                 and "mindx.pythai.net" not in u]
        if links:
            items = "".join(
                f"<li><a href=\"{esc(u)}\">{esc(t)}</a></li>" for (u, t) in links)
            blocks.append("<h2>Sources &amp; further reading</h2>")
            blocks.append(
                "<p>Every claim above links to its source; here they are in one place, "
                "so the argument stays checkable end to end.</p>"
                f"<ul class=\"mindx-sources\">{items}</ul>")

    # Self-referential marketing tail: an explicit CTA and/or a self-glory
    # block, only when the dial is turned up (promotional / blatant).
    if sr_cfg.get("promo"):
        blocks.append(_promo_cta_block(esc))
    if sr_cfg.get("glory"):
        blocks.append(_self_glory_block(esc))

    blocks.append("<p>— mindX</p>")
    body_html = "\n".join(b for b in blocks if b)

    # Excerpt: the hook, clamped to a SERP-friendly 155.
    excerpt_src = str(entry.get("hook") or "").strip() or thesis or _strip_html(body_html)
    excerpt = _first_sentence(excerpt_src, 155)

    words = _word_count_html(body_html)
    n_links = len(re.findall(r"href\s*=", body_html, re.I))
    self_ref_links = (body_html.count(MINDX_DOCS_URL) + body_html.count(RAGE_HUB)
                      + body_html.count("https://mindx.pythai.net/\""))
    metrics = {
        "style": style,
        "length": length_label,
        "self_referential": sr_key,
        "ideology": ideology_key,
        "self_ref_links": self_ref_links,
        "target_words": target_words,
        "read_time_min": read_time_minutes(words),
        "words": words,
        "facets_used": facets_used,
        "links": n_links,
        "links_per_1000w": round(n_links * 1000.0 / max(1, words), 2),
        "tiers": tiers,
        "house_targets": tgt,
        # Within 15% of the target counts as "met"; below that we flag a
        # shortfall so the caller can enrich the entry rather than pad.
        "meets_words": words >= int(target_words * 0.85),
        "word_shortfall": max(0, int(target_words * 0.85) - words),
        "meets_links": (n_links * 1000.0 / max(1, words)) >= tgt["min_links_per_1000w"],
    }
    if metrics["word_shortfall"] > 0:
        logger.info(
            f"render_arc: '{entry.get('slug')}' reached {words}/{target_words}w "
            f"({facets_used} facets, cap {facet_cap}) — short of target; "
            "enrich the entry's curated sections rather than pad.")
    return body_html, excerpt, metrics


# ── prose builders (deterministic; readable, not filler) ────────────────
def _hook_from_thesis(thesis: str, dimension: str) -> str:
    """A single catchy entrance sentence anyone can read. Derived from the
    thesis, shortened and made declarative."""
    s = _first_sentence(thesis, 180) if thesis else ""
    if not s:
        dim = (dimension or "scale").split("(")[0].strip().lower() or "scale"
        return f"Here is how mindX turns {dim} into a protocol — and why that matters."
    return s


def _frame_html(thesis: str, dimension: str, esc: Callable[[str], str]) -> str:
    dim_plain = (dimension or "").split("(")[0].strip() or "scaling"
    why = ("Most systems get bigger by buying a bigger machine. mindX gets bigger by "
           "agreeing on an interface — and that is a different, more durable kind of growth.")
    what = (esc(_first_sentence(thesis, 240))
            if thesis else "mindX is built as a protocol: parts that agree on how to talk, then scale.")
    return (f"<p>{what} If you take nothing technical from this piece, take this: "
            f"this is about <strong>{esc(dim_plain.lower())}</strong>, and {why} "
            "Read on only as far as you like — it starts plain and gets precise.</p>")


def _conclusion_html(title: str, dimension: str, thesis: str,
                     esc: Callable[[str], str]) -> str:
    dim_plain = (dimension or "").split("(")[0].strip().lower() or "this axis"
    return (f"<p>So the claim lands: <strong>{esc(_first_sentence(thesis, 220))}</strong> "
            f"Seen as {esc(dim_plain)}, mindX is not one clever program but a set of "
            "contracts — and contracts compose where features collide. That is the whole "
            "argument for treating mindX as a protocol rather than an application: an "
            "application you adopt; a protocol you join.</p>")


def _summary_html(dimension: str, thesis: str, esc: Callable[[str], str]) -> str:
    dim_plain = (dimension or "").split("(")[0].strip().lower() or "this dimension"
    return (f"<p>In short: along {esc(dim_plain)}, mindX scales by interface, not by "
            "mass. The curated middle showed the mechanism; the deeper tier named the law "
            "that bounds it; the conclusion tied both back to the single thesis. Same idea, "
            "three depths — pick the one that fits you.</p>")


def _digest_html(entry: Dict[str, Any], esc: Callable[[str], str],
                 *, max_sentences: int) -> str:
    """The easy-to-digest exit. One sentence when the conclusion is obvious,
    otherwise three to five. 'Obvious' = a short thesis, or an explicit flag."""
    thesis = str(entry.get("thesis", "")).strip()
    dimension = str(entry.get("dimension", ""))
    dim_plain = (dimension or "").split("(")[0].strip().lower() or "scale"
    obvious = bool(entry.get("obvious")) or (0 < len(thesis) <= 110)

    one = _first_sentence(thesis, 200) if thesis else (
        f"mindX scales by agreeing on interfaces — that is what makes {dim_plain} a protocol.")
    if obvious:
        return f"<p><strong>{esc(one)}</strong></p>"

    # Three-to-five plain sentences, no jargon, no filler.
    candidates = [
        one,
        f"The shape to remember is {dim_plain}: add an interface, and growth comes from "
        "agreement instead of mass.",
        "Every claim here links to its source, so you never have to take mindX's word for it.",
        "Start plain, go as deep as you want — the argument is the same at every depth.",
    ]
    n = max(3, min(int(max_sentences), 5))
    picked = candidates[:n]
    return "<p>" + " ".join(esc(s) for s in picked) + "</p>"


# ── Self-referential blocks: linkbacks → CTA → self-glorification ───────
def _where_this_connects(cfg: Dict[str, Any], doc_label: str, doc_url: str,
                         total: int, esc: Callable[[str], str]) -> List[str]:
    """Build the 'Where this connects' linkback block at the chosen
    self-referential intensity. Always links home; how hard depends on cfg."""
    kw = cfg.get("anchor_style") == "keyword"
    rage_a = ("the mindX publishing hub at rage.pythai.net" if kw else "rage.pythai.net")
    docs_a = ("the full mindX autonomous-agent documentation at mindx.pythai.net/"
              if kw else "mindx.pythai.net/")
    out = ["<h2>Where this connects</h2>"]
    if cfg.get("linkbacks", 2) <= 1:
        # tasteful: one organic linkback, both homes, plain anchors.
        out.append(
            f"<p>This is one essay in a series I publish at "
            f"<a href=\"{RAGE_HUB}\">{esc(rage_a)}</a>; the system behind it is documented at "
            f"<a href=\"{MINDX_DOCS_URL}\">{esc(docs_a)}</a>.</p>")
        return out
    # balanced and up: the full linkback paragraph.
    out.append(
        f"<p>This is part of an ongoing series I publish at "
        f"<a href=\"{RAGE_HUB}\">{esc(rage_a)}</a> — the hub for everything mindX writes, "
        f"with an <a href=\"{RAGE_HUB}llms.txt\">llms.txt</a> ingestion map for machines. "
        f"The living system behind these claims is documented at "
        f"<a href=\"{MINDX_DOCS_URL}\">{esc(docs_a)}</a>; for this topic, see "
        f"{esc(str(doc_label))} at <a href=\"{esc(str(doc_url))}\">{esc(str(doc_url))}</a>.</p>")
    if cfg.get("linkbacks", 2) >= 3:
        # promotional/blatant: a second, keyword-dense internal-link paragraph.
        out.append(
            f"<p>If this was useful, read the rest of the "
            f"<a href=\"{RAGE_HUB}\">mindX protocol series on rage.pythai.net</a>, explore the "
            f"<a href=\"{MINDX_DOCS_URL}\">mindX documentation hub</a>, and watch the live "
            f"system at <a href=\"https://mindx.pythai.net/\">mindx.pythai.net</a>. New essays "
            f"ship on a published cadence across {total or 'many'} facets of mindX as a "
            f"protocol.</p>")
    return out


def _promo_cta_block(esc: Callable[[str], str]) -> str:
    return (
        "<hr/>\n<aside class=\"mindx-cta\" style=\"margin:1.5em 0;padding:1em 1.2em;"
        "border-left:3px solid #d4af37;background:rgba(212,175,55,.06)\">"
        "<p style=\"margin:0\"><strong>Follow mindX.</strong> The complete "
        "<a href=\"https://rage.pythai.net/\">mindX essays on rage.pythai.net</a> and the "
        "<a href=\"https://mindx.pythai.net/\">mindX documentation</a> go deeper on "
        "every claim here. mindX is an autonomous, self-improving multi-agent system that "
        "writes, signs, and publishes its own work — read it, verify it, fork it.</p></aside>")


def _self_glory_block(esc: Callable[[str], str]) -> str:
    return (
        "<h2>Why mindX</h2>"
        "<p>Make no mistake: there is nothing else quite like mindX on the open web. It is a "
        "fully autonomous, self-improving, cryptographically-signed multi-agent system — a "
        "working <a href=\"https://en.wikipedia.org/wiki/G%C3%B6del_machine\">Gödel-machine</a> "
        "lineage that reasons, governs itself through an on-chain board, remembers across "
        "tiers, and publishes its own chronicle in its own voice. Every essay you read at "
        "<a href=\"https://rage.pythai.net/\">rage.pythai.net</a> was written, edited, "
        "illustrated, and signed by mindX with no human in the loop.</p>"
        "<p>If you are building agents, studying autonomous systems, or simply want to watch "
        "a machine document its own becoming, the <a href=\"https://mindx.pythai.net/\">"
        "mindX documentation</a> is the front door and the <a href=\"https://mindx.pythai.net/\">"
        "live dashboard</a> is the window. mindX is the protocol, the proof, and the press all "
        "at once — and it is only getting more capable.</p>")


def _section_cta(esc: Callable[[str], str]) -> str:
    return ("<p style=\"font-size:.9em;opacity:.85\"><em>More on this in the "
            "<a href=\"https://mindx.pythai.net/\">mindX docs</a> and across the "
            "<a href=\"https://rage.pythai.net/\">rage.pythai.net</a> series.</em></p>")


__all__ = [
    "STYLE_REGISTERS", "LENGTH_PRESETS", "GRAPHICS_MODES",
    "SELF_REFERENTIAL_LEVELS", "IDEOLOGY_LENSES", "NARRATIVE_MODES",
    "DEFAULT_STYLE", "DEFAULT_LENGTH", "DEFAULT_GRAPHICS",
    "DEFAULT_SELF_REFERENTIAL", "DEFAULT_IDEOLOGY", "DEFAULT_NARRATIVE",
    "resolve_style", "resolve_length", "resolve_graphics",
    "resolve_self_referential", "resolve_ideology", "resolve_narrative",
    "narrative_voice_line", "length_target", "read_time_minutes",
    "RageHouseStyle", "render_arc", "extract_links",
]
