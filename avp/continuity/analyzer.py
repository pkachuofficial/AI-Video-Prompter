"""
avp.continuity.analyzer — Multi-pass continuity and human-realism analyzer.

Executes the conceptual pipeline:
  Scene Relationship Analysis → Relevance/Reset Analysis → Contradiction Detection →
  Human Realism Analysis → Cinematic/Geometry Analysis → Pacing Analysis →
  Performance/Dialogue Analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from avp.continuity.contradiction import audit_contradictions
from avp.continuity.geometry import analyze_spatial_continuity
from avp.continuity.models import (
    ContinuityHandoff,
    ContinuityMode,
    CorrectionItem,
    RelevanceType,
    RiskItem,
)
from avp.continuity.performance import (
    audit_dialogue_timing,
    extract_dialogue,
    is_listening_performance,
    structure_listening_performance,
    translate_emotion_to_performance,
)
from avp.continuity.realism import (
    analyze_anatomical_safeguards,
    analyze_movement_kinematics,
    build_dynamic_negative_constraints,
)
from avp.continuity.relevance import (
    build_continuity_handoff,
    classify_elements,
    determine_scene_relationship,
    extract_character_names,
    extract_location,
)


class ContinuityAnalysisResult:
    """Internal container for the complete analysis pass."""
    def __init__(
        self,
        mode: ContinuityMode,
        classifications: Dict[str, Tuple[RelevanceType, str]],
        handoff: ContinuityHandoff,
        continuity_items: List[str],
        risks: List[RiskItem],
        corrections: List[CorrectionItem],
        movement_directive: Optional[str],
        spatial_directive: Optional[str],
        emotion_directive: Optional[str],
        listening_directive: Optional[str],
        anatomical_safeguards: List[str],
        dialogue_info: Optional[Tuple[str, str]],
        dynamic_negative: str,
        detailed_analysis: Dict[str, Any]
    ) -> None:
        self.mode = mode
        self.classifications = classifications
        self.handoff = handoff
        self.continuity_items = continuity_items
        self.risks = risks
        self.corrections = corrections
        self.movement_directive = movement_directive
        self.spatial_directive = spatial_directive
        self.emotion_directive = emotion_directive
        self.listening_directive = listening_directive
        self.anatomical_safeguards = anatomical_safeguards
        self.dialogue_info = dialogue_info
        self.dynamic_negative = dynamic_negative
        self.detailed_analysis = detailed_analysis


def run_continuity_analysis(
    prev_prompt: str,
    new_prompt: str,
    duration_sec: float = 6.0
) -> ContinuityAnalysisResult:
    """
    Run full multi-pass analysis on the pair of shot prompts.
    """
    # 1. Scene Relationship
    mode = determine_scene_relationship(prev_prompt, new_prompt)

    # 2. Relevance / Reset Classification
    classifications = classify_elements(prev_prompt, new_prompt, mode)
    handoff = build_continuity_handoff(prev_prompt, new_prompt, mode, classifications)

    # 3. Contradiction Detection
    contradictions, contra_risks, contra_corrections = audit_contradictions(prev_prompt, new_prompt)

    # 4. Spatial & Geometry Analysis
    spatial_directive, geom_risks, geom_corrections = analyze_spatial_continuity(prev_prompt, new_prompt, mode)

    # 5. Human Realism & Kinematics
    movement_directive, move_risks, move_corrections = analyze_movement_kinematics(new_prompt)
    anatomical_safeguards = analyze_anatomical_safeguards(new_prompt)

    # 6. Performance, Emotion & Dialogue
    emotion_directive, emotion_corrections = translate_emotion_to_performance(new_prompt)
    dialogue_info = extract_dialogue(new_prompt)

    perf_risks: List[RiskItem] = []
    perf_corrections: List[CorrectionItem] = []

    if dialogue_info:
        speaker, line = dialogue_info
        timing_risk = audit_dialogue_timing(line, duration_sec)
        if timing_risk:
            perf_risks.append(timing_risk)
            perf_corrections.append(CorrectionItem(
                category="dialogue",
                description="Dialogue structured: pacing adjusted for shot duration."
            ))

    listening_directive = None
    has_listening = is_listening_performance(new_prompt)
    if has_listening:
        prev_chars = extract_character_names(prev_prompt)
        new_chars = extract_character_names(new_prompt)
        char_name = next(iter(new_chars.intersection(prev_chars) or new_chars), "Subject")
        listening_directive = structure_listening_performance(char_name)
        perf_corrections.append(CorrectionItem(
            category="listening",
            description="Listening performance: speaking-mouth animation suppressed; realistic micro-reactions added."
        ))

    # Compile user-facing concise items
    continuity_items: List[str] = []
    prev_chars = extract_character_names(prev_prompt)
    new_chars = extract_character_names(new_prompt)
    common_chars = prev_chars.intersection(new_chars)

    if common_chars:
        continuity_items.append(f"✓ Same character ({', '.join(sorted(common_chars))})")

    # Wardrobe status
    ward_cls = classifications.get("wardrobe")
    if ward_cls:
        if ward_cls[0] == RelevanceType.INHERIT:
            continuity_items.append("✓ Wardrobe carried forward")
        elif ward_cls[0] == RelevanceType.RESET:
            continuity_items.append("✓ Wardrobe updated to new shot specification")

    # Location / Environment status
    if mode == ContinuityMode.CONTINUE:
        continuity_items.append("✓ Same room geometry and spatial anchors preserved")
    elif mode == ContinuityMode.TRANSITION:
        continuity_items.append("↻ Location changed — previous environment and camera geometry reset")
    else:
        continuity_items.append("↻ Genuinely new scene — previous environment, lighting, and props reset")

    # Emotional status
    if emotion_directive:
        continuity_items.append("✓ Emotional progression preserved")

    # Aggregate risks and corrections
    all_risks = contra_risks + geom_risks + move_risks + perf_risks
    all_corrections = contra_corrections + geom_corrections + move_corrections + emotion_corrections + perf_corrections

    has_scene_change = mode in (ContinuityMode.TRANSITION, ContinuityMode.RESET)
    has_dialogue = dialogue_info is not None
    has_screen_media = "character_duplication" in [r.category for r in all_risks]

    dynamic_negative = build_dynamic_negative_constraints(
        new_prompt,
        has_scene_change=has_scene_change,
        has_dialogue=has_dialogue,
        has_listening=has_listening,
        has_screen_media=has_screen_media
    )

    detailed_analysis = {
        "mode": mode.value,
        "classifications": {k: {"relevance": v[0].value, "reason": v[1]} for k, v in classifications.items()},
        "contradictions": [c.model_dump() for c in contradictions],
        "risks": [r.model_dump() for r in all_risks],
        "corrections": [c.model_dump() for c in all_corrections],
        "movement_directive": movement_directive,
        "spatial_directive": spatial_directive,
        "emotion_directive": emotion_directive,
        "listening_directive": listening_directive,
        "anatomical_safeguards": anatomical_safeguards,
    }

    return ContinuityAnalysisResult(
        mode=mode,
        classifications=classifications,
        handoff=handoff,
        continuity_items=continuity_items,
        risks=all_risks,
        corrections=all_corrections,
        movement_directive=movement_directive,
        spatial_directive=spatial_directive,
        emotion_directive=emotion_directive,
        listening_directive=listening_directive,
        anatomical_safeguards=anatomical_safeguards,
        dialogue_info=dialogue_info,
        dynamic_negative=dynamic_negative,
        detailed_analysis=detailed_analysis
    )
