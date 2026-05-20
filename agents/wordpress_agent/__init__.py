# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""WordPress.agent — agnostic publishing tool for the PYTHAI/DELTAVERSE ecosystem.

Single responsibility: take finished content, put it on WordPress.
"""
from .agent import WordpressAgent, PublishResult, MediaResult
from .config import Settings

__version__ = "0.1.0"
__all__ = ["WordpressAgent", "PublishResult", "MediaResult", "Settings", "__version__"]
