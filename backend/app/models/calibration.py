"""Court calibration Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .base import ProjectArtifact


class ImagePoint(BaseModel):
    """Pixel-space point on an image or frame."""

    x: float
    y: float


class CourtPoint(BaseModel):
    """Court-space point in a canonical 2D coordinate system."""

    x: float
    y: float
    label: str | None = None


class CourtKeypointPair(BaseModel):
    """Mapping between one image point and one court point."""

    keypoint_id: str
    image_point: ImagePoint
    court_point: CourtPoint
    confidence: float | None = None


class Calibration(ProjectArtifact):
    """Persisted calibration document stored at calibration.json."""

    frame_id: str | None = None
    homography: list[list[float]] | None = None
    keypoint_pairs: list[CourtKeypointPair] = Field(default_factory=list)
    reprojection_error: float | None = None


class SaveCalibrationRequest(BaseModel):
    """Client payload for saving calibration keypoints and outputs."""

    project_id: str
    frame_id: str | None = None
    keypoint_pairs: list[CourtKeypointPair] = Field(default_factory=list)
    homography: list[list[float]] | None = None
    debug_metadata: dict[str, Any] = Field(default_factory=dict)


class SaveCalibrationResponse(BaseModel):
    """Response returned after saving calibration."""

    calibration: Calibration
    storage_path: str
