"""Guided workflow orchestration models for local artifact workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now

WorkflowTemplateKey = Literal[
    "BUILD_PLAYER_VALUE",
    "IMPROVE_DATA_QUALITY",
    "TRAINING_RECOMMENDATION",
    "COACH_REPORT",
    "MODEL_GOVERNANCE",
]
WorkflowStatus = Literal["NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETED"]
WorkflowStepStatus = Literal["PENDING", "READY", "BLOCKED", "COMPLETED", "SKIPPED"]
WorkflowPrerequisiteKey = Literal[
    "has_tracking",
    "has_tracking_review",
    "has_player_aliases",
    "has_decision_events",
    "has_player_value",
    "has_dataset_health",
    "has_active_recognition_model",
    "has_drill_recommendations",
    "has_practice_plan",
    "has_practice_execution",
    "has_coach_report",
    "has_open_high_priority_review_items",
]


class WorkflowStartRequest(BaseModel):
    """Request to instantiate a guided workflow from a known template."""

    template_key: WorkflowTemplateKey
    project_id: str | None = None
    player_key: str | None = None
    title: str | None = None
    source_action_id: str | None = None
    context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class WorkflowFromActionRequest(BaseModel):
    """Request to map a dashboard next-best-action into a workflow template."""

    action_id: str
    project_id: str | None = None
    player_key: str | None = None
    title: str | None = None
    context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class WorkflowStepUpdateRequest(BaseModel):
    """Manual workflow step state update; no underlying operation is executed."""

    status: WorkflowStepStatus
    note: str | None = None


class WorkflowPrerequisiteState(BaseModel):
    """A single prerequisite check resolved from local artifacts."""

    key: WorkflowPrerequisiteKey
    label: str
    satisfied: bool
    detail: str
    artifact_path: str | None = None


class WorkflowStep(BaseModel):
    """A guided workflow step that points humans at an existing operation."""

    step_id: str
    title: str
    description: str
    action_label: str
    href: str
    status: WorkflowStepStatus = "PENDING"
    prerequisite_keys: list[WorkflowPrerequisiteKey] = Field(default_factory=list)
    blocking_prerequisite_keys: list[WorkflowPrerequisiteKey] = Field(default_factory=list)
    completion_prerequisite_key: WorkflowPrerequisiteKey | None = None
    notes: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkflowTemplate(BaseModel):
    """Static guided workflow template."""

    template_key: WorkflowTemplateKey
    title: str
    description: str
    steps: list[WorkflowStep]


class Workflow(BaseModel):
    """Persisted guided workflow instance."""

    schema_version: str = "1.0"
    workflow_id: str
    template_key: WorkflowTemplateKey
    title: str
    description: str
    status: WorkflowStatus = "NOT_STARTED"
    project_id: str | None = None
    player_key: str | None = None
    source_action_id: str | None = None
    context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    prerequisites: list[WorkflowPrerequisiteState] = Field(default_factory=list)
    steps: list[WorkflowStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    storage_path: str | None = None


class WorkflowListItem(BaseModel):
    """Compact workflow list item."""

    workflow_id: str
    template_key: WorkflowTemplateKey
    title: str
    status: WorkflowStatus
    project_id: str | None = None
    player_key: str | None = None
    source_action_id: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_step_count: int = 0
    total_step_count: int = 0
    blocked_step_count: int = 0


class WorkflowListResponse(BaseModel):
    """Stored guided workflow index."""

    workflows: list[WorkflowListItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
