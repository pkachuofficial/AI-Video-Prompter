# AI Video Prompter (AVP)

**Automated Prompt Compilation and Multi-Modal Continuity Orchestration for Generative AI Video Production**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Production Bible (DB)                      │
│   CharacterIdentity · WardrobeState · SceneContext              │
└───────────────────┬─────────────────────────────────────────────┘
                    │
          ┌─────────▼──────────┐
          │  ScreenplayParser  │  .fountain / .fdx → ParsedScene[]
          └─────────┬──────────┘
                    │
          ┌─────────▼──────────┐
          │   PromptCompiler   │  C_Optics ⊕ C_Subject ⊕ C_Env ⊕ C_Dyn ⊕ C_Aes
          └─────────┬──────────┘
                    │
        ┌───────────┴─────────────┐
        │                         │
┌───────▼──────┐         ┌────────▼───────┐
│   Stage 1    │         │    Stage 2     │
│  T2I Keyframe│  ──────►│  I2V Animation │
│  (ComfyUI)   │  [gate] │ Kling/Runway/  │
└──────────────┘         │  WAN 2.1 local │
                         └────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Provenance Log (SQLite)   │
                    │  seed · hash · sampler · cfg│
                    └────────────────────────────┘
```

---

## Five-Layer Prompt Hierarchy

$$\text{Prompt}_{\text{final}} = \mathcal{C}_{\text{Optics}} \oplus \mathcal{C}_{\text{Subject}} \oplus \mathcal{C}_{\text{Environment}} \oplus \mathcal{C}_{\text{Dynamics}} \oplus \mathcal{C}_{\text{Aesthetics}}$$

| Layer | Source | Purpose |
|---|---|---|
| `C_Optics` | `ShotPlan.shot_type` + `focal_length` | Lens, framing, camera movement |
| `C_Subject` | `CharacterIdentity` + `WardrobeState` | Immutable biometrics + costume |
| `C_Environment` | `SceneContext` | Lighting, spatial config, colour science |
| `C_Dynamics` | `ShotPlan.action_beat` | Single kinematic action (one beat only) |
| `C_Aesthetics` | Global constant | Film grain, colour science, rendering standard |

---

## Prompt-Centric Cinematic Continuity & Human-Realism Engine

The `avp.continuity` module upgrades AI Video Prompter into a prompt-centric continuity supervisor, spatial director, and human-realism optimizer.

### Core Philosophy
```
PREVIOUS SHOT PROMPT + NEW SHOT PROMPT
                ↓
       CONTINUITY BRIDGE
                ↓
  • Scene Relationship Analysis (CONTINUE / TRANSITION / RESET)
  • Relevance / Reset Analysis (INHERIT / CONDITIONAL / RESET / IRRELEVANT)
  • Contradiction Resolution (The New Prompt is Authoritative)
  • Human Kinematics & Physical Realism (3-4 ft/s traversal, no sliding)
  • Cinematic Geometry & Eyeline Matching (Compass anchors, 180° rule)
  • Dialogue Pacing & Performance (~2.5 wps, micro-reactions)
                ↓
   ONE CLEAN OPTIMIZED GENERATION PROMPT FOR THE NEW SHOT
