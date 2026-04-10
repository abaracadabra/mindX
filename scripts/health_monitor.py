#!/usr/bin/env python3
"""
mindX Health Monitor — standalone script for systemd timer or external monitoring.

Checks the mindX backend HTTP endpoint and reports status.
Exit codes: 0 = healthy, 1 = unhealthy response, 2 = unreachable, 3 = error.

Usage:
    python scripts/health_monitor.py                  # Check localhost:8000
    python scripts/health_monitor.py --url https://mindx.pythai.net/health
"""
import sys
import json
import urllib.request
import urllib.error

DEFAULT_URL = "http://localhost:8000/health"
TIMEOUT = 10


def main():
    url = DEFAULT_URL
    if len(sys.argv) > 1 and sys.argv[1] == "--url" and len(sys.argv) > 2:
        url = sys.argv[2]
    elif len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        url = sys.argv[1]

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            status = data.get("status", "unknown")
            if resp.status == 200 and status in ("healthy", "ok"):
                print(f"HEALTHY: {json.dumps(data)}")
                sys.exit(0)
            else:
                print(f"UNHEALTHY: {json.dumps(data)}")
                sys.exit(1)
    except urllib.error.URLError as e:
        print(f"UNREACHABLE: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
