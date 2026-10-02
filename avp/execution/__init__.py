"""
avp.execution — ComfyUI headless execution bridge + video API dispatchers.

Components:
  ComfyUIBridge      — REST + WebSocket client for local ComfyUI instances
  WorkflowMutator    — Patches compiled ShotPlan tokens into a base graph JSON
  VideoAPIDispatcher — Routes approved keyframes to cloud video APIs
                       (Kling, Runway) based on shot profile
"""

from __future__ import annotations

import json
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import websocket  # type: ignore[import]
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False

from avp.models import ShotPlan


# ---------------------------------------------------------------------------
# ComfyUI Execution Bridge
# ---------------------------------------------------------------------------

class ComfyUIBridge:
    """Headless REST + WebSocket client for a running ComfyUI instance.

    Dispatches compiled workflow graphs and monitors execution to completion
    via a persistent WebSocket stream.  Raises RuntimeError on node errors.

    Usage::

        bridge = ComfyUIBridge()
        prompt_id = bridge.dispatch_workflow(graph)
        output_paths = bridge.monitor_execution(prompt_id)
    """

    def __init__(self, host: str = "127.0.0.1:8188") -> None:
        self.host = host
        self.client_id = str(uuid.uuid4())
        self._ws: Optional[Any] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open WebSocket connection to the ComfyUI /ws endpoint."""
        if not _WS_AVAILABLE:
            raise RuntimeError(
                "websocket-client is required. Install with: pip install websocket-client"
            )
        self._ws = websocket.WebSocket()
        self._ws.connect(f"ws://{self.host}/ws?clientId={self.client_id}")

    def disconnect(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    def __enter__(self) -> "ComfyUIBridge":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Workflow dispatch
    # ------------------------------------------------------------------

    def dispatch_workflow(self, graph: Dict[str, Any]) -> str:
        """POST a workflow graph to /prompt and return the prompt_id."""
        payload = {"prompt": graph, "client_id": self.client_id}
        encoded = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://{self.host}/prompt",
            data=encoded,
            headers={"Content-Type": "application/json"},
        )
        response_bytes = urllib.request.urlopen(req).read()
        response = json.loads(response_bytes)
        return response["prompt_id"]

    # ------------------------------------------------------------------
    # Execution monitoring
    # ------------------------------------------------------------------

    def monitor_execution(self, prompt_id: str) -> Dict[str, Any]:
        """Block until the given prompt_id completes.

        Returns a dict with output node metadata once all nodes have
        finished executing, or raises RuntimeError on node failure.
        """
        if self._ws is None:
            raise RuntimeError("Call connect() (or use as context manager) before monitoring.")

        outputs: Dict[str, Any] = {}

        while True:
            frame = self._ws.recv()
            if not isinstance(frame, str):
                # Binary frame — skip (image preview bytes)
                continue

            event = json.loads(frame)
            event_type = event.get("type", "")
            data = event.get("data", {})

            if event_type == "executed":
                # Collect per-node outputs (image filenames, etc.)
                if data.get("prompt_id") == prompt_id:
                    node_id = data.get("node")
                    if node_id and "output" in data:
                        outputs[node_id] = data["output"]

            elif event_type == "executing":
                # None node signals full graph completion
                if data.get("prompt_id") == prompt_id and data.get("node") is None:
                    break

            elif event_type == "execution_error":
                raise RuntimeError(
                    f"ComfyUI node execution halted with error: {data}"
                )

        return outputs

    # ------------------------------------------------------------------
    # Queue helpers
    # ------------------------------------------------------------------

    def get_queue_status(self) -> Dict[str, Any]:
        """Return current queue and running job status from /queue."""
        with urllib.request.urlopen(f"http://{self.host}/queue") as resp:
            return json.loads(resp.read())

    def interrupt(self) -> None:
        """Send an interrupt signal to halt the currently running job."""
        req = urllib.request.Request(
            f"http://{self.host}/interrupt",
            data=b"",
            method="POST",
        )
        urllib.request.urlopen(req)


# ---------------------------------------------------------------------------
# Workflow Mutator
# ---------------------------------------------------------------------------

class WorkflowMutator:
    """Patches a base ComfyUI API graph JSON with compiled ShotPlan tokens.

    Base graphs are stored as JSON files in workflows/ and loaded once.
    The mutator updates only the fields that vary per-shot (text encoders,
    seed, image paths) without touching node topology.

    Node ID conventions (must match base graph):
      "positive_encoder"  — KSampler positive text encode node
      "negative_encoder"  — KSampler negative text encode node
      "seed_node"         — KSampler or RandomSeed node
      "load_image"        — LoadImage node for I2V keyframe injection
      "load_tail_image"   — Optional LoadImage node for imageTail
    """

    def __init__(self, base_graph_path: Path) -> None:
        self._base_graph = json.loads(base_graph_path.read_text())

    def _set_node_input(
        self, graph: Dict, node_id: str, input_key: str, value: Any
    ) -> None:
        if node_id not in graph:
            return  # Node not present in this workflow variant — skip silently
        graph[node_id]["inputs"][input_key] = value

    def patch(self, shot: ShotPlan, seed: Optional[int] = None) -> Dict[str, Any]:
        """Return a patched copy of the base graph for the given shot."""
        import copy

        graph = copy.deepcopy(self._base_graph)

        # Text encoders
        if shot.compiled_positive_prompt:
            self._set_node_input(graph, "positive_encoder", "text", shot.compiled_positive_prompt)
        if shot.compiled_negative_prompt:
            self._set_node_input(graph, "negative_encoder", "text", shot.compiled_negative_prompt)

        # Seed (deterministic reproduction)
        if seed is not None:
            self._set_node_input(graph, "seed_node", "seed", seed)

        # Stage 2 keyframe path
        if shot.keyframe_path:
            self._set_node_input(graph, "load_image", "image", shot.keyframe_path)

        # Optional tail frame for dual-keyframe interpolation
        if shot.tail_frame_path:
            self._set_node_input(graph, "load_tail_image", "image", shot.tail_frame_path)

        return graph


# ---------------------------------------------------------------------------
# Cloud Video API Dispatcher
# ---------------------------------------------------------------------------

class VideoAPIDispatcher:
    """Routes approved keyframes to cloud video generation APIs.

    Supports:
      • Kling 3.0 / Omni — REST Elements API
      • Runway Gen-3 / Gen-4 — REST Reference Image API

    The router selects the backend based on shot_type and camera_movement:
      • Complex action, extreme cuts, multi-angle → Kling
      • Architectural sweeps, commercial environment → Runway
      • All other (default) → returns None to indicate local WAN routing
    """

    def __init__(
        self,
        kling_api_key: Optional[str] = None,
        runway_api_key: Optional[str] = None,
    ) -> None:
        self._kling_key = kling_api_key
        self._runway_key = runway_api_key

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------

    def select_backend(self, shot: ShotPlan) -> str:
        """Return backend name: 'kling' | 'runway' | 'local'."""
        if shot.camera_movement in {"Tracking", "Crane-up", "Crane-down", "Pan-left", "Pan-right"}:
            return "kling"
        if shot.shot_type == "WS":
            return "runway"
        return "local"

    # ------------------------------------------------------------------
    # Kling REST dispatcher
    # ------------------------------------------------------------------

    def dispatch_kling(
        self,
        shot: ShotPlan,
        duration_seconds: int = 5,
        element_refs: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Submit a generation task to the Kling Elements API.

        Raises RuntimeError if kling_api_key was not provided.
        """
        if not self._kling_key:
            raise RuntimeError("Kling API key not configured.")

        payload: Dict[str, Any] = {
            "model": "kling-v3",
            "prompt": shot.compiled_positive_prompt,
            "negative_prompt": shot.compiled_negative_prompt,
            "duration": duration_seconds,
        }
        if shot.keyframe_path:
            payload["image"] = shot.keyframe_path  # I2V anchor
        if shot.tail_frame_path:
            payload["tail_image"] = shot.tail_frame_path
        if element_refs:
            payload["element_list"] = element_refs

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.klingai.com/v1/videos/image2video",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._kling_key}",
            },
        )
        response = json.loads(urllib.request.urlopen(req).read())
        return response

    # ------------------------------------------------------------------
    # Runway REST dispatcher
    # ------------------------------------------------------------------

    def dispatch_runway(
        self,
        shot: ShotPlan,
        duration_seconds: int = 5,
        ratio: str = "1280:768",
    ) -> Dict[str, Any]:
        """Submit a generation task to the Runway Gen-4 API."""
        if not self._runway_key:
            raise RuntimeError("Runway API key not configured.")

        payload: Dict[str, Any] = {
            "model": "gen4_turbo",
            "promptText": shot.compiled_positive_prompt,
            "ratio": ratio,
            "duration": duration_seconds,
        }
        if shot.keyframe_path:
            payload["promptImage"] = shot.keyframe_path

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.dev.runwayml.com/v1/image_to_video",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._runway_key}",
                "X-Runway-Version": "2024-11-06",
            },
        )
        response = json.loads(urllib.request.urlopen(req).read())
        return response
