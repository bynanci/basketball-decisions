"""Development progress dashboard models for local artifact aggregation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import utc_now

DevelopmentDashboardSeverity = Literal["info", "warning", "action"]


class DevelopmentDashboardMetric(BaseModel):
    """One key metric card on the development dashboard."""

    key: str
    label: str
    value: int | float | str
    detail: str | None = None
    severity: DevelopmentDashboardSeverity = "info"


class DevelopmentDashboardTeamSummary(BaseModel):
    """Team-level rollup from existing local artifacts only."""

    player_count: int = 0
    average_player_value_score: float | None = None
    average_confidence: float | None = None
    total_decision_events: int = 0
    trend_series_count: int = 0
    practice_plan_count: int = 0
    practice_execution_count: int = 0
    coach_report_count: int = 0
    notes: list[str] = Field(default_factory=list)


class DevelopmentDashboardPlayerSummary(BaseModel):
    """Player development row derived from Player Value and trend artifacts."""

    project_id: str
    player_key: str
    display_name: str | None = None
    team_side: str | None = None
    role_hint: str | None = None
    player_value_score: float | None = None
    confidence: float | None = None
    decision_event_count: int = 0
    trend_points: int = 0
    latest_trend_delta: float | None = None
    warnings: list[str] = Field(default_factory=list)


class DevelopmentDashboardAction(BaseModel):
    """Operational next-best-action, never generated coaching advice."""

    action_id: str
    title: str
    detail: str
    severity: DevelopmentDashboardSeverity = "info"
    artifact: str | None = None
    href: str | None = None


class DevelopmentDashboardDatasetHealthSummary(BaseModel):
    """Compact readiness rollup from dataset health artifacts."""

    available: bool = False
    recognition_sample_count: int = 0
    recognition_label_count: int = 0
    recognition_warning_count: int = 0
    decision_sample_count: int = 0
    decision_label_count: int = 0
    decision_warning_count: int = 0
    generated_at: datetime | None = None


class DevelopmentDashboardModelRegistrySummary(BaseModel):
    """Compact recognition model registry summary."""

    available: bool = False
    active_version: str | None = None
    model_count: int = 0
    latest_version: str | None = None
    updated_at: datetime | None = None


class DevelopmentDashboardPracticeFeedbackSummary(BaseModel):
    """Global practice feedback signal and execution rollup."""

    signal_count: int = 0
    action_signal_count: int = 0
    warning_signal_count: int = 0
    latest_signal_at: datetime | None = None
    completion_rate_average: float | None = None
    skipped_count: int = 0
    modified_count: int = 0


class DevelopmentDashboardReviewQueueSummary(BaseModel):
    """Open review queue rollup."""

    item_count: int = 0
    open_count: int = 0
    high_priority_count: int = 0
    action_log_count: int = 0


class DevelopmentDashboardResponse(BaseModel):
    """M26 dashboard response aggregated from existing local artifacts."""

    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    metrics: list[DevelopmentDashboardMetric] = Field(default_factory=list)
    team_summary: DevelopmentDashboardTeamSummary = Field(default_factory=DevelopmentDashboardTeamSummary)
    player_summaries: list[DevelopmentDashboardPlayerSummary] = Field(default_factory=list)
    next_best_actions: list[DevelopmentDashboardAction] = Field(default_factory=list)
    dataset_health_summary: DevelopmentDashboardDatasetHealthSummary = Field(default_factory=DevelopmentDashboardDatasetHealthSummary)
    model_registry_summary: DevelopmentDashboardModelRegistrySummary = Field(default_factory=DevelopmentDashboardModelRegistrySummary)
    practice_feedback_summary: DevelopmentDashboardPracticeFeedbackSummary = Field(default_factory=DevelopmentDashboardPracticeFeedbackSummary)
    review_queue_summary: DevelopmentDashboardReviewQueueSummary = Field(default_factory=DevelopmentDashboardReviewQueueSummary)
    warnings: list[str] = Field(default_factory=list)
    artifact_counts: dict[str, int] = Field(default_factory=dict)
    artifact_status: dict[str, bool] = Field(default_factory=dict)
    raw_artifact_refs: dict[str, Any] = Field(default_factory=dict)
