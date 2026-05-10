"""Local JSON/JSONL dataset models for future ML training exports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import utc_now
from .quiz import CourtRoleTarget, DecisionQuizOption, QuizQuestionMode, SituationType, UserRole
from .source import VideoSourceRecord

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
TrainingLabelSource = Literal["TRACKING_REVIEW", "MANUAL", "HEURISTIC", "QUIZ_AUTHOR", "EXPECTED_VALUE", "QUIZ_ATTEMPT"]
DatasetType = Literal["recognition", "decision", "player_value"]
DecisionOptionTrainingLabelValue = Literal["GOOD_DECISION", "BAD_DECISION"]
DecisionAttemptTrainingLabelValue = Literal["GOOD_READ", "ACCEPTABLE_READ", "BAD_READ", "MISSED_READ"]


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


class DecisionOptionTrainingLabel(BaseModel):
    project_id: str
    prompt_id: str
    option_id: str
    label: DecisionOptionTrainingLabelValue
    source: TrainingLabelSource
    created_at: datetime = Field(default_factory=utc_now)
    rationale: str
    trace: dict[str, Any] = Field(default_factory=dict)


class CuratedTrainingSample(BaseModel):
    sample_id: str
    dataset_type: DatasetType
    sample_type: str
    project_id: str
    label: str
    source: TrainingLabelSource
    trace: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CuratedTrainingLabel(BaseModel):
    sample_id: str
    dataset_type: DatasetType
    target_type: str
    target_id: str
    project_id: str
    label: str
    source: TrainingLabelSource
    rationale: str
    trace: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


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


class DecisionEventsBuildSummary(BaseModel):
    event_count: int = 0
    avg_raw_score: float = 0.0
    avg_role_adjusted_score: float = 0.0
    opportunity_cost_avg: float = 0.0


class SkippedProject(BaseModel):
    project_id: str
    name: str | None = None
    reason: str


class DatasetManifest(BaseModel):
    dataset_type: DatasetType
    schema_version: str = "1.0"
    sample_count: int = 0
    label_count: int = 0
    project_count: int = 0
    included_project_count: int = 0
    skipped_project_count: int = 0
    skipped_projects: list[SkippedProject] = Field(default_factory=list)
    exported_at: datetime = Field(default_factory=utc_now)
    storage_paths: dict[str, str] = Field(default_factory=dict)
    positive_sample_count: int = 0
    negative_sample_count: int = 0
    positive_negative_ratio: float | None = None
    source_project_ids: list[str] = Field(default_factory=list)
    skipped_project_ids: list[str] = Field(default_factory=list)
    label_distribution: dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class DatasetSummary(BaseModel):
    dataset_type: DatasetType
    sample_count: int = 0
    label_count: int = 0
    project_count: int = 0
    last_exported_at: datetime | None = None
    storage_paths: dict[str, str] = Field(default_factory=dict)
    positive_sample_count: int = 0
    negative_sample_count: int = 0
    positive_negative_ratio: float | None = None
    label_distribution: dict[str, int] = Field(default_factory=dict)


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
    source: VideoSourceRecord | None = None


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
