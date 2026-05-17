"""Practice plan builder and export routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.api.common import api_error
from app.models import PracticePlan, PracticePlanBuildRequest, PracticePlanListResponse
from app.services.practice_plan_service import build_practice_plan, get_practice_plan, list_practice_plans

router = APIRouter(prefix="/practice-plans", tags=["practice-plans"])


@router.post("", response_model=PracticePlan)
def create_practice_plan(request: PracticePlanBuildRequest) -> PracticePlan:
    return build_practice_plan(request)


@router.get("", response_model=PracticePlanListResponse)
def list_plans() -> PracticePlanListResponse:
    return list_practice_plans()


@router.get("/{plan_id}", response_model=PracticePlan)
def read_plan(plan_id: str) -> PracticePlan:
    plan = get_practice_plan(plan_id)
    if plan is None:
        raise api_error(404, "PRACTICE_PLAN_NOT_FOUND", "Practice plan was not found.", {"plan_id": plan_id}, "Choose a plan_id from GET /api/practice-plans.")
    return plan


@router.get("/{plan_id}/markdown", response_class=PlainTextResponse)
def read_plan_markdown(plan_id: str) -> PlainTextResponse:
    plan = read_plan(plan_id)
    return PlainTextResponse(plan.markdown, media_type="text/markdown; charset=utf-8")


@router.get("/{plan_id}/json", response_model=PracticePlan)
def read_plan_json(plan_id: str) -> PracticePlan:
    return read_plan(plan_id)
