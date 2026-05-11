"""Unified active-learning review queue models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now

ReviewQueueItemType = Literal[
    "RECOGNITION_TRACK",
    "RECOGNITION_DETECTION",
    "DECISION_PROMPT",
    "DECISION_ATTEMPT",
    "PLAYER_VALUE_ATTRIBUTION",
    "RULE_DRAFT",
]
ReviewQueuePriority = Literal["LOW", "MEDIUM", "HIGH"]
ReviewQueueStatus = Literal["OPEN", "RESOLVED", "DISMISSED"]


class ReviewQueueItem(BaseModel):
    """One reviewer action surfaced from diagnostics, recognition, or governance artifacts."""

    item_id: str
    item_type: ReviewQueueItemType
    priority: ReviewQueuePriority
    project_id: str | None = None
    prompt_id: str | None = None
    attempt_id: str | None = None
    track_id: str | None = None
    player_key: str | None = None
    reason: str
    recommended_action: str
    status: ReviewQueueStatus = "OPEN"
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None


class ReviewQueueGenerateResponse(BaseModel):
    """Response returned after rebuilding open review queue candidates."""

    items: list[ReviewQueueItem] = Field(default_factory=list)
    generated_count: int = 0
    open_count: int = 0
    resolved_count: int = 0
    dismissed_count: int = 0


class UpdateReviewQueueItemRequest(BaseModel):
    status: ReviewQueueStatus
