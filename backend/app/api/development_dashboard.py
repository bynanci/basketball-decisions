"""Development progress dashboard route."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import DevelopmentDashboardResponse
from app.services.development_dashboard_service import build_development_dashboard

router = APIRouter(prefix="/development-dashboard", tags=["development-dashboard"])


@router.get("", response_model=DevelopmentDashboardResponse)
def read_development_dashboard() -> DevelopmentDashboardResponse:
    return build_development_dashboard()
