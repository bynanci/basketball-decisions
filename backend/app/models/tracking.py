"""Detection and player tracking Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .base import ProjectArtifact


class DetectionBox(BaseModel):
    """Axis-aligned detection bounding box in pixel coordinates."""

    x: float
    y: float
    width: float
    height: float


class Detection(BaseModel):
    """Single model detection for one frame."""

    detection_id: str
    frame_id: str
    frame_index: int
    box: DetectionBox
    confidence: float
    class_name: str = "player"
    track_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrackPoint(BaseModel):
    """One point in a player's image-space track."""

    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_point_x: float
    image_point_y: float
    detection_id: str | None = None
    confidence: float | None = None


class PlayerTrack(BaseModel):
    """Image-space track for a single player."""

    track_id: str
    player_id: str | None = None
    points: list[TrackPoint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunTrackingRequest(BaseModel):
    """Request parameters for running detection and tracking."""

    project_id: str
    frame_ids: list[str] | None = None
    model_name: str | None = None
    confidence_threshold: float | None = None
    iou_threshold: float | None = None
    max_players: int | None = None


class RunTrackingResponse(ProjectArtifact):
    """Persisted tracking output for detections.json and tracks.json."""

    request: RunTrackingRequest
    detections: list[Detection] = Field(default_factory=list)
    tracks: list[PlayerTrack] = Field(default_factory=list)


class TrackReviewPatch(BaseModel):
    """Manual tracking quality-control edits supplied by a reviewer."""

    excluded_detection_ids: list[str] = Field(default_factory=list)
    excluded_track_ids: list[str] = Field(default_factory=list)
    track_id_aliases: dict[str, str] = Field(default_factory=dict)
    notes: str | None = None


class ProjectTracksResponse(BaseModel):
    """Combined tracking and projected court-coordinate response."""

    project_id: str
    tracking: RunTrackingResponse | None = None
    projected_tracks: list["ProjectedPlayerTrack"] = Field(default_factory=list)
    storage_paths: dict[str, str] = Field(default_factory=dict)


class TrackReviewResponse(BaseModel):
    """Raw tracking, reviewer patch, and cleaned tracking artifacts."""

    project_id: str
    tracking: RunTrackingResponse
    review_patch: TrackReviewPatch = Field(default_factory=TrackReviewPatch)
    cleaned_tracking: RunTrackingResponse | None = None
    cleaned_projected_tracks: list["ProjectedPlayerTrack"] = Field(default_factory=list)
    storage_paths: dict[str, str] = Field(default_factory=dict)


from .projection import ProjectedPlayerTrack
ProjectTracksResponse.model_rebuild()
TrackReviewResponse.model_rebuild()
