"""Project-level Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .base import ProjectArtifact
from .calibration import Calibration
from .player_identity import PlayerAliasListResponse
from .source import VideoSourceRecord
from .tracking import ProjectTracksResponse, RunTrackingResponse, TrackReviewResponse
from .video import ExtractFramesResponse, VideoAsset


class Project(ProjectArtifact):
    """Persisted project document stored at project.json."""

    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreateRequest(BaseModel):
    """Client payload for creating a project."""

    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreateResponse(BaseModel):
    """Response returned after creating a project."""

    project: Project
    storage_path: str


class ProjectBundleResponse(BaseModel):
    """Refresh-safe bundle of a project and any persisted local artifacts."""

    project: Project
    video: VideoAsset | None = None
    source: VideoSourceRecord | None = None
    frames: ExtractFramesResponse | None = None
    calibration: Calibration | None = None
    tracking: RunTrackingResponse | None = None
    projected_tracks: ProjectTracksResponse | None = None
    tracking_review: TrackReviewResponse | None = None
    player_aliases: PlayerAliasListResponse | None = None
