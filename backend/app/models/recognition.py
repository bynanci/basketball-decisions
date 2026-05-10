"""Recognition quality feature and score models."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class TrackRecognitionScore(BaseModel):
    """Explainable false-positive risk score for one track."""

    track_id: str
    false_positive_risk: float = Field(ge=0.0, le=1.0)
    recommended_label: str
    reasons: list[str] = Field(default_factory=list)
    features: TrackRecognitionFeatures


class RecognitionScoreSummary(BaseModel):
    """Aggregate counts for a project recognition scoring run."""

    high_risk_detection_count: int
    high_risk_track_count: int


class RecognitionScoreProjectResponse(BaseModel):
    """Recognition quality scores for a project."""

    project_id: str
    detection_scores: list[DetectionRecognitionScore] = Field(default_factory=list)
    track_scores: list[TrackRecognitionScore] = Field(default_factory=list)
    summary: RecognitionScoreSummary
