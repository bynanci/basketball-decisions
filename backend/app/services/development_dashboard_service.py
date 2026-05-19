"""Aggregate local development artifacts into the M26 progress dashboard.

This service only summarizes existing deterministic artifacts. It does not add a
new scoring formula, run live analytics, provide medical/injury advice, or use
LLM-generated coaching advice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models import (
    DevelopmentDashboardAction,
    DevelopmentDashboardArtifactHealthSummary,
    DevelopmentDashboardDatasetHealthSummary,
    DevelopmentDashboardMetric,
    DevelopmentDashboardModelRegistrySummary,
    DevelopmentDashboardPlayerSummary,
    DevelopmentDashboardPracticeFeedbackSummary,
    DevelopmentDashboardResponse,
    DevelopmentDashboardReviewQueueSummary,
    DevelopmentDashboardTeamSummary,
    PlayerValueBuildResponse,
    PlayerValueTrendsResponse,
    RecognitionModelRegistry,
)
from app.models.base import utc_now
from app.models.dataset import DatasetHealthResponse
from app.models.practice_execution import PracticeExecutionListResponse, PracticeFeedbackSignalsResponse
from app.models.practice_plan import PracticePlanListResponse
from app.models.coach_report import CoachReportListResponse
from app.services.artifact_map_service import build_artifact_map

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATASETS_DIR = APP_DATA_DIR / "datasets"
DRILLS_DIR = APP_DATA_DIR / "drills"
PRACTICE_PLANS_DIR = APP_DATA_DIR / "practice_plans"
PRACTICE_EXECUTIONS_DIR = APP_DATA_DIR / "practice_executions"
REVIEW_QUEUE_DIR = APP_DATA_DIR / "review_queue"
RECOGNITION_MODELS_DIR = APP_DATA_DIR / "models" / "recognition"
REPORTS_DIR = APP_DATA_DIR / "reports" / "coach"
DECISION_RULES_DIR = APP_DATA_DIR / "decision_rules"


def _read_json(path: Path, warnings: list[str], label: str) -> Any | None:
    if not path.exists():
        warnings.append(f"Missing artifact: {label} at {path}.")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(f"Unreadable artifact: {label} at {path} ({exc.__class__.__name__}).")
        return None


def _read_jsonl(path: Path, warnings: list[str], label: str) -> list[dict[str, Any]]:
    if not path.exists():
        warnings.append(f"Missing artifact: {label} at {path}.")
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Unreadable {label} line {line_number} at {path}.")
                continue
            if isinstance(row, dict):
                rows.append(row)
    except OSError as exc:
        warnings.append(f"Unreadable artifact: {label} at {path} ({exc.__class__.__name__}).")
    return rows


def _validate(model_type: Any, payload: Any, warnings: list[str], label: str) -> Any | None:
    if payload is None:
        return None
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        warnings.append(f"Invalid artifact schema: {label} ({exc.__class__.__name__}).")
        return None


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _trend_lookup(trends: PlayerValueTrendsResponse | None) -> dict[tuple[str, str], tuple[int, float | None, list[str]]]:
    lookup: dict[tuple[str, str], tuple[int, float | None, list[str]]] = {}
    if trends is None:
        return lookup
    for series in trends.trends:
        points = sorted(series.points, key=lambda point: point.generated_at)
        delta = None
        if len(points) >= 2:
            delta = round(points[-1].player_value_score - points[-2].player_value_score, 4)
        lookup[(series.project_id, series.player_key)] = (len(points), delta, series.warnings)
    return lookup


def _action(action_id: str, title: str, detail: str, *, severity: str = "action", artifact: str | None = None, href: str | None = None) -> DevelopmentDashboardAction:
    return DevelopmentDashboardAction(action_id=action_id, title=title, detail=detail, severity=severity, artifact=artifact, href=href)


def build_development_dashboard() -> DevelopmentDashboardResponse:
    warnings: list[str] = []
    next_best_actions: list[DevelopmentDashboardAction] = []
    artifact_status: dict[str, bool] = {}
    player_value = _validate(PlayerValueBuildResponse, _read_json(DATASETS_DIR / "player_value" / "player_value_summary.json", warnings, "player value summaries"), warnings, "player value summaries")
    artifact_status["player_value_summaries"] = player_value is not None
    if player_value is None:
        next_best_actions.append(_action("build-player-value", "Build Player Value summaries", "Run the local Player Value build so the dashboard can show project-scoped player rows.", artifact="player_value_summaries", href="/player-value"))

    trends = _validate(PlayerValueTrendsResponse, _read_json(DATASETS_DIR / "player_value" / "player_value_trends.json", warnings, "player value trends"), warnings, "player value trends")
    artifact_status["player_value_trends"] = trends is not None
    if trends is None:
        next_best_actions.append(_action("build-player-trends", "Create Player Value trend snapshots", "Build at least two immutable Player Value snapshots to populate trend deltas.", severity="warning", artifact="player_value_trends", href="/player-value/trends"))

    drill_recommendations = _read_json(DRILLS_DIR / "latest_recommendations.json", warnings, "drill recommendations")
    artifact_status["drill_recommendations"] = drill_recommendations is not None
    if drill_recommendations is None:
        next_best_actions.append(_action("build-drill-recommendations", "Generate drill recommendations", "Use existing Player Value and review artifacts to generate deterministic drill recommendations.", artifact="drill_recommendations", href="/drills"))

    practice_plans = _validate(PracticePlanListResponse, _read_json(PRACTICE_PLANS_DIR / "index.json", warnings, "practice plans"), warnings, "practice plans")
    artifact_status["practice_plans"] = practice_plans is not None
    if practice_plans is None or not practice_plans.plans:
        next_best_actions.append(_action("create-practice-plan", "Create a practice plan", "Build a deterministic practice plan from saved drill recommendations before tracking execution feedback.", artifact="practice_plans", href="/practice-plans"))

    practice_executions = _validate(PracticeExecutionListResponse, _read_json(PRACTICE_EXECUTIONS_DIR / "index.json", warnings, "practice executions"), warnings, "practice executions")
    artifact_status["practice_executions"] = practice_executions is not None
    if practice_executions is None or not practice_executions.executions:
        next_best_actions.append(_action("capture-practice-execution", "Capture practice execution", "Start or update a practice execution so completion, skipped, and modified block signals are available.", artifact="practice_executions", href="/practice-executions"))

    feedback_signals = _validate(PracticeFeedbackSignalsResponse, {"signals": _read_jsonl(PRACTICE_EXECUTIONS_DIR / "practice_feedback_signals.jsonl", warnings, "practice feedback signals"), "updated_at": utc_now()}, warnings, "practice feedback signals")
    artifact_status["practice_feedback_signals"] = feedback_signals is not None and bool(feedback_signals.signals)

    review_queue_payload = _read_json(REVIEW_QUEUE_DIR / "review_queue.json", warnings, "review queue")
    review_items = review_queue_payload if isinstance(review_queue_payload, list) else review_queue_payload.get("items", []) if isinstance(review_queue_payload, dict) else []
    if not isinstance(review_items, list):
        review_items = []
    artifact_status["review_queue"] = review_queue_payload is not None
    if review_queue_payload is None:
        next_best_actions.append(_action("generate-review-queue", "Generate review queue", "Generate or refresh the review queue so unresolved recognition, decision, and attribution items are visible.", artifact="review_queue", href="/review-queue"))

    review_actions_payload = _read_json(REVIEW_QUEUE_DIR / "review_action_log.json", warnings, "review action log")
    review_actions = review_actions_payload if isinstance(review_actions_payload, list) else []
    artifact_status["review_action_log"] = review_actions_payload is not None

    dataset_health = _validate(DatasetHealthResponse, _read_json(DATASETS_DIR / "dataset_health.json", warnings, "dataset health"), warnings, "dataset health")
    if dataset_health is None:
        # Dataset health is usually computed on demand rather than persisted; summarize manifest counts as fallback.
        recognition_manifest = _read_json(DATASETS_DIR / "recognition" / "dataset_manifest.json", warnings, "recognition dataset manifest")
        decision_manifest = _read_json(DATASETS_DIR / "decision" / "dataset_manifest.json", warnings, "decision dataset manifest")
        dataset_summary = DevelopmentDashboardDatasetHealthSummary(
            available=recognition_manifest is not None or decision_manifest is not None,
            recognition_sample_count=int(recognition_manifest.get("sample_count", 0)) if isinstance(recognition_manifest, dict) else 0,
            recognition_label_count=int(recognition_manifest.get("label_count", 0)) if isinstance(recognition_manifest, dict) else 0,
            decision_sample_count=int(decision_manifest.get("sample_count", 0)) if isinstance(decision_manifest, dict) else 0,
            decision_label_count=int(decision_manifest.get("label_count", 0)) if isinstance(decision_manifest, dict) else 0,
        )
    else:
        dataset_summary = DevelopmentDashboardDatasetHealthSummary(
            available=True,
            recognition_sample_count=dataset_health.recognition.sample_count,
            recognition_label_count=dataset_health.recognition.label_count,
            recognition_warning_count=len(dataset_health.recognition.warnings),
            decision_sample_count=dataset_health.decision.sample_count,
            decision_label_count=dataset_health.decision.label_count,
            decision_warning_count=len(dataset_health.decision.warnings),
            generated_at=dataset_health.generated_at,
        )
    artifact_status["dataset_health"] = dataset_summary.available
    if not dataset_summary.available:
        next_best_actions.append(_action("export-datasets", "Export local datasets", "Export or curate recognition and decision datasets to populate health summaries.", artifact="dataset_health", href="/local-lab"))

    model_registry = _validate(RecognitionModelRegistry, _read_json(RECOGNITION_MODELS_DIR / "model_registry.json", warnings, "model registry"), warnings, "model registry")
    model_summary = DevelopmentDashboardModelRegistrySummary(
        available=model_registry is not None,
        active_version=model_registry.active_version if model_registry else None,
        model_count=len(model_registry.models) if model_registry else 0,
        latest_version=max((model.version for model in model_registry.models), default=None) if model_registry else None,
        updated_at=model_registry.updated_at if model_registry else None,
    )
    artifact_status["model_registry"] = model_summary.available
    if model_registry is None or not model_registry.models:
        next_best_actions.append(_action("train-recognition-baseline", "Train or register a recognition baseline", "Use the model registry workflow after dataset health is sufficient.", artifact="model_registry", href="/model-registry"))

    diagnostics_payload = _read_json(DATASETS_DIR / "decision" / "decision_diagnostics.json", warnings, "decision diagnostics")
    artifact_status["decision_diagnostics"] = diagnostics_payload is not None
    if diagnostics_payload is None:
        next_best_actions.append(_action("build-decision-diagnostics", "Build decision diagnostics", "Run local decision diagnostics to expose prompt and attempt quality summaries.", artifact="decision_diagnostics", href="/local-lab"))

    coach_reports = _validate(CoachReportListResponse, _read_json(REPORTS_DIR / "index.json", warnings, "coach reports"), warnings, "coach reports")
    artifact_status["coach_reports"] = coach_reports is not None
    if coach_reports is None or not coach_reports.reports:
        next_best_actions.append(_action("build-coach-report", "Build a coach report", "Export a deterministic coach report when the underlying artifacts are ready.", severity="warning", artifact="coach_reports", href="/reports/coach"))

    rules_payload = _read_json(DECISION_RULES_DIR / "active_rule_set.json", warnings, "active decision rule set")
    artifact_status["active_rule_set"] = rules_payload is not None

    trend_by_player = _trend_lookup(trends)
    player_summaries: list[DevelopmentDashboardPlayerSummary] = []
    if player_value is not None:
        for summary in sorted(player_value.summaries, key=lambda item: (item.project_id, item.player_key)):
            trend_points, trend_delta, trend_warnings = trend_by_player.get((summary.project_id, summary.player_key), (0, None, []))
            player_summaries.append(
                DevelopmentDashboardPlayerSummary(
                    project_id=summary.project_id,
                    player_key=summary.player_key,
                    display_name=summary.display_name,
                    team_side=str(summary.team_side),
                    role_hint=summary.role_hint,
                    player_value_score=summary.player_value_score,
                    confidence=summary.confidence,
                    decision_event_count=summary.decision_event_count,
                    trend_points=trend_points,
                    latest_trend_delta=trend_delta,
                    warnings=[*summary.warnings, *trend_warnings],
                )
            )

    completion_rates = [float(item.completion_rate) for item in practice_executions.executions] if practice_executions else []
    practice_feedback_summary = DevelopmentDashboardPracticeFeedbackSummary(
        signal_count=len(feedback_signals.signals) if feedback_signals else 0,
        action_signal_count=sum(1 for signal in (feedback_signals.signals if feedback_signals else []) if signal.severity == "action"),
        warning_signal_count=sum(1 for signal in (feedback_signals.signals if feedback_signals else []) if signal.severity == "warning"),
        latest_signal_at=max((signal.created_at for signal in (feedback_signals.signals if feedback_signals else [])), default=None),
        completion_rate_average=_average(completion_rates),
        skipped_count=sum(int(item.skipped_count) for item in practice_executions.executions) if practice_executions else 0,
        modified_count=sum(int(item.modified_count) for item in practice_executions.executions) if practice_executions else 0,
    )

    open_items = [item for item in review_items if str(item.get("status", "OPEN")) != "RESOLVED" and str(item.get("status", "OPEN")) != "DISMISSED"]
    review_summary = DevelopmentDashboardReviewQueueSummary(
        item_count=len(review_items),
        open_count=len(open_items),
        high_priority_count=sum(1 for item in open_items if item.get("priority") == "HIGH"),
        action_log_count=len(review_actions),
    )
    if review_summary.open_count:
        next_best_actions.append(_action("resolve-review-queue", "Resolve open review items", f"There are {review_summary.open_count} open review items before downstream summaries should be treated as complete.", severity="warning", artifact="review_queue", href="/review-queue"))

    team_summary = DevelopmentDashboardTeamSummary(
        player_count=len(player_summaries),
        average_player_value_score=_average([row.player_value_score for row in player_summaries if row.player_value_score is not None]),
        average_confidence=_average([row.confidence for row in player_summaries if row.confidence is not None]),
        total_decision_events=sum(row.decision_event_count for row in player_summaries),
        trend_series_count=len(trends.trends) if trends else 0,
        practice_plan_count=len(practice_plans.plans) if practice_plans else 0,
        practice_execution_count=len(practice_executions.executions) if practice_executions else 0,
        coach_report_count=len(coach_reports.reports) if coach_reports else 0,
        notes=[
            "Dashboard summarizes local artifacts only; it is not an official scouting-grade evaluation.",
            "Recommended next steps are operational artifact follow-ups, not LLM-generated coaching advice.",
        ],
    )

    artifact_map = build_artifact_map()
    artifact_health_summary = DevelopmentDashboardArtifactHealthSummary(
        stale_artifact_count=artifact_map.stale_artifact_count,
        missing_artifact_count=artifact_map.missing_artifact_count,
        action_artifact_count=artifact_map.severity_counts.get("action", 0),
        warning_artifact_count=artifact_map.severity_counts.get("warning", 0),
        generated_at=artifact_map.generated_at,
    )
    if artifact_health_summary.stale_artifact_count:
        next_best_actions.append(_action("review-artifact-map", "Review stale artifact dependencies", f"{artifact_health_summary.stale_artifact_count} artifact(s) are stale according to the read-only dependency map.", severity="warning", artifact="artifact_map", href="/local-lab"))

    metrics = [
        DevelopmentDashboardMetric(key="players", label="Players", value=team_summary.player_count, detail="Player Value summary rows"),
        DevelopmentDashboardMetric(key="avg_player_value", label="Avg Player Value", value=team_summary.average_player_value_score if team_summary.average_player_value_score is not None else "—", detail="Existing Player Value v1 scores only"),
        DevelopmentDashboardMetric(key="decision_events", label="Decision Events", value=team_summary.total_decision_events, detail="Events linked to player summaries"),
        DevelopmentDashboardMetric(key="open_reviews", label="Open Reviews", value=review_summary.open_count, detail="Review queue items not resolved", severity="warning" if review_summary.open_count else "info"),
        DevelopmentDashboardMetric(key="practice_feedback", label="Practice Signals", value=practice_feedback_summary.signal_count, detail="Captured deterministic feedback signals"),
        DevelopmentDashboardMetric(key="registered_models", label="Models", value=model_summary.model_count, detail=f"Active: {model_summary.active_version or 'None'}", severity="info" if model_summary.model_count else "warning"),
    ]

    artifact_counts = {
        "player_summaries": len(player_summaries),
        "trend_series": len(trends.trends) if trends else 0,
        "drill_recommendations": len(drill_recommendations.get("recommendations", [])) if isinstance(drill_recommendations, dict) else 0,
        "practice_plans": team_summary.practice_plan_count,
        "practice_executions": team_summary.practice_execution_count,
        "practice_feedback_signals": practice_feedback_summary.signal_count,
        "review_items": review_summary.item_count,
        "model_registry_models": model_summary.model_count,
        "coach_reports": team_summary.coach_report_count,
    }
    raw_refs = {"generated_from": sorted(artifact_status.keys())}

    return DevelopmentDashboardResponse(
        generated_at=utc_now(),
        metrics=metrics,
        team_summary=team_summary,
        player_summaries=player_summaries,
        next_best_actions=next_best_actions,
        dataset_health_summary=dataset_summary,
        model_registry_summary=model_summary,
        practice_feedback_summary=practice_feedback_summary,
        review_queue_summary=review_summary,
        artifact_health_summary=artifact_health_summary,
        warnings=warnings,
        artifact_counts=artifact_counts,
        artifact_status=artifact_status,
        raw_artifact_refs=raw_refs,
    )
