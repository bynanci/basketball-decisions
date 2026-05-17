"""Unified active-learning review queue routes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import TypeAdapter, ValidationError

from app.api.common import DATA_DIR, api_error, read_json, require_project_dir, write_json_model
from app.api.decision_rules import approve_decision_rule_draft, reject_decision_rule_draft
from app.models import (
    Calibration,
    DecisionDiagnosticsReport,
    DecisionEvent,
    DecisionRuleDraft,
    ApproveDecisionRuleDraftRequest,
    PlayerAlias,
    PlayerAliasListResponse,
    PlayerValueBuildResponse,
    ReviewActionLog,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewActionStatus,
    ReviewActionType,
    ReviewQueueGenerateResponse,
    ReviewQueueItem,
    RunTrackingResponse,
    TrackReviewPatch,
    UpdateReviewQueueItemRequest,
)
from app.models.base import utc_now
from app.pipeline.recognition_quality import HIGH_RISK_THRESHOLD, score_project_recognition

router = APIRouter(prefix="/review-queue", tags=["review-queue"])

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATASETS_DIR = APP_DATA_DIR / "datasets"
REVIEW_QUEUE_DIR = APP_DATA_DIR / "review_queue"
REVIEW_QUEUE_PATH = REVIEW_QUEUE_DIR / "review_queue.json"
REVIEW_ACTION_LOG_PATH = REVIEW_QUEUE_DIR / "review_action_log.json"
DECISION_RULE_DRAFTS_PATH = APP_DATA_DIR / "reference_videos" / "decision_rule_drafts.json"
_QUEUE_ADAPTER = TypeAdapter(list[ReviewQueueItem])
_ACTION_LOG_ADAPTER = TypeAdapter(list[ReviewActionLog])
_RULE_DRAFTS_ADAPTER = TypeAdapter(list[DecisionRuleDraft])

LOW_CONFIDENCE_DETECTION_THRESHOLD = 0.35
UNCERTAIN_MODEL_RISK_LOW = 0.4
UNCERTAIN_MODEL_RISK_HIGH = 0.6
HIGH_OPPORTUNITY_COST_THRESHOLD = 0.3


def allowed_actions_for_item(item: ReviewQueueItem) -> list[ReviewActionType]:
    actions_by_type: dict[str, list[ReviewActionType]] = {
        "RECOGNITION_TRACK": [
            ReviewActionType.MARK_TRACK_FALSE_POSITIVE,
            ReviewActionType.MARK_TRACK_VALID_PLAYER,
            ReviewActionType.ASSIGN_TRACK_TO_PLAYER_ALIAS,
        ],
        "RECOGNITION_DETECTION": [ReviewActionType.MARK_TRACK_FALSE_POSITIVE, ReviewActionType.MARK_TRACK_VALID_PLAYER],
        "DECISION_PROMPT": [ReviewActionType.FLAG_PROMPT_LABEL_ISSUE],
        "DECISION_ATTEMPT": [ReviewActionType.MARK_ATTEMPT_TEACHING_CASE],
        "PLAYER_VALUE_ATTRIBUTION": [ReviewActionType.ASSIGN_TRACK_TO_PLAYER_ALIAS, ReviewActionType.ACCEPT_UNKNOWN_ATTRIBUTION, ReviewActionType.OPEN_ALIAS_REVIEW],
        "RULE_DRAFT": [ReviewActionType.APPROVE_RULE_DRAFT, ReviewActionType.REJECT_RULE_DRAFT],
    }
    return [*actions_by_type.get(item.item_type, []), ReviewActionType.DISMISS_WITH_NOTE]


def _with_allowed_actions(item: ReviewQueueItem) -> ReviewQueueItem:
    return item.model_copy(update={"allowed_actions": allowed_actions_for_item(item)})


def _read_action_log() -> list[ReviewActionLog]:
    if not REVIEW_ACTION_LOG_PATH.exists():
        return []
    try:
        return _ACTION_LOG_ADAPTER.validate_json(REVIEW_ACTION_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValidationError):
        return []


def _write_action_log(actions: list[ReviewActionLog]) -> None:
    REVIEW_ACTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_ACTION_LOG_PATH.write_text(json.dumps([action.model_dump(mode="json") for action in actions], indent=2), encoding="utf-8")


def _append_action_log(action: ReviewActionLog) -> None:
    actions = _read_action_log()
    actions.append(action)
    _write_action_log(actions)


def _target_ref(item: ReviewQueueItem) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "project_id": item.project_id,
            "prompt_id": item.prompt_id,
            "attempt_id": item.attempt_id,
            "track_id": item.track_id,
            "detection_id": item.detection_id,
            "player_key": item.player_key,
        }.items()
        if value is not None
    }


def _new_action_log(item: ReviewQueueItem, request: ReviewActionRequest, status: ReviewActionStatus, warnings: list[str] | None = None) -> ReviewActionLog:
    return ReviewActionLog(
        action_id=f"review-action-{uuid4().hex}",
        item_id=item.item_id,
        item_type=item.item_type,
        action_type=request.action_type,
        project_id=item.project_id,
        target_ref=_target_ref(item),
        payload=request.payload,
        note=request.note,
        status=status,
        warnings=warnings or [],
    )


def _write_json_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, default=str, indent=2) + "\n", encoding="utf-8")


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise api_error(422, "INVALID_REVIEW_ACTION_ARTIFACT", f"Review action artifact '{path.name}' is not valid JSON.", {"path": str(path), "error": str(exc)}, "Fix or remove the local JSON file and retry.") from exc
    return data if isinstance(data, list) else []


def _project_dirs() -> list[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.parent for path in DATA_DIR.glob("*/project.json"))


def _queue_item_id(item_type: str, *parts: str | None) -> str:
    source_key = ":".join([item_type, *(part or "" for part in parts)])
    digest = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:16]
    return f"rq-{digest}"


def _read_queue() -> list[ReviewQueueItem]:
    if not REVIEW_QUEUE_PATH.exists():
        return []
    try:
        return [_with_allowed_actions(item) for item in _QUEUE_ADAPTER.validate_json(REVIEW_QUEUE_PATH.read_text(encoding="utf-8"))]
    except (json.JSONDecodeError, ValidationError):
        return []


def _write_queue(items: list[ReviewQueueItem]) -> None:
    REVIEW_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_QUEUE_PATH.write_text(json.dumps([_with_allowed_actions(item).model_dump(mode="json") for item in items], indent=2), encoding="utf-8")


def _existing_item_by_id() -> dict[str, ReviewQueueItem]:
    return {item.item_id: item for item in _read_queue()}


def _with_existing_state(item: ReviewQueueItem, existing: dict[str, ReviewQueueItem]) -> ReviewQueueItem:
    previous = existing.get(item.item_id)
    if previous is None:
        return item
    return item.model_copy(update={"status": previous.status, "created_at": previous.created_at, "resolved_at": previous.resolved_at})


def _review_patch(directory: Path) -> TrackReviewPatch:
    path = directory / "tracking_review_patch.json"
    if not path.exists():
        return TrackReviewPatch()
    try:
        return TrackReviewPatch.model_validate(read_json(path))
    except (json.JSONDecodeError, ValidationError):
        return TrackReviewPatch()


def _recognition_items() -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for directory in _project_dirs():
        project_id = directory.name
        tracking_path = directory / "tracking.json"
        if not tracking_path.exists():
            continue
        try:
            tracking = RunTrackingResponse.model_validate(read_json(tracking_path))
            calibration_path = directory / "calibration.json"
            calibration = Calibration.model_validate(read_json(calibration_path)) if calibration_path.exists() else None
            scores = score_project_recognition(project_id, tracking.detections, tracking.tracks, _review_patch(directory), calibration)
        except (json.JSONDecodeError, ValidationError):
            continue

        for score in scores.track_scores:
            if score.false_positive_risk >= HIGH_RISK_THRESHOLD:
                items.append(
                    ReviewQueueItem(
                        item_id=_queue_item_id("RECOGNITION_TRACK", project_id, score.track_id),
                        item_type="RECOGNITION_TRACK",
                        priority="HIGH",
                        project_id=project_id,
                        track_id=score.track_id,
                        reason=f"Track false-positive risk is {score.false_positive_risk:.0%}: {'; '.join(score.reasons) or 'high-risk recognition score.'}",
                        recommended_action="Open tracking review, inspect the track, and exclude or correct it if it is not a player.",
                    )
                )
        for score in scores.detection_scores:
            low_detector_confidence = score.features.confidence <= LOW_CONFIDENCE_DETECTION_THRESHOLD
            uncertain_model_sample = score.scoring_source == "MODEL" and UNCERTAIN_MODEL_RISK_LOW <= score.false_positive_risk <= UNCERTAIN_MODEL_RISK_HIGH
            high_risk = score.false_positive_risk >= HIGH_RISK_THRESHOLD
            if not (high_risk or low_detector_confidence or uncertain_model_sample):
                continue
            priority = "HIGH" if high_risk else "MEDIUM"
            reason_bits = []
            if high_risk:
                reason_bits.append(f"false-positive risk is {score.false_positive_risk:.0%}")
            if low_detector_confidence:
                reason_bits.append(f"detector confidence is {score.features.confidence:.0%}")
            if uncertain_model_sample:
                reason_bits.append(f"model risk is uncertain at {score.false_positive_risk:.0%}")
            items.append(
                ReviewQueueItem(
                    item_id=_queue_item_id("RECOGNITION_DETECTION", project_id, score.detection_id),
                    item_type="RECOGNITION_DETECTION",
                    priority=priority,
                    project_id=project_id,
                    track_id=score.track_id,
                    detection_id=score.detection_id,
                    reason=f"Detection {score.detection_id} needs review because {', '.join(reason_bits)}. {'; '.join(score.reasons)}",
                    recommended_action="Review the frame detection and add/correct a recognition label before using it for training.",
                )
            )
    return items


def _diagnostics_path() -> Path:
    return DATASETS_DIR / "decision" / "decision_diagnostics.json"


def _decision_event_path() -> Path:
    return DATASETS_DIR / "player_value" / "player_decision_events.jsonl"


def _decision_items() -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    path = _diagnostics_path()
    if path.exists():
        try:
            report = DecisionDiagnosticsReport.model_validate(read_json(path))
            for diagnostic in report.prompt_diagnostics:
                if diagnostic.suspected_label_issue:
                    items.append(
                        ReviewQueueItem(
                            item_id=_queue_item_id("DECISION_PROMPT", diagnostic.project_id, diagnostic.prompt_id, "label"),
                            item_type="DECISION_PROMPT",
                            priority="HIGH",
                            project_id=diagnostic.project_id,
                            prompt_id=diagnostic.prompt_id,
                            reason="Suspected label issue from decision diagnostics. " + " ".join(diagnostic.reasons),
                            recommended_action="Audit the prompt's correct option, explanation, expected values, and source evidence.",
                        )
                    )
                elif diagnostic.difficulty == "TOO_HARD":
                    items.append(
                        ReviewQueueItem(
                            item_id=_queue_item_id("DECISION_PROMPT", diagnostic.project_id, diagnostic.prompt_id, "too-hard"),
                            item_type="DECISION_PROMPT",
                            priority="MEDIUM",
                            project_id=diagnostic.project_id,
                            prompt_id=diagnostic.prompt_id,
                            reason="Prompt is classified as TOO_HARD. " + " ".join(diagnostic.reasons),
                            recommended_action="Review prompt clarity, answer choices, role targeting, and whether the teaching point needs scaffolding.",
                        )
                    )
        except (json.JSONDecodeError, ValidationError):
            pass

    event_path = _decision_event_path()
    if event_path.exists():
        for line in event_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = DecisionEvent.model_validate_json(line)
            except ValidationError:
                continue
            if event.opportunity_cost is None or event.opportunity_cost <= HIGH_OPPORTUNITY_COST_THRESHOLD:
                continue
            priority = "HIGH" if event.opportunity_cost >= 0.6 else "MEDIUM"
            items.append(
                ReviewQueueItem(
                    item_id=_queue_item_id("DECISION_ATTEMPT", event.project_id, event.prompt_id, event.attempt_id),
                    item_type="DECISION_ATTEMPT",
                    priority=priority,
                    project_id=event.project_id,
                    prompt_id=event.prompt_id,
                    attempt_id=event.attempt_id,
                    reason=f"Attempt had high opportunity cost ({event.opportunity_cost:.2f}) on a {event.question_mode} prompt.",
                    recommended_action="Inspect the attempt evidence and decide whether the prompt, label, or feedback should be revised.",
                )
            )
    return items


def _player_value_items() -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    path = DATASETS_DIR / "player_value" / "player_value_summary.json"
    if not path.exists():
        return items
    try:
        response = PlayerValueBuildResponse.model_validate(read_json(path))
    except (json.JSONDecodeError, ValidationError):
        return items
    for summary in response.summaries:
        if summary.player_key != "UNKNOWN":
            continue
        items.append(
            ReviewQueueItem(
                item_id=_queue_item_id("PLAYER_VALUE_ATTRIBUTION", summary.project_id, summary.player_key, *summary.trace.decision_event_ids),
                item_type="PLAYER_VALUE_ATTRIBUTION",
                priority="HIGH" if summary.decision_event_count >= 3 else "MEDIUM",
                project_id=summary.project_id,
                player_key=summary.player_key,
                reason=f"Player Value attribution is UNKNOWN for {summary.decision_event_count} decision event(s). {' '.join(summary.warnings)}",
                recommended_action="Assign source tracks to a player alias or confirm the attribution should remain unknown before using this evidence.",
            )
        )
    return items


def _rule_draft_items() -> list[ReviewQueueItem]:
    if not DECISION_RULE_DRAFTS_PATH.exists():
        return []
    try:
        drafts = _RULE_DRAFTS_ADAPTER.validate_json(DECISION_RULE_DRAFTS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValidationError):
        return []
    return [
        ReviewQueueItem(
            item_id=_queue_item_id("RULE_DRAFT", draft.draft_id),
            item_type="RULE_DRAFT",
            priority="MEDIUM",
            prompt_id=draft.draft_id,
            reason=f"Decision rule draft is pending approval for {draft.court_role} / {draft.situation_type}: {draft.condition_text}",
            recommended_action="Approve or reject the reference-derived rule draft from the Decision Rules page.",
        )
        for draft in drafts
        if draft.status == "DRAFT"
    ]


def _generated_items() -> list[ReviewQueueItem]:
    return [*_recognition_items(), *_decision_items(), *_player_value_items(), *_rule_draft_items()]


def _apply_mark_track_false_positive(item: ReviewQueueItem) -> list[str]:
    if not item.project_id:
        raise api_error(422, "REVIEW_ACTION_PROJECT_REQUIRED", "This action requires a project_id on the review item.", {"item_id": item.item_id}, "Regenerate the queue from a project-scoped artifact.")
    directory = require_project_dir(item.project_id)
    patch = _review_patch(directory)
    warnings: list[str] = []
    if item.item_type == "RECOGNITION_TRACK":
        if not item.track_id:
            raise api_error(422, "REVIEW_ACTION_TARGET_REQUIRED", "Track false-positive action requires a track_id.", {"item_id": item.item_id}, "Use a recognition track item with a concrete track_id.")
        if item.track_id not in patch.excluded_track_ids:
            patch.excluded_track_ids.append(item.track_id)
        else:
            warnings.append("Track ID was already excluded in tracking_review_patch.json.")
    elif item.item_type == "RECOGNITION_DETECTION":
        detection_id = item.detection_id
        if not detection_id:
            raise api_error(422, "REVIEW_ACTION_TARGET_REQUIRED", "Detection false-positive action requires a detection_id.", {"item_id": item.item_id}, "Regenerate the review queue so detection IDs are included.")
        if detection_id not in patch.excluded_detection_ids:
            patch.excluded_detection_ids.append(detection_id)
        else:
            warnings.append("Detection ID was already excluded in tracking_review_patch.json.")
    else:
        raise api_error(400, "REVIEW_ACTION_NOT_ALLOWED", "This action is only valid for recognition items.", {"item_type": item.item_type}, "Choose an action from allowed_actions.")
    write_json_model(directory / "tracking_review_patch.json", patch)
    return warnings


def _apply_assign_track_to_player_alias(item: ReviewQueueItem, request: ReviewActionRequest) -> list[str]:
    if not item.project_id:
        raise api_error(422, "REVIEW_ACTION_PROJECT_REQUIRED", "Alias assignment requires a project_id.", {"item_id": item.item_id}, "Use a project-scoped Player Value or recognition track item.")
    directory = require_project_dir(item.project_id)
    player_key = str(request.payload.get("player_key") or "").strip()
    if not player_key:
        raise api_error(422, "PLAYER_ALIAS_KEY_REQUIRED", "ASSIGN_TRACK_TO_PLAYER_ALIAS requires payload.player_key.", {"payload": request.payload}, "Provide the local player_key to assign.")
    requested_track_ids = request.payload.get("track_ids") or ([item.track_id] if item.track_id else [])
    track_ids = [str(track_id).strip() for track_id in requested_track_ids if str(track_id).strip()]
    if not track_ids:
        raise api_error(422, "PLAYER_ALIAS_TRACK_IDS_REQUIRED", "ASSIGN_TRACK_TO_PLAYER_ALIAS requires at least one track_id.", {"payload": request.payload, "item_track_id": item.track_id}, "Provide payload.track_ids or act on an item with track_id.")
    path = directory / "player_aliases.json"
    if path.exists():
        aliases = PlayerAliasListResponse.model_validate(read_json(path))
    else:
        aliases = PlayerAliasListResponse(project_id=item.project_id, aliases=[])

    overlap = [alias for alias in aliases.aliases if alias.player_key != player_key and set(alias.track_ids).intersection(track_ids)]
    if overlap:
        raise api_error(
            409,
            "PLAYER_ALIAS_TRACK_OVERLAP",
            "One or more track IDs already belong to another player alias.",
            {"track_ids": track_ids, "existing_player_keys": [alias.player_key for alias in overlap]},
            "Remove the track from the other alias manually before assigning it here.",
        )

    now = utc_now()
    updated_aliases = []
    found = False
    for alias in aliases.aliases:
        if alias.player_key != player_key:
            updated_aliases.append(alias)
            continue
        found = True
        merged_track_ids = [*alias.track_ids, *(track_id for track_id in track_ids if track_id not in alias.track_ids)]
        updated_aliases.append(
            alias.model_copy(
                update={
                    "track_ids": merged_track_ids,
                    "team_side": request.payload.get("team_side") or alias.team_side,
                    "display_name": request.payload.get("display_name", alias.display_name),
                    "notes": request.note or alias.notes,
                    "updated_at": now,
                }
            )
        )
    if not found:
        updated_aliases.append(
            PlayerAlias(
                player_key=player_key,
                project_id=item.project_id,
                track_ids=track_ids,
                display_name=request.payload.get("display_name"),
                team_side=request.payload.get("team_side") or "UNKNOWN",
                notes=request.note,
                created_at=now,
                updated_at=now,
            )
        )
    write_json_model(path, PlayerAliasListResponse(project_id=item.project_id, aliases=updated_aliases))
    return []


def _apply_prompt_label_issue(item: ReviewQueueItem, request: ReviewActionRequest) -> list[str]:
    if not item.project_id or not item.prompt_id:
        raise api_error(422, "PROMPT_REVIEW_TARGET_REQUIRED", "Prompt label issue actions require project_id and prompt_id.", {"item_id": item.item_id}, "Regenerate the queue from decision diagnostics.")
    directory = require_project_dir(item.project_id)
    path = directory / "prompt_review_notes.json"
    rows = _read_json_list(path)
    rows.append({"prompt_id": item.prompt_id, "reason": request.payload.get("reason") or item.reason, "note": request.note, "created_at": utc_now().isoformat()})
    _write_json_list(path, rows)
    return []


def _apply_teaching_case(item: ReviewQueueItem, request: ReviewActionRequest) -> list[str]:
    if not item.project_id or not item.prompt_id or not item.attempt_id:
        raise api_error(422, "TEACHING_CASE_TARGET_REQUIRED", "Teaching case actions require project_id, prompt_id, and attempt_id.", {"item_id": item.item_id}, "Regenerate the queue from decision events.")
    directory = require_project_dir(item.project_id)
    path = directory / "teaching_cases.json"
    rows = _read_json_list(path)
    rows.append({"project_id": item.project_id, "prompt_id": item.prompt_id, "attempt_id": item.attempt_id, "reason": request.payload.get("reason") or item.reason, "note": request.note, "created_at": utc_now().isoformat()})
    _write_json_list(path, rows)
    return []


def _apply_rule_draft_action(item: ReviewQueueItem, request: ReviewActionRequest) -> list[str]:
    draft_id = item.prompt_id
    if not draft_id:
        raise api_error(422, "RULE_DRAFT_TARGET_REQUIRED", "Rule draft actions require prompt_id to contain the draft_id.", {"item_id": item.item_id}, "Regenerate the queue from rule drafts.")
    if request.action_type == ReviewActionType.APPROVE_RULE_DRAFT:
        approve_decision_rule_draft(
            draft_id,
            ApproveDecisionRuleDraftRequest(rule_set_id=request.payload.get("rule_set_id"), approved_by=request.payload.get("approved_by")),
        )
    else:
        reject_decision_rule_draft(draft_id)
    return []


def _apply_review_action(item: ReviewQueueItem, request: ReviewActionRequest) -> tuple[str, list[str]]:
    if request.action_type == ReviewActionType.DISMISS_WITH_NOTE:
        if not request.note or not request.note.strip():
            raise api_error(422, "DISMISS_NOTE_REQUIRED", "DISMISS_WITH_NOTE requires a reviewer note.", {"item_id": item.item_id}, "Explain why the item can be dismissed.")
        return "DISMISSED", []
    if request.action_type == ReviewActionType.MARK_TRACK_FALSE_POSITIVE:
        return "RESOLVED", _apply_mark_track_false_positive(item)
    if request.action_type == ReviewActionType.MARK_TRACK_VALID_PLAYER:
        return "RESOLVED", ["Recorded as valid player track/detection; no tracking exclusions were removed automatically."]
    if request.action_type == ReviewActionType.ASSIGN_TRACK_TO_PLAYER_ALIAS:
        return "RESOLVED", _apply_assign_track_to_player_alias(item, request)
    if request.action_type == ReviewActionType.FLAG_PROMPT_LABEL_ISSUE:
        return "RESOLVED", _apply_prompt_label_issue(item, request)
    if request.action_type == ReviewActionType.MARK_ATTEMPT_TEACHING_CASE:
        return "RESOLVED", _apply_teaching_case(item, request)
    if request.action_type in {ReviewActionType.APPROVE_RULE_DRAFT, ReviewActionType.REJECT_RULE_DRAFT}:
        return "RESOLVED", _apply_rule_draft_action(item, request)
    if request.action_type == ReviewActionType.ACCEPT_UNKNOWN_ATTRIBUTION:
        return "RESOLVED", ["UNKNOWN Player Value attribution accepted; no player identity was created."]
    if request.action_type == ReviewActionType.OPEN_ALIAS_REVIEW:
        return "RESOLVED", ["Alias review follow-up recorded; no alias was changed."]
    raise api_error(501, "REVIEW_ACTION_NOT_IMPLEMENTED", "This review action is not implemented yet.", {"action_type": request.action_type}, "Choose one of the implemented review actions.")

@router.post("/generate", response_model=ReviewQueueGenerateResponse)
def generate_review_queue() -> ReviewQueueGenerateResponse:
    existing = _existing_item_by_id()
    items_by_id = {item.item_id: _with_existing_state(item, existing) for item in _generated_items()}
    items = sorted(items_by_id.values(), key=lambda item: (item.status != "OPEN", item.item_type, item.priority, item.created_at.isoformat()))
    _write_queue(items)
    return ReviewQueueGenerateResponse(
        items=[_with_allowed_actions(item) for item in items],
        generated_count=len(items),
        open_count=sum(1 for item in items if item.status == "OPEN"),
        resolved_count=sum(1 for item in items if item.status == "RESOLVED"),
        dismissed_count=sum(1 for item in items if item.status == "DISMISSED"),
    )


@router.get("", response_model=list[ReviewQueueItem])
def list_review_queue() -> list[ReviewQueueItem]:
    return [_with_allowed_actions(item) for item in _read_queue()]


@router.get("/actions", response_model=list[ReviewActionLog])
def list_review_actions(
    item_id: str | None = None,
    project_id: str | None = None,
    action_type: ReviewActionType | None = Query(default=None),
) -> list[ReviewActionLog]:
    actions = _read_action_log()
    if item_id is not None:
        actions = [action for action in actions if action.item_id == item_id]
    if project_id is not None:
        actions = [action for action in actions if action.project_id == project_id]
    if action_type is not None:
        actions = [action for action in actions if action.action_type == action_type]
    return actions


@router.post("/{item_id}/actions", response_model=ReviewActionResponse)
def perform_review_action(item_id: str, request: ReviewActionRequest) -> ReviewActionResponse:
    items = _read_queue()
    for index, item in enumerate(items):
        if item.item_id != item_id:
            continue
        if request.action_type not in allowed_actions_for_item(item):
            action = _new_action_log(item, request, "FAILED", [f"Action {request.action_type} is not allowed for {item.item_type}."])
            _append_action_log(action)
            raise api_error(400, "REVIEW_ACTION_NOT_ALLOWED", "Review action is not allowed for this queue item type.", {"item_type": item.item_type, "action_type": request.action_type, "allowed_actions": allowed_actions_for_item(item)}, "Choose an action from item.allowed_actions.")
        try:
            new_status, warnings = _apply_review_action(item, request)
        except Exception:
            action = _new_action_log(item, request, "FAILED")
            _append_action_log(action)
            raise
        resolved_at = utc_now() if new_status in {"RESOLVED", "DISMISSED"} else None
        updated = _with_allowed_actions(item.model_copy(update={"status": new_status, "resolved_at": resolved_at}))
        items[index] = updated
        _write_queue(items)
        action = _new_action_log(updated, request, "APPLIED", warnings)
        _append_action_log(action)
        return ReviewActionResponse(item=updated, action=action)
    raise api_error(404, "REVIEW_QUEUE_ITEM_NOT_FOUND", "Review queue item was not found.", {"item_id": item_id}, "Generate the review queue and retry with an item_id from the response.")


@router.put("/{item_id}", response_model=ReviewQueueItem)
def update_review_queue_item(item_id: str, request: UpdateReviewQueueItemRequest) -> ReviewQueueItem:
    items = _read_queue()
    for index, item in enumerate(items):
        if item.item_id != item_id:
            continue
        resolved_at = utc_now() if request.status in {"RESOLVED", "DISMISSED"} else None
        updated = item.model_copy(update={"status": request.status, "resolved_at": resolved_at})
        items[index] = updated
        _write_queue(items)
        return _with_allowed_actions(updated)
    raise api_error(404, "REVIEW_QUEUE_ITEM_NOT_FOUND", "Review queue item was not found.", {"item_id": item_id}, "Generate the review queue and retry with an item_id from the response.")
