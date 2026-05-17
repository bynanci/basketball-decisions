"""Practice execution and deterministic feedback routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error
from app.models import (
    PracticeExecution,
    PracticeExecutionCreateRequest,
    PracticeExecutionListResponse,
    PracticeExecutionUpdateRequest,
    PracticeFeedbackSignalsResponse,
    PracticeFeedbackSummary,
)
from app.services.practice_execution_service import (
    create_practice_execution,
    get_feedback_summary,
    get_practice_execution,
    list_feedback_signals,
    list_practice_executions,
    update_practice_execution,
)

router = APIRouter(prefix="/practice-executions", tags=["practice-executions"])


@router.post("", response_model=PracticeExecution)
def create_execution(request: PracticeExecutionCreateRequest) -> PracticeExecution:
    execution = create_practice_execution(request)
    if execution is None:
        raise api_error(404, "PRACTICE_PLAN_NOT_FOUND", "Practice plan was not found.", {"plan_id": request.plan_id}, "Choose a plan_id from GET /api/practice-plans.")
    return execution


@router.get("", response_model=PracticeExecutionListResponse)
def list_executions() -> PracticeExecutionListResponse:
    return list_practice_executions()


@router.get("/signals", response_model=PracticeFeedbackSignalsResponse)
def read_feedback_signals() -> PracticeFeedbackSignalsResponse:
    return list_feedback_signals()


@router.get("/{execution_id}", response_model=PracticeExecution)
def read_execution(execution_id: str) -> PracticeExecution:
    execution = get_practice_execution(execution_id)
    if execution is None:
        raise api_error(404, "PRACTICE_EXECUTION_NOT_FOUND", "Practice execution was not found.", {"execution_id": execution_id}, "Choose an execution_id from GET /api/practice-executions.")
    return execution


@router.put("/{execution_id}", response_model=PracticeExecution)
def update_execution(execution_id: str, request: PracticeExecutionUpdateRequest) -> PracticeExecution:
    execution = update_practice_execution(execution_id, request)
    if execution is None:
        raise api_error(404, "PRACTICE_EXECUTION_NOT_FOUND", "Practice execution was not found.", {"execution_id": execution_id}, "Choose an execution_id from GET /api/practice-executions.")
    return execution


@router.get("/{execution_id}/feedback-summary", response_model=PracticeFeedbackSummary)
def read_feedback_summary(execution_id: str) -> PracticeFeedbackSummary:
    summary = get_feedback_summary(execution_id)
    if summary is None:
        raise api_error(404, "PRACTICE_EXECUTION_NOT_FOUND", "Practice execution was not found.", {"execution_id": execution_id}, "Choose an execution_id from GET /api/practice-executions.")
    return summary
