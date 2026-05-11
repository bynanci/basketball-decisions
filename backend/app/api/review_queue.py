"""Unified active-learning review queue routes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import TypeAdapter, ValidationError

from app.api.common import DATA_DIR, api_error, read_json, write_json_model
from app.models import (
    Calibration,
    DecisionDiagnosticsReport,
    DecisionEvent,
    DecisionRuleDraft,
    PlayerValueBuildResponse,
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
REVIEW_QUEUE_PATH = APP_DATA_DIR / "review_queue.json"
DECISION_RULE_DRAFTS_PATH = APP_DATA_DIR / "reference_videos" / "decision_rule_drafts.json"
_QUEUE_ADAPTER = TypeAdapter(list[ReviewQueueItem])
_RULE_DRAFTS_ADAPTER = TypeAdapter(list[DecisionRuleDraft])

LOW_CONFIDENCE_DETECTION_THRESHOLD = 0.35
UNCERTAIN_MODEL_RISK_LOW = 0.4
UNCERTAIN_MODEL_RISK_HIGH = 0.6
HIGH_OPPORTUNITY_COST_THRESHOLD = 0.3


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
        return _QUEUE_ADAPTER.validate_json(REVIEW_QUEUE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValidationError):
        return []


def _write_queue(items: list[ReviewQueueItem]) -> None:
    REVIEW_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_QUEUE_PATH.write_text(json.dumps([item.model_dump(mode="json") for item in items], indent=2), encoding="utf-8")


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


@router.post("/generate", response_model=ReviewQueueGenerateResponse)
def generate_review_queue() -> ReviewQueueGenerateResponse:
    existing = _existing_item_by_id()
    items_by_id = {item.item_id: _with_existing_state(item, existing) for item in _generated_items()}
    items = sorted(items_by_id.values(), key=lambda item: (item.status != "OPEN", item.item_type, item.priority, item.created_at.isoformat()))
    _write_queue(items)
    return ReviewQueueGenerateResponse(
        items=items,
        generated_count=len(items),
        open_count=sum(1 for item in items if item.status == "OPEN"),
        resolved_count=sum(1 for item in items if item.status == "RESOLVED"),
        dismissed_count=sum(1 for item in items if item.status == "DISMISSED"),
    )


@router.get("", response_model=list[ReviewQueueItem])
def list_review_queue() -> list[ReviewQueueItem]:
    return _read_queue()


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
        return updated
    raise api_error(404, "REVIEW_QUEUE_ITEM_NOT_FOUND", "Review queue item was not found.", {"item_id": item_id}, "Generate the review queue and retry with an item_id from the response.")
