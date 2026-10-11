"""
avp.continuity.geometry — Spatial geometry and camera kinematics engine.

Reasons about physical spatial relationships, compass/room anchors,
eyelines, screen direction, and camera placement.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from avp.continuity.models import ContinuityMode, CorrectionItem, RiskItem


def parse_spatial_anchors(text: str) -> Dict[str, str]:
    """Extract cardinal or wall anchors from prompt text."""
    anchors = {}
    lower = text.lower()

    # Match North/South/East/West wall references
    for direction in ["north", "south", "east", "west"]:
        match = re.search(rf"\b{direction}\s+wall\s*=\s*([^,.\n]+)", lower)
        if match:
            anchors[direction] = match.group(1).strip()
        else:
            # check phrases like "against the north wall"
            match2 = re.search(rf"\b(against\s+the\s+|along\s+the\s+){direction}\s+wall\s+([a-z\s]+?)(?:[,.]|$)", lower)
            if match2:
                anchors[direction] = match2.group(2).strip()

    # Check for prominent room anchors (monitors, bed, door, window)
    if "monitor" in lower and "north" not in anchors:
        anchors["monitors"] = "north wall"
    if "door" in lower and "entrance" not in anchors:
        anchors["doorway"] = "entrance threshold"

    return anchors


def analyze_spatial_continuity(
    prev_prompt: str,
    new_prompt: str,
    mode: ContinuityMode
) -> Tuple[Optional[str], List[RiskItem], List[CorrectionItem]]:
    """
    Analyze spatial geometry for continuity, mirroring prevention, and anchor handling.
    """
    risks: List[RiskItem] = []
    corrections: List[CorrectionItem] = []
    geometry_directive: Optional[str] = None

    p_low = prev_prompt.lower()
    n_low = new_prompt.lower()

    if mode == ContinuityMode.CONTINUE:
        # Same room: inherit established geometry and anchors
        prev_anchors = parse_spatial_anchors(prev_prompt)
        new_anchors = parse_spatial_anchors(new_prompt)

        # Merge anchors
        merged = {**prev_anchors, **new_anchors}
        anchor_desc = []
        if "monitors" in p_low or "monitor wall" in p_low:
            anchor_desc.append("monitor wall established as fixed focal anchor ahead")
        if "bed" in p_low:
            anchor_desc.append("bed position preserved")
        if "window" in p_low:
            anchor_desc.append("window wall preserved")

        # Character Stage Position Continuity
        pos_regex = r"\b(screen-left|screen-right|screen-center|center frame|stage left|stage right)\b"
        prev_pos_match = re.search(pos_regex, p_low)
        new_pos_match = re.search(pos_regex, n_low)
        if prev_pos_match and new_pos_match and prev_pos_match.group(1) != new_pos_match.group(1):
            has_movement = any(w in n_low for w in ["walk", "step", "stride", "cross", "move", "run"])
            if not has_movement:
                risks.append(RiskItem(
                    category="spatial_position",
                    severity="WARNING",
                    description=f"Character position jump: subject was {prev_pos_match.group(1)} in previous shot but is {new_pos_match.group(1)} without movement steps.",
                    suggestion="Add physical traversal footsteps or preserve established stage coordinates."
                ))

        if anchor_desc:
            geometry_directive = f"Preserve established room geometry: {'; '.join(anchor_desc)}. Do not mirror or rotate the layout. Character stage position locked to established coordinates; zero position jumping."
        else:
            geometry_directive = "Preserve established room geometry and cardinal spatial orientation; do not mirror or invert the layout. Character stage position locked to established coordinates; zero position jumping."

        corrections.append(CorrectionItem(
            category="geometry",
            description="Established room geometry, wall anchors, and character stage coordinates inherited."
        ))
        corrections.append(CorrectionItem(
            category="spatial_position",
            description="Character stage position locked: zero instantaneous position jumping or stage swapping."
        ))

    elif mode == ContinuityMode.TRANSITION:
        # Transition: reset previous room geometry
        geometry_directive = "New location: previous room architecture, wall anchors, and furniture are reset. Establish new spatial geometry for this space."
        corrections.append(CorrectionItem(
            category="geometry",
            description="Previous room geometry reset for transition into new space."
        ))

    else:  # RESET
        geometry_directive = "Complete scene reset: do not carry any previous room geometry, wall anchors, or furniture into this shot."
        corrections.append(CorrectionItem(
            category="geometry",
            description="All previous spatial geometry discarded."
        ))

    # Eyeline check for two characters
    has_two_people = any(
        w in n_low for w in [
            "speaks to", "talks to", "listens to", "looks at", "stares at him", "stares at her",
            "facing each other", "across from", "between them"
        ]
    )
    if has_two_people:
        corrections.append(CorrectionItem(
            category="eyelines",
            description="Eyeline match enforced: subjects orient gaze directly toward each other across the 180-degree line."
        ))

    return geometry_directive, risks, corrections
