"""Sample project install/status models."""

from __future__ import annotations

from pydantic import BaseModel, Field

SAMPLE_PROJECT_ID = "sample-court-iq-pnr"
SAMPLE_PROJECT_NAME = "Court IQ Sample: Pick-and-Roll Reads"


class SampleDataArtifactStatus(BaseModel):
    """Status for one seeded sample artifact."""

    key: str
    path: str
    installed: bool


class SampleDataStatusResponse(BaseModel):
    """Current install status for the deterministic local sample project."""

    project_id: str = SAMPLE_PROJECT_ID
    project_name: str = SAMPLE_PROJECT_NAME
    installed: bool
    can_seed: bool
    protected_existing_project: bool = False
    artifact_count: int = 0
    artifacts: list[SampleDataArtifactStatus] = Field(default_factory=list)
    quick_links: list[dict[str, str]] = Field(default_factory=list)
    message: str


class SampleDataMutationResponse(SampleDataStatusResponse):
    """Response returned after installing or removing sample artifacts."""

    changed: bool = False