```

- **Prompt-Centric**: No heavy databases, complex episode state graphs, or vector stores. The prompts themselves are the primary source of truth.
- **Authoritative Target**: The new prompt always wins when it introduces changes. The previous prompt provides temporary contextual baseline.
- **Three Modes**:
  - `CONTINUE`: Same physical room/situation. Inherits wardrobe, geometry, lighting, spatial anchors.
  - `TRANSITION`: Same sequence, new location or setup. Resets room geometry and camera; preserves identity, emotional progression, and carried objects.
  - `RESET`: Genuine scene jump or temporal leap. Resets room, camera, and props. Retains identity if character reappears.

---

### Demonstrated Production Scenarios

#### 1. Same-Scene Continuation (`CONTINUE`)
* **Previous Shot**: `Evelyn stands screen-left by the walnut desk in the dim study, clutching an ivory envelope. Faint rain hits the North bay window. Tension in her shoulders.`
* **New Shot**: `Evelyn opens the envelope and reads the letter inside.`
* **Continuity Mode**: `CONTINUE`
* **Risks Flagged**:
  * ⚠ Missing temporal beats for opening envelope
  * ⚠ Risk of prop teleportation if hands are not anchored to the ivory envelope
* **Corrections Applied**:
  * ✓ Inherited study environment, rain ambience, and North bay window
  * ✓ Structured action into 3 temporal beats (lift flap, draw letter, eyeline drops to text)
* **Final Optimized Generation Prompt**:
  ```text
  [SHOT INTENT: Intimate continuation of letter discovery]
  [SUBJECT + IDENTITY: Evelyn, early 20s, dark brown hair in low bun, charcoal knit sweater, locked identity]
  [ENVIRONMENT: Dim private study, warm desk lamp, rain streaks on North bay window, mahogany desk]
  [SPATIAL GEOMETRY: Screen-left by desk, camera on 50mm medium close-up at eye level]
  [ACTION + TEMPORAL BEATS: 0-2s: Evelyn slips her right thumb beneath the ivory envelope seal. 2-4s: Extracts the folded parchment with careful finger articulation. 4-6s: Unfolds paper; gaze shifts downward, pupil contraction.]
  [EMOTIONAL PERFORMANCE: Subdued apprehension; subtle throat swallow; lips closed, shallow chest breathing.]
  [CAMERA: Subtle push-in 50mm, f/2.8, shallow depth of field, steady locked-off axis.]
  [CONTINUITY LOCK: Retains charcoal knit sweater, walnut desk, and North window rain audio from previous shot.]
  [PHYSICAL REALISM: Weight of hands grounded on paper; natural knuckle bending; zero finger gliding.]
  ```

#### 2. Scene Transition (`TRANSITION`)
* **Previous Shot**: `Evelyn is in the dim study. She sets the letter on the desk and looks toward the corridor door.`
* **New Shot**: `Evelyn walks rapidly down the marble mansion corridor, now determined, clutching her keys.`
* **Continuity Mode**: `TRANSITION`
* **Risks Flagged**:
  * ⚠ Previous study furniture and North window may leak into hallway
  * ⚠ Rapid walking risks sliding feet without heel-to-toe kinematic constraints
* **Corrections Applied**:
  * ✓ Hard reset applied to study desk, room geometry, and window
  * ✓ Inherited Evelyn identity, charcoal sweater, and emotional momentum
  * ✓ Added kinetic cadence: firm footfall at ~4 ft/sec with realistic weight transfer
* **Final Optimized Generation Prompt**:
  ```text
  [SHOT INTENT: Transition to purposeful traversal through mansion corridor]
  [SUBJECT + IDENTITY: Evelyn, locked biometric reference, charcoal knit sweater, dark trousers]
  [ENVIRONMENT: Grand neoclassical mansion hallway, checkered marble floor, tall fluted pilasters, cool morning daylight from East arches]
  [SPATIAL GEOMETRY: Camera leading subject backward from South corridor heading, keeping Evelyn center-frame]
  [ACTION + TEMPORAL BEATS: 0-3s: Strides forward at measured 4 ft/s cadence with firm heel-to-toe ground contact. 3-6s: Her right hand grasps brass keychain, keys resting firmly in palm without jiggling.]
  [EMOTIONAL PERFORMANCE: Transition from earlier shock into rigid, controlled determination; jaw set, forward-fixed gaze.]
  [CAMERA: Steadicam tracking backward at eye level, 35mm lens, dynamic leading perspective.]
  [CONTINUITY LOCK: Inherited wardrobe and character state; study geometry and props fully cleared.]
  [PHYSICAL REALISM: True gravitational weight transfer per step; fabric folds sway naturally with stride momentum.]
  ```

#### 3. Completely New Scene (`RESET`)
* **Previous Shot**: `Evelyn collapses onto the lobby couch at 2:00 AM, exhausted after the interrogation.`
* **New Shot**: `Next morning. INT. MODERN GLASS BOARDROOM - DAY. Evelyn stands before the executive committee in a tailored navy suit.`
* **Continuity Mode**: `RESET`
* **Risks Flagged**:
  * ⚠ Previous night lighting, exhaustion posture, and casual clothing must not bleed through
  * ⚠ Screenplay time jump (+8 hours) mandates complete environmental wipe
* **Corrections Applied**:
  * ✓ Complete environmental, lighting, and wardrobe reset
  * ✓ Preserved Evelyn facial biometrics and scar coordinates while updating to formal posture
* **Final Optimized Generation Prompt**:
  ```text
  [SHOT INTENT: Clean reset to high-stakes morning corporate presentation]
  [SUBJECT + IDENTITY: Evelyn, canonical facial structure, styled corporate hair chignon, tailored navy blue wool blazer, white crisp blouse]
  [ENVIRONMENT: High-rise boardroom, floor-to-ceiling glass wall overlooking morning city skyline, pale diffused 5600K daylight, polished conference table]
  [SPATIAL GEOMETRY: Standing at head of boardroom table (North), facing seated executives (South)]
  [ACTION + TEMPORAL BEATS: 0-2s: Stands erect behind podium, hands resting flat on lectern surface. 2-5s: Delivers presentation with subtle single-hand gesture. 5-6s: Re-anchors hand to podium.]
  [EMOTIONAL PERFORMANCE: Composed, guarded authority; steady gaze sweeping across table; controlled vocal projection.]
  [CAMERA: Wide medium 35mm shot, pristine architectural symmetry, slow dolly left-to-right.]
  [CONTINUITY LOCK: All previous lobby assets, couch, and night lighting completely reset.]
  ```

#### 4. Dialogue-Heavy Scene (`PACING & DELIVERY AUDIT`)
* **Previous Shot**: `Viktor glares across the table at Julian in silence.`
* **New Shot**: `Viktor delivers a furious monologue: "You thought you could bury this contract, deceive the board, and walk away clean with sixty million dollars while our families took the fall!" (26 words, 4.0-second shot).`
* **Continuity Mode**: `CONTINUE`
* **Risks Flagged**:
  * ⚠ Severe dialogue pacing conflict: 26 words in 4.0s = 6.5 words/sec (far exceeds human maximum of ~2.5 wps)
  * ⚠ Risk of unnatural hyper-speed lip sync and lack of breath support
* **Corrections Applied**:
  * ✓ Dialogue structured into punchy key clause with natural breathing pause
  * ✓ Added physical delivery constraints: lip articulation, diaphragmatic breath before onset
* **Final Optimized Generation Prompt**:
  ```text
  [SHOT INTENT: High-tension dramatic confrontation line delivery]
  [SUBJECT + IDENTITY: Viktor, early 40s, sharp jawline, slate-gray wool suit, locked facial structure]
  [ENVIRONMENT: Dim mahogany dining room, low-hung tungsten pendant over dining table, heavy background bokeh]
  [SPATIAL GEOMETRY: Seated screen-right, leaning forward 15 degrees toward screen-left across table]
  [DIALOGUE + DELIVERY: "You thought you could bury this contract and walk away clean?" Spoken with cold, measured venom; vocal cadence timed at 2.3 words/sec.]
  [ACTION + TEMPORAL BEATS: 0-1.5s: Inhales sharply through nose; shoulders tense. 1.5-4.5s: Speaks line with tight lip articulation, teeth visible on consonants. 4.5-6s: Closes lips into hard line, holding unbroken eye contact.]
  [CAMERA: Over-the-shoulder dirty single favoring Viktor, 85mm portrait lens, f/2.0, subtle handheld tension.]
  [CONTINUITY LOCK: Eyeline matches previous shot screen-left vector; slate suit maintained.]
  ```

#### 5. Human-Motion-Heavy Scene (`KINEMATICS & PHYSICS`)
* **Previous Shot**: `Marcus sits tied to a wooden chair in the abandoned warehouse.`
* **New Shot**: `Marcus breaks free, sprints across the warehouse floor, jumps over the wooden crate, and kicks open the metal exit door.`
* **Continuity Mode**: `CONTINUE`
* **Risks Flagged**:
  * ⚠ Over-packed action density: four major physical actions crammed into a single shot
  * ⚠ Unrealistic acceleration risk: sitting to full sprint without kinetic weight shift
  * ⚠ Skating/sliding feet artifact common in diffusion video models
* **Corrections Applied**:
  * ✓ Single primary subject action isolated for maximum visual realism: the crate vault and sprint
  * ✓ Enforced physical kinematics: push-off foot planted, gravitational drop, and shoe traction
* **Final Optimized Generation Prompt**:
  ```text
  [SHOT INTENT: Kinetic parkour vault and recovery run in industrial space]
  [SUBJECT + IDENTITY: Marcus, mid-30s, athletic build, distressed utility jacket, dark denim trousers]
  [ENVIRONMENT: Industrial warehouse, cracked concrete floor with fine dust, shafts of dusty rim light]
  [SPATIAL GEOMETRY: Traversal along East axis toward distant red exit door; low-angle camera tracking profile]
  [ACTION + TEMPORAL BEATS: 0-2s: Marcus charges into frame, plants his left palm firmly on top of a 3-foot wooden crate. 2-3.5s: Vaults legs through with hips clearing edge, landing with heavy bilateral foot plant on dusty concrete. 3.5-6s: Absorbs impact with knee flexion and accelerates forward in low sprint.]
  [PHYSICS & KINEMATICS SAFEGUARDS: Visible dust puff upon foot contact; real downward weight compression on landing; zero gliding or floating feet; jacket fabric flaps with kinetic momentum.]
  [CAMERA: Fast dynamic dolly tracking alongside subject at waist height, 28mm wide lens, shutter angle 90° for crisp action cadence.]
  ```

#### 6. Geometry-Heavy Scene (`SPATIAL ANCHORS & EYELINE`)
* **Previous Shot**: `Camera is positioned directly behind Viktor's shoulder facing Sophia who is standing by the fireplace (North wall).`
* **New Shot**: `Close-up of Viktor's face as he frowns, with the camera still behind his shoulder.`
* **Continuity Mode**: `CONTINUE`
* **Risks Flagged**:
  * 🔴 CRITICAL CAMERA GEOMETRY CONTRADICTION: A camera positioned behind Viktor cannot capture a frontal close-up of Viktor's face
  * ⚠ Eyeline match risk: Sophia is North; Viktor must look South-Southwest to match Sophia's eyeline
