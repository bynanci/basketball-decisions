"""Evidence-locked LLM coach summary request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now

LLMProvider = Literal["mock", "external"]


class EvidenceLockedSummaryRequest(BaseModel):
    report_id: str
    provider: LLMProvider = "mock"
    created_by: str | None = None


class EvidenceLockedSummaryValidation(BaseModel):
    warnings_preserved: bool
    scores_unchanged: bool
    evidence_refs_preserved: bool
    prohibited_phrases: list[str] = Field(default_factory=list)


class EvidenceLockedSummaryResponse(BaseModel):
    schema_version: str = "1.0"
    summary_id: str
    report_id: str
    provider: LLMProvider
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None
    llm_assisted_wording: str
    warnings: list[str] = Field(default_factory=list)
    validation: EvidenceLockedSummaryValidation
    source_report_json_path: str
    json_path: str
