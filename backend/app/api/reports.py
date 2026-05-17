"""Coach report export routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.api.common import api_error
from app.models import CoachReport, CoachReportBuildRequest, CoachReportListResponse
from app.services.coach_report_service import build_coach_report, get_coach_report, list_coach_reports

router = APIRouter(prefix="/reports/coach", tags=["coach-reports"])


@router.post("", response_model=CoachReport)
def create_coach_report(request: CoachReportBuildRequest) -> CoachReport:
    return build_coach_report(request)


@router.get("", response_model=CoachReportListResponse)
def list_reports() -> CoachReportListResponse:
    return list_coach_reports()


@router.get("/{report_id}", response_model=CoachReport)
def read_report(report_id: str) -> CoachReport:
    report = get_coach_report(report_id)
    if report is None:
        raise api_error(404, "COACH_REPORT_NOT_FOUND", "Coach report was not found.", {"report_id": report_id}, "Choose a report_id from GET /api/reports/coach.")
    return report


@router.get("/{report_id}/markdown", response_class=PlainTextResponse)
def read_report_markdown(report_id: str) -> PlainTextResponse:
    report = read_report(report_id)
    return PlainTextResponse(report.markdown, media_type="text/markdown; charset=utf-8")


@router.get("/{report_id}/json", response_model=CoachReport)
def read_report_json(report_id: str) -> CoachReport:
    return read_report(report_id)