* **Corrections Applied**:
  * ✓ Camera perspective corrected: reverse OTS angle placed over Sophia's shoulder looking back at Viktor
  * ✓ Locked spatial anchors: fireplace established on North wall; Viktor facing North-Northeast toward Sophia
* **Final Optimized Generation Prompt**:
  ```text
  [SHOT INTENT: Reverse-angle close-up capturing Viktor's reaction, resolving camera contradiction]
  [SUBJECT + IDENTITY: Viktor, slate-gray suit, canonical facial tokens, sharp furrowed brow]
  [ENVIRONMENT: Luxury penthouse living room, fireplace glow out of frame screen-right, dark moody ambient lighting]
  [SPATIAL GEOMETRY & CAMERA: Reverse over-the-shoulder angle positioned over Sophia's out-of-focus right shoulder (screen-left foreground), looking directly toward Viktor's front 3/4 face profile (screen-right).]
  [ACTION + TEMPORAL BEATS: 0-2s: Viktor maintains rigid forward eyeline toward Sophia. 2-4s: His brow knits deeper, jaw clenches once. 4-6s: Slow exhalation through slightly parted lips, eyes narrowing slightly.]
  [EYELINE & 180° RULE LOCK: Eyeline locked to upper screen-left vector; perfectly matches reverse coverage of Sophia.]
  [PHYSICAL REALISM: Natural micro-expressions in deltoid and neck muscles; warm amber firelight rimming anatomical left cheekbone.]
  ```

