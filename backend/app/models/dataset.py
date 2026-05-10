"""Local JSON/JSONL dataset models for future ML training exports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import utc_now
from .quiz import CourtRoleTarget, DecisionQuizOption, QuizQuestionMode, SituationType, UserRole

DetectionTrainingLabelValue = Literal[
    "PLAYER",
    "REFEREE",
    "COACH",
    "BENCH_PLAYER",
    "SPECTATOR",
    "BALL",
    "UNKNOWN",
    "FALSE_POSITIVE",
]
TrackTrainingLabelValue = Literal[
    "VALID_PLAYER_TRACK",
    "FALSE_POSITIVE_TRACK",
    "BROKEN_TRACK",
    "MERGED_PLAYERS",
    "LOST_TRACK",
    "OCCLUDED",
]
TrainingLabelSource = Literal["TRACKING_REVIEW", "MANUAL", "HEURISTIC"]
DatasetType = Literal["recognition", "decision", "player_value"]


class DetectionTrainingLabel(BaseModel):
    project_id: str
    frame_id: str
    frame_index: int
    detection_id: str
    track_id: str | None = None
    label: DetectionTrainingLabelValue
    source: TrainingLabelSource
    created_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class TrackTrainingLabel(BaseModel):
    project_id: str
    track_id: str
    label: TrackTrainingLabelValue
    source: TrainingLabelSource
    created_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class DecisionTrainingSample(BaseModel):
    project_id: str
    prompt_id: str
    frame_id: str
    frame_index: int
    court_role_target: CourtRoleTarget
    situation_type: SituationType
    question_mode: QuizQuestionMode
    option_count: int
    correct_option_id: str
    options: list[DecisionQuizOption]
    explanation: str


class DecisionAttemptTrainingLabel(BaseModel):
    project_id: str
    prompt_id: str
    selected_option_id: str | None = None
    correct_option_id: str
    is_correct: bool
    score: int
    opportunity_cost: float | None = None
    response_time_ms: int | None = None
    timed_out: bool = False
    user_role: UserRole | None = None
    created_at: datetime = Field(default_factory=utc_now)


class DatasetManifest(BaseModel):
    dataset_type: DatasetType
    schema_version: str = "1.0"
    sample_count: int = 0
    label_count: int = 0
    project_count: int = 0
    exported_at: datetime = Field(default_factory=utc_now)
    storage_paths: dict[str, str] = Field(default_factory=dict)
    notes: str | None = None


class DatasetSummary(BaseModel):
    dataset_type: DatasetType
    sample_count: int = 0
    label_count: int = 0
    project_count: int = 0
    last_exported_at: datetime | None = None
    storage_paths: dict[str, str] = Field(default_factory=dict)


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class LocalLabProjectArtifact(BaseModel):
    project_id: str
    name: str
    has_video: bool
    frame_count: int
    has_calibration: bool
    has_tracking: bool
    has_tracking_review: bool
    has_cleaned_tracking: bool
    has_projected_tracks: bool
    quiz_prompt_count: int
    quiz_attempt_count: int
    updated_at: datetime | None = None


class LocalLabProjectsResponse(BaseModel):
    projects: list[LocalLabProjectArtifact]


class RecognitionTrainingSample(BaseModel):
    sample_type: Literal["detection", "track"]
    project_id: str
    frame_id: str | None = None
    frame_index: int | None = None
    detection_id: str | None = None
    track_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
