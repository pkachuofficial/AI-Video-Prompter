"""
avp.continuity — Prompt-Centric Cinematic Continuity and Human-Realism Engine.

Exposes ContinuityBridge, ContinuityReport, ContinuityMode, and submodules.
"""

from avp.continuity.bridge import ContinuityBridge
from avp.continuity.models import (
    ContinuityHandoff,
    ContinuityMode,
    ContinuityReport,
    RelevanceType,
)

__all__ = [
    "ContinuityBridge",
    "ContinuityReport",
    "ContinuityMode",
    "RelevanceType",
    "ContinuityHandoff",
]
