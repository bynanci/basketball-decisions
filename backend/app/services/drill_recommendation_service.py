"""Deterministic drill recommendations from local basketball decision artifacts.

The recommendation engine never generates new coaching advice. It selects from a
small, human-authored local catalog and attaches local evidence references.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models import (
    DrillCatalogItem,
    DrillCatalogResponse,
    DrillEvidenceRef,
    DrillRecommendation,
    DrillRecommendationRequest,
    DrillRecommendationResponse,
    RecommendationAdjustment,
)
from app.models.base import utc_now
from app.models.practice_execution import PracticeFeedbackSignal
from app.services.practice_feedback_signal_service import read_practice_feedback_signals

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATASETS_DIR = APP_DATA_DIR / "datasets"
REVIEW_QUEUE_DIR = APP_DATA_DIR / "review_queue"
DRILLS_DIR = APP_DATA_DIR / "drills"
CATALOG_PATH = DRILLS_DIR / "catalog.json"
LATEST_RECOMMENDATIONS_PATH = DRILLS_DIR / "latest_recommendations.json"

SITUATION_TO_DRILL = {
    "PICK_AND_ROLL": "pnr-two-read-pocket-skip",
    "BALL_SCREEN": "pnr-two-read-pocket-skip",
    "TRANSITION": "transition-lane-advance",
    "ADVANTAGE": "advantage-read-kickout",
    "DRIVE_AND_KICK": "spacing-drift-lift",
    "CLOSEOUT": "closeout-contain-no-middle",
    "HELP_ROTATION": "help-tag-recover",
}
ROLE_TO_DRILL = {
    "BALL_HANDLER": "advantage-read-kickout",
    "PRIMARY_BALL_HANDLER": "pnr-two-read-pocket-skip",
    "WING": "transition-lane-advance",
    "OFF_BALL": "spacing-drift-lift",
    "ON_BALL_DEFENDER": "closeout-contain-no-middle",
    "HELP_DEFENDER": "help-tag-recover",
}
DEFAULT_DRILL_ID = "advantage-read-kickout"

PRIORITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
PRIORITY_BY_RANK = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}


def _adjustment_id(recommendation_id: str, signal_id: str, adjustment_type: str) -> str:
    digest = hashlib.sha256(f"{recommendation_id}|{signal_id}|{adjustment_type}".encode("utf-8")).hexdigest()[:12]
    return f"rec-adjust-{digest}"


def _signal_matches_recommendation(signal: PracticeFeedbackSignal, recommendation: DrillRecommendation) -> bool:
    if signal.recommendation_id and signal.recommendation_id == recommendation.recommendation_id:
        return True
    if signal.drill_id and signal.drill_id == recommendation.drill_id:
        return True
    return False


def _adjustments_for_signal(signal: PracticeFeedbackSignal, recommendation: DrillRecommendation) -> list[RecommendationAdjustment]:
    signal_id = signal.signal_id or "practice-feedback-unknown"
    base = {
        "signal_id": signal_id,
        "signal_type": signal.signal_type,
        "execution_id": signal.execution_id,
        "block_id": signal.block_id,
        "drill_id": signal.drill_id,
        "recommendation_id": signal.recommendation_id,
    }
    if signal.signal_type == "REPEAT_DRILL":
        return [
            RecommendationAdjustment(
                **base,
                adjustment_id=_adjustment_id(recommendation.recommendation_id, signal_id, "PRIORITY_UP"),
                adjustment_type="PRIORITY_UP",
                priority_delta=1,
                confidence_delta=0.08,
                reason=f"Recent practice feedback recommends repeating this drill: {signal.reason}",
            )
        ]
    if signal.signal_type == "SIMPLIFY_DRILL":
        return [
            RecommendationAdjustment(
                **base,
                adjustment_id=_adjustment_id(recommendation.recommendation_id, signal_id, "CONFIDENCE_UP"),
                adjustment_type="CONFIDENCE_UP",
                confidence_delta=0.05,
                reason=f"Recent practice feedback suggests simplifying this drill before progressing: {signal.reason}",
            )
        ]
    if signal.signal_type == "PROGRESS_DRILL":
        return [
            RecommendationAdjustment(
                **base,
                adjustment_id=_adjustment_id(recommendation.recommendation_id, signal_id, "PRIORITY_DOWN"),
                adjustment_type="PRIORITY_DOWN",
                priority_delta=-1,
                confidence_delta=-0.08,
                reason=f"Recent practice feedback showed strong completion, so this drill can be deprioritized: {signal.reason}",
            )
        ]
    return [
        RecommendationAdjustment(
            **base,
            adjustment_id=_adjustment_id(recommendation.recommendation_id, signal_id, "REASON_HINT"),
            adjustment_type="REASON_HINT",
            reason=f"Recent practice feedback is relevant to this drill: {signal.reason}",
        )
    ]


def _apply_feedback_adjustments(
    recommendations: list[DrillRecommendation],
    request: DrillRecommendationRequest,
    warnings: list[str],
) -> tuple[list[DrillRecommendation], int, list[str]]:
    if not request.include_practice_feedback:
        return recommendations, 0, []

    signals = read_practice_feedback_signals(
        limit=request.feedback_lookback_limit,
        project_id=request.project_id,
        player_key=request.player_key,
        warnings=warnings,
    )
    if not signals:
        warnings.append("No recent practice feedback signals were available for recommendation adjustment.")
        return recommendations, 0, []

    response_summary: list[str] = []
    for recommendation in recommendations:
        matched = [signal for signal in signals if _signal_matches_recommendation(signal, recommendation)]
        adjustments = [adjustment for signal in matched for adjustment in _adjustments_for_signal(signal, recommendation)]
        if not adjustments:
            continue
        priority_delta = sum(adjustment.priority_delta for adjustment in adjustments)
        confidence_delta = sum(adjustment.confidence_delta for adjustment in adjustments)
        current_rank = PRIORITY_RANK[recommendation.priority]
        recommendation.priority = PRIORITY_BY_RANK[max(0, min(2, current_rank + priority_delta))]  # type: ignore[assignment]
        recommendation.confidence = max(0.25, min(0.95, recommendation.confidence + confidence_delta))
        recommendation.adjustments = adjustments[:8]
        recommendation.feedback_signal_ids = list(dict.fromkeys(adjustment.signal_id for adjustment in adjustments))
        recommendation.adjustment_summary = list(dict.fromkeys(adjustment.reason for adjustment in adjustments))[:5]
        recommendation.feedback_adjusted = True
        response_summary.extend(recommendation.adjustment_summary)

    return recommendations, len(signals), list(dict.fromkeys(response_summary))[:8]


def _stable_id(parts: list[str]) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"drill-rec-{digest}"


def _read_json(path: Path, warnings: list[str], artifact: str) -> Any | None:
    if not path.exists():
        warnings.append(f"Missing artifact: {artifact} was not found at {path}.")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(f"Unreadable artifact: {artifact} at {path} ({exc.__class__.__name__}).")
        return None


def _read_jsonl(path: Path, warnings: list[str], artifact: str) -> list[dict[str, Any]]:
    if not path.exists():
        warnings.append(f"Missing artifact: {artifact} was not found at {path}.")
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(f"Unreadable artifact: {artifact} at {path} ({exc.__class__.__name__}).")
        return []
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def load_drill_catalog() -> DrillCatalogResponse:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return DrillCatalogResponse(drills=[DrillCatalogItem.model_validate(row) for row in payload.get("drills", [])])


def _catalog_by_id() -> dict[str, DrillCatalogItem]:
    return {drill.drill_id: drill for drill in load_drill_catalog().drills}


def _pick_drill_id(role: str | None, situation: str | None, text: str = "") -> str:
    normalized_situation = (situation or "").upper()
    normalized_role = (role or "").upper()
    normalized_text = text.upper()
    if normalized_situation in SITUATION_TO_DRILL:
        return SITUATION_TO_DRILL[normalized_situation]
    if normalized_role in ROLE_TO_DRILL:
        return ROLE_TO_DRILL[normalized_role]
    if "PICK" in normalized_text or "SCREEN" in normalized_text:
        return "pnr-two-read-pocket-skip"
    if "TRANSITION" in normalized_text:
        return "transition-lane-advance"
    if "CLOSEOUT" in normalized_text:
        return "closeout-contain-no-middle"
    if "HELP" in normalized_text or "ROTATION" in normalized_text:
        return "help-tag-recover"
    if "SPACING" in normalized_text or "OFF BALL" in normalized_text:
        return "spacing-drift-lift"
    return DEFAULT_DRILL_ID


def _priority_from_score(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    if score >= 0.45:
        return "MEDIUM"
    return "LOW"


def _add_candidate(
    candidates: dict[str, dict[str, Any]],
    catalog: dict[str, DrillCatalogItem],
    drill_id: str,
    score: float,
    reason: str,
    evidence: DrillEvidenceRef,
) -> None:
    drill = catalog.get(drill_id) or catalog[DEFAULT_DRILL_ID]
    existing = candidates.setdefault(
        drill.drill_id,
        {
            "drill": drill,
            "score": 0.0,
            "reasons": [],
            "evidence_refs": [],
        },
    )
    existing["score"] += score
    existing["reasons"].append(reason)
    existing["evidence_refs"].append(evidence)


def _matches_filters(row: dict[str, Any], request: DrillRecommendationRequest) -> bool:
    if request.project_id and row.get("project_id") != request.project_id:
        return False
    if request.player_key and row.get("player_key") != request.player_key and row.get("alias_player_key") != request.player_key:
        return False
    return True


def _from_decision_diagnostics(candidates: dict[str, dict[str, Any]], catalog: dict[str, DrillCatalogItem], request: DrillRecommendationRequest, warnings: list[str]) -> None:
    payload = _read_json(DATASETS_DIR / "decision" / "decision_diagnostics.json", warnings, "Decision diagnostics")
    if not isinstance(payload, dict):
        return
    prompts = payload.get("prompt_diagnostics", [])
    if isinstance(prompts, list):
        for prompt in prompts:
            if not isinstance(prompt, dict) or not _matches_filters(prompt, request):
                continue
            correct_rate = float(prompt.get("correct_rate") or 0)
            avg_cost = float(prompt.get("avg_opportunity_cost") or 0)
            timeout_rate = float(prompt.get("timeout_rate") or 0)
            difficulty = str(prompt.get("difficulty") or "")
            if correct_rate > 0.65 and avg_cost < 8 and timeout_rate < 0.25 and difficulty != "TOO_HARD":
                continue
            score = (1 - correct_rate) + min(avg_cost / 50, 0.4) + min(timeout_rate, 0.3)
            role = prompt.get("court_role_target")
            situation = prompt.get("situation_type")
            drill_id = _pick_drill_id(role, situation)
            _add_candidate(
                candidates,
                catalog,
                drill_id,
                score,
                f"Decision diagnostics flagged {prompt.get('prompt_id', 'a prompt')} with correct rate {correct_rate:.2f}, opportunity cost {avg_cost:.1f}, and timeout rate {timeout_rate:.2f}.",
                DrillEvidenceRef(
                    source="DECISION_DIAGNOSTICS",
                    artifact=str(DATASETS_DIR / "decision" / "decision_diagnostics.json"),
                    ref_id=str(prompt.get("prompt_id") or ""),
                    project_id=prompt.get("project_id"),
                    prompt_id=prompt.get("prompt_id"),
                    detail="Prompt-level decision diagnostics exceeded deterministic thresholds.",
                ),
            )

    roles = payload.get("role_diagnostics", [])
    if isinstance(roles, list):
        for role_row in roles:
            if not isinstance(role_row, dict):
                continue
            avg_score = float(role_row.get("avg_score") or 100)
            timeout_rate = float(role_row.get("timeout_rate") or 0)
            if avg_score >= 70 and timeout_rate < 0.25:
                continue
            role = role_row.get("court_role")
            weakest = role_row.get("weakest_situation_types") or []
            situation = weakest[0] if isinstance(weakest, list) and weakest else None
            drill_id = _pick_drill_id(role, situation)
            _add_candidate(
                candidates,
                catalog,
                drill_id,
                min((70 - avg_score) / 70, 0.6) + timeout_rate,
                f"Role diagnostics show {role or 'an unspecified role'} averaging {avg_score:.1f} with timeout rate {timeout_rate:.2f}.",
                DrillEvidenceRef(source="DECISION_DIAGNOSTICS", artifact=str(DATASETS_DIR / "decision" / "decision_diagnostics.json"), ref_id=str(role or "role"), detail="Role diagnostics crossed deterministic score or timeout thresholds."),
            )


def _from_player_value(candidates: dict[str, dict[str, Any]], catalog: dict[str, DrillCatalogItem], request: DrillRecommendationRequest, warnings: list[str]) -> None:
    payload = _read_json(DATASETS_DIR / "player_value" / "player_value_summary.json", warnings, "Player Value summary")
    summaries = payload.get("summaries", []) if isinstance(payload, dict) else []
    if not isinstance(summaries, list):
        return
    for summary in summaries:
        if not isinstance(summary, dict) or not _matches_filters(summary, request):
            continue
        avg_score = float(summary.get("avg_role_adjusted_score") or summary.get("player_value_score") or 0)
        correct_rate = float(summary.get("correct_rate") or 0)
        timeout_rate = float(summary.get("timeout_rate") or 0)
        if avg_score >= 70 and correct_rate >= 0.65 and timeout_rate < 0.25:
            continue
        drill_id = _pick_drill_id(summary.get("role_hint"), None)
        player_label = summary.get("display_name") or summary.get("player_key") or "local player alias"
        _add_candidate(
            candidates,
            catalog,
            drill_id,
            min((70 - avg_score) / 70, 0.6) + (1 - correct_rate) * 0.4 + timeout_rate * 0.4,
            f"Player Value summary for {player_label} shows average decision score {avg_score:.1f}, correct rate {correct_rate:.2f}, and timeout rate {timeout_rate:.2f}.",
            DrillEvidenceRef(
                source="PLAYER_VALUE",
                artifact=str(DATASETS_DIR / "player_value" / "player_value_summary.json"),
                ref_id=str(summary.get("player_key") or ""),
                project_id=summary.get("project_id"),
                player_key=summary.get("player_key"),
                detail="Player Value summary crossed deterministic decision score, correct-rate, or timeout thresholds.",
            ),
        )


def _from_trends(candidates: dict[str, dict[str, Any]], catalog: dict[str, DrillCatalogItem], request: DrillRecommendationRequest, warnings: list[str]) -> None:
    index_path = DATASETS_DIR / "player_value" / "player_value_build_index.json"
    payload = _read_json(index_path, warnings, "Player Value build index")
    build_entries = payload.get("builds", []) if isinstance(payload, dict) else []
    if not isinstance(build_entries, list) or len(build_entries) < 2:
        return

    grouped: dict[tuple[str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
    builds_dir = DATASETS_DIR / "player_value" / "builds"
    for entry in build_entries:
        if not isinstance(entry, dict):
            continue
        snapshot_path = builds_dir / f"{entry.get('build_id')}.json"
        snapshot = _read_json(snapshot_path, warnings, f"Player Value snapshot {entry.get('build_id')}")
        summaries = snapshot.get("build", {}).get("summaries", []) if isinstance(snapshot, dict) else []
        if not isinstance(summaries, list):
            continue
        for summary in summaries:
            if not isinstance(summary, dict) or not _matches_filters(summary, request):
                continue
            grouped[(summary.get("project_id"), summary.get("player_key"))].append(
                {
                    "build_id": entry.get("build_id"),
                    "generated_at": entry.get("generated_at"),
                    "player_value_score": summary.get("player_value_score"),
                    "role_hint": summary.get("role_hint"),
                }
            )

    for (project_id, player_key), rows in grouped.items():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda row: str(row.get("generated_at", "")))
        first = rows[0]
        latest = rows[-1]
        first_score = float(first.get("player_value_score") or 0)
        latest_score = float(latest.get("player_value_score") or 0)
        delta = latest_score - first_score
        if delta >= -5:
            continue
        _add_candidate(
            candidates,
            catalog,
            _pick_drill_id(latest.get("role_hint"), None),
            min(abs(delta) / 20, 0.8),
            f"Player Value trend declined by {abs(delta):.1f} points from {first.get('build_id')} to {latest.get('build_id')}.",
            DrillEvidenceRef(source="PLAYER_VALUE_TRENDS", artifact=str(index_path), ref_id=str(latest.get("build_id") or ""), project_id=project_id, player_key=player_key, detail="Latest trend point declined beyond the deterministic threshold."),
        )


def _from_teaching_cases(candidates: dict[str, dict[str, Any]], catalog: dict[str, DrillCatalogItem], request: DrillRecommendationRequest, warnings: list[str]) -> None:
    rows = _read_jsonl(DATASETS_DIR / "player_value" / "player_decision_events.jsonl", warnings, "Player decision events")
    for event in rows:
        if not _matches_filters(event, request):
            continue
        is_correct = bool(event.get("is_correct", event.get("selected_option_id") == event.get("correct_option_id")))
        score = float(event.get("role_adjusted_score") or event.get("raw_score") or 0)
        timed_out = bool(event.get("timed_out", False))
        if is_correct and score >= 70 and not timed_out:
            continue
        drill_id = _pick_drill_id(event.get("court_role_target") or event.get("user_role"), event.get("situation_type"), event.get("prompt_question") or "")
        _add_candidate(
            candidates,
            catalog,
            drill_id,
            min((70 - score) / 70, 0.6) + (0.25 if timed_out else 0.15),
            f"Teaching case {event.get('attempt_id', 'attempt')} had score {score:.1f} with correct={is_correct} and timed_out={timed_out}.",
            DrillEvidenceRef(source="TEACHING_CASE", artifact=str(DATASETS_DIR / "player_value" / "player_decision_events.jsonl"), ref_id=str(event.get("attempt_id") or event.get("decision_event_id") or ""), project_id=event.get("project_id"), player_key=event.get("alias_player_key"), prompt_id=event.get("prompt_id"), detail="Decision event selected as a deterministic teaching-case signal."),
        )


def _from_review_queue(candidates: dict[str, dict[str, Any]], catalog: dict[str, DrillCatalogItem], request: DrillRecommendationRequest, warnings: list[str]) -> None:
    payload = _read_json(REVIEW_QUEUE_DIR / "review_queue.json", warnings, "Review queue")
    items = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict) or not _matches_filters(item, request) or item.get("status", "OPEN") != "OPEN":
            continue
        if item.get("item_type") not in {"DECISION_PROMPT", "DECISION_ATTEMPT", "PLAYER_VALUE_ATTRIBUTION"}:
            continue
        priority = str(item.get("priority") or "LOW")
        score = {"HIGH": 0.75, "MEDIUM": 0.5}.get(priority, 0.25)
        text = f"{item.get('reason', '')} {item.get('recommended_action', '')}"
        drill_id = _pick_drill_id(None, None, text)
        _add_candidate(
            candidates,
            catalog,
            drill_id,
            score,
            f"Open review queue item {item.get('item_id')} has {priority.lower()} priority: {item.get('reason', 'review required')}.",
            DrillEvidenceRef(source="REVIEW_QUEUE", artifact=str(REVIEW_QUEUE_DIR / "review_queue.json"), ref_id=str(item.get("item_id") or ""), project_id=item.get("project_id"), player_key=item.get("player_key"), prompt_id=item.get("prompt_id"), detail="Open review finding contributes a deterministic recommendation signal."),
        )


def build_drill_recommendations(request: DrillRecommendationRequest) -> DrillRecommendationResponse:
    catalog = _catalog_by_id()
    warnings: list[str] = []
    candidates: dict[str, dict[str, Any]] = {}
    _from_decision_diagnostics(candidates, catalog, request, warnings)
    _from_player_value(candidates, catalog, request, warnings)
    _from_trends(candidates, catalog, request, warnings)
    _from_teaching_cases(candidates, catalog, request, warnings)
    _from_review_queue(candidates, catalog, request, warnings)

    recommendations: list[DrillRecommendation] = []
    for drill_id, candidate in candidates.items():
        drill: DrillCatalogItem = candidate["drill"]
        score = float(candidate["score"])
        evidence_refs: list[DrillEvidenceRef] = candidate["evidence_refs"]
        reason = " ".join(dict.fromkeys(candidate["reasons"]))
        recommendations.append(
            DrillRecommendation(
                recommendation_id=_stable_id([drill_id, request.project_id or "", request.player_key or "", reason]),
                drill_id=drill.drill_id,
                title=drill.title,
                priority=_priority_from_score(score),
                confidence=max(0.25, min(0.95, 0.35 + score / 2 + min(len(evidence_refs), 4) * 0.05)),
                role=drill.role,
                situation=drill.situation,
                reason=reason,
                coaching_cues=drill.coaching_cues,
                success_metrics=drill.success_metrics,
                evidence_refs=evidence_refs[:8],
            )
        )
    recommendations, feedback_signal_count, adjustment_summary = _apply_feedback_adjustments(recommendations, request, warnings)
    recommendations.sort(key=lambda rec: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[rec.priority], -rec.confidence, rec.title))
    response = DrillRecommendationResponse(
        generated_at=utc_now(),
        project_id=request.project_id,
        player_key=request.player_key,
        recommendations=recommendations[: request.max_recommendations],
        feedback_signal_count=feedback_signal_count,
        adjustment_summary=adjustment_summary,
        warnings=list(dict.fromkeys(warnings)),
        catalog_path=str(CATALOG_PATH),
        latest_path=str(LATEST_RECOMMENDATIONS_PATH),
    )
    _write_json(LATEST_RECOMMENDATIONS_PATH, response.model_dump(mode="json"))
    return response


def get_latest_drill_recommendations() -> DrillRecommendationResponse | None:
    if not LATEST_RECOMMENDATIONS_PATH.exists():
        return None
    try:
        return DrillRecommendationResponse.model_validate(json.loads(LATEST_RECOMMENDATIONS_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return None
