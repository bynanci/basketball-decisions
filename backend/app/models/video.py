"""Video and frame extraction Pydantic models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import ProjectArtifact

VideoSourceType = Literal["upload", "youtube"]


class YouTubeVideoRequest(BaseModel):
    """Client payload for registering or downloading a YouTube video."""

    url: str


class VideoAsset(ProjectArtifact):
    """Persisted source video document stored at video.json."""

    asset_id: str
    source_type: VideoSourceType
    uri: str | None = None
    filename: str | None = None
    content_type: str | None = None
    duration_seconds: float | None = None
    fps: float | None = None
    frame_count: int | None = None
    width: int | None = None
    height: int | None = None


class FrameAsset(BaseModel):
    """Single extracted frame entry within frames/index.json."""

    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_path: str
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractFramesRequest(BaseModel):
    """Request parameters for extracting frames from a video asset."""

    project_id: str
    video_asset_id: str
    target_fps: float | None = None
    start_time_seconds: float | None = None
    end_time_seconds: float | None = None
    max_frames: int | None = None


class ExtractFramesResponse(ProjectArtifact):
    """Persisted extracted-frame index stored at frames/index.json."""

    request: ExtractFramesRequest
    frames: list[FrameAsset] = Field(default_factory=list)
