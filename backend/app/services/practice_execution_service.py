"""Persist and summarize local practice execution sessions.

All feedback is deterministic from coach-entered execution data. The service
copies practice-plan block metadata into execution blocks so updates never
mutate the original saved plan.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.models import (
    PracticeExecution,
    PracticeExecutionBlock,
    PracticeExecutionCreateRequest,
    PracticeExecutionListItem,
    PracticeExecutionListResponse,
    PracticeExecutionUpdateRequest,
    PracticeFeedbackSignal,
    PracticeFeedbackSignalsResponse,
    PracticeFeedbackSummary,
)
from app.models.base import utc_now
from app.services.practice_plan_service import get_practice_plan

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRACTICE_EXECUTIONS_DIR = APP_DATA_DIR / "practice_executions"
PRACTICE_EXECUTION_INDEX_PATH = PRACTICE_EXECUTIONS_DIR / "index.json"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _execution_id_for(plan_id: str) -> str:
    digest = hashlib.sha256(json.dumps({"plan_id": plan_id, "nonce": uuid4().hex}, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"execution-{digest}"


def _read_index() -> PracticeExecutionListResponse:
    if not PRACTICE_EXECUTION_INDEX_PATH.exists():
        return PracticeExecutionListResponse(executions=[])
    try:
        return PracticeExecutionListResponse.model_validate(json.loads(PRACTICE_EXECUTION_INDEX_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return PracticeExecutionListResponse(executions=[])


def _execution_path(execution_id: str) -> Path:
    return PRACTICE_EXECUTIONS_DIR / f"{execution_id}.json"


def _summary_counts(execution: PracticeExecution) -> tuple[float, int, int]:
    block_count = len(execution.blocks)
    completed_count = sum(1 for block in execution.blocks if block.status == "COMPLETED")
    skipped_count = sum(1 for block in execution.blocks if block.status == "SKIPPED")
    modified_count = sum(1 for block in execution.blocks if block.status == "MODIFIED")
    completion_rate = round(completed_count / block_count, 3) if block_count else 0
    return completion_rate, skipped_count, modified_count


def _index_item(execution: PracticeExecution) -> PracticeExecutionListItem:
    completion_rate, skipped_count, modified_count = _summary_counts(execution)
    return PracticeExecutionListItem(
        execution_id=execution.execution_id,
        plan_id=execution.plan_id,
        plan_title=execution.plan_title,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
        started_by=execution.started_by,
        completed_at=execution.completed_at,
        planned_duration_minutes=execution.planned_duration_minutes,
        completion_rate=completion_rate,
        skipped_count=skipped_count,
        modified_count=modified_count,
        json_path=execution.json_path,
    )


def _save_execution(execution: PracticeExecution) -> PracticeExecution:
    execution.updated_at = utc_now()
    _write_json(_execution_path(execution.execution_id), execution.model_dump(mode="json"))
    index = _read_index()
    index.executions = [item for item in index.executions if item.execution_id != execution.execution_id]
    index.executions.append(_index_item(execution))
    index.executions.sort(key=lambda item: item.updated_at, reverse=True)
    index.updated_at = utc_now()
    _write_json(PRACTICE_EXECUTION_INDEX_PATH, index.model_dump(mode="json"))
    return execution


def create_practice_execution(request: PracticeExecutionCreateRequest) -> PracticeExecution | None:
    plan = get_practice_plan(request.plan_id)
    if plan is None:
        return None
    execution_id = _execution_id_for(plan.plan_id)
    blocks = [
        PracticeExecutionBlock(
            block_id=f"exec-{block.block_id}",
            plan_block_id=block.block_id,
            block_type=block.block_type,
            title=block.title,
            planned_start_minute=block.start_minute,
            planned_end_minute=block.end_minute,
            planned_duration_minutes=block.duration_minutes,
            drill_id=block.drill_id,
            recommendation_id=block.recommendation_id,
            success_metrics=list(block.success_metrics),
            metric_results=[{"metric": metric, "met": False} for metric in block.success_metrics],
        )
        for block in plan.blocks
    ]
    execution = PracticeExecution(
        execution_id=execution_id,
        plan_id=plan.plan_id,
        plan_title=plan.title,
        started_by=request.started_by,
        notes=request.notes,
        project_id=plan.project_id,
        player_key=plan.player_key,
        player_keys=list(plan.player_keys),
        planned_duration_minutes=plan.total_duration_minutes,
        blocks=blocks,
        source_plan_json_path=plan.json_path,
        json_path=str(_execution_path(execution_id)),
    )
    return _save_execution(execution)


def list_practice_executions() -> PracticeExecutionListResponse:
    return _read_index()


def get_practice_execution(execution_id: str) -> PracticeExecution | None:
    path = _execution_path(execution_id)
    if not path.exists():
        return None
    try:
        return PracticeExecution.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return None


def update_practice_execution(execution_id: str, request: PracticeExecutionUpdateRequest) -> PracticeExecution | None:
    execution = get_practice_execution(execution_id)
    if execution is None:
        return None
    if request.started_by is not None:
        execution.started_by = request.started_by
    if request.notes is not None:
        execution.notes = request.notes
    if request.completed_at is not None:
        execution.completed_at = request.completed_at
    if request.blocks is not None:
        existing_by_plan_block = {block.plan_block_id: block for block in execution.blocks}
        merged_blocks: list[PracticeExecutionBlock] = []
        for block in request.blocks:
            original = existing_by_plan_block.get(block.plan_block_id)
            if original is None:
                continue
            # Preserve immutable source-plan snapshot fields from the execution record.
            payload = block.model_dump()
            for field in [
                "block_id",
                "plan_block_id",
                "block_type",
                "title",
                "planned_start_minute",
                "planned_end_minute",
                "planned_duration_minutes",
                "drill_id",
                "recommendation_id",
                "success_metrics",
            ]:
                payload[field] = getattr(original, field)
            merged_blocks.append(PracticeExecutionBlock.model_validate(payload))
        if len(merged_blocks) == len(execution.blocks):
            execution.blocks = merged_blocks
    return _save_execution(execution)


def generate_feedback_summary(execution: PracticeExecution) -> PracticeFeedbackSummary:
    completion_rate, skipped_count, modified_count = _summary_counts(execution)
    ratings = [block.outcome_rating for block in execution.blocks if block.outcome_rating is not None]
    average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    met_metrics = [result.metric for block in execution.blocks for result in block.metric_results if result.met]
    missed_metrics = [result.metric for block in execution.blocks for result in block.metric_results if not result.met]
    actual_duration = sum(block.actual_duration_minutes or 0 for block in execution.blocks)
    signals = _signals_for_execution(execution, completion_rate, average_rating, skipped_count, modified_count, missed_metrics, actual_duration)
    actions: list[str] = []
    if skipped_count:
        actions.append("Review skipped blocks and decide whether to repeat their drills in the next plan.")
    if modified_count:
        actions.append("Compare modified blocks with plan evidence before reusing the same timing.")
    if missed_metrics:
        actions.append("Revisit missed success metrics before progressing drill difficulty.")
    if average_rating is not None and average_rating >= 4 and completion_rate >= 0.8:
        actions.append("Progress high-rated completed drills when metrics were met.")
    if actual_duration > execution.planned_duration_minutes:
        actions.append("Shorten the next plan or reduce block count to fit the intended time box.")
    if not actions:
        actions.append("Keep collecting coach notes, player notes, ratings, and metric results after practice.")
    return PracticeFeedbackSummary(
        execution_id=execution.execution_id,
        plan_id=execution.plan_id,
        completion_rate=completion_rate,
        average_block_rating=average_rating,
        met_metrics=met_metrics,
        missed_metrics=missed_metrics,
        skipped_count=skipped_count,
        modified_count=modified_count,
        actual_duration_minutes=actual_duration,
        planned_duration_minutes=execution.planned_duration_minutes,
        recommended_next_actions=actions,
        signals=signals,
    )


def _signals_for_execution(
    execution: PracticeExecution,
    completion_rate: float,
    average_rating: float | None,
    skipped_count: int,
    modified_count: int,
    missed_metrics: list[str],
    actual_duration: int,
) -> list[PracticeFeedbackSignal]:
    signals: list[PracticeFeedbackSignal] = []
    for block in execution.blocks:
        missed_for_block = [result for result in block.metric_results if not result.met]
        if block.status in {"SKIPPED", "INCOMPLETE"}:
            signals.append(PracticeFeedbackSignal(signal_type="REPEAT_DRILL", execution_id=execution.execution_id, block_id=block.block_id, drill_id=block.drill_id, recommendation_id=block.recommendation_id, reason=f"{block.title} was {block.status.lower()}.", severity="action"))
        if block.outcome_rating is not None and block.outcome_rating <= 2:
            signals.append(PracticeFeedbackSignal(signal_type="SIMPLIFY_DRILL", execution_id=execution.execution_id, block_id=block.block_id, drill_id=block.drill_id, recommendation_id=block.recommendation_id, reason=f"{block.title} rating was {block.outcome_rating}/5.", severity="warning"))
        if block.status == "COMPLETED" and block.outcome_rating is not None and block.outcome_rating >= 4 and not missed_for_block:
            signals.append(PracticeFeedbackSignal(signal_type="PROGRESS_DRILL", execution_id=execution.execution_id, block_id=block.block_id, drill_id=block.drill_id, recommendation_id=block.recommendation_id, reason=f"{block.title} was completed with strong rating and met metrics.", severity="info"))
        if any("alias" in (result.notes or "").lower() for result in block.metric_results) or "alias" in (block.coach_notes or "").lower():
            signals.append(PracticeFeedbackSignal(signal_type="REVIEW_ALIAS_ATTRIBUTION", execution_id=execution.execution_id, block_id=block.block_id, drill_id=block.drill_id, recommendation_id=block.recommendation_id, reason=f"{block.title} notes mention alias attribution.", severity="warning"))
    if completion_rate < 0.75 or actual_duration > execution.planned_duration_minutes:
        signals.append(PracticeFeedbackSignal(signal_type="SHORTEN_PLAN", execution_id=execution.execution_id, reason="Completion rate or actual duration indicates the plan may be too long.", severity="action"))
    if len(missed_metrics) >= 3 or (average_rating is not None and average_rating < 3):
        signals.append(PracticeFeedbackSignal(signal_type="REBUILD_DATASETS", execution_id=execution.execution_id, reason="Multiple missed metrics or low average ratings suggest source datasets should be reviewed.", severity="warning"))
    if modified_count > skipped_count and modified_count > 0:
        signals.append(PracticeFeedbackSignal(signal_type="REPEAT_DRILL", execution_id=execution.execution_id, reason="Modified blocks should be repeated after updating constraints.", severity="info"))
    return signals


def get_feedback_summary(execution_id: str) -> PracticeFeedbackSummary | None:
    execution = get_practice_execution(execution_id)
    if execution is None:
        return None
    return generate_feedback_summary(execution)


def list_feedback_signals() -> PracticeFeedbackSignalsResponse:
    signals: list[PracticeFeedbackSignal] = []
    for item in _read_index().executions:
        summary = get_feedback_summary(item.execution_id)
        if summary is not None:
            signals.extend(summary.signals)
    return PracticeFeedbackSignalsResponse(signals=signals, updated_at=utc_now())
