"""
avp.continuity.relevance — Scene relationship and conditional relevance analyzer.

Determines whether the upcoming shot represents CONTINUE, TRANSITION, or RESET,
and classifies previous shot details as INHERIT, CONDITIONAL, RESET, or IRRELEVANT.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from avp.continuity.models import (
    ContinuityHandoff,
    ContinuityMode,
    RelevanceType,
)


# Keywords and regex patterns for temporal leaps and reality state shifts
TEMPORAL_LEAP_PATTERNS = [
    r"\bnext morning\b",
    r"\bthe following (day|morning|night|week)\b",
    r"\bthree days later\b",
    r"\b\d+\s+(days?|hours?|weeks?|months?|years?)\s+later\b",
    r"\blater that (day|night|evening)\b",
    r"\bthe next day\b",
    r"\bhours later\b",
    r"\bmorning after\b",
    r"\bmeanwhile\b",
]

FLASHBACK_PATTERNS = [
    r"\bflashback\b",
    r"\b\d+\s+years?\s+earlier\b",
    r"\byears earlier\b",
    r"\bchildhood memory\b",
    r"\bmemory sequence\b",
    r"\bdream sequence\b",
    r"\bin her dream\b",
    r"\bin his dream\b",
]

TRANSITION_VERB_PATTERNS = [
    r"\bleaves?\s+(the\s+)?[\w\s]+\s+and\s+enters?\b",
    r"\bexits?\s+(the\s+)?[\w\s]+\s+and\s+enters?\b",
    r"\bwalks?\s+out\s+(of\s+the\s+)?[\w\s]+\s+into\b",
    r"\bsteps?\s+into\s+(the\s+)?[\w\s]+\b",
    r"\benters?\s+(the\s+)?(hallway|corridor|elevator|lobby|street|courtyard|stairwell|room|office)\b",
    r"\bwalks?\s+down\s+(the\s+)?(hallway|corridor|street|staircase)\b",
    r"\bmoves?\s+to\s+(the\s+)?[\w\s]+\b",
]

# Common environment keywords
LOCATION_KEYWORDS = [
    "surveillance room", "control room", "mansion hallway", "hallway", "corridor",
    "bedroom", "railway station", "train station", "outdoor cafe", "cafe", "safehouse",
    "safe-house", "hospital room", "hospital", "boxing gym", "gym", "warehouse",
    "balcony", "lobby", "rooftop", "alleyway", "kitchen", "office", "elevator",
    "living room", "street", "car", "subway", "interrogation room"
]


def extract_location(text: str) -> Optional[str]:
    """Extract location name or recognized environment from prompt text."""
    lower = text.lower()
    for loc in LOCATION_KEYWORDS:
        if loc in lower:
            return loc
    # Check for INT. / EXT. sluglines if present
    match = re.search(r"\b(INT|EXT)\.?\s+([A-Z0-9\s\-]+?)(?:\s*-\s*(DAY|NIGHT|DUSK|DAWN))?", text, re.IGNORECASE)
    if match:
        return match.group(2).strip().lower()
    return None


def extract_character_names(text: str) -> Set[str]:
    """Extract potential character names from prompt text."""
    # Look for capitalized names commonly appearing in screenplays
    names = set()
    for word in re.findall(r"\b[A-Z][a-z]+\b|\b[A-Z]{3,}\b", text):
        w_upper = word.upper()
        if w_upper not in {
            "THE", "AND", "WITH", "FROM", "INTO", "CAMERA", "CLOSE", "WIDE", "MEDIUM",
            "SHOT", "SCENE", "CONTINUE", "RESET", "TRANSITION", "NORTH", "SOUTH", "EAST",
            "WEST", "DAY", "NIGHT", "SLOWLY", "SUDDENLY", "AFTER", "BEFORE", "FLASHBACK"
        }:
            names.add(word.capitalize())
    return names


def determine_scene_relationship(prev_prompt: str, new_prompt: str) -> ContinuityMode:
    """Classify relationship as CONTINUE, TRANSITION, or RESET."""
    if not prev_prompt or not prev_prompt.strip():
        return ContinuityMode.RESET

    p_low = prev_prompt.lower()
    n_low = new_prompt.lower()

    # 1. Check for Flashback or Dream Shift
    for pat in FLASHBACK_PATTERNS:
        if re.search(pat, n_low):
            return ContinuityMode.RESET

    # 2. Check for Temporal Leaps
    for pat in TEMPORAL_LEAP_PATTERNS:
        if re.search(pat, n_low):
            return ContinuityMode.RESET

    prev_loc = extract_location(prev_prompt)
    new_loc = extract_location(new_prompt)

    # 3. Check for explicit narrative transition verbs (e.g. leaves room, enters hallway)
    for pat in TRANSITION_VERB_PATTERNS:
        if re.search(pat, n_low):
            return ContinuityMode.TRANSITION

    # 4. Check if location changed completely
    if prev_loc and new_loc and prev_loc != new_loc:
        # If moving between adjacent parts of same building (e.g. room -> hallway)
        adjacent_pairs = [
            ("room", "hallway"), ("room", "corridor"), ("surveillance", "hallway"),
            ("bedroom", "hallway"), ("office", "corridor"), ("lobby", "elevator")
        ]
        is_adjacent = any(
            (p in prev_loc and n in new_loc) or (n in prev_loc and p in new_loc)
            for p, n in adjacent_pairs
        )
        if is_adjacent:
            return ContinuityMode.TRANSITION
        else:
            return ContinuityMode.RESET

    # 5. Check for day/night flip without continuous lighting motivation
    has_night_prev = "night" in p_low or "dark" in p_low
    has_day_new = "morning" in n_low or "sunlight" in n_low or "daylight" in n_low or "cafe" in n_low
    if has_night_prev and has_day_new and ("next" in n_low or "morning" in n_low):
        return ContinuityMode.RESET

    # Default: same scene continuation
    return ContinuityMode.CONTINUE


def classify_elements(
    prev_prompt: str,
    new_prompt: str,
    mode: ContinuityMode
) -> Dict[str, Tuple[RelevanceType, str]]:
    """
    Classify key previous details as INHERIT, CONDITIONAL, RESET, or IRRELEVANT.
    Returns: Dict[element_name, (RelevanceType, reason)]
    """
    classifications: Dict[str, Tuple[RelevanceType, str]] = {}

    prev_chars = extract_character_names(prev_prompt)
    new_chars = extract_character_names(new_prompt)
    common_chars = prev_chars.intersection(new_chars)

    # Character Identity
    if common_chars:
        for char in common_chars:
            classifications[f"character_{char}"] = (
                RelevanceType.INHERIT,
                f"Identity for {char} persists across shots"
            )

    # Wardrobe
    # Check if new prompt explicitly defines or changes wardrobe
    has_new_wardrobe = any(
        w in new_prompt.lower()
        for w in [
            "white shirt", "linen shirt", "jacket", "coat", "dress", "suit",
            "blouse", "t-shirt", "trousers", "jeans", "wearing", "changed into"
        ]
    )
    if has_new_wardrobe and "changed into" in new_prompt.lower():
        classifications["wardrobe"] = (
            RelevanceType.RESET,
            "New prompt explicitly updates wardrobe — new garment is authoritative"
        )
    elif mode == ContinuityMode.CONTINUE or mode == ContinuityMode.TRANSITION:
        classifications["wardrobe"] = (
            RelevanceType.INHERIT,
            "Costume continuity carried forward from baseline"
        )
    else:
        classifications["wardrobe"] = (
            RelevanceType.RESET,
            "New scene or temporal leap — previous wardrobe is reset unless specified"
        )

    # Room Geometry & Spatial Anchors
    if mode == ContinuityMode.CONTINUE:
        classifications["room_geometry"] = (
            RelevanceType.INHERIT,
            "Same physical room — preserve established architecture, wall anchors, and furniture"
        )
        classifications["lighting"] = (
            RelevanceType.INHERIT,
            "Preserve established key light and practical color science"
        )
    else:
        classifications["room_geometry"] = (
            RelevanceType.RESET,
            "Location changed or scene reset — previous room geometry, wall anchors, and furniture are reset"
        )
        classifications["lighting"] = (
            RelevanceType.RESET,
            "Previous lighting setup is reset for new environment"
        )

    # Props / Handheld Objects
    classifications["props"] = (
        RelevanceType.CONDITIONAL,
        "Props carried forward only if physically retained or continued in new shot"
    )

    # Camera Position & Movement
    classifications["camera_framing"] = (
        RelevanceType.IRRELEVANT,
        "Camera angle, framing, and movement are established per shot"
    )

    return classifications


def build_continuity_handoff(
    prev_prompt: str,
    new_prompt: str,
    mode: ContinuityMode,
    classifications: Dict[str, Tuple[RelevanceType, str]]
) -> ContinuityHandoff:
    """Build a compact, clean continuity handoff."""
    prev_chars = extract_character_names(prev_prompt)
    new_chars = extract_character_names(new_prompt)
    common_chars = prev_chars.intersection(new_chars)

    prev_loc = extract_location(prev_prompt)
    new_loc = extract_location(new_prompt)

    char_handoff = None
    if common_chars:
        char_handoff = f"Same character identity for {', '.join(sorted(common_chars))}."

    loc_handoff = None
    reset_summary = None
    if mode == ContinuityMode.CONTINUE:
        loc_handoff = f"Continuous in {new_loc or 'same room'}; established spatial anchors and room geometry retained."
    elif mode == ContinuityMode.TRANSITION:
        loc_handoff = f"Transitioned to {new_loc or 'new space'}; previous room geometry and furniture are reset."
        reset_summary = f"Previous {prev_loc or 'room'} architecture and camera position discarded."
    else:
        loc_handoff = f"New scene in {new_loc or 'new location'}; complete environmental reset."
        reset_summary = f"All previous environment, lighting, and camera details discarded."

    return ContinuityHandoff(
        mode=mode,
        character_handoff=char_handoff,
        location_handoff=loc_handoff,
        reset_summary=reset_summary
    )
