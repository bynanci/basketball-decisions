"""Decision quiz extension-point Pydantic models.

Future storage path:
- backend/data/projects/{project_id}/quiz_prompts.json
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import ProjectArtifact, utc_now

DecisionDirection = Literal["left", "right", "up", "down", "hold", "pass", "shoot", "drive", "unknown"]


class FreezeFrame(BaseModel):
    """A traceable still-frame reference used to ask one decision prompt."""

    frame_id: str
    frame_index: int
    timestamp_seconds: float
    image_path: str | None = None
    video_asset_id: str | None = None
    width: int | None = None
    height: int | None = None
    source_track_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionOption(BaseModel):
    """One selectable decision direction or action for a quiz prompt."""

    option_id: str
    label: str
    direction: DecisionDirection = "unknown"
    description: str | None = None
    target_player_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionAnswer(BaseModel):
    """A recorded user answer without scoring or coach-label interpretation."""

    answer_id: str
    prompt_id: str
    selected_option_id: str
    respondent_id: str | None = None
    answered_at: datetime = Field(default_factory=utc_now)
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuizPrompt(ProjectArtifact):
    """Persisted decision prompt stored in quiz_prompts.json.

    This model is intentionally an extension point only: it traces the source
    frame/options/answers, but does not define scoring, coach annotation joins,
    or multi-player decision semantics for the MVP.
    """

    prompt_id: str
    question: str
    freeze_frame: FreezeFrame
    options: list[DecisionOption] = Field(default_factory=list)
    answers: list[DecisionAnswer] = Field(default_factory=list)
    coach_annotation_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
