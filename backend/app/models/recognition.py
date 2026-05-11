"""Recognition quality feature and score models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now


class DetectionRecognitionFeatures(BaseModel):
    """Local model-ready features for one detection."""

    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    bbox_area: float
    bbox_aspect_ratio: float
    confidence: float
    frame_index: int
    has_track_id: bool
    track_point_count: int | None = None
    inside_projected_court: bool | None = None


class TrackRecognitionFeatures(BaseModel):
    """Local model-ready features for one image-space track."""

    point_count: int
    avg_confidence: float | None = None
    min_confidence: float | None = None
    max_confidence: float | None = None
    avg_bbox_area: float | None = None
    bbox_area_variance: float | None = None
    avg_speed_image: float | None = None
    max_jump_distance_image: float | None = None
    frame_span: int
    gap_count: int
    projected_inside_court_ratio: float | None = None


class DetectionRecognitionScore(BaseModel):
    """Explainable false-positive risk score for one detection."""

    detection_id: str
    track_id: str | None = None
    false_positive_risk: float = Field(ge=0.0, le=1.0)
    recommended_label: str
    reasons: list[str] = Field(default_factory=list)
    features: DetectionRecognitionFeatures
    model_version: str | None = None
    scoring_source: Literal["RULE", "MODEL"] = "RULE"


class TrackRecognitionScore(BaseModel):
    """Explainable false-positive risk score for one track."""

    track_id: str
    false_positive_risk: float = Field(ge=0.0, le=1.0)
    recommended_label: str
    reasons: list[str] = Field(default_factory=list)
    features: TrackRecognitionFeatures
    model_version: str | None = None
    scoring_source: Literal["RULE", "MODEL"] = "RULE"


class RecognitionScoreSummary(BaseModel):
    """Aggregate counts for a project recognition scoring run."""

    high_risk_detection_count: int
    high_risk_track_count: int
    model_version: str | None = None
    scoring_source: Literal["RULE", "MODEL"] = "RULE"


class RecognitionScoreProjectResponse(BaseModel):
    """Recognition quality scores for a project."""

    project_id: str
    detection_scores: list[DetectionRecognitionScore] = Field(default_factory=list)
    track_scores: list[TrackRecognitionScore] = Field(default_factory=list)
    summary: RecognitionScoreSummary
    model_version: str | None = None
    scoring_source: Literal["RULE", "MODEL"] = "RULE"


class RecognitionModelMetrics(BaseModel):
    """Saved metrics for a local recognition baseline."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: list[list[int]]
    train_sample_count: int
    test_sample_count: int
    feature_importance: dict[str, float] | None = None


class RecognitionDatasetLineage(BaseModel):
    """Dataset lineage captured at recognition model training time."""

    dataset_type: Literal["recognition"] = "recognition"
    manifest_path: str
    samples_path: str
    labels_path: str
    dataset_fingerprint: str
    manifest_fingerprint: str | None = None
    samples_fingerprint: str | None = None
    labels_fingerprint: str | None = None
    sample_count: int = 0
    label_count: int = 0
    source_project_ids: list[str] = Field(default_factory=list)
    exported_at: datetime | None = None


class RecognitionEvaluationReport(BaseModel):
    """Registered immutable evaluation report for a recognition model."""

    report_id: str
    model_version: str
    created_at: datetime = Field(default_factory=utc_now)
    metrics_path: str
    report_path: str
    dataset_fingerprint: str
    metrics: RecognitionModelMetrics


class RecognitionModelInfo(BaseModel):
    """Registered local recognition model metadata."""

    version: str
    active: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    model_path: str
    metrics_path: str
    feature_schema_path: str
    lineage_path: str | None = None
    evaluation_report_path: str | None = None
    dataset_fingerprint: str | None = None
    dataset_lineage: RecognitionDatasetLineage | None = None
    metrics: RecognitionModelMetrics | None = None


class RecognitionModelRegistry(BaseModel):
    """Local registry for recognition baseline models."""

    active_version: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    models: list[RecognitionModelInfo] = Field(default_factory=list)
    active_model: RecognitionModelInfo | None = None


class RecognitionModelComparison(BaseModel):
    """Metric comparison between two recognition model versions."""

    base_version: str
    candidate_version: str
    base_model: RecognitionModelInfo
    candidate_model: RecognitionModelInfo
    metric_deltas: dict[str, float] = Field(default_factory=dict)


class RecognitionActivationRequest(BaseModel):
    activate: bool = True
    reason: str | None = None


class RecognitionActivationResponse(BaseModel):
    active_version: str | None = None
    previous_active_version: str | None = None
    activated_version: str
    updated_at: datetime = Field(default_factory=utc_now)
    reason: str | None = None
    registry: RecognitionModelRegistry


class RecognitionEvaluationReportRegistry(BaseModel):
    reports: list[RecognitionEvaluationReport] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
