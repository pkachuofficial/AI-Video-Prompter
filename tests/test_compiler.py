"""
Tests for the PromptCompiler — five-layer assembly, shot-type weighting,
negative prompt composition, and Production Bible isolation.
"""

import pytest
from avp.compiler import PromptCompiler, GLOBAL_AESTHETIC_NEGATIVE
from avp.models import CharacterIdentity, WardrobeState, SceneContext, ShotPlan

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CHARACTER = CharacterIdentity(
    character_id="CHAR_VIKTOR",
    canonical_name="Viktor Kazan",
    age_range="late 30s",
    ethnicity="Eastern European Caucasian male",
    facial_features="strong square jaw, deep-set dark brown eyes, prominent cheekbones, thin scar along left jawline",
    hair_specification="short dark brown hair, no facial hair",
    body_morphology="tall athletic build, 6 foot 1 inch, broad shoulders",
    canonical_negative_prompt="beard, mustache, blonde hair, blue eyes, makeup",
    default_lora_trigger=None,
)

WARDROBE = WardrobeState(
    wardrobe_id="WARDROBE_VIKTOR_TACTICAL_01",
    character_id="CHAR_VIKTOR",
    garment_layers="black fitted tactical turtleneck, dark charcoal trousers, matte black combat boots",
    distress_level="battle-worn",
    accessories=["matte black tactical watch", "slim holster"],
)

SCENE = SceneContext(
    scene_id="S01E01_SCN_007",
    episode_id="S01E01",
    location_name="Obsidian Safe-House",
    setting="INT",
    time_of_day="NIGHT",
    spatial_configuration="low-ceilinged industrial safe-house, exposed concrete walls",
    lighting_setup="harsh single practical overhead key light at 2800K amber, deep shadow fill 5:1",
    color_palette_tokens=["desaturated teal", "amber practicals", "deep crushed blacks"],
    environmental_anchors=["tactical map on table", "hanging amber light"],
    global_style_negative="sunlight, bright daylight, warm colour grading",
)


@pytest.fixture
def compiler():
    return PromptCompiler(
        characters={"CHAR_VIKTOR": CHARACTER},
        wardrobes={"WARDROBE_VIKTOR_TACTICAL_01": WARDROBE},
        scenes={"S01E01_SCN_007": SCENE},
    )


def make_shot(shot_type: str, camera_movement: str = "Static") -> ShotPlan:
    return ShotPlan(
        shot_id=f"TEST_{shot_type}",
        scene_id="S01E01_SCN_007",
        primary_character_id="CHAR_VIKTOR",
        wardrobe_id="WARDROBE_VIKTOR_TACTICAL_01",
        shot_type=shot_type,
        camera_movement=camera_movement,
        action_beat="Viktor stares at the map",
    )


# ---------------------------------------------------------------------------
# Core compilation
# ---------------------------------------------------------------------------

class TestPromptCompiler:
    def test_compiles_positive_prompt(self, compiler):
        shot = compiler.compile(make_shot("MCU"))
        assert shot.compiled_positive_prompt is not None
        assert len(shot.compiled_positive_prompt) > 50

    def test_compiles_negative_prompt(self, compiler):
        shot = compiler.compile(make_shot("MCU"))
        assert shot.compiled_negative_prompt is not None

    def test_biometric_tokens_present(self, compiler):
        shot = compiler.compile(make_shot("CU"))
        prompt = shot.compiled_positive_prompt or ""
        assert "square jaw" in prompt
        assert "dark brown eyes" in prompt

    def test_wardrobe_tokens_present(self, compiler):
        shot = compiler.compile(make_shot("MS"))
        prompt = shot.compiled_positive_prompt or ""
        assert "turtleneck" in prompt

    def test_distress_level_injected(self, compiler):
        shot = compiler.compile(make_shot("MS"))
        prompt = shot.compiled_positive_prompt or ""
        assert "battle-worn" in prompt

    def test_accessories_injected(self, compiler):
        shot = compiler.compile(make_shot("MS"))
        prompt = shot.compiled_positive_prompt or ""
        assert "holster" in prompt

    def test_scene_color_tokens_present(self, compiler):
        shot = compiler.compile(make_shot("WS"))
        prompt = shot.compiled_positive_prompt or ""
        assert "desaturated teal" in prompt

    def test_action_beat_present(self, compiler):
        shot = compiler.compile(make_shot("MCU"))
        prompt = shot.compiled_positive_prompt or ""
        assert "tactical map" in prompt or "stares" in prompt

    def test_global_negative_present(self, compiler):
        shot = compiler.compile(make_shot("MCU"))
        neg = shot.compiled_negative_prompt or ""
        assert "cgi" in neg
        assert "deformed fingers" in neg

    def test_character_specific_negative_present(self, compiler):
        shot = compiler.compile(make_shot("MCU"))
        neg = shot.compiled_negative_prompt or ""
        assert "beard" in neg
        assert "mustache" in neg

    def test_scene_negative_present(self, compiler):
        shot = compiler.compile(make_shot("MCU"))
        neg = shot.compiled_negative_prompt or ""
        assert "sunlight" in neg

    # ------------------------------------------------------------------
    # Shot-type attention weighting
    # ------------------------------------------------------------------

    def test_ecu_contains_facial_detail_tokens(self, compiler):
        shot = compiler.compile(make_shot("ECU"))
        prompt = shot.compiled_positive_prompt or ""
        assert "extreme close-up" in prompt
        assert "iris striations" in prompt or "macro facial detail" in prompt

    def test_ws_contains_environment_tokens(self, compiler):
        shot = compiler.compile(make_shot("WS"))
        prompt = shot.compiled_positive_prompt or ""
        assert "concrete walls" in prompt or "safe-house" in prompt

    def test_ws_optics_prefix_wide(self, compiler):
        shot = compiler.compile(make_shot("WS"))
        prompt = shot.compiled_positive_prompt or ""
        assert "wide" in prompt.lower() or "establishing" in prompt.lower()

    def test_lora_trigger_injected_when_set(self, compiler):
        char_with_lora = CHARACTER.model_copy(
            update={"default_lora_trigger": "viktor_lora_v2"}
        )
        c = PromptCompiler(
            characters={"CHAR_VIKTOR": char_with_lora},
            wardrobes={"WARDROBE_VIKTOR_TACTICAL_01": WARDROBE},
            scenes={"S01E01_SCN_007": SCENE},
        )
        shot = c.compile(make_shot("MCU"))
        assert "viktor_lora_v2" in (shot.compiled_positive_prompt or "")

    def test_missing_character_raises(self, compiler):
        shot = make_shot("MCU")
        shot.primary_character_id = "CHAR_NONEXISTENT"
        with pytest.raises(KeyError):
            compiler.compile(shot)

    def test_compile_manifest(self, compiler):
        shots = [make_shot(t) for t in ("WS", "MCU", "ECU")]
        compiled = compiler.compile_manifest(shots)
        assert all(s.compiled_positive_prompt for s in compiled)
        assert len(compiled) == 3
