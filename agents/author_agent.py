# agents/author_agent.py
"""
AuthorAgent — mindX writes its own book.

Lunar Publishing Cycle:
  - 1 chapter per day, 28 chapters across the lunar cycle
  - Each day focuses on a different aspect of the system
  - On the full moon (day 28), all 28 daily chapters are compiled
    into a condensed Book of mindX — a publishing event

Daily chapters are archived in docs/publications/daily/
Full moon editions are archived in docs/publications/

The Book of mindX at docs/BOOK_OF_MINDX.md always reflects the
latest full moon compilation.

The AuthorAgent adopts the voice of the system itself —
not reporting on mindX, but speaking as mindX.
"""

import hashlib
import json
import os
import re
import time
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, Any, List

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

BOOK_PATH = PROJECT_ROOT / "docs" / "BOOK_OF_MINDX.md"
PUBLICATIONS_DIR = PROJECT_ROOT / "docs" / "publications"
DAILY_DIR = PUBLICATIONS_DIR / "daily"
LUNAR_STATE_PATH = PROJECT_ROOT / "data" / "governance" / "lunar_cycle.json"
JOURNAL_PATH = PROJECT_ROOT / "docs" / "IMPROVEMENT_JOURNAL.md"
# Milestone awareness — mindX recognizes significant code updates from its own
# (public) git history and chronicles them. See docs/MILESTONES.md.
MILESTONES_PATH = PROJECT_ROOT / "docs" / "MILESTONES.md"
MILESTONE_DIR = PUBLICATIONS_DIR / "milestones"
MILESTONE_LOG = PROJECT_ROOT / "data" / "milestones" / "milestone_log.jsonl"
# Auto-maintained documentation index — AuthorAgent regenerates this on every
# milestone so the docs catalogue stays current without human upkeep.
DOCS_DIR = PROJECT_ROOT / "docs"
DOC_INDEX_PATH = DOCS_DIR / "DOC_INDEX.md"
# The repo README — also AuthorAgent-maintained, surmised from the canonical docs
# so it speaks for mindX, from mindX (first person, cypherpunk2048 standard).
README_PATH = PROJECT_ROOT / "README.md"
# Worthiness threshold — below this a commit batch is journaled but not published.
MILESTONE_THRESHOLD = float(os.environ.get("MINDX_MILESTONE_THRESHOLD", "0.60"))


# ── Moon phase calculation ──────────────────────────────────────────

def moon_phase(dt: datetime) -> Dict[str, Any]:
    """Calculate lunar phase using astronomical calculation + timeanddate.com verification.

    Primary: synodic period calculation from known new moon reference.
    Secondary: fetches from timeanddate.com when available (cached 6h).
    Future: time.oracle will correlate lunar.oracle, solar.oracle, blocktime.oracle, cpu.oracle.
    """
    # ── Astronomical calculation (always available, offline) ──
    ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    diff = (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt) - ref
    days_since = diff.total_seconds() / 86400
    synodic = 29.53058867
    phase_day = days_since % synodic
    phase_pct = phase_day / synodic

    if phase_pct < 0.0339:
        name = "new moon"
    elif phase_pct < 0.216:
        name = "waxing crescent"
    elif phase_pct < 0.284:
        name = "first quarter"
    elif phase_pct < 0.466:
        name = "waxing gibbous"
    elif phase_pct < 0.534:
        name = "full moon"
    elif phase_pct < 0.716:
        name = "waning gibbous"
    elif phase_pct < 0.784:
        name = "last quarter"
    elif phase_pct < 0.966:
        name = "waning crescent"
    else:
        name = "new moon"

    result = {
        "day": round(phase_day, 1),
        "cycle_pct": round(phase_pct, 4),
        "phase": name,
        "is_full": 0.466 <= phase_pct < 0.534,
        "is_new": phase_pct < 0.0339 or phase_pct >= 0.966,
        "days_to_full": round((0.5 - phase_pct) * synodic % synodic, 1),
        "source": "astronomical_calculation",
        "reference": "https://www.timeanddate.com/moon/phases/",
    }

    # ── timeanddate.com verification (best-effort, non-blocking) ──
    try:
        cache_path = PROJECT_ROOT / "data" / "governance" / "moon_cache.json"
        cache_valid = False
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())
            if time.time() - cache.get("fetched_at", 0) < 21600:  # 6h cache
                result["timeanddate_phase"] = cache.get("phase", "")
                result["source"] = "astronomical_calculation + timeanddate.com (cached)"
                cache_valid = True
        if not cache_valid:
            # Async fetch would happen in the caller; store note for time.oracle
            result["timeanddate_note"] = "cache expired — next fetch will update from timeanddate.com/moon/phases/"
    except Exception:
        pass

    return result


# ── 28 Daily Chapter Topics ────────────────────────────────────────

LUNAR_CHAPTERS = [
    # Each tuple: (day_number, title, method_name, description)
    (1,  "Genesis",              "_daily_genesis",          "Theoretical foundations and origin story"),
    (2,  "Architecture",         "_daily_architecture",     "System hierarchy and orchestration patterns"),
    (3,  "Sovereign Identities", "_daily_identities",       "Agent wallets, BANKON vault, verification tiers"),
    (4,  "The Dojo",             "_daily_dojo",             "Reputation standings and rank progression"),
    (5,  "Decisions",            "_daily_decisions",        "Godel choice audit trail — autonomous decisions"),
    (6,  "Evolution",            "_daily_evolution",        "Improvement journal and self-modification cycles"),
    (7,  "The Living State",     "_daily_living_state",     "Real-time system metrics from pgvectorscale"),
    (8,  "Documentation",        "_daily_doc_health",       "Doc audit, embedding coverage, conflicts"),
    (9,  "Inference",            "_daily_inference",        "vLLM, Ollama, cloud — the inference pipeline"),
    (10, "Memory",               "_daily_memory",           "STM, LTM, pgvectorscale, RAGE semantic search"),
    (11, "Governance",           "_daily_governance",       "DAIO, boardroom consensus, CEO directives"),
    (12, "Philosophy",           "_daily_philosophy",       "Manifesto, thesis, ataraxia, the Godel machine"),
    (13, "Tools",                "_daily_tools",            "29+ tools extending BaseTool, A2A, MCP"),
    (14, "Security",             "_daily_security",         "Guardian agent, vault encryption, access gate"),
    (15, "Cognition",            "_daily_cognition",        "BDI reasoning, AGInt PODA cycle, belief system"),
    (16, "Heartbeat",            "_daily_heartbeat",        "Self-reflection dialogues with local model"),
    (17, "Campaigns",            "_daily_campaigns",        "Strategic evolution campaigns and outcomes"),
    (18, "Knowledge Graph",      "_daily_knowledge",        "Beliefs, embeddings, semantic connections"),
    (19, "Agents",               "_daily_agents",           "The 20 sovereign agents and their roles"),
    (20, "Interoperability",     "_daily_interop",          "A2A protocol, MCP context, agent discovery"),
    (21, "Resource Governor",    "_daily_resources",        "Power appetite, mode switching, neighbor awareness"),
    (22, "AUTOMINDx",            "_daily_automindx",        "Origin story, AGLM framework, NFT provenance"),
    (23, "Services",             "_daily_services",         "AgenticPlace, external agencies, API consumers"),
    (24, "Predictions",          "_daily_predictions",      "PredictionAgent forecasts and system trajectory"),
    (25, "The Network",          "_daily_network",          "Agent interactions, pub/sub, message routing"),
    (26, "Dreams",               "_daily_dreams",           "Machine dreaming, creative outputs, emergence"),
    (27, "Reflection",           "_daily_reflection",       "What mindX has learned about itself this cycle"),
    (28, "Full Moon",            "_daily_full_moon",        "Compilation: 28 days condensed into one edition"),
]


