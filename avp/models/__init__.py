"""
avp.models — Pydantic data schemas for the Production Bible.

These schemas are the single source of truth for all generated media.
Fields are intentionally strict; no optional drift is permitted for
identity-critical attributes.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Character Identity
# ---------------------------------------------------------------------------

class CharacterIdentity(BaseModel):
    """Immutable biometric and stylistic definition for a single character.

    This record lives in the Production Bible database and is NEVER
    overridden by per-scene prompt text.  The prompt compiler pulls these
    tokens verbatim into every shot that features this character.
    """

    character_id: str = Field(
        ...,
        description="Immutable primary key token, e.g. 'CHAR_VIKTOR'",
    )
    canonical_name: str = Field(..., description="Screen name used in the screenplay")
    age_range: str = Field(..., description="e.g. 'late 30s', '42 years old'")
    ethnicity: str = Field(..., description="Diffusion-friendly ethnicity token string")

    # High-frequency biometric tokens injected at every framing level
    facial_features: str = Field(
        ...,
        description=(
            "Fixed facial geometry, skin topography, eye colour, and unique scars. "
            "Use comma-separated diffusion tokens."
        ),
    )
    hair_specification: str = Field(
        ...,
        description="Exact hair geometry, cut style, and colour tokens",
    )
    body_morphology: str = Field(
        ...,
        description="Stature, skeletal frame, and muscular build tokens",
    )

    # Negative conditioning pulled into every shot featuring this character
    canonical_negative_prompt: str = Field(
        ...,
        description=(
            "Negative tokens that suppress character-specific drift. "
            "Comma-separated list of suppressed attributes."
        ),
    )

    # Optional identity-injection hooks
    default_lora_trigger: Optional[str] = Field(
        None,
        description="LoRA trigger word baked into the fine-tuned checkpoint",
    )
    face_embedding_path: Optional[str] = Field(
        None,
        description=(
            "Filesystem path to the InsightFace reference tensor (.npy or .pt) "
            "used by PuLID / FaceID nodes."
        ),
    )


# ---------------------------------------------------------------------------
# Wardrobe State
# ---------------------------------------------------------------------------

class WardrobeState(BaseModel):
    """A single costume configuration including wear and distress state.

    A character may have multiple WardrobeState records (tactical, civilian,
    formal …).  The narrative may also advance distress_level between scenes
    to represent progressive physical damage without redefining the garment.
    """

    wardrobe_id: str = Field(
        ...,
        description="Unique costume code, e.g. 'WARDROBE_VIKTOR_TACTICAL_01'",
    )
    character_id: str = Field(..., description="FK → CharacterIdentity.character_id")

    garment_layers: str = Field(
        ...,
        description=(
            "Explicit description of upper, lower, and outer apparel layers "
            "in diffusion-compatible token format."
        ),
    )
    distress_level: str = Field(
        "pristine",
        description=(
            "Surface damage descriptor. One of: "
            "'pristine' | 'lightly worn' | 'battle-worn' | 'blood-stained' | 'soaked'"
        ),
    )
    accessories: List[str] = Field(
        default_factory=list,
        description="Ordered list of accessories: watches, rings, holsters, glasses …",
    )
    ip_adapter_reference_path: Optional[str] = Field(
        None,
        description=(
            "Path to the reference costume image used by the IP-Adapter node "
            "for fabric and texture conditioning."
        ),
    )


# ---------------------------------------------------------------------------
# Scene Context
# ---------------------------------------------------------------------------

class SceneContext(BaseModel):
    """Environmental constants shared by all shots inside a single scene.

    Injected into every shot's $C_{Environment}$ layer.  Values here must
    not change between the shots of a scene (e.g. INT. SAFE-HOUSE - NIGHT).
    """

    scene_id: str = Field(..., description="e.g. 'S01E02_SCN_007'")
    episode_id: str = Field(..., description="e.g. 'S01E02'")
    location_name: str = Field(..., description="Human-readable set name")
    setting: str = Field(..., description="'INT' or 'EXT'")
    time_of_day: str = Field(
        ...,
        description="'DAY' | 'NIGHT' | 'GOLDEN HOUR' | 'OVERCAST' | 'MAGIC HOUR'",
    )

    # Spatial description shared across all camera angles in this scene
    spatial_configuration: str = Field(
        ...,
        description=(
            "Architectural or environmental description token string. "
            "Shared across all shot-reverse-shot pairs to prevent geometry mismatch."
        ),
    )
    lighting_setup: str = Field(
        ...,
        description=(
            "Key light source, colour temperature, contrast ratio, and fill quality."
        ),
    )
    color_palette_tokens: List[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of colour science tokens enforced across the entire scene. "
            "e.g. ['desaturated teal', 'amber practicals', 'deep shadow blacks']"
        ),
    )
    environmental_anchors: List[str] = Field(
        default_factory=list,
        description=(
            "Persistent environmental details that must appear in every shot: "
            "furniture pieces, prop continuity items, weather conditions, etc."
        ),
    )
    global_style_negative: str = Field(
        ...,
        description=(
            "Scene-level negative tokens in addition to the global aesthetic negatives. "
            "Used to suppress scene-inappropriate aesthetics (e.g. 'sunlight' in a NIGHT scene)."
        ),
    )


# ---------------------------------------------------------------------------
# Shot Plan
# ---------------------------------------------------------------------------

class ShotPlan(BaseModel):
    """A single camera take compiled from screenplay analysis.

    The prompt compiler populates compiled_positive_prompt and
    compiled_negative_prompt before dispatch; those fields are
    None on initial construction.
    """

    shot_id: str = Field(..., description="Unique take identifier, e.g. 'S01E02_SCN007_SH003'")
    scene_id: str = Field(..., description="FK → SceneContext.scene_id")
    primary_character_id: str = Field(..., description="FK → CharacterIdentity.character_id")
    wardrobe_id: str = Field(..., description="FK → WardrobeState.wardrobe_id")

    # Cinematographic parameters
    shot_type: str = Field(
        ...,
        description="Framing code: ECU | CU | MCU | MS | WS",
    )
    camera_movement: str = Field(
        ...,
        description=(
            "Camera vector: Static | Push-in | Pull-out | Pan-left | Pan-right | "
            "Tilt-up | Tilt-down | Tracking | Crane-up | Crane-down"
        ),
    )
    focal_length: str = Field("50mm", description="Simulated optical focal length")
    action_beat: str = Field(
        ...,
        description=(
            "Single, constrained kinematic action for this take. "
            "Must describe ONE motion to prevent temporal entropy."
        ),
    )

    # Optional secondary character (for two-shot or reaction compositions)
    secondary_character_id: Optional[str] = None

    # Stage 1 keyframe anchoring
    keyframe_path: Optional[str] = Field(
        None,
        description="Filesystem path to the approved Stage 1 master keyframe image.",
    )
    tail_frame_path: Optional[str] = Field(
        None,
        description=(
            "Optional end-frame for dual-keyframe interpolation (imageTail). "
            "When set, the video model interpolates between keyframe and tail_frame."
        ),
    )

    # Compiled prompt strings — populated by PromptCompiler
    compiled_positive_prompt: Optional[str] = None
    compiled_negative_prompt: Optional[str] = None

    # Provenance — populated after generation
    generation_seed: Optional[int] = None
    checkpoint_hash: Optional[str] = None
    lora_weights: Optional[str] = None
    sampler: Optional[str] = None
    cfg_scale: Optional[float] = None
    output_video_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Shot Manifest (episode-level container)
# ---------------------------------------------------------------------------

class ShotManifest(BaseModel):
    """Complete ordered shot list for a single episode."""

    episode_id: str
    shots: List[ShotPlan] = Field(default_factory=list)
