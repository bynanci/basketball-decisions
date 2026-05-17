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


class RoleBreakdownItem(BaseModel):
    """Aggregated Player Value evidence metrics for one court role."""

    court_role: str | None = None
    event_count: int
    avg_role_adjusted_score: float
    avg_opportunity_cost: float | None = None
    correct_rate: float
    timeout_rate: float


class SituationBreakdownItem(BaseModel):
    """Aggregated Player Value evidence metrics for one situation type."""

    situation_type: str | None = None
    event_count: int
    avg_role_adjusted_score: float
    avg_opportunity_cost: float | None = None
    correct_rate: float
    timeout_rate: float


class PlayerValueEvidenceEvent(BaseModel):
    """One decision event with prompt, track, alias, and warning evidence."""

    decision_event_id: str
    project_id: str
    prompt_id: str
    attempt_id: str
    frame_id: str | None = None
    frame_index: int | None = None
    user_role: str | None = None
    court_role_target: str | None = None
    situation_type: str | None = None
    question_mode: str | None = None
    selected_option_id: str | None = None
    correct_option_id: str | None = None
    is_correct: bool
    raw_score: float
    role_adjusted_score: float
    opportunity_cost: float | None = None
    response_time_ms: int | None = None
    timed_out: bool
    source_track_ids: list[str] = Field(default_factory=list)
    context_track_ids: list[str] = Field(default_factory=list)
    prompt_question: str | None = None
    prompt_explanation: str | None = None
    selected_option_label: str | None = None
    correct_option_label: str | None = None
    alias_player_key: str | None = None
    alias_display_name: str | None = None
    alias_team_side: str | None = None
    evidence_warnings: list[str] = Field(default_factory=list)


class PlayerValueEvidenceResponse(BaseModel):
    """Detailed evidence dashboard payload for one Player Value summary."""

    summary: PlayerValueSummary
    events: list[PlayerValueEvidenceEvent] = Field(default_factory=list)
    role_breakdown: list[RoleBreakdownItem] = Field(default_factory=list)
    situation_breakdown: list[SituationBreakdownItem] = Field(default_factory=list)
    warning_summary: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class PlayerValueBuildResponse(BaseModel):
    """Response returned by the Player Value v1 build/read endpoints."""

    summaries: list[PlayerValueSummary] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    warnings: list[str] = Field(default_factory=list)


class PlayerValueBuildMetadata(BaseModel):
    """Immutable baseline metadata captured with a Player Value build."""

    player_value_formula_version: str = "v1"
    recognition_model_version: str | None = None
    decision_rule_set_version: str | None = None
    dataset_fingerprint: str


class PlayerValueBuildIndexEntry(PlayerValueBuildMetadata):
    """Index row for one immutable Player Value build snapshot."""

    build_id: str
    generated_at: datetime
    summary_count: int
    snapshot_path: str
    warnings: list[str] = Field(default_factory=list)


class PlayerValueBuildIndexResponse(BaseModel):
    """Player Value build snapshot index."""

    builds: list[PlayerValueBuildIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class PlayerValueBuildSnapshot(BaseModel):
    """Immutable Player Value build snapshot payload."""

    build_id: str
    metadata: PlayerValueBuildMetadata
    build: PlayerValueBuildResponse


class PlayerValueTrendPoint(PlayerValueBuildMetadata):
    """One point in a project-scoped Player Value trend."""

    build_id: str
    generated_at: datetime
    project_id: str
    player_key: str
    player_value_score: float
    confidence: float
    warnings: list[str] = Field(default_factory=list)
    decision_event_count: int


class PlayerValueTrendSeries(BaseModel):
    """Trend series for one project-scoped player_key."""

    project_id: str
    player_key: str
    display_name: str | None = None
    points: list[PlayerValueTrendPoint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PlayerValueTrendsResponse(BaseModel):
    """All Player Value trend series."""

    trends: list[PlayerValueTrendSeries] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class PlayerValueTrendResponse(BaseModel):
    """Trend lookup for a player_key without cross-project alias merging."""

    player_key: str
    trends: list[PlayerValueTrendSeries] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class PlayerValueCompareRequest(BaseModel):
    """Compare two to four local player_keys without merging aliases."""

    player_keys: list[str] = Field(min_length=2, max_length=4)


class PlayerValueCompareResponse(BaseModel):
    """Comparison response for selected player_keys."""

    player_keys: list[str]
    trends: list[PlayerValueTrendSeries] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
