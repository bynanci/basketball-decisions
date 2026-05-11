"""Manual player identity and track alias models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import utc_now


class TeamSide(StrEnum):
    HOME = "HOME"
    AWAY = "AWAY"
    UNKNOWN = "UNKNOWN"


class PlayerAliasSource(StrEnum):
    MANUAL = "MANUAL"
    HEURISTIC = "HEURISTIC"
    MODEL = "MODEL"


class PlayerAlias(BaseModel):
    """Reviewer-managed mapping from one stable local player key to one or more track IDs."""

    player_key: str = Field(min_length=1)
    project_id: str
    track_ids: list[str] = Field(min_length=1)
    display_name: str | None = None
    team_side: TeamSide = TeamSide.UNKNOWN
    role_hint: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: PlayerAliasSource = PlayerAliasSource.MANUAL
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("player_key")
    @classmethod
    def player_key_must_not_be_blank(cls, player_key: str) -> str:
        normalized = player_key.strip()
        if not normalized:
            raise ValueError("player_key is required")
        return normalized

    @field_validator("track_ids")
    @classmethod
    def track_ids_must_be_unique(cls, track_ids: list[str]) -> list[str]:
        normalized_track_ids = [track_id.strip() for track_id in track_ids]
        if any(not track_id for track_id in normalized_track_ids):
            raise ValueError("track_ids must not contain blank values")
        if len(normalized_track_ids) != len(set(normalized_track_ids)):
            raise ValueError("track_ids must be unique within each alias")
        return normalized_track_ids


class PlayerAliasListResponse(BaseModel):
    """Full persisted manual alias list for a project."""

    project_id: str
    aliases: list[PlayerAlias] = Field(default_factory=list)

    @model_validator(mode="after")
    def aliases_must_be_unique_for_project(self) -> "PlayerAliasListResponse":
        player_keys: set[str] = set()
        track_ids: set[str] = set()
        for alias in self.aliases:
            if alias.project_id != self.project_id:
                raise ValueError("alias project_id must match response project_id")
            if alias.player_key in player_keys:
                raise ValueError("duplicate player_key values are not allowed")
            player_keys.add(alias.player_key)
            overlapping = sorted(track_ids.intersection(alias.track_ids))
            if overlapping:
                raise ValueError(f"duplicate track_id values across aliases are not allowed: {', '.join(overlapping)}")
            track_ids.update(alias.track_ids)
        return self
