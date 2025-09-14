"""
MindX Backend Service

This module contains the backend service components for the mindX system.
It provides the core service layer for the autonomous digital civilization.

Key Components:
- main_service.py: Main backend service implementation
- API endpoints and handlers
- Service orchestration
- Data management
"""

from .main_service import *

__all__ = [
    "MainService",
    "ServiceOrchestrator",
]
