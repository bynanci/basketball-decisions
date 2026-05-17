"""Build and persist deterministic coach report exports from local artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.models import (
    COACH_REPORT_SECTIONS,
    CoachReport,
    CoachReportArtifactStatus,
    CoachReportBuildRequest,
    CoachReportListItem,
    CoachReportListResponse,
    CoachReportSection,
)
from app.models.base import utc_now
from app.services.drill_recommendation_service import get_latest_drill_recommendations

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROJECTS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"
DATASETS_DIR = APP_DATA_DIR / "datasets"
REPORTS_DIR = APP_DATA_DIR / "reports" / "coach"
DECISION_RULES_DIR = APP_DATA_DIR / "decision_rules"
REVIEW_QUEUE_DIR = APP_DATA_DIR / "review_queue"
SOURCE_GOVERNANCE_DIR = APP_DATA_DIR / "reference_videos"
SOURCE_REGISTRY_PATH = APP_DATA_DIR / "source_registry.json"
REPORT_INDEX_PATH = REPORTS_DIR / "index.json"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _read_json(path: Path, warnings: list[str], statuses: list[CoachReportArtifactStatus], artifact: str) -> Any | None:
    if not path.exists():
        warning = f"Missing artifact: {artifact} was not found at {path}. Section uses available local context only."
        warnings.append(warning)
        statuses.append(CoachReportArtifactStatus(artifact=artifact, path=str(path), available=False, warning=warning))
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warning = f"Unreadable artifact: {artifact} at {path} could not be loaded ({exc.__class__.__name__}). Section uses available local context only."
        warnings.append(warning)
        statuses.append(CoachReportArtifactStatus(artifact=artifact, path=str(path), available=False, warning=warning))
        return None
    statuses.append(CoachReportArtifactStatus(artifact=artifact, path=str(path), available=True))
    return payload


def _read_jsonl(path: Path, warnings: list[str], statuses: list[CoachReportArtifactStatus], artifact: str) -> list[dict[str, Any]]:
    if not path.exists():
        warning = f"Missing artifact: {artifact} was not found at {path}. Section uses available local context only."
        warnings.append(warning)
        statuses.append(CoachReportArtifactStatus(artifact=artifact, path=str(path), available=False, warning=warning))
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
            else:
                warnings.append(f"Skipped non-object row {line_number} in {artifact}.")
    except (json.JSONDecodeError, OSError) as exc:
        warning = f"Unreadable artifact: {artifact} at {path} could not be loaded ({exc.__class__.__name__})."
        warnings.append(warning)
        statuses.append(CoachReportArtifactStatus(artifact=artifact, path=str(path), available=False, warning=warning))
        return []
    statuses.append(CoachReportArtifactStatus(artifact=artifact, path=str(path), available=True))
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if value is None:
        return "—"
    return str(value)


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- No local artifact rows available."


def _filter_summaries(payload: Any, project_id: str | None, player_key: str | None) -> list[dict[str, Any]]:
    summaries = payload.get("summaries", []) if isinstance(payload, dict) else []
    if not isinstance(summaries, list):
        return []
    rows = [row for row in summaries if isinstance(row, dict)]
    if project_id:
        rows = [row for row in rows if row.get("project_id") == project_id]
    if player_key:
        rows = [row for row in rows if row.get("player_key") == player_key]
    return sorted(rows, key=lambda row: (str(row.get("project_id", "")), str(row.get("player_key", ""))))


def _player_value_section(request: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    payload = _read_json(DATASETS_DIR / "player_value" / "player_value_summary.json", warnings, statuses, "Player Value summary")
    rows = _filter_summaries(payload, request.project_id, request.player_key)
    bullets = [
        f"{row.get('project_id', 'unknown')} / {row.get('player_key', 'UNKNOWN')} ({row.get('display_name') or 'local alias only'}): Player Value {_format_number(row.get('player_value_score'))}, confidence {_format_number(row.get('confidence'))}, events {_format_number(row.get('decision_event_count'))}."
        for row in rows[:12]
    ]
    section_warnings = [] if payload is not None else [warnings[-1]]
    if payload is not None and not rows:
        section_warnings.append("No Player Value summaries matched the selected filters.")
    markdown = "This section summarizes local Player Value outputs without official scouting grades or real identity claims.\n\n" + _bullet(bullets)
    return CoachReportSection(name="Player Value", heading="Player Value", markdown=markdown, data={"summaries": rows}, warnings=section_warnings)


def _trends_section(request: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    payload = _read_json(DATASETS_DIR / "player_value" / "player_value_build_index.json", warnings, statuses, "Player Value build index")
    builds = payload.get("builds", []) if isinstance(payload, dict) else []
    if isinstance(builds, list):
        builds = sorted([row for row in builds if isinstance(row, dict)], key=lambda row: str(row.get("generated_at", "")))
    else:
        builds = []
    bullets = [f"Build {row.get('build_id')}: {row.get('summary_count', 0)} summaries, generated {row.get('generated_at')}." for row in builds[-8:]]
    section_warnings = [] if payload is not None else [warnings[-1]]
    if payload is not None and not builds:
        section_warnings.append("No trend history builds are available yet.")
    return CoachReportSection(name="Trends", heading="Trends", markdown="Trend history is derived from immutable local Player Value builds.\n\n" + _bullet(bullets), data={"builds": builds}, warnings=section_warnings)


def _diagnostics_section(_: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    payload = _read_json(DATASETS_DIR / "decision" / "decision_diagnostics.json", warnings, statuses, "Decision diagnostics")
    data = payload if isinstance(payload, dict) else {}
    summary = data.get("global_summary", {}) if isinstance(data.get("global_summary"), dict) else {}
    bullets = [
        f"Attempt count: {_format_number(summary.get('attempt_count'))}.",
        f"Correct rate: {_format_number(summary.get('correct_rate'))}.",
        f"Average role-adjusted score: {_format_number(summary.get('avg_role_adjusted_score'))}.",
    ] if data else []
    section_warnings = [] if payload is not None else [warnings[-1]]
    return CoachReportSection(name="Decision Diagnostics", heading="Decision Diagnostics", markdown="Diagnostics describe local quiz attempts and labels; they are not coach advice generated by an LLM.\n\n" + _bullet(bullets), data=data, warnings=section_warnings)


def _rule_section(_: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    payload = _read_json(DECISION_RULES_DIR / "active_rule_set.json", warnings, statuses, "Active decision rule set")
    rules = payload.get("rules", []) if isinstance(payload, dict) else []
    if isinstance(rules, list):
        rules = sorted([row for row in rules if isinstance(row, dict)], key=lambda row: str(row.get("rule_id", "")))
    else:
        rules = []
    bullets = [f"{row.get('rule_id')}: {row.get('court_role')} / {row.get('situation_type')} weight {_format_number(row.get('weight'))} — {row.get('condition_text', 'No condition text')}." for row in rules[:12]]
    section_warnings = [] if payload is not None else [warnings[-1]]
    if payload is not None and not rules:
        section_warnings.append("Active rule set has no rules.")
    return CoachReportSection(name="Rule Contributions", heading="Rule Contributions", markdown="Rule contributions list transparent local rule weights where available.\n\n" + _bullet(bullets), data={"rule_set": payload or {}, "rules": rules}, warnings=section_warnings)


def _teaching_cases_section(request: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    events = _read_jsonl(DATASETS_DIR / "player_value" / "player_decision_events.jsonl", warnings, statuses, "Player decision events")
    if request.project_id:
        events = [event for event in events if event.get("project_id") == request.project_id]
    events = sorted(events, key=lambda event: (str(event.get("project_id", "")), str(event.get("prompt_id", "")), str(event.get("attempt_id", ""))))
    selected = events[:10]
    bullets = [
        f"{event.get('project_id')} / {event.get('prompt_id')}: selected {event.get('selected_option_id') or 'none'}, correct {event.get('correct_option_id') or 'unknown'}, score {_format_number(event.get('role_adjusted_score', event.get('raw_score')))}."
        for event in selected
    ]
    section_warnings = [] if events else ["No teaching cases were available from local decision events."]
    return CoachReportSection(name="Teaching Cases", heading="Teaching Cases", markdown="Teaching cases are deterministic examples from local quiz events, not newly generated coach advice.\n\n" + _bullet(bullets), data={"events": selected}, warnings=section_warnings)


def _review_findings_section(_: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    queue = _read_json(REVIEW_QUEUE_DIR / "review_queue.json", warnings, statuses, "Review queue")
    actions = _read_json(REVIEW_QUEUE_DIR / "review_action_log.json", warnings, statuses, "Review action log")
    items = queue if isinstance(queue, list) else queue.get("items", []) if isinstance(queue, dict) else []
    logs = actions if isinstance(actions, list) else actions.get("actions", []) if isinstance(actions, dict) else []
    if not isinstance(items, list):
        items = []
    if not isinstance(logs, list):
        logs = []
    bullets = [f"Open review items: {len(items)}.", f"Logged review actions: {len(logs)}."]
    section_warnings = []
    if queue is None:
        section_warnings.append("Review queue artifact is missing.")
    if actions is None:
        section_warnings.append("Review action log artifact is missing.")
    return CoachReportSection(name="Review Findings", heading="Review Findings", markdown="Review findings reflect local human review artifacts and unresolved queues.\n\n" + _bullet(bullets), data={"review_items": items, "review_actions": logs}, warnings=section_warnings)


def _source_governance_section(_: CoachReportBuildRequest, warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    registry = _read_json(SOURCE_REGISTRY_PATH, warnings, statuses, "Source registry")
    refs = _read_json(SOURCE_GOVERNANCE_DIR / "reference_videos.json", warnings, statuses, "Reference videos")
    registry_records = registry if isinstance(registry, list) else registry.get("sources", []) if isinstance(registry, dict) else []
    reference_records = refs if isinstance(refs, list) else refs.get("videos", []) if isinstance(refs, dict) else []
    if not isinstance(registry_records, list):
        registry_records = []
    if not isinstance(reference_records, list):
        reference_records = []
    records = [row for row in registry_records + reference_records if isinstance(row, dict)]
    records = sorted(records, key=lambda row: str(row.get("source_id", row.get("reference_id", row.get("name", "")))))
    bullets = [f"{row.get('title') or row.get('name') or row.get('reference_id') or row.get('source_id')}: usage {row.get('usage_scope', 'unknown')}, rights confirmed {row.get('rights_confirmed', 'unknown')}." for row in records[:12]]
    section_warnings = []
    if registry is None:
        section_warnings.append("Source registry artifact is missing.")
    if refs is None:
        section_warnings.append("Reference video governance artifact is missing.")
    return CoachReportSection(name="Source Governance", heading="Source Governance", markdown="Source governance lists local source metadata and training/redistribution constraints where recorded.\n\n" + _bullet(bullets), data={"sources": records}, warnings=section_warnings)


def _drill_recommendations_section(request: CoachReportBuildRequest, _: list[str], __: list[CoachReportArtifactStatus]) -> CoachReportSection:
    latest = get_latest_drill_recommendations()
    if latest is None:
        return CoachReportSection(
            name="Drill Recommendations",
            heading="Drill Recommendations",
            markdown="No saved drill recommendations are available yet. Build them from the Drills page or POST /api/drills/recommendations.",
            data={"recommendations": []},
            warnings=["No latest drill recommendations artifact was found."],
        )
    recommendations = latest.recommendations
    if request.project_id:
        recommendations = [rec for rec in recommendations if any(ref.project_id == request.project_id for ref in rec.evidence_refs)]
    if request.player_key:
        recommendations = [rec for rec in recommendations if any(ref.player_key == request.player_key for ref in rec.evidence_refs)]
    bullets = [
        f"{rec.priority} priority / {rec.title} ({rec.role or 'any role'}, {rec.situation}): confidence {_format_number(rec.confidence)} — {rec.reason}"
        for rec in recommendations[:8]
    ]
    warnings = []
    if not recommendations:
        warnings.append("Latest drill recommendations exist, but none matched the selected report filters.")
    markdown = "Drill recommendations are deterministic selections from a human-authored local drill catalog; no LLM-generated coaching advice is included.\n\n" + _bullet(bullets)
    return CoachReportSection(
        name="Drill Recommendations",
        heading="Drill Recommendations",
        markdown=markdown,
        data={"recommendations": [rec.model_dump(mode="json") for rec in recommendations]},
        warnings=warnings,
    )


def _methodology_section(request: CoachReportBuildRequest, all_warnings: list[str], statuses: list[CoachReportArtifactStatus]) -> CoachReportSection:
    available = sum(1 for status in statuses if status.available)
    missing = sum(1 for status in statuses if not status.available)
    bullets = [
        "This report is generated deterministically from local JSON/JSONL artifacts.",
        "It does not implement PDF, DOCX, email delivery, or LLM-generated coach advice.",
        "It does not claim official scouting grades and uses only project-scoped local aliases.",
        f"Artifacts available: {available}; artifacts missing or unreadable: {missing}.",
    ]
    if request.notes:
        bullets.append(f"Builder notes: {request.notes}")
    return CoachReportSection(name="Methodology & Limitations", heading="Methodology & Limitations", markdown=_bullet(bullets), data={"artifact_status": [status.model_dump(mode="json") for status in statuses]}, warnings=list(dict.fromkeys(all_warnings)))


_SECTION_BUILDERS = {
    "Player Value": _player_value_section,
    "Trends": _trends_section,
    "Decision Diagnostics": _diagnostics_section,
    "Rule Contributions": _rule_section,
    "Teaching Cases": _teaching_cases_section,
    "Review Findings": _review_findings_section,
    "Source Governance": _source_governance_section,
    "Drill Recommendations": _drill_recommendations_section,
}


def _render_markdown(report_id: str, title: str, created_at: str, sections: list[CoachReportSection], warnings: list[str]) -> str:
    lines = [f"# {title}", "", f"Report ID: `{report_id}`", f"Generated: {created_at}", "", "## Safety Notes", "", "- Uses local project aliases only; no real player identity is asserted beyond those aliases.", "- No official scouting grades are claimed.", "- No LLM-generated coach advice is included."]
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in list(dict.fromkeys(warnings)))
    for section in sections:
        lines.extend(["", f"## {section.heading}", "", section.markdown])
        if section.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in section.warnings)
    return "\n".join(lines).rstrip() + "\n"


def _report_id_for(request: CoachReportBuildRequest, sections: list[CoachReportSection]) -> str:
    digest = hashlib.sha256(_stable_json({"request": request.model_dump(mode="json"), "sections": [s.data for s in sections], "nonce": uuid4().hex}).encode("utf-8")).hexdigest()[:12]
    return f"coach-{digest}"


def _read_index() -> CoachReportListResponse:
    if not REPORT_INDEX_PATH.exists():
        return CoachReportListResponse(reports=[])
    try:
        return CoachReportListResponse.model_validate(json.loads(REPORT_INDEX_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return CoachReportListResponse(reports=[])


def build_coach_report(request: CoachReportBuildRequest) -> CoachReport:
    warnings: list[str] = []
    statuses: list[CoachReportArtifactStatus] = []
    section_names = [section for section in COACH_REPORT_SECTIONS if section in set(request.sections)]
    sections: list[CoachReportSection] = []
    for section_name in section_names:
        if section_name == "Methodology & Limitations":
            continue
        sections.append(_SECTION_BUILDERS[section_name](request, warnings, statuses))
    if "Methodology & Limitations" in section_names:
        sections.append(_methodology_section(request, warnings, statuses))

    report_id = _report_id_for(request, sections)
    created_at = utc_now()
    json_path = REPORTS_DIR / f"{report_id}.json"
    markdown_path = REPORTS_DIR / f"{report_id}.md"
    markdown = _render_markdown(report_id, request.title, created_at.isoformat(), sections, warnings)
    report = CoachReport(
        report_id=report_id,
        title=request.title,
        created_at=created_at,
        created_by=request.created_by,
        project_id=request.project_id,
        player_key=request.player_key,
        sections=sections,
        warnings=list(dict.fromkeys(warnings)),
        artifact_status=statuses,
        markdown=markdown,
        json_path=str(json_path),
        markdown_path=str(markdown_path),
    )
    _write_json(json_path, report.model_dump(mode="json"))
    markdown_path.write_text(markdown, encoding="utf-8")

    index = _read_index()
    index.reports = [item for item in index.reports if item.report_id != report.report_id]
    index.reports.append(
        CoachReportListItem(
            report_id=report.report_id,
            title=report.title,
            created_at=report.created_at,
            created_by=report.created_by,
            project_id=report.project_id,
            player_key=report.player_key,
            section_names=[section.name for section in report.sections],
            warning_count=len(report.warnings),
            json_path=report.json_path,
            markdown_path=report.markdown_path,
        )
    )
    index.reports.sort(key=lambda item: item.created_at, reverse=True)
    index.updated_at = utc_now()
    _write_json(REPORT_INDEX_PATH, index.model_dump(mode="json"))
    return report


def list_coach_reports() -> CoachReportListResponse:
    return _read_index()


def get_coach_report(report_id: str) -> CoachReport | None:
    path = REPORTS_DIR / f"{report_id}.json"
    if not path.exists():
        return None
    return CoachReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
