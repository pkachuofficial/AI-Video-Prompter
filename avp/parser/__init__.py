"""
avp.parser — Screenplay ingestion and scene-graph extraction.

Supports two industry-standard formats:
  • .fountain  — plain-text Fountain markup
  • .fdx       — Final Draft XML (FDX)

Output: a list of ParsedScene objects that downstream components consume.

Architecture:
  ScreenplayParser (façade)
    ├── FountainBackend   — regex state-machine over Fountain lines
    └── FDXBackend        — lxml ElementTree walk over <Paragraph> nodes

Each backend emits the same intermediate representation so the rest of
the pipeline remains format-agnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Intermediate Representation
# ---------------------------------------------------------------------------

@dataclass
class DialogueLine:
    character: str
    parenthetical: Optional[str]
    text: str


@dataclass
class ActionBeat:
    """A single paragraph of action / description."""
    raw_text: str
    characters_mentioned: List[str] = field(default_factory=list)
    props_mentioned: List[str] = field(default_factory=list)


@dataclass
class ParsedScene:
    """Document-object-model node for a single screenplay scene."""

    scene_number: Optional[str]           # e.g. "7" or "7A"
    slug: str                             # raw slugline, e.g. "INT. OBSIDIAN SAFE-HOUSE - NIGHT"
    setting: str                          # "INT" | "EXT" | "INT/EXT"
    location: str                         # "OBSIDIAN SAFE-HOUSE"
    time_of_day: str                      # "NIGHT", "DAY", etc.
    action_beats: List[ActionBeat] = field(default_factory=list)
    dialogue: List[DialogueLine] = field(default_factory=list)
    characters_present: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

# Slugline pattern: INT./EXT./INT/EXT followed by location and optional time
_SLUGLINE_RE = re.compile(
    r"^(INT\.?|EXT\.?|INT\.?/EXT\.?|I/E)\s+(.+?)(?:\s+-\s+(.+))?$",
    re.IGNORECASE,
)
# Character name: all-caps line (possibly with parenthetical on the same line)
_CHARACTER_RE = re.compile(r"^([A-Z][A-Z\s\-\.\']+?)(\s*\(.*?\))?$")


def _is_slugline(line: str) -> bool:
    return bool(_SLUGLINE_RE.match(line.strip()))


def _parse_slugline(line: str) -> tuple[str, str, str]:
    """Return (setting, location, time_of_day)."""
    m = _SLUGLINE_RE.match(line.strip())
    if not m:
        return ("INT", line.strip(), "DAY")
    setting = m.group(1).replace(".", "").upper()
    location = m.group(2).strip() if m.group(2) else ""
    time_of_day = m.group(3).strip().upper() if m.group(3) else "DAY"
    return setting, location, time_of_day


def _extract_character_mentions(text: str) -> List[str]:
    """Naive heuristic: uppercase contiguous tokens are likely character names."""
    tokens = re.findall(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b", text)
    return list(set(tokens))


# ---------------------------------------------------------------------------
# Fountain Backend
# ---------------------------------------------------------------------------

class FountainBackend:
    """Parse a .fountain file into a list of ParsedScene objects.

    Uses a simple line-oriented state machine rather than a full Fountain
    library so the dependency footprint stays minimal.  Complex edge-cases
    (dual dialogue, centered text, lyrics) are preserved as raw action beats.
    """

    _STATE_ACTION = "action"
    _STATE_DIALOGUE = "dialogue"
    _STATE_PARENTHETICAL = "parenthetical"
    _STATE_CHARACTER = "character"

    def parse(self, text: str) -> List[ParsedScene]:
        scenes: List[ParsedScene] = []
        current_scene: Optional[ParsedScene] = None
        state = self._STATE_ACTION

        pending_character: Optional[str] = None
        pending_parenthetical: Optional[str] = None
        scene_counter = 0

        lines = text.splitlines()

        for i, raw_line in enumerate(lines):
            line = raw_line.rstrip()

            # --- Scene heading ---
            if _is_slugline(line):
                scene_counter += 1
                setting, location, tod = _parse_slugline(line)
                current_scene = ParsedScene(
                    scene_number=str(scene_counter),
                    slug=line.strip(),
                    setting=setting,
                    location=location,
                    time_of_day=tod,
                )
                scenes.append(current_scene)
                state = self._STATE_ACTION
                pending_character = None
                continue

            if current_scene is None:
                # Pre-title content — ignore
                continue

            stripped = line.strip()

            # --- Blank line resets dialogue state ---
            if not stripped:
                if state in (self._STATE_DIALOGUE, self._STATE_CHARACTER, self._STATE_PARENTHETICAL):
                    state = self._STATE_ACTION
                    pending_character = None
                    pending_parenthetical = None
                continue

            # --- Parenthetical inside dialogue block ---
            if state == self._STATE_DIALOGUE and stripped.startswith("(") and stripped.endswith(")"):
                pending_parenthetical = stripped[1:-1]
                state = self._STATE_PARENTHETICAL
                continue

            # --- Dialogue line ---
            if state in (self._STATE_CHARACTER, self._STATE_PARENTHETICAL, self._STATE_DIALOGUE):
                if pending_character:
                    current_scene.dialogue.append(
                        DialogueLine(
                            character=pending_character,
                            parenthetical=pending_parenthetical,
                            text=stripped,
                        )
                    )
                    if pending_character not in current_scene.characters_present:
                        current_scene.characters_present.append(pending_character)
                    pending_parenthetical = None
                    state = self._STATE_DIALOGUE
                continue

            # --- Character cue (all-caps, alone on a line) ---
            char_match = _CHARACTER_RE.match(stripped)
            if (
                char_match
                and stripped == stripped.upper()
                and len(stripped) > 1
                and not _is_slugline(stripped)
            ):
                pending_character = char_match.group(1).strip()
                state = self._STATE_CHARACTER
                continue

            # --- Action paragraph ---
            mentions = _extract_character_mentions(stripped)
            beat = ActionBeat(raw_text=stripped, characters_mentioned=mentions)
            current_scene.action_beats.append(beat)
            state = self._STATE_ACTION

        return scenes


# ---------------------------------------------------------------------------
# FDX (Final Draft XML) Backend
# ---------------------------------------------------------------------------

class FDXBackend:
    """Parse a Final Draft .fdx file into ParsedScene objects."""

    def parse(self, text: str) -> List[ParsedScene]:
        try:
            from lxml import etree  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "lxml is required for FDX parsing.  Install it with: pip install lxml"
            ) from exc

        root = etree.fromstring(text.encode())
        paragraphs = root.findall(".//{http://www.finaldraft.com/products/final-draft}Paragraph")
        if not paragraphs:
            # Try without namespace
            paragraphs = root.findall(".//Paragraph")

        scenes: List[ParsedScene] = []
        current_scene: Optional[ParsedScene] = None
        pending_character: Optional[str] = None
        scene_counter = 0

        for para in paragraphs:
            para_type = para.get("Type", "")
            text_parts = [t.text or "" for t in para.findall(".//{*}Text")] or [
                (para.text or "")
            ]
            raw = " ".join(text_parts).strip()

            if not raw:
                continue

            if para_type == "Scene Heading":
                scene_counter += 1
                setting, location, tod = _parse_slugline(raw)
                current_scene = ParsedScene(
                    scene_number=str(scene_counter),
                    slug=raw,
                    setting=setting,
                    location=location,
                    time_of_day=tod,
                )
                scenes.append(current_scene)
                pending_character = None

            elif para_type == "Action" and current_scene:
                mentions = _extract_character_mentions(raw)
                current_scene.action_beats.append(
                    ActionBeat(raw_text=raw, characters_mentioned=mentions)
                )

            elif para_type == "Character" and current_scene:
                pending_character = raw.upper()
                if pending_character not in current_scene.characters_present:
                    current_scene.characters_present.append(pending_character)

            elif para_type in ("Dialogue", "Parenthetical") and current_scene and pending_character:
                parenthetical = raw if para_type == "Parenthetical" else None
                dialogue_text = raw if para_type == "Dialogue" else ""
                if dialogue_text:
                    current_scene.dialogue.append(
                        DialogueLine(
                            character=pending_character,
                            parenthetical=parenthetical,
                            text=dialogue_text,
                        )
                    )

        return scenes


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------

class ScreenplayParser:
    """Format-detecting screenplay parser.

    Usage::

        parser = ScreenplayParser()
        scenes = parser.parse(Path("episode_02.fountain"))
    """

    def parse(self, path: Path) -> List[ParsedScene]:
        """Ingest a screenplay file and return its scene graph."""
        suffix = path.suffix.lower()
        raw_text = path.read_text(encoding="utf-8", errors="replace")

        if suffix == ".fountain":
            return FountainBackend().parse(raw_text)
        elif suffix in (".fdx", ".xml"):
            return FDXBackend().parse(raw_text)
        else:
            # Attempt Fountain as the most forgiving format
            return FountainBackend().parse(raw_text)
