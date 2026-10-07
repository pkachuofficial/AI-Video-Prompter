"""
Tests for the Prompt-Centric Cinematic Continuity and Human-Realism Engine.

Covers all 15 acceptance scenarios specified in Section 51:
  1. SAME ROOM (Inherit geometry)
  2. NEW ROOM (Inherit identity, reset surveillance room)
  3. NEW DAY (Temporal leap, reset lighting)
  4. WARDROBE CHANGE (New prompt wins)
  5. PROP TRANSFER (Object leaves hand)
  6. CAMERA CONTRADICTION (Flag & correct)
  7. DIALOGUE (Timing audit for excessive speech)
  8. LISTENING (Mouth closed, subtle listening reaction)
  9. EMOTION (Progression shock -> determination)
  10. WALKING (Foot contact & weight transfer)
  11. TWO CHARACTERS (Speaker & eyeline)
  12. SCREEN DIRECTION (Direction preserved)
  13. MONITOR / VIDEO (Single physical human figure)
  14. FLASHBACK (Reset present-day environment)
  15. COMPLETELY NEW SCENE (Discard old room details)
"""

import pytest
from avp.continuity import ContinuityBridge, ContinuityMode


@pytest.fixture
def bridge():
    return ContinuityBridge()


# ---------------------------------------------------------------------------
# TEST 1 — SAME ROOM
# ---------------------------------------------------------------------------
def test_01_same_room(bridge):
    """Previous and new prompts continue in same room -> room geometry inherited."""
    prev = "Evelyn is standing in a surveillance room looking at monitors."
    new = "Evelyn walks toward the monitor wall and touches one of the screens."

    report = bridge.analyze_and_optimize(prev, new)

    assert report.mode == ContinuityMode.CONTINUE
    assert any("Same room geometry" in item or "geometry and spatial anchors preserved" in item for item in report.continuity_items)
    assert "SPATIAL GEOMETRY" in report.final_prompt
    assert "monitor wall" in report.final_prompt or "room geometry" in report.final_prompt


# ---------------------------------------------------------------------------
# TEST 2 — NEW ROOM
# ---------------------------------------------------------------------------
def test_02_new_room(bridge):
    """Previous surveillance room -> new hallway. Character identity inherited; surveillance room reset."""
    prev = "Evelyn is in a dark surveillance room wearing an ivory blouse. Twelve monitors glow behind her."
    new = "Evelyn leaves the surveillance room and enters the mansion hallway, reaching for the door handle."

    report = bridge.analyze_and_optimize(prev, new)

    assert report.mode == ContinuityMode.TRANSITION
    assert any("Evelyn" in item for item in report.continuity_items)
    assert any("Location changed" in item or "environment and camera geometry reset" in item for item in report.continuity_items)
    assert "mansion hallway" in report.final_prompt.lower()
    # Surveillance room geometry must be explicitly reset
    assert "reset" in report.final_prompt.lower() or "not visible" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 3 — NEW DAY
# ---------------------------------------------------------------------------
def test_03_new_day(bridge):
    """Night scene -> next morning. Character identity may continue; lighting and time reset."""
    prev = "Evelyn stands on the balcony at night in a safehouse overlooking the city."
    new = "The next morning, Evelyn sits at an outdoor cafe in Paris."

    report = bridge.analyze_and_optimize(prev, new)

    assert report.mode == ContinuityMode.RESET
    assert any("Evelyn" in item for item in report.continuity_items)
    assert any("new scene" in item.lower() or "reset" in item.lower() for item in report.continuity_items)
    assert "outdoor cafe" in report.final_prompt.lower()
    # Night lighting must not leak into morning scene
    assert "night" not in report.final_prompt.lower() or "reset" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 4 — WARDROBE CHANGE
# ---------------------------------------------------------------------------
def test_04_wardrobe_change(bridge):
    """Previous black jacket -> new prompt explicitly says white shirt. White shirt wins."""
    prev = "Viktor wears a black leather jacket and combat boots."
    new = "Viktor has changed into a crisp white linen shirt and dark trousers."

    report = bridge.analyze_and_optimize(prev, new)

    # New prompt wins
    assert "white linen shirt" in report.final_prompt.lower() or "white" in report.final_prompt.lower()
    assert any("Wardrobe" in item for item in report.continuity_items or report.corrections)


# ---------------------------------------------------------------------------
# TEST 5 — PROP TRANSFER
# ---------------------------------------------------------------------------
def test_05_prop_transfer(bridge):
    """Character holds phone -> puts phone on table. Phone leaves hand."""
    prev = "Evelyn holds a phone in her right hand."
    new = "Evelyn places the phone down on the table and folds her hands."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("phone" in c.lower() for c in report.corrections)
    # The action specifies phone on table, not in hand
    assert "places the phone" in report.final_prompt.lower() or "table" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 6 — CAMERA CONTRADICTION
# ---------------------------------------------------------------------------
def test_06_camera_contradiction(bridge):
    """'Camera behind character' + 'frontal face' -> flag contradiction and correct it."""
    prev = "Viktor stands in the doorway."
    new = "The camera is positioned directly behind Viktor's shoulder while framing an extreme frontal close-up of Viktor's face and eyes."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("Camera" in r and ("conflict" in r.lower() or "behind" in r.lower()) for r in report.risks)
    assert any("Camera corrected" in c for c in report.corrections)