---

### CLI Usage

```bash
# Analyze continuity between two shot prompts and print optimized output
avp continuity optimize \
    --prev "Evelyn stands screen-left by the walnut desk in the dim study, clutching an ivory envelope." \
    --new "Evelyn walks down the hallway determined." \
    --duration 5.0

# Include full internal technical analysis breakdown
avp continuity optimize \
    --prev "Viktor glares across the table." \
    --new "Viktor speaks: 'I know the truth.'" \
    --details
```

---

```bash
# Requires Python 3.10+
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Register Production Bible entries

```bash
avp bible add-character data/bibles/CHAR_VIKTOR.json
avp bible add-wardrobe  data/wardrobes/WARDROBE_VIKTOR_TACTICAL_01.json
avp bible add-scene     data/scenes/S01E01_SCN_007.json
```

### 2. Parse and preview a screenplay

```bash
avp parse data/obsidian_protocol_ep01.fountain
```

### 3. Compile prompts for a shot manifest

```bash
avp compile data/shots/S01E01_manifest.json --output data/shots/S01E01_compiled.json
```

### 4. Run the full two-stage episode pipeline

```bash
avp run-episode data/shots/S01E01_manifest.json \
    --s1 workflows/stage1_flux.json \
    --s2 workflows/stage2_wan21.json \
    --output-dir data/renders/S01E01
