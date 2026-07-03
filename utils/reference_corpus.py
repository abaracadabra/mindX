# mindx/utils/reference_corpus.py
"""Reference corpus — the private docs/ subtrees mindX ingests but does not publish.

Single source of truth for which parts of docs/ are *reference material*:
research dropped in for mindX to absorb (pgvector/RAGE embedding + memory
records) before AuthorAgent ever rewrites it for the public surface. These
subtrees must never be linked from /docs.html, listed in DOC_INDEX.md
subtrees, surfaced through the public /chat/docs RAG endpoint, or served by
/doc/ without a session.

Stdlib-only on purpose — imported by main_service, author_agent, and scripts.
"""
from pathlib import Path
from typing import Iterator, Tuple

# docs/-relative posix prefixes that are gated. Order: most-specific first is
# not required (matching is independent), but keep publications/pdf/ explicit —
# publications/*.md and publications/daily/ stay public.
PRIVATE_DOC_PREFIXES: Tuple[str, ...] = (
    "operations/",
    "blockchain/",
    "publications/pdf/",
)

# Directory names never served, listed, or ingested. node_modules matters:
# extracted codebases live inside the corpus (e.g. operations/dev/IDC/iDEBT)
# and would otherwise flood the catalogue with tens of thousands of files.
EXCLUDE_DIR_NAMES = {"__pycache__", "node_modules", ".git"}
# Saved-web-page asset directories ("Some Article_files/") are noise.
EXCLUDE_DIR_SUFFIXES = ("_files",)
EXCLUDE_FILE_SUFFIXES = (".pyc",)


def _normalize(relpath: str) -> str:
    p = relpath.replace("\\", "/").lstrip("/")
    while p.startswith("./"):
        p = p[2:]
    return p


def is_private_doc(relpath: str) -> bool:
    """True when a docs/-relative path falls under a gated reference subtree.

    Case-insensitive because /doc/{name} resolves filenames case-insensitively.
    Accepts paths with or without extension ("operations/HARD_GATE_RUNBOOK").
    """
    p = _normalize(relpath).lower()
    if not p.endswith("/"):
        # bare folder references ("operations") count as private too
        p_dir = p + "/"
    else:
        p_dir = p
    return any(p.startswith(prefix) or p_dir == prefix for prefix in PRIVATE_DOC_PREFIXES)


def _is_excluded(rel: Path) -> bool:
    for part in rel.parts[:-1]:
        if part in EXCLUDE_DIR_NAMES or part.startswith(".") or part.endswith(EXCLUDE_DIR_SUFFIXES):
            return True
    name = rel.name
    return name.startswith(".") or name.endswith(EXCLUDE_FILE_SUFFIXES)


def iter_reference_docs(docs_dir: Path) -> Iterator[Tuple[str, Path]]:
    """Yield (relpath, path) for every file under the private prefixes."""
    for relpath, path in iter_unlinked_docs(docs_dir):
        if is_private_doc(relpath):
            yield relpath, path


def iter_unlinked_docs(docs_dir: Path) -> Iterator[Tuple[str, Path]]:
    """Yield (relpath, path) for every docs/ file /docs.html does NOT link:
    all files inside subdirectories (recursive) plus top-level non-markdown.
    """
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        return
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(docs_dir)
        if _is_excluded(rel):
            continue
        if len(rel.parts) == 1 and rel.suffix.lower() == ".md":
            continue  # top-level *.md — already linked on /docs.html
        yield rel.as_posix(), path
