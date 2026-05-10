"""Source governance models for local project artifacts."""

from __future__ import annotations

from enum import StrEnum

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .base import utc_now


class SourceType(StrEnum):
    UPLOAD = "UPLOAD"
    YOUTUBE = "YOUTUBE"
    URL = "URL"
    DATASET = "DATASET"
    MANUAL_IMPORT = "MANUAL_IMPORT"


class SourceLicenseType(StrEnum):
    OWNED = "OWNED"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    CREATIVE_COMMONS = "CREATIVE_COMMONS"
    RESEARCH_DATASET = "RESEARCH_DATASET"
    YOUTUBE_REFERENCE_ONLY = "YOUTUBE_REFERENCE_ONLY"
    UNKNOWN = "UNKNOWN"


class UsageScope(StrEnum):
    TRAINING = "TRAINING"
    EVALUATION = "EVALUATION"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    DEMO_ONLY = "DEMO_ONLY"


class LeagueTag(StrEnum):
    NBA = "NBA"
    EUROLEAGUE = "EUROLEAGUE"
    NCAA = "NCAA"
    LOCAL = "LOCAL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class VideoSourceRecord(BaseModel):
    """Persisted data source governance record stored at source.json or in source_registry.json."""

    schema_version: str = "1.0"
    project_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    original_input: dict[str, Any] = Field(default_factory=dict)
    pipeline_output: dict[str, Any] = Field(default_factory=dict)
    debug_metadata: dict[str, Any] = Field(default_factory=dict)
    source_id: str
    name: str = "Untitled source"
    source_type: SourceType
    source_url: str | None = None
    title: str | None = None
    license_type: SourceLicenseType = SourceLicenseType.UNKNOWN
    rights_confirmed: bool = False
    allowed_for_training: bool = False
    allowed_for_redistribution: bool = False
    allowed_for_local_storage: bool = False
    league_tag: LeagueTag = LeagueTag.UNKNOWN
    usage_scope: UsageScope = UsageScope.REFERENCE_ONLY
    notes: str | None = None

    @model_validator(mode="after")
    def validate_training_eligibility(self) -> "VideoSourceRecord":
        blocked_license = self.license_type in {
            SourceLicenseType.UNKNOWN,
            SourceLicenseType.YOUTUBE_REFERENCE_ONLY,
        }
        if self.allowed_for_training and blocked_license:
            raise ValueError("UNKNOWN and YOUTUBE_REFERENCE_ONLY licenses cannot be allowed for training.")
        if self.allowed_for_training and not self.rights_confirmed:
            raise ValueError("rights_confirmed must be true before a source can be allowed for training.")
        if self.allowed_for_training and self.usage_scope in {UsageScope.REFERENCE_ONLY, UsageScope.DEMO_ONLY}:
            raise ValueError("Only TRAINING or EVALUATION usage scopes can be allowed for training.")
        return self
