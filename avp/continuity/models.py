"""
avp.continuity.models — Data schemas for the Continuity and Human-Realism Engine.

Prompt-centric continuity representations without heavy database or state-machine dependencies.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContinuityMode(str, Enum):
    """Relationship between the previous shot and the new shot."""
    CONTINUE = "CONTINUE"      # Same physical scene or immediate physical situation
    TRANSITION = "TRANSITION"  # Same narrative sequence, but location/blocking/camera changes
    RESET = "RESET"            # Genuinely new scene/location/time/narrative situation


class RelevanceType(str, Enum):
    """Classification of previous shot elements in the new shot context."""
    INHERIT = "INHERIT"          # Carried forward into new shot
    CONDITIONAL = "CONDITIONAL"  # Carried forward only if condition is met in new shot
    RESET = "RESET"              # Cleared/reset; must not leak into new shot
    IRRELEVANT = "IRRELEVANT"    # Not applicable to this shot


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CharacterContinuityState(BaseModel):
    name: str
    identity_tokens: Optional[str] = None
    wardrobe: Optional[str] = None
    hair: Optional[str] = None
    facial_features: Optional[str] = None
    emotional_state: Optional[str] = None
    held_objects: Dict[str, str] = Field(default_factory=dict)
    position: Optional[str] = None
    facing_direction: Optional[str] = None
    eyeline: Optional[str] = None


class EnvironmentContinuityState(BaseModel):
    location_name: Optional[str] = None
    setting_type: Optional[str] = None  # INT / EXT
    time_of_day: Optional[str] = None
    lighting_setup: Optional[str] = None
    spatial_anchors: Dict[str, str] = Field(default_factory=dict)
    active_props: List[str] = Field(default_factory=list)


class ContradictionItem(BaseModel):
    category: str
    description: str
    resolution: str
    priority_applied: str


class RiskItem(BaseModel):
    category: str
    severity: str  # WARNING, CAUTION, INFO
    description: str
    suggestion: str


class CorrectionItem(BaseModel):
    category: str
    description: str


class ContinuityHandoff(BaseModel):
    mode: ContinuityMode
    character_handoff: Optional[str] = None
    emotional_handoff: Optional[str] = None
    object_handoff: Optional[str] = None
    location_handoff: Optional[str] = None
    lighting_handoff: Optional[str] = None
    direction_handoff: Optional[str] = None
    reset_summary: Optional[str] = None


class ContinuityReport(BaseModel):
    """Concise user-facing report and final prompt output."""
    mode: ContinuityMode
    continuity_items: List[str] = Field(
        default_factory=list,
        description="Concise continuity bullet points (e.g. '✓ Same character', '↻ Location reset')"
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Concise risk flags (e.g. '⚠ Dialogue too long for shot duration')"
    )
    corrections: List[str] = Field(
        default_factory=list,
        description="Concise corrections applied (e.g. '✓ Action divided into temporal beats')"
    )
    handoff: ContinuityHandoff
    final_prompt: str
    negative_prompt: str
    detailed_analysis: Dict[str, Any] = Field(default_factory=dict)
