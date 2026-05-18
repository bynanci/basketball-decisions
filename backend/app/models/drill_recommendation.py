"""Deterministic drill recommendation models backed by a local catalog."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now

DrillPriority = Literal["LOW", "MEDIUM", "HIGH"]
DrillEvidenceSource = Literal[
    "DECISION_DIAGNOSTICS",
    "PLAYER_VALUE",
    "PLAYER_VALUE_TRENDS",
    "TEACHING_CASE",
    "REVIEW_QUEUE",
]
RecommendationAdjustmentType = Literal[
    "PRIORITY_UP",
    "PRIORITY_DOWN",
    "CONFIDENCE_UP",
    "CONFIDENCE_DOWN",
    "REASON_HINT",
]


class DrillCatalogItem(BaseModel):
    """One cataloged drill with human-authored coaching content."""

    drill_id: str
    title: str
    role: str | None = None
    situation: str
    description: str
    coaching_cues: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class DrillCatalogResponse(BaseModel):
    """Local drill catalog response."""

    drills: list[DrillCatalogItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class DrillEvidenceRef(BaseModel):
    """Traceable local artifact reference that caused a recommendation."""

    source: DrillEvidenceSource
    artifact: str
    ref_id: str | None = None
    project_id: str | None = None
    player_key: str | None = None
    prompt_id: str | None = None
    detail: str


class RecommendationAdjustment(BaseModel):
    """Deterministic practice-feedback adjustment applied to a recommendation."""

    adjustment_id: str
    signal_id: str
    signal_type: str
    adjustment_type: RecommendationAdjustmentType
    confidence_delta: float = 0.0
    priority_delta: int = 0
    reason: str
    execution_id: str | None = None
    block_id: str | None = None
    drill_id: str | None = None
    recommendation_id: str | None = None


class DrillRecommendation(BaseModel):
    """One deterministic drill recommendation from local analytics artifacts."""

    recommendation_id: str
    drill_id: str
    title: str
    priority: DrillPriority
    confidence: float = Field(ge=0.0, le=1.0)
    role: str | None = None
    situation: str
    reason: str
    coaching_cues: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    evidence_refs: list[DrillEvidenceRef] = Field(default_factory=list)
    feedback_adjusted: bool = False
    feedback_signal_ids: list[str] = Field(default_factory=list)
    adjustment_summary: list[str] = Field(default_factory=list)
    adjustments: list[RecommendationAdjustment] = Field(default_factory=list)


class DrillRecommendationRequest(BaseModel):
    """Options for building local drill recommendations."""

    project_id: str | None = None
    player_key: str | None = None
    max_recommendations: int = Field(default=8, ge=1, le=24)
    include_practice_feedback: bool = False
    feedback_lookback_limit: int = Field(default=25, ge=1, le=200)


class DrillRecommendationResponse(BaseModel):
    """Persisted recommendation set and warnings."""

    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    project_id: str | None = None
    player_key: str | None = None
    recommendations: list[DrillRecommendation] = Field(default_factory=list)
    feedback_signal_count: int = 0
    adjustment_summary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    catalog_path: str
    latest_path: str
