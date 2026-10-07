"""
avp.continuity.bridge — Continuity Bridge orchestrator.

Sits before the prompt compiler or functions standalone on raw prompt pairs:
  Previous Shot Prompt + New Shot Prompt
  → Continuity Bridge
  → Relevance, Contradiction, Geometry, Realism, Performance
  → Concise User Report + Clean Final Generation Prompt.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from avp.continuity.analyzer import (
    ContinuityAnalysisResult,
    run_continuity_analysis,
)
from avp.continuity.models import (
    ContinuityHandoff,
    ContinuityMode,
    ContinuityReport,
    RelevanceType,
)
from avp.continuity.performance import structure_temporal_beats
from avp.continuity.relevance import extract_character_names, extract_location


class ContinuityBridge:
    """Prompt-centric continuity and human-realism orchestration engine."""

    def __init__(self) -> None:
        pass

    def analyze_and_optimize(
        self,
        prev_prompt: str,
        new_prompt: str,
        duration_sec: float = 6.0,
        shot_type: Optional[str] = None
    ) -> ContinuityReport:
        """
        Analyze the previous and new prompts, detect contradictions,
        enforce human kinematics and geometry, and synthesize ONE clean optimized prompt.
        """
        analysis = run_continuity_analysis(prev_prompt, new_prompt, duration_sec)
        final_prompt = self._synthesize_final_prompt(
            prev_prompt,
            new_prompt,
            analysis,
            duration_sec,
            shot_type
        )

        # Build clean user-facing strings
        user_risks = [
            f"⚠ {r.description} (Suggestion: {r.suggestion})" if r.suggestion else f"⚠ {r.description}"
            for r in analysis.risks
        ]
        user_corrections = [f"✓ {c.description}" for c in analysis.corrections]

        return ContinuityReport(
            mode=analysis.mode,
            continuity_items=analysis.continuity_items,
            risks=user_risks,
            corrections=user_corrections,
            handoff=analysis.handoff,
            final_prompt=final_prompt,
            negative_prompt=analysis.dynamic_negative,
            detailed_analysis=analysis.detailed_analysis
        )

    def _synthesize_final_prompt(
        self,
        prev_prompt: str,
        new_prompt: str,
        analysis: ContinuityAnalysisResult,
        duration_sec: float,
        shot_type: Optional[str]
    ) -> str:
        """
        Assemble the final generation prompt strictly following the Prompt Density Principle.
        Only includes sections that are necessary for consistency and physical plausibility.
        """
        sections: List[str] = []

        # 1. Cleaned Core Shot Action from new_prompt
        clean_new = self._clean_source_prompt(new_prompt)

        # 2. Subject & Identity Locks (from handoff if relevant)
        prev_chars = extract_character_names(prev_prompt)
        new_chars = extract_character_names(new_prompt)
        common_chars = prev_chars.intersection(new_chars)

        char_lock = ""
        if common_chars:
            names = ", ".join(sorted(common_chars))
            # Wardrobe status
            ward_status = analysis.classifications.get("wardrobe")
            ward_phrase = ""
            if ward_status and ward_status[0] == RelevanceType.INHERIT:
                # check if prev had specific wardrobe
                match_ward = re.search(
                    r"\b(?:wearing\s+(?:an?\s+)?|in\s+(?:an?\s+)?)([\w\s]{2,30}?(?:blouse|shirt|jacket|suit|dress|trousers|sweater|coat|turtleneck|jeans|hoodie))",
                    prev_prompt,
                    re.I
                )
                if match_ward:
                    ward_phrase = f", preserving {match_ward.group(1).strip()}"
            char_lock = f"[SUBJECT + IDENTITY]: Consistent identity for {names}{ward_phrase}."

        if char_lock:
            sections.append(char_lock)

        # 3. Environment & Spatial Geometry
        if analysis.mode == ContinuityMode.CONTINUE:
            if analysis.spatial_directive:
                sections.append(f"[SPATIAL GEOMETRY]: {analysis.spatial_directive}")
        elif analysis.mode == ContinuityMode.TRANSITION:
            new_loc = extract_location(new_prompt) or "new setting"
            sections.append(
                f"[ENVIRONMENT]: Established in {new_loc}. Previous room geometry, monitors, and furniture are reset and not visible."
            )
        else:  # RESET
            new_loc = extract_location(new_prompt) or "new setting"
            sections.append(
                f"[ENVIRONMENT]: New scene established in {new_loc}. All previous room architecture, lighting, and props are completely reset."
            )

        # 4. Action & Temporal Beats
        temporal_beats = structure_temporal_beats(
            action=clean_new,
            emotion=analysis.emotion_directive,
            dialogue=analysis.dialogue_info[1] if analysis.dialogue_info else None,
            duration_sec=duration_sec
        )
        sections.append(f"[ACTION + TEMPORAL BEATS]: {temporal_beats}")

        # 5. Performance / Emotion / Dialogue
        if analysis.listening_directive:
            sections.append(f"[PERFORMANCE]: {analysis.listening_directive}")
        elif analysis.emotion_directive:
            sections.append(f"[EMOTIONAL PERFORMANCE]: {analysis.emotion_directive}")

        if analysis.dialogue_info and not analysis.listening_directive:
            speaker, line = analysis.dialogue_info
            sections.append(
                f"[DIALOGUE + DELIVERY]: {speaker} speaks: \"{line}\" with quiet, measured cadence, natural breaths, and synchronized mouth articulation."
            )

        # 6. Movement Kinematics
        if analysis.movement_directive:
            sections.append(f"[KINEMATICS]: {analysis.movement_directive}")

        # 7. Physical Realism Safeguards (Targeted only)
        if analysis.anatomical_safeguards:
            safeguards_str = "; ".join(analysis.anatomical_safeguards)
            sections.append(f"[PHYSICAL REALISM]: {safeguards_str}.")

        return "\n\n".join(sections)

    def _clean_source_prompt(self, text: str) -> str:
        """Strip redundant filler and normalize whitespace."""
        cleaned = text.strip()
        # Remove markdown headers if present
        cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
        return cleaned

    def bridge_shot_plans(
        self,
        prev_shot: Optional[Any],
        new_shot: Any,
        compiler: Optional[Any] = None
    ) -> Any:
        """
        Integrate directly with existing avp.compiler.PromptCompiler.
        Sits before compiler, injecting continuity context into the ShotPlan.
        """
        prev_prompt = getattr(prev_shot, "action_beat", "") if prev_shot else ""
        new_prompt = getattr(new_shot, "action_beat", "")

        report = self.analyze_and_optimize(prev_prompt, new_prompt)

        # Augment action_beat with temporal beats and continuity constraints
        new_shot.action_beat = report.final_prompt

        if compiler:
            return compiler.compile(new_shot)
        return new_shot
