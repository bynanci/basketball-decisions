"""Court projection Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectedTrackPoint(BaseModel):
    """One point in a player's projected court-space track."""

    frame_id: str
    frame_index: int
    timestamp_seconds: float
    court_x: float
    court_y: float
    source_image_point_x: float | None = None
    source_image_point_y: float | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectedPlayerTrack(BaseModel):
    """Projected court-space track for a single player."""

    track_id: str
    player_id: str | None = None
    points: list[ProjectedTrackPoint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