```

### 5. Inspect provenance for a specific shot

```bash
avp artifacts S01E01_SCN007_SH002
```

---

## Project Structure

```
ai-video-prompter/
├── avp/
│   ├── models/          # Pydantic schemas — CharacterIdentity, WardrobeState, SceneContext, ShotPlan
│   ├── db/              # SQLAlchemy ORM — Production Bible + provenance log
│   ├── parser/          # Screenplay ingestion — Fountain + FDX backends
│   ├── compiler/        # Deterministic five-layer prompt compiler
│   ├── execution/       # ComfyUI bridge + Kling/Runway API dispatchers
│   ├── pipeline/        # Two-stage orchestrator with human gate
│   └── cli.py           # Typer CLI (avp command)
├── data/
│   ├── bibles/          # CharacterIdentity JSON files
│   ├── wardrobes/       # WardrobeState JSON files
│   ├── scenes/          # SceneContext JSON files
│   ├── shots/           # ShotManifest JSON files
│   └── embeddings/      # InsightFace .npy tensors for PuLID / FaceID
├── workflows/           # ComfyUI API JSON base graphs (T2I + I2V)
├── tests/               # pytest suite
└── pyproject.toml
```

---

## Conditioning Hierarchy Summary

| Mechanism | Layer | Invariance |
|---|---|---|
| LoRA trigger token | `C_Subject` (highest priority) | High across diverse scenes |
| PuLID / FaceID embedding | Stage 1 ComfyUI node | High for facial geometry |
| IP-Adapter costume ref | Stage 1 ComfyUI node | High for fabric / texture |
| I2V Frame 0 anchoring | Stage 2 keyframe injection | Absolute at generation onset |
| Dual-keyframe (imageTail) | Stage 2 start + end frame | Camera interpolation locked |
| Flux Kontext inpainting | Fallback inpaint pass | Surgical facial re-lock |

---

## Operational Governance Rules

1. **Constants vs. Variables** — Biometric tokens live in the Production Bible only. Per-shot prompts may only modify camera angle, lighting variation, expression, and action beat.
2. **Provenance Logging** — Every artifact written to disk has a corresponding `GeneratedArtifact` record (seed, checkpoint hash, sampler, CFG, output path).
3. **No Unattended T2V** — The human approval gate between Stage 1 and Stage 2 is mandatory. Skipping it compounds errors exponentially.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Override default SQLite path (e.g. `postgresql://...`) |
| `KLING_API_KEY` | Kling cloud API authentication |
| `RUNWAY_API_KEY` | Runway Gen-4 API authentication |
