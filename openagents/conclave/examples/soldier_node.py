"""Counsellor (soldier) node — listens for ConveneManifest, acclaims,
deliberates, votes.

One process per role. Argument `--role` selects which member this is;
the AXL bridge port is conventionally 9002 + role_index*10.

Usage:

    python examples/soldier_node.py --role CFO --disposition yea
    python examples/soldier_node.py --role CISO --disposition nay  # paranoid
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from conclave import AXLClient, Conclave, KeyPair
from conclave.agent import MindXAgent, StaticMind
from conclave.roles import Role


KEYS_DIR = Path(__file__).parent / "keys"


# Convention: bridge ports for the 8 local nodes.
BRIDGE_PORTS: dict[Role, int] = {
    Role.CEO:  9002,
    Role.COO:  9012,
    Role.CFO:  9022,
    Role.CTO:  9032,
    Role.CISO: 9042,
    Role.GC:   9052,
    Role.COS:  9062,
    Role.OPS:  9072,
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--role", required=True,
                   choices=[r.value for r in Role if r is not Role.CEO])
    p.add_argument("--disposition", default="yea",
                   choices=["yea", "nay", "abstain"])
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    role = Role(args.role)

    kp = KeyPair.from_pem(str(KEYS_DIR / f"{role.value}.pem"))
    bridge = f"http://127.0.0.1:{BRIDGE_PORTS[role]}"
    axl = AXLClient(bridge=bridge)
    conclave = Conclave(keypair=kp, role=role, axl=axl)

    # Hackathon-grade Mind: deterministic vote.
    # In production this is wired to mindx.pythai.net/api via MindXMind.
    mind = StaticMind(disposition=args.disposition)
    agent = MindXAgent(conclave=conclave, mind=mind, capabilities=[
        # Each role advertises a different MCP service it exposes.
        # The CEO can call /mcp/{this-peer}/{capability} during deliberation.
        f"{role.value.lower()}-counsel",
    ])

    print(f"[{role.value}] running on {bridge} as peer {kp.peer_id}")
    agent.run()


if __name__ == "__main__":
    main()
