"""Unified active-learning review queue models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

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


class ReviewActionType(StrEnum):
    MARK_TRACK_FALSE_POSITIVE = "MARK_TRACK_FALSE_POSITIVE"
    MARK_TRACK_VALID_PLAYER = "MARK_TRACK_VALID_PLAYER"
    ASSIGN_TRACK_TO_PLAYER_ALIAS = "ASSIGN_TRACK_TO_PLAYER_ALIAS"
    OPEN_ALIAS_REVIEW = "OPEN_ALIAS_REVIEW"
    FLAG_PROMPT_LABEL_ISSUE = "FLAG_PROMPT_LABEL_ISSUE"
    UPDATE_PROMPT_EXPECTED_VALUE = "UPDATE_PROMPT_EXPECTED_VALUE"
    MARK_ATTEMPT_TEACHING_CASE = "MARK_ATTEMPT_TEACHING_CASE"
    APPROVE_RULE_DRAFT = "APPROVE_RULE_DRAFT"
    REJECT_RULE_DRAFT = "REJECT_RULE_DRAFT"
    ACCEPT_UNKNOWN_ATTRIBUTION = "ACCEPT_UNKNOWN_ATTRIBUTION"
    DISMISS_WITH_NOTE = "DISMISS_WITH_NOTE"


ReviewActionStatus = Literal["APPLIED", "FAILED", "NO_OP"]


class ReviewQueueItem(BaseModel):
    """One reviewer action surfaced from diagnostics, recognition, or governance artifacts."""

    item_id: str
    item_type: ReviewQueueItemType
    priority: ReviewQueuePriority
    project_id: str | None = None
    prompt_id: str | None = None
    attempt_id: str | None = None
    track_id: str | None = None
    detection_id: str | None = None
    player_key: str | None = None
    reason: str
    recommended_action: str
    status: ReviewQueueStatus = "OPEN"
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None
    allowed_actions: list[ReviewActionType] = Field(default_factory=list)


class ReviewActionRequest(BaseModel):
    action_type: ReviewActionType
    note: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewActionLog(BaseModel):
    action_id: str
    item_id: str
    item_type: ReviewQueueItemType
    action_type: ReviewActionType
    project_id: str | None = None
    target_ref: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    note: str | None = None
    status: ReviewActionStatus
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ReviewActionResponse(BaseModel):
    item: ReviewQueueItem
    action: ReviewActionLog


class ReviewBatchActionRequest(BaseModel):
    item_ids: list[str] = Field(min_length=1)
    action_type: ReviewActionType
    note: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewBatchActionItemResult(BaseModel):
    item_id: str
    success: bool
    item: ReviewQueueItem | None = None
    action: ReviewActionLog | None = None
    error_code: str | None = None
    error_message: str | None = None


class ReviewBatchActionResponse(BaseModel):
    requested_count: int
    succeeded_count: int
    failed_count: int
    results: list[ReviewBatchActionItemResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReviewQueueGenerateResponse(BaseModel):
    """Response returned after rebuilding open review queue candidates."""

    items: list[ReviewQueueItem] = Field(default_factory=list)
    generated_count: int = 0
    open_count: int = 0
    resolved_count: int = 0
    dismissed_count: int = 0


class UpdateReviewQueueItemRequest(BaseModel):
    status: ReviewQueueStatus
