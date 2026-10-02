"""
avp.compiler — Deterministic multi-layer prompt compilation engine.

Implements the token hierarchy:

  Prompt_final = C_Optics ⊕ C_Subject ⊕ C_Environment ⊕ C_Dynamics ⊕ C_Aesthetics

Each layer is assembled from validated Production Bible records, ensuring
that biometric tokens are never sourced from the screenplay text itself.

The compiler also:
  • Applies shot-type-aware attention weighting (ECU → face detail, WS → environment)
  • Merges global aesthetic negatives with character-specific drift guards
  • Returns a fully compiled ShotPlan ready for dispatch
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from avp.models import CharacterIdentity, SceneContext, ShotPlan, WardrobeState


# ---------------------------------------------------------------------------
# Global Aesthetic Negative (constant across all productions)
# ---------------------------------------------------------------------------

GLOBAL_AESTHETIC_NEGATIVE = (
    "cgi, 3d render, illustration, anime, smooth plastic skin, airbrushed, cartoon, "
    "oversaturated, amateur framing, bad anatomy, deformed fingers, extra limbs, "
    "motion blur artifacts, double heads, watermark, signature, text overlay, "
    "lens flare artifacts, noise grain overload, chromatic aberration overload, "
    "exaggerated facial expressions, melodramatic overacting, cartoonish crying, "
    "frantic unnatural pacing, hyper-accelerated motion, jerky erratic movement, "
    "teleporting, sliding across floor, unnatural gliding, skating motion, instant position snapping, floating feet, "
    "changing eye color, shifting iris color, mismatched eyes, heterochromia drift, "
    "Chinese dialogue, Chinese speech, Mandarin audio, Cantonese voice, foreign language dubbing, "
    "Chinese subtitles, hanzi text, Asian text watermark, foreign text overlays"
)


# ---------------------------------------------------------------------------
# Shot-type attention allocation tables
# ---------------------------------------------------------------------------

@dataclass
class _ShotProfile:
    focal_hint: str
    optics_prefix: str
    subject_emphasis: str      # token(s) prepended to C_Subject
    environment_weight: str    # "prominent" | "secondary" | "omit"
    face_detail_level: str     # "microscopic" | "standard" | "silhouette"


_SHOT_PROFILES: Dict[str, _ShotProfile] = {
    "ECU": _ShotProfile(
        focal_hint="85mm–105mm lens",
        optics_prefix="extreme close-up, macro facial detail, razor-sharp focus, shallow depth of field",
        subject_emphasis=(
            "epidermal pores, iris striations, ocular moisture, micro-expressions, "
            "catchlight in eyes, key light reflection"
        ),
        environment_weight="omit",
        face_detail_level="microscopic",
    ),
    "CU": _ShotProfile(
        focal_hint="50mm–85mm lens",
        optics_prefix="close-up, sharp facial focus, cinematic shallow depth of field",
        subject_emphasis="canonical facial structure, eye shape, jawline contour, hair detail",
        environment_weight="secondary",
        face_detail_level="standard",
    ),
    "MCU": _ShotProfile(
        focal_hint="50mm–85mm lens",
        optics_prefix="medium close-up, chest-to-head framing, cinematic depth of field",
        subject_emphasis="face and upper torso, collar and neckline, shoulder posture",
        environment_weight="secondary",
        face_detail_level="standard",
    ),
    "MS": _ShotProfile(
        focal_hint="35mm–50mm lens",
        optics_prefix="medium shot, waist-to-head framing, natural perspective",
        subject_emphasis="wardrobe silhouette, torso posture, hand gestures, full upper body",
        environment_weight="prominent",
        face_detail_level="standard",
    ),
    "WS": _ShotProfile(
        focal_hint="24mm–28mm lens",
        optics_prefix=(
            "wide establishing shot, full environment visible, "
            "natural wide-angle perspective, volumetric atmosphere"
        ),
        subject_emphasis="full-body silhouette, wardrobe colour massing, figure in environment",
        environment_weight="prominent",
        face_detail_level="silhouette",
    ),
}

_DEFAULT_PROFILE = _SHOT_PROFILES["MS"]


# ---------------------------------------------------------------------------
# Token layer builders
# ---------------------------------------------------------------------------

def _build_optics_layer(shot: ShotPlan, profile: _ShotProfile) -> str:
    """C_Optics: lens type, framing, optical depth."""
    return (
        f"{profile.optics_prefix}, "
        f"{shot.focal_length if shot.focal_length else profile.focal_hint}, "
        f"{shot.camera_movement} camera movement"
    )


def _build_subject_layer(
    character: CharacterIdentity,
    wardrobe: WardrobeState,
    profile: _ShotProfile,
) -> str:
    """C_Subject: immutable biometric tokens + wardrobe state."""
    # Biometric core pulled from Production Bible — never from screenplay prose
    biometric = (
        f"{character.ethnicity}, {character.age_range}, "
        f"{character.facial_features}, {character.hair_specification}, "
        f"{character.body_morphology}"
    )

    # Face detail weighting by shot type
    if profile.face_detail_level == "microscopic":
        biometric = f"{profile.subject_emphasis}, {biometric}"
    elif profile.face_detail_level == "standard":
        biometric = f"{profile.subject_emphasis}, {biometric}"
    else:
        # Wide shot: omit microscopic skin texturing
        biometric = f"{profile.subject_emphasis}, {biometric}"

    # LoRA trigger injection (highest priority token when present)
    if character.default_lora_trigger:
        biometric = f"{character.default_lora_trigger}, {biometric}"

    # Wardrobe tokens
    accessories_str = (
        ", ".join(wardrobe.accessories) if wardrobe.accessories else ""
    )
    garment_tokens = wardrobe.garment_layers
    if wardrobe.distress_level and wardrobe.distress_level != "pristine":
        garment_tokens += f", {wardrobe.distress_level} clothing"
    if accessories_str:
        garment_tokens += f", {accessories_str}"

    return f"{biometric}, {garment_tokens}"


def _build_environment_layer(
    scene: SceneContext,
    profile: _ShotProfile,
) -> str:
    """C_Environment: lighting, spatial config, colour science."""
    if profile.environment_weight == "omit":
        # ECU — only inject critical lighting tokens, suppress architecture
        return f"{scene.lighting_setup}, {', '.join(scene.color_palette_tokens)}"

    env_anchors = ", ".join(scene.environmental_anchors) if scene.environmental_anchors else ""
    color_tokens = ", ".join(scene.color_palette_tokens)

    if profile.environment_weight == "prominent":
        return (
            f"{scene.spatial_configuration}, {scene.lighting_setup}, "
            f"{color_tokens}, {env_anchors}"
        ).strip(", ")
    else:
        # secondary — lighting dominant, architecture subordinate
        return (
            f"{scene.lighting_setup}, {color_tokens}, {scene.spatial_configuration}"
        )


def _build_dynamics_layer(shot: ShotPlan) -> str:
    """C_Dynamics: single, constrained kinematic action beat with natural human pacing."""
    return f"{shot.action_beat}, natural unhurried human pacing, grounded movement cadence"


def _build_aesthetics_layer() -> str:
    """C_Aesthetics: global rendering standards and film stock emulation."""
    return (
        "cinematic film photography, 35mm film grain, photorealistic, "
        "RAW photo quality, professional cinematography, dramatic lighting, "
        "Arri Alexa colour science, anamorphic lens character, grounded authentic human performance, "
        "subtle restrained micro-expressions, no digital artifacts"
    )


# ---------------------------------------------------------------------------
# Negative prompt assembly
# ---------------------------------------------------------------------------

def _build_negative_prompt(
    character: CharacterIdentity,
    scene: SceneContext,
) -> str:
    """Merge global, scene-level, and character-specific negative tokens."""
    parts = [
        GLOBAL_AESTHETIC_NEGATIVE,
        scene.global_style_negative,
        character.canonical_negative_prompt,
    ]
    return ", ".join(p.strip() for p in parts if p.strip())


# ---------------------------------------------------------------------------
# Main Compiler
# ---------------------------------------------------------------------------

class PromptCompiler:
    """Stateless prompt compiler.

    Resolves script references against in-memory Production Bible dicts and
    compiles fully-formed positive and negative prompt strings into each
    ShotPlan.  All biometric identity is sourced exclusively from the
    CharacterIdentity record — never from action paragraph prose.

    Usage::

        compiler = PromptCompiler(characters, wardrobes, scenes)
        compiled_shot = compiler.compile(shot_plan)
    """

    def __init__(
        self,
        characters: Dict[str, CharacterIdentity],
        wardrobes: Dict[str, WardrobeState],
        scenes: Dict[str, SceneContext],
    ) -> None:
        self._characters = characters
        self._wardrobes = wardrobes
        self._scenes = scenes

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(self, shot: ShotPlan) -> ShotPlan:
        """Compile a ShotPlan in-place and return it.

        Raises KeyError if referenced character, wardrobe, or scene is
        not present in the Production Bible.
        """
        character = self._characters[shot.primary_character_id]
        wardrobe = self._wardrobes[shot.wardrobe_id]
        scene = self._scenes[shot.scene_id]
        profile = _SHOT_PROFILES.get(shot.shot_type.upper(), _DEFAULT_PROFILE)

        # Assemble the five conditioning layers in strict priority order
        layers = [
            _build_optics_layer(shot, profile),
            _build_subject_layer(character, wardrobe, profile),
            _build_environment_layer(scene, profile),
            _build_dynamics_layer(shot),
            _build_aesthetics_layer(),
        ]

        shot.compiled_positive_prompt = ", ".join(
            layer.strip().strip(",") for layer in layers if layer.strip()
        )
        shot.compiled_negative_prompt = _build_negative_prompt(character, scene)

        return shot

    def compile_manifest(self, shots: List[ShotPlan]) -> List[ShotPlan]:
        """Compile an ordered list of shots.  Returns the same list."""
        return [self.compile(s) for s in shots]
