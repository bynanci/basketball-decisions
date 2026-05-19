"""Deterministic mock synthesis service for external review round feedback."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.models.review_synthesis import (
    LLMReviewIssueProposal,
    LLMReviewSynthesisRequest,
    LLMReviewSynthesisResponse,
    LLMReviewTheme,
    ReviewerFeedbackEntry,
)

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EXTERNAL_REVIEW_SYNTHESIS_DIR = APP_DATA_DIR / "reviews" / "external_review_synthesis"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _theme_key(entry: ReviewerFeedbackEntry) -> str:
    return (entry.category or "general").strip().lower() or "general"


def _build_themes(feedback_entries: list[ReviewerFeedbackEntry]) -> list[LLMReviewTheme]:
    grouped: dict[str, list[ReviewerFeedbackEntry]] = {}
    for entry in feedback_entries:
        grouped.setdefault(_theme_key(entry), []).append(entry)

    themes: list[LLMReviewTheme] = []
    for idx, key in enumerate(sorted(grouped.keys()), start=1):
        group = grouped[key]
        avg_rating = round(sum(item.rating for item in group) / len(group), 2)
        quote_evidence = sorted({item.quote for item in group})
        reviewer_ids = sorted({item.reviewer_id for item in group})
        themes.append(
            LLMReviewTheme(
                theme_id=f"theme-{idx:02d}",
                title=f"{key.replace('_', ' ').title()} Feedback",
                summary=f"Draft synthesis cluster for {key.replace('_', ' ')} based on submitted reviewer quotes.",
                reviewer_ids=reviewer_ids,
                quote_evidence=quote_evidence,
                average_rating=avg_rating,
            )
        )
    return themes


def _build_issue_proposals(themes: list[LLMReviewTheme]) -> list[LLMReviewIssueProposal]:
    proposals: list[LLMReviewIssueProposal] = []
    for theme in themes:
        severity = "high" if theme.average_rating <= 2 else "medium" if theme.average_rating <= 3.5 else "low"
        proposals.append(
            LLMReviewIssueProposal(
                issue_key=f"issue-{theme.theme_id}",
                title=f"Follow-up: {theme.title}",
                description="Draft proposal generated from reviewer-provided quotes; requires ER3 human review approval.",
                severity=severity,
                reviewer_ids=list(theme.reviewer_ids),
                quote_evidence=list(theme.quote_evidence),
                ratings=[theme.average_rating],
            )
        )
    return proposals


def create_external_review_synthesis(request: LLMReviewSynthesisRequest) -> LLMReviewSynthesisResponse:
    if request.provider != "mock":
        raise ValueError("Unsupported provider. External provider is not enabled for this prototype.")

    synthesis_id = f"external-review-synthesis-{uuid4().hex[:10]}"
    themes = _build_themes(request.feedback_entries)
    issue_proposals = _build_issue_proposals(themes)
    json_path = EXTERNAL_REVIEW_SYNTHESIS_DIR / f"{synthesis_id}.json"

    payload = LLMReviewSynthesisResponse(
        synthesis_id=synthesis_id,
        provider=request.provider,
        created_by=request.created_by,
        source_feedback_entries=list(request.feedback_entries),
        themes=themes,
        issue_proposals=issue_proposals,
        json_path=str(json_path),
    )
    _write_json(json_path, payload.model_dump(mode="json"))
    return payload


def get_external_review_synthesis(synthesis_id: str) -> LLMReviewSynthesisResponse | None:
    path = EXTERNAL_REVIEW_SYNTHESIS_DIR / f"{synthesis_id}.json"
    if not path.exists():
        return None
    return LLMReviewSynthesisResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))
