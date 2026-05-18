"""Drill catalog and deterministic recommendation routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.common import api_error
from app.models import DrillCatalogResponse, DrillRecommendationRequest, DrillRecommendationResponse, PracticeFeedbackSignalsResponse
from app.services.drill_recommendation_service import build_drill_recommendations, get_latest_drill_recommendations, load_drill_catalog
from app.services.practice_feedback_signal_service import list_practice_feedback_signals

router = APIRouter(prefix="/drills", tags=["drills"])


@router.get("/catalog", response_model=DrillCatalogResponse)
def read_drill_catalog() -> DrillCatalogResponse:
    return load_drill_catalog()


@router.get("/feedback-signals", response_model=PracticeFeedbackSignalsResponse)
def read_drill_feedback_signals(limit: int | None = Query(default=None, ge=1, le=200)) -> PracticeFeedbackSignalsResponse:
    return list_practice_feedback_signals(limit=limit)


@router.post("/recommendations", response_model=DrillRecommendationResponse)
def create_drill_recommendations(request: DrillRecommendationRequest) -> DrillRecommendationResponse:
    return build_drill_recommendations(request)


@router.get("/recommendations/latest", response_model=DrillRecommendationResponse)
def read_latest_drill_recommendations() -> DrillRecommendationResponse:
    latest = get_latest_drill_recommendations()
    if latest is None:
        raise api_error(404, "DRILL_RECOMMENDATIONS_NOT_FOUND", "No drill recommendations have been generated yet.", {}, "POST /api/drills/recommendations first.")
    return latest
