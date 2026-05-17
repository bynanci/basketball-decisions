"""Drill catalog and deterministic recommendation routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error
from app.models import DrillCatalogResponse, DrillRecommendationRequest, DrillRecommendationResponse
from app.services.drill_recommendation_service import build_drill_recommendations, get_latest_drill_recommendations, load_drill_catalog

router = APIRouter(prefix="/drills", tags=["drills"])


@router.get("/catalog", response_model=DrillCatalogResponse)
def read_drill_catalog() -> DrillCatalogResponse:
    return load_drill_catalog()


@router.post("/recommendations", response_model=DrillRecommendationResponse)
def create_drill_recommendations(request: DrillRecommendationRequest) -> DrillRecommendationResponse:
    return build_drill_recommendations(request)


@router.get("/recommendations/latest", response_model=DrillRecommendationResponse)
def read_latest_drill_recommendations() -> DrillRecommendationResponse:
    latest = get_latest_drill_recommendations()
    if latest is None:
        raise api_error(404, "DRILL_RECOMMENDATIONS_NOT_FOUND", "No drill recommendations have been generated yet.", {}, "POST /api/drills/recommendations first.")
    return latest
