"""Shared Pydantic model primitives for persisted project artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for model defaults."""

    return datetime.now(timezone.utc)


class ProjectArtifact(BaseModel):
    """Common fields expected on MVP JSON storage documents.

    MVP storage paths:
    - backend/data/projects/{project_id}/project.json
    - backend/data/projects/{project_id}/video.json
    - backend/data/projects/{project_id}/frames/index.json
    - backend/data/projects/{project_id}/calibration.json
    - backend/data/projects/{project_id}/detections.json
    - backend/data/projects/{project_id}/tracks.json
    - backend/data/projects/{project_id}/projected_tracks.json
    """

    schema_version: str = "1.0"
    project_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    original_input: dict[str, Any] = Field(default_factory=dict)
    pipeline_output: dict[str, Any] = Field(default_factory=dict)
    debug_metadata: dict[str, Any] = Field(default_factory=dict)
