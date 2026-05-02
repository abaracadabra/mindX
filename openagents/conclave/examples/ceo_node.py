"""CEO node — convenes a Cabinet session over AXL.

Run after `./examples/run_local_8node.sh` is up. This script assumes:

  - The 8 AXL nodes are listening on bridges 9002, 9012, 9022, …, 9072
    (one per Cabinet seat) on the local host.
  - PEM keys for each member sit in `examples/keys/{role}.pem`.
  - The Conclave + ConclaveBond contracts are deployed and addresses
    exported in env vars CONCLAVE_ADDR and CONCLAVE_ID.

Usage:

    python examples/ceo_node.py --title "Q3 M&A Review" --agenda agenda.md
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from conclave import (
    AXLClient,
    Conclave,
    KeyPair,
    QuorumPolicy,
)
from conclave.crypto import canonical_bytes, hex32, sha256
from conclave.roles import Member, MotionClass, Role


CEO_BRIDGE = "http://127.0.0.1:9002"
KEYS_DIR = Path(__file__).parent / "keys"


def _load_member(role: Role) -> Member:
    """Load each member's pubkey from their PEM in keys/{role}.pem."""
    kp = KeyPair.from_pem(str(KEYS_DIR / f"{role.value}.pem"))
    return Member(pubkey=kp.peer_id, role=role)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--agenda", default=None,
                        help="Path to agenda doc (its sha256 goes in the manifest).")
    parser.add_argument("--ttl", type=int, default=7200)
    parser.add_argument("--conclave-id",
                        default="0x" + "00" * 31 + "01",
                        help="On-chain Conclave registration id.")
    parser.add_argument("--motion-class",
                        choices=["standard", "trade_secret", "membership"],
                        default="standard",
                        help="Motion class — controls quorum and abstain handling.")
    args = parser.parse_args()
    motion_class = MotionClass[args.motion_class.upper()]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Load CEO keypair from its PEM (matches the AXL node identity).
    ceo_kp = KeyPair.from_pem(str(KEYS_DIR / "CEO.pem"))
    axl = AXLClient(bridge=CEO_BRIDGE)
    conclave = Conclave(keypair=ceo_kp, role=Role.CEO, axl=axl)

    # Build the member set — one per Cabinet role, all running locally.
    members = [_load_member(r) for r in (
        Role.CEO, Role.COO, Role.CFO, Role.CTO,
        Role.CISO, Role.GC, Role.COS, Role.OPS,
    )]

    agenda_hash = "0x" + "00" * 32
    if args.agenda:
        agenda_hash = hex32(sha256(Path(args.agenda).read_bytes()))

    sess = conclave.convene(
        conclave_id=args.conclave_id,
        title=args.title,
        agenda_hash=agenda_hash,
        members=members,
        quorum=QuorumPolicy.cabinet_default(),
        ttl_seconds=args.ttl,
    )
    print(json.dumps({
        "session_id": sess.session_id,
        "title": sess.title,
        "members": [m.pubkey for m in members],
    }, indent=2))

    # Pump the dispatch loop until acclaim quorum -> session opens.
    print("waiting for acclaim quorum...")
    deadline = time.time() + 60
    while time.time() < deadline:
        conclave.poll_once()
        if conclave.open_session_if_quorum(sess.session_id):
            break
        time.sleep(0.05)
    else:
        raise SystemExit("acclaim quorum not reached in 60s")

    # Propose the canonical demo motion.
    motion_id = conclave.propose_motion(
        session_id=sess.session_id,
        text=f"Approve {args.title} per attached agenda.",
        class_=motion_class,
        deadline_seconds=120,
    )
    print(f"motion proposed: {motion_id} (class={motion_class.value})")

    # Auto-vote yea ourselves.
    conclave.cast_vote(sess.session_id, motion_id, "yea")

    # Pump until resolution.
    while True:
        conclave.poll_once()
        outcome, tally = sess.evaluate_motion(motion_id)
        if outcome != "pending":
            print(f"motion {motion_id}: {outcome} ({tally})")
            break
        time.sleep(0.1)

    # Adjourn.
    conclave.adjourn(sess.session_id, redacted_summary=f"{args.title}: {outcome}")
    print("adjourned. transcript merkle root:",
          hex32(sha256(canonical_bytes({
              "_": [e.to_dict() for e in sess.transcript],
          }))))


if __name__ == "__main__":
    main()
