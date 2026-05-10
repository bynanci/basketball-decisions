"""Decision Arrow Quiz MVP models.

Storage paths:
- backend/data/projects/{project_id}/quiz_prompts.json
- backend/data/projects/{project_id}/quiz_attempts.json
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, FiniteFloat, field_validator, model_validator

from .base import utc_now

ActionType = Literal["PASS", "DRIVE", "SHOT", "RESET", "HOLD"]
CourtRoleTarget = Literal[
    "BALL_HANDLER",
    "OFF_BALL_SHOOTER",
    "ROLLER",
    "SCREENER",
    "ON_BALL_DEFENDER",
    "HELP_DEFENDER",
    "LOW_MAN",
    "TRAILER",
    "WEAK_SIDE_WING",
]
SituationType = Literal[
    "PICK_AND_ROLL",
    "SHORT_ROLL",
    "SPOT_UP",
    "CLOSEOUT_ATTACK",
    "TRANSITION_3_ON_2",
    "LATE_CLOCK",
    "POST_DOUBLE",
    "DRIVE_AND_KICK",
    "HELP_ROTATION",
    "LOW_MAN_DECISION",
    "OFF_BALL_RELOCATION",
]
QuizPromptMode = Literal["STILL_FRAME", "VIDEO_FREEZE"]
QuizQuestionMode = Literal["FREEZE_FRAME", "QUICK_DECISION", "ROLE_READ"]
QuizScoringMode = Literal["EXPECTED_VALUE", "CORRECTNESS_ONLY"]
UserRole = Literal["COACH", "PLAYER", "ANALYST", "FAN"]


class DecisionArrowPoint(BaseModel):
    """Normalized image point for an arrow endpoint."""

    x: FiniteFloat = Field(ge=0, le=1)
    y: FiniteFloat = Field(ge=0, le=1)


class DecisionRoleFeedback(BaseModel):
    """Optional role-specific feedback for one quiz decision option."""

    coach: str | None = None
    player: str | None = None
    analyst: str | None = None
    fan: str | None = None

    @field_validator("coach", "player", "analyst", "fan")
    @classmethod
    def normalize_optional_feedback(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class DecisionQuizOption(BaseModel):
    """One selectable arrow decision option."""

    option_id: str
    label: str
    action_type: ActionType
    start: DecisionArrowPoint
    end: DecisionArrowPoint
    expected_value: FiniteFloat | None = None
    is_correct: bool = False
    explanation: str
    role_feedback: DecisionRoleFeedback | None = None

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
    court_role_target: CourtRoleTarget
    situation_type: SituationType
    user_role_targets: list[CourtRoleTarget] = Field(default_factory=list)
    role_instruction: str | None = None
    frame_id: str
    frame_index: int
    timestamp_seconds: FiniteFloat
    image_url: str | None = None
    image_path: str | None = None
    video_asset_id: str | None = None
    clip_start_seconds: FiniteFloat | None = Field(default=None, ge=0)
    freeze_frame_seconds: FiniteFloat | None = Field(default=None, ge=0)
    clip_end_seconds: FiniteFloat | None = Field(default=None, ge=0)
    mode: QuizPromptMode = "STILL_FRAME"
    question_mode: QuizQuestionMode = "FREEZE_FRAME"
    time_limit_ms: int | None = Field(default=None, ge=1)
    options: list[DecisionQuizOption] = Field(min_length=2, max_length=5)
    explanation: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def hydrate_legacy_role_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                "court_role_target": "BALL_HANDLER",
                "situation_type": "PICK_AND_ROLL",
                "user_role_targets": [],
                "role_instruction": None,
                "question_mode": "FREEZE_FRAME",
                "time_limit_ms": None,
                **data,
            }
        return data

    @field_validator("project_id", "prompt_id", "question", "frame_id", "explanation")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("role_instruction")
    @classmethod
    def normalize_optional_role_instruction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_single_correct_option(self) -> "QuizPrompt":
        correct_options = [option for option in self.options if option.is_correct]
        if len(correct_options) != 1:
            raise ValueError("exactly one option must be marked correct")
        option_ids = [option.option_id for option in self.options]
        if len(set(option_ids)) != len(option_ids):
            raise ValueError("option_id values must be unique")
        if self.mode == "VIDEO_FREEZE":
            freeze_at = self.freeze_frame_seconds if self.freeze_frame_seconds is not None else self.timestamp_seconds
            if self.clip_start_seconds is not None and self.clip_start_seconds > freeze_at:
                raise ValueError("clip_start_seconds must be less than or equal to freeze_frame_seconds")
            if self.clip_end_seconds is not None and self.clip_end_seconds < freeze_at:
                raise ValueError("clip_end_seconds must be greater than or equal to freeze_frame_seconds")
        if self.question_mode == "QUICK_DECISION" and self.time_limit_ms is None:
            raise ValueError("time_limit_ms must be greater than 0 for QUICK_DECISION prompts")
        return self


class CreateQuizPromptRequest(BaseModel):
    """Request body for creating a quiz prompt."""

    question: str
    court_role_target: CourtRoleTarget
    situation_type: SituationType
    user_role_targets: list[CourtRoleTarget] = Field(default_factory=list)
    role_instruction: str | None = None
    frame_id: str
    frame_index: int
    timestamp_seconds: FiniteFloat
    image_url: str | None = None
    image_path: str | None = None
    video_asset_id: str | None = None
    clip_start_seconds: FiniteFloat | None = Field(default=None, ge=0)
    freeze_frame_seconds: FiniteFloat | None = Field(default=None, ge=0)
    clip_end_seconds: FiniteFloat | None = Field(default=None, ge=0)
    mode: QuizPromptMode = "STILL_FRAME"
    question_mode: QuizQuestionMode = "FREEZE_FRAME"
    time_limit_ms: int | None = Field(default=None, ge=1)
    options: list[DecisionQuizOption] = Field(min_length=2, max_length=5)
    explanation: str

    @field_validator("question", "frame_id", "explanation")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("role_instruction")
    @classmethod
    def normalize_optional_role_instruction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_single_correct_option(self) -> "CreateQuizPromptRequest":
        correct_options = [option for option in self.options if option.is_correct]
        if len(correct_options) != 1:
            raise ValueError("exactly one option must be marked correct")
        option_ids = [option.option_id for option in self.options]
        if len(set(option_ids)) != len(option_ids):
            raise ValueError("option_id values must be unique")
        if self.mode == "VIDEO_FREEZE":
            freeze_at = self.freeze_frame_seconds if self.freeze_frame_seconds is not None else self.timestamp_seconds
            if self.clip_start_seconds is not None and self.clip_start_seconds > freeze_at:
                raise ValueError("clip_start_seconds must be less than or equal to freeze_frame_seconds")
            if self.clip_end_seconds is not None and self.clip_end_seconds < freeze_at:
                raise ValueError("clip_end_seconds must be greater than or equal to freeze_frame_seconds")
        if self.question_mode == "QUICK_DECISION" and self.time_limit_ms is None:
            raise ValueError("time_limit_ms must be greater than 0 for QUICK_DECISION prompts")
        return self


class QuizAttemptRequest(BaseModel):
    selected_option_id: str | None = None
    user_role: UserRole | None = None
    response_time_ms: int | None = Field(default=None, ge=0)
    timed_out: bool = False

    @field_validator("selected_option_id")
    @classmethod
    def require_non_empty_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_timeout_selection(self) -> "QuizAttemptRequest":
        if not self.timed_out and self.selected_option_id is None:
            raise ValueError("selected_option_id is required unless timed_out is true")
        return self


class QuizAttemptResponse(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def hydrate_legacy_scoring(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "score" not in data and "is_correct" in data:
                data = {**data, "score": 100 if data["is_correct"] else 0}
            if "scoring_mode" not in data:
                data = {**data, "scoring_mode": "CORRECTNESS_ONLY"}
            if "selected_role_feedback" not in data and "selected_explanation" in data:
                data = {**data, "selected_role_feedback": data["selected_explanation"]}
            if "correct_role_feedback" not in data and "correct_explanation" in data:
                data = {**data, "correct_role_feedback": data["correct_explanation"]}
        return data

    prompt_id: str
    selected_option_id: str | None = None
    correct_option_id: str
    is_correct: bool
    selected_expected_value: FiniteFloat | None = None
    correct_expected_value: FiniteFloat | None = None
    opportunity_cost: FiniteFloat | None = None
    score: int = Field(ge=0, le=100)
    scoring_mode: QuizScoringMode
    selected_explanation: str
    correct_explanation: str
    selected_role_feedback: str
    correct_role_feedback: str
    summary_explanation: str
    response_time_ms: int | None = Field(default=None, ge=0)
    timed_out: bool = False


class QuizAttemptRecord(QuizAttemptResponse):
    attempt_id: str
    project_id: str
    user_role: UserRole | None = None
    attempted_at: datetime = Field(default_factory=utc_now)


# Backward-compatible extension-point names retained for imports/tests that may
# still refer to the original lightweight quiz models.
DecisionOption = DecisionQuizOption

DecisionDirection = Literal["left", "right", "up", "down", "hold", "pass", "shoot", "drive", "unknown"]


class FreezeFrame(BaseModel):
    frame_id: str
    frame_index: int
    timestamp_seconds: FiniteFloat
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
