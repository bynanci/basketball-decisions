"""Coach report export routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.api.common import api_error
from app.models import CoachReport, CoachReportBuildRequest, CoachReportListResponse
from app.models.llm_summary import EvidenceLockedSummaryRequest, EvidenceLockedSummaryResponse
from app.services.coach_report_service import build_coach_report, get_coach_report, list_coach_reports
from app.services.evidence_locked_llm_service import create_evidence_locked_summary, get_evidence_locked_summary

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


@router.post("/evidence-locked-summary", response_model=EvidenceLockedSummaryResponse)
def create_evidence_locked_summary_route(request: EvidenceLockedSummaryRequest) -> EvidenceLockedSummaryResponse:
    try:
        return create_evidence_locked_summary(request)
    except FileNotFoundError:
        raise api_error(404, "COACH_REPORT_NOT_FOUND", "Coach report was not found.", {"report_id": request.report_id}, "Choose a report_id from GET /api/reports/coach.")
    except ValueError as exc:
        raise api_error(400, "LLM_PROVIDER_UNSUPPORTED", str(exc), {"provider": request.provider}, "Use provider='mock' for this prototype.")


@router.get("/evidence-locked-summary/{summary_id}", response_model=EvidenceLockedSummaryResponse)
def read_evidence_locked_summary(summary_id: str) -> EvidenceLockedSummaryResponse:
    summary = get_evidence_locked_summary(summary_id)
    if summary is None:
        raise api_error(404, "LLM_SUMMARY_NOT_FOUND", "Evidence-locked summary was not found.", {"summary_id": summary_id}, "Create it via POST /api/reports/coach/evidence-locked-summary.")
    return summary


@router.get("/evidence-locked-summary/{summary_id}/markdown", response_class=PlainTextResponse)
def read_evidence_locked_summary_markdown(summary_id: str) -> PlainTextResponse:
    summary = read_evidence_locked_summary(summary_id)
    body = (
        f"# LLM-assisted wording\n\n{summary.llm_assisted_wording}\n\n"
        "## Validation\n"
        f"- warnings_preserved: {summary.validation.warnings_preserved}\n"
        f"- scores_unchanged: {summary.validation.scores_unchanged}\n"
        f"- evidence_refs_preserved: {summary.validation.evidence_refs_preserved}\n"
        f"- prohibited_phrases: {', '.join(summary.validation.prohibited_phrases) if summary.validation.prohibited_phrases else 'none'}\n"
    )
    return PlainTextResponse(body, media_type="text/markdown; charset=utf-8")

