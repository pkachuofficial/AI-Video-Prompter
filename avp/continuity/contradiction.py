"""
avp.continuity.contradiction — Contradiction detector and resolution engine.

Applies strict resolution priority:
  1. Explicit NEW SHOT PROMPT (Authoritative)
  2. Physical reality
  3. Narrative continuity
  4. Previous SHOT PROMPT
  5. Generic cinematic convention
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from avp.continuity.models import ContradictionItem, CorrectionItem, RiskItem


def detect_camera_contradictions(prompt: str) -> List[Tuple[str, str, str]]:
    """
    Detect physical camera contradictions in a prompt.
    Returns: List of (description, resolution, category)
    """
    contradictions = []
    p_low = prompt.lower()

    # 1. Camera behind character vs Frontal facial view
    has_behind = bool(
        re.search(r"\b(behind\s+.*shoulder|behind\s+character|from\s+behind|positioned\s+.*behind|camera\s+.*behind)\b", p_low)
        or ("behind" in p_low and "camera" in p_low)
    )
    has_frontal = bool(
        re.search(r"\b(frontal|facing\s+camera|front\s+of\s+face|eyes\s+.*into\s+lens)\b", p_low)
    )

    if has_behind and has_frontal:
        contradictions.append((
            "Camera position behind subject directly conflicts with frontal facial view/close-up.",
            "Camera re-positioned to frontal three-quarter angle (or subject turns head over shoulder) to ensure facial visibility.",
            "camera"
        ))

    # 2. Extreme close-up vs Full body visible
    has_ecu = "extreme close-up" in p_low or "ecu" in p_low or "macro facial" in p_low
    has_full_body = "full body" in p_low or "full-body" in p_low or "head-to-toe" in p_low
    if has_ecu and has_full_body and "transition" not in p_low:
        contradictions.append((
            "Extreme close-up framing contradicts full-body visibility in a single static take.",
            "Framing unified: prioritize close-up facial features and suppress full-body requirement.",
            "camera"
        ))

    return contradictions


def detect_wardrobe_contradictions(prev_prompt: str, new_prompt: str) -> Optional[Tuple[str, str, str]]:
    """
    Check if previous wardrobe contradicts new explicit wardrobe.
    NEW PROMPT WINS: Previous wardrobe is not an error; new garment is authoritative.
    """
    p_low = prev_prompt.lower()
    n_low = new_prompt.lower()

    # Detect wardrobe markers
    garment_pairs = [
        ("black jacket", "white shirt"),
        ("black leather jacket", "white shirt"),
        ("jacket", "white shirt"),
        ("turtleneck", "shirt"),
        ("suit", "t-shirt"),
        ("coat", "blouse"),
        ("black jacket", "white linen shirt"),
    ]

    for prev_g, new_g in garment_pairs:
        if prev_g in p_low and new_g in n_low:
            return (
                f"Previous '{prev_g}' replaced by explicit '{new_g}'.",
                f"Authoritative update: '{new_g}' enforced; previous '{prev_g}' discarded.",
                "wardrobe"
            )

    if "changed into" in n_low:
        match = re.search(r"changed into\s+([^,.]+)", n_low)
        if match:
            new_item = match.group(1).strip()
            return (
                f"Wardrobe update: changed into {new_item}.",
                f"Authoritative update: '{new_item}' enforced; previous wardrobe discarded.",
                "wardrobe"
            )

    return None


def detect_prop_transfer(prev_prompt: str, new_prompt: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect prop state changes (e.g. holds phone -> puts phone on table).
    """
    p_low = prev_prompt.lower()
    n_low = new_prompt.lower()

    prop_cues = ["phone", "smartphone", "glass", "cup", "folder", "key", "gun", "book", "bag"]
    for prop in prop_cues:
        prev_held = (f"holds {prop}" in p_low or f"holding {prop}" in p_low or f"holding a {prop}" in p_low or f"holds a {prop}" in p_low)
        new_placed = (
            f"places the {prop}" in n_low or f"puts the {prop}" in n_low or
            f"sets the {prop}" in n_low or f"{prop} on table" in n_low or
            f"{prop} on the table" in n_low or f"{prop} into her pocket" in n_low or
            f"{prop} into pocket" in n_low or f"{prop} down" in n_low
        )
        if prev_held and new_placed:
            return (
                f"Prop state transition: {prop.capitalize()} was previously held and is now placed down/stored.",
                f"{prop.capitalize()} is resting in new position; subject's hand is no longer holding it.",
                "prop"
            )

    return None