# ---------------------------------------------------------------------------
# TEST 7 — DIALOGUE
# ---------------------------------------------------------------------------
def test_07_dialogue(bridge):
    """8-second shot with excessive dialogue (35+ words) -> flag timing problem and suggest shorter/split."""
    prev = "Viktor looks at Marcus."
    excessive_speech = (
        'Marcus says: "I told you three days ago that we could never trust the council after what happened in Prague, '
        'and if you think for a single second that walking in there today will solve anything, you are lying to yourself '
        'and risking everyone who ever fought alongside us."'
    )
    new = f"Marcus stares at Viktor. {excessive_speech}"

    report = bridge.analyze_and_optimize(prev, new, duration_sec=8.0)

    assert any("exceeds shot duration" in r.lower() or "dialogue" in r.lower() for r in report.risks)
    assert any("shorten" in r.lower() or "split" in r.lower() for r in [risk for risk in report.risks])


# ---------------------------------------------------------------------------
# TEST 8 — LISTENING
# ---------------------------------------------------------------------------
def test_08_listening(bridge):
    """Character listens to another character -> no speaking-mouth animation; subtle listening behavior."""
    prev = "Marcus begins to explain the situation."
    new = "Evelyn listens silently as Marcus speaks off-screen."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("listening" in c.lower() for c in report.corrections)
    assert "PERFORMANCE" in report.final_prompt
    assert "mouth remains closed" in report.final_prompt.lower() or "zero speaking lip animation" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 9 — EMOTION
# ---------------------------------------------------------------------------
def test_09_emotion(bridge):
    """Character goes from shock -> controlled determination. Gradual emotional progression."""
    prev = "Evelyn discovers the opened safe."
    new = "Evelyn reacts in shock and shifts into controlled determination."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("Emotional progression" in c or "shock evolves into controlled determination" in c for c in report.corrections)
    assert "EMOTIONAL PERFORMANCE" in report.final_prompt
    assert "shock" in report.final_prompt.lower() and "determination" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 10 — WALKING
# ---------------------------------------------------------------------------
def test_10_walking(bridge):
    """Character walks across room -> realistic steps, foot contact and weight transfer."""
    prev = "Viktor stands near the wall."
    new = "Viktor walks across the concrete warehouse floor toward the exit."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("foot contact" in c.lower() or "locomotion" in c.lower() for c in report.corrections)
    assert "KINEMATICS" in report.final_prompt
    assert "foot contact" in report.final_prompt.lower()
    assert "weight transfer" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 11 — TWO CHARACTERS
# ---------------------------------------------------------------------------
def test_11_two_characters(bridge):
    """Two people speak -> correct speaker attribution and eyelines."""
    prev = "Marcus and Evelyn enter the briefing room."
    new = 'Marcus speaks to Evelyn across the table: "We leave at midnight." Evelyn stares at him.'

    report = bridge.analyze_and_optimize(prev, new)

    assert any("Eyeline" in c for c in report.corrections)
    assert "DIALOGUE + DELIVERY" in report.final_prompt
    assert 'Marcus speaks: "We leave at midnight."' in report.final_prompt or "midnight" in report.final_prompt


# ---------------------------------------------------------------------------
# TEST 12 — SCREEN DIRECTION
# ---------------------------------------------------------------------------
def test_12_screen_direction(bridge):
    """Character exits frame left. Next shot continues movement -> direction preserved."""
    prev = "Evelyn walks from screen-right and exits frame left into darkness."
    new = "Evelyn continues walking down the corridor toward the glowing exit."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("directional continuity" in c.lower() for c in report.corrections)


# ---------------------------------------------------------------------------
# TEST 13 — MONITOR / VIDEO
# ---------------------------------------------------------------------------
def test_13_monitor_video(bridge):
    """Physical character + recording of same character on monitor -> only one physical character."""
    prev = "Evelyn enters the security room."
    new = "Evelyn stands inside the surveillance room watching recorded video playback of Evelyn running outside."

    report = bridge.analyze_and_optimize(prev, new)

    assert any("character_duplication" in r.lower() or "duplicate" in r.lower() for r in report.risks + report.corrections)
    assert "extra physical people" in report.negative_prompt.lower() or "duplicate character" in report.negative_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 14 — FLASHBACK
# ---------------------------------------------------------------------------
def test_14_flashback(bridge):
    """Present-day character -> flashback. Present-day environment/wardrobe does not contaminate."""
    prev = "Present-day Marcus sits in a modern hospital room in a black suit."
    new = "Flashback: Ten years earlier, young Marcus trains in a boxing gym in grey sweatpants."

    report = bridge.analyze_and_optimize(prev, new)

    assert report.mode == ContinuityMode.RESET
    assert "boxing gym" in report.final_prompt.lower()
    # Hospital room must not contaminate the gym scene
    assert "hospital" not in report.final_prompt.lower() or "reset" in report.final_prompt.lower()


# ---------------------------------------------------------------------------
# TEST 15 — COMPLETELY NEW SCENE
# ---------------------------------------------------------------------------
def test_15_completely_new_scene(bridge):
    """Previous scene is a bedroom. New scene is an outdoor railway station 3 days later -> bedroom details discarded."""
    prev = "Evelyn lies in her bedroom with an owl shelf and bedside lamp."
    new = "Three days later, Evelyn stands at an outdoor railway station in rainy London."

    report = bridge.analyze_and_optimize(prev, new)

    assert report.mode == ContinuityMode.RESET
    assert any("Evelyn" in item for item in report.continuity_items)
    assert "railway station" in report.final_prompt.lower()
    # Owl shelf and bedroom must not contaminate the railway station
    assert "owl" not in report.final_prompt.lower()
