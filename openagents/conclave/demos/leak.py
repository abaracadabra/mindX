"""leak.py — simulate a Cabinet member exfiltrating the signed transcript.

In a real attack the leaker would post the JSON to a journalist or
counter-party. For the demo we just dump it to stdout (or a file via
shell redirection) so `slash.py` has a real signed proof to submit.

Usage:

    python demos/leak.py --transcript /tmp/sess-XXX.json > /tmp/leaked.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True,
                        help="Path to a signed Conclave transcript JSON.")
    parser.add_argument("--leaker", default="COO",
                        help="Role attributing the leak (default: COO).")
    args = parser.parse_args()

    src = Path(args.transcript)
    if not src.exists():
        print(f"transcript not found: {src}", file=sys.stderr)
        raise SystemExit(2)

    transcript = json.loads(src.read_text())

    # The "leak" is just publishing the transcript verbatim plus an
    # attribution claim. The signed envelopes inside transcript['entries']
    # are themselves the proof — anyone who can verify the signatures
    # can confirm the transcript came from that exact session and that
    # the named role was a participant.
    leak = {
        "leaked_by": args.leaker,
        "session_id": transcript.get("session_id"),
        "entries": transcript.get("entries", []),
        "note": (
            "Each entry is a signed envelope under the AXL peer key of "
            "a Cabinet member. Recovering signers exposes the leaker."
        ),
    }
    json.dump(leak, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
