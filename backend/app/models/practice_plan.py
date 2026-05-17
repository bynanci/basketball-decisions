"""Practice plan models built from deterministic drill recommendations."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now
from .drill_recommendation import DrillEvidenceRef

PracticePlanDuration = Literal[60, 75, 90, 120]
PracticePlanBlockType = Literal["warmup", "drill", "scrimmage", "review"]


class PracticePlanBuildRequest(BaseModel):
    """Options for building a local, time-boxed practice plan."""

    title: str = "Practice Plan"
    total_duration_minutes: PracticePlanDuration = 90
    project_id: str | None = None
    player_key: str | None = None
    player_keys: list[str] = Field(default_factory=list)
    max_drill_blocks: int = Field(default=5, ge=1, le=10)
    created_by: str | None = None
    notes: str | None = None


class PracticePlanBlock(BaseModel):
    """One time-boxed practice block."""

    block_id: str
    block_type: PracticePlanBlockType
    title: str
    start_minute: int = Field(ge=0)
    end_minute: int = Field(ge=0)
    duration_minutes: int = Field(ge=1)
    drill_id: str | None = None
    recommendation_id: str | None = None
    priority: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    target_situations: list[str] = Field(default_factory=list)
    player_keys: list[str] = Field(default_factory=list)
    coaching_cues: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    evidence_refs: list[DrillEvidenceRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PracticePlan(BaseModel):
    """Persisted practice plan and export metadata."""

    schema_version: str = "1.0"
    plan_id: str
    title: str
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None
    project_id: str | None = None
    player_key: str | None = None
    total_duration_minutes: PracticePlanDuration
    target_roles: list[str] = Field(default_factory=list)
    target_situations: list[str] = Field(default_factory=list)
    player_keys: list[str] = Field(default_factory=list)
    source_recommendation_ids: list[str] = Field(default_factory=list)
    blocks: list[PracticePlanBlock] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[DrillEvidenceRef] = Field(default_factory=list)
    markdown: str
    json_path: str
    markdown_path: str


class PracticePlanListItem(BaseModel):
    """Compact list entry for a saved practice plan."""

    plan_id: str
    title: str
    created_at: datetime
    created_by: str | None = None
    project_id: str | None = None
    player_key: str | None = None
    total_duration_minutes: PracticePlanDuration
    target_roles: list[str] = Field(default_factory=list)
    target_situations: list[str] = Field(default_factory=list)
    player_keys: list[str] = Field(default_factory=list)
    warning_count: int = 0
    json_path: str
    markdown_path: str


class PracticePlanListResponse(BaseModel):
    """Saved practice plan index."""

    plans: list[PracticePlanListItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