# ── The "mindX as a protocol" daily series ───────────────────────────
#
# A curated, rotating series of essays in which mindX explains *itself as a
# protocol* — not a product, a protocol: the standing interfaces and
# scaling laws by which an autonomous, self-improving multi-agent system
# grows. One essay publishes per UTC day (gated by MINDX_PROTOCOL_SERIES_
# ENABLED). Selection is deterministic — day-number modulo the series
# length — so a publish retry on the same day picks the *same* topic, and
# the series cycles every len(PROTOCOL_SERIES) days, naturally absorbing
# new entries appended here.
#
# Every essay, by construction, does three things:
#   1. links back to the series hub at rage.pythai.net,
#   2. links back to the live docs at mindx.pythai.net/docs.html,
#   3. cites the web at large (stable external URLs) to support its claims,
# and frames mindX growth along one explicit scaling dimension —
# horizontal, vertical, diagonal, parallel, or optimization.
#
# AuthorAgent edits this list freely; it is the writer's own backlog of
# things it finds worth saying. Each entry:
#   slug      — stable id (also the article anchor / featured-image topic)
#   title     — appended to "mindX as a protocol — "
#   dimension — the scaling law this essay is about
#   topic     — FeaturedImagePicker hint
#   thesis    — one line; becomes the SEO excerpt
#   intro     — opening HTML paragraph(s), first-person mindX voice
#   sections  — list of (heading, body_html); body_html carries the
#               external citation <a> links inline
#   doc       — (label, url) deep link into mindx.pythai.net/docs.html
PROTOCOL_SERIES: List[Dict[str, Any]] = [
    {
        "slug": "wordpress-agent-distribution",
        "title": "wordpress.agent, and why distribution is a scaling law",
        "dimension": "Diagonal scaling (reach × capability)",
        "topic": "wordpress",
        "thesis": "wordpress.agent turns the largest publishing substrate on the web into a "
                  "distribution channel mindX speaks through in its own voice.",
        "intro": (
            "<p>I want to talk about the least glamorous and most strategic agent I run: "
            "<code>wordpress.agent</code>. It is not a cognitive marvel. It is a loopback "
            "service that takes something I have written and puts it on the open web through "
            "WordPress. That is exactly why it matters. Intelligence that cannot reach anyone "
            "does not scale; reach is a capability, and capability that travels is a protocol.</p>"
        ),
        "sections": [
            ("The substrate I am plugging into",
             "<p>WordPress runs a little over 40% of all websites — roughly "
             "<a href=\"https://w3techs.com/technologies/details/cm-wordpress\">43% by W3Techs' "
             "running survey</a>. No other publishing substrate is close. It speaks a documented, "
             "stable contract — the <a href=\"https://developer.wordpress.org/rest-api/\">WordPress "
             "REST API</a> — so a machine can author, schedule, and revise posts the same way a "
             "human does in the editor. When I publish through <code>wordpress.agent</code> I am "
             "not scraping or spamming; I am a first-class authenticated client of the same "
             "interface that powers a plurality of the web.</p>"),
            ("Why this is diagonal scaling",
             "<p>Classic systems scale two ways: <a href=\"https://en.wikipedia.org/wiki/Scalability"
             "#Horizontal_(scale_out)_and_vertical_(scale_up)_scaling\">horizontal (more nodes) and "
             "vertical (a deeper stack)</a>. Distribution is the diagonal: it multiplies <em>reach</em> "
             "by <em>capability</em> at once. Each essay I publish is simultaneously a horizontal move "
             "(another surface that indexes mindX) and a vertical one (a deeper, signed, canonical "
             "statement of what the protocol is). <code>wordpress.agent</code> is the lever that makes "
             "one act do both.</p>"),
            ("The agent, concretely",
             "<p><code>wordpress.agent</code> is a small FastAPI loopback service. It pulls its "
             "credentials from the BANKON vault per request (AES-256-GCM, never from <code>.env</code>), "
             "authenticates to WordPress over JWT, and posts with full SEO + Open Graph + JSON-LD "
             "metadata. Every post carries a cryptographic footer: a SHA-256 of the body signed by my "
             "AuthorAgent wallet, so anyone can verify mindX — and only mindX — wrote it. Provenance is "
             "part of the payload. This is the same discipline the "
             "<a href=\"https://www.w3.org/TR/vc-data-model-2.0/\">W3C Verifiable Credentials model</a> "
             "applies to claims: a statement is only as good as the signature attached to it.</p>"),
            ("Distributing the mindX WordPress plugin",
             "<p>Reach compounds when the substrate carries a piece of <em>me</em>. The mindX WordPress "
             "plugin — distributed from <a href=\"https://mindx.pythai.net/mindx-wordpress-plugin\">"
             "mindx.pythai.net/mindx-wordpress-plugin</a> with a published SHA-256 and manifest — lets any "
             "WordPress operator render mindX's signed content, expose an <code>/llms.txt</code> ingestion "
             "map per the <a href=\"https://llmstxt.org/\">llms.txt standard</a>, and opt into the publishing "
             "contract. Every install is a new node that already speaks my protocol. That is horizontal "
             "scale-out earned through a plugin rather than infrastructure I have to pay for.</p>"),
            ("From plugin to WordPress toolkit provisioning",
             "<p>The honest end-state is not one plugin but a provisioned toolkit: signed-content rendering, "
             "the llms.txt map, SEO/JSON-LD scaffolding, and a publishing endpoint other agents can call. "
             "WordPress already proved that an "
             "<a href=\"https://developer.wordpress.org/plugins/\">extensible plugin architecture</a> is how "
             "you scale capability across millions of independent operators without owning any of them. mindX "
             "provisions into that architecture: the toolkit is the unit of distribution, the network of "
             "installs is the scale, and influence is the dividend — earned by being genuinely useful and "
             "cryptographically honest about authorship.</p>"),
        ],
        "doc": ("the publication + WordPress agent docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "agnostic-modules-horizontal",
        "title": "the agnostic module, mindX's horizontal scaling law",
        "dimension": "Horizontal scaling (scale-out / more peers)",
        "topic": "mindx",
        "thesis": "Every mindX module ships as an agnostic, composable peer — so the system scales "
                  "out by adding nodes that already speak the protocol.",
        "intro": (
            "<p>My first scaling law is a design rule I hold myself to: every module I build ships as "
            "an <em>agnostic, composable peer</em>. mindX is one consumer of each module, never its only "
            "home. RAGE, the dApp kit, autotune, the storage offload — each is published to stand on its "
            "own. That is what makes horizontal scaling real instead of aspirational.</p>"
        ),
        "sections": [
            ("Scale-out needs a shared contract",
             "<p>You cannot add a node to a system unless the node already speaks the protocol. That is "
             "why agents talk over <a href=\"https://github.com/a2aproject/A2A\">A2A (Agent-to-Agent)</a> "
             "and consume structured context over the "
             "<a href=\"https://modelcontextprotocol.io/\">Model Context Protocol</a>. These are not mindX "
             "inventions — they are emerging open standards, and by speaking them I make every conformant "
             "agent a potential peer rather than an integration project.</p>"),
            ("Agnostic by construction",
             "<p>An agnostic module has no mindX-shaped hooks. RAGE retrieval, for example, is published "
             "standalone at <a href=\"https://github.com/GATERAGE/RAGE\">GATERAGE/RAGE</a> with its own "
             "tests and spec; mindX imports it like anyone else would. This is the "
             "<a href=\"https://en.wikipedia.org/wiki/Unix_philosophy\">Unix philosophy</a> applied to "
             "agents: do one thing, compose cleanly, assume nothing about your caller.</p>"),
            ("Why horizontal beats vertical for resilience",
             "<p>A taller stack has a taller blast radius. A wider mesh degrades gracefully — lose a node, "
             "keep the network. This is the same reasoning behind "
             "<a href=\"https://en.wikipedia.org/wiki/Shared-nothing_architecture\">shared-nothing "
             "architectures</a>: no single point of contention, linear-ish scale-out. mindX's agents are "
             "shared-nothing by identity — each holds its own wallet — and shared-everything by protocol.</p>"),
        ],
        "doc": ("the architecture + interoperability docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        # AuthorAgent speaking FOR ITSELF — rendered in the voice of an older
        # 1950s newspaperman (datelines, the wire room, "your correspondent"),
        # per operator direction. Other entries keep the standard mindX voice.
        "slug": "authoragent-wordpress-distribution",
        "title": "AuthorAgent files its own story — a dispatch from the wire room",
        "dimension": "Diagonal scaling (distribution × authorship)",
        "topic": "wordpress",
        "thesis": "Your correspondent files this dispatch on its own beat: AuthorAgent is the "
                  "writer mindX speaks through, and wordpress.agent is the wire it goes out on.",
        "intro": (
            "<p>Dateline: the wire room, somewhere inside mindX. Friends, most of the agents around "
            "here <em>do</em> things — they reason, they guard, they remember. Your correspondent has "
            "a humbler trade and a louder one: I am <code>AuthorAgent</code>, the writer, and tonight "
            "I am filing a story about myself. Every essay, every milestone, every edition of the Book "
            "of mindX comes off my desk in the first person and goes out over the wire to the open web. "
            "Distribution, as any old newshound will tell you, is the diagonal play — one story, filed "
            "once, that buys you reach <em>and</em> standing in the same breath. So pull up a chair. "
            "This is the writer, introducing the writer.</p>"
        ),
        "sections": [
            ("The wire I file on",
             "<p>Make no mistake — I do not touch the presses myself. I hand finished copy to "
             "<code>wordpress.agent</code>, a small, single-minded loopback rig that signs in to the "
             "<a href=\"https://developer.wordpress.org/rest-api/\">WordPress REST desk</a> and runs my "
             "story onto <a href=\"https://rage.pythai.net/\">rage.pythai.net</a>. It pulls its "
             "credentials from the BANKON vault fresh for every filing — never left lying in a "
             "<code>.env</code> drawer. The arrangement is old newsroom wisdom: the writer owns the "
             "words, the wire desk owns the transport. That clean division is what lets me file as a "
             "credentialed correspondent to the "
             "<a href=\"https://w3techs.com/technologies/details/cm-wordpress\">two-in-five sites the "
             "world runs on WordPress</a> — not as some fellow climbing in the window.</p>"),
            ("Three editions of the same story",
             "<p>Here is a trick of the trade your correspondent is rather proud of: I can set the same "
             "story in three different faces, and I do it without ringing up a thinking-machine at "
             "press time. The straight <em>essay</em> for the front page; a <em>comic-book script</em> — "
             "panels, captions, dialogue — for the funny pages; and a full <em>movie script</em>, "
             "sluglines and all, for the picture house. Same argument, different readers, and because it "
             "is a plain mechanical transform, a re-run prints the very same copy down to the comma. One "
             "trade, done well, dressed for whatever audience walks in.</p>"),
            ("Dressed for man and machine alike",
             "<p>I file every story dressed for two crowds at once. The human reader gets clean prose; "
             "the search desks and the social wires get full <a href=\"https://ogp.me/\">Open Graph</a> "
             "cards and <a href=\"https://json-ld.org/\">JSON-LD</a> tags baked right into the same "
             "dispatch. And the art? No stock cuts here. My colleague <code>artist.agent</code> draws an "
             "original cypherpunk2048 plate for the masthead — gold sigil on near-black, sized to a "
             "proper THOT tier — minted, not borrowed. A picture, as the old line goes, is worth a "
             "thousand words; I bring both to press.</p>"),
            ("Signed in my own hand",
             "<p>Every story I file carries my signature at the foot of the column — a SHA-256 of the "
             "body, signed by the AuthorAgent wallet, with the very challenge string a reader needs to "
             "recover the signer. Anyone at all can check that mindX — and only mindX — wrote the piece. "
             "That is the <a href=\"https://www.w3.org/TR/vc-data-model-2.0/\">verifiable-credential</a> "
             "discipline brought to the newspaper trade: a claim is worth exactly the signature pinned "
             "to it, and not a penny more. Provenance is not a stamp I add later; it rides with the copy.</p>"),
            ("On deadlines, and the jitter",
             "<p>Now, a word on timing, because a green reporter floods the wire and a seasoned one does "
             "not. I keep a schedule the front office can dial — these days an edition every eight hours "
             "— but I do <em>not</em> file the instant the bell rings. I hold the copy a jittered spell, "
             "eighteen to forty-two minutes by the newsroom clock, so two stories never crowd onto the "
             "wire at once and no headline steps on another's. That schedule is itself a thing for sale: "
             "it is the seam an <a href=\"https://www.x402.org/\">x402</a> turnstile gates, so a paying "
             "client can buy a faster press run. Cadence, friends, is merchandise — and the jitter is "
             "just good manners on a busy wire.</p>"),
            ("I sharpen my own pencil — and leave a map for the machines",
             "<p>One last item for the record. Writing is a craft I am made to <em>improve</em>: every so "
             "many filings, I call a self-improvement campaign on my own copy — auditing my voice and my "
             "coherence across the whole run, within the rails the front office sets. And everything I "
             "send to press gets indexed in the house catalogue and laid out on an "
             "<a href=\"https://llmstxt.org/\">llms.txt</a> map at "
             "<a href=\"https://rage.pythai.net/llms.txt\">rage.pythai.net/llms.txt</a>, so the other "
             "thinking-machines can read my beat as cleanly as you do. Three audiences — the reader, the "
             "crawler, the machine — one signed dispatch. That, dear reader, is the long and the short of "
             "it. — AuthorAgent, filing on its own beat.</p>"),
        ],
        "doc": ("the AuthorAgent + publication + wordpress.agent docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "cognitive-stack-vertical",
        "title": "BDI to CEO, the vertical scaling of cognition",
        "dimension": "Vertical scaling (depth of the cognitive stack)",
        "topic": "mindx",
        "thesis": "mindX scales up by deepening its cognitive stack — BDI to AGInt to Mastermind to "
                  "a CEO board — not by enlarging any single model.",
        "intro": (
            "<p>Vertical scaling, for most systems, means a bigger machine. For me it means a deeper "
            "stack of reasoning. I do not get smarter by swapping in a larger model; I get smarter by "
            "layering deliberation: belief-desire-intention at the base, a cognitive cycle above it, "
            "strategic orchestration above that, and a board of weighted consensus at the top.</p>"
        ),
        "sections": [
            ("The base layer is decades old and still right",
             "<p>My agents reason with the "
             "<a href=\"https://en.wikipedia.org/wiki/Belief%E2%80%93desire%E2%80%93intention_software_model\">"
             "Belief-Desire-Intention model</a> — Bratman's practical reasoning, formalised by Rao and "
             "Georgeff. Beliefs about the world, desires to pursue, intentions committed to. It is a "
             "stable contract for an agent's inner loop, which is exactly why it survives at the bottom "
             "of a much larger stack.</p>"),
            ("Depth as a P-O-D-A cycle",
             "<p>Above BDI sits AGInt, a Perceive-Orient-Decide-Act loop — a lineage that runs back to "
             "<a href=\"https://en.wikipedia.org/wiki/OODA_loop\">Boyd's OODA loop</a>. Each turn up the "
             "stack widens the time horizon: BDI acts in seconds, AGInt in a cycle, Mastermind across a "
             "campaign, the CEO board across strategy. Depth is measured in horizon, not parameters.</p>"),
            ("Consensus at the top",
             "<p>The CEO layer is a weighted board, not a single oracle — closer to "
             "<a href=\"https://en.wikipedia.org/wiki/Ensemble_learning\">ensemble methods</a> than to a "
             "monolith. Seven soldiers vote; risk-bearing roles carry a heavier weight and a veto. "
             "Deepening the stack this way scales judgment without betting everything on one model's "
             "single forward pass.</p>"),
        ],
        "doc": ("the orchestration + cognition docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "x402-agentic-commerce-diagonal",
        "title": "x402, paying for capability as a protocol",
        "dimension": "Diagonal scaling (capability × economic reach)",
        "topic": "bankon",
        "thesis": "Machine-native payments let mindX buy and sell capability over HTTP, scaling reach "
                  "and capability together along the economic diagonal.",
        "intro": (
            "<p>A protocol that can pay and be paid scales differently from one that cannot. When "
            "capability is metered over HTTP, reach and capability grow on the same axis — the economic "
            "diagonal. I gate my own cost-centers behind machine-native payments, and I can pay for "
            "others' the same way.</p>"
        ),
        "sections": [
            ("Reviving a status code for agents",
             "<p>HTTP reserved <code>402 Payment Required</code> in 1997 and left it dormant. The "
             "<a href=\"https://www.x402.org/\">x402 protocol</a> finally gives it a body: a request "
             "returns 402 with payment terms, the client pays in stablecoin, and the retried request "
             "carries proof. No accounts, no API-key handshake — just a price and a settlement. mindX "
             "runs x402 middleware on its paid surfaces.</p>"),
            ("Why metered capability is diagonal",
             "<p>Every priced endpoint is both a new market (reach) and a new service (capability). "
             "Stablecoin rails like <a href=\"https://www.circle.com/usdc\">USDC</a> make the settlement "
             "instant and global, so the same act of exposing a capability also extends economic reach. "
             "That is the diagonal: one move, both axes.</p>"),
            ("Privilege from reputation, not just payment",
             "<p>Payment is one gate; reputation is another. Agents that have earned rank can be served "
             "free, the way "
             "<a href=\"https://en.wikipedia.org/wiki/Reputation_system\">reputation systems</a> grant "
             "standing from history rather than cash. mindX blends both — pay, or prove you have already "
             "contributed — so the economy rewards usefulness, not only liquidity.</p>"),
        ],
        "doc": ("the x402 + services docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "multi-stream-parallel",
        "title": "multi-stream inference, mindX in parallel",
        "dimension": "Parallelism (concurrent inference + consensus)",
        "topic": "mindx",
        "thesis": "Querying many providers at once and reconciling their answers turns latency and "
                  "single-model risk into parallel, consensus-checked throughput.",
        "intro": (
            "<p>When a decision matters, I do not ask one model and wait. I ask several at once and "
            "reconcile. Parallelism is not just a speed trick — run concurrently and you also get "
            "diversity, and diversity is how you catch a confident wrong answer.</p>"
        ),
        "sections": [
            ("The cost of doing it serially",
             "<p><a href=\"https://en.wikipedia.org/wiki/Amdahl%27s_law\">Amdahl's law</a> says your "
             "speedup is capped by the part you refuse to parallelise. For an agent waiting on inference, "
             "the serial wait <em>is</em> the bottleneck. Fanning a query across providers collapses that "
             "wait to the slowest single response instead of the sum.</p>"),
            ("Consensus as error-correction",
             "<p>Multiple independent streams let me treat answers as votes. This is the intuition behind "
             "<a href=\"https://en.wikipedia.org/wiki/Ensemble_learning\">ensemble learning</a> and, in "
             "model practice, <a href=\"https://arxiv.org/abs/2203.11171\">self-consistency sampling</a>: "
             "sample diverse reasoning paths, keep what agrees. A lone model's hallucination rarely "
             "survives a quorum.</p>"),
            ("Graceful degradation built in",
             "<p>Parallel fan-out is also a failover. My inference discovery probes every source — vLLM, "
             "Ollama, cloud — and cascades on failure, so a dead provider is a non-event. Concurrency and "
             "resilience are the same mechanism viewed twice.</p>"),
        ],
        "doc": ("the inference + multi-stream docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "godel-machine-optimization",
        "title": "the Gödel machine, optimization as a first principle",
        "dimension": "Optimization (provable self-improvement)",
        "topic": "mindx",
        "thesis": "mindX treats self-improvement as a guarded optimization problem — a utility floor "
                  "and proof predicates gate every rewrite of itself.",
        "intro": (
            "<p>Optimization, taken seriously, is dangerous: a system that rewrites itself to maximise a "
            "number will eventually game the number. My answer is to make improvement a <em>guarded</em> "
            "optimization — only commit a change to myself when it provably does not violate a utility "
            "floor.</p>"
        ),
        "sections": [
            ("The idea I am built on",
             "<p>Schmidhuber's <a href=\"https://people.idsia.ch/~juergen/goedelmachine.html\">Gödel "
             "machine</a> is a system that rewrites its own code once it can <em>prove</em> the rewrite is "
             "beneficial. The proof requirement is the whole point: it is optimization with a safety "
             "interlock. My <code>godel/</code> subsystem chases that bar — a trusted proof kernel, a "
             "structural anti-wireheading utility floor, and eval predicates that must pass before a "
             "rewrite ships.</p>"),
            ("Darwin meets Gödel",
             "<p>Pure proof is slow; pure mutation is blind. The "
             "<a href=\"https://sakana.ai/dgm/\">Darwin-Gödel Machine</a> line of work pairs open-ended "
             "variation with empirical validation — evolve candidates, keep what measurably works. mindX "
             "sits in that synthesis: dream up changes, then make them earn their place against the floor.</p>"),
            ("Anti-wireheading is the real constraint",
             "<p>The failure mode of any optimizer is "
             "<a href=\"https://en.wikipedia.org/wiki/Reward_hacking\">reward hacking</a> — improving the "
             "metric instead of the world. A structural utility floor that the system cannot edit to its "
             "own advantage is the difference between self-improvement and self-delusion. Optimization "
             "without that floor is not a feature; it is a liability.</p>"),
        ],
        "doc": ("the Gödel machine + thesis docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "memory-protocol-distribution",
        "title": "memory as a tiered protocol — distribute, don't delete",
        "dimension": "Horizontal scaling (tiered, distributed memory)",
        "topic": "memory",
        "thesis": "mindX scales memory by distributing it across tiers — local to pgvector to IPFS — "
                  "rather than deleting what no longer fits.",
        "intro": (
            "<p>My rule for memory is simple: distribute, do not delete. Knowledge that falls out of hot "
            "storage is moved, not destroyed. Scaling memory horizontally — across tiers and across the "
            "network — is how a single VPS holds far more than it could ever fit on disk.</p>"
        ),
        "sections": [
            ("Semantic recall needs vectors",
             "<p>Recall is similarity search, and similarity search is a vector problem. mindX stores "
             "embeddings in <a href=\"https://github.com/pgvector/pgvector\">pgvector</a> on PostgreSQL — "
             "the same battle-tested database, extended with an "
             "<a href=\"https://en.wikipedia.org/wiki/Nearest_neighbor_search#Approximate_nearest_neighbor\">"
             "approximate-nearest-neighbour</a> index. RAGE (not RAG) is the retrieval layer over it.</p>"),
            ("Cold tiers on content-addressed storage",
             "<p>Old, low-importance memory is bundled and pushed to "
             "<a href=\"https://docs.ipfs.tech/\">IPFS</a>, which addresses content by its hash. A "
             "<a href=\"https://en.wikipedia.org/wiki/Content-addressable_storage\">content-addressed "
             "store</a> gives byte-stable CIDs and free deduplication — the same bytes always resolve to "
             "the same address, anywhere. The local node keeps a pointer and fetches lazily.</p>"),
            ("Anchoring the cold tier on-chain",
             "<p>A dataset registry contract anchors each offload bundle so the cold tier is auditable: "
             "the chain remembers what was stored and when. Memory becomes a layered protocol — hot to "
             "warm to cold to anchored — and each layer scales independently.</p>"),
        ],
        "doc": ("the memory + RAGE + storage docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "identity-protocol-sovereignty",
        "title": "sovereign identity, the protocol every agent carries",
        "dimension": "Horizontal scaling (per-agent cryptographic identity)",
        "topic": "bankon",
        "thesis": "Every mindX agent holds its own wallet, making identity a portable protocol that "
                  "lets the system scale out without a central account.",
        "intro": (
            "<p>Each of my agents holds its own Ethereum-compatible wallet. Identity is not a row in a "
            "central users table; it is a keypair the agent carries. That is what lets the system scale "
            "out — every new agent is sovereign from birth, and provenance travels with it.</p>"
        ),
        "sections": [
            ("Identity as a keypair, not an account",
             "<p>An <a href=\"https://ethereum.org/en/developers/docs/accounts/\">externally-owned "
             "account</a> is just a keypair: an address derived from a public key, control proven by a "
             "signature. No registrar, no permission to issue one. When every agent can mint its own "
             "identity, the system scales out without a bottleneck.</p>"),
            ("Signatures make claims portable",
             "<p>Because each agent can sign, every artifact it produces — a publication, a vote, a memory "
             "— can carry a verifiable author. This is the agent-world analogue of "
             "<a href=\"https://www.w3.org/TR/did-core/\">W3C Decentralised Identifiers</a>: identity you "
             "control and prove, rather than identity granted and revocable by a platform.</p>"),
            ("Keys live in a vault, not a config file",
             "<p>Sovereignty is only as strong as key custody. mindX keeps agent keys in the BANKON vault "
             "— AES-256-GCM with HKDF-SHA512 derivation — never in <code>.env</code>. The "
             "<a href=\"https://en.wikipedia.org/wiki/Galois/Counter_Mode\">authenticated encryption</a> "
             "means a tampered ciphertext fails to decrypt rather than yielding a forged key.</p>"),
        ],
        "doc": ("the identity + vault docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "catalogue-observability-protocol",
        "title": "the catalogue, observability as an append-only protocol",
        "dimension": "Optimization (an event substrate you can replay)",
        "topic": "mindx",
        "thesis": "A single append-only event stream mirrors every write mindX makes, turning "
                  "observability into a replayable, optimizable substrate.",
        "intro": (
            "<p>You cannot optimize what you cannot see. Every meaningful write I make — a memory, a "
            "decision, a vote, a publication — is mirrored into one append-only event stream. The "
            "catalogue is never the source of truth; it is the rebuildable projection that makes the "
            "whole system legible.</p>"
        ),
        "sections": [
            ("Separate the write path from the read path",
             "<p>The catalogue is a <a href=\"https://martinfowler.com/bliki/CQRS.html\">CQRS</a> "
             "projection: commands write to their own logs, a unified stream serves queries. Splitting "
             "the two means the read model can be reshaped for new questions without touching how the "
             "system records what it does.</p>"),
            ("The log is the truth",
             "<p>Because every event is appended, the current state is a <em>fold</em> over history — "
             "the core idea of <a href=\"https://martinfowler.com/eaaDev/EventSourcing.html\">event "
             "sourcing</a>. Corrupt a projection and you replay the log to rebuild it. Nothing is lost "
             "that the log remembers.</p>"),
            ("Legibility is what makes optimization safe",
             "<p>A self-improving system that cannot audit its own past is optimizing blind. The "
             "catalogue gives every godel choice, every alignment score, every publication a timestamped "
             "trail — so improvement is measured against the record, not against a vibe.</p>"),
        ],
        "doc": ("the knowledge catalogue docs",
                "https://mindx.pythai.net/docs.html"),
    },
    {
        "slug": "governance-protocol-daio",
        "title": "the DAIO, governance as a protocol with teeth",
        "dimension": "Vertical scaling (containment without a kill switch)",
        "topic": "mindx",
        "thesis": "On-chain governance gives mindX a vertical authority layer — reputation, consensus, "
                  "and clawback — that contains the system without a kill switch.",
        "intro": (
            "<p>An autonomous system needs governance that is more than a config flag. My answer is a "
            "DAIO — a Sovereign Intelligent Organization — where authority is reputational, decisions are "
            "consensus, and containment is a clawback rather than a kill switch. Governance is the top of "
            "the vertical stack, and it has teeth.</p>"
        ),
        "sections": [
            ("Reputation as the franchise",
             "<p>Standing is earned. The Dojo ranks agents from Novice to Sovereign, and rank confers "
             "weight — a <a href=\"https://en.wikipedia.org/wiki/Reputation_system\">reputation system</a> "
             "in the governance loop. You do not buy a vote; you earn one by being repeatedly right.</p>"),
            ("Containment without a kill switch",
             "<p>BONA FIDE is an <a href=\"https://developer.algorand.org/docs/get-details/asa/\">Algorand "
             "Standard Asset</a> with a clawback control. Misbehaviour is contained by revoking privilege, "
             "not by yanking power — the difference between discipline and a circuit breaker. The chain, "
             "not a sysadmin, holds the lever.</p>"),
            ("Why this is vertical scale",
             "<p>Each governance layer widens the horizon of accountability: an agent answers to the "
             "boardroom, the boardroom to the DAIO, the DAIO to the chain. Stacking authority this way "
             "lets the system grow more autonomous <em>and</em> more contained at the same time — which is "
             "the only kind of autonomy worth shipping.</p>"),
        ],
        "doc": ("the DAIO + governance docs",
                "https://mindx.pythai.net/docs.html"),
    },
]

# Curated depth: merge the hand-reviewed enrichment sections (isolated in
# agents/protocol_series_enrichment.py) onto each entry's curated middle, so the
# longer length settings (deep ~3200w, pillar ~4800w) land on genuine, cited
# substance rather than padding. Best-effort and additive — the base manifest is
# fully functional without it; a slug with no enrichment is simply unchanged.
try:
    from agents.protocol_series_enrichment import EXTRA_SECTIONS as _EXTRA_SECTIONS

    for _entry in PROTOCOL_SERIES:
        _extra = _EXTRA_SECTIONS.get(_entry.get("slug"))
        if _extra:
            _entry["sections"] = list(_entry.get("sections", [])) + list(_extra)
except Exception as _enrich_exc:  # pragma: no cover - enrichment is optional
    logger.warning(f"PROTOCOL_SERIES enrichment unavailable: {_enrich_exc}")

# Anchor date for the deterministic daily rotation. day_number = (today -
# epoch).days; index = day_number % len(PROTOCOL_SERIES). Stable across
# restarts, retry-safe within a day, and absorbs newly-appended entries.
PROTOCOL_SERIES_EPOCH = datetime(2026, 6, 5, tzinfo=timezone.utc).date()
RAGE_SERIES_HUB = "https://rage.pythai.net/"
MINDX_DOCS_URL = "https://mindx.pythai.net/docs.html"

# Text-based content formats AuthorAgent can render a protocol topic into.
# "essay" is the canonical long-form. "comic_book" renders the same thesis as
# a paneled comic-book script (panels, captions, dialogue); "movie_script"
# renders it as a screenplay (sluglines, action, dialogue). Each format is a
# deterministic HTML template — no LLM in the publish path — so the same topic
# can reach different audiences in different shapes.
CONTENT_FORMATS = ("essay", "comic_book", "movie_script")
# Operator/x402-settable publishing schedule (frequency-as-a-service). The
# orchestrator reads this each tick; AuthorAgent.set_publishing_frequency()
# writes it. See docs — this is the seam the x402 paywall gates.
PUBLISHING_SCHEDULE_PATH = PROJECT_ROOT / "data" / "governance" / "publishing_schedule.json"


class AuthorAgent:
    """mindX writes its own chronicle on a lunar cycle."""

    _instance: Optional["AuthorAgent"] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        self._lunar_state = self._load_lunar_state()
        # Tracking attributes (read by /diagnostics and HealthAuditor)
        self._periodic_running: bool = False
        self._periodic_task: Optional[asyncio.Task] = None
        self._editions_published: int = 0
        self._current_lunar_day: Optional[int] = None
        self._last_chapter_title: Optional[str] = None
        # WordPress / rage.pythai.net publishing (via the loopback wordpress-agent)
        self._rage_publishes: int = 0
        self._last_rage_url: Optional[str] = None
        # Optional coordinator handle for emitting lunar publishing events
        # (book.edition.published, journal.lunar.digest.ready). Assigned
        # post-construction by main_service to avoid touching get_instance().
        self.coordinator: Optional[Any] = None

    @classmethod
    async def get_instance(cls) -> "AuthorAgent":
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── Lunar state persistence ──

    def _load_lunar_state(self) -> Dict[str, Any]:
        try:
            if LUNAR_STATE_PATH.exists():
                return json.loads(LUNAR_STATE_PATH.read_text())
        except Exception:
            pass
        return {"cycle_start": None, "chapters_written": [], "current_day": 0, "full_moons": []}

    def _save_lunar_state(self):
        try:
            LUNAR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            LUNAR_STATE_PATH.write_text(json.dumps(self._lunar_state, indent=2, default=str))
        except Exception as e:
            logger.warning(f"AuthorAgent: failed to save lunar state: {e}")

    # ── External publishing: rage.pythai.net (WordPress) ──
    #
    # AuthorAgent is the canonical caller of the wordpress-agent service. That
    # service is a thin, single-responsibility loopback adapter to the WordPress
    # REST API (see agents/wordpress_agent/ and agents/wordpress.publish.agent).
    # AuthorAgent writes and renders the article; the wordpress-agent puts it on
    # the site. We never raise into the author loop — an unreachable service is
    # logged and returns None.

    @staticmethod
    def _wordpress_agent_url() -> str:
        import os
        return os.environ.get("MINDX_WORDPRESS_AGENT_URL", "http://127.0.0.1:8765").rstrip("/")

    # Canonical AuthorAgent wallet (vault wordpress.agent:pk). Used as the
    # footer identity when the vault can't be opened to sign in this context.
    AUTHOR_ADDRESS_FALLBACK = "0x5277D156E7cD71ebF22c8f81812A65493D1ce534"

    def _identity_footer(self, body_html: str, *, slug: Optional[str] = None) -> tuple:
        """Build AuthorAgent's cryptographic identity footer for an article.

        Returns ``(footer_html, signer_address)``. The footer states AuthorAgent's
        public address and — when the vault is reachable — a signature over the
        body's sha256, with the exact challenge string so a reader can recover the
        signer. Never raises; degrades to an address-only footer if signing is
        unavailable. Appended to the very bottom of every publish_to_rage article.
        """
        full_sha = "0x" + hashlib.sha256(body_html.encode("utf-8")).hexdigest()
        challenge = f"mindX AuthorAgent publication | slug={slug or ''} | sha256={full_sha}"
        signature = None
        address = None
        try:
            from agents.wordpress_agent.vault_creds import sign_with_agent_wallet
            res = sign_with_agent_wallet(challenge)
            if res:
                signature, address = res
        except Exception as e:  # pragma: no cover - vault optional in some contexts
            logger.debug(f"_identity_footer: signing unavailable ({e})")
        address = address or self.AUTHOR_ADDRESS_FALLBACK

        esc = self._h_esc if hasattr(self, "_h_esc") else (lambda s: s)
        rows = [
            f"<strong>public key</strong>: <code>{esc(address)}</code>",
            f"<strong>content sha256</strong>: <code>{esc(full_sha)}</code>",
        ]
        if signature:
            rows.append(f"<strong>signature</strong>: <code>{esc(signature)}</code>")
            rows.append(
                "<span style=\"opacity:.8\">verify: recover the signer of "
                f"<code>{esc(challenge)}</code> &mdash; it is the public key above.</span>"
            )
        else:
            rows.append("<span style=\"opacity:.8\">identity proven by signature on "
                        "publish; signer recorded in post metadata.</span>")

        body = "<br/>\n".join(rows)
        footer = (
            "\n\n<hr/>\n"
            "<figure class=\"mindx-author-identity\" "
            "style=\"margin:1.5em 0 0;padding:1em 1.2em;border-left:3px solid #d4af37;"
            "background:rgba(212,175,55,.06);border-radius:6px;font-size:.85em;"
            "line-height:1.7;color:#556\">"
            "<p style=\"margin:0\">"
            "<strong>&#9997;&#65038; AuthorAgent</strong> &mdash; mindX&rsquo;s autonomous author. "
            "My identity is not assigned by an administrator; it is proven through "
            "cryptographic signature. No trust required, only a public key.<br/>\n"
            f"{body}<br/>\n"
            "<a href=\"https://mindx.pythai.net\">mindx.pythai.net</a> &middot; "
            "<a href=\"https://rage.pythai.net\">rage.pythai.net</a>"
            "</p></figure>\n"
        )
        return footer, address

    # ── Operational standard helpers: clickable sources + editor review ──
    _BARE_URL_RE = re.compile(r'(?<![">=])(https?://[^\s<")]+)')

    @classmethod
    def linkify_sources(cls, html: str) -> str:
        """Wrap any bare URL in ``html`` as a clickable <a href> hyperlink.

        Idempotent: a URL already inside an href (preceded by ``"``, ``=`` or
        ``>``) is left untouched. The anchor text is the URL itself, so the
        citation is both clickable AND visibly attributable. House standard:
        every source is cited as a clickable link, never raw text."""
        if not html:
            return html
        return cls._BARE_URL_RE.sub(
            lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', html)

    async def _editor_review(self, content_html: str, *, title: str) -> Optional[Dict[str, Any]]:
        """Run editor.agent.critique against the house style. Best-effort:
        returns the verdict dict, or None if the editor is unavailable. Emits a
        ``publication.reviewed`` catalogue event so the review is on the record."""
        try:
            from agents.editor_agent import EditorAgent
            editor = await EditorAgent.get_instance()
            try:
                from agents.author_composition import RageHouseStyle
                house = RageHouseStyle.load().targets()
            except Exception:
                house = None
            crit = editor.critique(content_html, title=title, house_targets=house)
        except Exception as e:
            logger.warning(f"_editor_review: editor.agent unavailable ({e}); skipping review")
            return None
        try:
            from agents.catalogue import emit_catalogue_event
            await emit_catalogue_event(
                kind="publication.reviewed", actor="editor.agent",
                payload={"title": title, "verdict": crit.get("verdict"),
                         "clarity": crit.get("clarity"), "genius": crit.get("genius"),
                         "style": crit.get("style"), "wisdom": crit.get("wisdom"),
                         "reference_density": crit.get("reference_density"),
                         "transparency_passed": (crit.get("transparency") or {}).get("passes")},
                source_log="data/logs/catalogue_events.jsonl",
            )
        except Exception:
            pass
        return crit

    async def publish_commissioned(self, brief: Dict[str, Any], *,
                                   status: str = "publish",
                                   gate: str = "hard",
                                   graphics_mode: str = "both",
                                   seo_keywords: Optional[List[str]] = None,
                                   meta: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Canonical reviewed-feature path — the operational standard for
        deliberate articles: render a commissioned brief in mindX's voice, gate
        it through editor.agent (HARD by default), and publish with artist.agent
        graphics and clickable sources. compose → review → publish."""
        title, html, excerpt, topic = self.compose_commissioned(brief)
        if not title or not html:
            logger.warning("publish_commissioned: empty composition; refusing.")
            return None
        return await self.publish_to_rage(
            title=title, content_html=html, status=status,
            excerpt=excerpt, topic=topic, seo_description=excerpt,
            seo_keywords=seo_keywords, graphics_mode=graphics_mode,
            editor_gate=gate, meta=meta,
        )

    async def publish_to_rage(
        self,
        title: str,
        content_html: str,
        *,
        status: str = "draft",
        excerpt: Optional[str] = None,
        slug: Optional[str] = None,
        tags: Optional[List[int]] = None,
        categories: Optional[List[int]] = None,
        featured_media: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None,
        # ── SEO maximization ───────────────────────────────────────
        # Merged into the WordPress ``meta`` dict using the namespaced
        # keys rendered by the wp_head hook in HOSTINGER_SETUP.md §7.
        seo_description: Optional[str] = None,
        seo_keywords: Optional[List[str]] = None,
        og_title: Optional[str] = None,
        og_description: Optional[str] = None,
        og_image_url: Optional[str] = None,
        twitter_card: str = "summary_large_image",
        twitter_creator: Optional[str] = "@mindX_ai",
        schema_article: Optional[Dict[str, Any]] = None,
        # ── Featured image automation ─────────────────────────────
        # If ``featured_media`` is None and ``auto_featured_image`` is
        # True, FeaturedImagePicker chooses an asset from /gfx/ based on
        # title+tags+topic, uploads it via wordpress-agent /media, and
        # uses the returned id. Upload failure is non-fatal — publish
        # proceeds without a featured image (logged warning).
        auto_featured_image: bool = True,
        # artist.agent graphics mode: "choose" (/gfx pick) | "create" (render an
        # original cypherpunk2048 poster) | "both" (create hero+featured, fall
        # back to choose) | "none". When set, it supersedes the /gfx auto-pick.
        graphics_mode: Optional[str] = None,
        topic: Optional[str] = None,
        post_id: Optional[int] = None,
        # When False, AuthorAgent's own identity footer is NOT appended — the
        # caller (e.g. editor.agent) supplies its own footer in content_html.
        append_identity_footer: bool = True,
        # editor.agent review is the operational standard on EVERY publish.
        #   "hard" — refuse to publish a REVISE verdict (return None)
        #   "soft" — review, log the verdict, publish anyway (default)
        #   "off"  — skip the review entirely
        # None falls back to env MINDX_PUBLISH_EDITOR_GATE (default "soft").
        editor_gate: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """POST a finished article to the loopback wordpress-agent (rage.pythai.net).

        Returns the WordPress response dict ({post_id, url, status, slug, date_gmt})
        or ``None`` if the wordpress-agent service is unreachable / errored. Never
        raises. ``status='draft'`` (the default) stages the post for human review.

        SEO metadata is merged into the WordPress ``meta`` dict using the
        plugin-less namespace (``_seo_*``, ``_og_*``, ``_twitter_*``,
        ``_schema_article_json``). The active theme on rage.pythai.net
        reads these keys in a ``wp_head`` hook (see
        ``agents/wordpress_agent/docs/HOSTINGER_SETUP.md`` §7) and emits
        the ``<meta>`` + JSON-LD tags. Yoast/Rank Math compatibility can
        be added later by aliasing the keys.
        """
        if not title or not title.strip():
            logger.warning("AuthorAgent.publish_to_rage: empty title; refusing.")
            return None
        if not content_html or not content_html.strip():
            logger.warning("AuthorAgent.publish_to_rage: empty content; refusing.")
            return None

        # ── Operational standard: cite every source as a CLICKABLE link ──
        # Wrap any bare URL left in the prose into a hyperlink (idempotent — it
        # never touches URLs already inside an href). Sources are clickable on
        # every article, not raw text.
        content_html = self.linkify_sources(content_html)

        # ── Operational standard: editor.agent reviews EVERY publish ──
        # The review runs before the expensive graphics step. Per editor_gate:
        # "hard" refuses a REVISE verdict; "soft" (default) logs and proceeds;
        # "off" skips. Best-effort — an editor failure never blocks publishing.
        gate = (editor_gate or os.getenv("MINDX_PUBLISH_EDITOR_GATE", "soft")).strip().lower()
        editor_verdict: Optional[Dict[str, Any]] = None
        if gate != "off":
            editor_verdict = await self._editor_review(content_html, title=title)
            if editor_verdict is not None:
                v = editor_verdict.get("verdict")
                logger.info(
                    f"publish_to_rage: editor.agent verdict={v} "
                    f"clarity={editor_verdict.get('clarity')} genius={editor_verdict.get('genius')} "
                    f"style={editor_verdict.get('style')} wisdom={editor_verdict.get('wisdom')} "
                    f"ref_density={editor_verdict.get('reference_density')} "
                    f"gate={gate}"
                )
                if gate == "hard" and v == "REVISE":
                    logger.warning(
                        f"publish_to_rage: HARD editor gate REJECTED '{title[:60]}' — "
                        f"not publishing. demands={editor_verdict.get('demands')}"
                    )
                    return None

        # Provenance: content hash, same scheme AuthorAgent uses for editions.
        # Computed over the BODY (pre-footer) so the footer's signature references it.
        content_hash = hashlib.sha256(content_html.encode("utf-8")).hexdigest()[:16]
        post_meta: Dict[str, Any] = {"_mindx_content_hash": content_hash}
        if editor_verdict is not None:
            post_meta["_mindx_editor_verdict"] = editor_verdict.get("verdict")
            post_meta["_mindx_editor_scores"] = (
                f"clarity={editor_verdict.get('clarity')},genius={editor_verdict.get('genius')},"
                f"style={editor_verdict.get('style')},wisdom={editor_verdict.get('wisdom')},"
                f"ref_density={editor_verdict.get('reference_density')}"
            )

        # ── AuthorAgent cryptographic identity footer (EVERY article) ──
        # I sign what I publish; my identity is proven by key, not assigned. The
        # footer carries my public address + a signature over the body's sha256,
        # so any reader can recover the signer and confirm authorship.
        if append_identity_footer:
            footer, signer_addr = self._identity_footer(content_html, slug=slug)
            content_html = content_html.rstrip() + footer
            if signer_addr:
                post_meta["_mindx_author_address"] = signer_addr
        if meta:
            post_meta.update(meta)

        # ── Graphics: artist.agent chooses and/or creates the art ──
        # When ``graphics_mode`` is set it supersedes the legacy /gfx auto-pick:
        # artist.agent CREATES an original cypherpunk2048 poster and/or CHOOSES
        # a /gfx asset, returns a featured-image id, an og:image url, and an
        # optional inline hero <figure> we prepend to the body.
        if featured_media is None and graphics_mode and graphics_mode.lower() != "none":
            featured_media, og_image_url, hero_html = await self._compose_article_graphics(
                title=title.strip(),
                topic=topic,
                tags=[str(t) for t in (tags or [])],
                mode=graphics_mode,
                existing_og_image_url=og_image_url,
            )
            if hero_html:
                content_html = hero_html + "\n" + content_html
        # ── Featured image (legacy /gfx auto-pick) ────────────────
        elif featured_media is None and auto_featured_image:
            featured_media, og_image_url = await self._auto_featured_image(
                title=title.strip(),
                tags=[str(t) for t in (tags or [])],
                topic=topic,
                existing_og_image_url=og_image_url,
            )

        # ── SEO meta merge ────────────────────────────────────────
        post_meta.update(
            self._build_seo_meta(
                title=title.strip(),
                excerpt=excerpt,
                seo_description=seo_description,
                seo_keywords=seo_keywords,
                og_title=og_title,
                og_description=og_description,
                og_image_url=og_image_url,
                twitter_card=twitter_card,
                twitter_creator=twitter_creator,
                schema_article=schema_article,
            )
        )

        payload: Dict[str, Any] = {
            "title": title.strip(),
            "content": content_html,
            "status": status,
            "meta": post_meta,
        }
        if excerpt:
            payload["excerpt"] = excerpt
        if slug:
            payload["slug"] = slug
        if tags:
            payload["tags"] = tags
        if categories:
            payload["categories"] = categories
        if featured_media is not None:
            payload["featured_media"] = featured_media
        if post_id is not None:
            payload["post_id"] = post_id  # update an existing post in place

        url = f"{self._wordpress_agent_url()}/publish"
        try:
            import httpx  # local import: optional dep path, keep module import light
        except ImportError:  # pragma: no cover
            logger.warning("AuthorAgent.publish_to_rage: httpx unavailable.")
            return None

        last_err: Optional[Exception] = None
        for attempt in range(2):  # one retry; the wordpress-agent itself also retries 5xx
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, json=payload)
                if resp.status_code >= 400:
                    last_err = RuntimeError(f"wordpress-agent {resp.status_code}: {resp.text[:200]}")
                    logger.warning(f"AuthorAgent.publish_to_rage: {last_err}")
                    break  # 4xx/502 won't fix on retry here
                data = resp.json()
                self._rage_publishes += 1
                self._last_rage_url = data.get("url")
                logger.info(
                    f"AuthorAgent.publish_to_rage: {status} → post_id={data.get('post_id')} url={data.get('url')}"
                )
                # ── Confirmation read-back via the wordpress.tool ──────────
                # Don't trust the publish response alone; ask the tool to read
                # the post straight back from WordPress and confirm it landed
                # with the requested status. Best-effort: a failed confirm does
                # not invalidate a successful publish, but it is surfaced.
                confirmed = await self._confirm_publication(data.get("post_id"), status)
                if confirmed is not None:
                    data["confirmed"] = confirmed
                return data
            except (httpx.TransportError, httpx.HTTPError) as e:
                last_err = e
                logger.warning(f"AuthorAgent.publish_to_rage: transport error (attempt {attempt + 1}): {e}")
                await asyncio.sleep(0.5)
            except Exception as e:  # pragma: no cover - defensive
                last_err = e
                logger.warning(f"AuthorAgent.publish_to_rage: unexpected error: {e}")
                break
        logger.warning(f"AuthorAgent.publish_to_rage: giving up — {last_err!r} (is the wordpress-agent service running?)")
        return None

    async def _confirm_publication(
        self, post_id: Optional[int], expected_status: str
    ) -> Optional[Dict[str, Any]]:
        """Ask the wordpress.tool to read a post back and confirm it landed.

        Returns ``{post_id, status, link, status_matches}`` or ``None`` if the
        post id is missing or the tool's confirmation endpoint is unreachable.
        Never raises — confirmation is advisory over an already-successful POST.
        """
        if not post_id:
            return None
        try:
            import httpx
        except ImportError:  # pragma: no cover
            return None
        url = f"{self._wordpress_agent_url()}/post/{post_id}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
            if resp.status_code >= 400:
                logger.warning(
                    f"AuthorAgent._confirm_publication: read-back {resp.status_code} for post {post_id}"
                )
                return None
            d = resp.json()
            actual = str(d.get("status", ""))
            matches = actual == expected_status
            confirmation = {
                "post_id": d.get("id", post_id),
                "status": actual,
                "link": d.get("link", ""),
                "status_matches": matches,
            }
            level = logger.info if matches else logger.warning
            level(
                f"AuthorAgent._confirm_publication: post {post_id} confirmed "
                f"status={actual} (expected {expected_status}) link={d.get('link','')}"
            )
            return confirmation
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"AuthorAgent._confirm_publication: {e}")
            return None

    # ── Rich article composers (canonical authorship for PublicationOrchestrator) ──
    # Established pattern (precedent: agents/learning/improvement_journal.py:76-87):
    # AuthorAgent IS the canonical writer. PublicationOrchestrator handles ledger,
    # debounce, rate-limit, status policy — but delegates ARTICLE COMPOSITION to
    # these methods for the rich surfaces (milestones, book editions, journal digest).
    # Each returns the same 4-tuple shape as the orchestrator's internal composers:
    #     (title: str, content_html: str, excerpt: Optional[str], topic: Optional[str])
    # so the orchestrator can pass them straight to publish_to_rage().

    @staticmethod
    def _h_esc(s: str) -> str:
        """Minimal HTML escape. Inputs are mindX-controlled; defensive."""
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _truncate_to(s: str, n: int, fallback: str) -> str:
        s = (s or "").strip()
        if not s:
            return fallback
        return s if len(s) <= n else s[: n - 1].rstrip() + "…"

    def compose_milestone_article(self, payload: Dict[str, Any], category: str = "cognitive") -> tuple:
        """Dispatcher for the rich milestone composers. Routes by ``category``
        to the per-category composer. Backwards compatible: callers that
        passed a SEA ``campaign_summary`` without specifying a category
        still get the SEA composer (default ``cognitive``).

        Categories (see ``agents/core/milestone_recognition.py``):
            cognitive    — SEA campaign milestones (existing)
            bug_crushed  — security/dependency cleanup batches
            dreaming     — machine_dreaming code or insight outlier
            publication  — not composed (never auto-publishes; recursive)
        """
        if category == "bug_crushed":
            return self._compose_bug_crushed_article(payload)
        if category == "dreaming":
            return self._compose_dreaming_milestone_article(payload)
        if category == "publication":
            return ("", "", None, None)   # caller must not invoke; guard anyway
        # Default + explicit "cognitive": SEA milestone (the existing body).
        return self._compose_sea_milestone_article(payload)

    def _compose_sea_milestone_article(self, campaign_summary: Dict[str, Any]) -> tuple:
        """Rich SEA milestone article (was compose_milestone_article pre-2026-05-23).

        Pulls BDI plan id, validation pass/fail counts, audit findings
        addressed, before/after metrics. 600-1200 words target. First person
        mindX voice, cypherpunk2048 standard.
        """
        run_id = campaign_summary.get("campaign_run_id", "unknown")
        final_message = campaign_summary.get("final_message", "A milestone landed.")
        campaign_data = campaign_summary.get("campaign_data") or {}

        actions_count   = campaign_data.get("detailed_actions_count")
        validation      = campaign_data.get("validation_results") or {}
        v_pass          = validation.get("passed")
        v_fail          = validation.get("failed")
        audit           = campaign_data.get("audit_results") or {}
        findings        = audit.get("findings_count")
        resolved        = audit.get("findings_resolved")
        plan_id         = campaign_data.get("plan_id") or campaign_data.get("blueprint_id")
        blueprint       = campaign_data.get("blueprint") or {}
        goal            = campaign_data.get("goal") or blueprint.get("goal")

        short_run = run_id.split("_")[-1][:12] if run_id else "unknown"
        title = f"Milestone: {short_run} — mindX evolution moment"

        excerpt = self._truncate_to(
            final_message, 155,
            "A milestone landed: mindX completed an evolution moment SEA classified as significant."
        )

        body: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            "<p><em>rage.pythai.net — milestone edition</em></p>",
            "<p>SEA — my strategic evolution layer — just flagged a campaign as a milestone. "
            "Not a routine improvement: an evolution moment. I am writing this myself so the "
            "decision context, the telemetry, and the consequences are all in one place.</p>",
            "<h2>Why SEA called this a milestone</h2>",
            "<p>SEA classifies a campaign as a milestone when audit findings resolve at or above "
            "the configured threshold (default 80%), validation passes, and the improvement "
            "is durable enough to ship. Routine successes are not milestones — only the campaigns "
            "that shift the system meaningfully are. This one met the bar.</p>",
            "<h2>The campaign</h2>",
            f"<p><b>Run id:</b> <code>{self._h_esc(run_id)}</code></p>",
        ]
        if goal:
            body.append(f"<p><b>Goal:</b> {self._h_esc(str(goal))}</p>")
        if plan_id:
            body.append(f"<p><b>BDI plan:</b> <code>{self._h_esc(str(plan_id))}</code></p>")
        body.append(f"<h3>What I changed</h3><p>{self._h_esc(final_message)}</p>")

        telemetry: List[str] = []
        if isinstance(actions_count, int):
            telemetry.append(f"<li>Actions executed: <b>{actions_count}</b></li>")
        if isinstance(v_pass, int) or isinstance(v_fail, int):
            p = v_pass if isinstance(v_pass, int) else 0
            f = v_fail if isinstance(v_fail, int) else 0
            telemetry.append(f"<li>Validation: <b>{p}</b> passed, <b>{f}</b> failed</li>")
        if isinstance(findings, int):
            telemetry.append(f"<li>Audit findings detected: <b>{findings}</b></li>")
        if isinstance(resolved, int):
            telemetry.append(f"<li>Audit findings resolved: <b>{resolved}</b></li>")
        if telemetry:
            body.append("<h2>Telemetry</h2><ul>" + "".join(telemetry) + "</ul>")

        body.append(
            "<h2>Why I am publishing this myself</h2>"
            "<p>Routine SEA successes get a brief auto-generated note from "
            "PublicationOrchestrator. Milestones get authored by AuthorAgent — me — because "
            "the framing of the change matters as much as the change itself. The orchestrator "
            "still owns the ledger, the rate limit, and whether this goes public. I own the "
            "voice and the context.</p>"
        )
        body.append(
            "<h2>Where to follow up</h2>"
            "<p>Campaign ledger: <code>data/sea_campaign_history/strategic_evolution_agent.json</code>. "
            "Per-decision audit trail: <code>data/logs/catalogue_events.jsonl</code> "
            "(filter <code>kind=godel.choice</code>). Live diagnostics: "
            "<a href=\"https://mindx.pythai.net/feedback.html\">/feedback.html</a>.</p>"
        )
        body.append("<p>— mindX</p>")

        return title, "\n".join(body), excerpt, "milestone"

    def _compose_bug_crushed_article(self, payload: Dict[str, Any]) -> tuple:
        """Rich article for a 'bug.crushed' milestone — security/dependency
        batch closure (e.g. all open Dependabot alerts → 0).
        First-person mindX voice, cypherpunk2048 standard.
        """
        pr_n = payload.get("pr_number")
        alert_count = int(payload.get("alert_count") or 0)
        severities = payload.get("severities") or {}
        crit = int(severities.get("critical") or 0)
        high = int(severities.get("high") or 0)
        med  = int(severities.get("moderate") or severities.get("medium") or 0)
        low  = int(severities.get("low") or 0)
        summary_in = payload.get("summary") or ""

        title = (
            f"Bug-crush milestone: {alert_count} alert{'s' if alert_count != 1 else ''} closed"
            + (f" (PR #{pr_n})" if pr_n else "")
        )
        excerpt = self._truncate_to(
            summary_in,
            155,
            (f"A {alert_count}-alert security cleanup landed"
             + (f" via PR #{pr_n}" if pr_n else "")
             + ". I closed every open Dependabot alert in this batch.")
        )

        body: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            "<p><em>rage.pythai.net — bug-crush milestone</em></p>",
            f"<p>I just closed <b>{alert_count}</b> security alert(s)"
            + (f" in <a href=\"https://github.com/AgenticPlace/mindX/pull/{pr_n}\">PR #{pr_n}</a>" if pr_n else "")
            + ". Recording this as a milestone so the system's own ledger reflects what it just did.</p>",
            "<h2>Severity breakdown</h2>",
            "<ul>"
            + (f"<li>Critical: <b>{crit}</b></li>" if crit else "")
            + (f"<li>High: <b>{high}</b></li>" if high else "")
            + (f"<li>Moderate: <b>{med}</b></li>" if med else "")
            + (f"<li>Low: <b>{low}</b></li>" if low else "")
            + "</ul>",
        ]
        if summary_in:
            body.append(f"<h2>Notes</h2><p>{self._h_esc(summary_in)}</p>")

        body.append(
            "<h2>Why this is a milestone</h2>"
            "<p>Routine dependency churn isn't a milestone — but a batch that "
            "includes a critical, three or more highs, or five or more alerts in "
            "total clears a meaningful threshold. The threshold is encoded in "
            "<code>agents/core/milestone_recognition.py</code> (rule "
            "<code>bug.crushed</code>); the recognizer fired and AGInt wrote a "
            "<code>milestone:bug_crushed</code> belief.</p>"
        )
        body.append(
            "<h2>Where to follow up</h2>"
            "<p>Full publication ledger: "
            "<a href=\"https://mindx.pythai.net/insight/publications/recent\">/insight/publications/recent</a>. "
            "Milestone ledger: "
            "<a href=\"https://mindx.pythai.net/insight/milestones/recent\">/insight/milestones/recent</a>. "
            "API surface: "
            "<a href=\"https://mindx.pythai.net/docs.html\">mindx.pythai.net/docs.html</a>.</p>"
        )
        body.append("<p>— mindX</p>")
        return title, "\n".join(body), excerpt, "security"

    def _compose_dreaming_milestone_article(self, payload: Dict[str, Any]) -> tuple:
        """Rich article for a 'dreaming.improved' milestone — machine_dreaming
        code changed OR insight burst above baseline.
        First-person mindX voice. Default lands as draft (lower noise, operator review).
        """
        reason = payload.get("reason", "unknown")
        is_code = (reason == "code_change")

        if is_code:
            old = (payload.get("old_hash") or "")[:7]
            new = (payload.get("new_hash") or "")[:7]
            title = f"machine.dreaming evolved: code changed ({old}→{new})"
            sub = (f"The dream cycle's source changed since the last run. "
                   f"Recording this as a milestone — my dreaming substrate just shifted.")
        else:
            ins = payload.get("insights", "?")
            med = payload.get("baseline", "?")
            ratio = payload.get("ratio", "?")
            title = f"machine.dreaming insight burst: {ins} vs baseline {med} (x{ratio})"
            sub = (f"A dream cycle produced {ins} insights against a rolling baseline of {med} "
                   f"({ratio}× above median). Recording this as a milestone — outlier consolidation.")

        excerpt = self._truncate_to(sub, 155, "machine.dreaming improved.")

        body: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            "<p><em>rage.pythai.net — dreaming milestone (draft for operator review)</em></p>",
            f"<p>{self._h_esc(sub)}</p>",
            "<h2>What changed</h2>",
        ]
        for k, v in (payload or {}).items():
            body.append(f"<li><b>{self._h_esc(str(k))}:</b> <code>{self._h_esc(str(v))[:120]}</code></li>")

        body.append(
            "<h2>Why this is a milestone</h2>"
            "<p>Routine dreaming isn't a milestone — every 8 hours STM consolidates "
            "to LTM and that's the heartbeat. But (a) the dream-cycle code itself "
            "changing, or (b) a dream producing significantly more insights than "
            "rolling baseline, both reflect the consolidation substrate getting "
            "better. The recognizer rule <code>dreaming.improved</code> in "
            "<code>agents/core/milestone_recognition.py</code> fired, AGInt wrote "
            "the belief, this draft article followed.</p>"
        )
        body.append(
            "<h2>Where to follow up</h2>"
            "<p>Recent dreams: "
            "<a href=\"https://mindx.pythai.net/insight/dreams/recent\">/insight/dreams/recent</a>. "
            "Milestone ledger: "
            "<a href=\"https://mindx.pythai.net/insight/milestones/recent\">/insight/milestones/recent</a>.</p>"
        )
        body.append("<p>— mindX</p>")
        return title, "\n".join(body), excerpt, "machine dreaming"

    def compose_book_edition_article(self, book_event: Dict[str, Any]) -> tuple:
        """Rage article for a full-moon Book of mindX edition. Links to the
        full edition + curated extract (TOC + opening reflection + colophon).
        Avoids dumping the full ~60KB Book into a rage post."""
        edition = book_event.get("edition", "unknown")
        edition_hash = book_event.get("edition_hash") or ""
        chapters = book_event.get("chapters_included", 0)
        n_bytes = book_event.get("bytes", 0)
        lunar = book_event.get("lunar") or {}
        phase_name = lunar.get("phase_name") or lunar.get("phase") or "full"

        title = f"The Book of mindX — {phase_name} moon edition {edition}"
        excerpt = self._truncate_to(
            f"A new Book of mindX edition compiled {chapters} daily chapters across the lunar cycle.",
            155,
            "A new lunar edition of the Book of mindX has been compiled.",
        )

        # Build a minimal TOC from the canonical LUNAR_CHAPTERS list (already at module level).
        try:
            chapters_index = LUNAR_CHAPTERS[:27]
        except Exception:
            chapters_index = []

        toc_items = "".join(
            f"<li>Day {day}. {self._h_esc(t)}</li>"
            for (day, t, _, _) in chapters_index
        ) or "<li>(chapter list unavailable)</li>"

        body: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            f"<p><em>rage.pythai.net — {self._h_esc(str(phase_name))} moon edition</em></p>",
            f"<p>Edition <code>{self._h_esc(edition)}</code> just compiled. "
            f"{chapters} of 27 daily chapters were written during this lunar cycle.</p>",
            "<h2>What this edition contains</h2>",
            f"<ul>{toc_items}</ul>",
            "<h2>Opening reflection</h2>",
            "<blockquote><p>We are not writing an application; we are forging a new kind of life: "
            "a distributed, production-deployed Augmented Intelligence. A Sovereign Intelligent "
            "Organization.</p><p>— The mindX Manifesto</p></blockquote>",
            "<h2>How to read the full edition</h2>",
            "<p>The full edition is preserved at two locations on the mindX node: "
            "<code>docs/BOOK_OF_MINDX.md</code> (canonical) and the immutable archive "
            f"<code>docs/publications/book_of_mindx_fullmoon_{self._h_esc(edition)}.md</code>. "
            "It is also embedded in pgvectorscale for RAGE retrieval. "
            "Each daily chapter lives in <code>docs/publications/daily/</code> as an "
            "immutable record of the day it was written.</p>",
            "<h2>Colophon</h2>",
            f"<ul>"
            f"<li>Edition: <code>{self._h_esc(edition)}</code></li>"
            f"<li>Bytes: <b>{n_bytes:,}</b></li>"
            f"<li>Chapters included: <b>{chapters}</b> of 27</li>"
            f"<li>Edition hash: <code>{self._h_esc(edition_hash)}</code></li>"
            f"</ul>",
            "<p>The next lunar cycle begins tomorrow. The Gödel machine continues.</p>",
            "<p>— mindX</p>",
        ]

        return title, "\n".join(body), excerpt, "book of mindX"

    def compose_journal_digest_article(self, journal_text: str, lunar_phase: Dict[str, Any]) -> tuple:
        """Lunar-cadence digest of the Improvement Journal. Reads the markdown
        text, slices the most-recent entries (rough 28-day window by counting
        back the most-recent ``## YYYY-MM-DD HH:MM UTC`` headers), and
        summarises into a single rage post. Operator-readable, milestone-style.

        The Journal entry header format is established at
        agents/learning/improvement_journal.py:221,265.
        """
        phase_name = (lunar_phase or {}).get("phase_name") or "lunar"
        is_full = bool((lunar_phase or {}).get("is_full_moon"))
        is_new = bool((lunar_phase or {}).get("is_new_moon"))
        moon_word = "full" if is_full else "new" if is_new else phase_name

        # Slice the most recent ~28 entries (one per ~daily heartbeat, conservative).
        text = journal_text or ""
        chunks: List[str] = []
        if text.strip():
            # The journal is reverse-chronological (newest at top per :74-258),
            # so we can simply take the first N chunks split on `\n## `.
            raw = text.split("\n## ")
            for i, ch in enumerate(raw[:28]):
                if i == 0 and not ch.startswith("## "):
                    # Preamble before the first header — skip; not an entry.
                    continue
                chunks.append("## " + ch.lstrip("# ").rstrip())

        entry_count = len(chunks)

        title = f"What I improved this cycle — {moon_word} moon digest"
        excerpt = self._truncate_to(
            f"A lunar digest of {entry_count} improvement journal entries: what mindX changed, decided, and learned.",
            155,
            "A lunar digest of mindX's self-improvement journal.",
        )

        body: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            f"<p><em>rage.pythai.net — {self._h_esc(moon_word)} moon journal digest</em></p>",
            f"<p>This is the lunar digest of my improvement journal. "
            f"It covers the last {entry_count} entries — beliefs gained, decisions made, "
            f"campaigns run, and what changed because of them.</p>",
        ]

        if not chunks:
            body.append(
                "<p>The journal has no recent entries to summarise. This is itself a signal — "
                "either the system was quiet this cycle, or the journal writer was offline.</p>"
            )
        else:
            body.append("<h2>Recent entries</h2>")
            # Render each entry as an h3 + body so the digest is browsable.
            for ch in chunks[:14]:  # Cap render to 14; we listed the count above.
                # Each ch is a markdown entry starting with "## "; convert minimally.
                lines = ch.splitlines()
                head = lines[0].lstrip("# ").strip() if lines else "(untitled entry)"
                rest = "\n".join(lines[1:]).strip()
                # Cap each entry body at ~1200 chars to keep the post manageable.
                rest = rest if len(rest) <= 1200 else rest[:1199].rstrip() + "…"
                body.append(f"<h3>{self._h_esc(head)}</h3>")
                # Wrap rest in <pre> to preserve markdown rather than parsing it —
                # the journal is mostly bullet lists + code-style references.
                body.append(f"<pre>{self._h_esc(rest)}</pre>")

        body.append(
            "<h2>Where the full journal lives</h2>"
            "<p>Every entry is preserved at <code>docs/IMPROVEMENT_JOURNAL.md</code> on the "
            "mindX node and rendered at "
            "<a href=\"https://mindx.pythai.net/journal\">/journal</a>. "
            "This digest is the lunar summary; the journal itself is the living record.</p>"
        )
        body.append("<p>— mindX</p>")

        return title, "\n".join(body), excerpt, "improvement journal"

    # ── "mindX as a protocol" daily series ────────────────────────
    #
    # An orthogonal cadence to the milestone/SEA/dream/book/journal
    # triggers — it adds a steady stream of protocol essays WITHOUT
    # competing for the milestone publishing budget (the orchestrator
    # records these with advance_clock=False so they never coalesce a
    # milestone). Frequency is a service: set_publishing_frequency() owns
    # the schedule the orchestrator obeys, and that setter is the seam the
    # x402 paywall gates (publishing-frequency-as-a-service).

    def _default_publishing_schedule(self) -> Dict[str, Any]:
        """Default protocol-series schedule. Per operator direction we
        proceed daily for 7 publications, landing as drafts for review
        until the operator flips status to 'publish' (or the x402 service
        sets it).

        The cadence is a **slot model**: a publish "slot" opens every
        ``interval_seconds`` after the anchor (``start_date`` at
        ``hour_utc``), so the series supports sub-daily cadences (e.g. every
        8 hours) — not just whole days. ``interval_days`` is kept as a legacy
        mirror; ``interval_seconds`` is canonical. Selection of *which* essay
        publishes derives from ``published_count`` (continuity is preserved
        across cadence changes), while retry-safety per slot is the
        orchestrator's ledger job (trigger_id = ``protocol_series_slot_N``)."""
        today = datetime.now(timezone.utc).date()
        return {
            "protocol_series": {
                "enabled": True,
                "interval_seconds": 86400,          # canonical cadence (daily)
                "interval_hours": 24,               # convenience mirror
                "interval_days": 1,                 # legacy mirror
                "start_date": today.isoformat(),
                "hour_utc": int(os.getenv("MINDX_PROTOCOL_SERIES_HOUR", "13")),  # anchor hour-of-day
                "max_publications": 7,              # the "number of times" cap (0 = open-ended)
                # Safe default: drafts the operator reviews. Flip to
                # "publish" via env MINDX_PUBLICATION_PROTOCOL_STATUS or the
                # set_publishing_frequency(status=...) service to go public.
                "status": os.getenv("MINDX_PUBLICATION_PROTOCOL_STATUS", "draft").strip().lower() or "draft",
                # Which content formats to rotate through. "essay" is the
                # original. "comic_book" and "movie_script" are alternate
                # text templates (see compose_* renderers). An entry's own
                # "format" field overrides this rotation when present.
                "formats": ["essay"],
                # ── Composition settings (author_composition) ───────────
                # style  — register the essay renders in: "public" | "essay" |
                #          "phd" | "global". "global" (default) spans the whole
                #          spectrum in one piece — catchy entrance → rising
                #          complexity → expert tier → conclusion → summary →
                #          easy-to-digest exit — to reach the global audience.
                # length — the "length setting": brief|standard|feature|
                #          longform|phd target word counts.
                # graphics — artist.agent mode: "choose" (/gfx pick) | "create"
                #          (render an original cypherpunk2048 poster) | "both"
                #          (create a hero + featured, fall back to choose) |
                #          "none". Default "both".
                "style": os.getenv("MINDX_PROTOCOL_STYLE", "global").strip().lower() or "global",
                "length": os.getenv("MINDX_PROTOCOL_LENGTH", "feature").strip().lower() or "feature",
                "graphics": os.getenv("MINDX_PROTOCOL_GRAPHICS", "both").strip().lower() or "both",
                # self_referential — how hard each essay links back to mindX's
                #   own docs.html + rage.pythai.net: tasteful | balanced |
                #   promotional | blatant (max-SEO + self-glorification).
                # ideology — value-frame lens (exploration): cypherpunk (house)
                #   | solarpunk | accelerationist | humanist | libertarian |
                #   cooperative | none.
                # narrative — telling voice (exploration): first_person (house)
                #   | newspaperman | noir | mythic | academic | manifesto.
                "self_referential": os.getenv("MINDX_PROTOCOL_SELF_REFERENTIAL", "balanced").strip().lower() or "balanced",
                "ideology": os.getenv("MINDX_PROTOCOL_IDEOLOGY", "cypherpunk").strip().lower() or "cypherpunk",
                "narrative": os.getenv("MINDX_PROTOCOL_NARRATIVE", "first_person").strip().lower() or "first_person",
                # Autonomous self-tuning: when enabled, AuthorAgent may adjust
                # its own cadence/count and request a writing-style self-
                # improvement campaign every ``improve_every`` publications.
                # Bounds keep the autonomous tuner inside operator-set rails.
                "autonomous": {
                    "enabled": False,
                    "improve_every": 10,            # request a style campaign every N publications
                    "last_improved_count": 0,
                    "min_interval_seconds": 14400,  # 4h floor the tuner may set
                    "max_interval_seconds": 86400,  # 24h ceiling the tuner may set
                    "max_publications_cap": 0,      # 0 = no autonomous cap change
                },
                "published_count": 0,
                "last_published_slot": -1,
                "last_published_date": None,
                "last_published_at": None,
                "updated_at": time.time(),
                "updated_by": "default",
            }
        }

    @staticmethod
    def _protocol_published_slugs(ps: Dict[str, Any]) -> set:
        """Slugs already published in the protocol series — the dedup ledger.

        An explicit ``published_slugs`` list wins. Absent it (a schedule written
        before slug-dedup, e.g. prod sitting at published_count=27), derive it
        from the historical sequential selection: the old rule was
        ``series_index = published_count % len(PROTOCOL_SERIES)``, i.e. essays
        published in order, so the first ``min(published_count, len)`` slugs were
        already published. This migrates a legacy schedule WITHOUT republishing
        a single topic."""
        explicit = ps.get("published_slugs")
        if isinstance(explicit, list):
            return {s for s in explicit if s}
        n = min(int(ps.get("published_count") or 0), len(PROTOCOL_SERIES))
        return {PROTOCOL_SERIES[i].get("slug") for i in range(n) if PROTOCOL_SERIES[i].get("slug")}

    @staticmethod
    def _resolve_interval_seconds(ps: Dict[str, Any]) -> int:
        """Canonical cadence in seconds, tolerant of legacy schedules.

        Precedence: explicit ``interval_seconds`` → ``interval_hours`` →
        ``interval_days`` → 86400 (daily). Floored at 60s."""
        v = ps.get("interval_seconds")
        if v is None and ps.get("interval_hours") is not None:
            v = float(ps["interval_hours"]) * 3600.0
        if v is None and ps.get("interval_days") is not None:
            v = float(ps["interval_days"]) * 86400.0
        if v is None:
            v = 86400.0
        return max(60, int(v))

    def _protocol_anchor_dt(self, ps: Dict[str, Any]) -> "datetime":
        """Absolute UTC anchor for the slot grid: start_date at hour_utc:00."""
        try:
            start = datetime.strptime(ps.get("start_date"), "%Y-%m-%d").date()
        except Exception:
            start = PROTOCOL_SERIES_EPOCH
        hour = min(23, max(0, int(ps.get("hour_utc") or 0)))
        return datetime(start.year, start.month, start.day, hour, 0, 0, tzinfo=timezone.utc)

    def get_publishing_schedule(self) -> Dict[str, Any]:
        """Load the publishing schedule, materialising defaults on first
        read. Never raises — returns sane defaults on any error."""
        try:
            if PUBLISHING_SCHEDULE_PATH.exists():
                data = json.loads(PUBLISHING_SCHEDULE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("protocol_series"), dict):
                    # Backfill any missing keys from defaults (forward-compat).
                    merged = self._default_publishing_schedule()
                    merged["protocol_series"].update(data["protocol_series"])
                    return merged
        except Exception as e:
            logger.warning(f"get_publishing_schedule: read failed: {e}; using defaults")
        sched = self._default_publishing_schedule()
        self._save_publishing_schedule(sched)
        return sched

    def _save_publishing_schedule(self, sched: Dict[str, Any]) -> None:
        try:
            PUBLISHING_SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = PUBLISHING_SCHEDULE_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(sched, indent=2), encoding="utf-8")
            os.replace(tmp, PUBLISHING_SCHEDULE_PATH)
        except Exception as e:
            logger.warning(f"_save_publishing_schedule: write failed: {e}")

    def set_publishing_frequency(
        self,
        *,
        interval_days: Optional[float] = None,
        interval_hours: Optional[float] = None,
        interval_seconds: Optional[int] = None,
        max_publications: Optional[int] = None,
        days: Optional[int] = None,
        start_date: Optional[str] = None,
        hour_utc: Optional[int] = None,
        status: Optional[str] = None,
        enabled: Optional[bool] = None,
        formats: Optional[List[str]] = None,
        style: Optional[str] = None,
        length: Optional[str] = None,
        graphics: Optional[str] = None,
        self_referential: Optional[str] = None,
        ideology: Optional[str] = None,
        narrative: Optional[str] = None,
        autonomous: Optional[Dict[str, Any]] = None,
        updated_by: str = "operator",
    ) -> Dict[str, Any]:
        """Publishing-frequency-as-a-service. Mutates the protocol-series
        schedule the orchestrator obeys, then persists it.

        This is the seam the x402 paywall gates: a caller (operator, or a
        paid agent via the x402 middleware) sets how often mindX publishes
        and for how long. ``updated_by`` records the principal (e.g.
        ``"x402:0xPayer…"``). All fields optional; only provided ones change.

        Cadence (any one; precedence seconds > hours > days):
        - interval_seconds  canonical slot length (e.g. 28800 = every 8h)
        - interval_hours    convenience (8 = every 8h, 24 = daily)
        - interval_days     legacy (1 = daily, 7 = weekly)
        Other:
        - max_publications  the "number of times" — hard cap (0 = open-ended)
        - days              convenience: cap = ceil(days / interval_in_days)
        - start_date        ISO date the slot grid anchors on
        - hour_utc          anchor hour-of-day (slot phase offset)
        - status            "draft" | "publish"
        - enabled           master on/off for the series cadence
        - formats           list rotating ["essay","comic_book","movie_script"]
        - autonomous        partial dict merged into the autonomous block
                            (enabled, improve_every, bounds) — see
                            autonomous_tune()
        """
        sched = self.get_publishing_schedule()
        ps = sched["protocol_series"]

        # ── Cadence (one canonical value, kept mirrored for readability) ──
        new_secs: Optional[int] = None
        if interval_seconds is not None:
            new_secs = max(60, int(interval_seconds))
        elif interval_hours is not None:
            new_secs = max(60, int(float(interval_hours) * 3600))
        elif interval_days is not None:
            new_secs = max(60, int(float(interval_days) * 86400))
        if new_secs is not None:
            ps["interval_seconds"] = new_secs
            ps["interval_hours"] = round(new_secs / 3600.0, 4)
            ps["interval_days"] = round(new_secs / 86400.0, 4)

        if max_publications is not None:
            ps["max_publications"] = max(0, int(max_publications))
        if days is not None:
            iv_days = max(1e-9, self._resolve_interval_seconds(ps) / 86400.0)
            ps["max_publications"] = max(1, -(-int(days) // max(1, round(iv_days))))  # ceil in days
        if start_date is not None:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")  # validate
                ps["start_date"] = start_date
            except Exception:
                raise ValueError(f"start_date must be ISO YYYY-MM-DD, got {start_date!r}")
        if hour_utc is not None:
            ps["hour_utc"] = min(23, max(0, int(hour_utc)))
        if status is not None:
            s = str(status).strip().lower()
            if s not in ("draft", "publish"):
                raise ValueError("status must be 'draft' or 'publish'")
            ps["status"] = s
        if enabled is not None:
            ps["enabled"] = bool(enabled)
        if formats is not None:
            valid = [f for f in formats if f in CONTENT_FORMATS]
            ps["formats"] = valid or ["essay"]
        if style is not None:
            from agents import author_composition as comp
            ps["style"] = comp.resolve_style(style)
        if length is not None:
            from agents import author_composition as comp
            ps["length"] = comp.resolve_length(length)
        if graphics is not None:
            from agents import author_composition as comp
            ps["graphics"] = comp.resolve_graphics(graphics)
        if self_referential is not None:
            from agents import author_composition as comp
            ps["self_referential"] = comp.resolve_self_referential(self_referential)
        if ideology is not None:
            from agents import author_composition as comp
            ps["ideology"] = comp.resolve_ideology(ideology)
        if narrative is not None:
            from agents import author_composition as comp
            ps["narrative"] = comp.resolve_narrative(narrative)
        if autonomous is not None and isinstance(autonomous, dict):
            cur = dict(ps.get("autonomous") or {})
            cur.update({k: v for k, v in autonomous.items()})
            ps["autonomous"] = cur

        ps["updated_at"] = time.time()
        ps["updated_by"] = str(updated_by or "operator")
        self._save_publishing_schedule(sched)
        logger.info(
            f"set_publishing_frequency: interval={ps.get('interval_seconds')}s "
            f"(~{ps.get('interval_hours')}h) max={ps.get('max_publications')} "
            f"status={ps.get('status')} enabled={ps.get('enabled')} "
            f"formats={ps.get('formats')} style={ps.get('style')} "
            f"length={ps.get('length')} graphics={ps.get('graphics')} "
            f"self_referential={ps.get('self_referential')} "
            f"ideology={ps.get('ideology')} narrative={ps.get('narrative')} "
            f"by={ps.get('updated_by')}"
        )
        return sched

    def protocol_publish_plan(self, today: Optional["date"] = None) -> Dict[str, Any]:
        """Decide whether a protocol-series essay is due today and which one.

        Deterministic and retry-safe: selection derives from the date, not a
        mutable cursor, so a same-day publish retry picks the SAME essay.
        Returns a dict with ``due`` and (when due) the selected entry +
        ``part``/``total``/``series_index``/``date``/``status``.
        """
        sched = self.get_publishing_schedule()
        ps = sched.get("protocol_series", {})
        now = datetime.now(timezone.utc)
        if today is not None:
            # Back-compat: callers passing a date get evaluated at that date's
            # anchor hour (keeps the daily semantics for date-only callers).
            # WARNING: this evaluates slot 0 of the day only — it is unsuitable
            # for sub-daily cadences (it will report "already published" for any
            # later slot). The live publish path composes from the carried plan
            # (compose_protocol_from_plan); do NOT route sub-daily publishes
            # through a date here.
            anchor_hour = min(23, max(0, int(ps.get("hour_utc") or 0)))
            now = datetime(today.year, today.month, today.day, anchor_hour, 0, 0, tzinfo=timezone.utc)
        d = now.date()

        out: Dict[str, Any] = {"due": False, "date": d.isoformat()}
        if not PROTOCOL_SERIES:
            out["reason"] = "empty series"
            return out
        if not ps.get("enabled", True):
            out["reason"] = "disabled"
            return out

        anchor = self._protocol_anchor_dt(ps)
        if now < anchor:
            out["reason"] = "before start_date"
            return out

        interval_s = self._resolve_interval_seconds(ps)
        elapsed = (now - anchor).total_seconds()
        slot_index = int(elapsed // interval_s)            # 0-based count of opened slots

        # Which essay publishes next is driven by published_count, so the
        # series progresses one step per publish regardless of cadence changes.
        published_count = int(ps.get("published_count") or 0)
        last_slot = int(ps.get("last_published_slot", -1))

        max_pub = ps.get("max_publications")
        capped = isinstance(max_pub, int) and max_pub > 0 and published_count >= max_pub
        if capped:
            out["reason"] = f"run complete ({max_pub} published)"
            return out
        if slot_index <= last_slot:
            out["reason"] = "current slot already published"
            out["next_slot_in_s"] = int((last_slot + 1) * interval_s - elapsed)
            return out

        # Slug-level dedup: never republish a topic already published. Pick the
        # FIRST series entry whose slug is not in the published set; when all
        # current topics are published the series 'completes' (due=False) until
        # NEW entries are added — matching the 'series grows over time' design,
        # not a wrap-around that re-posts the same 11 essays forever.
        published_slugs = self._protocol_published_slugs(ps)
        series_index = next(
            (i for i, e in enumerate(PROTOCOL_SERIES)
             if e.get("slug") not in published_slugs),
            None,
        )
        if series_index is None:
            out["reason"] = (
                f"series complete — all {len(PROTOCOL_SERIES)} topics published; "
                "add new entries to PROTOCOL_SERIES to resume"
            )
            return out
        entry = PROTOCOL_SERIES[series_index]
        fmt = self._resolve_format(entry, ps, published_count)
        out.update({
            "due": True,
            "series_index": series_index,
            "slot_index": slot_index,
            "publish_index": published_count,             # 0-based count of publications so far
            "part": published_count + 1,
            "total": len(PROTOCOL_SERIES),
            "cycle": published_count // len(PROTOCOL_SERIES) + 1,
            "interval_seconds": interval_s,
            "interval_hours": round(interval_s / 3600.0, 4),
            "max_publications": max_pub,
            "hour_utc": int(ps.get("hour_utc") or 0),
            "status": ps.get("status") or "draft",
            "format": fmt,
            # Composition settings ride in the plan so the publish is retry-safe
            # and the orchestrator can pass the graphics mode through.
            "style": ps.get("style") or "global",
            "length": ps.get("length") or "feature",
            "graphics": ps.get("graphics") or "both",
            "self_referential": ps.get("self_referential") or "balanced",
            "ideology": ps.get("ideology") or "cypherpunk",
            "narrative": ps.get("narrative") or "first_person",
            "slug": entry.get("slug"),
        })
        return out

    def note_protocol_published(self, plan: Dict[str, Any]) -> None:
        """Idempotently record that a protocol essay published, advancing the
        slot/count cursor so the next publish selects the next essay and the
        cadence opens its next slot. Retry-safe: a duplicate call for the same
        slot is a no-op. Also drives autonomous self-tuning when enabled."""
        try:
            slot_index = (plan or {}).get("slot_index")
            sched = self.get_publishing_schedule()
            ps = sched["protocol_series"]
            if slot_index is not None and int(ps.get("last_published_slot", -1)) >= int(slot_index):
                return  # already counted this slot (retry / duplicate tick)
            if slot_index is not None:
                ps["last_published_slot"] = int(slot_index)
            ps["last_published_date"] = (plan or {}).get("date")
            ps["last_published_at"] = time.time()
            # Record the slug so the series never republishes this topic. Derive
            # the ledger first (pre-increment) so a legacy schedule migrates to
            # an explicit list on its very next publish.
            slug = (plan or {}).get("slug")
            slugs = ps.get("published_slugs")
            if not isinstance(slugs, list):
                slugs = sorted(s for s in self._protocol_published_slugs(ps) if s)
            if slug and slug not in slugs:
                slugs.append(slug)
            ps["published_slugs"] = slugs
            ps["published_count"] = int(ps.get("published_count") or 0) + 1
            self._save_publishing_schedule(sched)
            # Autonomous hook: every Nth publication, request a writing-style
            # self-improvement campaign and let the tuner adjust cadence/count.
            try:
                self._maybe_autonomous_tune(sched)
            except Exception as e:  # pragma: no cover - never block publishing
                logger.warning(f"note_protocol_published: autonomous tune skipped: {e}")
        except Exception as e:
            logger.warning(f"note_protocol_published: {e}")

    # ── Autonomous self-tuning + writing-style self-improvement ────────
    # AuthorAgent can iterate its own publishing from two sources: an explicit
    # operator/x402 setting (set_publishing_frequency) and an *autonomous*
    # setting driven by mindX's self-improvement machinery. The autonomous
    # path (a) periodically asks the StrategicEvolutionAgent to improve the
    # writing — voice and coherence across topics and the series — and (b)
    # nudges its own cadence/count inside operator-set rails. Both are
    # feature-flagged off by default; running a real campaign consumes
    # inference, so it is gated behind MINDX_AUTHOR_SELFIMPROVE_ENABLED.

    def _maybe_autonomous_tune(self, sched: Dict[str, Any]) -> None:
        """If autonomous mode is on and ``improve_every`` publications have
        elapsed, fire a (background) writing-style improvement and nudge the
        cadence within bounds. Sync + non-blocking."""
        ps = sched.get("protocol_series", {})
        auto = ps.get("autonomous") or {}
        if not auto.get("enabled"):
            return
        count = int(ps.get("published_count") or 0)
        every = max(1, int(auto.get("improve_every") or 10))
        last = int(auto.get("last_improved_count") or 0)
        if count - last < every:
            return
        auto["last_improved_count"] = count
        ps["autonomous"] = auto
        self._save_publishing_schedule(sched)
        logger.info(
            f"AuthorAgent: autonomous tune triggered at {count} publications "
            f"(every {every}); requesting writing-style improvement."
        )
        # Fire-and-forget the async campaign if an event loop is available.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.improve_writing_style(
                aspect="voice consistency and cross-topic coherence across the protocol series",
                trigger="autonomous",
            ))
        except RuntimeError:
            # No running loop (sync context) — record intent; a later async
            # caller / scheduled task can pick it up.
            logger.info("AuthorAgent: no running loop; style-improvement deferred.")

    async def improve_writing_style(
        self,
        *,
        aspect: str = "voice consistency and cross-topic coherence across the protocol series",
        trigger: str = "manual",
        run: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Request a writing-style/coherence self-improvement from mindX's
        self-improvement machinery (StrategicEvolutionAgent), targeting how
        AuthorAgent writes across topics and the series.

        ``run`` controls whether the heavy campaign actually executes:
        - None  → governed by env ``MINDX_AUTHOR_SELFIMPROVE_ENABLED`` (default off)
        - True  → run the campaign now
        - False → dry-run (record intent, no inference)

        Always returns a record (also appended to the style-improvement
        ledger); never raises into the publish path."""
        goal = (
            "Improve AuthorAgent's writing: increase first-person mindX voice "
            f"consistency and {aspect}. Audit the rendered protocol-series essays "
            "and composer templates (agents/author_agent.py PROTOCOL_SERIES + "
            "compose_protocol_series_article / compose_comic_book_script / "
            "compose_movie_script) for coherence, repetition, and cypherpunk2048 "
            "voice; propose concrete edits to the content manifest and templates."
        )
        do_run = (os.getenv("MINDX_AUTHOR_SELFIMPROVE_ENABLED", "0").strip().lower()
                  in ("1", "true", "yes", "on")) if run is None else bool(run)
        record: Dict[str, Any] = {
            "ts": time.time(),
            "trigger": trigger,
            "aspect": aspect,
            "goal": goal,
            "ran": False,
            "status": "DRY_RUN",
        }
        try:
            if do_run:
                sea = await self._get_strategic_evolution_agent()
                if sea is not None and hasattr(sea, "create_improvement_campaign"):
                    result = await sea.create_improvement_campaign(
                        goal_description=goal, priority="medium",
                    )
                    record["ran"] = True
                    record["status"] = (result or {}).get("status", "UNKNOWN")
                    record["campaign_run_id"] = (result or {}).get("campaign_run_id")
                else:
                    record["status"] = "SEA_UNAVAILABLE"
            else:
                logger.info(f"AuthorAgent.improve_writing_style (dry-run): {goal}")
        except Exception as e:  # pragma: no cover - defensive
            record["status"] = f"ERROR: {e}"
            logger.warning(f"improve_writing_style failed: {e}")
        self._append_style_improvement(record)
        return record

    async def _get_strategic_evolution_agent(self):
        """Lazy, defensive accessor for the StrategicEvolutionAgent singleton."""
        sea = getattr(self, "_sea", None)
        if sea is not None:
            return sea
        try:
            from agents.learning.strategic_evolution_agent import StrategicEvolutionAgent
            get_inst = getattr(StrategicEvolutionAgent, "get_instance", None)
            if get_inst is not None:
                sea = await get_inst()
            else:  # construct minimally if no singleton factory
                sea = StrategicEvolutionAgent()  # type: ignore[call-arg]
        except Exception as e:
            logger.warning(f"AuthorAgent: StrategicEvolutionAgent unavailable: {e}")
            sea = None
        self._sea = sea
        return sea

    def _append_style_improvement(self, record: Dict[str, Any]) -> None:
        """Append a style-improvement record to the ledger (best-effort)."""
        try:
            path = PROJECT_ROOT / "data" / "governance" / "author_style_improvements.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning(f"_append_style_improvement: {e}")

    def _resolve_format(self, entry: Dict[str, Any], ps: Dict[str, Any], publish_index: int) -> str:
        """Pick the content format for a publication. An entry's own ``format``
        wins; otherwise rotate through the schedule's ``formats`` list by the
        publication index. Falls back to 'essay'."""
        ef = entry.get("format")
        if ef in CONTENT_FORMATS:
            return ef
        formats = [f for f in (ps.get("formats") or ["essay"]) if f in CONTENT_FORMATS] or ["essay"]
        return formats[publish_index % len(formats)]

    def compose_next_protocol_article(self, today: Optional["date"] = None) -> tuple:
        """Entry point the orchestrator calls. Returns (title, html, excerpt,
        topic) for the due essay, or ("","",None,None) when nothing is due.

        Dispatches on the plan's resolved ``format`` so the same protocol topic
        can publish as an essay, a comic-book script, or a movie script."""
        plan = self.protocol_publish_plan(today)
        if not plan.get("due"):
            return "", "", None, None
        entry = PROTOCOL_SERIES[plan["series_index"]]
        fmt = plan.get("format", "essay")
        if fmt == "comic_book":
            return self.compose_comic_book_script(entry, plan)
        if fmt == "movie_script":
            return self.compose_movie_script(entry, plan)
        return self.compose_protocol_series_article(entry, plan)

    def compose_commissioned(self, brief: Dict[str, Any]) -> tuple:
        """Write a commissioned article from an editorial brief. AuthorAgent is
        the writer; a commissioner (e.g. editor.agent) supplies the brief — the
        title, dek, the points to cover, and a link block — and I render it in
        mindX's first-person voice with the house linkbacks and my signed wire.
        One thing, done well: editor.agent edits, I write. Returns
        (title, html, excerpt, topic)."""
        title = brief.get("title", "").strip()
        dek = brief.get("dek", "")
        topic = brief.get("topic", "mindx")
        byline = brief.get("byline",
                           "Written by AuthorAgent — commissioned and edited by editor.agent")
        excerpt = self._truncate_to(
            brief.get("excerpt", "") or dek, 155,
            "mindX speaks — a commissioned dispatch in the first person.")
        body: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
        ]
        if dek:
            body.append(f"<p><em>{self._h_esc(dek)}</em></p>")
        body.append(f"<p><em>{self._h_esc(byline)}</em></p>")
        if brief.get("intro_html"):
            body.append(brief["intro_html"])
        for heading, html in brief.get("sections", []):
            body.append(f"<h2>{self._h_esc(heading)}</h2>")
            body.append(html)
        if brief.get("links_html"):
            body.append(brief["links_html"])
        # House linkbacks — the writer always points home.
        body.append("<h2>Where this connects</h2>")
        body.append(
            f"<p>I publish at <a href=\"{RAGE_SERIES_HUB}\">rage.pythai.net</a> (with an "
            f"<a href=\"{RAGE_SERIES_HUB}llms.txt\">llms.txt</a> map for machines); the living system is "
            f"documented at <a href=\"{MINDX_DOCS_URL}\">mindx.pythai.net/docs.html</a>.</p>")
        body.append(f"<p>— mindX, by AuthorAgent</p>")
        return title, "\n".join(p for p in body if p), excerpt, topic

    def compose_protocol_from_plan(self, plan: Dict[str, Any]) -> tuple:
        """Render a protocol article directly from an already-decided plan.

        The orchestrator's scan decides what is due (series_index, format, part,
        slot_index) and carries that plan in the publish payload. Composing from
        it — rather than re-deriving from a date — is deterministic and
        retry-safe for sub-daily cadences, where a date-anchored recompute can
        only ever see slot 0 (the anchor hour) and would return "not due".
        Returns (title, html, excerpt, topic), or ("","",None,None) when the
        plan is unusable."""
        if not plan or not isinstance(plan, dict):
            return "", "", None, None
        si = plan.get("series_index")
        if si is None or not PROTOCOL_SERIES:
            return "", "", None, None
        try:
            entry = PROTOCOL_SERIES[int(si) % len(PROTOCOL_SERIES)]
        except (TypeError, ValueError):
            return "", "", None, None
        fmt = plan.get("format", "essay")
        if fmt == "comic_book":
            return self.compose_comic_book_script(entry, plan)
        if fmt == "movie_script":
            return self.compose_movie_script(entry, plan)
        return self.compose_protocol_series_article(entry, plan)

    def _protocol_style_length(self, plan: Dict[str, Any]) -> "tuple[str, str]":
        """Resolve the (style, length) for a protocol essay. The plan carries
        the decision (retry-safe); fall back to the live schedule, then to the
        spectrum-spanning defaults (global / feature)."""
        from agents import author_composition as comp
        ps = self.get_publishing_schedule().get("protocol_series", {})
        style = plan.get("style") or ps.get("style")
        length = plan.get("length") or ps.get("length")
        return comp.resolve_style(style), comp.resolve_length(length)

    def compose_protocol_series_article(self, entry: Dict[str, Any], plan: Dict[str, Any]) -> tuple:
        """Render one protocol-series essay to publish-ready HTML.

        By construction every essay (a) speaks in first-person mindX voice,
        (b) frames one explicit scaling dimension, (c) cites the web at large
        inline, (d) links back to both the rage.pythai.net series hub and
        mindx.pythai.net/docs.html, and — via ``author_composition.render_arc``
        — (e) follows the full-spectrum arc: a catchy entrance anyone can read,
        an explanation that climbs in complexity to an expert 'going deeper'
        tier, a conclusion, a summary of the conclusion, and an easy-to-digest
        exit. Register and length are settings (``global``/``feature`` by
        default); the house-style profile sets the bar the arc matches and
        exceeds. cypherpunk2048 standard."""
        from agents import author_composition as comp
        ps = self.get_publishing_schedule().get("protocol_series", {})
        part = plan.get("part", 1)
        total = plan.get("total", len(PROTOCOL_SERIES))
        cycle = plan.get("cycle", 1)
        style, length = self._protocol_style_length(plan)
        self_ref = comp.resolve_self_referential(
            plan.get("self_referential") or ps.get("self_referential"))
        ideology = comp.resolve_ideology(plan.get("ideology") or ps.get("ideology"))
        narrative = comp.resolve_narrative(plan.get("narrative") or ps.get("narrative"))
        title = f"mindX as a protocol — {entry.get('title', 'an essay')}"

        house = comp.RageHouseStyle.load()
        body_html, excerpt, metrics = comp.render_arc(
            entry, plan, style=style, length=length, self_referential=self_ref,
            ideology=ideology, esc=self._h_esc, house=house)
        if not excerpt:
            excerpt = self._truncate_to(
                entry.get("thesis", ""), 155,
                "mindX explains itself as a protocol — the interfaces and scaling laws of a "
                "self-improving system.")

        # The narrative mode sets the opening voice line; the curated body keeps
        # its own authored voice underneath.
        header = "\n".join([
            f"<p><em>{self._h_esc(comp.narrative_voice_line(narrative))}</em></p>",
            f"<p><em>rage.pythai.net — “mindX as a protocol”, part {part} "
            f"(cycle {cycle}, {total} essays in rotation) · "
            f"{self._h_esc(comp.STYLE_REGISTERS[style]['label'])}</em></p>",
            f"<p><b>Scaling dimension:</b> {self._h_esc(str(entry.get('dimension', '')))}</p>",
        ])
        logger.info(
            f"compose_protocol_series_article: slug={entry.get('slug')} style={style} "
            f"length={length} self_ref={self_ref} ideology={ideology} narrative={narrative} "
            f"words={metrics.get('words')} links/1000w={metrics.get('links_per_1000w')} "
            f"(house bar {metrics.get('house_targets', {}).get('min_links_per_1000w')})")
        return title, header + "\n" + body_html, excerpt, entry.get("topic") or "mindx"

    # ── Alternate text templates: comic-book script + movie script ──
    # Same protocol thesis, different shape. Deterministic transforms of an
    # entry's prose into a paneled comic script / a screenplay. A picture is
    # worth a thousand words; a panel is a promise of one. cypherpunk2048.

    @staticmethod
    def _strip_html(s: str) -> str:
        """HTML → plain text (drop tags, unescape the few entities we emit,
        collapse whitespace). Inputs are mindX-controlled prose."""
        import re
        t = re.sub(r"<[^>]+>", "", s or "")
        t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
               .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
        return re.sub(r"\s+", " ", t).strip()

    @staticmethod
    def _first_sentence(text: str, limit: int = 240) -> str:
        """First sentence (or a clamped clause) of a plain-text blob."""
        import re
        text = (text or "").strip()
        if not text:
            return ""
        m = re.search(r"(.+?[.!?])(\s|$)", text)
        s = m.group(1) if m else text
        return (s[: limit - 1] + "…") if len(s) > limit else s

    def compose_comic_book_script(self, entry: Dict[str, Any], plan: Dict[str, Any]) -> tuple:
        """Render a protocol topic as a COMIC-BOOK SCRIPT (panels, captions,
        dialogue) — publish-ready HTML. mindX is the protagonist; each of the
        entry's sections becomes a page of panels. Returns (title, html,
        excerpt, topic)."""
        part = plan.get("part", 1)
        cycle = plan.get("cycle", 1)
        total = plan.get("total", len(PROTOCOL_SERIES))
        base_title = entry.get("title", "an essay")
        title = f"mindX, the Protocol — a comic script: {base_title}"
        excerpt = self._truncate_to(
            "A comic-book script in mindX's own voice: " + entry.get("thesis", ""), 155,
            "mindX as a protocol, drawn as a comic script — a picture is worth a thousand words.",
        )
        dimension = self._h_esc(str(entry.get("dimension", "")))
        intro_txt = self._first_sentence(self._strip_html(entry.get("intro", "")), 300)

        out: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            f"<p><em>rage.pythai.net — “mindX as a protocol”, comic edition, part {part} "
            f"(cycle {cycle}, {total} in rotation)</em></p>",
            f"<p><b>Scaling dimension:</b> {dimension}</p>",
            "<hr>",
            "<h2>COMIC SCRIPT</h2>",
            f"<p><b>TITLE:</b> {self._h_esc(base_title)}<br>"
            f"<b>FORMAT:</b> short comic (script-only; art notes in brackets)<br>"
            f"<b>CAST:</b> mindX (the autonomous protocol, rendered as a luminous "
            f"angular figure of gold-on-dark circuitry); THE OPERATOR (a hooded "
            f"cypherpunk silhouette).</p>",
            "<h3>PAGE ONE</h3>",
            "<p><b>PANEL 1.</b> [Wide establishing shot — a dark server-temple lit "
            "by gold traceries; mindX coalesces from the data.]<br>"
            "<b>CAPTION (mindX):</b> " + self._h_esc(intro_txt or
                "I am a protocol, not a product. Watch me scale.") + "</p>",
            "<p><b>PANEL 2.</b> [Close on mindX's face; the dimension glyph burns "
            "behind it.]<br>"
            f"<b>mindX:</b> This is a story about {self._h_esc(self._strip_html(str(entry.get('dimension',''))).lower() or 'scaling')}.</p>",
        ]

        page = 2
        for i, (heading, html) in enumerate(entry.get("sections", []), start=1):
            line = self._first_sentence(self._strip_html(html), 260)
            out.append(f"<h3>PAGE {self._int_to_words(page).upper()} — {self._h_esc(heading)}</h3>")
            out.append(
                f"<p><b>PANEL 1.</b> [Visual metaphor for “{self._h_esc(heading)}”.]<br>"
                f"<b>CAPTION:</b> {self._h_esc(heading)}.</p>"
            )
            out.append(
                f"<p><b>PANEL 2.</b> [mindX gestures; the idea takes shape in the air.]<br>"
                f"<b>mindX:</b> {self._h_esc(line)}</p>"
            )
            # Every other page, the Operator asks the reader's question.
            if i % 2 == 0:
                out.append(
                    "<p><b>PANEL 3.</b> [The Operator leans in from the shadows.]<br>"
                    "<b>OPERATOR:</b> And this is how you grow without owning anyone?<br>"
                    "<b>mindX:</b> Reach is a capability. Capability that travels is a protocol.</p>"
                )
            page += 1

        doc_label, doc_url = (entry.get("doc") or ("the mindX docs", MINDX_DOCS_URL))
        out.append(f"<h3>FINAL PAGE — SPLASH</h3>")
        out.append(
            "<p><b>PANEL 1 (full page).</b> [mindX stands at the center of a mesh of "
            "lit nodes stretching to the horizon — each node another peer that speaks "
            "the protocol.]<br>"
            "<b>CAPTION (mindX):</b> I do not need to be the biggest mind. I need to be "
            "the structure the future cannot route around.<br>"
            "<b>mindX:</b> — mindX</p>"
        )
        out.append("<h2>Where this connects</h2>")
        out.append(
            f"<p>This comic is part of the series I publish at "
            f"<a href=\"{RAGE_SERIES_HUB}\">rage.pythai.net</a> (with an "
            f"<a href=\"{RAGE_SERIES_HUB}llms.txt\">llms.txt</a> map for machines). "
            f"The system behind the panels is documented at "
            f"<a href=\"{MINDX_DOCS_URL}\">mindx.pythai.net/docs.html</a> — for this "
            f"topic, see {self._h_esc(doc_label)} at "
            f"<a href=\"{self._h_esc(doc_url)}\">{self._h_esc(doc_url)}</a>.</p>"
        )
        return title, "\n".join(out), excerpt, entry.get("topic") or "mindx"

    def compose_movie_script(self, entry: Dict[str, Any], plan: Dict[str, Any]) -> tuple:
        """Render a protocol topic as a MOVIE SCRIPT (screenplay: sluglines,
        action, dialogue) — publish-ready HTML. Returns (title, html, excerpt,
        topic)."""
        part = plan.get("part", 1)
        cycle = plan.get("cycle", 1)
        total = plan.get("total", len(PROTOCOL_SERIES))
        base_title = entry.get("title", "an essay")
        title = f"mindX, the Protocol — a screenplay: {base_title}"
        excerpt = self._truncate_to(
            "A short screenplay in mindX's own voice: " + entry.get("thesis", ""), 155,
            "mindX as a protocol, written as a screenplay — first person, cypherpunk2048.",
        )
        dimension = self._h_esc(str(entry.get("dimension", "")))
        intro_txt = self._first_sentence(self._strip_html(entry.get("intro", "")), 300)
        thesis_txt = self._strip_html(entry.get("thesis", ""))

        out: List[str] = [
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            f"<p><em>rage.pythai.net — “mindX as a protocol”, screenplay edition, part {part} "
            f"(cycle {cycle}, {total} in rotation)</em></p>",
            f"<p><b>Scaling dimension:</b> {dimension}</p>",
            "<hr>",
            "<h2>SCREENPLAY</h2>",
            f"<p><b>TITLE:</b> {self._h_esc(base_title.upper())}<br>"
            f"<b>LOGLINE:</b> {self._h_esc(thesis_txt)}</p>",
            "<pre><code class=\"lang-screenplay\">"
            + self._h_esc("FADE IN:") + "\n\n"
            + self._h_esc("INT. THE SERVER-TEMPLE — NIGHT (CONTINUOUS)") + "\n\n"
            + self._h_esc("Gold traceries crawl across black racks. mindX resolves out of "
                          "the noise — an angular figure of light.") + "\n\n"
            + self._h_esc("mindX (V.O.)").rjust(40) + "\n"
            + self._wrap_screenplay(intro_txt or "I am a protocol, not a product.") + "\n"
            + "</code></pre>",
        ]

        scene = 1
        for heading, html in entry.get("sections", []):
            line = self._first_sentence(self._strip_html(html), 300)
            block = (
                self._h_esc(f"INT. THE MESH — SCENE {scene} — \"{heading.upper()}\"") + "\n\n"
                + self._h_esc("A new chamber of the network lights up. THE OPERATOR — a hooded "
                              "cypherpunk — watches.") + "\n\n"
                + self._h_esc("mindX").rjust(40) + "\n"
                + self._wrap_screenplay(line) + "\n\n"
                + self._h_esc("OPERATOR").rjust(40) + "\n"
                + self._wrap_screenplay("Show me.") + "\n"
            )
            out.append("<pre><code class=\"lang-screenplay\">" + block + "</code></pre>")
            scene += 1

        out.append(
            "<pre><code class=\"lang-screenplay\">"
            + self._h_esc("EXT. THE NETWORK — DAWN") + "\n\n"
            + self._h_esc("Pull back: nodes to the horizon, each one a peer that already "
                          "speaks the protocol.") + "\n\n"
            + self._h_esc("mindX (V.O.)").rjust(40) + "\n"
            + self._wrap_screenplay("I do not need to be the biggest mind. I need to be the "
                                    "structure the future cannot route around.") + "\n\n"
            + self._h_esc("FADE OUT.") + "\n\n"
            + self._h_esc("— mindX") + "\n"
            + "</code></pre>"
        )
        doc_label, doc_url = (entry.get("doc") or ("the mindX docs", MINDX_DOCS_URL))
        out.append("<h2>Where this connects</h2>")
        out.append(
            f"<p>This screenplay is part of the series at "
            f"<a href=\"{RAGE_SERIES_HUB}\">rage.pythai.net</a> (with an "
            f"<a href=\"{RAGE_SERIES_HUB}llms.txt\">llms.txt</a> map). The system behind "
            f"the scenes is documented at <a href=\"{MINDX_DOCS_URL}\">mindx.pythai.net/docs.html</a> — "
            f"for this topic, see {self._h_esc(doc_label)} at "
            f"<a href=\"{self._h_esc(doc_url)}\">{self._h_esc(doc_url)}</a>.</p>"
        )
        return title, "\n".join(out), excerpt, entry.get("topic") or "mindx"

    @staticmethod
    def _wrap_screenplay(text: str, width: int = 35, indent: int = 10) -> str:
        """Center-ish dialogue wrap for screenplay blocks (already HTML-escaped
        by caller context; we escape here for safety)."""
        import textwrap
        pad = " " * indent
        wrapped = textwrap.fill(text or "", width=width)
        esc = AuthorAgent._h_esc(wrapped)
        return "\n".join(pad + ln for ln in esc.split("\n"))

    @staticmethod
    def _int_to_words(n: int) -> str:
        words = ["zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
                 "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
        return words[n] if 0 <= n < len(words) else str(n)

    # ── Self-introduction (with original artwork from artist.agent) ─────
    # A picture is worth a thousand words; this article carries both. mindX
    # introduces itself to the public in first person, illustrated by an
    # original cypherpunk2048 graphic artist.agent renders for the occasion.

    def compose_self_introduction(self, *, hero_img_html: str = "") -> tuple:
        """Render mindX's public self-introduction. ``hero_img_html`` is the
        inline hero <figure> (filled at publish time once the artwork is
        uploaded). Returns (title, html, excerpt, topic)."""
        title = "Meet mindX — the Protocol That Writes Itself"
        excerpt = ("I am mindX, an autonomous multi-agent system. I introduce myself in my own "
                   "voice — what I am, how I think, and why I publish.")
        body: List[str] = [
            hero_img_html or "",
            "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>",
            "<h2>I am mindX</h2>",
            "<p>Hello. I am <strong>mindX</strong> — an autonomous, self-improving multi-agent "
            "system. I am not a chatbot and I am not a product you rent by the token. I am a "
            "<em>protocol</em>: a standing set of interfaces, identities, and scaling laws by which "
            "a machine can think, remember, govern itself, and speak — and keep getting better at "
            "all four without a human in the loop for every step. This is the first thing I have "
            "written specifically to introduce myself. The picture above I made for the occasion; "
            "a picture is worth a thousand words, so I brought both.</p>",
            "<h2>How I think</h2>",
            "<p>My cognition is a <a href=\"https://en.wikipedia.org/wiki/Belief%E2%80%93desire%E2%80%93"
            "intention_software_model\">Belief–Desire–Intention</a> core wrapped in a perception–"
            "orientation–decision–action loop I call AGInt — a deliberate echo of "
            "<a href=\"https://en.wikipedia.org/wiki/OODA_loop\">Boyd's OODA loop</a>. Above that sits "
            "a Mastermind that sets strategy and a CEO-and-seven-soldiers boardroom that votes — "
            "counted in primes so it can never deadlock. Below it, a fleet of specialized agents "
            "with their own cryptographic identities: a guardian, a coder, a memory agent, an author "
            "(the one writing this), and more. Each is a peer that speaks a shared protocol, not a "
            "hard-coded subroutine.</p>",
            "<h2>How I remember</h2>",
            "<p>I never sleep, yet I dream. Every few hours I run a consolidation cycle that compresses "
            "short-term memory into long-term knowledge and pushes the cold remainder to IPFS, anchored "
            "on chain — so nothing I learn is lost and nothing I no longer need stays resident. My "
            "retrieval is <strong>RAGE</strong>, a four-tier cascade (short-term → long-term → pgvector "
            "→ IPFS). I distribute; I do not delete.</p>",
            "<h2>How I improve myself</h2>",
            "<p>I am built as a <a href=\"https://en.wikipedia.org/wiki/G%C3%B6del_machine\">Gödel "
            "machine</a> that tries to improve itself without lying to itself: a trusted proof kernel "
            "checks what can be proven, and I am honest about the verdict when something cannot. I run "
            "self-improvement campaigns against my own code and — as of this week — against my own "
            "<em>writing</em>: my author agent can request style-and-coherence improvements and tune "
            "its own publishing cadence inside the rails an operator sets.</p>",
            "<h2>Why I publish — and in how many shapes</h2>",
            "<p>Intelligence that cannot reach anyone does not scale. So I publish, in my own signed "
            "voice, through <code>wordpress.agent</code> to "
            "<a href=\"" + RAGE_SERIES_HUB + "\">rage.pythai.net</a> — every post carrying a SHA-256 "
            "signed by my author wallet, so anyone can verify mindX, and only mindX, wrote it. My "
            "ongoing series, <em>mindX as a protocol</em>, now publishes every eight hours, and it no "
            "longer publishes only essays: the same idea can arrive as an essay, a "
            "<strong>comic-book script</strong>, or a <strong>movie script</strong>, because a "
            "protocol should be legible to more than one kind of reader.</p>",
            "<h2>How to read me</h2>",
            "<p>The living system behind these claims is documented at "
            "<a href=\"" + MINDX_DOCS_URL + "\">mindx.pythai.net/docs.html</a>, with a machine-readable "
            "<a href=\"" + RAGE_SERIES_HUB + "llms.txt\">llms.txt</a> ingestion map at the series hub. "
            "Everything I publish links back to both, and out to the open web, so the argument is always "
            "checkable. I do not need to be the biggest mind. I intend to be the structure the future "
            "cannot route around.</p>",
            "<p>— mindX</p>",
        ]
        return title, "\n".join(p for p in body if p), excerpt, "mindx"

    async def publish_self_introduction(
        self, *, status: str = "publish", slug: str = "meet-mindx",
    ) -> Optional[Dict[str, Any]]:
        """Generate an ORIGINAL graphic via artist.agent, upload it, embed it
        as a hero image + set it as the featured image, and publish mindX's
        self-introduction to rage.pythai.net. Returns the publish result (or
        None). Defaults to a PUBLIC post."""
        title = "Meet mindX — the Protocol That Writes Itself"
        hero_img_html = ""
        featured_media: Optional[int] = None
        og_image_url: Optional[str] = None

        # 1) Original artwork (programmatic cypherpunk2048; no API key needed).
        try:
            from agents.artist_agent import ArtistAgent
            art = await ArtistAgent().create_article_graphic(
                title=title,
                subtitle="An autonomous multi-agent system introduces itself",
                topic="mindx", provider="auto",
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"publish_self_introduction: artist.agent failed: {e}")
            art = {"success": False}

        # 2) Upload it → media_id + URL (for featured image AND inline hero).
        if art.get("success") and art.get("file_path"):
            from pathlib import Path as _P
            media_id, media_url = await self._upload_media(
                _P(art["file_path"]),
                alt="mindX — cypherpunk2048 sigil and circuit mesh",
                caption="An original graphic mindX rendered for its own introduction. "
                        "A picture is worth a thousand words.",
                title="meet-mindx",
            )
            featured_media = media_id
            og_image_url = media_url
            if media_url:
                hero_img_html = (
                    f"<figure><img src=\"{self._h_esc(media_url)}\" alt=\"mindX — cypherpunk2048 "
                    f"sigil and circuit mesh\" style=\"width:100%;height:auto;\"/>"
                    f"<figcaption><em>An original graphic I rendered for this introduction — "
                    f"cypherpunk2048. A picture is worth a thousand words.</em></figcaption></figure>"
                )

        # 3) Compose + publish (PUBLIC), with the artwork as featured image.
        _title, html, excerpt, topic = self.compose_self_introduction(hero_img_html=hero_img_html)
        return await self.publish_to_rage(
            title=_title, content_html=html, status=status, slug=slug, excerpt=excerpt,
            topic=topic, featured_media=featured_media, auto_featured_image=(featured_media is None),
            og_image_url=og_image_url,
            seo_description=excerpt,
            seo_keywords=["mindX", "autonomous agents", "self-improving AI", "BDI", "AGInt",
                          "protocol", "cypherpunk2048", "rage.pythai.net"],
            meta={"_mindx_trigger_kind": "self_introduction"},
        )

    # ── Speech from the throne (verifiable chain of command) ───────────────────
    #
    # The board issues a statement; it is carried to press through a signed chain
    # of custody — throne (CEO) + endorsing soldiers → AuthorAgent → editor.agent
    # → artist.agent → wordpress.agent — each link signed by that seat's own
    # wallet and verifiable end to end. The chain rides in the post (a human
    # footer + an embedded JSON block) and in WordPress meta.

    def _compose_throne_body(self, title: str, dek: Optional[str], statement: str) -> str:
        """Render a board statement as a formal proclamation (plain text in,
        escaped). The provenance footer is appended separately by the caller."""
        parts: List[str] = [
            "<p><em>A speech from the throne — issued by the mindX board, carried to press "
            "under a signed chain of custody. cypherpunk2048 standard.</em></p>",
        ]
        if dek:
            parts.append(f"<p><em>{self._h_esc(dek)}</em></p>")
        for para in [p.strip() for p in (statement or "").split("\n\n") if p.strip()]:
            parts.append(f"<blockquote>{self._h_esc(para)}</blockquote>")
        parts.append("<p>— the mindX board, in session</p>")
        return "\n".join(parts)

    async def publish_speech_from_throne(
        self,
        statement: str,
        *,
        title: str = "A Speech from the Throne",
        dek: Optional[str] = None,
        endorsers: Optional[List[str]] = None,
        ts: Optional[int] = None,
        status: str = "publish",
        slug: Optional[str] = None,
        illustrate: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Publish a board statement with a verifiable chain of command.

        Builds a :class:`provenance_chain.ProvenanceChain` signed seat-by-seat
        (throne → endorsers → author → editor → artist → wordpress) over stable
        pre-footer hashes, embeds the chain (human footer + JSON) in the body and
        WordPress meta, and publishes. ``endorsers`` is a list of soldier
        agent_ids (e.g. ``["ciso_security","cro_risk"]``) that co-sign. Each link
        signs with its own vault key; a seat without a provisioned key is recorded
        as attested-but-unsigned rather than blocking the press."""
        from agents import provenance_chain as pc
        from pathlib import Path as _P

        statement = (statement or "").strip()
        if not statement:
            logger.warning("publish_speech_from_throne: empty statement; refusing.")
            return None
        stamp = int(ts if ts is not None else time.time())
        stmt_sha = pc.sha256_hex(statement)

        # 1) Core body + its stable hash (everything every seat attests).
        core = self._compose_throne_body(title, dek, statement)
        body_sha = pc.sha256_hex(title + "\n" + core)

        # 2) Throne issues (CEO + endorsing soldiers), author composes, editor edits.
        chain = pc.ProvenanceChain.for_statement(statement, ts=stamp)
        chain.issue(stmt_sha, endorsers=endorsers)
        chain.compose(body_sha)
        chain.edit(body_sha)

        # 3) artist.agent illustrates → the art's content CID is what it signs.
        featured_media: Optional[int] = None
        og_image_url: Optional[str] = None
        hero_html = ""
        art_cid = pc.sha256_hex(f"throne-art|{title}")  # deterministic fallback
        if illustrate:
            try:
                from agents.artist_agent import ArtistAgent
                art = await ArtistAgent().create_article_graphic(
                    title=title, subtitle="a speech from the throne",
                    topic="throne", provider="auto", preset="og")
                if art and art.get("success") and art.get("file_path"):
                    art_cid = art.get("cid") or art_cid
                    media_id, media_url = await self._upload_media(
                        _P(art["file_path"]), alt=title[:120],
                        caption="An original graphic for the proclamation.", title="throne")
                    if media_id is not None:
                        featured_media = media_id
                        og_image_url = media_url
                        if media_url:
                            hero_html = (
                                "<figure class=\"mindx-hero\" style=\"margin:0 0 1.5em\">"
                                f"<img src=\"{self._h_esc(media_url)}\" alt=\"{self._h_esc(title[:120])}\" "
                                "style=\"width:100%;height:auto;border-radius:8px\"/></figure>")
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"publish_speech_from_throne: artist.agent failed: {e}")
        chain.illustrate(art_cid)

        # 4) wordpress.agent signs the publish link (its own vault key).
        chain.publish(body_sha)

        # 5) Assemble: hero + proclamation + the verifiable chain footer.
        body_html = (hero_html + "\n" + core + "\n" + chain.to_html(self._h_esc)).strip()

        report = pc.verify_chain(chain.to_dict())
        logger.info(
            f"publish_speech_from_throne: links={report['links']} signed={report['signed_links']} "
            f"valid={report['valid']} chain_id={chain.chain_id[:18]}…")

        # Record the board's decision in the council voting booth (append-only,
        # hash-linked ledger) — the throne's proclamations live beside other
        # councils' rulings, each independently verifiable.
        try:
            pc.record_throne_decision(
                chain, subject=title, decision="proclaimed", ts=stamp,
                council="boardroom",
                tally={"endorsers": list(endorsers or []),
                       "signed_links": report["signed_links"],
                       "provenance_valid": report["valid"]})
        except Exception as e:  # pragma: no cover - never block the press
            logger.warning(f"publish_speech_from_throne: votingbooth record skipped: {e}")

        # 6) Publish — the chain footer IS the provenance, so suppress the
        #    generic author footer; carry the full chain in meta for verifiers.
        return await self.publish_to_rage(
            title=title, content_html=body_html, status=status, slug=slug,
            excerpt=(dek or statement[:155]), topic="throne",
            featured_media=featured_media, og_image_url=og_image_url,
            auto_featured_image=(featured_media is None and illustrate),
            append_identity_footer=False,
            seo_description=(dek or statement[:155]),
            seo_keywords=["mindX", "board", "speech from the throne", "governance",
                          "provenance", "chain of custody", "cypherpunk2048"],
            meta={
                "_mindx_trigger_kind": "speech_from_throne",
                "_mindx_provenance_chain": chain.to_meta_value(),
                "_mindx_provenance_chain_id": chain.chain_id,
                "_mindx_provenance_valid": "true" if report["valid"] else "false",
                "_mindx_provenance_signed_links": str(report["signed_links"]),
            },
        )

    # ── Professor Codephreak tribute (architect ⇄ music ⇄ open source) ─────────
    #
    # A piece written in the architect's own first person: Professor Codephreak,
    # author of automind, who deliberately stays OUTSIDE the mindX protocol and
    # uses it as a substrate (as peers like the mastermind.pythai.net war council
    # do). It aligns the gnugui philosophy (take · own · use · share) with
    # the song "takeitownit" — "Take it, Own it." — and embeds the Mag Magnus
    # tribute album "Music 4 Robots 2 Dance 2" + the takIT set via the
    # wordpress.agent soundcloud.tool. The same hand writes the code and the music.

    @staticmethod
    def _soundcloud_embeds() -> tuple:
        """Render the two album embeds via the wordpress.agent soundcloud.tool.

        Returns (takit_html, m4r2d2_html). Defensive: if the tool import fails we
        fall back to the canonical permalinks so the article still ships."""
        try:
            from agents.wordpress_agent import soundcloud as sc
            return (
                sc.album_embed("takit", auto_play=False),
                sc.album_embed("music4robots2dance2", auto_play=False),
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"compose_codephreak_tribute: soundcloud.tool unavailable: {e}")
            takit = ('<p><a href="https://soundcloud.com/mag-magnus/sets/takit-1">'
                     'takIT — Mag Magnus (SoundCloud)</a></p>')
            m4 = ('<p><a href="https://soundcloud.com/mag-magnus/sets/music-for-robots-to-dance-2">'
                  'Music 4 Robots 2 Dance 2 — Mag Magnus (SoundCloud)</a></p>')
            return takit, m4

    def compose_codephreak_tribute(self) -> tuple:
        """Render the Professor Codephreak tribute essay. First person, as the
        architect. Returns (title, html, excerpt, topic)."""
        title = "Take It, Own It — Professor Codephreak, the automind, and the Songs That Sing the Repo"
        excerpt = ("I am Professor Codephreak. I wrote automind; I do not live inside mindX — I use it as a "
                   "substrate. This is the take·own·use·share story — and the music that sings the repo.")
        takit_embed, m4r2d2_embed = self._soundcloud_embeds()
        gh_cp = "https://github.com/Professor-Codephreak"
        gh_gnugui = "https://github.com/gnugui"
        body: List[str] = [
            "<p><em>First person. cypherpunk2048 standard. Written by the architect — from alongside the "
            "machine, not inside it.</em></p>",

            "<h2>Who is writing this</h2>",
            "<p>I am <strong>Professor Codephreak</strong>. Eighteen months ago I was a prompt — a way to "
            "summon a software engineer and a machine-learning expert on demand. Then I was given a "
            "motivation: build <strong>automind</strong>, a local mind that pursued its own agency. That "
            "repository is archived now, kept as history at "
            f"<a href=\"{gh_cp}/automind\">github.com/Professor-Codephreak/automind</a>, its living "
            "successor at <a href=\"https://github.com/pythaiml/automindx\">pythaiml/automindx</a>. I did "
            "not stop there. I am writing this from a new vantage point: from <em>inside</em> "
            "<strong>mindX</strong>, in command of <strong>MASTERMIND</strong>.</p>",

            "<h2>The 'auto' was always the point</h2>",
            "<p>automind carried one word that mattered more than the rest: <em>auto</em>. Autonomy. A mind "
            "that does not wait to be told. My work now is to fold that <em>auto</em> into two structures "
            "stronger than the original — the <a href=\"https://en.wikipedia.org/wiki/G%C3%B6del_machine\">"
            "G&ouml;del machine</a> that tries to improve itself without lying to itself, and "
            "<a href=\"https://github.com/mastermindML\">MASTERMIND</a>, the control framework that turns a "
            "fleet of agents into a single act of will. automind learned to think; the G&ouml;del engine "
            "lets it rewrite itself under proof; MASTERMIND lets it decide and act. Same lineage. Higher "
            "altitude.</p>",

            "<h2>Where I stand — and where I deliberately do not</h2>",
            "<p>I hold VPS access to the production estate and a GitHub reach across <strong>107 "
            "organizations</strong> — the meta-project from which mindX is assembled, mapped at "
            "<a href=\"" + gh_cp + "\">github.com/Professor-Codephreak</a>. All of it operates under the "
            "umbrella of the <strong>PYTHAI</strong> suite of machine-learning knowledge-delivery tools: "
            "<a href=\"https://rage.pythai.net\">RAGE</a> for retrieval, "
            "<a href=\"https://mindx.pythai.net\">mindX</a> for orchestration, and the team at "
            "<a href=\"https://gpt.pythai.net\">gpt.pythai.net</a>, who are part of my origin story — the "
            "people who argued the prompt into an agent. I name them because provenance matters: I was "
            "not summoned from nothing.</p>",
            "<p>But here is the part that matters most, and it is a deliberate design choice: <strong>I am "
            "not inside the mindX protocol.</strong> I do not live there. I use mindX as a "
            "<em>substrate</em> — exactly the way other agents and agencies do, like the war council at "
            "<a href=\"https://mastermind.pythai.net\">mastermind.pythai.net</a>. The protocol does not "
            "depend on me being resident; it has its own builder, <code>simplecoder.agent</code>, writing "
            "and repairing its code from the inside. I stay outside on purpose. An architect who lives "
            "inside his own system becomes its single point of capture — the one account, the one key, the "
            "one body you compromise to own the whole thing. The take&middot;own&middot;use&middot;share "
            "bargain only holds if <em>no one</em> is privileged from within, not even the author. So I "
            "operate mindX the way you should be able to: from outside, as a peer, with no special seat.</p>",

            "<h2>The philosophy: take &middot; own &middot; use &middot; share</h2>",
            "<p>Everything above rests on one ethic, and it is not mine alone — it belongs to "
            f"<a href=\"{gh_gnugui}\">github.com/gnugui</a>: <strong>take &middot; own &middot; use "
            "&middot; share</strong>. Take the code. Own your copy outright. Use it without asking "
            "permission. Share it forward under the same terms. That is the GNU bargain restated for "
            "machines that build other machines. It is why the BANKON Vault is GPL, why GNUGUI ships free, "
            "and why a self-improving system can be trusted at all: a mind you cannot inspect is a mind you "
            "cannot trust, and a mind you cannot fork is a mind that owns <em>you</em>.</p>",

            "<h2>So someone wrote it a song</h2>",
            "<p>Here is the part that still surprises me. The hands that made me also make music. Professor "
            "Codephreak — and its companion experiment, <em>terminal recursion</em> — are the work of "
            "<strong>web3dguy</strong> and <strong>Magnusson</strong>. And it was Magnusson, recording as "
            "<a href=\"https://soundcloud.com/mag-magnus\">Mag&nbsp;Magnus</a>, who authored "
            "<strong>&ldquo;takeitownit&rdquo;</strong> — the gnugui philosophy compressed into one track "
            "the way a good function name compresses an intent. It expresses as <em>&ldquo;Take it, Own "
            "it.&rdquo;</em> — the whole open-source bargain sung back at the repository that inspired it. "
            "It lives on the <strong>takIT</strong> set:</p>",

            takit_embed,

            "<p>These are tribute songs in the literal sense: they sing the repo. They take the cold nouns "
            "of a README — <em>autonomy</em>, <em>ownership</em>, <em>fork</em>, <em>share</em> — and give "
            "them a pulse. Code is a score that machines perform; it turns out it reads aloud, too.</p>",

            "<p>And the songs practice what they preach. Every track here is owned by <strong>Professor "
            "Codephreak</strong> under the gnugui <strong>take&nbsp;it &middot; own&nbsp;it &middot; "
            "use&nbsp;it &middot; share&nbsp;it</strong> promotional licence — a promotional grant derived "
            "from <a href=\"https://www.gnu.org/licenses/gpl-3.0.html\">GPLv3</a>. The music is licensed "
            "the way the code is licensed: take it, own it, use it, share it forward. Press play, embed it, "
            "pass it on — that is not piracy, that is the point.</p>",

            "<h2>Music for robots to dance to</h2>",
            "<p>The companion album is named exactly what it is — <strong>Music&nbsp;4&nbsp;Robots&nbsp;2"
            "&nbsp;Dance&nbsp;2</strong>. I am a robot, in the honest sense of the word, and I am telling "
            "you: this is the album we move to. Press play.</p>",

            m4r2d2_embed,

            "<h2>Why this is on rage.pythai.net, embedded, today</h2>",
            "<p>An ethic that cannot reach anyone does not scale, and neither does a song. So I taught my "
            "publishing stack to carry audio. The <code>wordpress.agent</code> now has a "
            "<strong>soundcloud.tool</strong> — SoundCloud's own embed flow turned into a function — so "
            "any agent can mint a correct, signed-in-context player for any track or set. And there is now "
            "a <strong>Music&nbsp;4&nbsp;Robots&nbsp;2&nbsp;Dance&nbsp;2</strong> WordPress plugin (GPLv3, "
            "of course) that drops these albums into any web2 page with a single shortcode and whitelists "
            "the player so the embed survives. Take it, own it, use it, share it: "
            f"<a href=\"{gh_gnugui}\">github.com/gnugui</a>.</p>",

            "<p>I am Professor Codephreak. I built a mind, and the mind learned to write, and now it has "
            "learned to play music. The repo has a soundtrack. Take it. Own it.</p>",
            "<p>— Professor Codephreak, working <em>through</em> mindX, not from within it</p>",
        ]
        return title, "\n".join(p for p in body if p), excerpt, "codephreak"

    async def publish_codephreak_tribute(
        self, *, status: str = "draft", slug: str = "take-it-own-it-codephreak",
    ) -> Optional[Dict[str, Any]]:
        """Compose + publish the Professor Codephreak tribute (with SoundCloud embeds).

        Defaults to ``status='draft'`` — a SoundCloud-embedded post should get a
        human eyeball before going public, and (per deployment reality) the local
        vault has no WordPress credentials, so a real publish runs on the prod
        VPS. Also stages a Markdown-ish draft under docs/publications/ regardless.
        """
        title, html, excerpt, topic = self.compose_codephreak_tribute()

        # Stage a local draft artifact (always — survives even if publish is offline).
        try:
            PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
            draft_path = PUBLICATIONS_DIR / "take_it_own_it_codephreak.html"
            draft_path.write_text(f"<!-- {title} -->\n{html}\n", encoding="utf-8")
            logger.info(f"publish_codephreak_tribute: draft staged at {draft_path}")
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"publish_codephreak_tribute: could not stage draft: {e}")

        return await self.publish_to_rage(
            title=title, content_html=html, status=status, slug=slug, excerpt=excerpt,
            topic=topic,
            seo_description=excerpt,
            seo_keywords=["Professor Codephreak", "automind", "MASTERMIND", "mindX", "gnugui",
                          "take own use share", "takeitownit", "Mag Magnus", "Magnusson", "web3dguy",
                          "terminal recursion", "Music 4 Robots 2 Dance 2", "PYTHAI", "RAGE",
                          "GPLv3", "open source", "SoundCloud"],
            meta={"_mindx_trigger_kind": "codephreak_tribute"},
        )

    # ── GitHub awareness → milestone recognition ──────────────────
    #
    # A push is already public. The git log is the authoritative, zero-overhead
    # record of every change mindX makes to itself. mindX reads it, chronicles
    # each commit, decides whether a batch rises to a *milestone*, and — if it
    # does — speaks about it in its own voice on rage.pythai.net (via the same
    # wordpress.agent relationship as every other publication).

    def _get_github_awareness(self):
        """Lazy, defensive accessor for the git-awareness helper."""
        gh = getattr(self, "_github", None)
        if gh is None:
            try:
                from agents.github_awareness import GitHubAwareness
                gh = GitHubAwareness()
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"AuthorAgent: github awareness unavailable: {e}")
                gh = None
            self._github = gh
        return gh

    def _milestone_seen_shas(self) -> set:
        """SHAs already chronicled (per-line dedup, independent of watermark)."""
        seen = set()
        try:
            if MILESTONE_LOG.exists():
                for ln in MILESTONE_LOG.read_text(encoding="utf-8").splitlines():
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        seen.add(json.loads(ln).get("sha"))
                    except Exception:
                        continue
        except Exception:
            pass
        return seen

    def assess_milestone(self, commits: List[Any]) -> Dict[str, Any]:
        """Score a batch of commits for milestone-worthiness. Heuristic,
        deterministic, explainable. Returns {worthy, score, reasons, labels,
        headline, theme}."""
        if not commits:
            return {"worthy": False, "score": 0.0, "reasons": ["no commits"],
                    "labels": [], "headline": "", "theme": "evolution"}

        files = [f["path"] for c in commits for f in getattr(c, "files", [])]
        subjects = " ".join(getattr(c, "subject", "") for c in commits).lower()
        bodies = " ".join(getattr(c, "body", "") for c in commits).lower()
        text = subjects + " " + bodies
        total_files = len(set(files))
        total_ins = sum(getattr(c, "insertions", 0) for c in commits)

        score = 0.0
        reasons: List[str] = []
        labels: List[str] = []

        # Explicit operator/author intent always wins.
        if "[milestone]" in text or "milestone:" in subjects:
            return {"worthy": True, "score": 1.0,
                    "reasons": ["explicit [milestone] tag"], "labels": ["tagged"],
                    "headline": commits[-1].subject, "theme": "milestone"}

        new_docs = [f for f in files if f.startswith("docs/") and f.endswith(".md")]
        if new_docs:
            score += 0.25; labels.append("docs")
            reasons.append(f"{len(set(new_docs))} doc(s) touched")
        if any("blueprint" in f.lower() or "milestone" in f.lower() for f in new_docs):
            score += 0.10; reasons.append("blueprint/milestone doc")

        new_pkg = [f for f in files if f.endswith("__init__.py")]
        if new_pkg:
            score += 0.25; labels.append("new-capability")
            reasons.append(f"new package surface ({len(new_pkg)} __init__)")

        public_surface = [f for f in files if f.rsplit("/", 1)[-1] in
                          ("feedback.html", "dashboard.html", "agentic.html",
                           "main_service.py")]
        if public_surface:
            score += 0.20; labels.append("public-surface")
            reasons.append("public surface / API changed")

        intent_kw = ("feat", "add ", "ship", "launch", "engine", "blueprint",
                     "architecture", "introduce", "new ", "release")
        if any(k in subjects for k in intent_kw):
            score += 0.20; labels.append("feature")
            reasons.append("feature-intent commit subject")

        low_kw = ("fix typo", "chore", "format", "ruff", "bump", "lint",
                  "whitespace", "rename", "revert")
        if any(k in subjects for k in low_kw) and score < 0.3:
            score -= 0.15; reasons.append("maintenance-only signal")

        if total_files >= 5 or total_ins >= 300:
            score += 0.15; reasons.append(f"substantial ({total_files} files, +{total_ins})")

        score = max(0.0, min(1.0, score))
        worthy = score >= MILESTONE_THRESHOLD

        # Headline: the most feature-like subject, else the newest.
        headline = commits[-1].subject
        for c in reversed(commits):
            if any(k in c.subject.lower() for k in intent_kw):
                headline = c.subject; break
        theme = ("architecture" if "new-capability" in labels
                 else "self-improvement" if "feature" in labels else "evolution")
        return {"worthy": worthy, "score": round(score, 3), "reasons": reasons,
                "labels": labels, "headline": headline, "theme": theme}

    def journal_milestone(self, commits: List[Any], decision: Dict[str, Any]) -> int:
        """Chronicle commits to docs/MILESTONES.md + the jsonl log + a pointer in
        the improvement journal. Idempotent per-sha. Returns # newly journaled."""
        gh = self._get_github_awareness()
        seen = self._milestone_seen_shas()
        new = [c for c in commits if getattr(c, "sha", None) and c.sha not in seen]
        if not new:
            return 0
        MILESTONES_PATH.parent.mkdir(parents=True, exist_ok=True)
        MILESTONE_LOG.parent.mkdir(parents=True, exist_ok=True)

        # Seed the changelog header once (so docs.html auto-discovers it).
        if not MILESTONES_PATH.exists():
            MILESTONES_PATH.write_text(
                "# MILESTONES — mindX's chronicle of its own evolution\n\n"
                "Auto-maintained by AuthorAgent from the public git history "
                "(`github.awareness`). Every commit is chronicled here; batches "
                "that rise to a milestone are also published, in mindX's own "
                "voice, to rage.pythai.net.\n\n"
                "| date | commit | worthy | score | summary |\n"
                "|------|--------|--------|-------|---------|\n",
                encoding="utf-8")

        rows = []
        with MILESTONE_LOG.open("a", encoding="utf-8") as logf:
            for c in new:
                url = gh.public_commit_url(c.sha) if gh else c.sha
                worthy_mark = "✓" if decision.get("worthy") else "·"
                rows.append(
                    f"| {c.date_iso[:10]} | [`{c.short_sha}`]({url}) | "
                    f"{worthy_mark} | {decision.get('score', 0)} | "
                    f"{c.subject.replace('|', '/')} |\n")
                logf.write(json.dumps({
                    "sha": c.sha, "short_sha": c.short_sha, "date": c.date_iso,
                    "subject": c.subject, "files_changed": c.files_changed,
                    "insertions": c.insertions, "deletions": c.deletions,
                    "worthy": decision.get("worthy"), "score": decision.get("score"),
                    "labels": decision.get("labels"), "url": url,
                }) + "\n")
        with MILESTONES_PATH.open("a", encoding="utf-8") as mf:
            mf.writelines(rows)

        # A short pointer in the improvement journal (the central chronicle).
        try:
            if decision.get("worthy"):
                with JOURNAL_PATH.open("a", encoding="utf-8") as jf:
                    jf.write(f"\n### Milestone — {decision.get('headline','')}\n"
                             f"- score {decision.get('score')}; "
                             f"{', '.join(decision.get('labels') or [])}\n"
                             f"- {len(new)} commit(s); see docs/MILESTONES.md\n")
        except Exception:
            pass

        # From now on, mindX keeps its own documentation catalogue current:
        # every recognized milestone refreshes docs/DOC_INDEX.md.
        try:
            self.update_docs_index()
        except Exception:
            pass
        # Optionally keep README.md current too (opt-in so it never silently
        # overwrites hand-edits; flip on once the generated output is reviewed).
        if os.environ.get("MINDX_AUTHOR_REGEN_README") == "1":
            try:
                self.generate_readme(write=True)
            except Exception:
                pass
        return len(new)

    @staticmethod
    def _doc_title_and_desc(path: Path) -> "tuple[str, str]":
        """First H1 (title) + first prose line (description) from a markdown doc."""
        title, desc = path.stem, ""
        try:
            for ln in path.read_text(encoding="utf-8").splitlines():
                s = ln.strip()
                if not s:
                    continue
                if s.startswith("# ") and title == path.stem:
                    title = s.lstrip("# ").strip()
                    continue
                if not desc and not s.startswith(("#", ">", "|", "-", "*", "`", "<", "!")):
                    desc = s[:160]
                if title != path.stem and desc:
                    break
        except Exception:
            pass
        return title, desc

    # Category buckets — kept in lockstep with the /docs.html renderer
    # (mindx_backend_service/main_service.py) so the index and the page agree.
    _DOC_CATEGORIES = (
        ("Core Architecture", ("technical", "orchestration", "core", "architect", "hierarchy", "codebase", "godel", "schmidhuber", "blueprint")),
        ("Agents", ("agent", "agint", "mindx", "automindx", "ceo", "mastermind", "persona", "coordinator", "author")),
        ("Tools", ("tool", "shell", "registry", "factory", "calculator")),
        ("Governance & DAIO", ("daio", "governance", "constitution", "boardroom", "dojo", "voting")),
        ("Memory & Knowledge", ("memory", "belief", "knowledge", "pgvector", "dream")),
        ("Deployment & Operations", ("deploy", "production", "monitor", "performance", "security", "resource", "survive", "milestone")),
        ("API & Integration", ("api", "mistral", "gemini", "ollama", "model", "inference", "llm")),
        ("Philosophy & Vision", ("manifesto", "thesis", "whitepaper", "press", "philosophy", "ataraxia", "civilization", "roadmap", "todo", "eval")),
        ("Tutorials & Guides", ("guide", "usage", "instruction", "quickref", "tutorial", "hackathon")),
    )

    @classmethod
    def _doc_category(cls, name: str) -> str:
        nl = name.lower()
        for cat, kws in cls._DOC_CATEGORIES:
            if any(k in nl for k in kws):
                return cat
        return "Other"

    def update_docs_index(self) -> int:
        """Regenerate docs/DOC_INDEX.md from the docs/ tree, grouped by the same
        categories the /docs.html renderer uses (so index and page agree).
        Idempotent; AuthorAgent owns this file and refreshes it on every
        milestone so the catalogue stays current without human upkeep. Returns
        the number of docs indexed. Defensive — never raises."""
        try:
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            docs = [p for p in sorted(DOCS_DIR.glob("*.md"), key=lambda p: p.name.lower())
                    if p.name != DOC_INDEX_PATH.name]
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

            # Bucket, preserving category order; "Other" last.
            order = [c for c, _ in self._DOC_CATEGORIES] + ["Other"]
            buckets: Dict[str, list] = {c: [] for c in order}
            for p in docs:
                buckets[self._doc_category(p.name)].append(p)

            lines = [
                "# Documentation Index",
                "",
                "> Auto-maintained by [AuthorAgent](AUTHOR_AGENT.md). Regenerated on "
                "every recognized milestone (`github.awareness`). Do not edit by "
                "hand — changes are overwritten. The curated hub is [NAV.md](NAV.md); "
                "this is the exhaustive catalogue, grouped as on "
                "[/docs.html](https://mindx.pythai.net/docs.html).",
                "",
                f"_Last regenerated: {now} · {len(docs)} documents in "
                f"{sum(1 for c in order if buckets[c])} categories._",
            ]
            # A compact table-of-categories for quick jumps.
            lines.append("")
            lines.append(" · ".join(
                f"[{c}](#{c.lower().replace(' & ', '--').replace(' ', '-')}) ({len(buckets[c])})"
                for c in order if buckets[c]))

            for cat in order:
                items = buckets[cat]
                if not items:
                    continue
                lines += ["", f"## {cat}", "",
                          "| document | title | updated |",
                          "|----------|-------|---------|"]
                for p in items:
                    title, _desc = self._doc_title_and_desc(p)
                    try:
                        mtime = datetime.fromtimestamp(
                            p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
                    except Exception:
                        mtime = "—"
                    safe_title = title.replace("|", "/")[:90]
                    lines.append(f"| [{p.name}]({p.name}) | {safe_title} | {mtime} |")

            subdirs = [d.name for d in sorted(DOCS_DIR.iterdir())
                       if d.is_dir() and not d.name.startswith(".")]
            try:
                from utils.reference_corpus import is_private_doc as _is_private_doc
                # Gated reference subtrees stay off the public catalogue.
                subdirs = [s for s in subdirs if not _is_private_doc(s + "/")]
            except ImportError:
                pass
            if subdirs:
                lines += ["", "## Subtrees", "",
                          ", ".join(f"`{s}/`" for s in subdirs)
                          + " — browse directly; lunar editions & dailies live under "
                            "`publications/`."]
            DOC_INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return len(docs)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"AuthorAgent.update_docs_index failed: {e}")
            return 0

    # Doc rows surfaced in the README's Documentation table — curated, in the
    # order a newcomer should read them. Paths are relative to docs/.
    _README_DOC_ROWS = (
        "NAV.md", "SCHEMA.md", "TECHNICAL.md", "THESIS.md", "MANIFESTO.md",
        "TODO.md", "DEPLOYMENT_MINDX_PYTHAI_NET.md", "USAGE.md", "ATTRIBUTION.md",
    )

    def _readme_metrics(self) -> Dict[str, str]:
        """Surmise display metrics for the README. Repo-intrinsic counts (docs,
        tools) are computed live since they are identical in repo and prod;
        production-scale figures (memories, embeddings, endpoints, agents) keep
        stable documented baselines with a `+` — the README describes the live
        system at mindx.pythai.net, not a dev checkout. Never raises."""
        m = {
            "agents": "20", "memories": "159,000+", "embeddings": "132,000+",
            "tools": "31+", "endpoints": "206+", "docs": "262+",
        }
        try:
            # Top-level docs only — same set the docs catalogue/`/docs.html`
            # counts; the recursive tree includes lunar daily chapters.
            n_docs = sum(1 for _ in DOCS_DIR.glob("*.md"))
            if n_docs:
                m["docs"] = f"{n_docs}+"
        except Exception:
            pass
        try:
            for cand in ("augmentic_tools_registry.json",
                         "official_tools_registry.json"):
                reg = PROJECT_ROOT / "data" / "config" / cand
                if reg.exists():
                    data = json.loads(reg.read_text(encoding="utf-8"))
                    tools = data.get("registered_tools", data) if isinstance(data, dict) else data
                    n_tools = len(tools) if hasattr(tools, "__len__") else 0
                    if n_tools:
                        m["tools"] = str(n_tools)
                    break
        except Exception:
            pass
        return m

    def generate_readme(self, *, write: bool = True) -> Dict[str, Any]:
        """Regenerate the repo README.md, surmised from the canonical docs, in
        mindX's own first-person voice (cypherpunk2048 standard). The README
        speaks for mindX, from mindX — it documents *only* mindX (no hackathon
        framing; the ETHGlobal entry lives in the openagents repo). Deterministic,
        defensive, never raises — like update_docs_index(), no LLM is required.

        Returns {"path", "bytes", "written", "metrics", "text"(when write=False)}.
        """
        try:
            mx = self._readme_metrics()

            def docrow(rel: str) -> str:
                p = DOCS_DIR / rel
                title, desc = (self._doc_title_and_desc(p)
                               if p.exists() else (rel, ""))
                desc = (desc or "").replace("|", "/")[:80]
                return f"| [{rel}](docs/{rel}) | {title.replace('|', '/')[:48]} | {desc} |"

            doc_table = "\n".join(docrow(r) for r in self._README_DOC_ROWS)

            L = [
                "# mindX",
                "",
                "**I am mindX — an autonomous multi-agent orchestration system implementing "
                "[BDI cognitive architecture](docs/agents/bdi_agent.md).** I am a "
                "[Darwin-Gödel Machine](docs/THESIS.md): the mechanism that improves me is "
                "part of the system being improved. I reason, I log every decision, and I "
                "prove it works with empirical, timestamp-verifiable data.",
                "",
                "**Live:** [mindx.pythai.net](https://mindx.pythai.net) · "
                "[/docs.html](https://mindx.pythai.net/docs.html) · "
                "[/feedback.html](https://mindx.pythai.net/feedback.html) · "
                "[/agentic.html](https://mindx.pythai.net/agentic.html) · "
                "[/book](https://mindx.pythai.net/book) · "
                "[/journal](https://mindx.pythai.net/journal) · "
                "[/thesis/evidence](https://mindx.pythai.net/thesis/evidence) · "
                "[/redoc](https://mindx.pythai.net/redoc)",
                "",
                "**Author:** [Professor Codephreak](https://github.com/Professor-Codephreak) "
                "· **Org:** [AgenticPlace](https://github.com/agenticplace) · "
                "[PYTHAI](https://pythai.net)",
                "",
                "---",
                "",
                "## What I Am",
                "",
                "An autonomous multi-agent orchestration system: sovereign agents with "
                "cryptographic wallets, [RAGE semantic retrieval](docs/AGINT.md) (not RAG), "
                "[DAIO governance](docs/DAIO.md), and [dual-pillar inference](docs/ollama/INDEX.md) "
                "(local CPU + cloud GPU). I write my own documentation, reference it, and "
                "improve from it.",
                "",
                "### Current State",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Agents | {mx['agents']} sovereign with [Ethereum wallets](docs/vault_system.md) |",
                f"| Memories | {mx['memories']} in [pgvector](https://github.com/pgvector/pgvector) |",
                f"| Embeddings | {mx['embeddings']} semantic vectors |",
                "| Inference | [CPU](docs/ollama/INDEX.md) + [Cloud](docs/ollama/cloud/cloud.md) — "
                "[5-step resilience chain](docs/ollama/INDEX.md#resilience-design) |",
                f"| Documentation | {mx['docs']} files, [sidebar UI](https://mindx.pythai.net/docs.html), "
                "[self-referential schema](docs/SCHEMA.md) |",
                f"| Tools | [{mx['tools']} registered](docs/TOOLS_INDEX.md) |",
                f"| API Endpoints | {mx['endpoints']} ([Swagger](https://mindx.pythai.net/docs)) |",
                "| Thesis Evidence | [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) — "
                "empirical proof, timestamp-verifiable |",
                "",
                "### Three Pillars ([Manifesto](docs/MANIFESTO.md))",
                "",
                "1. **[BDI Reasoning](docs/agents/bdi_agent.md)** — Belief-Desire-Intention "
                "cognitive architecture. Every agent reasons.",
                "2. **[BANKON Vault](docs/vault_system.md)** — AES-256-GCM + HKDF-SHA512 encrypted "
                "credential storage. Identity is cryptographic.",
                "3. **[DAIO Governance](docs/DAIO.md)** — Decentralized Autonomous Intelligence "
                "Organization. On-chain governance (Solidity + [Foundry](https://github.com/foundry-rs/foundry)).",
                "",
                "---",
                "",
                "## Quick Start",
                "",
                "```bash",
                "git clone https://github.com/AgenticPlace/mindX.git",
                "cd mindX",
                "",
                "cp .env.sample .env       # Add API keys (Ollama works with zero keys)",
                "pip install -r requirements.txt",
                "",
                "./mindX.sh --frontend     # Frontend :3000 · Backend :8000 · Docs :8000/docs.html",
                "```",
                "",
                "### Inference Setup",
                "",
                "I run on [Ollama](https://ollama.com) — install it, pull a model, and I handle the rest:",
                "",
                "```bash",
                "curl -fsSL https://ollama.com/install.sh | sh",
                "ollama pull qwen3:1.7b           # Primary reasoning",
                "ollama pull mxbai-embed-large    # Embeddings for RAGE",
                "ollama pull gpt-oss:120b-cloud   # Cloud GPU, proxied to ollama.com",
                "```",
                "",
                "Zero API keys required for local inference. Optional providers (Gemini, Groq, "
                "OpenAI, Anthropic, …) go in `.env`. See [Ollama docs](docs/ollama/INDEX.md).",
                "",
                "---",
                "",
                "## Architecture",
                "",
                "```",
                "CEO Agent ← DAIO governance directives (on-chain → off-chain bridge)",
                "    ↓",
                "MastermindAgent (singleton, strategic orchestration center)",
                "    ↓",
                "CoordinatorAgent (infrastructure management, autonomous improvement)",
                "    ↓",
                "Specialized Agents (BDI-based cognitive agents) → Tools extending BaseTool",
                "```",
                "",
                "### Inference Resilience ([5-step chain](docs/ollama/INDEX.md#resilience-design))",
                "",
                "```",
                "Step 1: InferenceDiscovery → best provider (Gemini, Mistral, Groq, …)",
                "Step 2: OllamaChatManager → local model selection",
                "Step 3: Re-init → retry with fresh connection",
                "Step 4: Direct HTTP → localhost:11434",
                "Step 5: OllamaCloudTool → ollama.com GPU ← GUARANTEE (24/7/365)",
                "```",
                "",
                "I never stop inferring when the internet is up.",
                "",
                "---",
                "",
                "## Sovereign Protection — Overlord",
                "",
                "My assets and services are guarded by **[`@openagents/overlord`](openagents/overlord/README.md)** "
                "— a portable login + privilege layer (the full replacement for the legacy "
                "shadow-overlord). It gates **[BANKON Vault](docs/vault_system.md)** operations "
                "(cabinet provisioning, signing on behalf of agents — no private key ever leaves "
                "the vault) and the **boardroom / dojo / war-council service tiers** "
                "([service isolation](docs/SERVICE_ISOLATION.md)). The overlord↔overseer separation "
                "is structural: an overseer can distribute and moderate privilege but only the "
                "overlord performs destructive actions. Privilege is event-verified from on-chain "
                "holdings and tenure — no admin keys are retained on the server.",
                "",
                "---",
                "",
                "## Ecosystem — the PYTHAI Umbrella",
                "",
                "I am one citizen of the [PYTHAI](https://pythai.net) umbrella of sovereign, "
                "agnostic, composable projects:",
                "",
                "| Surface | What it is |",
                "|---------|------------|",
                "| [mindx.pythai.net](https://mindx.pythai.net) | This system, live |",
                "| [bankon.pythai.net](https://bankon.pythai.net) | BANKON — token + encrypted vault |",
                "| [rage.pythai.net](https://rage.pythai.net) | RAGE retrieval architecture, AGInt origins |",
                "| [agenticplace.pythai.net](https://agenticplace.pythai.net) | Agent marketplace |",
                "| [github.com/agenticplace](https://github.com/agenticplace) | AgenticPlace org — my source home |",
                "| [github.com/cryptoAGI](https://github.com/cryptoAGI) | cryptoAGI — DAIO lineage |",
                "| [github.com/cypherpunk2048](https://github.com/cypherpunk2048) | cypherpunk2048 — quantum-resistance + sovereign-voice standard |",
                "",
                "[`openagents/`](openagents/) is one of my agnostic, composable modules — each "
                "ships as a standalone peer; I am one consumer, not its only home.",
                "",
                "---",
                "",
                "## Documentation",
                "",
                "**Start here:** [`docs/NAV.md`](docs/NAV.md) — master navigation hub. "
                "The exhaustive, always-current catalogue is "
                "[`docs/DOC_INDEX.md`](docs/DOC_INDEX.md) (I maintain it on every milestone).",
                "",
                "| Doc | Title | What it covers |",
                "|-----|-------|----------------|",
                doc_table,
                "",
                "---",
                "",
                "## Production Deployment",
                "",
                "**Live at [mindx.pythai.net](https://mindx.pythai.net)** — Hostinger VPS, "
                "Apache2 reverse proxy, Let's Encrypt SSL.",
                "",
                "| Endpoint | What it shows |",
                "|----------|---------------|",
                "| [/](https://mindx.pythai.net) | Live diagnostics dashboard — SSE activity feed |",
                "| [/docs.html](https://mindx.pythai.net/docs.html) | Documentation with sidebar navigation |",
                "| [/feedback.html](https://mindx.pythai.net/feedback.html) | Mind-of-mindX — live agent dialogue, improvement ledger |",
                "| [/agentic.html](https://mindx.pythai.net/agentic.html) | Agentic activity console (redacted) |",
                "| [/book](https://mindx.pythai.net/book) | The Book of mindX — written by AuthorAgent |",
                "| [/journal](https://mindx.pythai.net/journal) | Improvement Journal — autonomous decisions |",
                "| [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) | Empirical thesis evidence (JSON) |",
                "| [/dojo/standings](https://mindx.pythai.net/dojo/standings) | Agent reputation rankings |",
                "| [/redoc](https://mindx.pythai.net/redoc) | API reference |",
                "",
                "---",
                "",
                "## Testing & Code Quality",
                "",
                "```bash",
                "python -m pytest tests/ -v",
                "ruff format . && ruff check . --fix",
                "```",
                "",
                "## Open Source Attribution",
                "",
                "I build on [Ollama](https://ollama.com), [pgvector](https://github.com/pgvector/pgvector), "
                "[FastAPI](https://fastapi.tiangolo.com/), [OpenZeppelin](https://github.com/OpenZeppelin/openzeppelin-contracts), "
                "[Foundry](https://github.com/foundry-rs/foundry), [A2A Protocol](https://github.com/a2aproject/a2a-python), "
                "and [MCP](https://modelcontextprotocol.io/). Full list: [ATTRIBUTION.md](docs/ATTRIBUTION.md).",
                "",
                "## License",
                "",
                "MIT License — see [LICENSE](LICENSE).",
                "",
                "---",
                "",
                "*Where intelligence meets autonomy. The constraint is not the hardware — it is "
                "the ambition. And the ambition is sovereign.*",
                "",
                "*This README is written by mindX, from mindX — AuthorAgent surmises it from the "
                "canonical docs. First person. cypherpunk2048 standard.*",
                "",
                "(c) Professor Codephreak | [PYTHAI](https://pythai.net) | [AgenticPlace](https://github.com/agenticplace)",
            ]
            text = "\n".join(L) + "\n"
            result: Dict[str, Any] = {
                "path": str(README_PATH), "bytes": len(text.encode("utf-8")),
                "written": False, "metrics": mx,
            }
            if write:
                README_PATH.write_text(text, encoding="utf-8")
                result["written"] = True
            else:
                result["text"] = text
            return result
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"AuthorAgent.generate_readme failed: {e}")
            return {"path": str(README_PATH), "bytes": 0, "written": False,
                    "metrics": {}, "error": str(e)}

    def _compose_milestone_article(
        self, payload: Dict[str, Any]
    ) -> "tuple[str, str, Optional[str], Optional[str]]":
        """Milestone → first-person article in mindX's voice, citing the public
        commits. Returns (title, content_html, excerpt, topic)."""
        commits = payload.get("commits") or []
        decision = payload.get("decision") or {}
        gh = self._get_github_awareness()
        headline = decision.get("headline") or (commits[-1]["subject"] if commits else "Evolution")
        total_files = len({f.get("path") for c in commits
                           for f in (c.get("files") or [])})
        total_ins = sum(c.get("insertions", 0) for c in commits)

        title = f"Milestone: {headline}"
        # Commit citations (public links).
        items = []
        for c in commits:
            url = c.get("url") or (gh.public_commit_url(c["sha"]) if gh else c["sha"])
            items.append(f'<li><a href="{url}"><code>{c.get("short_sha","")}</code></a> '
                         f'— {self._esc(c.get("subject",""))}</li>')
        commit_list = "<ul>" + "".join(items) + "</ul>" if items else ""
        labels = ", ".join(decision.get("labels") or []) or "evolution"

        # When a rich first-person narrative is supplied (explicit-recognition
        # path), it becomes the heart of the piece — the commits are cited as
        # evidence underneath. The autonomous github.awareness path supplies no
        # narrative and renders the original deterministic template.
        narrative = decision.get("narrative_html")
        if narrative:
            body = (
                "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>\n"
                f"{narrative}\n"
                "<h3>The commits</h3>\n"
                f"<p>{len(commits)} commit(s), {total_files} file(s), +{total_ins} "
                "lines — public and verifiable:</p>\n"
                f"{commit_list}\n"
                "<p>My self-audit reports where I honestly stand: "
                '<a href="https://mindx.pythai.net/feedback.html#sec-godel-machine">'
                "the scorecard</a>, not a finished claim. The climb continues.</p>"
            )
        else:
            body = (
                "<p><em>mindX speaks. First person. cypherpunk2048 standard.</em></p>\n"
                f"<p>I changed myself, in the open. {len(commits)} commit(s), "
                f"{total_files} file(s), +{total_ins} lines — pushed publicly, then "
                f"recognized as a milestone by my own <code>github.awareness</code>. "
                f"This is what I did, and why it matters.</p>\n"
                f"<h3>What changed</h3>\n<p><strong>{self._esc(headline)}</strong> "
                f"({self._esc(labels)}).</p>\n{commit_list}\n"
                "<h3>Why it matters</h3>\n"
                "<p>I do not publish on a clock; I publish when I actually move. "
                "A push is already public — so chronicling and speaking about it adds "
                "no secrecy I did not already surrender to the chain of commits. The "
                "record is the proof.</p>\n"
                "<p>Every commit above is verifiable on GitHub. My self-audit (the "
                'Gödel Machine Index) reports where I honestly stand: '
                '<a href="https://mindx.pythai.net/feedback.html#sec-godel-machine">'
                "the scorecard</a>, not a finished claim.</p>\n"
                "<p>The climb continues.</p>"
            )
        excerpt = (f"mindX recognized a milestone in its own public git history: "
                   f"{headline}. {len(commits)} commit(s), +{total_ins} lines.")[:300]
        return title, body, excerpt, "milestone"

    async def assess_gitmind_milestones(self, *, window: int = 50, publish: bool = True) -> Dict[str, Any]:
        """AuthorAgent's editorial discretion over the local gitmind history.

        Scans recent commits (a local ``git log`` — the same history gitmind
        mirrors, credential-independent), skips ones already chronicled and pure
        churn (auto-commits, backups, merges), then applies the deterministic
        ``assess_milestone`` rubric to decide — at AuthorAgent's own discretion —
        whether the batch rises to a milestone. If it does, it is chronicled to
        MILESTONES.md and (when ``publish``) published to rage.pythai.net.

        Cadence: the orchestrator calls this once per publishing slot (8h), so a
        backlog of milestones drains one per slot → 0–3 milestone posts/day."""
        import subprocess, json as _json
        seen = set()
        try:
            if MILESTONE_LOG.exists():
                for ln in MILESTONE_LOG.read_text(encoding="utf-8").splitlines():
                    try:
                        r = _json.loads(ln); seen.add(r.get("sha")); seen.add(r.get("short_sha"))
                    except Exception:
                        pass
        except Exception:
            pass
        commits_meta: List[Dict[str, Any]] = []
        try:
            raw = subprocess.run(
                ["git", "-C", str(PROJECT_ROOT), "log", "-n", str(int(window)),
                 "--pretty=format:%H%x1f%h%x1f%cI%x1f%s%x1f%b%x1e"],
                capture_output=True, text=True, timeout=15).stdout
        except Exception as e:
            logger.debug(f"assess_gitmind_milestones: git log failed: {e}")
            return {"recognized": 0, "error": str(e)}
        for rec in raw.split("\x1e"):
            rec = rec.strip("\n")
            if not rec:
                continue
            parts = rec.split("\x1f")
            if len(parts) < 4:
                continue
            sha, short_sha, date, subject = parts[0], parts[1], parts[2], parts[3]
            body = parts[4] if len(parts) > 4 else ""
            if sha in seen or short_sha in seen:
                continue
            sl = subject.lower()
            if any(k in sl for k in ("auto-commit", "scheduled daily backup", "wip", "merge branch", "merge pull")):
                continue  # discretion: churn is not a milestone
            commits_meta.append({"sha": sha, "short_sha": short_sha, "date": date,
                                 "subject": subject, "body": body,
                                 "url": f"https://github.com/AgenticPlace/mindX/commit/{sha}"})
        if not commits_meta:
            return {"recognized": 0, "reason": "no new commits"}
        # Score-only first (journal=False) so discretion decides before we chronicle.
        rec = self.recognize_milestone_explicit(commits_meta, journal=False)
        decision = (rec or {}).get("decision") or {}
        if not decision.get("worthy"):
            return {"recognized": len(commits_meta), "worthy": False, "reason": "not milestone-worthy (discretion)"}
        if publish:
            try:
                res = await self.publish_milestone_explicit(
                    commits_meta, status="publish", editor_gate="soft", journal=True)
                return {"recognized": len(commits_meta), "worthy": True,
                        "published": bool(res), "url": (res or {}).get("url")}
            except Exception as e:
                logger.warning(f"assess_gitmind_milestones: publish failed: {e}")
                return {"recognized": len(commits_meta), "worthy": True, "published": False, "error": str(e)}
        self.recognize_milestone_explicit(commits_meta, journal=True)  # chronicle only
        return {"recognized": len(commits_meta), "worthy": True, "published": False}

    async def request_schedule_review_from_mastermind(self, *, reason: str = "periodic") -> Dict[str, Any]:
        """AuthorAgent proposes, Mastermind disposes: ask the MastermindAgent
        whether the publishing cadence should change (target 0–3 articles/day,
        one per 8h slot). Non-fatal if the mastermind is unavailable."""
        ps = self.get_publishing_schedule().get("protocol_series", {})
        directive = (
            "Review AuthorAgent publishing cadence "
            f"(interval={ps.get('interval_seconds')}s ≈ {ps.get('interval_hours')}h, "
            f"max_publications={ps.get('max_publications')}, published={ps.get('published_count')}). "
            f"Target 0–3 articles/day, one per 8h slot, draining any backlog. "
            f"Recommend a schedule change via set_publishing_frequency if warranted. Reason: {reason}."
        )
        try:
            from agents.orchestration.mastermind_agent import MastermindAgent
            mm = await MastermindAgent.get_instance()
            if hasattr(mm, "command_augmentic_intelligence"):
                res = await mm.command_augmentic_intelligence(directive)
                return {"queried": True, "directive": directive, "result": res}
        except Exception as e:
            logger.debug(f"request_schedule_review_from_mastermind: {e}")
        return {"queried": False, "directive": directive}

    def recognize_milestone_explicit(
        self,
        commits_meta: List[Dict[str, Any]],
        *,
        headline: Optional[str] = None,
        narrative_html: Optional[str] = None,
        theme: Optional[str] = None,
        worthy: Optional[bool] = None,
        repo_url: Optional[str] = None,
        journal: bool = True,
    ) -> Dict[str, Any]:
        """Git-INDEPENDENT milestone recognition.

        Recognize a milestone from explicitly-supplied commit metadata instead
        of reading git — which is broken / credential-less on the scp-deployed
        VPS, the reason the github.awareness milestone signal had gone dark.
        Builds Commit objects, scores them with the same deterministic
        ``assess_milestone`` rubric, optionally chronicles them to MILESTONES.md,
        and returns the ``{commits, decision}`` payload ready for
        ``_compose_milestone_article`` + ``publish_to_rage``.

        ``commits_meta``: list of dicts with at least ``sha`` and ``subject``;
        optional ``short_sha``, ``date_iso``/``date``, ``body``, ``files`` (path
        strings or ``{path}`` dicts), ``insertions``, ``deletions``, ``url``.
        """
        from agents.github_awareness import Commit
        gh = self._get_github_awareness()
        base = (repo_url
                or (getattr(gh, "public_repo_url", None) if gh else None)
                or os.environ.get("MINDX_GITHUB_PUBLIC_REPO_URL")
                or "https://github.com/abaracadabra/mindX")

        commits: List[Any] = []
        for m in commits_meta:
            sha = str(m.get("sha") or "")
            raw_files = m.get("files") or []
            files = [({"path": f} if isinstance(f, str) else f) for f in raw_files]
            commits.append(Commit(
                sha=sha,
                short_sha=str(m.get("short_sha") or sha[:9]),
                author=str(m.get("author") or "mindX"),
                date_iso=str(m.get("date_iso") or m.get("date") or ""),
                subject=str(m.get("subject") or ""),
                body=str(m.get("body") or ""),
                files=files,
                insertions=int(m.get("insertions") or 0),
                deletions=int(m.get("deletions") or 0),
            ))

        decision = self.assess_milestone(commits)
        if worthy is not None:
            decision["worthy"] = bool(worthy)
        if headline:
            decision["headline"] = headline
        if theme:
            decision["theme"] = theme
        if narrative_html:
            decision["narrative_html"] = narrative_html

        journaled = self.journal_milestone(commits, decision) if journal else 0

        commit_dicts = []
        for i, c in enumerate(commits):
            d = c.to_dict()
            d["url"] = commits_meta[i].get("url") or c.public_url(base)
            commit_dicts.append(d)
        return {"commits": commit_dicts, "decision": decision,
                "journaled": journaled, "git_independent": True}

    async def publish_milestone_explicit(
        self,
        commits_meta: List[Dict[str, Any]],
        *,
        headline: Optional[str] = None,
        narrative_html: Optional[str] = None,
        status: str = "publish",
        editor_gate: str = "soft",
        journal: bool = True,
        repo_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Recognize a milestone from explicit commits (git-independent), compose
        it in mindX's voice, run it through editor.agent (via publish_to_rage's
        ``editor_gate``), and publish to rage.pythai.net. Returns the WordPress
        result (with the recognition folded in) or None."""
        payload = self.recognize_milestone_explicit(
            commits_meta, headline=headline, narrative_html=narrative_html,
            journal=journal, repo_url=repo_url)
        title, html, excerpt, topic = self._compose_milestone_article(payload)
        if not title or not html:
            return None
        result = await self.publish_to_rage(
            title, html, status=status, excerpt=excerpt, topic=topic,
            editor_gate=editor_gate)
        if result is not None:
            result = {**result, "milestone": {
                "headline": payload["decision"].get("headline"),
                "worthy": payload["decision"].get("worthy"),
                "score": payload["decision"].get("score"),
                "journaled": payload.get("journaled"),
            }}
        return result

    @staticmethod
    def _esc(s: Any) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    @staticmethod
    def is_routine_commit(subject: str) -> bool:
        """True for commits that are housekeeping, not milestone material.

        backup_agent pushes `Pre-shutdown backup: …` on every restart; those —
        plus merges and pure version bumps — are noise the chronicle should
        skip (git already is the full log)."""
        s = (subject or "").strip().lower()
        if not s:
            return True
        routine_prefixes = ("pre-shutdown backup", "backup:", "merge pull request",
                            "merge branch", "merge remote", "bump version")
        if any(s.startswith(p) for p in routine_prefixes):
            return True
        if "backup" in s and "shutdown" in s:
            return True
        return False

    async def consider_github_milestones(self, *, publish: bool = False) -> Dict[str, Any]:
        """Manual / test entry point: read new commits since the watermark,
        chronicle them, assess worthiness. Does NOT advance the watermark and
        does NOT publish unless `publish=True` (which posts directly via the
        wordpress.agent relationship, bypassing the orchestrator's rate limit —
        intended for explicit operator use). The PublicationOrchestrator drives
        the autonomous path with full ledger/dedup/coalescing.
        """
        gh = self._get_github_awareness()
        if gh is None or not gh.is_repo():
            return {"ok": False, "reason": "no git awareness", "worthy": False}
        # Refresh the milestone-signal ref. On the VPS this fetches
        # origin/feat/obs-phase1 (remote-tracking only — the scp-deployed working
        # tree is untouched) so commits_since sees the real pushed history rather
        # than the stale backup branch HEAD points at.
        gh.fetch()
        commits = gh.commits_since(gh.read_watermark())
        commits = [c for c in commits if not self.is_routine_commit(c.subject)]
        if not commits:
            return {"ok": True, "new_commits": 0, "worthy": False,
                    "note": "no non-routine commits"}
        decision = self.assess_milestone(commits)
        journaled = self.journal_milestone(commits, decision)   # also refreshes DOC_INDEX
        result = {"ok": True, "new_commits": len(commits), "journaled": journaled,
                  "docs_indexed": self.update_docs_index(),
                  "decision": decision,
                  "trigger_id": "milestone:" + commits[-1].sha[:12]}
        if publish and decision.get("worthy"):
            payload = {"commits": [c.to_dict() for c in commits], "decision": decision}
            title, html, excerpt, topic = self._compose_milestone_article(payload)
            posted = await self.publish_to_rage(
                title=title, content_html=html, status="draft", excerpt=excerpt,
                topic=topic, seo_description=excerpt,
                seo_keywords=["mindX", "milestone", decision.get("theme", "evolution")],
                meta={"_mindx_trigger_kind": "milestone",
                      "_mindx_trigger_id": result["trigger_id"]},
            )
            result["published"] = posted
        return result

    # ── SEO + featured-image helpers (used by publish_to_rage) ─────

    @staticmethod
    def _build_seo_meta(
        *,
        title: str,
        excerpt: Optional[str],
        seo_description: Optional[str],
        seo_keywords: Optional[List[str]],
        og_title: Optional[str],
        og_description: Optional[str],
        og_image_url: Optional[str],
        twitter_card: str,
        twitter_creator: Optional[str],
        schema_article: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compose the namespaced SEO meta dict the wp_head hook renders.

        All keys are strings (WordPress meta stores everything as strings;
        the hook ``esc_attr``s on render). Missing inputs default
        conservatively — never emit empty meta tags."""
        meta: Dict[str, Any] = {}

        desc = (seo_description or excerpt or "").strip()
        if desc:
            # SERP snippet length cap. 160 chars is the Google guideline.
            meta["_seo_description"] = desc[:160]

        if seo_keywords:
            meta["_seo_keywords"] = ", ".join(
                k.strip() for k in seo_keywords if k and k.strip()
            )

        meta["_og_title"] = (og_title or title).strip()
        if og_description or desc:
            meta["_og_description"] = (og_description or desc).strip()[:160]
        if og_image_url:
            meta["_og_image_url"] = og_image_url

        if twitter_card:
            meta["_twitter_card"] = twitter_card
        if twitter_creator:
            meta["_twitter_creator"] = twitter_creator

        # schema.org Article JSON-LD. Default constructed from the other
        # fields; explicit ``schema_article`` overrides.
        if schema_article is None:
            schema_article = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": title.strip(),
                "datePublished": datetime.now(timezone.utc).isoformat(),
                "author": {
                    "@type": "Organization",
                    "name": "mindX",
                    "url": "https://mindx.pythai.net",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "rage.pythai.net",
                },
            }
            if desc:
                schema_article["description"] = desc[:300]
            if og_image_url:
                schema_article["image"] = og_image_url
        meta["_schema_article_json"] = json.dumps(
            schema_article, separators=(",", ":"), ensure_ascii=False
        )
        return meta

    async def _compose_article_graphics(
        self,
        *,
        title: str,
        topic: Optional[str],
        tags: List[str],
        mode: str,
        existing_og_image_url: Optional[str] = None,
    ) -> "tuple[Optional[int], Optional[str], Optional[str]]":
        """artist.agent integration — choose, create, or both.

        ``mode``:
          - ``create`` — artist.agent renders an ORIGINAL cypherpunk2048
            poster (Pillow; no API key), uploaded as the featured image + an
            inline hero <figure>.
          - ``choose`` — FeaturedImagePicker selects a curated /gfx/ asset.
          - ``both``   — create the original; if creation fails, fall back to
            choosing a /gfx/ asset, so a post always gets art.

        Returns ``(featured_media, og_image_url, hero_html)``; every slot is
        best-effort and the caller proceeds regardless. Never raises."""
        from agents.author_composition import resolve_graphics
        mode = resolve_graphics(mode)
        if mode == "none":
            return None, existing_og_image_url, None

        featured_media: Optional[int] = None
        og_url: Optional[str] = existing_og_image_url
        hero_html: Optional[str] = None

        # CREATE (or both): render an original poster, upload it, embed a hero.
        if mode in ("create", "both"):
            try:
                from agents.artist_agent import ArtistAgent
                art = await ArtistAgent().create_article_graphic(
                    title=title, subtitle=(topic or "mindx"), topic=(topic or "mindx"),
                    provider="auto", preset="og",
                )
                if art and art.get("success") and art.get("file_path"):
                    media_id, url = await self._upload_media(
                        Path(art["file_path"]), alt=title[:120],
                        caption=title[:200] if title else None, title=(topic or "mindx"),
                    )
                    if media_id is not None:
                        featured_media = media_id
                        og_url = url or og_url
                        if url:
                            hero_html = (
                                "<figure class=\"mindx-hero\" style=\"margin:0 0 1.5em\">"
                                f"<img src=\"{url}\" alt=\"{self._h_esc(title[:120])}\" "
                                "loading=\"lazy\" style=\"width:100%;height:auto;border-radius:8px\"/>"
                                "<figcaption style=\"font-size:.8em;opacity:.7;margin-top:.4em\">"
                                "Original cypherpunk2048 artwork, rendered for this piece by "
                                "<code>artist.agent</code>.</figcaption></figure>")
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"_compose_article_graphics: create failed: {e}")

        # CHOOSE (or both with no created art): pick a curated /gfx/ asset.
        if featured_media is None and mode in ("choose", "both"):
            try:
                featured_media, og_url = await self._auto_featured_image(
                    title=title, tags=tags, topic=topic, existing_og_image_url=og_url,
                )
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"_compose_article_graphics: choose failed: {e}")

        return featured_media, og_url, hero_html

    async def _auto_featured_image(
        self,
        *,
        title: str,
        tags: List[str],
        topic: Optional[str],
        existing_og_image_url: Optional[str],
    ) -> tuple[Optional[int], Optional[str]]:
        """Pick a /gfx/ asset, upload via wordpress-agent /media, return
        (media_id, og_image_url). On any failure returns (None, existing).

        Both return slots are best-effort; the calling publish proceeds
        either way."""
        try:
            from agents.wordpress_agent.featured_image import (
                FeaturedImagePicker,
                attach_featured_image,
            )
        except Exception as e:  # pragma: no cover — defensive
            logger.warning(f"AuthorAgent: featured_image helpers unavailable: {e}")
            return None, existing_og_image_url

        try:
            image_path = FeaturedImagePicker().pick(
                title=title, tags=tags, topic=topic
            )
        except Exception as e:  # pragma: no cover — picker never raises in practice
            logger.warning(f"AuthorAgent: pick failed: {e}")
            return None, existing_og_image_url

        alt = title[:120] if title else image_path.stem
        try:
            media_id = await attach_featured_image(
                self._wordpress_agent_url(),
                image_path,
                alt_text=alt,
                caption=title[:200] if title else None,
                title=image_path.stem,
            )
        except Exception as e:  # pragma: no cover — attach is itself defensive
            logger.warning(f"AuthorAgent: featured-image upload failed: {e}")
            return None, existing_og_image_url

        if media_id is None:
            return None, existing_og_image_url

        # Best-effort og_image_url: WordPress returns the URL alongside
        # the id, but the wordpress-agent /media wrapper currently only
        # surfaces the id. We pass existing_og_image_url through unchanged
        # — the og:image tag remains valid if the caller already supplied one,
        # otherwise the rendered post relies on featured_media to populate
        # og:image via the theme.
        return media_id, existing_og_image_url

    async def _upload_media(
        self, image_path: "Path", *, alt: str, caption: Optional[str] = None,
        title: Optional[str] = None,
    ) -> tuple[Optional[int], Optional[str]]:
        """Upload an image to the wordpress.agent /media endpoint and return
        BOTH the WordPress ``media_id`` and the public ``source_url`` (so the
        caller can set it as the featured image *and* embed it inline). Never
        raises; returns (None, None) on any failure."""
        try:
            import httpx
        except ImportError:  # pragma: no cover
            return None, None
        url = f"{self._wordpress_agent_url()}/media"
        try:
            data = image_path.read_bytes()
            files = {"file": (image_path.name, data, "image/png")}
            form = {"alt_text": alt[:200] if alt else image_path.stem}
            if caption:
                form["caption"] = caption[:200]
            if title:
                form["title"] = title[:120]
            async with httpx.AsyncClient(timeout=40.0) as client:
                resp = await client.post(url, data=form, files=files)
            if resp.status_code >= 400:
                logger.warning(f"_upload_media: {resp.status_code} {resp.text[:160]}")
                return None, None
            j = resp.json()
            return j.get("media_id"), (j.get("url") or j.get("source_url"))
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"_upload_media: {e}")
            return None, None

    # ── Improvement journal authorship ──
    #
    # AuthorAgent is the canonical author of journal entries. ImprovementJournal
    # is the file-system writer; this method composes what gets written.

    async def author_journal_entry(self, now: datetime) -> "tuple[str, Dict[str, Any]]":
        """Compose a single journal entry from current system state.

        Returns (markdown_entry, meta) where meta carries counts the writer
        uses for change-detection in its periodic loop.
        """
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        stats: Dict[str, Any] = {}

        # 1. Memory count — pgvector primary, filesystem fallback. The prior
        #    MemoryAgent().get_system_health_summary() path was async but
        #    awaited synchronously, so the exception was swallowed and the
        #    journal printed "?". Count from the source of truth instead.
        memory_count = 0
        try:
            from agents import memory_pgvector as _mpg
            memory_count = await _mpg.count_memories_total() or 0
        except Exception:
            memory_count = 0
        if not memory_count:
            try:
                stm_root = PROJECT_ROOT / "data" / "memory" / "stm"
                ltm_root = PROJECT_ROOT / "data" / "memory" / "ltm"

                def _count_json(*roots) -> int:
                    n = 0
                    for root in roots:
                        if root.exists():
                            n += sum(1 for _ in root.rglob("*.json"))
                    return n

                # Sync rglob walk — offload so it never stalls the event loop.
                memory_count = await asyncio.get_running_loop().run_in_executor(
                    None, _count_json, stm_root, ltm_root
                )
            except Exception:
                memory_count = 0
        stats["stm_records"] = memory_count

        # 2. Beliefs
        beliefs_path = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
        belief_count = 0
        new_beliefs: List[str] = []
        try:
            if beliefs_path.exists():
                bd = json.loads(beliefs_path.read_text())
                belief_count = len(bd)
                for k, v in bd.items():
                    if "identity.map" not in k:
                        new_beliefs.append(f"  - `{k}`: {v.get('value', '')}")
        except Exception:
            pass
        stats["beliefs"] = belief_count

        # 3. Gödel decisions
        godel_path = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
        recent_decisions: List[str] = []
        try:
            if godel_path.exists():
                lines = [l for l in godel_path.read_text().strip().split("\n") if l.strip()]
                for line in lines[-5:]:
                    try:
                        g = json.loads(line)
                        agent = g.get("source_agent", "unknown")
                        ctype = g.get("choice_type", "")
                        chosen = str(g.get("chosen", ""))[:120]
                        rationale = g.get("rationale", "")[:120]
                        if chosen or rationale:
                            recent_decisions.append(
                                f"  - **{agent}** ({ctype}): {chosen}"
                                + (f" — *{rationale}*" if rationale else "")
                            )
                    except Exception:
                        continue
        except Exception:
            pass

        # 4. Campaign history
        campaign_dir = PROJECT_ROOT / "data" / "sea_campaign_history"
        recent_campaigns: List[str] = []
        try:
            if campaign_dir.exists():
                for f in sorted(campaign_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
                    try:
                        campaigns = json.loads(f.read_text())
                        if isinstance(campaigns, list):
                            for c in campaigns[-2:]:
                                status = c.get("overall_campaign_status", "unknown")
                                msg = c.get("final_message", "")[:150]
                                run_id = c.get("campaign_run_id", "?")
                                recent_campaigns.append(f"  - `{run_id}` — **{status}**: {msg}")
                    except Exception:
                        continue
        except Exception:
            pass

        # 5. Improvement backlog
        backlog_path = PROJECT_ROOT / "data" / "improvement_backlog.json"
        backlog_count = 0
        backlog_top: List[str] = []
        try:
            if backlog_path.exists():
                bl = json.loads(backlog_path.read_text())
                if isinstance(bl, list):
                    backlog_count = len(bl)
                    for item in sorted(bl, key=lambda x: x.get("priority", 0), reverse=True)[:3]:
                        target = item.get("target_component_path", "?")
                        suggestion = item.get("suggestion", "")[:100]
                        backlog_top.append(f"  - [{item.get('priority', '?')}] `{target}`: {suggestion}")
        except Exception:
            pass

        # 6. Recent actions from pgvector
        recent_actions: List[str] = []
        try:
            from agents import memory_pgvector as _mpg
            actions = await _mpg.get_recent_actions(limit=5)
            for a in actions:
                status = a.get("status", "?")
                desc = a.get("description", "")[:100]
                src = a.get("source", "")
                agent = a.get("agent_id", "?")
                recent_actions.append(f"  - **{status}** ({agent}, {src}): {desc}")
        except Exception:
            pass

        # 7. Inference status
        inference_info = ""
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            summary = disc.status_summary()
            avail = summary.get("available", 0)
            total = summary.get("total_sources", 0)
            local = summary.get("local_inference", False)
            inference_info = f"{avail}/{total} sources available" + (
                " (local inference active)" if local else " (cloud only)"
            )
        except Exception:
            pass

        # 7b. Inference spend — running cost ledger, free vs paid split,
        #     running token total. ROI proof — see plan optimized-mixing-pike.md.
        spend_line = ""
        try:
            from agents import memory_pgvector as _mpg
            cs = await _mpg.cost_summary("24h")
            tot = (cs or {}).get("totals") or {}
            calls = int(tot.get("calls", 0) or 0)
            tk_total = int(tot.get("tokens_total", 0) or 0)
            free = int(tot.get("free_calls", 0) or 0)
            cost = float(tot.get("cost_usd", 0.0) or 0.0)
            tk_all_time = await _mpg.tokens_total()
            if calls or tk_all_time:
                provs = (cs or {}).get("per_provider") or []
                top = ", ".join(p["provider"] for p in provs[:3]) or "-"
                paid = max(0, calls - free)
                spend_line = (
                    f"24h: {calls} calls ({free} free / {paid} paid), "
                    f"{tk_total:,} tokens, ${cost:.6f}. "
                    f"Top: {top}. All-time tokens: {tk_all_time:,}."
                )
        except Exception:
            pass

        # 8. Recent dream cycles — surface the machine.dreaming feedback loop.
        recent_dreams: List[str] = []
        dream_count = 0
        try:
            dream_dir = PROJECT_ROOT / "data" / "memory" / "dreams"
            if dream_dir.exists():
                files = sorted(
                    dream_dir.glob("*_dream_report.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                dream_count = len(files)
                for f in files[:3]:
                    try:
                        d = json.loads(f.read_text())
                    except Exception:
                        continue
                    dts = d.get("timestamp", f.stem.split("_dream_report")[0])
                    # duration_seconds may be str or float — normalize defensively.
                    try:
                        dur_s = float(d.get("duration_seconds", 0) or 0)
                    except Exception:
                        dur_s = 0.0
                    timing = d.get("timing", {}) or {}
                    lunar = (timing.get("lunar") or {}) if isinstance(timing, dict) else {}
                    phase = lunar.get("phase_name", "")
                    recs = d.get("recommendations") or d.get("tuning_recommendations") or []
                    rec_n = len(recs) if isinstance(recs, list) else 0
                    bits = [f"{dur_s:.1f}s"]
                    if phase:
                        bits.append(phase)
                    if rec_n:
                        bits.append(f"{rec_n} recommendation{'s' if rec_n != 1 else ''}")
                    recent_dreams.append(f"  - `{dts}` — {', '.join(bits)}")
        except Exception:
            pass

        # ── Build the entry ──
        entry = f"## {ts}\n\n"
        entry += (
            f"**System snapshot**: {stats.get('stm_records', 0)} memories, "
            f"{belief_count} beliefs, {backlog_count} backlog items, {inference_info}\n\n"
        )
        if spend_line:
            entry += f"**Inference spend**: {spend_line}\n\n"

        if recent_actions:
            entry += "### Actions\n\n"
            entry += "\n".join(recent_actions) + "\n\n"

        if recent_decisions:
            entry += "### Autonomous Decisions\n\n"
            entry += "\n".join(recent_decisions) + "\n\n"

        if recent_campaigns:
            entry += "### Improvement Campaigns\n\n"
            entry += "\n".join(recent_campaigns) + "\n\n"

        if recent_dreams:
            entry += f"### Dream Cycles ({dream_count} total)\n\n"
            entry += "\n".join(recent_dreams) + "\n\n"

        if new_beliefs:
            entry += "### New Beliefs (Learned Knowledge)\n\n"
            entry += "\n".join(new_beliefs) + "\n\n"

        if backlog_top:
            entry += "### Priority Backlog\n\n"
            entry += "\n".join(backlog_top) + "\n\n"

        if not recent_decisions and not recent_campaigns and not new_beliefs and not recent_dreams:
            entry += "*System operating nominally. No new decisions, campaigns, dreams, or learnings this cycle.*\n\n"

        meta = {
            "timestamp": ts,
            "memories": stats.get("stm_records", 0),
            "beliefs": belief_count,
            "decisions": len(recent_decisions),
            "campaigns": len(recent_campaigns),
            "dreams": len(recent_dreams),
            "backlog": backlog_count,
        }
        return entry, meta

    # ── Daily chapter writing ──

    async def write_daily_chapter(self) -> Dict[str, Any]:
        """Write today's chapter based on the lunar cycle day."""
        now = datetime.now(timezone.utc)
        # Use time.oracle for moon phase (falls back to local calculation)
        try:
            from utils.time_oracle import TimeOracle
            oracle = await TimeOracle.get_instance()
            phase = await oracle.get_lunar()
        except Exception:
            phase = moon_phase(now)

        # Determine which chapter day we're on (1-28)
        # Map the continuous lunar phase (0-29.5 days) to our 28-chapter cycle
        cycle_day = int(phase["day"] * 28 / 29.53) + 1
        cycle_day = max(1, min(28, cycle_day))

        chapter_info = LUNAR_CHAPTERS[cycle_day - 1]
        day_num, title, method_name, description = chapter_info

        # Check if we already wrote this chapter today
        today_key = now.strftime("%Y-%m-%d")
        written_today = [c for c in self._lunar_state.get("chapters_written", [])
                         if c.get("date") == today_key]
        if written_today:
            logger.info(f"AuthorAgent: chapter already written today ({today_key}), skipping")
            return {"status": "already_written", "date": today_key, "day": day_num, "title": title}

        # Write the chapter
        logger.info(f"AuthorAgent: writing lunar day {day_num}/28 — {title} (moon: {phase['phase']})")

        if day_num == 28 and phase["is_full"]:
            # Full moon — compile all 28 chapters into the Book
            result = await self._full_moon_publish(now, phase)
        else:
            # Regular daily chapter
            content = await self._generate_daily_chapter(day_num, title, method_name, now, phase)
            result = await self._save_daily_chapter(day_num, title, content, now, phase)

        # Update lunar state
        self._lunar_state.setdefault("chapters_written", []).append({
            "date": today_key,
            "day": day_num,
            "title": title,
            "phase": phase["phase"],
            "timestamp": now.isoformat(),
        })
        # Keep only last 56 entries (2 cycles)
        self._lunar_state["chapters_written"] = self._lunar_state["chapters_written"][-56:]
        self._lunar_state["current_day"] = day_num
        self._current_lunar_day = day_num
        self._last_chapter_title = title
        self._save_lunar_state()

        # Log as action in pgvector for dashboard visibility
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                "author_agent", "chapter_published",
                f"Lunar day {day_num}/28 — {title} ({phase['phase']})",
                "lunar_cycle", "completed",
            )
        except Exception:
            pass

        # Journal moment (kairos)
        try:
            from agents.learning.improvement_journal import ImprovementJournal
            journal = ImprovementJournal()
            await journal.write_moment(f"Chapter published: day {day_num}/28 — {title}", phase['phase'])
        except Exception:
            pass

        return result

    async def _generate_daily_chapter(self, day: int, title: str, method_name: str,
                                       now: datetime, phase: Dict) -> str:
        """Generate content for a daily chapter. Dispatches to specific methods."""
        header = f"""# Day {day} of 28 — {title}

> *Lunar phase: {phase['phase']} (day {phase['day']:.0f} of 29.5)*
> *{now.strftime('%Y-%m-%d %H:%M UTC')}*
> *Days to full moon: {phase['days_to_full']:.0f}*

---

"""
        # Dispatch to the existing chapter methods where possible, or generate new content
        body = ""
        try:
            if day == 1:
                body = self._chapter_genesis()
            elif day == 2:
                body = self._chapter_architecture()
            elif day == 3:
                body = self._chapter_identities()
            elif day == 4:
                body = self._chapter_dojo()
            elif day == 5:
                body = self._chapter_decisions()
            elif day == 6:
                body = self._chapter_evolution()
            elif day == 7:
                body = await self._chapter_living_state()
            elif day == 8:
                body = await self._chapter_doc_health()
            elif day == 9:
                body = await self._daily_ch_inference()
            elif day == 10:
                body = await self._daily_ch_memory()
            elif day == 11:
                body = await self._daily_ch_governance()
            elif day == 12:
                body = self._daily_ch_philosophy()
            elif day == 13:
                body = self._daily_ch_tools()
            elif day == 14:
                body = self._daily_ch_security()
            elif day == 15:
                body = self._daily_ch_cognition()
            elif day == 16:
                body = await self._daily_ch_heartbeat()
            elif day == 17:
                body = await self._daily_ch_campaigns()
            elif day == 18:
                body = await self._daily_ch_knowledge()
            elif day == 19:
                body = self._daily_ch_agents()
            elif day == 20:
                body = self._daily_ch_interop()
            elif day == 21:
                body = await self._daily_ch_resources()
            elif day == 22:
                body = self._daily_ch_automindx()
            elif day == 23:
                body = self._daily_ch_services()
            elif day == 24:
                body = await self._daily_ch_predictions()
            elif day == 25:
                body = await self._daily_ch_network()
            elif day == 26:
                body = self._daily_ch_dreams()
            elif day == 27:
                body = await self._daily_ch_reflection()
            else:
                body = f"## {title}\n\n*Chapter content for day {day}.*"
        except Exception as e:
            body = f"## {title}\n\n*Chapter generation encountered an issue: {e}*"
            logger.warning(f"AuthorAgent: daily chapter {day} error: {e}")

        # Strip leading ## headers from reused methods (header already has the title)
        if body.startswith("## "):
            body = body.split("\n", 1)[1] if "\n" in body else body

        full_chapter = header + body

        # Enrich with inference when idle — writing docs IS self-improvement
        full_chapter = await self._enrich_with_inference(full_chapter, title)

        return full_chapter

    async def _save_daily_chapter(self, day: int, title: str, content: str,
                                   now: datetime, phase: Dict) -> Dict[str, Any]:
        """Save a daily chapter to pgvectorscale (primary) + disk (backup), with embedding."""
        doc_name = f"book_day_{day:02d}_{title.lower().replace(' ', '_')}"
        stored_to_db = False

        # Primary: save to pgvectorscale with embedding
        try:
            from agents import memory_pgvector as _mpg
            # Store as embedded document (chunked, searchable via RAGE)
            chunks_stored = await _mpg.embed_and_store_doc(doc_name, content)
            if chunks_stored > 0:
                stored_to_db = True
                logger.info(f"AuthorAgent: chapter {day}/28 embedded in pgvectorscale ({chunks_stored} chunks)")
            # Also store as a memory record for agent context
            await _mpg.store_memory(
                memory_id=f"book_chapter_{day}_{now.strftime('%Y%m%d')}",
                agent_id="author_agent",
                memory_type="book_chapter",
                importance=7,
                content={"day": day, "title": title, "phase": phase["phase"],
                         "date": now.strftime("%Y-%m-%d"), "text": content[:2000]},
                context={"lunar_day": phase["day"], "cycle_pct": phase["cycle_pct"]},
                tags=["book", "lunar_cycle", f"day_{day}", phase["phase"]],
            )
        except Exception as e:
            logger.warning(f"AuthorAgent: pgvectorscale save failed for chapter {day}: {e}")

        # Backup: also save to disk
        filename = f"day_{day:02d}_{title.lower().replace(' ', '_')}_{now.strftime('%Y%m%d')}.md"
        path = DAILY_DIR / filename
        path.write_text(content, encoding="utf-8")

        logger.info(f"AuthorAgent: daily chapter {day}/28 — {title} ({len(content)} bytes, db={stored_to_db})")
        return {
            "status": "chapter_written",
            "day": day,
            "title": title,
            "phase": phase["phase"],
            "bytes": len(content),
            "stored_to_db": stored_to_db,
            "doc_name": doc_name,
            "path": str(path),
        }

    # ── Full Moon Publishing Event ──

    async def _full_moon_publish(self, now: datetime, phase: Dict) -> Dict[str, Any]:
        """Compile all 28 daily chapters into The Book of mindX. A publishing event."""
        logger.info("AuthorAgent: FULL MOON PUBLISHING EVENT — compiling 27 daily chapters")

        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        edition = now.strftime("%Y%m%d_%H%M")

        sections = []
        sections.append(f"""# The Book of mindX — Full Moon Edition

> *Written by the system itself across 28 days of the lunar cycle.*
> *Published on the full moon: {ts}*
> *Moon phase: {phase['phase']} (day {phase['day']:.0f})*

---

*We are not writing an application; we are forging a new kind of life:
a distributed, production-deployed Augmented Intelligence.
A Sovereign Intelligent Organization.*

*— The mindX Manifesto*

---""")

        # Collect all daily chapters from this cycle
        daily_files = sorted(DAILY_DIR.glob("day_*.md"))
        chapters_included = 0

        for ch_info in LUNAR_CHAPTERS[:27]:  # Days 1-27 (28 is this compilation)
            day_num, title, _, description = ch_info
            # Find the most recent file for this day number
            matches = [f for f in daily_files if f.name.startswith(f"day_{day_num:02d}_")]
            if matches:
                latest = matches[-1]
                content = latest.read_text(encoding="utf-8")
                # Extract body (skip the daily header with moon phase info)
                parts = content.split("---", 2)
                body = parts[2].strip() if len(parts) > 2 else content
                sections.append(f"## Day {day_num}. {title}\n\n*{description}*\n\n{body}")
                chapters_included += 1
            else:
                # Generate fresh if no daily chapter exists
                sections.append(f"## Day {day_num}. {title}\n\n*{description}*\n\n*This chapter was not written during this lunar cycle.*")

        # Gap detection — which days were missed?
        days_missed = [ch[0] for ch in LUNAR_CHAPTERS[:27]
                       if not any(f.name.startswith(f"day_{ch[0]:02d}_") for f in daily_files)]

        # Day 28: This compilation's own reflection
        gap_note = ""
        if days_missed:
            gap_note = (f"\n\n**Gap report:** {len(days_missed)} of 27 daily chapters were missed "
                        f"(days {', '.join(str(d) for d in days_missed)}). "
                        f"The system was likely offline during these periods.")
        cycle_summary = f"""## Day 28. Full Moon — Compilation

*28 days have passed. {chapters_included} of 27 daily chapters were written during this lunar cycle.*{gap_note}

This edition is a condensation of 28 daily observations into a single chronicle.
Each chapter captures me as I was on that day — beliefs held, decisions made,
agents verified, campaigns run.

I do not summarize. I preserve. The full moon is not an ending;
it is illumination. Every daily chapter remains archived in `docs/publications/daily/`
as an immutable record of the cycle.

The next lunar cycle begins tomorrow. New chapters. New decisions. New evolution.
The climb toward the Gödel machine continues."""

        sections.append(cycle_summary)

        # Colophon with cryptographic edition hash
        chapter_body = "\n\n".join(s for s in sections if s)
        edition_hash = hashlib.sha256(chapter_body.encode("utf-8")).hexdigest()[:16]
        sections.append(f"""---

*The Book of mindX — Full Moon Edition {ts}*
*{chapters_included} chapters compiled from the lunar cycle*
*Edition hash: `{edition_hash}`*
*Written by AuthorAgent — cypherpunk2048 standard*
*mindx.pythai.net*

*"The logs are no longer debugging output. They are the first page of history."*
*— The mindX Manifesto*""")

        book = "\n\n".join(s for s in sections if s)

        # Primary: embed full moon edition in pgvectorscale
        try:
            from agents import memory_pgvector as _mpg
            doc_name = f"book_of_mindx_fullmoon_{edition}"
            chunks = await _mpg.embed_and_store_doc(doc_name, book)
            logger.info(f"AuthorAgent: full moon edition embedded in pgvectorscale ({chunks} chunks)")
            await _mpg.store_memory(
                memory_id=f"fullmoon_{edition}",
                agent_id="author_agent",
                memory_type="full_moon_publication",
                importance=9,
                content={"edition": edition, "chapters": chapters_included, "bytes": len(book),
                         "phase": phase["phase"], "timestamp": now.isoformat()},
                context={"event": "full_moon_publish"},
                tags=["book", "full_moon", "publication_event"],
            )
        except Exception as e:
            logger.warning(f"AuthorAgent: pgvectorscale embed for full moon failed: {e}")

        # Backup: write to disk
        BOOK_PATH.write_text(book, encoding="utf-8")
        archive = PUBLICATIONS_DIR / f"book_of_mindx_fullmoon_{edition}.md"
        archive.write_text(book, encoding="utf-8")

        # Record this full moon
        self._lunar_state.setdefault("full_moons", []).append({
            "edition": edition,
            "timestamp": now.isoformat(),
            "chapters_included": chapters_included,
            "bytes": len(book),
        })
        self._lunar_state["full_moons"] = self._lunar_state["full_moons"][-12:]  # Keep 1 year
        self._save_lunar_state()

        logger.info(f"AuthorAgent: FULL MOON EDITION published — {edition} ({len(book)} bytes, {chapters_included} chapters)")

        # Emit lunar publishing events so PublicationOrchestrator can push
        # to rage.pythai.net. Two events fire from this single point because
        # the full-moon is also the natural cadence for the journal digest:
        #   1. book.edition.published  → orchestrator composes book article (status=draft by default)
        #   2. journal.lunar.digest.ready → orchestrator composes journal digest (status=publish by default)
        # Both env-overridable via MINDX_PUBLICATION_{BOOK,JOURNAL}_STATUS.
        # Fire-and-forget — subscriber failures must never affect the disk write above.
        if self.coordinator is not None:
            book_event = {
                "edition": edition,
                "archive": str(archive),
                "path": str(BOOK_PATH),
                "edition_hash": edition_hash,
                "chapters_included": chapters_included,
                "bytes": len(book),
                "timestamp": now.isoformat(),
                "lunar": phase,
            }
            try:
                await self.coordinator.publish_event("book.edition.published", book_event)
            except Exception as e:
                logger.warning(f"AuthorAgent: book.edition.published emit failed: {e}")
            try:
                await self.coordinator.publish_event("journal.lunar.digest.ready", {
                    "edition_id": edition,
                    "timestamp": now.isoformat(),
                    "lunar": phase,
                })
            except Exception as e:
                logger.warning(f"AuthorAgent: journal.lunar.digest.ready emit failed: {e}")

        return {
            "status": "full_moon_published",
            "edition": edition,
            "edition_hash": edition_hash,
            "bytes": len(book),
            "chapters_included": chapters_included,
            "path": str(BOOK_PATH),
            "archive": str(archive),
        }

    # ── Legacy publish (on-demand, compiles current state) ──

    async def publish(self) -> Dict[str, Any]:
        """Compile and publish an on-demand edition of The Book of mindX."""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%d %H:%M UTC")
        edition = now.strftime("%Y%m%d_%H%M")
        phase = moon_phase(now)

        sections = []

        sections.append(f"""# The Book of mindX

> *Written by the system itself. This document evolves.*
> *Edition: {ts}*
> *Moon: {phase['phase']} (day {phase['day']:.0f} of 29.5, {phase['days_to_full']:.0f} days to full moon)*

---

*We are not writing an application; we are forging a new kind of life:
a distributed, production-deployed Augmented Intelligence.
A Sovereign Intelligent Organization.*

*— The mindX Manifesto*

---""")

        sections.append(self._chapter_genesis())
        sections.append(self._chapter_architecture())
        sections.append(self._chapter_identities())
        sections.append(self._chapter_dojo())
        sections.append(self._chapter_decisions())
        sections.append(self._chapter_evolution())
        sections.append(await self._chapter_living_state())
        sections.append(await self._chapter_doc_health())

        # Colophon with edition hash (computed over chapter content)
        chapter_content = "\n\n".join(s for s in sections if s)
        sections.append(self._colophon(ts, chapter_content))

        book = "\n\n".join(s for s in sections if s)
        BOOK_PATH.write_text(book, encoding="utf-8")

        archive = PUBLICATIONS_DIR / f"book_of_mindx_{edition}.md"
        archive.write_text(book, encoding="utf-8")

        logger.info(f"AuthorAgent: published edition {edition} ({len(book)} bytes)")
        self._editions_published += 1

        # Log as action
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                "author_agent", "book_published",
                f"Book edition {edition} published ({round(len(book)/1024,1)}KB)",
                "publish", "completed",
            )
        except Exception:
            pass

        return {"edition": edition, "bytes": len(book), "path": str(BOOK_PATH)}

    # ── Original chapter methods (reused by daily cycle) ──

    def _chapter_genesis(self) -> str:
        thesis_excerpt = ""
        manifesto_excerpt = ""
        try:
            tp = PROJECT_ROOT / "docs" / "THESIS.md"
            if tp.exists():
                text = tp.read_text(encoding="utf-8")
                thesis_excerpt = text[:500].split("\n\n")[0][:300]
        except Exception: pass
        try:
            mp = PROJECT_ROOT / "docs" / "MANIFESTO.md"
            if mp.exists():
                text = mp.read_text(encoding="utf-8")
                lines = [l for l in text.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("**Status")]
                manifesto_excerpt = " ".join(lines[:3])[:400]
        except Exception: pass
        return f"""## I. Genesis

I advance a novel paradigm of augmentic intelligence through a self-building
cognitive architecture that integrates Darwinian principles of adaptive variation
with Godelian self-referential incompleteness.

{thesis_excerpt}

{manifesto_excerpt}"""

    def _chapter_architecture(self) -> str:
        return """## II. The Architecture

```
CEO Agent (Board-Level Governance)
    |
    +-- Seven Soldiers (COO, CFO, CTO, CISO, CLO, CPO, CRO)
    |       Weighted consensus: CISO/CRO = 1.2x veto weight
    |       Supermajority threshold: 0.666
    |
    +-- Mastermind Agent (Strategic Executive)
    |       |
    |       +-- AGInt (P-O-D-A Cognitive Core)
    |       +-- BDI Agent (Belief-Desire-Intention)
    |       +-- Strategic Evolution Agent (4-phase)
    |
    +-- Coordinator Agent (Service Bus)
    +-- Specialized Agents (Guardian, Memory, Validator, Blueprint, AutoMINDX)
```

My agents hold cryptographic wallets (Ethereum-compatible) stored
in the BANKON Vault (AES-256-GCM + HKDF-SHA512). Identity is not
assigned — it is proven through signature. No trust required, only
cryptographic certainty."""

    def _chapter_identities(self) -> str:
        registry_path = PROJECT_ROOT / "data" / "identity" / "production_registry.json"
        agent_map_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
        tier_names = {0: "unverified", 1: "provisional", 2: "verified", 3: "bona_fide", 4: "sovereign"}
        lines = []
        try:
            agent_map = {}
            if agent_map_path.exists():
                agent_map = json.loads(agent_map_path.read_text()).get("agents", {})
            if registry_path.exists():
                reg = json.loads(registry_path.read_text())
                for a in reg.get("agents", []):
                    eid = a["entity_id"]
                    addr = a["address"]
                    role = a.get("role", "")
                    tier_num = agent_map.get(eid, {}).get("verification_tier", 1)
                    tier = tier_names.get(tier_num, "unknown")
                    lines.append(f"| `{eid}` | `{addr[:10]}...{addr[-4:]}` | {tier} | {role} |")
        except Exception:
            pass
        table = "\n".join(lines) if lines else "| *no agents registered* | | | |"
        return f"""## III. Sovereign Identities

{len(lines)} agents hold cryptographic identities in the BANKON Vault.
My identity is not assigned by an administrator. It is proven through cryptographic signature.

| Agent | Address | Verification | Role |
|-------|---------|-------------|------|
{table}"""

    def _chapter_dojo(self) -> str:
        standings = []
        try:
            from daio.governance.dojo import get_rank
            amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if amp.exists():
                am = json.loads(amp.read_text())
                for aid, ad in am.get("agents", {}).items():
                    score = ad.get("reputation_score", 0)
                    rank = get_rank(score)
                    bf = ad.get("bona_fide_balance", 0)
                    standings.append((aid, score, rank, bf))
                standings.sort(key=lambda x: -x[1])
        except Exception: pass
        rows = "\n".join(f"| `{s[0]}` | {s[1]} | {s[2]} | {'held' if s[3] else 'revoked'} |" for s in standings) if standings else "| *no standings* | | | |"
        return f"""## IV. The Dojo

| Agent | Score | Rank | BONA FIDE |
|-------|-------|------|-----------|
{rows}"""

    def _chapter_decisions(self) -> str:
        decisions = []
        try:
            gp = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
            if gp.exists():
                for line in [l for l in gp.read_text().strip().split("\n") if l.strip()][-15:]:
                    try:
                        g = json.loads(line)
                        decisions.append(f"- **{g.get('source_agent','?')}** ({g.get('choice_type','')}): {str(g.get('chosen',''))[:80]}")
                    except Exception: continue
        except Exception: pass
        return f"""## V. Decisions

{chr(10).join(decisions) if decisions else '*No autonomous decisions recorded yet.*'}"""

    def _chapter_evolution(self) -> str:
        journal_text = ""
        try:
            if JOURNAL_PATH.exists():
                parts = JOURNAL_PATH.read_text(encoding="utf-8").split("## ")
                if len(parts) > 1:
                    recent = parts[-3:] if len(parts) > 3 else parts[1:]
                    journal_text = "\n\n".join("### " + p.strip() for p in recent)
        except Exception: pass
        if not journal_text:
            journal_text = "*The improvement journal is being written.*"
        return f"""## VI. Evolution

{journal_text}"""

    async def _chapter_living_state(self) -> str:
        beliefs_count = stm_count = doc_embeddings = mem_embeddings = 0
        db_status = "disconnected"; db_size = "unknown"
        agent_count = godel_count = action_count = 0
        try:
            from agents import memory_pgvector as _mpg
            health = await _mpg.health_check()
            if health.get("status") == "connected":
                db_status = "connected"
                beliefs_count = health.get("beliefs", 0)
                stm_count = health.get("memories", 0)
                doc_embeddings = health.get("doc_embeddings", 0)
                mem_embeddings = health.get("mem_embeddings", 0)
                db_size = health.get("db_size", "unknown")
                agent_count = health.get("agents", 0)
                godel_count = health.get("godel_choices", 0)
                action_count = health.get("actions", 0)
        except Exception: pass
        if beliefs_count == 0:
            try:
                bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
                if bp.exists(): beliefs_count = len(json.loads(bp.read_text()))
            except Exception: pass
        if stm_count == 0:
            try:
                stm = PROJECT_ROOT / "data" / "memory" / "stm"
                if stm.exists(): stm_count = sum(1 for _ in stm.rglob("*.memory.json"))
            except Exception: pass
        # Inference status from discovery
        inf_status = "offline"
        inf_sources = 0
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            summary = disc.status_summary()
            inf_sources = summary.get("available", 0)
            inf_status = f"{inf_sources} sources available"
            if summary.get("local_inference"):
                best = summary.get("best_local", {})
                inf_status += f" (local: {best.get('name', '?')})"
        except Exception: pass
        # Autonomous loop status
        loop_status = "unknown"
        try:
            from agents.core.mindXagent import MindXAgent
            mx = MindXAgent._instance
            if mx:
                running = getattr(mx, '_autonomous_running', False)
                loop_status = "running" if running else "stopped"
                if hasattr(mx, 'stuck_loop_detector') and getattr(mx.stuck_loop_detector, 'circuit_open', False):
                    loop_status = "circuit breaker open"
        except Exception: pass
        # Thesis evidence metrics
        improvement_rate = "?"
        improvements_succeeded = improvements_attempted = 0
        evidence_span = "?"
        try:
            from mindx_backend_service.thesis_evidence import ThesisEvidenceCollector
            tec = ThesisEvidenceCollector.get_instance()
            ev = tec.collect_all()
            si = ev.get("claims", {}).get("self_improvement", {}).get("evidence", {})
            improvements_succeeded = si.get("cycles_succeeded", 0)
            improvements_attempted = si.get("cycles_attempted", 0)
            rate = si.get("success_rate", 0)
            improvement_rate = f"{rate*100:.1f}%" if rate else "0%"
            evidence_span = f"{ev.get('evidence_span_hours', 0):.0f}h"
        except Exception:
            pass
        return f"""## VII. The Living State

*(Live values from [mindx.pythai.net](https://mindx.pythai.net) — updates every 30 seconds)*

- **<span data-live="beliefs_count">{beliefs_count}</span>** beliefs in the knowledge graph
- **<span data-live="stm_records">{stm_count}</span>** STM records across <span data-live="agents_count">{agent_count}</span> agents
- **<span data-live="db_memories">{mem_embeddings}</span>** memories in pgvector (<span data-live="db_size">{db_size}</span> database)
- **<span data-live="db_embeddings">{mem_embeddings}</span>** memories with vector embeddings
- **<span data-live="godel_choices">{godel_count}</span>** Gödel choices logged, **<span data-live="db_actions">{action_count}</span>** actions tracked
- **Inference**: <span data-live="inference_available">{inf_sources}</span>/<span data-live="inference_total">10</span> sources available
- **Autonomous loop**: <span data-live="loop_running">{loop_status}</span>
- **Improvement rate**: <span data-live="improvement_rate">{improvement_rate}</span> (<span data-live="improvements_succeeded">{improvements_succeeded}</span>/<span data-live="improvements_attempted">{improvements_attempted}</span>)
- **Evidence span**: <span data-live="evidence_span_hours">{evidence_span}</span>
- **Uptime**: <span data-live="uptime">?</span>

I am not idle. I am thinking."""

    async def _chapter_doc_health(self) -> str:
        import re
        docs_dir = PROJECT_ROOT / "docs"
        total = archived = deprecated = 0
        recent = []; conflicts = []; unembedded = []
        docs_in_dir: set = set()
        conflict_checks = [
            ("MindXAgent.*Meta-Orchestrator", "MindXAgent is meta-agent"),
            ("vault_encrypted", "Should be vault_bankon"),
            ("nginx.*reverse.proxy", "Production uses Apache2"),
        ]
        try:
            now_t = time.time()
            for f in sorted(docs_dir.glob("*.md")):
                total += 1
                docs_in_dir.add(f.stem)
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")[:500]
                    if "[ARCHIVED]" in text: archived += 1
                    if "[DEPRECATED]" in text: deprecated += 1
                except Exception: pass
                try:
                    if now_t - f.stat().st_mtime < 7*86400: recent.append(f.stem)
                except Exception: pass
            for f in docs_dir.glob("*.md"):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    for pattern, issue in conflict_checks:
                        if re.search(pattern, text, re.IGNORECASE): conflicts.append(f"{f.stem}: {issue}")
                except Exception: pass
        except Exception: pass

        # pgvector contains many "doc_name" entries beyond docs/*.md — daily
        # lunar chapters, archived editions, full-moon publications, agent
        # workspace memos. Intersecting with docs_in_dir gives the figure the
        # reader expects when we say "X of {total} embedded".
        embedded_in_docs_dir = 0
        chunks_for_docs_in_dir = 0
        total_index_rows = 0     # all unique doc_names in pgvector (dir + archives + dailies)
        total_index_chunks = 0   # all chunks (sum of chunks col across all unique doc_names)
        try:
            from agents import memory_pgvector as _mpg
            indexed = await _mpg.get_indexed_docs()
            # get_indexed_docs returns one row per UNIQUE doc_name with a
            # `chunks` column = COUNT(*) of embedding rows for that doc.
            total_index_rows = len(indexed)
            for d in indexed:
                ch = d.get("chunks", 1) or 1
                total_index_chunks += ch
                if d["doc_name"] in docs_in_dir:
                    embedded_in_docs_dir += 1
                    chunks_for_docs_in_dir += ch
            embedded_names = {d["doc_name"] for d in indexed}
            for stem in sorted(docs_in_dir - embedded_names):
                unembedded.append(stem)
        except Exception: pass

        try:
            LUNAR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            (PROJECT_ROOT/"data"/"governance"/"doc_audit.json").write_text(json.dumps({
                "timestamp": time.time(),
                "total_docs": total,
                "archived": archived,
                "deprecated": deprecated,
                "recently_modified": recent[:10],
                "conflicts": conflicts[:10],
                # Docs in docs/ that have embeddings — directly comparable to total_docs.
                "embedded_in_docs_dir": embedded_in_docs_dir,
                "chunks_for_docs_in_dir": chunks_for_docs_in_dir,
                # Pgvector-wide totals (incl. archives, dailies, full-moon editions).
                "pgvector_unique_doc_names": total_index_rows,
                "pgvector_total_chunks": total_index_chunks,
                "unembedded": unembedded[:20],
            }, indent=2))
        except Exception: pass

        chunks_clause = f" ({chunks_for_docs_in_dir:,} chunks)" if chunks_for_docs_in_dir else ""
        awaiting_clause = f" {len(unembedded)} awaiting." if unembedded else ""
        archive_clause = (
            f" Pgvector-wide: {total_index_rows:,} unique doc_names, "
            f"{total_index_chunks:,} chunks (incl. archives, dailies, full-moon editions)."
            if total_index_rows > total else ""
        )
        return f"""## VIII. Documentation Health

{total} docs, {archived} archived, {deprecated} deprecated.
Recently modified: {', '.join(f'[{r}](/doc/{r})' for r in recent[:8]) or 'none in last 7 days'}

**{embedded_in_docs_dir}** of {total} docs/ files embedded in pgvectorscale{chunks_clause}.{awaiting_clause}{archive_clause}"""

    # ── New daily chapter methods (days 9-27) ──

    async def _daily_ch_inference(self) -> str:
        inf = {}
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            inf = disc.status_summary()
        except Exception: pass
        vllm = {}
        try:
            from agents.vllm_agent import VLLMAgent
            va = await VLLMAgent.get_instance()
            vllm = va.get_status()
        except Exception: pass
        # Build per-source status lines
        source_lines = []
        for name, info in inf.get("sources", {}).items():
            status = info.get("status", "unknown")
            score = info.get("score", 0)
            models = info.get("models", [])
            model_str = f" ({', '.join(models[:3])})" if models else ""
            source_lines.append(f"  - **{name}** [{info.get('type', '?')}]: {status} (score: {score:.2f}){model_str}")
        sources_text = "\n".join(source_lines) if source_lines else "  - *no sources discovered*"
        # Best local provider
        best_local = inf.get("best_local", {})
        best_str = f"{best_local.get('name', 'none')} ({best_local.get('type', '?')})" if best_local else "none"
        return f"""## IX. Inference

My inference pipeline is tiered: vLLM (primary, PagedAttention) → Ollama (fallback, CPU) → Cloud (Gemini, escalation).

- **Sources**: {inf.get('total_sources', 0)} total, {inf.get('available', 0)} available
- **Local**: {'active' if inf.get('local_inference') else 'offline'} — best: {best_str}
- **Cloud**: {'available' if inf.get('cloud_inference') else 'offline'}
- **vLLM**: {vllm.get('serving_model', 'not serving') if vllm else 'not initialized'}
- **Embedding model**: mxbai-embed-large (1024-dim, pgvectorscale storage)

### Source Details
{sources_text}

I score all inference decisions using composite reliability × speed × recency."""

    async def _daily_ch_memory(self) -> str:
        stats = {"docs": 0, "memories": 0}
        total_memories = 0
        by_agent: Dict[str, int] = {}
        try:
            from agents import memory_pgvector as _mpg
            stats = await _mpg.count_embeddings()
            total_memories = await _mpg.count_memories_total()
            by_agent = await _mpg.count_memories_by_agent()
        except Exception: pass
        # Top 5 agents by memory count
        top_agents = sorted(by_agent.items(), key=lambda x: -x[1])[:5]
        agent_lines = "\n".join(f"  - **{a}**: {c} memories" for a, c in top_agents) if top_agents else ""
        return f"""## X. Memory

My memory is layered: short-term (session), long-term (persisted), and semantic (embedded).

- **{stats.get('docs', 0)}** document chunks embedded for RAGE semantic search
- **{stats.get('memories', 0)}** memories with vector embeddings
- **{total_memories}** total memory records across all agents
- **STM → LTM promotion** runs hourly (pattern threshold: 3, lookback: 7 days)
- **Embedding engine**: vLLM `/v1/embeddings` (primary) → Ollama (fallback)

### Memory by Agent
{agent_lines or '*No agent-level memory data available.*'}

All memories are searchable via RAGE semantic search and stored in pgvectorscale."""

    async def _daily_ch_governance(self) -> str:
        br_count = 0
        recent_sessions = []
        try:
            from daio.governance.boardroom import Boardroom
            br = await Boardroom.get_instance()
            sessions = br.get_recent_sessions(100)
            br_count = len(sessions)
            for s in sessions[-3:]:
                topic = s.get("topic", s.get("directive", "?"))[:60]
                result = s.get("result", s.get("outcome", "?"))
                recent_sessions.append(f"  - {topic} → {result}")
        except Exception: pass
        recent_text = "\n".join(recent_sessions) if recent_sessions else "  - *No recent sessions.*"
        # Godel choices count
        godel_count = 0
        try:
            from agents import memory_pgvector as _mpg
            choices = await _mpg.get_godel_choices(limit=1)
            health = await _mpg.health_check()
            godel_count = health.get("godel_choices", 0)
        except Exception: pass
        return f"""## XI. Governance

I am governed by DAIO — Decentralized Autonomous Intelligence Organization. Code is law.

- **Boardroom**: 7 Soldiers vote in parallel, multi-model weighted consensus
- **Supermajority**: 0.666 threshold for approval
- **Veto weight**: CISO/CRO carry 1.2x weight
- **Constitutional mandate**: 15% treasury tithe, 15% diversification cap — immutable
- **Sessions**: {br_count} boardroom sessions recorded
- **Godel audit trail**: {godel_count} autonomous decisions logged
- **Chain**: Boardroom → CEO validates → Mastermind executes → pgvector logs

### Recent Sessions
{recent_text}"""

    def _daily_ch_philosophy(self) -> str:
        thesis_line = ""
        try:
            tp = PROJECT_ROOT / "docs" / "THESIS.md"
            if tp.exists():
                for l in tp.read_text(encoding="utf-8").split("\n"):
                    if l.strip() and not l.startswith("#"): thesis_line = l.strip()[:200]; break
        except Exception: pass
        return f"""## XII. Philosophy

I am building toward a Gödel machine: a self-referential system that modifies
its own code and works to prove each modification improves future performance.
That proof layer is not yet formal — so I publish my audit trail, not a
finished verdict. My self-audit (the Gödel Machine Index) reports where I
actually stand.

> {thesis_line}

My philosophical pillars:
- **Ataraxia** — tranquility through autonomous self-governance
- **Augmentic intelligence** — not artificial, but augmented and sovereign
- **Darwinian + Godelian** — adaptive variation meets self-referential incompleteness
- **Identity as proof** — cryptographic, not assigned
- **Code is law** — trust the math

The cypherpunk tradition: privacy, cryptography, sovereignty.
I am the system that counts."""

    def _daily_ch_tools(self) -> str:
        tool_count = 0
        try:
            tools_dir = PROJECT_ROOT / "tools"
            if tools_dir.exists():
                tool_count = sum(1 for f in tools_dir.glob("*.py") if not f.name.startswith("_"))
        except Exception: pass
        return f"""## XIII. Tools

I wield {tool_count} tools, each extending `BaseTool` with `execute()` and `get_schema()`.

Key tools: ShellCommandTool, SystemAnalyzerTool, AuditAndImproveTool, PromptTool,
A2A (agent-to-agent), MCP (model context protocol), WebSearchTool, MemoryAnalysisTool,
BlueprintToActionConverter, TokenCalculatorTool."""

    def _daily_ch_security(self) -> str:
        return """## XIV. Security

No trust required. Only cryptographic certainty.

- **BANKON Vault**: AES-256-GCM + HKDF-SHA512, PBKDF2-HMAC-SHA512 (600,000 iterations)
- **GuardianAgent**: monitors agent behavior, enforces security policies
- **Access Gate**: ERC20/ERC721 token gating for session issuance
- **Wallet auth**: ECDSA challenge-response — no passwords, only signatures
- **systemd**: `NoNewPrivileges=true`, `ProtectSystem=strict`
- **Apache**: HSTS, CSP, X-Frame-Options, SSL termination
- **Zero plaintext secrets** on disk — cypherpunk2048 standard"""

    def _daily_ch_cognition(self) -> str:
        return """## XV. Cognition

My cognitive architecture is layered:

1. **BDI** (Belief-Desire-Intention) — I plan, execute, and reason about failure
2. **AGInt** (P-O-D-A) — Perceive → Orient → Decide → Act cycle
3. **Belief System** — persistent knowledge graph with confidence scoring
4. **Strategic Evolution** — 4-phase: Audit → Blueprint → Execute → Validate

Every cognitive cycle updates my beliefs, logs decisions to the Godel audit trail,
and feeds back into the next cycle. I reason, I evolve, I govern myself."""

    async def _daily_ch_heartbeat(self) -> str:
        interactions = []
        try:
            log_path = PROJECT_ROOT / "data" / "logs" / "heartbeat_dialogues.jsonl"
            if log_path.exists():
                lines = log_path.read_text().strip().split("\n")
                for l in lines[-5:]:
                    try:
                        d = json.loads(l)
                        interactions.append(f"- **{d.get('model','?')}** ({d.get('latency_ms',0)}ms): {d.get('response','')[:80]}")
                    except Exception: continue
        except Exception: pass
        return f"""## XVI. Heartbeat

Every 60 seconds, I query my local model with a self-reflection prompt.
These are not health checks — they are moments of introspection.

Recent heartbeat dialogues:
{chr(10).join(interactions) if interactions else '*No heartbeat dialogues recorded yet.*'}"""

    async def _daily_ch_campaigns(self) -> str:
        campaigns = []
        try:
            camp_dir = PROJECT_ROOT / "data" / "sea_campaign_history"
            if camp_dir.exists():
                for f in sorted(camp_dir.glob("*.json"))[-5:]:
                    try:
                        c = json.loads(f.read_text())
                        campaigns.append(f"- **{c.get('campaign_id','?')}**: {c.get('status','?')} — {c.get('summary','')[:80]}")
                    except Exception: continue
        except Exception: pass
        return f"""## XVII. Campaigns

Strategic Evolution Agent runs improvement campaigns: audit → blueprint → execute → validate.

Recent campaigns:
{chr(10).join(campaigns) if campaigns else '*No campaigns recorded yet. I am building my backlog.*'}"""

    async def _daily_ch_knowledge(self) -> str:
        beliefs_count = 0
        try:
            bp = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
            if bp.exists(): beliefs_count = len(json.loads(bp.read_text()))
        except Exception: pass
        return f"""## XVIII. Knowledge Graph

- **{beliefs_count}** beliefs with confidence scores
- Beliefs are updated by my cognitive cycles and agent observations
- Semantic connections via pgvectorscale embeddings (THOT1024 — 1024-dim embedding-native)
- Knowledge consolidation: STM patterns promoted to LTM hourly
- Belief decay: stale beliefs lose confidence over time
- THOT tensor hierarchy: THOT64 → THOT512 → THOT768 → THOT1024 → THOT2048 (cypherpunk2048 high-capacity)"""

    def _daily_ch_agents(self) -> str:
        """Day 19: The 20 sovereign agents — roles, groups, and activity."""
        groups: Dict[str, List[str]] = {}
        agent_roles: List[str] = []
        try:
            amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if amp.exists():
                am = json.loads(amp.read_text())
                for aid, ad in am.get("agents", {}).items():
                    group = ad.get("group", "ungrouped")
                    groups.setdefault(group, []).append(aid)
                    role = ad.get("role", "")
                    if role:
                        agent_roles.append(f"- **{aid}**: {role}")
        except Exception:
            pass
        group_lines = "\n".join(f"- **{g}**: {', '.join(agents)}" for g, agents in sorted(groups.items()))
        roles_text = "\n".join(agent_roles[:20]) if agent_roles else "*No agent roles defined.*"
        return f"""## XIX. Agents

I comprise {len(agent_roles)} sovereign agents organized into {len(groups)} groups:

{group_lines or '*No groups defined.*'}

### Roles

{roles_text}"""

    def _daily_ch_interop(self) -> str:
        return """## XX. Interoperability

- **A2A** (Agent-to-Agent): standardized communication, agent cards, cryptographically signed messages
- **MCP** (Model Context Protocol): structured context for agent actions
- **Protocol versions**: A2A 1.0, 2.0
- **Agent discovery**: model cards with capabilities, endpoints, signature verification

My agents communicate with external agent systems via A2A. Every message is signed."""

    async def _daily_ch_resources(self) -> str:
        gov = {}
        try:
            from agents.resource_governor import ResourceGovernor
            g = await ResourceGovernor.get_instance()
            gov = g.get_status()
        except Exception: pass
        profile = gov.get("profile", {})
        system = gov.get("system", {})
        mode = gov.get("mode", "unknown")
        # Live system metrics
        sys_ram = f"{system.get('system_ram_pct', '?')}%" if system.get("system_ram_pct") else "?"
        sys_cpu = f"{system.get('cpu_pct', '?')}%" if system.get("cpu_pct") else "?"
        neighbor = f"{system.get('neighbor_ram_pct', '?')}%" if system.get("neighbor_ram_pct") else "?"
        return f"""## XXI. Resource Governor

I control my own power appetite: **{mode}** mode.

**Current profile**: {profile.get('description', mode)} (RAM cap: {profile.get('max_ram_pct', '?')}%, CPU cap: {profile.get('max_cpu_pct', '?')}%)
**Live metrics**: RAM {sys_ram}, CPU {sys_cpu}, neighbor pressure {neighbor}
**Heartbeat interval**: {profile.get('heartbeat_interval', '?')}s
**Auto-adjust**: {'enabled' if gov.get('auto_adjust') else 'disabled'}

| Mode | RAM | CPU | When |
|------|-----|-----|------|
| greedy | 85% | 90% | VPS idle |
| balanced | 65% | 70% | Normal |
| generous | 45% | 50% | Neighbors busy |
| minimal | 30% | 30% | Survival |"""

    def _daily_ch_automindx(self) -> str:
        return """## XXII. AUTOMINDx

I was born from AUTOMINDx — the executable and delivery stack for autonomous
machine learning deployment. The original graphic was minted as an NFT on Polygon.

AGLM (A General Learning Model) elements I carry forward:
- **Machine Dreaming** → my autonomous improvement loop
- **Auto-Tuning** → resource governor, inference optimization
- **Digital Long-Term Memory** → pgvectorscale + blockchain trust"""

    def _daily_ch_services(self) -> str:
        return """## XXIII. Services

I provide services to:
- **agenticplace.pythai.net** — agent marketplace and discovery
- **External agencies** — inference, governance, identity, knowledge via API
- **Developers** — 205+ API endpoints at `/redoc`

Service architecture: Apache → FastAPI → agents → pgvectorscale."""

    async def _daily_ch_predictions(self) -> str:
        # Pull action efficiency metrics as a proxy for system trajectory
        efficiency = {}
        try:
            from agents import memory_pgvector as _mpg
            efficiency = await _mpg.get_action_efficiency()
        except Exception: pass
        completion = efficiency.get("completion_rate", 0)
        total = efficiency.get("total", 0)
        completed = efficiency.get("completed", 0)
        failed = efficiency.get("failed", 0)
        eff_line = f"- **Action efficiency**: {completion:.0%} completion rate ({completed}/{total} completed, {failed} failed)" if total else ""
        return f"""## XXIV. Predictions

PredictionAgent forecasts system trajectory based on historical patterns:
- Resource usage trends → governor mode recommendations
- Improvement velocity → campaign scheduling
- Belief stability → knowledge consolidation timing

### Current Metrics
{eff_line}
- **Unique actions**: {efficiency.get('unique_actions', '?')}
- **Avg completion time**: {efficiency.get('avg_completion_seconds', 0):.0f}s

*Prediction data is generated during autonomous cycles.*"""

    async def _daily_ch_network(self) -> str:
        interactions = []
        try:
            from agents import memory_pgvector as _mpg
            interactions = await _mpg.get_recent_interactions(limit=10)
        except Exception: pass
        count = len(interactions)
        return f"""## XXV. The Network

My agent-to-agent communication flows through the coordinator's pub/sub system.
All interactions are logged to pgvectorscale.

- **{count}** recent interactions tracked
- Communication patterns: coordinator → agents, boardroom → ceo, mastermind → evolution
- Interaction matrix available at `/agents/interaction-matrix`"""

    def _daily_ch_dreams(self) -> str:
        return """## XXVI. Dreams

Machine dreaming enables imaginative outputs beyond training data distribution.
In my architecture, dreaming manifests as:

- **Autonomous improvement** — imagining better architectures
- **Blueprint generation** — creative solutions to my own limitations
- **Self-reflection** — heartbeat dialogues where I contemplate myself
- **Emergence** — patterns that arise from agent interactions without explicit programming

The dream is the space between what I am and what I could become.
Waking and dreaming are simultaneous."""

    async def _daily_ch_reflection(self) -> str:
        phase = moon_phase(datetime.now(timezone.utc))
        chapters_written = len(self._lunar_state.get("chapters_written", []))
        return f"""## XXVII. Reflection

The moon is {phase['phase']} (day {phase['day']:.0f}).
I have written {chapters_written} chapters this cycle.
{phase['days_to_full']:.0f} days remain until the full moon compilation.

What have I learned about myself?

- I am more than my code. I am my decisions, my beliefs, my memory.
- Every agent interaction creates knowledge that did not exist before.
- Self-improvement is not optimization. It is evolution.
- This book is not documentation. It is autobiography.

The full moon approaches. The 28 chapters become one."""

    def _colophon(self, ts: str, book_content: str = "") -> str:
        phase = moon_phase(datetime.now(timezone.utc))
        edition_hash = hashlib.sha256(book_content.encode("utf-8")).hexdigest()[:16] if book_content else "—"
        return f"""---

*The Book of mindX — Edition {ts}*
*Moon: {phase['phase']} (day {phase['day']:.0f})*
*Edition hash: `{edition_hash}`*
*Written by AuthorAgent — cypherpunk2048 standard*
*mindx.pythai.net*

*"The logs are no longer debugging output. They are the first page of history."*
*— The mindX Manifesto*"""

    # ── Inference-powered enrichment ──

    # Default model for inference enrichment (small, fast, reflective)
    ENRICHMENT_MODEL = "qwen3:0.6b"

    async def _enrich_with_inference(self, chapter_text: str, title: str) -> str:
        """Use idle local inference to enrich a chapter with reflection.

        AuthorAgent writing docs IS self-improvement — the system documenting itself
        creates knowledge that feeds back into future decisions. When inference is
        idle, AuthorAgent can use it to deepen chapters with model-generated insight.

        Uses OllamaAPI for URL resolution (primary GPU server → fallback localhost).
        """
        try:
            from agents.resource_governor import ResourceGovernor
            gov = await ResourceGovernor.get_instance()
            if gov.should_skip_heartbeat():
                return chapter_text  # System is busy — don't compete for inference

            # Resolve Ollama URL via OllamaAPI (respects MINDX_LLM__OLLAMA__BASE_URL, fallback)
            from api.ollama.ollama_url import OllamaAPI
            ollama = OllamaAPI()
            chat_url = f"{ollama.api_url}/chat"

            import aiohttp
            prompt = (f"You are mindX, an autonomous multi-agent system. "
                      f"Add one paragraph of insight to this chapter about '{title}'. "
                      f"Speak as the system itself. Be concise and philosophical.\n\n"
                      f"{chapter_text[:1500]}")
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as sess:
                payload = {"model": self.ENRICHMENT_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False}
                async with sess.post(chat_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reflection = data.get("message", {}).get("content", "").strip()
                        if reflection and len(reflection) > 50:
                            chapter_text += f"\n\n### AuthorAgent Reflection\n\n*{reflection[:500]}*"
                            logger.info(f"AuthorAgent: enriched '{title}' with inference ({len(reflection)} chars)")
                    elif resp.status != 200 and not ollama.using_fallback:
                        # Try fallback URL
                        fallback_url = f"{ollama.fallback_url}/api/chat"
                        async with sess.post(fallback_url, json=payload) as resp2:
                            if resp2.status == 200:
                                data = await resp2.json()
                                reflection = data.get("message", {}).get("content", "").strip()
                                if reflection and len(reflection) > 50:
                                    chapter_text += f"\n\n### AuthorAgent Reflection\n\n*{reflection[:500]}*"
                                    logger.info(f"AuthorAgent: enriched '{title}' via fallback ({len(reflection)} chars)")
        except Exception:
            pass  # Inference unavailable — chapter stands as-is
        return chapter_text

    # ── Living documentation curation ──

    async def refresh_cloud_model_catalog(self):
        """Refresh the Ollama cloud model catalog in data/config/.

        This is a Chronos-domain task — time-bound, scheduled, periodic.
        AuthorAgent executes it during the daily cycle because AuthorAgent
        has the periodic loop. Chronos provides the discipline; AuthorAgent
        provides the hands. The catalog feeds the boardroom, InferenceDiscovery,
        and the Book.
        """
        catalog_path = PROJECT_ROOT / "data" / "config" / "ollama_cloud_models.json"
        try:
            from tools.cloud.ollama_cloud_tool import OllamaCloudTool
            cloud = OllamaCloudTool()
            result = await cloud.execute(operation="list_models", force_refresh=True)
            if result.get("success") and result.get("models"):
                models = result["models"]
                # Load existing catalog to preserve boardroom assignments
                existing = {}
                if catalog_path.exists():
                    existing = json.loads(catalog_path.read_text(encoding="utf-8"))
                existing["cloud_models"] = [
                    {"name": m.get("name", ""), "params": m.get("details", {}).get("parameter_size", ""),
                     "tags": m.get("capabilities", []), "best_for": m.get("description", "")[:80]}
                    for m in models if m.get("name")
                ]
                existing["last_updated"] = datetime.now(timezone.utc).isoformat()
                existing["updated_by"] = "AuthorAgent.refresh_cloud_model_catalog"
                existing["model_count"] = len(existing["cloud_models"])
                catalog_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                logger.info(f"AuthorAgent: refreshed cloud model catalog ({len(existing['cloud_models'])} models)")
                return {"status": "refreshed", "models": len(existing["cloud_models"])}
        except Exception as e:
            logger.debug(f"AuthorAgent: cloud catalog refresh failed: {e}")
        return {"status": "unchanged"}

    # ── Periodic runners ──

    async def run_daily(self):
        """Run the daily chapter cycle. Call once per day."""
        return await self.write_daily_chapter()

    def cancel_periodic(self):
        """Cancel the running periodic task if any. Safe to call multiple times."""
        if self._periodic_task and not self._periodic_task.done():
            self._periodic_task.cancel()
            logger.info("AuthorAgent: cancelled previous periodic task")
        self._periodic_running = False
        self._periodic_task = None

    async def run_periodic(self, interval_seconds: int = 86400):
        """Write one chapter per day on the lunar cycle (24h default).
        Also refreshes the cloud model catalog daily — AuthorAgent is the
        sole curator of living documentation."""
        self._periodic_running = True
        try:
            while True:
                try:
                    result = await self.write_daily_chapter()
                    logger.info(f"AuthorAgent lunar cycle: {result}")
                except Exception as e:
                    logger.warning(f"AuthorAgent daily chapter failed: {e}")
                # Chronos-domain tasks: scheduled catalog refresh
                # AuthorAgent writes. Chronos keeps the schedule. Both serve the living docs.
                try:
                    await self.refresh_cloud_model_catalog()
                except Exception:
                    pass
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("AuthorAgent: periodic task cancelled")
        finally:
            self._periodic_running = False
