"""Project-level Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .base import ProjectArtifact


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
