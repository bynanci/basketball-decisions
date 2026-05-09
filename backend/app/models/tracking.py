from typing import Any, Literal

from pydantic import BaseModel, Field


class RunTrackingRequest(BaseModel):
    confidence_threshold: float = Field(default=0.35, ge=0, le=1)
    frame_stride: int = Field(default=1, gt=0)
    max_frames: int | None = Field(default=None, gt=0)
    use_stub_when_unavailable: bool = True


class TrackPoint(BaseModel):
    frame_index: int
    timestamp_seconds: float | None = None
    bbox_xyxy: list[float] = Field(..., min_length=4, max_length=4)
    confidence: float | None = None
    court_x: float | None = None
    court_y: float | None = None


class DetectionTrack(BaseModel):
    track_id: str
    class_name: Literal["person"] = "person"
    points: list[TrackPoint]


class RunTrackingResponse(BaseModel):
    project_id: str
    status: Literal["completed", "stubbed"]
    tracks: list[DetectionTrack]
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
