"""Evidence-locked LLM rewrite service for coach report summaries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from app.models import CoachReport
from app.models.llm_summary import EvidenceLockedSummaryRequest, EvidenceLockedSummaryResponse, EvidenceLockedSummaryValidation
from app.services.coach_report_service import get_coach_report

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LLM_SUMMARIES_DIR = APP_DATA_DIR / "reports" / "llm_summaries"
LLM_SUMMARY_INDEX_PATH = LLM_SUMMARIES_DIR / "index.json"

PROHIBITED_PATTERNS = [r"official scouting grade", r"real player", r"nba scout", r"john doe", r"jane doe"]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _find_scores(text: str) -> set[str]:
    return set(re.findall(r"\b(?:score|confidence)\s*[:]?\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE))


def _collect_evidence_refs(report: CoachReport) -> set[str]:
    refs: set[str] = set()
    for section in report.sections:
        section_text = section.markdown
        refs.update(re.findall(r"\b[A-Za-z0-9_-]+\.jsonl?\b", section_text))
        refs.update(re.findall(r"\b(?:prompt|attempt|project|player|build|rule|source)-[A-Za-z0-9_-]+\b", section_text))
    return refs


def _mock_rewrite(report: CoachReport) -> str:
    lines = [
        "LLM-assisted wording (mock provider; evidence-locked):",
        "Keep this as a coach-facing rewrite only; no new facts were introduced.",
    ]
    for section in report.sections[:4]:
        lines.append(f"- {section.heading}: {section.markdown.splitlines()[0]}")
    return "\n".join(lines)


def _validate(report: CoachReport, rewritten: str) -> EvidenceLockedSummaryValidation:
    original = report.markdown
    warnings_ok = all(w in rewritten for w in report.warnings) if report.warnings else True
    original_scores = _find_scores(original)
    rewritten_scores = _find_scores(rewritten)
    scores_ok = original_scores.issubset(rewritten_scores) if original_scores else True
    original_refs = _collect_evidence_refs(report)
    refs_ok = original_refs.issubset(set(re.findall(r"\b[A-Za-z0-9_.-]+\b", rewritten))) if original_refs else True
    prohibited: list[str] = []
    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, rewritten, flags=re.IGNORECASE):
            prohibited.append(pattern)
    return EvidenceLockedSummaryValidation(
        warnings_preserved=warnings_ok,
        scores_unchanged=scores_ok,
        evidence_refs_preserved=refs_ok,
        prohibited_phrases=prohibited,
    )


def create_evidence_locked_summary(request: EvidenceLockedSummaryRequest) -> EvidenceLockedSummaryResponse:
    if request.provider != "mock":
        raise ValueError("Unsupported provider. Only 'mock' is available in this prototype.")
    report = get_coach_report(request.report_id)
    if report is None:
        raise FileNotFoundError(request.report_id)

    rewritten = _mock_rewrite(report)
    validation = _validate(report, rewritten)
    summary_id = f"llm-summary-{uuid4().hex[:10]}"
    payload = EvidenceLockedSummaryResponse(
        summary_id=summary_id,
        report_id=report.report_id,
        provider=request.provider,
        created_by=request.created_by,
        llm_assisted_wording=rewritten,
        warnings=list(report.warnings),
        validation=validation,
        source_report_json_path=report.json_path,
        json_path=str(LLM_SUMMARIES_DIR / f"{summary_id}.json"),
    )
    _write_json(LLM_SUMMARIES_DIR / f"{summary_id}.json", payload.model_dump(mode="json"))
    index = {"summaries": [], "updated_at": payload.created_at.isoformat()}
    if LLM_SUMMARY_INDEX_PATH.exists():
        index = json.loads(LLM_SUMMARY_INDEX_PATH.read_text(encoding="utf-8"))
    index.setdefault("summaries", []).insert(0, {"summary_id": summary_id, "report_id": report.report_id, "created_at": payload.created_at.isoformat(), "provider": request.provider, "json_path": payload.json_path})
    index["updated_at"] = payload.created_at.isoformat()
    _write_json(LLM_SUMMARY_INDEX_PATH, index)
    return payload


def get_evidence_locked_summary(summary_id: str) -> EvidenceLockedSummaryResponse | None:
    path = LLM_SUMMARIES_DIR / f"{summary_id}.json"
    if not path.exists():
        return None
    return EvidenceLockedSummaryResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))
