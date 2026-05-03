# agents/model_catalogue.py
"""
ModelCatalogue — live model intelligence sourced from ollama.com/library.

Pulls the registry index plus each model's page, extracts:
  - sizes (parameter counts)
  - tag variants (so we know exactly what `ollama pull/run` to use)
  - capability chips (vision / tools / thinking / cloud / embedding)
  - description
  - pull count + updated timestamp

Then derives `skills` heuristically — the layer the rest of mindX uses to
pick the best model per task class. Persisted to
`data/config/ollama_library_catalogue.json`. The free-tier router and the
boardroom dispatcher consult this file at request time.

CLI:
    python -m agents.model_catalogue refresh [--limit N]
    python -m agents.model_catalogue list <task_kind>
    python -m agents.model_catalogue show <model_name>
    python -m agents.model_catalogue local
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiohttp

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

LIBRARY_INDEX = "https://ollama.com/library"
MODEL_PAGE = "https://ollama.com/library/{name}"
CATALOGUE_PATH = PROJECT_ROOT / "data" / "catalogue" / "ollama_library.json"
CATALOGUE_TTL_SECONDS = 24 * 3600
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 mindX-model-catalogue/1.0"
)
FETCH_CONCURRENCY = 6
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=45, connect=10)
FETCH_RETRIES = 2

KNOWN_CAPABILITIES = ("vision", "tools", "thinking", "cloud", "embedding")

# Tags this catalogue is allowed to pull from a model page link, sorted so
# `latest` always wins and explicit sizes outrank "instruct"/"chat" suffixes
# when ranking. (We just collect; ranking is done at routing time.)
TAG_LINK_RE = re.compile(r'<a[^>]*href="/library/([^":]+):([^"#?]+)"', re.IGNORECASE)
INDEX_LINK_RE = re.compile(r'href="/library/([a-z0-9][a-z0-9\.\-_]+?)"', re.IGNORECASE)
SIZE_SPAN_RE = re.compile(r'<span[^>]*x-test-size[^>]*>([^<]+)</span>', re.IGNORECASE)
CAPABILITY_SPAN_RE = re.compile(
    r'<span[^>]*class="inline-flex[^"]*"[^>]*>(' + "|".join(KNOWN_CAPABILITIES) + r')</span>',
    re.IGNORECASE,
)
DESC_META_RE = re.compile(
    r'<meta[^>]+name="description"[^>]+content="([^"]*)"', re.IGNORECASE
)
PULL_COUNT_RE = re.compile(r'<span[^>]*x-test-pull-count[^>]*>([^<]+)</span>', re.IGNORECASE)
UPDATED_RE = re.compile(r'<span[^>]*x-test-updated[^>]*>([^<]+)</span>', re.IGNORECASE)


def _parse_humanized_count(s: str) -> Optional[int]:
    """'28.2M' -> 28_200_000; '1.4K' -> 1_400; '930' -> 930."""
    if not s:
        return None
    m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([kmbg]?)\s*$", s.strip().lower())
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    mult = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "g": 1_000_000_000}.get(unit, 1)
    return int(val * mult)


def _parse_size_to_billions(s: str) -> Optional[float]:
    """'7b' -> 7.0; '0.6b' -> 0.6; '270m' -> 0.27; '120b' -> 120."""
    if not s:
        return None
    m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([bm])\s*", s.lower())
    if not m:
        return None
    val = float(m.group(1))
    return val / 1000.0 if m.group(2) == "m" else val


@dataclass
class ModelEntry:
    name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)        # raw tag strings as registered
    sizes_b: List[float] = field(default_factory=list)   # numeric param sizes in billions
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)      # derived
    strengths: List[str] = field(default_factory=list)   # derived, human-readable
    weaknesses: List[str] = field(default_factory=list)  # derived, human-readable
    pulls: Optional[int] = None
    updated: str = ""
    is_cloud: bool = False
    fetched_at: float = 0.0

    def smallest_b(self) -> Optional[float]:
        return min(self.sizes_b) if self.sizes_b else None

    def biggest_b(self) -> Optional[float]:
        return max(self.sizes_b) if self.sizes_b else None

    def recommended_tag(self, max_size_gb: Optional[float] = None) -> str:
        """Pick a sensible tag for `ollama pull` / `ollama run`.

        - Cloud models: prefer the `:cloud` (or `*-cloud`) tag.
        - Otherwise: prefer the smallest size that fits `max_size_gb` (rough
          heuristic: 1 B ≈ 0.6 GB at q4_k_m).
        """
        if self.is_cloud:
            for t in self.tags:
                if t.endswith("cloud"):
                    return t
        # Map size→tag back to the original tag string.
        size_tags: List[tuple] = []
        for t in self.tags:
            b = _parse_size_to_billions(t)
            if b is not None:
                size_tags.append((b, t))
        if size_tags:
            size_tags.sort()
            if max_size_gb is None:
                return size_tags[0][1]  # smallest by default
            cap_b = max_size_gb / 0.6
            for b, t in size_tags:
                if b <= cap_b:
                    return t
            return size_tags[0][1]
        return "latest"

    def pull_cmd(self, tag: Optional[str] = None) -> str:
        t = tag or self.recommended_tag()
        return f"ollama pull {self.name}:{t}"

    def run_cmd(self, tag: Optional[str] = None) -> str:
        t = tag or self.recommended_tag()
        return f"ollama run {self.name}:{t}"


def _derive_skills(entry: ModelEntry) -> List[str]:
    skills = set()
    name_l = entry.name.lower()
    desc_l = entry.description.lower()
    caps = {c.lower() for c in entry.capabilities}

    if "vision" in caps:
        skills.add("vision")
    if "tools" in caps:
        skills.add("agentic")
    if "thinking" in caps:
        skills.add("reasoning")
    if "embedding" in caps or any(p in name_l for p in ("embed", "bge-", "minilm", "nomic", "mxbai", "all-minilm")):
        skills.add("embedding")

    if any(p in name_l for p in ("code", "coder", "codestral", "devstral", "starcoder", "wizardcoder")):
        skills.add("code")
    if "granite-code" in name_l or "granitecode" in name_l:
        skills.add("code")

    if any(p in desc_l for p in ("reasoning", "math", "problem-solv", "logic")):
        skills.add("reasoning")
    if any(p in desc_l for p in ("agentic", "agent ", "tool-use", "tool use")):
        skills.add("agentic")
    if any(
        p in desc_l
        for p in ("1m token", "1 million token", "million-token", "million token", "128k", "256k", "long context", "long-context")
    ):
        skills.add("long_context")
    if any(p in desc_l for p in ("multilingual", "multi-lingual", "languages", "translation")):
        skills.add("multilingual")

    if entry.smallest_b() is not None:
        if entry.smallest_b() <= 3:
            skills.add("fast")
            skills.add("edge")
        if entry.biggest_b() is not None and entry.biggest_b() >= 30:
            skills.add("heavy")
        if not skills and entry.biggest_b() is not None and entry.biggest_b() >= 7:
            skills.add("general")

    if not skills:
        skills.add("general")
    return sorted(skills)


def _derive_strengths_weaknesses(entry: ModelEntry) -> tuple:
    """Plain-language strengths and weaknesses derived from skills + size."""
    sk = set(entry.skills)
    s, w = [], []

    if "code" in sk:
        s.append("code generation and review")
    if "reasoning" in sk:
        s.append("multi-step reasoning")
    if "agentic" in sk:
        s.append("tool use and agentic workflows")
    if "vision" in sk:
        s.append("image and document understanding")
    if "long_context" in sk:
        s.append("long-document analysis")
    if "embedding" in sk:
        s.append("vector embeddings (no chat completion)")
    if "fast" in sk and "edge" in sk:
        s.append("low latency and small memory footprint")
    if "heavy" in sk:
        s.append("highest-capability deliberation")
    if "multilingual" in sk:
        s.append("multilingual generation")

    if entry.smallest_b() is not None and entry.smallest_b() <= 1.5 and "reasoning" not in sk:
        w.append("limited multi-step reasoning depth")
    if entry.biggest_b() is not None and entry.biggest_b() >= 30:
        w.append("high latency / heavy memory load")
    if "long_context" not in sk and entry.biggest_b() is not None and entry.biggest_b() >= 7:
        w.append("typical 8k–32k context window — not a long-doc model")
    if "vision" not in sk and "embedding" not in sk:
        w.append("text-only (no image input)")
    if "embedding" in sk:
        w.append("not a chat model — completions will be empty")
    if entry.is_cloud:
        w.append("requires Ollama Cloud auth and counts against rate limits")

    return s, w


# ── Fetching ──────────────────────────────────────────────────────────────


async def _fetch(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Fetch with retry. Surfaces last error at WARNING so refresh stalls are diagnosable."""
    last_err: Optional[str] = None
    for attempt in range(FETCH_RETRIES + 1):
        try:
            async with session.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=FETCH_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    last_err = f"HTTP {resp.status}"
                    if attempt < FETCH_RETRIES:
                        await asyncio.sleep(1.0 + attempt)
                        continue
                    logger.warning(f"catalogue fetch {url} -> {last_err}")
                    return None
                return await resp.text()
        except Exception as e:
            last_err = repr(e)
            if attempt < FETCH_RETRIES:
                await asyncio.sleep(1.0 + attempt)
                continue
            logger.warning(f"catalogue fetch {url} failed after {attempt + 1} attempts: {last_err}")
            return None
    return None


