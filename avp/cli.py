"""
avp.cli — Typer command-line interface for the AVP production pipeline.

Commands:
  avp bible add-character   — Register a character in the Production Bible
  avp bible add-wardrobe    — Register a wardrobe state
  avp bible add-scene       — Register a scene context
  avp parse                 — Parse a screenplay file and preview scene graph
  avp compile               — Compile prompts for a shot manifest JSON
  avp run-episode           — Execute the full two-stage pipeline for a manifest
  avp artifacts             — List provenance records for a shot
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from avp.db import (
    CharacterRecord,
    GeneratedArtifact,
    SceneRecord,
    WardrobeRecord,
    get_session,
    init_db,
)
from avp.models import (
    CharacterIdentity,
    SceneContext,
    ShotManifest,
    WardrobeState,
)
from avp.parser import ScreenplayParser

app = typer.Typer(
    name="avp",
    help="AI Video Prompter — Generative Drama Production Pipeline",
    no_args_is_help=True,
)
bible_app = typer.Typer(help="Manage the Production Bible (characters, wardrobes, scenes).")
app.add_typer(bible_app, name="bible")

console = Console()


# ---------------------------------------------------------------------------
# Database initialisation (runs on every command)
# ---------------------------------------------------------------------------

@app.callback()
def _startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# bible add-character
# ---------------------------------------------------------------------------

@bible_app.command("add-character")
def add_character(
    json_path: Path = typer.Argument(..., help="Path to a CharacterIdentity JSON file"),
) -> None:
    """Register a character identity record in the Production Bible."""
    data = json.loads(json_path.read_text())
    char = CharacterIdentity(**data)

    session = get_session()
    try:
        existing = session.get(CharacterRecord, char.character_id)
        if existing:
            console.print(f"[yellow]Character {char.character_id} already exists — updating.[/yellow]")
            for k, v in char.model_dump().items():
                setattr(existing, k, v)
        else:
            record = CharacterRecord(**char.model_dump())
            session.add(record)
        session.commit()
        console.print(f"[green]✓ Character '{char.canonical_name}' registered.[/green]")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# bible add-wardrobe
# ---------------------------------------------------------------------------

@bible_app.command("add-wardrobe")
def add_wardrobe(
    json_path: Path = typer.Argument(..., help="Path to a WardrobeState JSON file"),
) -> None:
    """Register a wardrobe state record in the Production Bible."""
    data = json.loads(json_path.read_text())
    wardrobe = WardrobeState(**data)

    session = get_session()
    try:
        existing = session.get(WardrobeRecord, wardrobe.wardrobe_id)
        if existing:
            console.print(f"[yellow]Wardrobe {wardrobe.wardrobe_id} exists — updating.[/yellow]")
            d = wardrobe.model_dump()
            for k, v in d.items():
                setattr(existing, k, v)
        else:
            d = wardrobe.model_dump()
            session.add(WardrobeRecord(**d))
        session.commit()
        console.print(f"[green]✓ Wardrobe '{wardrobe.wardrobe_id}' registered.[/green]")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# bible add-scene
# ---------------------------------------------------------------------------

@bible_app.command("add-scene")
def add_scene(
    json_path: Path = typer.Argument(..., help="Path to a SceneContext JSON file"),
) -> None:
    """Register a scene context in the Production Bible."""
    data = json.loads(json_path.read_text())
    scene = SceneContext(**data)

    session = get_session()
    try:
        existing = session.get(SceneRecord, scene.scene_id)
        if existing:
            console.print(f"[yellow]Scene {scene.scene_id} exists — updating.[/yellow]")
            d = scene.model_dump()
            for k, v in d.items():
                setattr(existing, k, v)
        else:
            d = scene.model_dump()
            session.add(SceneRecord(**d))
        session.commit()
        console.print(f"[green]✓ Scene '{scene.scene_id}' registered.[/green]")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# parse — screenplay preview
# ---------------------------------------------------------------------------

@app.command()
def parse(
    screenplay: Path = typer.Argument(..., help="Path to .fountain or .fdx screenplay file"),
    max_scenes: int = typer.Option(10, "--max-scenes", "-n", help="Maximum scenes to display"),
) -> None:
    """Parse a screenplay and display its scene graph."""
    parser = ScreenplayParser()
    scenes = parser.parse(screenplay)

    table = Table(title=f"Scene Graph — {screenplay.name}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Slug", style="cyan", min_width=30)
    table.add_column("Setting")
    table.add_column("ToD")
    table.add_column("Characters", style="green")
    table.add_column("Beats", justify="right")
    table.add_column("Dialogue", justify="right")

    for scene in scenes[:max_scenes]:
        table.add_row(
            scene.scene_number or "?",
            scene.slug[:60],
            scene.setting,
            scene.time_of_day,
            ", ".join(scene.characters_present[:3]),
            str(len(scene.action_beats)),
            str(len(scene.dialogue)),
        )

    console.print(table)
    console.print(f"\n[dim]Total scenes parsed: {len(scenes)}[/dim]")


# ---------------------------------------------------------------------------
# compile — batch prompt compilation
# ---------------------------------------------------------------------------

@app.command()
def compile(
    manifest_path: Path = typer.Argument(..., help="Path to ShotManifest JSON file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write compiled manifest to file"),
) -> None:
    """Compile prompt strings for every shot in a ShotManifest JSON."""
    from avp.compiler import PromptCompiler
    from avp.db import CharacterRecord, SceneRecord, WardrobeRecord, get_session

    manifest = ShotManifest(**json.loads(manifest_path.read_text()))

    # Load Production Bible from DB
    session = get_session()
    try:
        char_records = session.query(CharacterRecord).all()
        wardrobe_records = session.query(WardrobeRecord).all()
        scene_records = session.query(SceneRecord).all()
    finally:
        session.close()

    characters = {r.character_id: CharacterIdentity(**r.__dict__) for r in char_records}
    wardrobes = {r.wardrobe_id: WardrobeState(**r.__dict__) for r in wardrobe_records}
    scenes = {r.scene_id: SceneContext(**r.__dict__) for r in scene_records}

    compiler = PromptCompiler(characters, wardrobes, scenes)

    compiled = compiler.compile_manifest(manifest.shots)
    manifest.shots = compiled

    compiled_json = manifest.model_dump_json(indent=2)

    if output:
        output.write_text(compiled_json)
        console.print(f"[green]✓ Compiled manifest written to {output}[/green]")
    else:
        console.print_json(compiled_json)


# ---------------------------------------------------------------------------
# artifacts — provenance log viewer
# ---------------------------------------------------------------------------

@app.command()
def artifacts(
    shot_id: str = typer.Argument(..., help="Shot ID to query"),
) -> None:
    """Display provenance records for a given shot ID."""
    session = get_session()
    try:
        records = (
            session.query(GeneratedArtifact)
            .filter(GeneratedArtifact.shot_id == shot_id)
            .order_by(GeneratedArtifact.created_at)
            .all()
        )
    finally:
        session.close()

    if not records:
        console.print(f"[yellow]No artifacts found for shot '{shot_id}'.[/yellow]")
        raise typer.Exit()

    table = Table(title=f"Provenance Log — {shot_id}", show_lines=True)
    table.add_column("ID", width=4)
    table.add_column("Type")
    table.add_column("Seed")
    table.add_column("Sampler")
    table.add_column("CFG")
    table.add_column("Created At")
    table.add_column("Output Path", style="dim")

    for r in records:
        table.add_row(
            str(r.id),
            r.artifact_type,
            str(r.seed),
            r.sampler or "—",
            str(r.cfg_scale) if r.cfg_scale else "—",
            str(r.created_at)[:19],
            r.output_path,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# run-episode — full pipeline execution
# ---------------------------------------------------------------------------

@app.command("run-episode")
def run_episode(
    manifest_path: Path = typer.Argument(..., help="Path to ShotManifest JSON"),
    stage1_workflow: Path = typer.Option(
        ..., "--s1", help="Path to Stage 1 ComfyUI workflow JSON"
    ),
    stage2_workflow: Path = typer.Option(
        ..., "--s2", help="Path to Stage 2 ComfyUI workflow JSON"
    ),
    output_dir: Path = typer.Option(
        Path("data/renders"), "--output-dir", "-o", help="Root render output directory"
    ),
    comfyui_host: str = typer.Option("127.0.0.1:8188", "--comfyui-host"),
    kling_api_key: Optional[str] = typer.Option(None, envvar="KLING_API_KEY"),
    runway_api_key: Optional[str] = typer.Option(None, envvar="RUNWAY_API_KEY"),
    max_retries: int = typer.Option(3, "--retries"),
) -> None:
    """Execute the full two-stage pipeline for a shot manifest."""
    from avp.db import CharacterRecord, SceneRecord, WardrobeRecord, get_session
    from avp.pipeline import ProductionPipeline

    manifest = ShotManifest(**json.loads(manifest_path.read_text()))

    session = get_session()
    try:
        char_records = session.query(CharacterRecord).all()
        wardrobe_records = session.query(WardrobeRecord).all()
        scene_records = session.query(SceneRecord).all()
    finally:
        session.close()

    characters = {r.character_id: CharacterIdentity(**r.__dict__) for r in char_records}
    wardrobes = {r.wardrobe_id: WardrobeState(**r.__dict__) for r in wardrobe_records}
    scenes = {r.scene_id: SceneContext(**r.__dict__) for r in scene_records}

    pipeline = ProductionPipeline(
        characters=characters,
        wardrobes=wardrobes,
        scenes=scenes,
        stage1_workflow=stage1_workflow,
        stage2_workflow=stage2_workflow,
        output_dir=output_dir,
        comfyui_host=comfyui_host,
        kling_api_key=kling_api_key,
        runway_api_key=runway_api_key,
    )

    completed = pipeline.run_episode(manifest, max_retries=max_retries)
    console.print(f"\n[green]Episode complete. {len(completed)} shots rendered.[/green]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
