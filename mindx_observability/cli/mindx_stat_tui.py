#!/usr/bin/env python3
"""mindx-stat-tui — Python TUI complement to scripts/mindx-stat.

Same subcommands (top/disk/probes/alerts/all/help) as the bash dispatcher, but
renders with `rich` tables when available. Falls back to plain text when not.

Designed to run on the VPS as `.mindx_env/bin/mindx-stat-tui` or via
`python3 -m mindx_observability.cli.mindx_stat_tui <subcmd>` from the repo root.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request

try:
    import psutil
except ImportError:
    print("ERROR: psutil required. apt install python3-psutil", file=sys.stderr)
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    _RICH = True
    _console = Console()
except ImportError:
    _RICH = False
    _console = None


PROM_LOCAL = os.environ.get("PROM_LOCAL", "http://localhost:9090")
PROMETHEUS_DATA = os.environ.get("PROMETHEUS_DATA", "/home/mindx/obs/prometheus_data")


def _print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    if _RICH:
        t = Table(title=title, show_lines=False, expand=False)
        for c in columns:
            t.add_column(c)
        for r in rows:
            t.add_row(*[str(x) for x in r])
        _console.print(t)
    else:
        widths = [max(len(c), *(len(str(r[i])) for r in rows)) for i, c in enumerate(columns)]
        print(f"== {title} ==")
        print("  " + "  ".join(c.ljust(w) for c, w in zip(columns, widths)))
        for r in rows:
            print("  " + "  ".join(str(x).ljust(w) for x, w in zip(r, widths)))


def cmd_top(top: int = 10) -> None:
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "memory_info", "cpu_percent"]):
        try:
            info = p.info
            rss = info["memory_info"].rss if info.get("memory_info") else 0
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "?",
                "user": info["username"] or "?",
                "rss_mb": rss / (1 << 20),
                "cpu": info.get("cpu_percent", 0.0),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p["rss_mb"], reverse=True)
    rows = [[p["pid"], p["user"][:12], f"{p['cpu']:5.1f}", f"{p['rss_mb']:8.1f}", p["name"]]
            for p in procs[:top]]
    _print_table(f"TOP {top} processes by RSS", ["PID", "USER", "CPU%", "RSS_MB", "NAME"], rows)


def cmd_disk() -> None:
    usage = shutil.disk_usage("/")
    rows = [[
        "/",
        f"{usage.total / (1 << 30):.1f} GB",
        f"{usage.used / (1 << 30):.1f} GB",
        f"{usage.free / (1 << 30):.1f} GB",
        f"{(usage.used / usage.total) * 100:.0f}%",
    ]]
    _print_table("DISK — root", ["mount", "total", "used", "free", "pct"], rows)

    # Prometheus TSDB size
    if os.path.isdir(PROMETHEUS_DATA):
        size = 0
        for dirpath, _, fnames in os.walk(PROMETHEUS_DATA):
            for f in fnames:
                try:
                    size += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        print(f"  Prometheus TSDB: {size / (1 << 20):.1f} MB (cap 4 GB per Phase 1.1 retention)")
    else:
        print(f"  Prometheus TSDB: not found at {PROMETHEUS_DATA}")

    # RAM + swap
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    _print_table("MEMORY", ["scope", "total", "used", "free", "pct"], [
        ["RAM", f"{vm.total / (1 << 30):.2f} GB", f"{vm.used / (1 << 30):.2f} GB",
         f"{vm.available / (1 << 30):.2f} GB", f"{vm.percent:.0f}%"],
        ["swap", f"{sm.total / (1 << 30):.2f} GB", f"{sm.used / (1 << 30):.2f} GB",
         f"{sm.free / (1 << 30):.2f} GB", f"{sm.percent:.0f}%"],
    ])


def _prom_query(path: str, query: str | None = None) -> dict:
    url = f"{PROM_LOCAL}{path}"
    if query:
        from urllib.parse import urlencode
        url += "?" + urlencode({"query": query})
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)}


def cmd_probes() -> None:
    res = _prom_query("/api/v1/query", "probe_success")
    if "_error" in res:
        print(f"  Prometheus unreachable at {PROM_LOCAL}: {res['_error']}")
        return
    rows = []
    for r in res.get("data", {}).get("result", []):
        instance = r["metric"].get("instance", "?")
        value = "UP" if r["value"][1] == "1" else "DOWN"
        rows.append([value, instance])
    _print_table("PROBES — blackbox_http_2xx", ["state", "target"], rows or [["—", "no data"]])


def cmd_alerts() -> None:
    res = _prom_query("/api/v1/alerts")
    if "_error" in res:
        print(f"  Prometheus unreachable at {PROM_LOCAL}: {res['_error']}")
        return
    alerts = [a for a in res.get("data", {}).get("alerts", []) if a.get("state") == "firing"]
    if not alerts:
        print("  no active alerts")
        return
    rows = [[a["labels"].get("severity", "?"),
             a["labels"].get("alertname", "?"),
             a.get("annotations", {}).get("summary", "")] for a in alerts]
    _print_table(f"ALERTS — {len(alerts)} firing", ["severity", "alertname", "summary"], rows)


def cmd_all(top: int = 10) -> None:
    cmd_top(top)
    print()
    cmd_disk()
    print()
    cmd_probes()
    print()
    cmd_alerts()


def main() -> int:
    p = argparse.ArgumentParser(
        prog="mindx-stat-tui",
        description="mindX text-mode dashboard (Python TUI). Pair with scripts/mindx-stat shell tool.",
    )
    sub = p.add_subparsers(dest="cmd", required=False)
    sub.add_parser("top").add_argument("--top", type=int, default=10)
    sub.add_parser("disk")
    sub.add_parser("probes")
    sub.add_parser("alerts")
    sa = sub.add_parser("all"); sa.add_argument("--top", type=int, default=10)
    sub.add_parser("help")
    args = p.parse_args()

    cmd = args.cmd or "help"
    if cmd == "top":
        cmd_top(args.top)
    elif cmd == "disk":
        cmd_disk()
    elif cmd == "probes":
        cmd_probes()
    elif cmd == "alerts":
        cmd_alerts()
    elif cmd == "all":
        cmd_all(getattr(args, "top", 10))
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
