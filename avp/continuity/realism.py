"""
avp.continuity.realism — Human movement realism, anatomical integrity, and physics engine.

Ensures physically plausible locomotion, weight transfer, object contact,
and dynamically generates only targeted safeguards.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from avp.continuity.models import CorrectionItem, RiskItem


def analyze_movement_kinematics(prompt: str) -> Tuple[Optional[str], List[RiskItem], List[CorrectionItem]]:
    """
    Analyze physical human movement (walking, standing, turning, reaching).
    """
    risks: List[RiskItem] = []
    corrections: List[CorrectionItem] = []
    movement_directive: Optional[str] = None

    p_low = prompt.lower()

    # Walking detection
    walking_cues = ["walks", "walking", "steps", "stepping", "runs", "running", "strides", "approaches"]
    is_walking = any(re.search(rf"\b{cue}\b", p_low) for cue in walking_cues)

    if is_walking:
        movement_directive = (
            "Movement kinematics: measured steps with grounded foot contact and natural weight transfer "
            "between feet; natural deceleration near destination; strictly no sliding, gliding, skating, or floating feet."
        )
        corrections.append(CorrectionItem(
            category="kinematics",
            description="Locomotion structured: realistic foot contact and weight transfer enforced."
        ))

    # Sitting or surface contact
    elif "sits" in p_low or "sitting" in p_low or "sat" in p_low:
        movement_directive = (
            "Physical posture: body maintains continuous, weighted contact with seat surface; "
            "natural torso weight resting believably against support without floating."
        )
        corrections.append(CorrectionItem(
            category="kinematics",
            description="Surface contact verified: realistic weight grounding."
        ))

    # Reaching or object interaction
    elif any(w in p_low for w in ["reaches", "touches", "picks up", "holds", "places", "opens", "closes"]):
        movement_directive = (
            "Biomechanical interaction: arm articulates naturally from shoulder and elbow; "
            "hand maintains anatomically connected wrist and believable grip contact."
        )
        corrections.append(CorrectionItem(
            category="kinematics",
            description="Manual dexterity verified: articulated reach and natural grip."
        ))

    return movement_directive, risks, corrections


def analyze_anatomical_safeguards(prompt: str) -> List[str]:
    """
    Identify specific anatomical risks and generate targeted constraints.
    """
    safeguards: List[str] = []
    p_low = prompt.lower()

    # Hand and finger risks
    if any(w in p_low for w in ["hand", "touch", "grip", "hold", "pick", "place", "reaches", "finger", "phone"]):
        safeguards.append("maintain anatomically correct hands with 5 distinct fingers, natural wrist connection, and continuous physical contact without limb clipping")

    # Walking / foot risks
    if any(w in p_low for w in ["walk", "run", "step", "stride"]):
        safeguards.append("grounded foot placement with realistic floor contact; no foot sliding across surfaces or floating")

    # Facial closeup risks
    if any(w in p_low for w in ["close-up", "cu", "face", "eyes", "expression", "look"]):
        safeguards.append("stable facial proportions and symmetrical ocular alignment without warping or facial deformation")

    return safeguards


def build_dynamic_negative_constraints(
    prompt: str,
    has_scene_change: bool,
    has_dialogue: bool,
    has_listening: bool,
    has_screen_media: bool
) -> str:
    """
    Build dynamic, targeted negative constraints tailored specifically to this shot's risk factors.
    Avoids giant static negative boilerplate (Section 30).
    """
    negatives = [
        "deformed limbs", "extra fingers", "missing fingers", "fused hands",
        "floating feet", "sliding across floor", "body clipping through objects"
    ]

    p_low = prompt.lower()

    if has_dialogue and not has_listening:
        negatives.extend(["frozen mouth", "exaggerated cartoonish jaw movement", "speech desynchronization"])
    elif has_listening:
        negatives.extend(["speaking mouth movement", "lip sync while listening", "mouth opening"])

    if any(w in p_low for w in ["walk", "run", "step"]):
        negatives.extend(["skating motion", "instant position snapping", "teleporting"])

    if has_screen_media:
        negatives.extend(["extra physical people in room", "duplicate character bodies", "twin figure hallucination"])

    if has_scene_change:
        negatives.extend(["previous room architecture", "previous furniture leaking", "old scene geometry contamination"])

    return ", ".join(negatives)
