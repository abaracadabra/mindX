# SPDX-License-Identifier: Apache-2.0
"""mindX-side integration for bankoneth.

The mindX consumer surface for bankoneth. Wraps the @bankoneth/cli CLI in a
mindX BaseTool so AGI agents inside mindX can claim their own bankon.eth
subname, derive their ERC-6551 TBA wallet, and publish a marketplace listing
on agenticplace.pythai.net — all via the same tool registry that exposes the
rest of mindX's capabilities.

This package is mindX-aware on purpose. The agnostic core (`bankoneth/contracts/`
+ `packages/`) has zero mindX imports; everything mindX-specific lives here.
"""

from .tool import BankonethTool

__all__ = ["BankonethTool"]
