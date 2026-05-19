"""Models for LLM-assisted synthesis of external review feedback."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now

LLMReviewProvider = Literal["mock", "external"]


class ReviewerFeedbackEntry(BaseModel):
    reviewer_id: str
    quote: str = Field(min_length=1)
    rating: float
    category: str | None = None


class LLMReviewSynthesisRequest(BaseModel):
    provider: LLMReviewProvider = "mock"
    feedback_entries: list[ReviewerFeedbackEntry] = Field(default_factory=list)
    created_by: str | None = None


class LLMReviewTheme(BaseModel):
    theme_id: str
    title: str
    summary: str
    reviewer_ids: list[str] = Field(default_factory=list)
    quote_evidence: list[str] = Field(default_factory=list)
    average_rating: float


class LLMReviewIssueProposal(BaseModel):
    issue_key: str
    title: str
    description: str
    severity: Literal["low", "medium", "high"]
    reviewer_ids: list[str] = Field(default_factory=list)
    quote_evidence: list[str] = Field(default_factory=list)
    ratings: list[float] = Field(default_factory=list)


class LLMReviewSynthesisResponse(BaseModel):
    schema_version: str = "1.0"
    synthesis_id: str
    provider: LLMReviewProvider
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None
    draft_only: bool = True
    requires_human_approval: bool = True
    release_decision_automated: bool = False
    source_feedback_entries: list[ReviewerFeedbackEntry] = Field(default_factory=list)
    themes: list[LLMReviewTheme] = Field(default_factory=list)
    issue_proposals: list[LLMReviewIssueProposal] = Field(default_factory=list)
    json_path: str
