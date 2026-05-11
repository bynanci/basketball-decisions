"""Decision rule lifecycle models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import utc_now
from .quiz import CourtRoleTarget, SituationType

DecisionRuleStatus = Literal["ACTIVE", "DISABLED"]


class DecisionRule(BaseModel):
    rule_id: str
    source_draft_id: str | None = None
    court_role: CourtRoleTarget
    situation_type: SituationType
    condition_text: str
    positive_cue: str
    negative_cue: str
    weight: float = 1.0
    explanation: str
    status: DecisionRuleStatus = "ACTIVE"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime = Field(default_factory=utc_now)
    approved_by: str | None = None


class DecisionRuleSet(BaseModel):
    rule_set_id: str
    name: str
    version: int = 1
    rules: list[DecisionRule] = Field(default_factory=list)
    active: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DecisionRuleSetListResponse(BaseModel):
    rule_sets: list[DecisionRuleSet]
    active_rule_set: DecisionRuleSet | None = None


class ApproveDecisionRuleDraftRequest(BaseModel):
    rule_set_id: str | None = None
    approved_by: str | None = None


class CreateDecisionRuleSetRequest(BaseModel):
    name: str
    version: int = 1
    active: bool = False


class UpdateDecisionRuleRequest(BaseModel):
    condition_text: str | None = None
    positive_cue: str | None = None
    negative_cue: str | None = None
    weight: float | None = None
    explanation: str | None = None
    status: DecisionRuleStatus | None = None
