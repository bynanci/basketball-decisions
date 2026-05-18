"""Build a read-only artifact dependency map with deterministic freshness checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from app.models import ArtifactDependency, ArtifactMapResponse, Workflow
from app.models.base import utc_now

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROJECTS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"
DATASETS_DIR = APP_DATA_DIR / "datasets"
DRILLS_DIR = APP_DATA_DIR / "drills"
PRACTICE_PLANS_DIR = APP_DATA_DIR / "practice_plans"
PRACTICE_EXECUTIONS_DIR = APP_DATA_DIR / "practice_executions"
REPORTS_DIR = APP_DATA_DIR / "reports" / "coach"
WORKFLOWS_DIR = APP_DATA_DIR / "workflows"
DECISION_RULES_DIR = APP_DATA_DIR / "decision_rules"
RECOGNITION_MODELS_DIR = APP_DATA_DIR / "models" / "recognition"
REVIEW_QUEUE_DIR = APP_DATA_DIR / "review_queue"
REFERENCE_VIDEOS_DIR = APP_DATA_DIR / "reference_videos"


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _file_mtime(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        return _as_utc(datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc))
    except OSError:
        return None


def _payload_updated_at(path: Path) -> datetime | None:
    payload = _read_json(path)
    if isinstance(payload, dict):
        for key in ("updated_at", "generated_at", "created_at", "last_exported_at"):
            parsed = _parse_datetime(payload.get(key))
            if parsed is not None:
                return parsed
    return None


def _updated_at(path: Path) -> datetime | None:
    return _payload_updated_at(path) or _file_mtime(path)


def _latest(paths: Iterable[Path]) -> datetime | None:
    values = [_updated_at(path) for path in paths]
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _has_jsonl_rows(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return any(line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return False


def _project_dirs() -> list[Path]:
    if not PROJECTS_DATA_DIR.exists():
        return []
    return sorted(path for path in PROJECTS_DATA_DIR.iterdir() if path.is_dir() and (path / "project.json").exists())


def _project_name(directory: Path) -> str:
    payload = _read_json(directory / "project.json")
    if isinstance(payload, dict):
        return str(payload.get("name") or directory.name)
    return directory.name


def _artifact(
    *,
    key: str,
    label: str,
    category: str,
    path: Path | None,
    depends_on: list[str] | None = None,
    stale_after: datetime | None = None,
    stale_reason: str | None = None,
    detail: str | None = None,
    action_if_missing: bool = False,
    exists: bool | None = None,
) -> ArtifactDependency:
    exists_value = path.exists() if exists is None and path is not None else bool(exists)
    updated = _updated_at(path) if path is not None and exists_value else None
    status = "fresh"
    severity = "info"
    if not exists_value:
        status = "missing"
        severity = "action" if action_if_missing else "warning"
    elif stale_after is not None and updated is not None and stale_after > updated:
        status = "stale"
        severity = "warning"
    elif updated is None:
        status = "unknown"
        severity = "warning"
    return ArtifactDependency(
        key=key,
        label=label,
        category=category,
        path=str(path) if path is not None else None,
        exists=exists_value,
        status=status,
        severity=severity,
        updated_at=updated,
        stale_after=stale_after,
        depends_on=depends_on or [],
        stale_reason=stale_reason if status == "stale" else None,
        detail=detail,
    )


def _append_project_artifacts(artifacts: list[ArtifactDependency]) -> None:
    for directory in _project_dirs():
        project_id = directory.name
        label_prefix = _project_name(directory)
        tracking_path = directory / "tracking.json"
        tracking_cleaned_path = directory / "tracking_cleaned.json"
        review_patch_path = directory / "tracking_review_patch.json"
        calibration_path = directory / "calibration.json"
        projected_path = directory / "projected_tracks.json"
        aliases_path = directory / "player_aliases.json"
        prompts_path = directory / "quiz_prompts.json"
        attempts_path = directory / "quiz_attempts.json"

        review_updated = _updated_at(review_patch_path)
        tracking_source_updated = _latest([calibration_path, tracking_cleaned_path if tracking_cleaned_path.exists() else tracking_path])
        artifacts.extend(
            [
                _artifact(key=f"project:{project_id}:project", label=f"{label_prefix} project", category="project", path=directory / "project.json"),
                _artifact(key=f"project:{project_id}:calibration", label=f"{label_prefix} calibration", category="analysis", path=calibration_path),
                _artifact(key=f"project:{project_id}:tracking", label=f"{label_prefix} tracking", category="analysis", path=tracking_path),
                _artifact(key=f"project:{project_id}:tracking_review_patch", label=f"{label_prefix} tracking review patch", category="analysis", path=review_patch_path),
                _artifact(
                    key=f"project:{project_id}:tracking_cleaned",
                    label=f"{label_prefix} cleaned tracking",
                    category="analysis",
                    path=tracking_cleaned_path,
                    depends_on=[f"project:{project_id}:tracking_review_patch"],
                    stale_after=review_updated,
                    stale_reason="tracking_review_patch.json is newer than tracking_cleaned.json.",
                ),
                _artifact(
                    key=f"project:{project_id}:projected_tracks",
                    label=f"{label_prefix} projected tracks",
                    category="analysis",
                    path=projected_path,
                    depends_on=[f"project:{project_id}:calibration", f"project:{project_id}:tracking_cleaned", f"project:{project_id}:tracking"],
                    stale_after=tracking_source_updated,
                    stale_reason="Calibration or tracking is newer than projected_tracks.json.",
                ),
                _artifact(key=f"project:{project_id}:player_aliases", label=f"{label_prefix} player aliases", category="analysis", path=aliases_path, depends_on=[f"project:{project_id}:tracking_cleaned", f"project:{project_id}:tracking"]),
                _artifact(key=f"project:{project_id}:quiz_prompts", label=f"{label_prefix} quiz prompts", category="analysis", path=prompts_path),
                _artifact(key=f"project:{project_id}:quiz_attempts", label=f"{label_prefix} quiz attempts", category="analysis", path=attempts_path, depends_on=[f"project:{project_id}:quiz_prompts"]),
            ]
        )


def _append_global_artifacts(artifacts: list[ArtifactDependency]) -> None:
    project_dirs = _project_dirs()
    prompt_paths = [directory / "quiz_prompts.json" for directory in project_dirs]
    attempt_paths = [directory / "quiz_attempts.json" for directory in project_dirs]
    alias_paths = [directory / "player_aliases.json" for directory in project_dirs]
    active_rules = DECISION_RULES_DIR / "active_rule_set.json"
    decision_events = DATASETS_DIR / "player_value" / "player_decision_events.jsonl"
    player_value = DATASETS_DIR / "player_value" / "player_value_summary.json"
    trends = DATASETS_DIR / "player_value" / "player_value_trends.json"
    diagnostics = DATASETS_DIR / "decision" / "decision_diagnostics.json"
    feedback = PRACTICE_EXECUTIONS_DIR / "practice_feedback_signals.jsonl"
    recommendations = DRILLS_DIR / "latest_recommendations.json"
    practice_plans = PRACTICE_PLANS_DIR / "index.json"
    coach_reports = REPORTS_DIR / "index.json"

    decision_inputs_updated = _latest([*prompt_paths, *attempt_paths, active_rules])
    player_value_inputs_updated = _latest([decision_events, *alias_paths])
    recommendation_inputs_updated = _latest([player_value, diagnostics, feedback])
    recommendations_updated = _updated_at(recommendations)
    report_inputs_updated = _latest([player_value, trends, diagnostics, recommendations])

    artifacts.extend(
        [
            _artifact(key="datasets:recognition_manifest", label="Recognition dataset manifest", category="dataset/model", path=DATASETS_DIR / "recognition" / "dataset_manifest.json"),
            _artifact(key="datasets:decision_manifest", label="Decision dataset manifest", category="dataset/model", path=DATASETS_DIR / "decision" / "dataset_manifest.json"),
            _artifact(key="datasets:player_value_manifest", label="Player Value dataset manifest", category="dataset/model", path=DATASETS_DIR / "player_value" / "dataset_manifest.json"),
            _artifact(key="models:recognition_registry", label="Recognition model registry", category="dataset/model", path=RECOGNITION_MODELS_DIR / "model_registry.json"),
            _artifact(key="decision:active_rule_set", label="Active decision rule set", category="analysis", path=active_rules),
            _artifact(
                key="player_value:decision_events",
                label="Player decision events",
                category="dataset/model",
                path=decision_events,
                exists=_has_jsonl_rows(decision_events),
                depends_on=["project:*:quiz_prompts", "project:*:quiz_attempts", "decision:active_rule_set"],
                stale_after=decision_inputs_updated,
                stale_reason="Quiz prompts, quiz attempts, or active_rule_set.json are newer than player_decision_events.jsonl.",
                action_if_missing=True,
            ),
            _artifact(
                key="player_value:summary",
                label="Player Value summary",
                category="dataset/model",
                path=player_value,
                depends_on=["player_value:decision_events", "project:*:player_aliases"],
                stale_after=player_value_inputs_updated,
                stale_reason="Decision events or player aliases are newer than player_value_summary.json.",
                action_if_missing=True,
            ),
            _artifact(key="player_value:trends", label="Player Value trends", category="dataset/model", path=trends, depends_on=["player_value:summary"]),
            _artifact(key="decision:diagnostics", label="Decision diagnostics", category="report", path=diagnostics, depends_on=["player_value:decision_events"]),
            _artifact(key="practice:feedback_signals", label="Practice feedback signals", category="workflow/training/report", path=feedback, exists=_has_jsonl_rows(feedback)),
            _artifact(
                key="drills:recommendations",
                label="Drill recommendations",
                category="workflow/training/report",
                path=recommendations,
                depends_on=["player_value:summary", "decision:diagnostics", "practice:feedback_signals"],
                stale_after=recommendation_inputs_updated,
                stale_reason="Player Value, diagnostics, or feedback signals are newer than latest_recommendations.json.",
                action_if_missing=True,
            ),
            _artifact(
                key="practice:plans",
                label="Practice plan index",
                category="workflow/training/report",
                path=practice_plans,
                depends_on=["drills:recommendations"],
                stale_after=recommendations_updated,
                stale_reason="Drill recommendations are newer than the practice plan index.",
                action_if_missing=True,
            ),
            _artifact(
                key="reports:coach",
                label="Coach report index",
                category="workflow/training/report",
                path=coach_reports,
                depends_on=["player_value:summary", "player_value:trends", "decision:diagnostics", "drills:recommendations"],
                stale_after=report_inputs_updated,
                stale_reason="Player Value, trends, diagnostics, or recommendations are newer than coach reports.",
                action_if_missing=True,
            ),
            _artifact(key="review:queue", label="Review queue", category="analysis", path=REVIEW_QUEUE_DIR / "review_queue.json"),
            _artifact(key="reference:quiz_prompt_drafts", label="Reference quiz prompt drafts", category="project", path=REFERENCE_VIDEOS_DIR / "quiz_prompt_drafts.json"),
            _artifact(key="reference:decision_rule_drafts", label="Reference decision rule drafts", category="project", path=REFERENCE_VIDEOS_DIR / "decision_rule_drafts.json"),
        ]
    )


def _workflow_input_paths(workflow: Workflow) -> list[Path]:
    paths: list[Path] = [
        DATASETS_DIR / "player_value" / "player_decision_events.jsonl",
        DATASETS_DIR / "player_value" / "player_value_summary.json",
        DATASETS_DIR / "player_value" / "player_value_trends.json",
        DATASETS_DIR / "decision" / "decision_diagnostics.json",
        DRILLS_DIR / "latest_recommendations.json",
        PRACTICE_PLANS_DIR / "index.json",
        PRACTICE_EXECUTIONS_DIR / "index.json",
        PRACTICE_EXECUTIONS_DIR / "practice_feedback_signals.jsonl",
        REPORTS_DIR / "index.json",
        REVIEW_QUEUE_DIR / "review_queue.json",
        RECOGNITION_MODELS_DIR / "model_registry.json",
    ]
    project_dirs = [PROJECTS_DATA_DIR / workflow.project_id] if workflow.project_id else _project_dirs()
    for directory in project_dirs:
        paths.extend(
            [
                directory / "tracking.json",
                directory / "tracking_cleaned.json",
                directory / "tracking_review_patch.json",
                directory / "projected_tracks.json",
                directory / "player_aliases.json",
                directory / "quiz_prompts.json",
                directory / "quiz_attempts.json",
            ]
        )
    return paths


def _append_workflow_artifacts(artifacts: list[ArtifactDependency], warnings: list[str]) -> None:
    if not WORKFLOWS_DIR.exists():
        artifacts.append(_artifact(key="workflows:index", label="Workflow index", category="workflow/training/report", path=WORKFLOWS_DIR / "index.json"))
        return
    artifacts.append(_artifact(key="workflows:index", label="Workflow index", category="workflow/training/report", path=WORKFLOWS_DIR / "index.json"))
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            workflow = Workflow.model_validate(_read_json(path))
        except (ValidationError, TypeError):
            warnings.append(f"Unreadable workflow artifact at {path}.")
            artifacts.append(_artifact(key=f"workflow:{path.stem}", label=f"Workflow {path.stem}", category="workflow/training/report", path=path, detail="Workflow JSON could not be validated."))
            continue
        input_updated = _latest(_workflow_input_paths(workflow))
        artifacts.append(
            _artifact(
                key=f"workflow:{workflow.workflow_id}",
                label=f"Workflow: {workflow.title}",
                category="workflow/training/report",
                path=path,
                depends_on=["project artifacts", "player value", "training", "reports"],
                stale_after=input_updated,
                stale_reason="One or more underlying artifacts changed after the workflow updated_at timestamp.",
                detail=f"Status: {workflow.status}",
            )
        )


def build_artifact_map() -> ArtifactMapResponse:
    """Return artifact map without rebuilding or mutating any artifacts."""

    artifacts: list[ArtifactDependency] = []
    warnings: list[str] = []
    _append_project_artifacts(artifacts)
    _append_global_artifacts(artifacts)
    _append_workflow_artifacts(artifacts, warnings)

    status_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for artifact in artifacts:
        status_counts[artifact.status] = status_counts.get(artifact.status, 0) + 1
        severity_counts[artifact.severity] = severity_counts.get(artifact.severity, 0) + 1
    stale_count = status_counts.get("stale", 0)
    missing_count = status_counts.get("missing", 0)
    if stale_count:
        warnings.append(f"{stale_count} artifact(s) are stale relative to deterministic dependency checks.")
    if missing_count:
        warnings.append(f"{missing_count} artifact(s) are missing; no rebuilds were triggered.")

    return ArtifactMapResponse(
        generated_at=utc_now(),
        artifacts=artifacts,
        status_counts=status_counts,
        severity_counts=severity_counts,
        stale_artifact_count=stale_count,
        missing_artifact_count=missing_count,
        warnings=warnings,
    )
