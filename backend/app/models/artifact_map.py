"""Artifact dependency map and freshness status models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now

ArtifactStatus = Literal["fresh", "stale", "missing", "unknown"]
ArtifactSeverity = Literal["info", "warning", "action"]


class ArtifactDependency(BaseModel):
    """One local artifact plus dependency freshness metadata."""

    key: str
    label: str
    category: str
    path: str | None = None
    exists: bool = False
    status: ArtifactStatus = "unknown"
    severity: ArtifactSeverity = "info"
    updated_at: datetime | None = None
    stale_after: datetime | None = None
    depends_on: list[str] = Field(default_factory=list)
    stale_reason: str | None = None
    detail: str | None = None


class ArtifactMapResponse(BaseModel):
    """Deterministic dependency map for local lab artifacts."""

    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    artifacts: list[ArtifactDependency] = Field(default_factory=list)
    status_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    stale_artifact_count: int = 0
    missing_artifact_count: int = 0
    warnings: list[str] = Field(default_factory=list)
