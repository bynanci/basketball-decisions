"""Local guided workflow orchestration without executing underlying operations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models import (
    Workflow,
    WorkflowFromActionRequest,
    WorkflowListItem,
    WorkflowListResponse,
    WorkflowPrerequisiteKey,
    WorkflowPrerequisiteState,
    WorkflowStartRequest,
    WorkflowStep,
    WorkflowStepStatus,
    WorkflowStepUpdateRequest,
    WorkflowTemplate,
    WorkflowTemplateKey,
)
from app.models.base import utc_now

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROJECTS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"
WORKFLOWS_DIR = APP_DATA_DIR / "workflows"
WORKFLOW_INDEX_PATH = WORKFLOWS_DIR / "index.json"
DATASETS_DIR = APP_DATA_DIR / "datasets"
DRILLS_DIR = APP_DATA_DIR / "drills"
PRACTICE_PLANS_DIR = APP_DATA_DIR / "practice_plans"
PRACTICE_EXECUTIONS_DIR = APP_DATA_DIR / "practice_executions"
REPORTS_DIR = APP_DATA_DIR / "reports" / "coach"
REVIEW_QUEUE_DIR = APP_DATA_DIR / "review_queue"
RECOGNITION_MODELS_DIR = APP_DATA_DIR / "models" / "recognition"

PREREQUISITE_LABELS: dict[WorkflowPrerequisiteKey, str] = {
    "has_tracking": "Tracking artifact exists",
    "has_tracking_review": "Tracking review has been saved",
    "has_player_aliases": "Player aliases exist",
    "has_decision_events": "Decision events exist",
    "has_player_value": "Player Value summary exists",
    "has_dataset_health": "Dataset health or manifests exist",
    "has_active_recognition_model": "Active recognition model exists",
    "has_drill_recommendations": "Drill recommendations exist",
    "has_practice_plan": "Practice plan exists",
    "has_practice_execution": "Practice execution exists",
    "has_coach_report": "Coach report exists",
    "has_open_high_priority_review_items": "Open high-priority review items exist",
}


def _step(step_id: str, title: str, description: str, action_label: str, href: str, *, prerequisite_keys: list[WorkflowPrerequisiteKey] | None = None, blocking_prerequisite_keys: list[WorkflowPrerequisiteKey] | None = None, completion_prerequisite_key: WorkflowPrerequisiteKey | None = None) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        title=title,
        description=description,
        action_label=action_label,
        href=href,
        prerequisite_keys=prerequisite_keys or [],
        blocking_prerequisite_keys=blocking_prerequisite_keys or [],
        completion_prerequisite_key=completion_prerequisite_key,
    )


TEMPLATES: dict[WorkflowTemplateKey, WorkflowTemplate] = {
    "BUILD_PLAYER_VALUE": WorkflowTemplate(
        template_key="BUILD_PLAYER_VALUE",
        title="Build Player Value",
        description="Guide local artifacts from tracking review through deterministic Player Value summaries.",
        steps=[
            _step("review-tracking", "Review tracking", "Confirm tracks and aliases before deriving decision events.", "Open tracking review", "/projects/{project_id}/tracking-review", prerequisite_keys=["has_tracking"], blocking_prerequisite_keys=["has_tracking"], completion_prerequisite_key="has_tracking_review"),
            _step("confirm-aliases", "Confirm player aliases", "Ensure player identities are available for attribution.", "Open project", "/projects/{project_id}", prerequisite_keys=["has_tracking_review"], blocking_prerequisite_keys=["has_tracking_review"], completion_prerequisite_key="has_player_aliases"),
            _step("build-decision-events", "Build decision events", "Run the existing Local Lab build when ready; this workflow will not run it for you.", "Open Local Lab", "/local-lab", prerequisite_keys=["has_player_aliases"], blocking_prerequisite_keys=["has_player_aliases"], completion_prerequisite_key="has_decision_events"),
            _step("build-player-value", "Build Player Value", "Use the existing Player Value action after decision events exist.", "Open Player Value", "/player-value", prerequisite_keys=["has_decision_events"], blocking_prerequisite_keys=["has_decision_events"], completion_prerequisite_key="has_player_value"),
        ],
    ),
    "IMPROVE_DATA_QUALITY": WorkflowTemplate(
        template_key="IMPROVE_DATA_QUALITY",
        title="Improve Data Quality",
        description="Work through review queue, dataset health, and recognition readiness artifacts.",
        steps=[
            _step("triage-review", "Triage high-priority review", "Resolve or document high-priority review items before rebuilding datasets.", "Open Review Queue", "/review-queue", prerequisite_keys=["has_open_high_priority_review_items"]),
            _step("refresh-datasets", "Refresh dataset health", "Use Local Lab dataset tools to export or curate datasets.", "Open Local Lab", "/local-lab", completion_prerequisite_key="has_dataset_health"),
            _step("check-model", "Check recognition model", "Register or activate a local recognition model only after data quality is acceptable.", "Open Model Registry", "/model-registry", prerequisite_keys=["has_dataset_health"], blocking_prerequisite_keys=["has_dataset_health"], completion_prerequisite_key="has_active_recognition_model"),
        ],
    ),
    "TRAINING_RECOMMENDATION": WorkflowTemplate(
        template_key="TRAINING_RECOMMENDATION",
        title="Training Recommendation",
        description="Guide Player Value outputs into drill recommendations, practice plans, and execution feedback.",
        steps=[
            _step("confirm-player-value", "Confirm Player Value", "Player Value is needed before recommendations are meaningful.", "Open Player Value", "/player-value", completion_prerequisite_key="has_player_value"),
            _step("build-drills", "Build drill recommendations", "Use deterministic catalog matching; the workflow does not generate advice automatically.", "Open Drills", "/drills", prerequisite_keys=["has_player_value"], blocking_prerequisite_keys=["has_player_value"], completion_prerequisite_key="has_drill_recommendations"),
            _step("build-plan", "Create practice plan", "Create a time-boxed plan from saved recommendations.", "Open Practice Plans", "/practice-plans", prerequisite_keys=["has_drill_recommendations"], blocking_prerequisite_keys=["has_drill_recommendations"], completion_prerequisite_key="has_practice_plan"),
            _step("capture-execution", "Capture execution", "Record completion, skips, and modifications after practice.", "Open Practice Executions", "/practice-executions", prerequisite_keys=["has_practice_plan"], blocking_prerequisite_keys=["has_practice_plan"], completion_prerequisite_key="has_practice_execution"),
        ],
    ),
    "COACH_REPORT": WorkflowTemplate(
        template_key="COACH_REPORT",
        title="Coach Report",
        description="Collect readiness artifacts before exporting a deterministic coach report.",
        steps=[
            _step("confirm-player-value", "Confirm Player Value", "Reports should reference current Player Value summaries.", "Open Player Value", "/player-value", completion_prerequisite_key="has_player_value"),
            _step("confirm-practice", "Confirm practice context", "Reports are more useful with practice plans or execution feedback.", "Open Practice Plans", "/practice-plans", prerequisite_keys=["has_practice_plan"]),
            _step("build-report", "Build coach report", "Use the existing deterministic report export when prerequisites are ready.", "Open Coach Reports", "/reports/coach", prerequisite_keys=["has_player_value"], blocking_prerequisite_keys=["has_player_value"], completion_prerequisite_key="has_coach_report"),
        ],
    ),
    "MODEL_GOVERNANCE": WorkflowTemplate(
        template_key="MODEL_GOVERNANCE",
        title="Model Governance",
        description="Check data health, review items, and active recognition model status.",
        steps=[
            _step("review-health", "Review dataset health", "Inspect dataset counts and warnings before model changes.", "Open Local Lab", "/local-lab", completion_prerequisite_key="has_dataset_health"),
            _step("review-queue", "Review quality queue", "Address open high-priority recognition or attribution items.", "Open Review Queue", "/review-queue", prerequisite_keys=["has_open_high_priority_review_items"]),
            _step("activate-model", "Activate recognition model", "Train/register via the existing model registry workflow; no cloud orchestration is added.", "Open Model Registry", "/model-registry", prerequisite_keys=["has_dataset_health"], blocking_prerequisite_keys=["has_dataset_health"], completion_prerequisite_key="has_active_recognition_model"),
        ],
    ),
}

ACTION_TEMPLATE_MAP: dict[str, WorkflowTemplateKey] = {
    "build-player-value": "BUILD_PLAYER_VALUE",
    "build-player-trends": "BUILD_PLAYER_VALUE",
    "export-datasets": "IMPROVE_DATA_QUALITY",
    "generate-review-queue": "IMPROVE_DATA_QUALITY",
    "train-recognition-baseline": "MODEL_GOVERNANCE",
    "build-drill-recommendations": "TRAINING_RECOMMENDATION",
    "create-practice-plan": "TRAINING_RECOMMENDATION",
    "capture-practice-execution": "TRAINING_RECOMMENDATION",
    "build-coach-report": "COACH_REPORT",
}


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (json.JSONDecodeError, OSError):
        return None


def _has_jsonl_rows(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return any(line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return False


def _project_dirs(project_id: str | None) -> list[Path]:
    if project_id:
        return [PROJECTS_DATA_DIR / project_id]
    if not PROJECTS_DATA_DIR.exists():
        return []
    return [path for path in PROJECTS_DATA_DIR.iterdir() if path.is_dir()]


def _list_has_items(path: Path, key: str) -> bool:
    payload = _read_json(path)
    items = payload.get(key, []) if isinstance(payload, dict) else []
    return isinstance(items, list) and bool(items)


def evaluate_prerequisites(project_id: str | None = None) -> list[WorkflowPrerequisiteState]:
    checks: dict[WorkflowPrerequisiteKey, tuple[bool, str | None, str]] = {}
    project_dirs = _project_dirs(project_id)
    checks["has_tracking"] = (any((d / "tracks.json").exists() or (d / "projected_tracks.json").exists() for d in project_dirs), None, "Found tracks.json or projected_tracks.json in project storage." if project_dirs else "No project storage was found.")
    checks["has_tracking_review"] = (any((d / "tracking_review_patch.json").exists() for d in project_dirs), None, "Found tracking_review_patch.json in project storage.")
    checks["has_player_aliases"] = (any(_list_has_items(d / "player_aliases.json", "aliases") for d in project_dirs), None, "Found at least one player alias.")
    decision_events = DATASETS_DIR / "player_value" / "player_decision_events.jsonl"
    checks["has_decision_events"] = (_has_jsonl_rows(decision_events), str(decision_events), "Found player_decision_events.jsonl rows.")
    player_value = DATASETS_DIR / "player_value" / "player_value_summary.json"
    checks["has_player_value"] = (_list_has_items(player_value, "summaries"), str(player_value), "Found Player Value summaries.")
    dataset_health = DATASETS_DIR / "dataset_health.json"
    rec_manifest = DATASETS_DIR / "recognition" / "dataset_manifest.json"
    dec_manifest = DATASETS_DIR / "decision" / "dataset_manifest.json"
    checks["has_dataset_health"] = (dataset_health.exists() or rec_manifest.exists() or dec_manifest.exists(), str(dataset_health), "Found dataset health or dataset manifests.")
    registry_path = RECOGNITION_MODELS_DIR / "model_registry.json"
    registry = _read_json(registry_path)
    checks["has_active_recognition_model"] = (bool(isinstance(registry, dict) and registry.get("active_version")), str(registry_path), "Found active_version in model registry.")
    checks["has_drill_recommendations"] = (_list_has_items(DRILLS_DIR / "latest_recommendations.json", "recommendations"), str(DRILLS_DIR / "latest_recommendations.json"), "Found latest drill recommendations.")
    checks["has_practice_plan"] = (_list_has_items(PRACTICE_PLANS_DIR / "index.json", "plans"), str(PRACTICE_PLANS_DIR / "index.json"), "Found practice plan index entries.")
    checks["has_practice_execution"] = (_list_has_items(PRACTICE_EXECUTIONS_DIR / "index.json", "executions"), str(PRACTICE_EXECUTIONS_DIR / "index.json"), "Found practice execution index entries.")
    checks["has_coach_report"] = (_list_has_items(REPORTS_DIR / "index.json", "reports"), str(REPORTS_DIR / "index.json"), "Found coach report index entries.")
    review_payload = _read_json(REVIEW_QUEUE_DIR / "review_queue.json")
    review_items = review_payload if isinstance(review_payload, list) else review_payload.get("items", []) if isinstance(review_payload, dict) else []
    has_high = any(isinstance(item, dict) and item.get("priority") == "HIGH" and item.get("status", "OPEN") not in {"RESOLVED", "DISMISSED"} for item in review_items)
    checks["has_open_high_priority_review_items"] = (has_high, str(REVIEW_QUEUE_DIR / "review_queue.json"), "Found open high-priority review items.")
    return [WorkflowPrerequisiteState(key=key, label=PREREQUISITE_LABELS[key], satisfied=value[0], artifact_path=value[1], detail=value[2] if value[0] else f"Missing: {PREREQUISITE_LABELS[key].lower()}.") for key, value in checks.items()]


def _hydrate_href(href: str, project_id: str | None) -> str:
    if "{project_id}" not in href:
        return href
    return href.replace("{project_id}", project_id or "select-project")


def _refresh_status(workflow: Workflow, manual_step_status: dict[str, WorkflowStepStatus] | None = None) -> Workflow:
    prereqs = {item.key: item.satisfied for item in workflow.prerequisites}
    completed = blocked = 0
    for step in workflow.steps:
        if step.step_id in (manual_step_status or {}):
            step.status = manual_step_status[step.step_id]
        elif step.completion_prerequisite_key and prereqs.get(step.completion_prerequisite_key):
            step.status = "COMPLETED"
        elif any(not prereqs.get(key, False) for key in step.blocking_prerequisite_keys):
            step.status = "BLOCKED"
        else:
            step.status = "READY"
        completed += step.status == "COMPLETED"
        blocked += step.status == "BLOCKED"
    if completed == len(workflow.steps):
        workflow.status = "COMPLETED"
    elif blocked:
        workflow.status = "BLOCKED"
    elif completed or any(step.status == "READY" for step in workflow.steps):
        workflow.status = "IN_PROGRESS"
    else:
        workflow.status = "NOT_STARTED"
    workflow.updated_at = utc_now()
    return workflow


def _workflow_path(workflow_id: str) -> Path:
    return WORKFLOWS_DIR / f"{workflow_id}.json"


def _write_workflow(workflow: Workflow) -> Workflow:
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    workflow.storage_path = str(_workflow_path(workflow.workflow_id))
    _workflow_path(workflow.workflow_id).write_text(workflow.model_dump_json(indent=2), encoding="utf-8")
    _write_index()
    return workflow


def _read_workflow(path: Path) -> Workflow | None:
    try:
        return Workflow.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def _all_workflows() -> list[Workflow]:
    if not WORKFLOWS_DIR.exists():
        return []
    workflows = [_read_workflow(path) for path in WORKFLOWS_DIR.glob("workflow-*.json")]
    return sorted([workflow for workflow in workflows if workflow is not None], key=lambda item: item.updated_at, reverse=True)


def _list_item(workflow: Workflow) -> WorkflowListItem:
    return WorkflowListItem(workflow_id=workflow.workflow_id, template_key=workflow.template_key, title=workflow.title, status=workflow.status, project_id=workflow.project_id, player_key=workflow.player_key, source_action_id=workflow.source_action_id, created_at=workflow.created_at, updated_at=workflow.updated_at, completed_step_count=sum(1 for step in workflow.steps if step.status == "COMPLETED"), total_step_count=len(workflow.steps), blocked_step_count=sum(1 for step in workflow.steps if step.status == "BLOCKED"))


def _write_index() -> None:
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    WORKFLOW_INDEX_PATH.write_text(WorkflowListResponse(workflows=[_list_item(workflow) for workflow in _all_workflows()]).model_dump_json(indent=2), encoding="utf-8")


def list_workflows() -> WorkflowListResponse:
    return WorkflowListResponse(workflows=[_list_item(workflow) for workflow in _all_workflows()])


def get_workflow(workflow_id: str) -> Workflow | None:
    return _read_workflow(_workflow_path(workflow_id))


def create_workflow(request: WorkflowStartRequest) -> Workflow:
    template = TEMPLATES[request.template_key]
    created_at = utc_now()
    seed = f"{request.template_key}|{request.project_id or ''}|{request.player_key or ''}|{request.source_action_id or ''}|{created_at.isoformat()}"
    workflow_id = f"workflow-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"
    steps = [deepcopy(step) for step in template.steps]
    for step in steps:
        step.href = _hydrate_href(step.href, request.project_id)
    workflow = Workflow(workflow_id=workflow_id, template_key=template.template_key, title=request.title or template.title, description=template.description, project_id=request.project_id, player_key=request.player_key, source_action_id=request.source_action_id, context=request.context, created_at=created_at, updated_at=created_at, prerequisites=evaluate_prerequisites(request.project_id), steps=steps, warnings=["Guided workflows do not execute operations automatically; use each step link and refresh after artifacts change."])
    return _write_workflow(_refresh_status(workflow))


def create_workflow_from_action(request: WorkflowFromActionRequest) -> Workflow:
    template_key = ACTION_TEMPLATE_MAP.get(request.action_id)
    if template_key is None:
        template_key = "IMPROVE_DATA_QUALITY"
    return create_workflow(WorkflowStartRequest(template_key=template_key, project_id=request.project_id, player_key=request.player_key, title=request.title, source_action_id=request.action_id, context=request.context))


def refresh_workflow(workflow_id: str) -> Workflow | None:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        return None
    manual = {step.step_id: step.status for step in workflow.steps if step.status in {"SKIPPED"}}
    workflow.prerequisites = evaluate_prerequisites(workflow.project_id)
    return _write_workflow(_refresh_status(workflow, manual))


def update_workflow_step(workflow_id: str, step_id: str, request: WorkflowStepUpdateRequest) -> Workflow | None:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        return None
    found = False
    for step in workflow.steps:
        if step.step_id == step_id:
            step.status = request.status
            if request.note:
                step.notes.append(request.note)
            step.updated_at = utc_now()
            found = True
            break
    if not found:
        raise KeyError(step_id)
    manual = {step.step_id: step.status for step in workflow.steps if step.status in {"COMPLETED", "SKIPPED"}}
    workflow.prerequisites = evaluate_prerequisites(workflow.project_id)
    return _write_workflow(_refresh_status(workflow, manual))