def _parse_index(html: str) -> List[str]:
    """Extract unique base model names from the library index."""
    names = set()
    for m in INDEX_LINK_RE.finditer(html):
        n = m.group(1).strip().lower()
        # Drop obvious non-model paths (search, blog, etc.)
        if n in {"library", "search", "models", "blog", "download", "discover", "api"}:
            continue
        names.add(n)
    return sorted(names)


def _parse_model_page(name: str, html: str) -> ModelEntry:
    entry = ModelEntry(name=name, fetched_at=time.time())
    if not html:
        return entry

    m = DESC_META_RE.search(html)
    if m:
        entry.description = m.group(1).strip()

    sizes = []
    for s in SIZE_SPAN_RE.findall(html):
        b = _parse_size_to_billions(s)
        if b is not None:
            sizes.append(b)
    entry.sizes_b = sorted(set(sizes))

    tags = set()
    for m in TAG_LINK_RE.finditer(html):
        base, tag = m.group(1).lower(), m.group(2).lower()
        if base == name.lower():
            tags.add(tag)
    entry.tags = sorted(tags)

    caps = {c.lower() for c in CAPABILITY_SPAN_RE.findall(html)}
    entry.capabilities = sorted(caps)
    entry.is_cloud = "cloud" in caps or any(t.endswith("cloud") for t in entry.tags)

    pc = PULL_COUNT_RE.search(html)
    if pc:
        entry.pulls = _parse_humanized_count(pc.group(1))

    up = UPDATED_RE.search(html)
    if up:
        entry.updated = up.group(1).strip()

    entry.skills = _derive_skills(entry)
    entry.strengths, entry.weaknesses = _derive_strengths_weaknesses(entry)
    return entry


