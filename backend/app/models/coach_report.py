"""Coach report export models for local, explainable basketball decision artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import utc_now

CoachReportSectionName = Literal[
    "Player Value",
    "Trends",
    "Decision Diagnostics",
    "Rule Contributions",
    "Teaching Cases",
    "Review Findings",
    "Source Governance",
    "Methodology & Limitations",
]

COACH_REPORT_SECTIONS: tuple[CoachReportSectionName, ...] = (
    "Player Value",
    "Trends",
    "Decision Diagnostics",
    "Rule Contributions",
    "Teaching Cases",
    "Review Findings",
    "Source Governance",
    "Methodology & Limitations",
)


class CoachReportBuildRequest(BaseModel):
    """Options for building a coach report from local artifacts only."""

    title: str = "Coach Report"
    project_id: str | None = None
    player_key: str | None = None
    sections: list[CoachReportSectionName] = Field(default_factory=lambda: list(COACH_REPORT_SECTIONS))
    created_by: str | None = None
    notes: str | None = None


class CoachReportArtifactStatus(BaseModel):
    """Status for one artifact consumed by the report builder."""

    artifact: str
    path: str
    available: bool
    warning: str | None = None


class CoachReportSection(BaseModel):
    """Structured and Markdown-ready content for one report section."""

    name: CoachReportSectionName
    heading: str
    markdown: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class CoachReport(BaseModel):
    """Persisted coach report with deterministic Markdown and structured JSON."""

    schema_version: str = "1.0"
    report_id: str
    title: str
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None
    project_id: str | None = None
    player_key: str | None = None
    sections: list[CoachReportSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifact_status: list[CoachReportArtifactStatus] = Field(default_factory=list)
    markdown: str
    json_path: str
    markdown_path: str


class CoachReportListItem(BaseModel):
    """Index row for a generated coach report."""

    report_id: str
    title: str
    created_at: datetime
    created_by: str | None = None
    project_id: str | None = None
    player_key: str | None = None
    section_names: list[str] = Field(default_factory=list)
    warning_count: int = 0
    json_path: str
    markdown_path: str


class CoachReportListResponse(BaseModel):
    """Coach report history response."""

    reports: list[CoachReportListItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)
