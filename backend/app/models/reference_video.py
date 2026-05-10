"""Reference-only video breakdown and draft authoring models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import utc_now
from .quiz import CourtRoleTarget, SituationType
from .source import SourceLicenseType, SourceType, UsageScope

ReferenceSourceType = Literal[SourceType.YOUTUBE, SourceType.URL]
BreakdownConfidence = Literal["LOW", "MEDIUM", "HIGH"]
DraftStatus = Literal["DRAFT", "APPROVED", "REJECTED"]


class ReferenceVideo(BaseModel):
    reference_id: str
    source_id: str
    title: str
    url: str
    source_type: ReferenceSourceType
    license_type: SourceLicenseType = SourceLicenseType.UNKNOWN
    usage_scope: UsageScope = UsageScope.REFERENCE_ONLY
    allowed_for_training: bool = False
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()]

    @model_validator(mode="after")
    def validate_reference_governance(self) -> "ReferenceVideo":
        if self.source_type == SourceType.YOUTUBE:
            self.license_type = SourceLicenseType.YOUTUBE_REFERENCE_ONLY
            self.usage_scope = UsageScope.REFERENCE_ONLY
            self.allowed_for_training = False
        if self.usage_scope == UsageScope.REFERENCE_ONLY and self.allowed_for_training:
            raise ValueError("REFERENCE_ONLY reference videos cannot be allowed for training.")
        return self


class CreateReferenceVideoRequest(BaseModel):
    title: str
    url: str
    source_type: ReferenceSourceType | None = None
    license_type: SourceLicenseType | None = None
    usage_scope: UsageScope | None = None
    allowed_for_training: bool | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ReferenceBreakdownNote(BaseModel):
    note_id: str
    reference_id: str
    timestamp_sec: float | None = None
    timestamp_label: str | None = None
    court_role: CourtRoleTarget
    situation_type: SituationType
    concept: str
    good_read: str
    bad_read: str
    coaching_cue: str
    tags: list[str] = Field(default_factory=list)
    confidence: BreakdownConfidence = "MEDIUM"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()]


class UpsertReferenceBreakdownNoteRequest(BaseModel):
    timestamp_sec: float | None = None
    timestamp_label: str | None = None
    court_role: CourtRoleTarget
    situation_type: SituationType
    concept: str
    good_read: str
    bad_read: str
    coaching_cue: str
    tags: list[str] = Field(default_factory=list)
    confidence: BreakdownConfidence = "MEDIUM"


class QuizPromptDraftOption(BaseModel):
    option_id: str
    label: str
    is_correct: bool = False


class QuizPromptDraft(BaseModel):
    draft_id: str
    reference_id: str
    source_note_id: str
    question: str
    court_role_target: CourtRoleTarget
    situation_type: SituationType
    role_instruction: str
    options: list[QuizPromptDraftOption]
    explanation: str
    status: DraftStatus = "DRAFT"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DecisionRuleDraft(BaseModel):
    draft_id: str
    reference_id: str
    source_note_id: str
    court_role: CourtRoleTarget
    situation_type: SituationType
    condition_text: str
    positive_cue: str
    negative_cue: str
    suggested_weight: float = 1.0
    explanation: str
    status: DraftStatus = "DRAFT"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReferenceVideoListResponse(BaseModel):
    reference_videos: list[ReferenceVideo]


class ReferenceVideoDraftSummary(BaseModel):
    reference_only_source_count: int = 0
    quiz_prompt_draft_count: int = 0
    decision_rule_draft_count: int = 0