# ── Top-level catalogue ──────────────────────────────────────────────────


class ModelCatalogue:

    def __init__(self, path: Path = CATALOGUE_PATH, ttl: int = CATALOGUE_TTL_SECONDS):
        self.path = path
        self.ttl = ttl

    # --- Persistence ---

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"catalogue load failed: {e}")
            return {}

    def save(self, data: Dict[str, Any]):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def is_fresh(self) -> bool:
        d = self.load()
        return bool(d) and (time.time() - float(d.get("fetched_at", 0))) < self.ttl

    # --- Fetching ---

    async def refresh(self, limit: Optional[int] = None) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            index_html = await _fetch(session, LIBRARY_INDEX)
            if index_html is None:
                logger.warning("catalogue refresh: index fetch failed; keeping existing data")
                return self.load()
            names = _parse_index(index_html)
            if limit:
                names = names[: int(limit)]
            logger.info(f"catalogue refresh: {len(names)} models discovered")

            sem = asyncio.Semaphore(FETCH_CONCURRENCY)

            async def fetch_one(n: str) -> ModelEntry:
                async with sem:
                    html = await _fetch(session, MODEL_PAGE.format(name=n))
                    return _parse_model_page(n, html or "")

            entries = await asyncio.gather(*(fetch_one(n) for n in names))

        # ─ De-dup by (name) preferring richest entry ─
        catalogue: Dict[str, Any] = {
            "fetched_at": time.time(),
            "source": LIBRARY_INDEX,
            "model_count": len(entries),
            "models": {e.name: asdict(e) for e in entries},
        }
        # Build a skill index for fast routing.
        skill_index: Dict[str, List[str]] = {}
        for e in entries:
            for s in e.skills:
                skill_index.setdefault(s, []).append(e.name)
        for v in skill_index.values():
            v.sort()
        catalogue["skill_index"] = skill_index
        self.save(catalogue)
        logger.info(f"catalogue refresh: saved {len(entries)} models to {self.path}")
        return catalogue

    # --- Routing ---

    def get_for_task(
        self,
        task_kind: str,
        prefer_local: bool = True,
        max_size_gb: Optional[float] = None,
        cloud_ok: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return ranked candidates for a task.

        Ranking:
          - Filter to models whose `skills` include the requested task or a synonym.
          - Prefer non-cloud (local) when `prefer_local=True`.
          - Within each tier, prefer smaller models for fast tasks, larger for
            heavy tasks. `max_size_gb` filters out models that won't fit.
        """
        data = self.load()
        models: Dict[str, Dict[str, Any]] = data.get("models", {}) or {}
        if not models:
            return []

        synonyms = {
            "agentic_general": {"agentic", "general"},
            "long_context_1m": {"long_context"},
            "code": {"code"},
            "reasoning": {"reasoning"},
            "vision": {"vision"},
            "embedding": {"embedding"},
            "fast_general": {"fast", "general", "edge"},
            "heavy": {"heavy"},
        }
        wanted = synonyms.get(task_kind, {task_kind})

        candidates: List[Dict[str, Any]] = []
        for name, m in models.items():
            mskills = set(m.get("skills") or [])
            if not (wanted & mskills):
                continue
            if not cloud_ok and m.get("is_cloud"):
                continue
            sizes = m.get("sizes_b") or []
            if max_size_gb is not None and sizes:
                if min(sizes) * 0.6 > max_size_gb:
                    continue
            candidates.append(m)

        def rank(m: Dict[str, Any]) -> tuple:
            local_first = 0 if (prefer_local and not m.get("is_cloud")) else 1
            sizes = m.get("sizes_b") or [9999]
            size_pref = min(sizes) if task_kind in {"fast_general", "embedding"} else -max(sizes)
            popularity = -(m.get("pulls") or 0)
            return (local_first, size_pref, popularity, m.get("name") or "")

        candidates.sort(key=rank)
        return candidates

    # --- Local introspection ---

    async def local_pulled(self, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query the local Ollama daemon for installed models."""
        url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
        try:
            async with aiohttp.ClientSession() as session:
                html = await _fetch(session, url)
                if not html:
                    return []
                d = json.loads(html)
                return d.get("models") or []
        except Exception as e:
            logger.debug(f"local_pulled failed: {e}")
            return []


# ── CLI ───────────────────────────────────────────────────────────────────


def _cli_show(name: str):
    cat = ModelCatalogue().load()
    m = (cat.get("models") or {}).get(name)
    if not m:
        print(f"No entry for '{name}'. Run `python -m agents.model_catalogue refresh` first.")
        return
    print(f"# {m['name']}")
    if m.get("description"):
        print(m["description"])
    if m.get("sizes_b"):
        sizes = ", ".join(f"{b}B" for b in m["sizes_b"])
        print(f"sizes:        {sizes}")
    if m.get("tags"):
        print(f"tags:         {', '.join(m['tags'])}")
    if m.get("capabilities"):
        print(f"capabilities: {', '.join(m['capabilities'])}")
    print(f"skills:       {', '.join(m.get('skills') or [])}")
    if m.get("strengths"):
        print("strengths:")
        for s in m["strengths"]:
            print(f"  - {s}")
    if m.get("weaknesses"):
        print("weaknesses:")
        for w in m["weaknesses"]:
            print(f"  - {w}")
    if m.get("pulls"):
        print(f"pulls:        {m['pulls']:,}")
    if m.get("updated"):
        print(f"updated:      {m['updated']}")
    entry = ModelEntry(**{k: v for k, v in m.items() if k in ModelEntry.__dataclass_fields__})
    print(f"pull:         {entry.pull_cmd()}")
    print(f"run:          {entry.run_cmd()}")


def _cli_list(task: str):
    cat = ModelCatalogue()
    rows = cat.get_for_task(task)
    if not rows:
        print(f"No matches for task '{task}'. Try refresh, or one of:")
        d = cat.load()
        skills = sorted((d.get("skill_index") or {}).keys())
        print("  " + ", ".join(skills))
        return
    print(f"{'name':28s}  {'size(B)':10s}  {'cloud':6s}  {'skills':40s}  pulls")
    print("-" * 100)
    for m in rows[:30]:
        sizes = m.get("sizes_b") or []
        s_disp = "-" if not sizes else (f"{min(sizes)}–{max(sizes)}" if len(sizes) > 1 else f"{sizes[0]}")
        print(
            f"{m['name'][:28]:28s}  {s_disp:10s}  "
            f"{'yes' if m.get('is_cloud') else 'no':6s}  "
            f"{', '.join((m.get('skills') or [])[:5])[:40]:40s}  "
            f"{(m.get('pulls') or 0):>12,}"
        )


async def _cli_local():
    cat = ModelCatalogue()
    rows = await cat.local_pulled()
    if not rows:
        print("No local Ollama models found (or daemon not reachable).")
        return
    print(f"{'name':40s}  {'size':>10s}  modified")
    print("-" * 80)
    for m in rows:
        size = m.get("size", 0)
        size_h = f"{size/(1024**3):.2f} GB" if size else "-"
        print(f"{m.get('name',''):40s}  {size_h:>10s}  {m.get('modified_at','')[:19]}")


async def _cli_refresh(limit: Optional[int]):
    cat = ModelCatalogue()
    data = await cat.refresh(limit=limit)
    print(f"refreshed: {data.get('model_count', 0)} models -> {cat.path}")


def main(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(prog="model_catalogue")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("refresh")
    pr.add_argument("--limit", type=int, default=None)
    pl = sub.add_parser("list")
    pl.add_argument("task")
    ps = sub.add_parser("show")
    ps.add_argument("name")
    sub.add_parser("local")
    args = p.parse_args(argv)
    if args.cmd == "refresh":
        asyncio.run(_cli_refresh(args.limit))
    elif args.cmd == "list":
        _cli_list(args.task)
    elif args.cmd == "show":
        _cli_show(args.name)
    elif args.cmd == "local":
        asyncio.run(_cli_local())


if __name__ == "__main__":
    main()
