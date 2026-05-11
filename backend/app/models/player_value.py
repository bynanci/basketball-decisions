"""Explainable Player Value v1 models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .base import utc_now
from .player_identity import TeamSide


class PlayerValueComponent(BaseModel):
    """One weighted part of the Player Value v1 formula."""

    name: str
    value: float
    weight: float
    contribution: float
    explanation: str


class PlayerValueTrace(BaseModel):
    """Source IDs used to build a Player Value summary."""

    project_ids: list[str] = Field(default_factory=list)
    track_ids: list[str] = Field(default_factory=list)
    decision_event_ids: list[str] = Field(default_factory=list)
    prompt_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class PlayerValueSummary(BaseModel):
    """Explainable local summary for one alias-based player identity."""

    project_id: str
    player_key: str
    display_name: str | None = None
    team_side: TeamSide = TeamSide.UNKNOWN
    role_hint: str | None = None
    track_ids: list[str] = Field(default_factory=list)
    decision_event_count: int
    avg_raw_decision_score: float
    avg_role_adjusted_score: float
    avg_opportunity_cost: float | None = None
    correct_rate: float
    timeout_rate: float
    recognition_reliability_score: float
    consistency_score: float
    improvement_score: float
    participation_score: float
    player_value_score: float
    components: list[PlayerValueComponent] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    trace: PlayerValueTrace
    created_at: datetime = Field(default_factory=utc_now)


class PlayerValueBuildResponse(BaseModel):
    """Response returned by the Player Value v1 build/read endpoints."""

    summaries: list[PlayerValueSummary] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    warnings: list[str] = Field(default_factory=list)
