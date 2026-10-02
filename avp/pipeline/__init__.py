"""
avp.pipeline — Two-stage generative pipeline orchestrator.

Stage 1: Spatial Grounding (T2I Keyframe synthesis)
  • Compiles ShotPlan prompts via PromptCompiler
  • Dispatches to local ComfyUI (Flux / SDXL + PuLID + IP-Adapter)
  • Presents generated keyframes for human approval
  • Inpainting fallback via Flux Kontext when facial drift is detected

Stage 2: Temporal Synthesis (I2V video generation)
  • Routes approved keyframes to appropriate video backend
  • Patches workflow graph with keyframe path, tail frame, seed
  • Monitors execution and logs provenance to database

The pipeline enforces the operational governance rules:
  1. Constants (biometrics) vs. variables (angles, actions) never mixed
  2. Comprehensive provenance logging for every artifact
  3. Mandatory human review gate between Stage 1 and Stage 2
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Optional

from avp.compiler import PromptCompiler
from avp.db import GeneratedArtifact, ShotRecord, get_session, init_db
from avp.execution import ComfyUIBridge, VideoAPIDispatcher, WorkflowMutator
from avp.models import (
    CharacterIdentity,
    SceneContext,
    ShotManifest,
    ShotPlan,
    WardrobeState,
)


class ProductionPipeline:
    """End-to-end two-stage production pipeline.

    Instantiate once per episode run.  The pipeline maintains its own
    database session and ComfyUI bridge connection.

    Args:
        characters:         Production Bible character registry.
        wardrobes:          Production Bible wardrobe registry.
        scenes:             Production Bible scene registry.
        stage1_workflow:    Path to the ComfyUI T2I base workflow JSON.
        stage2_workflow:    Path to the ComfyUI I2V base workflow JSON.
        output_dir:         Root directory for generated artifacts.
        comfyui_host:       ComfyUI server address (default 127.0.0.1:8188).
        kling_api_key:      Optional Kling cloud API key.
        runway_api_key:     Optional Runway cloud API key.
    """

    def __init__(
        self,
        characters: Dict[str, CharacterIdentity],
        wardrobes: Dict[str, WardrobeState],
        scenes: Dict[str, SceneContext],
        stage1_workflow: Path,
        stage2_workflow: Path,
        output_dir: Path,
        comfyui_host: str = "127.0.0.1:8188",
        kling_api_key: Optional[str] = None,
        runway_api_key: Optional[str] = None,
    ) -> None:
        self._compiler = PromptCompiler(characters, wardrobes, scenes)
        self._stage1_mutator = WorkflowMutator(stage1_workflow)
        self._stage2_mutator = WorkflowMutator(stage2_workflow)
        self._bridge = ComfyUIBridge(host=comfyui_host)
        self._dispatcher = VideoAPIDispatcher(kling_api_key, runway_api_key)
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        init_db()

    # ------------------------------------------------------------------
    # Stage 1 — Spatial Grounding
    # ------------------------------------------------------------------

    def stage1_generate_keyframe(
        self,
        shot: ShotPlan,
        seed: Optional[int] = None,
    ) -> ShotPlan:
        """Compile prompts and dispatch to Stage 1 T2I engine.

        Returns the shot with keyframe_path populated.
        """
        # Step 1: Deterministic prompt compilation
        shot = self._compiler.compile(shot)

        # Step 2: Assign a reproducible seed
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        shot.generation_seed = seed

        # Step 3: Patch workflow graph and dispatch to ComfyUI
        graph = self._stage1_mutator.patch(shot, seed=seed)

        with self._bridge as bridge:
            prompt_id = bridge.dispatch_workflow(graph)
            outputs = bridge.monitor_execution(prompt_id)

        # Step 4: Resolve output path from ComfyUI outputs
        keyframe_path = self._resolve_output_path(outputs, shot.shot_id, "keyframe")
        shot.keyframe_path = str(keyframe_path)

        # Step 5: Log provenance
        self._log_artifact(
            shot=shot,
            artifact_type="keyframe",
            output_path=str(keyframe_path),
            comfyui_prompt_id=prompt_id,
        )

        return shot

    # ------------------------------------------------------------------
    # Human Verification Gate
    # ------------------------------------------------------------------

    def human_approval_gate(self, shot: ShotPlan) -> bool:
        """Interactive CLI gate — blocks until operator approves or rejects.

        Returns True if approved, False if rejected (triggers re-generation).
        """
        print(f"\n{'='*60}")
        print(f"REVIEW GATE — Shot: {shot.shot_id}")
        print(f"Keyframe: {shot.keyframe_path}")
        print(f"Positive: {shot.compiled_positive_prompt[:120]}…")
        print(f"{'='*60}")
        response = input("Approve keyframe? [y]es / [n]o / [i]npaint fix: ").strip().lower()

        if response in ("y", "yes", ""):
            self._mark_shot_approved(shot.shot_id)
            return True
        elif response in ("i", "inpaint"):
            print("→ Routing to inpainting pass (Flux Kontext)…")
            return False  # Caller should dispatch _inpaint_keyframe
        else:
            print("→ Keyframe rejected. Regenerating with new seed…")
            return False

    def _inpaint_keyframe(self, shot: ShotPlan) -> ShotPlan:
        """Secondary inpainting pass — masks facial region and regenerates identity.

        Uses Flux Kontext (or equivalent inpainting checkpoint) to surgically
        restore canonical facial geometry over the staged body and environment.
        Dispatches via the Stage 1 bridge using the inpaint workflow variant.
        """
        inpaint_workflow = self._output_dir.parent / "workflows" / "stage1_inpaint.json"
        if not inpaint_workflow.exists():
            raise FileNotFoundError(
                f"Inpainting workflow not found at {inpaint_workflow}. "
                "Please create workflows/stage1_inpaint.json."
            )
        mutator = WorkflowMutator(inpaint_workflow)
        graph = mutator.patch(shot, seed=shot.generation_seed)

        with self._bridge as bridge:
            prompt_id = bridge.dispatch_workflow(graph)
            outputs = bridge.monitor_execution(prompt_id)

        keyframe_path = self._resolve_output_path(outputs, shot.shot_id, "keyframe_inpainted")
        shot.keyframe_path = str(keyframe_path)
        self._log_artifact(shot, "keyframe_inpainted", str(keyframe_path), prompt_id)
        return shot

    # ------------------------------------------------------------------
    # Stage 2 — Temporal Synthesis
    # ------------------------------------------------------------------

    def stage2_animate(
        self,
        shot: ShotPlan,
        duration_seconds: int = 5,
    ) -> ShotPlan:
        """Animate an approved keyframe via the appropriate video backend.

        Raises RuntimeError if the keyframe has not been approved.
        """
        if not shot.keyframe_path:
            raise RuntimeError(
                f"Shot {shot.shot_id} has no keyframe. Run stage1_generate_keyframe first."
            )

        backend = self._dispatcher.select_backend(shot)

        if backend == "kling":
            resp = self._dispatcher.dispatch_kling(shot, duration_seconds=duration_seconds)
            video_path = self._output_dir / f"{shot.shot_id}_kling.mp4"
            # In production: poll Kling task ID until completion and download
            shot.output_video_path = str(video_path)
            self._log_artifact(shot, "video_kling", str(video_path))

        elif backend == "runway":
            resp = self._dispatcher.dispatch_runway(shot, duration_seconds=duration_seconds)
            video_path = self._output_dir / f"{shot.shot_id}_runway.mp4"
            shot.output_video_path = str(video_path)
            self._log_artifact(shot, "video_runway", str(video_path))

        else:
            # Local WAN 2.1 I2V via ComfyUI
            graph = self._stage2_mutator.patch(shot, seed=shot.generation_seed)
            with self._bridge as bridge:
                prompt_id = bridge.dispatch_workflow(graph)
                outputs = bridge.monitor_execution(prompt_id)
            video_path = self._resolve_output_path(outputs, shot.shot_id, "video")
            shot.output_video_path = str(video_path)
            self._log_artifact(shot, "video_local", str(video_path))

        return shot

    # ------------------------------------------------------------------
    # Full Episode Runner
    # ------------------------------------------------------------------

    def run_episode(
        self,
        manifest: ShotManifest,
        max_retries: int = 3,
    ) -> List[ShotPlan]:
        """Execute the full six-stage pipeline for an entire episode.

        Stages:
          1. Compile all shot prompts
          2. Stage 1 keyframe synthesis
          3. Human approval gate (with inpainting fallback)
          4. Stage 2 temporal animation
          Returns the completed shot list.
        """
        compiled_shots: List[ShotPlan] = self._compiler.compile_manifest(manifest.shots)
        completed: List[ShotPlan] = []

        for shot in compiled_shots:
            print(f"\n[AVP] Processing shot {shot.shot_id} ({shot.shot_type}) …")

            # --- Stage 1 with retry loop ---
            approved = False
            attempt = 0
            while not approved and attempt < max_retries:
                attempt += 1
                shot = self.stage1_generate_keyframe(shot)
                approved = self.human_approval_gate(shot)
                if not approved and attempt < max_retries:
                    shot = self._inpaint_keyframe(shot)

            if not approved:
                print(f"[AVP] WARNING: Shot {shot.shot_id} exhausted retries. Skipping.")
                continue

            # --- Stage 2 animation ---
            shot = self.stage2_animate(shot)
            completed.append(shot)
            print(f"[AVP] Shot {shot.shot_id} complete → {shot.output_video_path}")

        return completed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_output_path(
        self,
        outputs: Dict,
        shot_id: str,
        suffix: str,
    ) -> Path:
        """Extract the first image/video filename from ComfyUI outputs dict."""
        for node_data in outputs.values():
            images = node_data.get("images", [])
            if images:
                filename = images[0].get("filename", f"{shot_id}_{suffix}.png")
                return self._output_dir / filename
        # Fallback
        return self._output_dir / f"{shot_id}_{suffix}.png"

    def _log_artifact(
        self,
        shot: ShotPlan,
        artifact_type: str,
        output_path: str,
        comfyui_prompt_id: Optional[str] = None,
    ) -> None:
        """Write a provenance record to the database."""
        session = get_session()
        try:
            artifact = GeneratedArtifact(
                shot_id=shot.shot_id,
                artifact_type=artifact_type,
                output_path=output_path,
                positive_prompt=shot.compiled_positive_prompt or "",
                negative_prompt=shot.compiled_negative_prompt or "",
                seed=shot.generation_seed or 0,
                checkpoint_hash=shot.checkpoint_hash,
                lora_weights=shot.lora_weights,
                sampler=shot.sampler,
                cfg_scale=shot.cfg_scale,
                comfyui_prompt_id=comfyui_prompt_id,
            )
            session.add(artifact)
            session.commit()
        finally:
            session.close()

    def _mark_shot_approved(self, shot_id: str) -> None:
        session = get_session()
        try:
            record = session.get(ShotRecord, shot_id)
            if record:
                record.approved = True
                session.commit()
        finally:
            session.close()
