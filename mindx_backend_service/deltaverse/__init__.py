"""DeltaVerse REALM — the identity-aware participant fabric for mindX.

The DeltaVerse is a fabric for a changing story; the story is woven from
participant interaction. Identity is recognized from a public wallet address
and/or a subdomain.bankon.eth name and mapped to the cypherpunk2048 hierarchy
(public < model < agent < overseer < overlord). The REALM is both a gated
surface (`/realm`, overlord-controlled) and the privileged story-shaping layer
within the fabric. The Cypherian Weaver weaves participant interaction into the
story (the six emergence traits). Bubblerooms are role-gated rooms mapped onto
mindX's existing service-isolation tiers.

Agnostic and feature-flagged: set MINDX_DELTAVERSE_ENABLED=1 to mount. mindX is
one consumer of this fabric, not its only home.
"""
from .routes import deltaverse_router  # noqa: F401
from .config import is_enabled  # noqa: F401

__all__ = ["deltaverse_router", "is_enabled"]
