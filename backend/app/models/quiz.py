"""Decision Arrow Quiz MVP models.

Storage paths:
- backend/data/projects/{project_id}/quiz_prompts.json
- backend/data/projects/{project_id}/quiz_attempts.json
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import utc_now

ActionType = Literal["PASS", "DRIVE", "SHOT", "RESET", "HOLD"]


class DecisionArrowPoint(BaseModel):
    """Normalized image point for an arrow endpoint."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class DecisionOption(BaseModel):
    """One selectable arrow decision option."""

    option_id: str
    label: str
    action_type: ActionType
    start: DecisionArrowPoint
    end: DecisionArrowPoint
    expected_value: float | None = None
    is_correct: bool = False
    explanation: str

    @field_validator("option_id", "label", "explanation")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class QuizPrompt(BaseModel):
    """Persisted still-frame decision prompt with 2-5 arrow options."""

    project_id: str
    prompt_id: str
    question: str
    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_url: str | None = None
    image_path: str | None = None
    options: list[DecisionOption] = Field(min_length=2, max_length=5)
    explanation: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("project_id", "prompt_id", "question", "frame_id", "explanation")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_single_correct_option(self) -> "QuizPrompt":
        correct_options = [option for option in self.options if option.is_correct]
        if len(correct_options) != 1:
            raise ValueError("exactly one option must be marked correct")
        option_ids = [option.option_id for option in self.options]
        if len(set(option_ids)) != len(option_ids):
            raise ValueError("option_id values must be unique")
        return self


class CreateQuizPromptRequest(BaseModel):
    """Request body for creating a quiz prompt."""

    question: str
    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_url: str | None = None
    image_path: str | None = None
    options: list[DecisionOption] = Field(min_length=2, max_length=5)
    explanation: str

    @field_validator("question", "frame_id", "explanation")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_single_correct_option(self) -> "CreateQuizPromptRequest":
        correct_options = [option for option in self.options if option.is_correct]
        if len(correct_options) != 1:
            raise ValueError("exactly one option must be marked correct")
        option_ids = [option.option_id for option in self.options]
        if len(set(option_ids)) != len(option_ids):
            raise ValueError("option_id values must be unique")
        return self


class QuizAttemptRequest(BaseModel):
    selected_option_id: str

    @field_validator("selected_option_id")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class QuizAttemptResponse(BaseModel):
    prompt_id: str
    selected_option_id: str
    correct_option_id: str
    is_correct: bool
    selected_expected_value: float | None = None
    correct_expected_value: float | None = None
    opportunity_cost: float | None = None
    selected_explanation: str
    correct_explanation: str
    summary_explanation: str


class QuizAttemptRecord(QuizAttemptResponse):
    attempt_id: str
    project_id: str
    attempted_at: datetime = Field(default_factory=utc_now)


# Backward-compatible extension-point names retained for imports/tests that may
# still refer to the original lightweight quiz models.
DecisionDirection = Literal["left", "right", "up", "down", "hold", "pass", "shoot", "drive", "unknown"]


class FreezeFrame(BaseModel):
    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_path: str | None = None
    video_asset_id: str | None = None
    width: int | None = None
    height: int | None = None
    source_track_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionAnswer(BaseModel):
    answer_id: str
    prompt_id: str
    selected_option_id: str
    respondent_id: str | None = None
    answered_at: datetime = Field(default_factory=utc_now)
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
