"""
avp.continuity.performance — Emotion, dialogue delivery, listening, and temporal pacing engine.

Translates emotions into observable micro-behaviors, audits dialogue timing,
enforces listening performance, and structures temporal beats.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from avp.continuity.models import CorrectionItem, RiskItem


# Spoken speech rate: ~2.5 words per second for dramatic dialogue
WORDS_PER_SECOND = 2.5


def extract_dialogue(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract speaker and spoken dialogue from prompt text if present.
    Returns: (speaker, dialogue_text) or None
    """
    # Pattern: Name says: "..." or "..."
    match = re.search(r'(?:([A-Z][a-z]+|[A-Z]{2,})\s+(?:says|whispers|responds|replies|shouts|mutters|speaks):\s*)?"([^"]+)"', text)
    if match:
        speaker = match.group(1) or "Subject"
        line = match.group(2).strip()
        return speaker, line

    # Check for says ...
    match2 = re.search(r'\bsays\s+["\']([^"\']+)["\']', text, re.IGNORECASE)
    if match2:
        return "Subject", match2.group(1).strip()

    return None


def audit_dialogue_timing(
    dialogue_text: str,
    shot_duration_sec: float = 6.0
) -> Optional[RiskItem]:
    """
    Audit whether spoken dialogue fits naturally into the allotted shot duration.
    """
    words = dialogue_text.split()
    word_count = len(words)
    estimated_seconds = word_count / WORDS_PER_SECOND

    # If dialogue takes more than 80% of shot duration without room for breathing
    if estimated_seconds > shot_duration_sec:
        return RiskItem(
            category="dialogue_timing",
            severity="WARNING",
            description=(
                f"Dialogue line ({word_count} words, ~{estimated_seconds:.1f}s spoken) "
                f"exceeds shot duration ({shot_duration_sec:.1f}s)."
            ),
            suggestion="Shorten the spoken line, reduce pauses, or split dialogue across multiple shot takes."
        )
    return None


def is_listening_performance(text: str) -> bool:
    """Check if the visible character's primary role in this shot is listening."""
    lower = text.lower()
    return any(
        cue in lower
        for cue in [
            "listens to", "listens silently", "listening", "as she listens",
            "as he listens", "watches silently as", "hears the voice"
        ]
    ) and not any(say in lower for say in ['says "', 'speaks "', 'shouts "'])


def translate_emotion_to_performance(text: str) -> Tuple[Optional[str], List[CorrectionItem]]:
    """
    Translate static emotional labels into observable human micro-behavior and gradual arcs.
    """
    corrections = []
    p_low = text.lower()
    performance_cues = []

    # Shock to determination transition
    if ("shock" in p_low or "frightened" in p_low or "fear" in p_low) and ("determined" in p_low or "determination" in p_low):
        performance_cues.append(
            "Emotional progression: begins with brief stunned stillness and guarded gaze, "
            "then breathing steadies and jaw tightens as expression transitions into controlled, resolute determination"
        )
        corrections.append(CorrectionItem(
            category="emotion",
            description="Emotional transition structured: shock evolves into controlled determination without abrupt jumping."
        ))

    elif "shock" in p_low:
        performance_cues.append(
            "Observable performance: brief physical stillness, widened eyes, slightly interrupted breathing, "
            "restrained micro-expression avoiding melodramatic melodrama"
        )

    elif "frightened" in p_low or "fear" in p_low:
        performance_cues.append(
            "Observable performance: cautious evaluating gaze, shallow controlled breathing, subtle tension around eyes, "
            "guarded posture with restrained physical movement"
        )

    elif "anger" in p_low or "angry" in p_low:
        performance_cues.append(
            "Observable performance: controlled jaw tension, focused unwavering gaze, clipped deliberate speech delivery, "
            "tighter posture without cartoonish screaming"
        )

    elif "determined" in p_low or "determination" in p_low:
        performance_cues.append(
            "Observable performance: focused forward gaze, steady measured breathing, deliberate grounded posture, "
            "restrained self-possession"
        )

    performance_directive = "; ".join(performance_cues) if performance_cues else None
    return performance_directive, corrections


def structure_listening_performance(character_name: str = "Subject") -> str:
    """Generate subtle, realistic listening behavior with suppressed speech mouth movement."""
    return (
        f"Listening performance for {character_name}: mouth remains closed and relaxed with zero speaking lip animation; "
        "natural eye gaze tracking the speaker, rhythmic breathing, subtle listening micro-reactions, "
        "and tiny posture adjustments without excessive nodding."
    )


def structure_temporal_beats(
    action: str,
    emotion: Optional[str] = None,
    dialogue: Optional[str] = None,
    duration_sec: float = 6.0
) -> str:
    """Structure the shot into clear narrative beats."""
    beats = []
    b1_end = max(1.5, duration_sec * 0.25)
    b2_end = max(3.0, duration_sec * 0.6)

    beats.append(f"0.0–{b1_end:.1f}s: Subject establishes initial presence and spatial orientation; {emotion or 'grounded focus'}.")
    beats.append(f"{b1_end:.1f}–{b2_end:.1f}s: Primary action: {action}.")
    if dialogue:
        beats.append(f"{b2_end:.1f}–{duration_sec:.1f}s: Spoken delivery: \"{dialogue}\" with natural pauses, followed by held gaze.")
    else:
        beats.append(f"{b2_end:.1f}–{duration_sec:.1f}s: Final settling beat: subtle deceleration, holding eyeline.")

    return " | ".join(beats)
