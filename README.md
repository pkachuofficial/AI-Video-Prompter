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

## Installation

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
