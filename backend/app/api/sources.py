"""Global source governance registry routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import TypeAdapter, ValidationError

from app.api.common import api_error
from app.models import LeagueTag, SourceLicenseType, SourceType, UsageScope, VideoSourceRecord
from app.models.base import utc_now

router = APIRouter(prefix="/sources", tags=["sources"])
_SOURCE_ADAPTER = TypeAdapter(list[VideoSourceRecord])
SOURCE_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "source_registry.json"


def _registry_path() -> Path:
    return SOURCE_REGISTRY_PATH


def _read_registry() -> list[VideoSourceRecord]:
    path = _registry_path()
    if not path.exists():
        return []
    try:
        return _SOURCE_ADAPTER.validate_json(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise api_error(
            422,
            "INVALID_SOURCE_REGISTRY",
            "The global source registry is not valid JSON source governance metadata.",
            {"path": str(path), "error": str(exc)},
            "Fix or remove source_registry.json, then seed the candidate sources again.",
        ) from exc


def _write_registry(sources: list[VideoSourceRecord]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_SOURCE_ADAPTER.dump_json(sources, indent=2).decode("utf-8"), encoding="utf-8")


def _candidate_sources() -> list[VideoSourceRecord]:
    created_at = utc_now()
    return [
        VideoSourceRecord(
            project_id=None,
            source_id="candidate-bard",
            name="BARD: Basketball Action Recognition Dataset",
            source_type=SourceType.DATASET,
            source_url="https://github.com/GabrieleGiudic/BARD",
            license_type=SourceLicenseType.CREATIVE_COMMONS,
            rights_confirmed=True,
            allowed_for_training=True,
            allowed_for_redistribution=False,
            allowed_for_local_storage=True,
            league_tag=LeagueTag.UNKNOWN,
            usage_scope=UsageScope.EVALUATION,
            notes="Action recognition dataset with structured JSON labels and multi-label annotations. Useful for action recognition and decision prompt research. Candidate metadata only; user must verify rights and media terms before import.",
            created_at=created_at,
            updated_at=created_at,
        ),
        VideoSourceRecord(
            project_id=None,
            source_id="candidate-e-bard",
            name="E-BARD: Extended Basketball Action Recognition Dataset",
            source_type=SourceType.DATASET,
            source_url="https://github.com/GabrieleGiudic/E-BARD",
            license_type=SourceLicenseType.CREATIVE_COMMONS,
            rights_confirmed=True,
            allowed_for_training=True,
            allowed_for_redistribution=False,
            allowed_for_local_storage=True,
            league_tag=LeagueTag.UNKNOWN,
            usage_scope=UsageScope.TRAINING,
            notes="Multi-task basketball visual understanding dataset. Useful for object detection, player/referee classification, team attribution, jersey number recognition. Candidate metadata only; user must verify rights and media terms before import.",
            created_at=created_at,
            updated_at=created_at,
        ),
        VideoSourceRecord(
            project_id=None,
            source_id="candidate-spacejam",
            name="SpaceJam / Basketball Action Recognition",
            source_type=SourceType.DATASET,
            source_url="https://github.com/simonefrancia/SpaceJam",
            license_type=SourceLicenseType.UNKNOWN,
            rights_confirmed=False,
            allowed_for_training=False,
            allowed_for_redistribution=False,
            allowed_for_local_storage=False,
            league_tag=LeagueTag.UNKNOWN,
            usage_scope=UsageScope.EVALUATION,
            notes="Useful for action classification baseline such as pass, dribble, shoot, defence, pick. Must verify license before training.",
            created_at=created_at,
            updated_at=created_at,
        ),
        VideoSourceRecord(
            project_id=None,
            source_id="candidate-youtube-highlights",
            name="YouTube / NBA / EuroLeague / NCAA Highlights",
            source_type=SourceType.YOUTUBE,
            license_type=SourceLicenseType.YOUTUBE_REFERENCE_ONLY,
            rights_confirmed=False,
            allowed_for_training=False,
            allowed_for_redistribution=False,
            allowed_for_local_storage=False,
            league_tag=LeagueTag.UNKNOWN,
            usage_scope=UsageScope.REFERENCE_ONLY,
            notes="Can be used for manual study and prompt inspiration only unless explicit rights are confirmed. Do not bulk-download highlights.",
            created_at=created_at,
            updated_at=created_at,
        ),
    ]


@router.get("", response_model=list[VideoSourceRecord])
def list_sources() -> list[VideoSourceRecord]:
    """Return global candidate source governance metadata."""

    return _read_registry()


@router.post("/seed-candidates", response_model=list[VideoSourceRecord])
def seed_candidate_sources() -> list[VideoSourceRecord]:
    """Seed known basketball dataset/reference candidates without downloading media."""

    existing_by_id = {source.source_id: source for source in _read_registry()}
    for candidate in _candidate_sources():
        existing_by_id[candidate.source_id] = candidate.model_copy(
            update={"created_at": existing_by_id.get(candidate.source_id, candidate).created_at, "updated_at": utc_now()}
        )
    sources = sorted(existing_by_id.values(), key=lambda source: source.name)
    _write_registry(sources)
    return sources
