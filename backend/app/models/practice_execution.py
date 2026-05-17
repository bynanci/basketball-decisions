"""Practice execution models for local feedback capture."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now
from .practice_plan import PracticePlanBlockType, PracticePlanDuration

PracticeExecutionBlockStatus = Literal["PLANNED", "COMPLETED", "SKIPPED", "MODIFIED", "INCOMPLETE"]
PracticeFeedbackSignalType = Literal[
    "REPEAT_DRILL",
    "PROGRESS_DRILL",
    "SIMPLIFY_DRILL",
    "SHORTEN_PLAN",
    "REBUILD_DATASETS",
    "REVIEW_ALIAS_ATTRIBUTION",
]


class PracticeMetricResult(BaseModel):
    """Observed result for a plan success metric."""

    metric: str
    result: str | None = None
    met: bool = False
    notes: str | None = None


class PracticeExecutionBlock(BaseModel):
    """Execution state for one immutable plan block snapshot."""

    block_id: str
    plan_block_id: str
    block_type: PracticePlanBlockType
    title: str
    planned_start_minute: int = Field(ge=0)
    planned_end_minute: int = Field(ge=0)
    planned_duration_minutes: int = Field(ge=1)
    drill_id: str | None = None
    recommendation_id: str | None = None
    success_metrics: list[str] = Field(default_factory=list)
    status: PracticeExecutionBlockStatus = "PLANNED"
    coach_notes: str | None = None
    player_notes: str | None = None
    metric_results: list[PracticeMetricResult] = Field(default_factory=list)
    outcome_rating: int | None = Field(default=None, ge=1, le=5)
    actual_duration_minutes: int | None = Field(default=None, ge=0)
    modified_title: str | None = None
    modified_notes: str | None = None


class PracticeExecutionCreateRequest(BaseModel):
    """Start a practice execution from a saved practice plan."""

    plan_id: str
    started_by: str | None = None
    notes: str | None = None


class PracticeExecutionUpdateRequest(BaseModel):
    """Update captured execution details without changing the source plan."""

    started_by: str | None = None
    notes: str | None = None
    completed_at: datetime | None = None
    blocks: list[PracticeExecutionBlock] | None = None


class PracticeExecution(BaseModel):
    """Persisted execution session for one practice plan."""

    schema_version: str = "1.0"
    execution_id: str
    plan_id: str
    plan_title: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_by: str | None = None
    notes: str | None = None
    completed_at: datetime | None = None
    project_id: str | None = None
    player_key: str | None = None
    player_keys: list[str] = Field(default_factory=list)
    planned_duration_minutes: PracticePlanDuration
    blocks: list[PracticeExecutionBlock] = Field(default_factory=list)
    source_plan_json_path: str
    json_path: str


class PracticeExecutionListItem(BaseModel):
    """Compact list item for saved execution sessions."""

    execution_id: str
    plan_id: str
    plan_title: str
    created_at: datetime
    updated_at: datetime
    started_by: str | None = None
    completed_at: datetime | None = None
    planned_duration_minutes: PracticePlanDuration
    completion_rate: float = 0
    skipped_count: int = 0
    modified_count: int = 0
    json_path: str


class PracticeExecutionListResponse(BaseModel):
    """Saved execution index."""

    executions: list[PracticeExecutionListItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class PracticeFeedbackSignal(BaseModel):
    """Deterministic signal generated from captured practice execution data."""

    signal_type: PracticeFeedbackSignalType
    execution_id: str
    block_id: str | None = None
    drill_id: str | None = None
    recommendation_id: str | None = None
    reason: str
    severity: Literal["info", "warning", "action"] = "info"


class PracticeFeedbackSummary(BaseModel):
    """Aggregate feedback summary for one execution."""

    execution_id: str
    plan_id: str
    completion_rate: float
    average_block_rating: float | None = None
    met_metrics: list[str] = Field(default_factory=list)
    missed_metrics: list[str] = Field(default_factory=list)
    skipped_count: int = 0
    modified_count: int = 0
    actual_duration_minutes: int = 0
    planned_duration_minutes: int
    recommended_next_actions: list[str] = Field(default_factory=list)
    signals: list[PracticeFeedbackSignal] = Field(default_factory=list)


class PracticeFeedbackSignalsResponse(BaseModel):
    """Global practice feedback signals across saved executions."""

    signals: list[PracticeFeedbackSignal] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
