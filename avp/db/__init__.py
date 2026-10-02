"""
avp.db — SQLAlchemy ORM layer + provenance logging.

Stores:
  • CharacterIdentity, WardrobeState, SceneContext (Production Bible)
  • ShotPlan records with their compiled prompts
  • GeneratedArtifact provenance log (seed, hash, sampler, CFG, paths)

Default backend: SQLite (file-based, zero-config).
Override DATABASE_URL environment variable for PostgreSQL in production.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# ---------------------------------------------------------------------------
# Engine bootstrap
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "production.db"
)
_DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.abspath(_DEFAULT_DB_PATH)}"
)

_engine = create_engine(_DATABASE_URL, echo=False, future=True)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class CharacterRecord(Base):
    __tablename__ = "characters"

    character_id: Mapped[str] = mapped_column(String, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    age_range: Mapped[str] = mapped_column(String, nullable=False)
    ethnicity: Mapped[str] = mapped_column(String, nullable=False)
    facial_features: Mapped[str] = mapped_column(Text, nullable=False)
    hair_specification: Mapped[str] = mapped_column(Text, nullable=False)
    body_morphology: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_negative_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    default_lora_trigger: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    face_embedding_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class WardrobeRecord(Base):
    __tablename__ = "wardrobes"

    wardrobe_id: Mapped[str] = mapped_column(String, primary_key=True)
    character_id: Mapped[str] = mapped_column(String, nullable=False)
    garment_layers: Mapped[str] = mapped_column(Text, nullable=False)
    distress_level: Mapped[str] = mapped_column(String, default="pristine")
    accessories: Mapped[list] = mapped_column(JSON, default=list)
    ip_adapter_reference_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class SceneRecord(Base):
    __tablename__ = "scenes"

    scene_id: Mapped[str] = mapped_column(String, primary_key=True)
    episode_id: Mapped[str] = mapped_column(String, nullable=False)
    location_name: Mapped[str] = mapped_column(String, nullable=False)
    setting: Mapped[str] = mapped_column(String, nullable=False)
    time_of_day: Mapped[str] = mapped_column(String, nullable=False)
    spatial_configuration: Mapped[str] = mapped_column(Text, nullable=False)
    lighting_setup: Mapped[str] = mapped_column(Text, nullable=False)
    color_palette_tokens: Mapped[list] = mapped_column(JSON, default=list)
    environmental_anchors: Mapped[list] = mapped_column(JSON, default=list)
    global_style_negative: Mapped[str] = mapped_column(Text, nullable=False)


class ShotRecord(Base):
    __tablename__ = "shots"

    shot_id: Mapped[str] = mapped_column(String, primary_key=True)
    scene_id: Mapped[str] = mapped_column(String, nullable=False)
    primary_character_id: Mapped[str] = mapped_column(String, nullable=False)
    wardrobe_id: Mapped[str] = mapped_column(String, nullable=False)
    shot_type: Mapped[str] = mapped_column(String, nullable=False)
    camera_movement: Mapped[str] = mapped_column(String, nullable=False)
    focal_length: Mapped[str] = mapped_column(String, default="50mm")
    action_beat: Mapped[str] = mapped_column(Text, nullable=False)
    secondary_character_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    keyframe_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tail_frame_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    compiled_positive_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compiled_negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)


class GeneratedArtifact(Base):
    """Immutable provenance log entry for every rendered image or video."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shot_id: Mapped[str] = mapped_column(String, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)  # 'keyframe' | 'video'
    output_path: Mapped[str] = mapped_column(String, nullable=False)
    positive_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    checkpoint_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lora_weights: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sampler: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cfg_scale: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comfyui_prompt_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    """Return a new SQLAlchemy session.  Caller is responsible for closing."""
    return SessionLocal()
