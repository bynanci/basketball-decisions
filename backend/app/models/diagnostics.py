"""Explainable diagnostics models for Decision Engine quiz quality."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, FiniteFloat

from .base import utc_now
from .quiz import CourtRoleTarget, QuizQuestionMode, SituationType

DecisionPromptDifficulty = Literal["TOO_EASY", "BALANCED", "TOO_HARD", "INSUFFICIENT_DATA"]


class DecisionPromptDiagnostics(BaseModel):
    prompt_id: str
    project_id: str
    court_role_target: CourtRoleTarget
    situation_type: SituationType
    question_mode: QuizQuestionMode
    attempt_count: int = Field(ge=0)
    correct_rate: FiniteFloat = Field(ge=0, le=1)
    avg_score: FiniteFloat = Field(ge=0, le=100)
    avg_role_adjusted_score: FiniteFloat = Field(ge=0, le=100)
    avg_opportunity_cost: FiniteFloat = Field(ge=0)
    timeout_rate: FiniteFloat = Field(ge=0, le=1)
    most_selected_wrong_option_id: str | None = None
    difficulty: DecisionPromptDifficulty
    suspected_label_issue: bool = False
    reasons: list[str] = Field(default_factory=list)


class DecisionRoleDiagnostics(BaseModel):
    court_role: CourtRoleTarget
    prompt_count: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    avg_score: FiniteFloat = Field(ge=0, le=100)
    avg_opportunity_cost: FiniteFloat = Field(ge=0)
    timeout_rate: FiniteFloat = Field(ge=0, le=1)
    weakest_situation_types: list[SituationType] = Field(default_factory=list)


class DecisionSituationDiagnostics(BaseModel):
    situation_type: SituationType
    prompt_count: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    avg_score: FiniteFloat = Field(ge=0, le=100)
    avg_opportunity_cost: FiniteFloat = Field(ge=0)
    timeout_rate: FiniteFloat = Field(ge=0, le=1)


class DecisionDiagnosticsGlobalSummary(BaseModel):
    prompt_count: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    too_easy_count: int = Field(ge=0)
    too_hard_count: int = Field(ge=0)
    balanced_count: int = Field(ge=0)
    insufficient_data_count: int = Field(ge=0)
    suspected_label_issue_count: int = Field(ge=0)
    high_cost_prompt_count: int = Field(ge=0)
    time_pressure_prompt_count: int = Field(ge=0)
    analytics_only: bool = True


class DecisionDiagnosticsReport(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    prompt_diagnostics: list[DecisionPromptDiagnostics] = Field(default_factory=list)
    role_diagnostics: list[DecisionRoleDiagnostics] = Field(default_factory=list)
    situation_diagnostics: list[DecisionSituationDiagnostics] = Field(default_factory=list)
    global_summary: DecisionDiagnosticsGlobalSummary
