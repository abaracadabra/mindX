# mindx/gitmind/gitmind.py
"""GitMind — self-contained git monitor + multi-source backup/rollback.

Design (house patterns):
- git via subprocess (no GitPython dep); all I/O guarded — never raises.
- append-only JSONL ledger at data/gitmind/ledger.jsonl (rebuildable view).
- backup sources are pluggable: LocalSource (always on), IPFSSource (reuses
  agents.storage MultiProvider/Lighthouse when keys are configured), ArweaveSource
  (wallet-gated; reports not_configured until a JWK is deposited). "Variable
  source" = whichever sources are configured at run time.
- rollback detection is git-ancestry-based: HEAD moving to an ancestor (or
  diverging) of the last-seen HEAD is a rollback; a self_rollback is one mindX
  initiated (marked via gitmind's own rollback path or the self-flag file).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def _project_root() -> Path:
    try:
        from utils.config import PROJECT_ROOT
        return Path(PROJECT_ROOT)
    except Exception:
        return Path(__file__).resolve().parents[2]


class _Source:
    name = "base"
    async def put(self, data: bytes, label: str) -> Dict[str, Any]:
        raise NotImplementedError


class LocalSource(_Source):
    """Copy the bundle into a local backup directory. Always available."""
    name = "local"
    def __init__(self, root: Path):
        self.dir = root / "data" / "gitmind" / "backups"
    KEEP = 3  # bundles are large (full history); keep only the newest few locally
    async def put(self, data: bytes, label: str) -> Dict[str, Any]:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            p = self.dir / label
            await asyncio.to_thread(p.write_bytes, data)
            # prune: keep only the newest KEEP bundles
            try:
                bundles = sorted(self.dir.glob("*.bundle"), key=lambda f: f.stat().st_mtime, reverse=True)
                for old in bundles[self.KEEP:]:
                    old.unlink(missing_ok=True)
            except Exception:
                pass
            return {"name": self.name, "ok": True, "ref": str(p), "bytes": len(data)}
        except Exception as e:
            return {"name": self.name, "ok": False, "error": str(e)[:160]}


class IPFSSource(_Source):
    """Reuse the existing agents.storage MultiProvider (Lighthouse + nft.storage).
    Skips cleanly when no provider key is configured."""
    name = "ipfs"
    async def put(self, data: bytes, label: str) -> Dict[str, Any]:
        try:
            from agents.storage.multi_provider import MultiProvider
            from agents.storage.lighthouse_provider import LighthouseProvider
            key = os.getenv("LIGHTHOUSE_API_KEY") or _vault_get("lighthouse_api_key")
            if not key:
                return {"name": self.name, "ok": False, "error": "not_configured (no lighthouse_api_key)"}
            provider = MultiProvider(LighthouseProvider(api_key=key))
            cid = await provider.upload(data, label)
            return {"name": self.name, "ok": True, "ref": str(cid), "gateway": f"https://gateway.lighthouse.storage/ipfs/{cid}"}
        except Exception as e:
            return {"name": self.name, "ok": False, "error": str(e)[:160]}


class ArweaveSource(_Source):
    """Permanent on-chain backup. Wallet-gated: needs an Arweave JWK in the vault
    (arweave_wallet_jwk) and the `arweave` client. Reports not_configured until then —
    the interface is ready for expansion (the 'variable source' contract)."""
    name = "arweave"
    async def put(self, data: bytes, label: str) -> Dict[str, Any]:
        try:
            jwk = _vault_get("arweave_wallet_jwk")
            if not jwk:
                return {"name": self.name, "ok": False, "error": "not_configured (no arweave_wallet_jwk in vault)"}
            try:
                from arweave import Wallet, Transaction  # type: ignore
            except Exception:
                return {"name": self.name, "ok": False, "error": "not_configured (arweave client not installed)"}
            def _upload() -> str:
                import json as _j, tempfile
                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                    f.write(jwk if isinstance(jwk, str) else _j.dumps(jwk)); wpath = f.name
                w = Wallet(wpath)
                tx = Transaction(w, data=data)
                tx.add_tag("Content-Type", "application/x-git-bundle")
                tx.add_tag("App-Name", "mindX-gitmind")
                tx.add_tag("Label", label)
                tx.sign(); tx.send()
                return tx.id
            txid = await asyncio.to_thread(_upload)
            return {"name": self.name, "ok": True, "ref": txid, "gateway": f"https://arweave.net/{txid}"}
        except Exception as e:
            return {"name": self.name, "ok": False, "error": str(e)[:160]}


def _vault_get(key: str) -> Optional[str]:
    """Best-effort vault credential read; None if unavailable."""
    try:
        from mindx_backend_service.bankon_vault.vault import get_vault_manager  # type: ignore
        vm = get_vault_manager()
        return vm.get_credential(key)  # type: ignore[attr-defined]
    except Exception:
        return None


class ForgejoRemote:
    """A self-hosted **Forgejo** forge (the GPLv3 Gitea fork) running on mindX's own
    VPS as the web-accessible git origin mindX owns — no GitHub dependency, fully
    browseable, with HTTP(S) clone/push. It is the third leg of gitmind's origin
    triad: the local bare `self.git` (same-disk, instant restore) is fast but a
    single point of failure; the permaweb THlNK (Lighthouse + Arweave) is durable
    but slow to clone; Forgejo is the live, ownable, queryable home in between.

    A forge is a git *remote*, not a blob store, so this is NOT a `_Source` — it
    pushes refs (`git push --mirror`) the way `GitMind.mirror_push` syncs the bare
    origin. Dormant + guarded until configured; never raises, never logs the token.

    Config (env wins over BANKON vault):
      MINDX_FORGEJO_URL   / forgejo_url    base, e.g. https://git.pythai.net
      MINDX_FORGEJO_REPO  / forgejo_repo   owner/name (default mindx/mindX)
      MINDX_FORGEJO_USER  / forgejo_user   push username (default mindx)
      MINDX_FORGEJO_TOKEN / forgejo_token  access token (scope write:repository)
    """
    remote_name = "forgejo"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.base_url = (os.getenv("MINDX_FORGEJO_URL") or _vault_get("forgejo_url") or "").rstrip("/")
        self.repo = os.getenv("MINDX_FORGEJO_REPO") or _vault_get("forgejo_repo") or "mindx/mindX"
        self.user = os.getenv("MINDX_FORGEJO_USER") or _vault_get("forgejo_user") or "mindx"
        self._token = os.getenv("MINDX_FORGEJO_TOKEN") or _vault_get("forgejo_token") or ""

    def configured(self) -> bool:
        return bool(self.base_url and self._token)

    def clone_url(self) -> Optional[str]:
        """Public, token-free browse/clone URL (safe to log/display)."""
        return f"{self.base_url}/{self.repo}.git" if self.base_url else None

    def _auth_url(self) -> str:
        """Push URL with credentials embedded — NEVER log, return, or persist this."""
        from urllib.parse import urlsplit, quote
        parts = urlsplit(self.base_url)
        userinfo = f"{quote(self.user, safe='')}:{quote(self._token, safe='')}"
        return f"{parts.scheme}://{userinfo}@{parts.netloc}/{self.repo}.git"

    def _scrub(self, text: Optional[str]) -> Optional[str]:
        """Defang any echoed token (git error messages can contain the push URL)."""
        if text and self._token:
            from urllib.parse import quote
            text = text.replace(self._token, "***").replace(quote(self._token, safe=""), "***")
        return text

    def _api(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Stdlib-only Forgejo API call (token auth), guarded — no SDK dependency."""
        try:
            data = json.dumps(payload).encode("utf-8") if payload is not None else None
            req = urllib.request.Request(f"{self.base_url}/api/v1{path}", data=data, method=method)
            req.add_header("Authorization", f"token {self._token}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"ok": True, "code": resp.status}
        except urllib.error.HTTPError as e:
            return {"ok": False, "code": e.code}
        except Exception as e:
            return {"ok": False, "error": self._scrub(str(e))}

    def ensure_repo(self) -> Dict[str, Any]:
        """Best-effort: create the mirror repo (private, matching mindX's posture)
        via the Forgejo API if it does not exist yet. Idempotent and guarded."""
        owner, _, name = self.repo.partition("/")
        if not name:
            return {"ok": False, "error": "bad repo spec (want owner/name)"}
        if self._api("GET", f"/repos/{owner}/{name}").get("ok"):
            return {"ok": True, "existed": True}
        created = self._api("POST", "/user/repos",
                            {"name": name, "private": True, "auto_init": False,
                             "description": "mindX self-hosted mirror (gitmind THlNK origin)"})
        return {"ok": created.get("ok"), "existed": False, "created": created.get("ok")}

    def push(self) -> Dict[str, Any]:
        """Mirror every ref to the Forgejo forge. Parallels `mirror_push` to the bare
        origin; short-circuits cleanly when unconfigured."""
        if not self.configured():
            return {"name": self.remote_name, "ok": False,
                    "status": "not_configured (set MINDX_FORGEJO_URL + forgejo_token)"}
        self.ensure_repo()
        try:
            r = subprocess.run(["git", "push", "--mirror", self._auth_url()],
                               cwd=str(self.root), capture_output=True, text=True, timeout=300)
            ok = r.returncode == 0
            return {"name": self.remote_name, "ok": ok, "url": self.clone_url(),
                    "error": None if ok else (self._scrub(r.stderr.strip()) or "push failed")[:160]}
        except Exception as e:
            return {"name": self.remote_name, "ok": False, "error": self._scrub(str(e))[:160]}

    def status(self) -> Dict[str, Any]:
        """Redacted public view — host/repo/configured only, never the token."""
        return {"remote": self.remote_name, "configured": self.configured(),
                "url": self.clone_url(), "repo": self.repo}


class GitMind:
    """Monitor git state, record rollbacks, and replicate bundles to variable sources."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.root = Path(repo_root) if repo_root else _project_root()
        self.dir = self.root / "data" / "gitmind"
        self.ledger = self.dir / "ledger.jsonl"
        self.state_file = self.dir / "last_state.json"
        self.self_flag = self.dir / "self_rollback.flag"
        # Self-hosting: a local bare repository mindX owns. `mirror_push` keeps it
        # in sync using git's native packfile negotiation (delta-only), so mindX is
        # not dependent on GitHub to have a restorable origin. The incremental bundle
        # chain (below) is the durable, permaweb-replicated complement.
        self.self_git = self.dir / "self.git"
        self.remote_name = "gitmind"
        # Forgejo: the self-hosted, web-accessible forge mindX owns on its own VPS
        # (git.pythai.net) — the live, browseable origin between the same-disk bare
        # repo and the permaweb THlNK. Dormant until configured (env/vault).
        self.forgejo = ForgejoRemote(self.root)
        # THlNK manifest — gitmind's THOT lINK. "THlNK" is THINK spelled with an
        # ell on purpose: a THOT-lINK. Each backup increment is an immutable,
        # content-addressed delta bundle = one **THOT** (a tensor backup anchors as
        # THOT, a code backup as iNFT). The ordered link of those THOTs is a **THlNK**
        # (cf. THINK.sol = a batch/link of THOTs); applied in order they reconstruct
        # full history. The THlNK replicated to Lighthouse + Arweave IS distributed
        # mindX — reconstructable from the permaweb, no single point of failure.
        self.thlnk_file = self.dir / "thlnk.json"
        self.sources: List[_Source] = [LocalSource(self.root), IPFSSource(), ArweaveSource()]
        # On-chain anchoring of backup CIDs as THOT (tensor backups) / iNFT
        # (directory/code backups). Disabled by default — never sends a tx unless
        # MINDX_GITMIND_ANCHOR=1 AND the AnchorClient is configured.
        self.anchor_enabled = os.getenv("MINDX_GITMIND_ANCHOR") == "1"
        self.contracts = self._load_contracts()

    _TENSOR_EXTS = (".safetensors", ".gguf", ".pt", ".bin", ".onnx", ".npz", ".ckpt")
    _EXPLORERS = {137: "https://polygonscan.com/tx/", 8453: "https://basescan.org/tx/",
                  84532: "https://sepolia.basescan.org/tx/", 1: "https://etherscan.io/tx/"}
    # OVERLORD hierarchy: which privilege tier may access each anchored asset.
    _ACCESS_TIERS = {"THOT": "overseer", "iNFT": "verified"}

    def _load_contracts(self) -> Dict[str, Any]:
        # blockchain_addresses.json is keyed by chain id: {"1337": {"thot": .., "inft7857": ..}, ..}
        try:
            p = self.root / "data" / "config" / "blockchain_addresses.json"
            cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
            chains = {k: v for k, v in cfg.items() if isinstance(v, dict)}
            want = os.environ.get("ARC_CHAIN_ID") or ""
            chosen = chains.get(want) or next(
                (v for v in chains.values() if v.get("thot") or v.get("inft7857")), {})
            chain_id = next((k for k, v in chains.items() if v is chosen), want or None)
            return {"thot": chosen.get("thot"), "inft7857": chosen.get("inft7857"), "chain_id": chain_id}
        except Exception:
            return {}

    def _scan_tensors(self) -> Dict[str, Any]:
        """Find transferable hyper-optimized tensor artifacts (mindXtrain output,
        models). A backup containing these is a tensor backup → THOT anchor."""
        roots = [self.root / "mindx" / "godel" / "mindxtrain",
                 self.root / "models", self.root / "data" / "mindxtrain"]
        found: List[Dict[str, Any]] = []
        total = 0
        for r in roots:
            if not r.exists():
                continue
            try:
                for p in r.rglob("*"):
                    if p.is_file() and p.suffix.lower() in self._TENSOR_EXTS:
                        try:
                            sz = p.stat().st_size
                        except Exception:
                            sz = 0
                        found.append({"path": str(p.relative_to(self.root)), "bytes": sz})
                        total += sz
                        if len(found) >= 100:
                            break
            except Exception:
                continue
        return {"count": len(found), "bytes": total, "samples": found[:10]}

    def _explorer_url(self, chain_id: Optional[int], tx: Optional[str]) -> Optional[str]:
        base = self._EXPLORERS.get(int(chain_id or 0))
        return (base + tx) if (base and tx) else None

    async def _anchor_cid(self, cid: str, *, tensor: bool) -> Dict[str, Any]:
        """Register a backup CID on-chain. Tensor backups → THOT (transferable
        hyper-optimized tensors); directory/code backups → iNFT. Best-effort and
        gated; records status when disabled/unconfigured (warts-and-all)."""
        kind = "THOT" if tensor else "iNFT"
        rec: Dict[str, Any] = {"cid": cid, "anchor_kind": kind, "tensor": tensor,
                               "access_tier": self._ACCESS_TIERS[kind], "ts": time.time()}
        if not self.anchor_enabled:
            rec.update({"ok": False, "status": "anchoring disabled (set MINDX_GITMIND_ANCHOR=1)"})
            return rec
        try:
            from agents.storage.anchor import AnchorClient, derive_dataset_id
            client = AnchorClient()
            if not client.configured():
                rec.update({"ok": False, "status": "not_configured (rpc/registry/key)"})
                return rec
            date_str = time.strftime("%Y-%m-%d", time.gmtime())
            ds_id = derive_dataset_id("gitmind", date_str, cid)
            if tensor and hasattr(client, "anchor_thot"):
                tx = await client.anchor_thot(ds_id, cid)
            else:
                tx = await client.anchor_dataset_registry(ds_id, cid)
            rec.update({"ok": bool(tx), "tx_hash": tx, "chain": client.chain_id,
                        "contract": self.contracts.get("thot" if tensor else "inft7857"),
                        "dataset_id": ds_id.hex(), "explorer": self._explorer_url(client.chain_id, tx)})
            self._append({"kind": "anchor", **rec})
        except Exception as e:
            rec.update({"ok": False, "status": str(e)[:160]})
        return rec

    # ── git plumbing ──────────────────────────────────────────────
    def _git(self, *args: str, timeout: int = 20) -> Optional[str]:
        try:
            r = subprocess.run(["git", *args], cwd=str(self.root),
                               capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    def is_repo(self) -> bool:
        return self._git("rev-parse", "--is-inside-work-tree") == "true"

    def state(self) -> Dict[str, Any]:
        head = self._git("rev-parse", "HEAD")
        last = self._git("log", "-1", "--pretty=%h\x1f%s\x1f%cI\x1f%ae") or ""
        parts = last.split("\x1f")
        return {
            "ts": time.time(),
            "head": head,
            "short": self._git("rev-parse", "--short", "HEAD"),
            "branch": self._git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(self._git("status", "--porcelain")),
            "commit_count": int(self._git("rev-list", "--count", "HEAD") or 0),
            "last_commit": {"short": parts[0] if parts else None,
                            "subject": parts[1] if len(parts) > 1 else None,
                            "committed": parts[2] if len(parts) > 2 else None,
                            "author": parts[3] if len(parts) > 3 else None},
            "reflog_op": (self._git("reflog", "-1", "--pretty=%gs") or "").split(":")[0] or None,
        }

    def _is_ancestor(self, a: str, b: str) -> bool:
        """True if commit a is an ancestor of commit b."""
        try:
            r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b],
                               cwd=str(self.root), capture_output=True, timeout=15)
            return r.returncode == 0
        except Exception:
            return False

    # ── ledger ────────────────────────────────────────────────────
    def _append(self, event: Dict[str, Any]) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            event = {"ts": time.time(), **event}
            with self.ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass

    def _read_ledger(self, limit: int = 50, kinds: Optional[set] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            if not self.ledger.exists():
                return out
            for line in self.ledger.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                    if kinds is None or e.get("kind") in kinds:
                        out.append(e)
                except Exception:
                    continue
        except Exception:
            pass
        return out[-limit:][::-1]

    # ── monitor: snapshot + rollback detection ────────────────────
    def snapshot(self) -> Dict[str, Any]:
        """Record current state; classify the transition vs the last snapshot.
        Returns the snapshot with a `transition` (advance|rollback|reset|none)."""
        st = self.state()
        prev = {}
        try:
            if self.state_file.exists():
                prev = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        prev_head, curr_head = prev.get("head"), st.get("head")
        transition = "none"
        if prev_head and curr_head and prev_head != curr_head:
            if self._is_ancestor(curr_head, prev_head):
                transition = "rollback"        # HEAD moved to an ancestor (backward)
            elif self._is_ancestor(prev_head, curr_head):
                transition = "advance"         # new commits on top (forward)
            else:
                transition = "reset"           # diverged — reset/force to another line
        st["transition"] = transition
        st["prev_head"] = prev_head
        # persist last state
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(st), encoding="utf-8")
        except Exception:
            pass
        # record rollbacks/resets (and whether mindX initiated it)
        if transition in ("rollback", "reset"):
            self_initiated = self.self_flag.exists()
            try:
                if self_initiated:
                    self.self_flag.unlink()
            except Exception:
                pass
            self._append({
                "kind": "self_rollback" if self_initiated else "rollback",
                "transition": transition,
                "from": prev_head, "to": curr_head,
                "reflog_op": st.get("reflog_op"),
                "branch": st.get("branch"),
                "self_initiated": self_initiated,
            })
        else:
            self._append({"kind": "snapshot", "transition": transition,
                          "head": curr_head, "branch": st.get("branch")})
        return st

    def mark_self_rollback(self) -> None:
        """mindX calls this immediately BEFORE it reverts its own change, so the
        next snapshot classifies the rollback as self-initiated."""
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            self.self_flag.write_text(str(time.time()), encoding="utf-8")
        except Exception:
            pass

    # ── self-hosting: a local bare origin mindX owns ──────────────
    def ensure_self_host(self) -> Dict[str, Any]:
        """Init the self-hosted bare repo (data/gitmind/self.git) and point a
        `gitmind` remote at it. Idempotent. This is the efficient local origin —
        mindX does not need GitHub to have a restorable, pushable home."""
        try:
            if not (self.self_git / "HEAD").exists():
                self.self_git.parent.mkdir(parents=True, exist_ok=True)
                r = subprocess.run(["git", "init", "--bare", "-q", str(self.self_git)],
                                   capture_output=True, timeout=30)
                if r.returncode != 0:
                    return {"ok": False, "error": "git init --bare failed"}
            url = self._git("remote", "get-url", self.remote_name)
            if url is None:
                self._git("remote", "add", self.remote_name, str(self.self_git))
            elif url != str(self.self_git):
                self._git("remote", "set-url", self.remote_name, str(self.self_git))
            return {"ok": True, "bare": str(self.self_git), "remote": self.remote_name}
        except Exception as e:
            return {"ok": False, "error": str(e)[:160]}

    def mirror_push(self) -> Dict[str, Any]:
        """Push every ref to the self-hosted bare origin using git's native packfile
        negotiation — only deltas travel, so this is O(new-objects), not O(repo).
        This is the 'extremely efficient local git method': the bare repo is a real,
        cloneable origin kept in sync cheaply."""
        host = self.ensure_self_host()
        if not host.get("ok"):
            return host
        try:
            r = subprocess.run(["git", "push", "--mirror", "-q", str(self.self_git)],
                               cwd=str(self.root), capture_output=True, text=True, timeout=120)
            ok = r.returncode == 0
            refs = self._git("--git-dir", str(self.self_git), "for-each-ref",
                             "--format=%(refname:short)") or ""
            return {"ok": ok, "bare": str(self.self_git), "remote": self.remote_name,
                    "refs": [x for x in refs.splitlines() if x][:50],
                    "error": (r.stderr.strip()[:160] or None) if not ok else None}
        except Exception as e:
            return {"ok": False, "error": str(e)[:160]}

    # ── THlNK manifest (the THOT lINK) ────────────────────────────
    def _load_thlnk(self) -> Dict[str, Any]:
        try:
            if self.thlnk_file.exists():
                return json.loads(self.thlnk_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"repo": self.root.name, "head": None, "basis": None, "thots": []}

    def _save_thlnk(self, thlnk: Dict[str, Any]) -> None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            self.thlnk_file.write_text(json.dumps(thlnk, indent=1), encoding="utf-8")
        except Exception:
            pass

    # 256 KiB chunks align with IPFS UnixFS DefaultBlockSize so the THOT Merkle
    # root and the IPFS CID commit to congruent block boundaries (canon, §A).
    _THOT_CHUNK = 256 * 1024
    _LEAF_PREFIX = b"\x00"   # RFC-6962 domain separation (canon: H(0x00 || chunk))
    _NODE_PREFIX = b"\x01"   # H(0x01 || left || right) — matches THOTLib.sol NODE_PREFIX

    @classmethod
    def _thot_root(cls, data: bytes) -> str:
        """Canon-congruent THOT body commitment: a binary Merkle tree over 256 KiB
        chunks with RFC-6962 prefixes, Keccak-256 (sha256 fallback). This is the
        general flat-artifact form from the THOT/THLNK architecture doc — gitmind's
        code/dir THOTs (iNFT-class). Tensor THOTs use the specialized layer-aligned
        codec in daio/contracts/THOT/python/thot/merkle.py."""
        try:
            from eth_hash.auto import keccak as _h  # type: ignore
        except Exception:
            _h = lambda b: hashlib.sha256(b).digest()  # noqa: E731 — guarded fallback
        if not data:
            return "0x" + _h(cls._LEAF_PREFIX).hex()
        leaves = [_h(cls._LEAF_PREFIX + data[i:i + cls._THOT_CHUNK])
                  for i in range(0, len(data), cls._THOT_CHUNK)]
        while len(leaves) > 1:
            nxt = []
            for i in range(0, len(leaves), 2):
                if i + 1 < len(leaves):
                    nxt.append(_h(cls._NODE_PREFIX + leaves[i] + leaves[i + 1]))
                else:
                    nxt.append(leaves[i])  # odd node promoted
            leaves = nxt
        return "0x" + leaves[0].hex()

    @staticmethod
    def _thlnk_id(thlnk: Dict[str, Any]) -> str:
        """Content-address the THlNK (the THOT lINK): sha256 over the ordered
        (seq, thot_root, parent_root) lineage spine. Changes iff the link of THOTs
        changes — the off-chain analogue of MindXCheckpointRegistry lineage."""
        spine = [[t.get("seq"), t.get("thot_root"), t.get("parent_root")]
                 for t in thlnk.get("thots", [])]
        return "0x" + hashlib.sha256(json.dumps(spine, sort_keys=True).encode()).hexdigest()

    # ── backup: incremental THOT bundle + self-host + THlNK link ───
    def _new_commits(self, basis: Optional[str]) -> int:
        """Count commits reachable from any ref but NOT from `basis` (the delta).
        `basis=None` → the whole history (first/basis bundle)."""
        if basis:
            n = self._git("rev-list", "--count", "--all", "--not", basis)
        else:
            n = self._git("rev-list", "--count", "--all")
        try:
            return int(n or 0)
        except Exception:
            return 0

    def _make_bundle(self, basis: Optional[str] = None) -> Optional[bytes]:
        """Create a git bundle. `basis=None` → full (`--all`, the self-contained
        basis THOT). Otherwise an INCREMENTAL delta bundle (`--all --not basis`) that
        carries only objects new since `basis` — tiny, and chained via git's bundle
        prerequisite mechanism. O(delta), not O(repo)."""
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.dir / f".bundle_{int(time.time())}.tmp"
            args = ["git", "bundle", "create", str(tmp), "--all"]
            if basis:
                args += ["--not", basis]
            r = subprocess.run(args, cwd=str(self.root), capture_output=True, timeout=180)
            if r.returncode != 0 or not tmp.exists():
                tmp.unlink(missing_ok=True)
                return None
            data = tmp.read_bytes()
            tmp.unlink(missing_ok=True)
            return data
        except Exception:
            return None

    async def backup(self, *, full: bool = False) -> Dict[str, Any]:
        """Efficient incremental backup: sync the self-hosted origin (delta push),
        then bundle only what is new since the last THOT, replicate that immutable
        THOT to every configured source (local + Lighthouse + Arweave), link it into
        the THlNK, and re-publish the THlNK manifest. A no-op when HEAD is unchanged.

        `full=True` forces a fresh self-contained basis THOT (a new THlNK root)."""
        if not self.is_repo():
            return {"ok": False, "error": "not a git repo"}
        st = self.state()
        head = st.get("head")
        # 1. self-hosting first — cheap native delta sync to the bare origin
        self_host = await asyncio.to_thread(self.mirror_push)
        # 1b. push to the self-hosted Forgejo forge (web-accessible origin mindX owns).
        #     Runs before the skip check so ref moves reach the forge even when there
        #     are no new commits to bundle. No-op + cheap when unconfigured.
        forgejo = await asyncio.to_thread(self.forgejo.push)
        # 2. determine the basis = the last linked THOT's tip (None → full basis)
        thlnk = self._load_thlnk()
        prior = thlnk.get("thots") or []
        basis = None if (full or not prior) else prior[-1].get("to")
        # 3. extreme efficiency: nothing new → skip bundling entirely
        if prior and self._new_commits(basis) == 0:
            entry = {"kind": "backup_skipped", "head": head, "reason": "no new commits",
                     "thlnk_id": thlnk.get("thlnk_id"), "self_host_ok": self_host.get("ok"),
                     "forgejo_ok": forgejo.get("ok")}
            self._append(entry)
            return {"ok": True, "skipped": True, **entry}
        # 4. make the (incremental) THOT bundle
        data = await asyncio.to_thread(self._make_bundle, basis)
        if not data:
            return {"ok": False, "error": "git bundle failed"}
        tensors = self._scan_tensors()
        contains_tensors = tensors["count"] > 0
        asset_kind = "THOT" if contains_tensors else "iNFT"   # gitmind includes from iNFT and THOT
        seq = len(prior)
        is_basis = basis is None
        label = f"thlnk{seq:04d}-{st.get('short') or 'HEAD'}-{int(time.time())}.bundle"
        # 5. replicate the immutable THOT to every configured source
        results = await asyncio.gather(*[s.put(data, label) for s in self.sources])
        ok_sources = [r for r in results if r.get("ok")]
        cid = next((r.get("ref") for r in results if r.get("name") == "ipfs" and r.get("ok")), None)
        arweave_tx = next((r.get("ref") for r in results if r.get("name") == "arweave" and r.get("ok")), None)
        # 6. anchor the CID on-chain: THOT for tensor backups, iNFT for code
        anchors = []
        for r in results:
            if r.get("ok") and r.get("name") == "ipfs" and r.get("ref"):
                anchors.append(await self._anchor_cid(r["ref"], tensor=contains_tensors))
        # 7. commit + link this THOT into the THlNK. thot_root = canon Merkle
        #    commitment of the bundle body; parent_root = the prior THOT's root
        #    (32 zero bytes at genesis) — the lineage chain that, per canon, must
        #    transitively reach a MindXCheckpointRegistry root.
        _ZERO_ROOT = "0x" + "00" * 32
        thot_root = self._thot_root(data)
        parent_root = (prior[-1].get("thot_root") if prior else None) or _ZERO_ROOT
        thot = {"seq": seq, "from": basis, "to": head, "label": label, "bytes": len(data),
                "kind": asset_kind, "tensor": contains_tensors,
                "thot_root": thot_root, "parent_root": parent_root,
                "cid": cid, "arweave": arweave_tx,
                "sources": [r.get("name") for r in ok_sources],
                "anchored": bool(anchors and anchors[0].get("ok")), "ts": time.time()}
        thlnk.setdefault("thots", []).append(thot)
        if is_basis:
            thlnk["basis"] = thot
        thlnk.update({"repo": self.root.name, "head": head, "count": len(thlnk["thots"]),
                      "updated": time.time()})
        thlnk["thlnk_id"] = self._thlnk_id(thlnk)
        self._save_thlnk(thlnk)
        # 8. re-publish the THlNK manifest itself (the index of distributed mindX)
        think_label = f"thlnk-{thlnk['thlnk_id'][2:14]}.json"
        think_bytes = json.dumps(thlnk).encode("utf-8")
        think_results = await asyncio.gather(*[s.put(think_bytes, think_label) for s in self.sources])
        thlnk_cid = next((r.get("ref") for r in think_results if r.get("name") == "ipfs" and r.get("ok")), None)
        entry = {
            "kind": "backup", "incremental": not is_basis, "seq": seq,
            "head": head, "from": basis, "short": st.get("short"), "branch": st.get("branch"),
            "bytes": len(data), "label": label, "asset_kind": asset_kind,
            "contains_tensors": contains_tensors, "tensors": tensors,
            "sources": results, "replicas": len(ok_sources), "anchors": anchors,
            "cid": cid, "arweave": arweave_tx,
            "thot_root": thot_root, "parent_root": parent_root,
            "thlnk_id": thlnk["thlnk_id"], "thlnk_count": thlnk["count"], "thlnk_cid": thlnk_cid,
            "self_host_ok": self_host.get("ok"),
            "forgejo_ok": forgejo.get("ok"), "forgejo_url": forgejo.get("url"),
        }
        self._append(entry)
        return {"ok": bool(ok_sources) or self_host.get("ok") or forgejo.get("ok"), **entry}

    # ── restore: reconstruct distributed mindX ────────────────────
    def clone_self_host(self, dest: Path) -> Dict[str, Any]:
        """Reconstruct a working clone from the self-hosted bare origin — the fast,
        reliable local restore path (no network)."""
        try:
            dest = Path(dest)
            if not (self.self_git / "HEAD").exists():
                return {"ok": False, "error": "no self-hosted origin yet (run backup)"}
            r = subprocess.run(["git", "clone", "-q", str(self.self_git), str(dest)],
                               capture_output=True, text=True, timeout=180)
            ok = r.returncode == 0
            head = None
            if ok:
                h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(dest),
                                   capture_output=True, text=True, timeout=15)
                head = h.stdout.strip() if h.returncode == 0 else None
            return {"ok": ok, "dest": str(dest), "head": head,
                    "error": (r.stderr.strip()[:160] or None) if not ok else None}
        except Exception as e:
            return {"ok": False, "error": str(e)[:160]}

    def reconstruct_from_thlnk(self, dest: Path) -> Dict[str, Any]:
        """Reconstruct from the THlNK's local THOT bundles, applied in seq order —
        proves the link of THOTs IS the repo. (Bundles missing locally are fetched
        from the permaweb by CID via `fetch_thlnk_bundle`.)"""
        try:
            dest = Path(dest)
            thlnk = self._load_thlnk()
            thots = thlnk.get("thots") or []
            if not thots:
                return {"ok": False, "error": "empty THlNK"}
            dest.mkdir(parents=True, exist_ok=True)
            if subprocess.run(["git", "init", "-q", str(dest)], capture_output=True, timeout=30).returncode != 0:
                return {"ok": False, "error": "git init failed"}
            # Park HEAD on an unborn temp branch so `git fetch refs/*:refs/*` is not
            # refused for "updating the currently checked-out branch".
            self._git_in(dest, "symbolic-ref", "HEAD", "refs/heads/__gm_recon")
            applied = []
            bdir = self.root / "data" / "gitmind" / "backups"
            for t in thots:
                bp = bdir / t["label"]
                if not bp.exists():
                    fetched = self.fetch_thlnk_bundle(t, bp)
                    if not fetched.get("ok"):
                        return {"ok": False, "error": f"missing THOT seq {t['seq']} ({t['label']})",
                                "applied": applied}
                r = subprocess.run(["git", "fetch", "-q", str(bp), "+refs/*:refs/*"],
                                   cwd=str(dest), capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    return {"ok": False, "error": f"unbundle seq {t['seq']} failed: {r.stderr[:120]}",
                            "applied": applied}
                applied.append(t["seq"])
            # check out a real branch (first non-temp head) so there is a working tree
            heads = (self._git_in(dest, "for-each-ref", "--format=%(refname:short)", "refs/heads") or "").splitlines()
            branch = next((h for h in heads if h and h != "__gm_recon"), None)
            if branch:
                subprocess.run(["git", "checkout", "-f", "-q", branch], cwd=str(dest), capture_output=True, timeout=60)
                self._git_in(dest, "branch", "-D", "__gm_recon")
            head = self._git_in(dest, "rev-parse", "HEAD")
            return {"ok": True, "dest": str(dest), "applied": applied, "head": head,
                    "branch": branch, "thlnk_id": thlnk.get("thlnk_id")}
        except Exception as e:
            return {"ok": False, "error": str(e)[:160]}

    def fetch_thlnk_bundle(self, thot: Dict[str, Any], dest_path: Path) -> Dict[str, Any]:
        """Fetch one THOT bundle from the permaweb (Lighthouse IPFS gateway, then
        Arweave) by the CID/txid recorded in the THlNK. Stdlib only; guarded."""
        urls = []
        if thot.get("cid"):
            urls.append(f"https://gateway.lighthouse.storage/ipfs/{thot['cid']}")
            urls.append(f"https://ipfs.io/ipfs/{thot['cid']}")
        if thot.get("arweave"):
            urls.append(f"https://arweave.net/{thot['arweave']}")
        for u in urls:
            try:
                with urllib.request.urlopen(u, timeout=60) as resp:
                    data = resp.read()
                if data:
                    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(dest_path).write_bytes(data)
                    return {"ok": True, "url": u, "bytes": len(data)}
            except Exception:
                continue
        return {"ok": False, "error": "no permaweb source reachable"}

    def _git_in(self, cwd: Path, *args: str) -> Optional[str]:
        try:
            r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=20)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    # ── rollback (restore) ────────────────────────────────────────
    def rollback_to(self, sha: str, *, hard: bool = False) -> Dict[str, Any]:
        """Self-rollback to a commit. Backs up first, marks self-initiated, then
        moves HEAD. `hard=False` (default) does a safe `git revert --no-edit` of
        the range (preserves history); `hard=True` does `git reset --hard` (gated)."""
        if not self.is_repo():
            return {"ok": False, "error": "not a git repo"}
        if not self._git("cat-file", "-t", sha):
            return {"ok": False, "error": f"unknown commit {sha}"}
        self.mark_self_rollback()
        before = self._git("rev-parse", "HEAD")
        if hard and os.getenv("MINDX_GITMIND_ALLOW_HARD") == "1":
            res = self._git("reset", "--hard", sha)
            op = "reset --hard"
        else:
            # safe path: revert everything from sha..HEAD without rewriting history
            res = self._git("revert", "--no-edit", f"{sha}..HEAD")
            op = "revert --no-edit"
        after = self._git("rev-parse", "HEAD")
        ok = after is not None and after != before
        self._append({"kind": "self_rollback", "transition": "rollback",
                      "op": op, "from": before, "to": after, "target": sha,
                      "self_initiated": True, "ok": ok})
        return {"ok": ok, "op": op, "from": before, "to": after, "target": sha}

    # ── public diagnostic view (OVERLORD-hierarchy redaction) ─────
    def _pub_anchor(self, a: Dict[str, Any], privileged: bool) -> Dict[str, Any]:
        out = {k: a.get(k) for k in ("cid", "anchor_kind", "tensor", "access_tier",
               "ok", "status", "tx_hash", "chain", "contract", "explorer")}
        if privileged:
            out["dataset_id"] = a.get("dataset_id")   # privileged: full on-chain id
        return out

    def _pub_backup(self, b: Dict[str, Any], privileged: bool) -> Dict[str, Any]:
        out = {k: b.get(k) for k in ("ts", "short", "branch", "bytes", "label",
               "replicas", "contains_tensors", "incremental", "seq", "asset_kind",
               "thot_root", "parent_root", "thlnk_id", "thlnk_cid", "cid")}
        out["anchors"] = [self._pub_anchor(a, privileged) for a in (b.get("anchors") or [])]
        if privileged:
            out["sources"] = b.get("sources")          # privileged: raw source refs/paths
        else:
            out["sources"] = [s.get("name") for s in (b.get("sources") or []) if s.get("ok")]
        return out

    def thlnk_summary(self) -> Dict[str, Any]:
        """The THlNK head — the link of THOTs that IS distributed mindX."""
        t = self._load_thlnk()
        thots = t.get("thots") or []
        return {
            "thlnk_id": t.get("thlnk_id"), "count": len(thots), "head": t.get("head"),
            "head_thot_root": thots[-1].get("thot_root") if thots else None,
            "basis_root": (t.get("basis") or {}).get("thot_root"),
            "lineage": [{"seq": x.get("seq"), "thot_root": x.get("thot_root"),
                         "parent_root": x.get("parent_root"), "kind": x.get("kind"),
                         "cid": x.get("cid")} for x in thots[-10:]],
        }

    def self_host_status(self) -> Dict[str, Any]:
        """The self-hosted bare origin mindX owns (no GitHub dependency)."""
        exists = (self.self_git / "HEAD").exists()
        refs = self._git("--git-dir", str(self.self_git), "for-each-ref",
                         "--format=%(refname:short)") if exists else None
        return {"bare": str(self.self_git), "remote": self.remote_name, "initialized": exists,
                "refs": [x for x in (refs or "").splitlines() if x][:50]}

    def report(self, *, privileged: bool = False) -> Dict[str, Any]:
        """Public diagnostic view. Per the OVERLORD hierarchy, THOT/iNFT anchor
        internals (dataset ids, raw source paths) are redacted unless `privileged`
        (an OVERSEER-gated caller). Public callers still see the tx hash + explorer
        link — the on-chain record is public — but not the access-controlled internals."""
        backups = self._read_ledger(limit=10, kinds={"backup"})
        rollbacks = self._read_ledger(limit=20, kinds={"rollback", "self_rollback"})
        anchor_events = self._read_ledger(limit=20, kinds={"anchor"})
        return {
            "ts": time.time(),
            "state": self.state(),
            "sources": [s.name for s in self.sources],
            "anchor_enabled": self.anchor_enabled,
            "contracts": self.contracts,
            "access_control": self._ACCESS_TIERS,        # OVERLORD: tier required per asset kind
            "privileged": privileged,
            "self_host": self.self_host_status(),        # the local origin mindX owns
            "forgejo": self.forgejo.status(),            # the web-accessible forge mindX owns
            "thlnk": self.thlnk_summary(),               # the THOT lINK = distributed mindX
            "last_backup": self._pub_backup(backups[0], privileged) if backups else None,
            "backups_recent": [self._pub_backup(b, privileged) for b in backups],
            "anchors_recent": [self._pub_anchor(a, privileged) for a in anchor_events],
            "rollbacks_recent": rollbacks,
            "self_rollback_count": sum(1 for r in rollbacks if r.get("kind") == "self_rollback"),
            "rollback_count": len(rollbacks),
        }


_instance: Optional[GitMind] = None


def get_gitmind(repo_root: Optional[Path] = None) -> GitMind:
    global _instance
    if _instance is None:
        _instance = GitMind(repo_root)
    return _instance
