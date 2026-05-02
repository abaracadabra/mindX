"""CONCLAVE — peer-to-peer agent conclave protocol over AXL."""

from .protocol import Conclave, SessionState
from .messages import (
    Envelope,
    ConveneManifest,
    Acclaim,
    SessionOpen,
    Speak,
    Motion,
    Vote,
    Resolution,
    Adjourn,
    MessageKind,
)
from .roles import Role, Member, MotionClass, QuorumPolicy
from .axl_client import AXLClient
from .crypto import KeyPair, sign, verify, canonical_bytes
from .agent import MindXAgent, StaticMind, MindXMind, make_agent

__version__ = "0.1.0"
__all__ = [
    "Conclave",
    "SessionState",
    "Envelope",
    "ConveneManifest",
    "Acclaim",
    "SessionOpen",
    "Speak",
    "Motion",
    "Vote",
    "Resolution",
    "Adjourn",
    "MessageKind",
    "Role",
    "Member",
    "MotionClass",
    "QuorumPolicy",
    "AXLClient",
    "KeyPair",
    "sign",
    "verify",
    "canonical_bytes",
    "MindXAgent",
    "StaticMind",
    "MindXMind",
    "make_agent",
]
