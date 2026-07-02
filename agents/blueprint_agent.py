# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""blueprint.agent — the agent that works the Gödel-Machine-Index UI.

Owns the /machine (public index) and /machine/admin (diagnostics) surfaces and the
clean-room blueprint.js renderer. It reads mindX's honest self-audit and turns it
into scientific, corporate-elegant data analysis — the blueprint that sets the
standard for how mindX presents its own measurements.

Toolset (blueprint tools + frontend tools):
  gmi / refresh_gmi           — read the live Gödel Machine Index
  predicate_report            — structured G1–G8 analysis (verdict + evidence)
  coverage_math               — actual vs blueprint thresholds (pass/below gates)
  summary_html / summary_text — deterministic briefs for publications/other agents
  svg_schematic               — an SVG blueprint diagram of the eight predicates
  diff                        — what changed between two audit snapshots
  export_report               — the audit as markdown or json
  blueprint_doc               — the Gödel Eval Blueprint source
  validate_ui                 — the UI assets exist + the JS parses (node)
  frontend_tools              — the available frontend toolchain (node + images)
  optimize_ui_assets          — optimise UI images via artist.agent's image toolchain
"""
from __future__ import annotations

import json
import time
import math
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Version + the growing catalogue of blueprint.agent skills. Each new capability is
# appended here as we discover it; save_version() snapshots (version, skills) to the
# manifest so every version is preserved with the skills it shipped with.
__version__ = "1.4.0"
SKILLS: List[Dict[str, str]] = [
    {"name": "gmi",                "kind": "blueprint", "desc": "read the live Gödel Machine Index"},
    {"name": "predicate_report",   "kind": "blueprint", "desc": "structured G1–G8 analysis (verdict + evidence)"},
    {"name": "coverage_math",      "kind": "blueprint", "desc": "actual vs blueprint thresholds, pass/below gates"},
    {"name": "summary_html/text",  "kind": "blueprint", "desc": "deterministic briefs for publications/agents"},
    {"name": "svg_schematic",      "kind": "blueprint", "desc": "SVG blueprint diagram of the eight predicates"},
    {"name": "diff",               "kind": "blueprint", "desc": "compare two audit snapshots"},
    {"name": "export_report",      "kind": "blueprint", "desc": "export the audit as markdown or json"},
    {"name": "blueprint_doc",      "kind": "blueprint", "desc": "the Gödel Eval Blueprint source"},
    {"name": "validate_ui",        "kind": "frontend",  "desc": "node JS-syntax check of the UI assets"},
    {"name": "frontend_tools",     "kind": "frontend",  "desc": "frontend toolchain inventory"},
    {"name": "optimize_ui_assets", "kind": "frontend",  "desc": "WebP-optimise UI images via artist.agent"},
    {"name": "frontend-design",    "kind": "skill",     "desc": "distinctive corporate/elegant UI direction"},
    {"name": "image-toolchain",    "kind": "skill",     "desc": "mozjpeg/cwebp/avifenc/pngquant/oxipng via artist.agent"},
    {"name": "client-cache",       "kind": "frontend",  "desc": "light sessionStorage GMI cache + deferred substrate"},
    {"name": "analyze_path",       "kind": "analysis",  "desc": "scientific structural analysis of a code directory (LOC, symbols, docstrings)"},
    {"name": "resources",          "kind": "monitoring","desc": "live host resource snapshot (CPU/RAM/disk) via the resource monitor"},
    {"name": "per_core",           "kind": "monitoring","desc": "per-core CPU + RAM observation (percpu)"},
    {"name": "resource_control",   "kind": "control",   "desc": "bounded per-core CPU + RAM load control (governor testing)"},
]

# Interaction mapping — every interaction and the substrate/UI effect it produces,
# catalogued across the realm + machine surfaces as we build them.
INTERACTIONS: List[Dict[str, str]] = [
    {"trigger": "hover CONNECT / logo", "surface": "realm gate", "effect": "doorway morph-warp + glow pulse grows with dwell", "physics": "charge ramp × sine pulse"},
    {"trigger": "cursor move",          "surface": "substrate",  "effect": "gravity well — bodies attract toward the pointer", "physics": "inverse-square, depth-scaled"},
    {"trigger": "hover mindX logo",     "surface": "machine",    "effect": "intelligence substrate attaches — the field gathers to the logo", "physics": "focus attractor"},
    {"trigger": "drag logo",            "surface": "machine",    "effect": "reposition (fixed → free)", "physics": "pointer follow"},
    {"trigger": "scroll on logo",       "surface": "machine",    "effect": "resize 32–320px", "physics": "wheel delta"},
    {"trigger": "click logo",           "surface": "machine",    "effect": "wallet login if a wallet is found (else MetaMask)", "physics": "—"},
    {"trigger": "drag crown",           "surface": "realm gate", "effect": "toroid magic rings on pickup", "physics": "expanding tori"},
    {"trigger": "drop crown on portal", "surface": "realm gate", "effect": "opens wallet login + crown vanishes", "physics": "scale-to-0 fade"},
    {"trigger": "ACCESS GRANTED",       "surface": "realm gate", "effect": "corkscrew-tornado rabbit-hole draw to the THRONE", "physics": "golden-ratio accel→decel"},
    {"trigger": "click predicate card", "surface": "machine",    "effect": "expand evidence JSON", "physics": "—"},
    {"trigger": "page load (deferred)", "surface": "machine",    "effect": "substrate fades in subtle after first paint", "physics": "idle/timeout + opacity ease"},
    {"trigger": "ambient",              "surface": "substrate",  "effect": "cohesive field with depth", "physics": "Hamiltonian well + spring mesh + z-parallax"},
]

try:
    from utils.config import PROJECT_ROOT as _ROOT
except Exception:
    _ROOT = Path(__file__).resolve().parents[1]

_BE = _ROOT / "mindx_backend_service"
_UI = {"index": _BE / "machine.html", "admin": _BE / "machine_admin.html",
       "renderer": _BE / "static" / "blueprint.js"}
_VCOLOR = {"PROVEN": "#5bd97b", "FALSIF": "#ff5c52", "UNTEST": "#e0ab46"}
_PROOF_THRESHOLD = 0.50


def _vkey(v: str) -> str:
    v = (v or "").upper()
    return "PROVEN" if "PROVEN" in v else "FALSIF" if "FALSIF" in v else "UNTEST"


class BlueprintAgent:
    """Stateless; safe to construct ad hoc. Works the Gödel-Machine-Index UI."""

    AGENT_ID = "blueprint.agent"

    # ── blueprint tools ────────────────────────────────────────────────
    def gmi(self) -> Dict[str, Any]:
        """The live Gödel Machine Index (honest self-audit)."""
        try:
            from mindx.godel.eval import compute_gmi
            return compute_gmi()
        except Exception as e:
            return {"verdict": "UNKNOWN", "error": str(e), "predicates": []}

    refresh_gmi = gmi

    def predicate_report(self, gmi: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Structured G1–G8: id, name, verdict, class, detail, evidence-key count."""
        g = gmi or self.gmi()
        out = []
        for p in g.get("predicates", []):
            ev = p.get("evidence") or {}
            out.append({
                "id": p.get("id"), "name": p.get("name"),
                "verdict": p.get("verdict"), "class": _vkey(p.get("verdict", "")),
                "color": _VCOLOR[_vkey(p.get("verdict", ""))],
                "detail": p.get("detail"), "evidence_keys": list(ev.keys()),
            })
        return out

    def coverage_math(self, gmi: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Actual measurements vs the blueprint thresholds, with pass/below gates."""
        g = gmi or self.gmi()
        pc = g.get("proof_coverage", 0.0) or 0.0
        pp = g.get("predicates_proven", 0) or 0
        return {
            "proof_coverage": {"actual": pc, "threshold": _PROOF_THRESHOLD, "pass": pc >= _PROOF_THRESHOLD},
            "surrogate_coverage": {"actual": g.get("surrogate_coverage", 0.0), "threshold": None, "pass": True},
            "predicates_proven": {"actual": pp, "threshold": 8, "pass": pp >= 8},
            "verdict_flips_when": "proof_coverage >= 0.50 AND predicates_proven == 8",
            "blockers": g.get("blockers", []),
        }

    def summary_text(self, gmi: Optional[Dict[str, Any]] = None) -> str:
        g = gmi or self.gmi()
        return (f"{(g.get('verdict') or 'UNKNOWN').replace('_',' ')} · phase {g.get('phase','?')} · "
                f"{g.get('predicates_proven',0)}/8 proven · proof coverage "
                f"{round((g.get('proof_coverage',0) or 0)*100)}% · blockers: "
                f"{', '.join(g.get('blockers',[]) or ['none'])}")

    def summary_html(self, gmi: Optional[Dict[str, Any]] = None) -> str:
        """Deterministic compact HTML brief (for publications / other agents)."""
        g = gmi or self.gmi()
        rows = "".join(
            f'<li><b>{p["id"]}</b> {(p.get("name") or "").replace("_"," ")} — '
            f'<span style="color:{p["color"]}">{p["verdict"]}</span></li>'
            for p in self.predicate_report(g))
        neg = "NOT" in (g.get("verdict") or "") or "FALSIF" in (g.get("verdict") or "")
        return (f'<div class="gmi-brief"><p><strong style="color:{"#ff5c52" if neg else "#5bd97b"}">'
                f'{(g.get("verdict") or "UNKNOWN").replace("_"," ")}</strong> — phase {g.get("phase","?")}, '
                f'{g.get("predicates_proven",0)}/8 predicates proven, proof coverage '
                f'{round((g.get("proof_coverage",0) or 0)*100)}%.</p><ul>{rows}</ul></div>')

    def svg_schematic(self, gmi: Optional[Dict[str, Any]] = None, *, size: int = 520) -> str:
        """An SVG blueprint diagram: the eight predicates on a φ-spaced ring, each
        node coloured by verdict, with a proof-coverage arc at the core."""
        g = gmi or self.gmi()
        preds = self.predicate_report(g)
        cx = cy = size / 2.0
        R = size * 0.36
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
                 f'role="img" aria-label="Gödel Machine Index schematic">',
                 f'<rect width="{size}" height="{size}" fill="#060d17"/>',
                 f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="rgba(120,170,225,.14)" stroke-width="1"/>']
        n = max(1, len(preds))
        for i, p in enumerate(preds):
            a = -math.pi / 2 + 2 * math.pi * i / n
            x, y = cx + R * math.cos(a), cy + R * math.sin(a)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{p["color"]}" opacity="0.9"/>')
            parts.append(f'<text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" '
                         f'font-family="monospace" font-size="10" fill="#060d17" font-weight="700">{p["id"]}</text>')
        pc = g.get("proof_coverage", 0.0) or 0.0
        r2 = R * 0.42
        circ = 2 * math.pi * r2
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r2:.1f}" fill="none" stroke="rgba(120,170,225,.12)" stroke-width="7"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r2:.1f}" fill="none" stroke="#ff5c52" stroke-width="7" '
                     f'stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ*(1-pc):.1f}" '
                     f'transform="rotate(-90 {cx} {cy})"/>')
        parts.append(f'<text x="{cx}" y="{cy+5:.0f}" text-anchor="middle" font-family="monospace" '
                     f'font-size="20" fill="#dfe8f2" font-weight="700">{round(pc*100)}%</text>')
        parts.append('</svg>')
        return "".join(parts)

    def diff(self, prev: Dict[str, Any], curr: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """What changed between two audit snapshots (verdict, coverage, per-predicate)."""
        c = curr or self.gmi()
        pv = {p.get("id"): p.get("verdict") for p in (prev or {}).get("predicates", [])}
        cv = {p.get("id"): p.get("verdict") for p in c.get("predicates", [])}
        changed = {k: {"from": pv.get(k), "to": cv[k]} for k in cv if pv.get(k) != cv[k]}
        return {
            "verdict": {"from": (prev or {}).get("verdict"), "to": c.get("verdict"),
                        "changed": (prev or {}).get("verdict") != c.get("verdict")},
            "proof_coverage_delta": round((c.get("proof_coverage", 0) or 0) - ((prev or {}).get("proof_coverage", 0) or 0), 4),
            "predicates_changed": changed,
        }

    def export_report(self, gmi: Optional[Dict[str, Any]] = None, *, fmt: str = "markdown") -> str:
        """Export the audit as markdown or json."""
        g = gmi or self.gmi()
        if fmt == "json":
            return json.dumps(g, indent=2)
        lines = [f"# Gödel Machine Index — {(g.get('verdict') or 'UNKNOWN').replace('_',' ')}",
                 "", f"- Phase: {g.get('phase','?')}",
                 f"- Predicates proven: {g.get('predicates_proven',0)}/8",
                 f"- Proof coverage: {round((g.get('proof_coverage',0) or 0)*100)}% (threshold 50%)",
                 f"- Blockers: {', '.join(g.get('blockers',[]) or ['none'])}",
                 "", "## Predicates", ""]
        for p in self.predicate_report(g):
            lines.append(f"- **{p['id']} {(p.get('name') or '').replace('_',' ')}** — {p['verdict']}: {p.get('detail','')}")
        return "\n".join(lines)

    def blueprint_doc(self) -> str:
        """The Gödel Eval Blueprint source (docs/GODEL_EVAL_BLUEPRINT.md)."""
        p = _ROOT / "docs" / "GODEL_EVAL_BLUEPRINT.md"
        try:
            return p.read_text(encoding="utf-8")
        except Exception as e:
            return f"(blueprint doc unavailable: {e})"

    # ── frontend tools ─────────────────────────────────────────────────
    def frontend_tools(self) -> Dict[str, Any]:
        """The frontend toolchain available to work the UI."""
        node = shutil.which("node")
        try:
            from agents import image_optimize
            imgs = image_optimize.available()
        except Exception:
            imgs = {}
        return {"node": node, "js_syntax_check": bool(node),
                "image_toolchain": {k: bool(v) for k, v in imgs.items()},
                "ui_assets": {k: v.exists() for k, v in _UI.items()}}

    def validate_ui(self) -> Dict[str, Any]:
        """Assert the UI assets exist and the inline/renderer JS parses (node)."""
        node = shutil.which("node")
        report: Dict[str, Any] = {"assets": {}, "js": {}, "ok": True}
        for name, path in _UI.items():
            ex = path.exists()
            report["assets"][name] = ex
            report["ok"] = report["ok"] and ex
        if node:
            # renderer
            if _UI["renderer"].exists():
                r = subprocess.run([node, "--check", str(_UI["renderer"])], capture_output=True, text=True)
                report["js"]["blueprint.js"] = "ok" if r.returncode == 0 else (r.stderr[:200] or "fail")
                report["ok"] = report["ok"] and r.returncode == 0
            # inline page scripts
            for name in ("index", "admin"):
                p = _UI[name]
                if not p.exists():
                    continue
                try:
                    html = p.read_text(encoding="utf-8")
                    js = self._extract_inline_js(html)
                    tmp = _ROOT / "data" / f".bp_check_{name}.js"
                    tmp.parent.mkdir(parents=True, exist_ok=True)
                    tmp.write_text(js, encoding="utf-8")
                    r = subprocess.run([node, "--check", str(tmp)], capture_output=True, text=True)
                    tmp.unlink(missing_ok=True)
                    report["js"][name] = "ok" if r.returncode == 0 else (r.stderr[:200] or "fail")
                    report["ok"] = report["ok"] and r.returncode == 0
                except Exception as e:
                    report["js"][name] = f"check-error: {e}"
        else:
            report["js"]["note"] = "node not installed — JS syntax not checked"
        return report

    @staticmethod
    def _extract_inline_js(html: str) -> str:
        out, depth = [], 0
        for line in html.splitlines():
            if line.strip() == "<script>":
                depth = 1; continue
            if "</script>" in line and depth:
                depth = 0; continue
            if depth:
                out.append(line)
        return "\n".join(out)

    async def optimize_ui_assets(self, *, width: int = 256) -> Dict[str, Any]:
        """Optimise the UI's raster assets (e.g. mindX.png) via artist.agent's
        image toolchain — WebP for delivery, per the permaweb doctrine."""
        import asyncio
        try:
            from agents import image_optimize
        except Exception as e:
            return {"success": False, "error": f"image_optimize unavailable: {e}"}
        src = _ROOT / "mindx_frontend_ui" / "gfx" / "mindX.png"
        if not src.exists():
            src = _BE / "static" / "mindX.png"
        if not src.exists():
            return {"success": False, "error": "mindX.png not found"}
        dst = str(src.with_suffix(".webp"))
        return await asyncio.to_thread(image_optimize.to_webp, str(src), dst, width=width, q=82)

    # ── code analysis (scientific structural read of a directory) ──────
    def analyze_path(self, rel_path: str) -> Dict[str, Any]:
        """Scientific structural analysis of a code directory: per-file LOC, classes,
        functions, async ratio, docstring coverage; aggregates + largest files.
        Read-only, ast-based, graceful per file."""
        import ast as _ast
        base = (_ROOT / rel_path).resolve()
        if not str(base).startswith(str(_ROOT.resolve())) or not base.exists():
            return {"path": rel_path, "error": "path not found or outside repo"}
        files: List[Dict[str, Any]] = []
        tot = {"files": 0, "loc": 0, "classes": 0, "functions": 0, "async": 0, "documented": 0}
        for f in sorted(base.rglob("*.py")):
            try:
                src = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            loc = sum(1 for ln in src.splitlines() if ln.strip() and not ln.strip().startswith("#"))
            cls = fns = afns = 0
            documented = False
            try:
                tree = _ast.parse(src)
                documented = _ast.get_docstring(tree) is not None
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.ClassDef):
                        cls += 1
                    elif isinstance(node, _ast.AsyncFunctionDef):
                        fns += 1; afns += 1
                    elif isinstance(node, _ast.FunctionDef):
                        fns += 1
            except SyntaxError:
                pass
            files.append({"file": str(f.relative_to(_ROOT)), "loc": loc, "classes": cls,
                          "functions": fns, "async": afns, "documented": documented})
            tot["files"] += 1; tot["loc"] += loc; tot["classes"] += cls
            tot["functions"] += fns; tot["async"] += afns; tot["documented"] += int(documented)
        largest = sorted(files, key=lambda x: x["loc"], reverse=True)[:8]
        return {
            "path": rel_path, "totals": tot,
            "async_ratio": round(tot["async"] / tot["functions"], 3) if tot["functions"] else 0,
            "docstring_coverage": round(tot["documented"] / tot["files"], 3) if tot["files"] else 0,
            "largest": largest, "files": files,
        }

    def analyze_core(self) -> Dict[str, Any]:
        """Analyze the cognitive core (agents/core — BDI, AGInt, mindXagent, self-eval)."""
        return self.analyze_path("agents/core")

    # ── resource monitoring (host CPU / RAM / disk) ────────────────────
    def resources(self) -> Dict[str, Any]:
        """Live host resource snapshot via the resource monitor (psutil fallback).
        Space/compute is money — the audit reads its own substrate's load."""
        usage = None
        try:
            from agents.monitoring.resource_monitor import get_resource_monitor
            usage = get_resource_monitor().get_resource_usage()
        except Exception:
            usage = None
        # If the monitor hasn't collected yet (cold: cpu_cores==0), read live via psutil.
        if not usage or not usage.get("cpu_cores"):
            try:
                import psutil
                vm = psutil.virtual_memory()
                return {"source": "psutil-live", "cpu": psutil.cpu_percent(interval=0.2),
                        "cpu_cores": psutil.cpu_count(),
                        "cpu_load": ", ".join(f"{x:.2f}" for x in __import__("os").getloadavg()) if hasattr(__import__("os"), "getloadavg") else "n/a",
                        "memory": vm.percent, "memory_used_gb": round(vm.used / 1e9, 2),
                        "memory_total_gb": round(vm.total / 1e9, 2),
                        "disk": psutil.disk_usage("/").percent}
            except Exception as e2:
                return usage or {"error": str(e2)}
        usage.setdefault("source", "resource_monitor")
        return usage

    # ── per-core observation + resource control (governor testing) ─────
    def per_core(self) -> Dict[str, Any]:
        """Per-core CPU utilisation + RAM — the fine-grained observation side."""
        from agents.monitoring.resource_control import ResourceController
        return ResourceController.status()

    def resource_controller(self):
        """The shared bounded load controller (test-only; every load self-stops)."""
        from agents.monitoring.resource_control import ResourceController
        if getattr(self, "_rc", None) is None:
            self._rc = ResourceController()
        return self._rc

    def control_cpu(self, targets, duration: float = 15.0) -> Dict[str, Any]:
        """Load each core to a target percent — {core: pct} or [pct0, pct1, …]."""
        return self.resource_controller().set_cores(targets, duration=duration)

    def control_ram(self, mb: float, duration: float = 15.0) -> Dict[str, Any]:
        """Hold `mb` megabytes resident for `duration` seconds."""
        return self.resource_controller().set_ram(mb, duration=duration)

    def stop_load(self) -> Dict[str, Any]:
        """Terminate every active test load immediately."""
        return self.resource_controller().stop()

    # ── versioned skills + interaction catalogue ───────────────────────
    def skills(self) -> List[Dict[str, str]]:
        return list(SKILLS)

    def interaction_map(self) -> List[Dict[str, str]]:
        """The catalogue of substrate/UI effects produced by each interaction."""
        return list(INTERACTIONS)

    def manifest(self) -> Dict[str, Any]:
        return {"version": __version__, "skills": SKILLS, "interactions": INTERACTIONS}

    def versions(self) -> List[Dict[str, Any]]:
        """The saved version history (each with its skills + interactions)."""
        p = _ROOT / "data" / "blueprint" / "versions.json"
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []

    def save_version(self, note: str = "") -> Dict[str, Any]:
        """Snapshot this version (skills + interaction map) to the manifest — appends
        only when the (version, skills, interactions) signature changes, so every
        distinct version is preserved as we discover new capabilities."""
        p = _ROOT / "data" / "blueprint" / "versions.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        hist = self.versions()
        skills = [s["name"] for s in SKILLS]
        inters = [i["trigger"] for i in INTERACTIONS]
        sig = hashlib.sha256(json.dumps({"v": __version__, "s": skills, "i": inters},
                                        sort_keys=True).encode()).hexdigest()[:12]
        if hist and hist[-1].get("sig") == sig:
            return {"saved": False, "reason": "unchanged", "sig": sig, "count": len(hist)}
        snap = {"version": __version__, "ts": time.time(), "sig": sig, "note": note,
                "skills": skills, "interactions": inters}
        hist.append(snap)
        p.write_text(json.dumps(hist, indent=2), encoding="utf-8")
        return {"saved": True, "version": __version__, "sig": sig,
                "skills": len(skills), "interactions": len(inters), "count": len(hist)}