def detect_screen_direction_issue(prev_prompt: str, new_prompt: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect unintentional screen direction reversals.
    """
    p_low = prev_prompt.lower()
    n_low = new_prompt.lower()

    exited_left = "exits frame left" in p_low or "exits screen left" in p_low or "moves left" in p_low
    if exited_left and "continues" in n_low:
        return (
            "Screen direction preservation: previous shot exited frame-left.",
            "Maintain directional continuity: enter from screen-right moving toward screen-left.",
            "screen_direction"
        )
    return None


def detect_duplicate_character_risk(prompt: str) -> Optional[Tuple[str, str, str]]:
    """
    Detect risk of generating duplicate physical people when monitor/recording is present.
    """
    p_low = prompt.lower()
    has_screen_media = any(w in p_low for w in ["monitor", "surveillance screen", "tv screen", "recorded video", "video playback", "footage of"])
    has_same_character = any(w in p_low for w in ["watching", "playback of", "screen showing", "recording of"])

    if has_screen_media and has_same_character:
        return (
            "Potential character duplication / duplicate character risk: physical subject in room + recorded video of same subject on monitor.",
            "Enforce single physical character in room; monitor footage strictly confined to the flat screen surface.",
            "character_duplication"
        )
    return None


def audit_contradictions(
    prev_prompt: str,
    new_prompt: str
) -> Tuple[List[ContradictionItem], List[RiskItem], List[CorrectionItem]]:
    """
    Comprehensive contradiction and integrity audit.
    """
    contradictions: List[ContradictionItem] = []
    risks: List[RiskItem] = []
    corrections: List[CorrectionItem] = []

    # 1. Camera contradictions in new prompt
    cam_issues = detect_camera_contradictions(new_prompt)
    for desc, res, cat in cam_issues:
        contradictions.append(ContradictionItem(
            category=cat,
            description=desc,
            resolution=res,
            priority_applied="Physical reality and creative intent alignment"
        ))
        risks.append(RiskItem(
            category="camera",
            severity="WARNING",
            description=desc,
            suggestion=res
        ))
        corrections.append(CorrectionItem(
            category="camera",
            description=f"Camera corrected: {res}"
        ))

    # 2. Wardrobe change
    ward_change = detect_wardrobe_contradictions(prev_prompt, new_prompt)
    if ward_change:
        desc, res, cat = ward_change
        contradictions.append(ContradictionItem(
            category=cat,
            description=desc,
            resolution=res,
            priority_applied="Explicit NEW SHOT PROMPT wins"
        ))
        corrections.append(CorrectionItem(
            category="wardrobe",
            description=f"Wardrobe updated: {res}"
        ))

    # 3. Prop transfer
    prop_change = detect_prop_transfer(prev_prompt, new_prompt)
    if prop_change:
        desc, res, cat = prop_change
        contradictions.append(ContradictionItem(
            category=cat,
            description=desc,
            resolution=res,
            priority_applied="Physical reality / state change"
        ))
        corrections.append(CorrectionItem(
            category="props",
            description=f"Prop state resolved: {res}"
        ))

    # 4. Screen direction
    dir_issue = detect_screen_direction_issue(prev_prompt, new_prompt)
    if dir_issue:
        desc, res, cat = dir_issue
        corrections.append(CorrectionItem(
            category="screen_direction",
            description=f"Directional continuity preserved: {res}"
        ))

    # 5. Duplicate character
    dup_issue = detect_duplicate_character_risk(new_prompt)
    if dup_issue:
        desc, res, cat = dup_issue
        risks.append(RiskItem(
            category="character_duplication",
            severity="WARNING",
            description=desc,
            suggestion=res
        ))
        corrections.append(CorrectionItem(
            category="character_duplication",
            description=f"Duplicate prevention enforced: {res}"
        ))

    return contradictions, risks, corrections
