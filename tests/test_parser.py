"""
Tests for the screenplay parser — both Fountain and FDX backends.
"""

import pytest
from avp.parser import ScreenplayParser, FountainBackend, FDXBackend

# ---------------------------------------------------------------------------
# Fountain Backend
# ---------------------------------------------------------------------------

FOUNTAIN_SAMPLE = """
Title: Obsidian Protocol
Author: A. Writer

INT. OBSIDIAN SAFE-HOUSE - NIGHT

The room is dim. A single amber light swings overhead.

VIKTOR enters, scanning the space with practiced calm.

VIKTOR
We've been compromised.

            (beat)

Every cell. Every safe-house.

EXT. ROOFTOP - DAY

Rain hammers the cityscape below.

AGENT
(into earpiece)
Package is secure.
"""

class TestFountainBackend:
    def test_scene_count(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        assert len(scenes) == 2

    def test_first_scene_slug(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        s = scenes[0]
        assert s.setting == "INT"
        assert "SAFE-HOUSE" in s.location
        assert s.time_of_day == "NIGHT"

    def test_second_scene_slug(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        s = scenes[1]
        assert s.setting == "EXT"
        assert s.time_of_day == "DAY"

    def test_action_beats_parsed(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        # "The room is dim…" and "VIKTOR enters…" should be action beats
        assert len(scenes[0].action_beats) >= 1

    def test_dialogue_parsed(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        dialogue = scenes[0].dialogue
        assert any(d.character == "VIKTOR" for d in dialogue)

    def test_character_present(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        assert "VIKTOR" in scenes[0].characters_present

    def test_scene_number_assigned(self):
        scenes = FountainBackend().parse(FOUNTAIN_SAMPLE)
        assert scenes[0].scene_number == "1"
        assert scenes[1].scene_number == "2"


# ---------------------------------------------------------------------------
# ScreenplayParser façade (format detection)
# ---------------------------------------------------------------------------

class TestScreenplayParserFacade:
    def test_fountain_detection(self, tmp_path):
        f = tmp_path / "test.fountain"
        f.write_text(FOUNTAIN_SAMPLE)
        parser = ScreenplayParser()
        scenes = parser.parse(f)
        assert len(scenes) == 2

    def test_unknown_extension_fallback(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(FOUNTAIN_SAMPLE)
        parser = ScreenplayParser()
        scenes = parser.parse(f)
        assert len(scenes) >= 1
