"""Decision rule draft approval and rule-set lifecycle routes."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter
from pydantic import TypeAdapter, ValidationError

from app.api.common import api_error
from app.models import (
    ApproveDecisionRuleDraftRequest,
    CreateDecisionRuleSetRequest,
    DecisionRule,
    DecisionRuleDraft,
    DecisionRuleSet,
    DecisionRuleSetListResponse,
    UpdateDecisionRuleRequest,
)
from app.models.base import utc_now

router = APIRouter(prefix="/decision-rules", tags=["decision-rules"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REFERENCE_VIDEO_DIR = DATA_DIR / "reference_videos"
DECISION_RULE_DRAFTS_PATH = REFERENCE_VIDEO_DIR / "decision_rule_drafts.json"
DECISION_RULES_DIR = DATA_DIR / "decision_rules"
RULE_SETS_PATH = DECISION_RULES_DIR / "rule_sets.json"
ACTIVE_RULE_SET_PATH = DECISION_RULES_DIR / "active_rule_set.json"

_RULE_DRAFT_ADAPTER = TypeAdapter(list[DecisionRuleDraft])
_RULE_SET_ADAPTER = TypeAdapter(list[DecisionRuleSet])
_ACTIVE_RULE_SET_ADAPTER = TypeAdapter(DecisionRuleSet)


def _read_list(path: Path, adapter):
    if not path.exists():
        return []
    try:
        return adapter.validate_json(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise api_error(
            500,
            "DECISION_RULE_STORAGE_INVALID",
            f"Decision rule storage file '{path.name}' is invalid.",
            {"path": str(path), "error": str(exc)},
            "Fix or remove the local JSON file and retry.",
        ) from exc


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, default=str, indent=2) + "\n", encoding="utf-8")


def _read_drafts() -> list[DecisionRuleDraft]:
    return _read_list(DECISION_RULE_DRAFTS_PATH, _RULE_DRAFT_ADAPTER)


def _write_drafts(drafts: list[DecisionRuleDraft]) -> None:
    _write_json(DECISION_RULE_DRAFTS_PATH, [draft.model_dump(mode="json") for draft in drafts])


def _read_rule_sets() -> list[DecisionRuleSet]:
    return _read_list(RULE_SETS_PATH, _RULE_SET_ADAPTER)


def _write_rule_sets(rule_sets: list[DecisionRuleSet]) -> None:
    _write_json(RULE_SETS_PATH, [rule_set.model_dump(mode="json") for rule_set in rule_sets])
    active_rule_set = next((rule_set for rule_set in rule_sets if rule_set.active), None)
    if active_rule_set:
        _write_active_rule_set(active_rule_set)


def _read_active_rule_set() -> DecisionRuleSet | None:
    if not ACTIVE_RULE_SET_PATH.exists():
        return next((rule_set for rule_set in _read_rule_sets() if rule_set.active), None)
    try:
        content = ACTIVE_RULE_SET_PATH.read_text(encoding="utf-8")
        if json.loads(content) is None:
            return next((rule_set for rule_set in _read_rule_sets() if rule_set.active), None)
        return _ACTIVE_RULE_SET_ADAPTER.validate_json(content)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise api_error(
            500,
            "ACTIVE_RULE_SET_STORAGE_INVALID",
            "The active decision rule set file is invalid.",
            {"path": str(ACTIVE_RULE_SET_PATH), "error": str(exc)},
            "Fix or remove active_rule_set.json and retry.",
        ) from exc


def _write_active_rule_set(rule_set: DecisionRuleSet) -> None:
    _write_json(ACTIVE_RULE_SET_PATH, rule_set.model_dump(mode="json"))


def _get_or_create_target_rule_set(rule_set_id: str | None) -> tuple[list[DecisionRuleSet], int]:
    rule_sets = _read_rule_sets()
    if rule_set_id:
        for index, rule_set in enumerate(rule_sets):
            if rule_set.rule_set_id == rule_set_id:
                return rule_sets, index
        raise api_error(404, "RULE_SET_NOT_FOUND", "Decision rule set was not found.", {"rule_set_id": rule_set_id}, "Choose an existing rule set or omit rule_set_id to use the active set.")

    for index, rule_set in enumerate(rule_sets):
        if rule_set.active:
            return rule_sets, index

    now = utc_now()
    rule_set = DecisionRuleSet(rule_set_id=f"rule-set-{uuid4().hex}", name="Default Decision Rules", version=1, active=True, created_at=now, updated_at=now)
    rule_sets.append(rule_set)
    return rule_sets, len(rule_sets) - 1


def _find_rule_set_for_rule(rule_sets: list[DecisionRuleSet], rule_id: str) -> tuple[int, int]:
    for rule_set_index, rule_set in enumerate(rule_sets):
        for rule_index, rule in enumerate(rule_set.rules):
            if rule.rule_id == rule_id:
                return rule_set_index, rule_index
    raise api_error(404, "RULE_NOT_FOUND", "Decision rule was not found.", {"rule_id": rule_id}, "Check the rule ID and retry.")


@router.get("/drafts", response_model=list[DecisionRuleDraft])
def list_decision_rule_drafts() -> list[DecisionRuleDraft]:
    return _read_drafts()


@router.post("/drafts/{draft_id}/approve", response_model=DecisionRule)
def approve_decision_rule_draft(draft_id: str, request: ApproveDecisionRuleDraftRequest | None = None) -> DecisionRule:
    payload = request or ApproveDecisionRuleDraftRequest()
    drafts = _read_drafts()
    draft_index = next((index for index, draft in enumerate(drafts) if draft.draft_id == draft_id), None)
    if draft_index is None:
        raise api_error(404, "RULE_DRAFT_NOT_FOUND", "Decision rule draft was not found.", {"draft_id": draft_id}, "Create a rule draft before approving it.")
    draft = drafts[draft_index]
    if draft.status != "DRAFT":
        raise api_error(409, "RULE_DRAFT_ALREADY_REVIEWED", "Decision rule draft has already been reviewed.", {"draft_id": draft_id, "status": draft.status}, "Only DRAFT decision rules can be approved.")

    now = utc_now()
    rule = DecisionRule(
        rule_id=f"rule-{uuid4().hex}",
        source_draft_id=draft.draft_id,
        court_role=draft.court_role,
        situation_type=draft.situation_type,
        condition_text=draft.condition_text,
        positive_cue=draft.positive_cue,
        negative_cue=draft.negative_cue,
        weight=draft.suggested_weight,
        explanation=draft.explanation,
        status="ACTIVE",
        created_at=now,
        updated_at=now,
        approved_at=now,
        approved_by=payload.approved_by,
    )
    rule_sets, target_index = _get_or_create_target_rule_set(payload.rule_set_id)
    target_rule_set = rule_sets[target_index]
    target_rule_set.rules.append(rule)
    target_rule_set.updated_at = now
    rule_sets[target_index] = target_rule_set

    drafts[draft_index] = draft.model_copy(update={"status": "APPROVED", "updated_at": now})
    _write_rule_sets(rule_sets)
    _write_drafts(drafts)
    return rule


@router.post("/drafts/{draft_id}/reject", response_model=DecisionRuleDraft)
def reject_decision_rule_draft(draft_id: str) -> DecisionRuleDraft:
    drafts = _read_drafts()
    for index, draft in enumerate(drafts):
        if draft.draft_id == draft_id:
            if draft.status != "DRAFT":
                raise api_error(409, "RULE_DRAFT_ALREADY_REVIEWED", "Decision rule draft has already been reviewed.", {"draft_id": draft_id, "status": draft.status}, "Only DRAFT decision rules can be rejected.")
            updated = draft.model_copy(update={"status": "REJECTED", "updated_at": utc_now()})
            drafts[index] = updated
            _write_drafts(drafts)
            return updated
    raise api_error(404, "RULE_DRAFT_NOT_FOUND", "Decision rule draft was not found.", {"draft_id": draft_id}, "Check the draft ID and retry.")


@router.get("/rule-sets", response_model=DecisionRuleSetListResponse)
def list_rule_sets() -> DecisionRuleSetListResponse:
    return DecisionRuleSetListResponse(rule_sets=_read_rule_sets(), active_rule_set=_read_active_rule_set())


@router.post("/rule-sets", response_model=DecisionRuleSet)
def create_rule_set(request: CreateDecisionRuleSetRequest) -> DecisionRuleSet:
    now = utc_now()
    rule_sets = _read_rule_sets()
    new_rule_set = DecisionRuleSet(rule_set_id=f"rule-set-{uuid4().hex}", name=request.name, version=request.version, active=request.active, created_at=now, updated_at=now)
    if request.active:
        rule_sets = [rule_set.model_copy(update={"active": False, "updated_at": now}) for rule_set in rule_sets]
    rule_sets.append(new_rule_set)
    _write_rule_sets(rule_sets)
    if new_rule_set.active:
        _write_active_rule_set(new_rule_set)
    return new_rule_set


@router.put("/rule-sets/{rule_set_id}/activate", response_model=DecisionRuleSet)
def activate_rule_set(rule_set_id: str) -> DecisionRuleSet:
    now = utc_now()
    rule_sets = _read_rule_sets()
    activated: DecisionRuleSet | None = None
    updated_rule_sets: list[DecisionRuleSet] = []
    for rule_set in rule_sets:
        updated = rule_set.model_copy(update={"active": rule_set.rule_set_id == rule_set_id, "updated_at": now if rule_set.rule_set_id == rule_set_id or rule_set.active else rule_set.updated_at})
        if updated.rule_set_id == rule_set_id:
            activated = updated
        updated_rule_sets.append(updated)
    if activated is None:
        raise api_error(404, "RULE_SET_NOT_FOUND", "Decision rule set was not found.", {"rule_set_id": rule_set_id}, "Check the rule set ID and retry.")
    _write_rule_sets(updated_rule_sets)
    _write_active_rule_set(activated)
    return activated


@router.put("/rules/{rule_id}", response_model=DecisionRule)
def update_rule(rule_id: str, request: UpdateDecisionRuleRequest) -> DecisionRule:
    rule_sets = _read_rule_sets()
    rule_set_index, rule_index = _find_rule_set_for_rule(rule_sets, rule_id)
    now = utc_now()
    existing = rule_sets[rule_set_index].rules[rule_index]
    changes = {key: value for key, value in request.model_dump().items() if value is not None}
    updated = existing.model_copy(update={**changes, "updated_at": now})
    rule_sets[rule_set_index].rules[rule_index] = updated
    rule_sets[rule_set_index].updated_at = now
    _write_rule_sets(rule_sets)
    return updated
