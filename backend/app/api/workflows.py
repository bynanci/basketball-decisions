"""Guided workflow orchestration routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error
from app.models import Workflow, WorkflowFromActionRequest, WorkflowListResponse, WorkflowStartRequest, WorkflowStepUpdateRequest
from app.services.workflow_orchestrator_service import create_workflow, create_workflow_from_action, get_workflow, list_workflows, refresh_workflow, update_workflow_step

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=Workflow)
def start_workflow(request: WorkflowStartRequest) -> Workflow:
    return create_workflow(request)


@router.post("/from-action", response_model=Workflow)
def start_workflow_from_action(request: WorkflowFromActionRequest) -> Workflow:
    return create_workflow_from_action(request)


@router.get("", response_model=WorkflowListResponse)
def read_workflows() -> WorkflowListResponse:
    return list_workflows()


@router.get("/{workflow_id}", response_model=Workflow)
def read_workflow(workflow_id: str) -> Workflow:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise api_error(404, "WORKFLOW_NOT_FOUND", "Guided workflow was not found.", {"workflow_id": workflow_id}, "Choose a workflow_id from GET /api/workflows.")
    return workflow


@router.put("/{workflow_id}/refresh", response_model=Workflow)
def refresh_existing_workflow(workflow_id: str) -> Workflow:
    workflow = refresh_workflow(workflow_id)
    if workflow is None:
        raise api_error(404, "WORKFLOW_NOT_FOUND", "Guided workflow was not found.", {"workflow_id": workflow_id}, "Choose a workflow_id from GET /api/workflows.")
    return workflow


@router.put("/{workflow_id}/steps/{step_id}", response_model=Workflow)
def update_existing_workflow_step(workflow_id: str, step_id: str, request: WorkflowStepUpdateRequest) -> Workflow:
    try:
        workflow = update_workflow_step(workflow_id, step_id, request)
    except KeyError:
        raise api_error(404, "WORKFLOW_STEP_NOT_FOUND", "Guided workflow step was not found.", {"workflow_id": workflow_id, "step_id": step_id}, "Choose a step_id from GET /api/workflows/{workflow_id}.") from None
    if workflow is None:
        raise api_error(404, "WORKFLOW_NOT_FOUND", "Guided workflow was not found.", {"workflow_id": workflow_id}, "Choose a workflow_id from GET /api/workflows.")
    return workflow
