"""Manual player identity / track alias API routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import ValidationError

from app.api.common import api_error, read_json, require_project_dir, write_json_model
from app.models import PlayerAliasListResponse, RunTrackingResponse
from app.models.base import utc_now

router = APIRouter(prefix="/projects/{project_id}/player-aliases", tags=["player-identity"])


def player_aliases_path(directory: Path) -> Path:
    return directory / "player_aliases.json"


def read_player_aliases(directory: Path, project_id: str) -> PlayerAliasListResponse | None:
    path = player_aliases_path(directory)
    if not path.exists():
        return None
    try:
        return PlayerAliasListResponse.model_validate(read_json(path))
    except json.JSONDecodeError as exc:
        raise api_error(
            422,
            "INVALID_PLAYER_ALIASES_JSON",
            "Player aliases artifact is not valid JSON.",
            {"path": str(path), "project_id": project_id, "error": str(exc)},
            "Fix or regenerate player_aliases.json before loading player identity data.",
        ) from exc
    except ValidationError as exc:
        raise api_error(
            422,
            "INVALID_PLAYER_ALIASES_SCHEMA",
            "Player aliases artifact does not match the expected schema.",
            {"path": str(path), "project_id": project_id, "errors": exc.errors()},
            "Ensure player_aliases.json contains unique player_key values and no overlapping track_ids.",
        ) from exc


def _known_track_ids(directory: Path) -> set[str]:
    ids: set[str] = set()
    for filename in ("tracking_cleaned.json", "tracking.json"):
        path = directory / filename
        if not path.exists():
            continue
        try:
            tracking = RunTrackingResponse.model_validate(read_json(path))
        except ValidationError:
            continue
        ids.update(track.track_id for track in tracking.tracks)
    return ids


def _validate_alias_payload(project_id: str, payload: PlayerAliasListResponse, directory: Path, strict: bool) -> PlayerAliasListResponse:
    data = payload.model_dump()
    data["project_id"] = project_id
    for alias in data.get("aliases", []):
        alias["project_id"] = project_id
        alias["updated_at"] = utc_now()
    try:
        aliases = PlayerAliasListResponse.model_validate(data)
    except ValidationError as exc:
        raise api_error(
            422,
            "INVALID_PLAYER_ALIASES",
            "Player alias payload is invalid.",
            {"errors": exc.errors()},
            "Ensure player_key values are unique and each track_id appears in only one alias.",
        ) from exc

    known_track_ids = _known_track_ids(directory)
    if strict and known_track_ids:
        referenced = {track_id for alias in aliases.aliases for track_id in alias.track_ids}
        missing = sorted(referenced - known_track_ids)
        if missing:
            raise api_error(
                422,
                "UNKNOWN_ALIAS_TRACK_ID",
                "Alias payload references track IDs that were not found in tracking artifacts.",
                {"track_ids": missing},
                "Save aliases against track IDs from tracking_cleaned.json or tracking.json, or retry without strict=true.",
            )
    return aliases


@router.get("", response_model=PlayerAliasListResponse)
def get_player_aliases(project_id: str) -> PlayerAliasListResponse:
    directory = require_project_dir(project_id)
    return read_player_aliases(directory, project_id) or PlayerAliasListResponse(project_id=project_id, aliases=[])


@router.put("", response_model=PlayerAliasListResponse)
def put_player_aliases(project_id: str, payload: PlayerAliasListResponse, strict: bool = False) -> PlayerAliasListResponse:
    directory = require_project_dir(project_id)
    aliases = _validate_alias_payload(project_id, payload, directory, strict)
    write_json_model(player_aliases_path(directory), aliases)
    return aliases
