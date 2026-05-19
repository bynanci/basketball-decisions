"""External review synthesis endpoints (draft-only, human-approved workflow)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error
from app.models.review_synthesis import LLMReviewSynthesisRequest, LLMReviewSynthesisResponse
from app.services.external_review_synthesis_service import create_external_review_synthesis, get_external_review_synthesis

router = APIRouter(prefix="/reviews/external-review", tags=["external-review"])


@router.post("/synthesize", response_model=LLMReviewSynthesisResponse)
def synthesize_external_review(request: LLMReviewSynthesisRequest) -> LLMReviewSynthesisResponse:
    try:
        return create_external_review_synthesis(request)
    except ValueError as exc:
        raise api_error(
            400,
            "LLM_PROVIDER_UNSUPPORTED",
            str(exc),
            {"provider": request.provider},
            "Use provider='mock' unless external provider support is explicitly configured.",
        )


@router.get("/synthesis/{synthesis_id}", response_model=LLMReviewSynthesisResponse)
def read_external_review_synthesis(synthesis_id: str) -> LLMReviewSynthesisResponse:
    synthesis = get_external_review_synthesis(synthesis_id)
    if synthesis is None:
        raise api_error(
            404,
            "EXTERNAL_REVIEW_SYNTHESIS_NOT_FOUND",
            "External review synthesis artifact was not found.",
            {"synthesis_id": synthesis_id},
            "Create one via POST /api/reviews/external-review/synthesize.",
        )
    return synthesis
