from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import PlayerAlias, PlayerAliasListResponse, Project, RunTrackingRequest, RunTrackingResponse, PlayerTrack


def write_project(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Alias test"))
    return directory


def alias_payload(project_id: str = "project-1") -> dict:
    return {
        "project_id": project_id,
        "aliases": [
            {
                "player_key": "P1",
                "project_id": project_id,
                "track_ids": ["track-1", "track-2"],
                "display_name": "Guard",
                "team_side": "HOME",
                "role_hint": "ball handler",
                "confidence": 1.0,
                "source": "MANUAL",
                "notes": "manual grouping",
            }
        ],
    }


def test_can_save_and_load_aliases(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)

    response = client.put("/api/projects/project-1/player-aliases", json=alias_payload())

    assert response.status_code == 200
    assert response.json()["aliases"][0]["player_key"] == "P1"
    assert (tmp_path / "project-1" / "player_aliases.json").exists()

    get_response = client.get("/api/projects/project-1/player-aliases")
    assert get_response.status_code == 200
    assert get_response.json()["aliases"][0]["track_ids"] == ["track-1", "track-2"]


def test_duplicate_player_key_rejected(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = alias_payload()
    payload["aliases"].append({**payload["aliases"][0], "track_ids": ["track-3"]})

    response = client.put("/api/projects/project-1/player-aliases", json=payload)

    assert response.status_code == 422


def test_duplicate_track_id_across_aliases_rejected(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = alias_payload()
    payload["aliases"].append({**payload["aliases"][0], "player_key": "P2", "track_ids": ["track-2"]})

    response = client.put("/api/projects/project-1/player-aliases", json=payload)

    assert response.status_code == 422


def test_missing_project_returns_404(client: TestClient) -> None:
    response = client.get("/api/projects/missing/player-aliases")

    assert response.status_code == 404
    assert response.json()["code"] == "PROJECT_NOT_FOUND"


def test_strict_rejects_unknown_track_id(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_json_model(
        directory / "tracking.json",
        RunTrackingResponse(
            project_id="project-1",
            request=RunTrackingRequest(project_id="project-1"),
            tracks=[PlayerTrack(track_id="track-1")],
            detections=[],
        ),
    )

    response = client.put("/api/projects/project-1/player-aliases?strict=true", json=alias_payload())

    assert response.status_code == 422
    assert response.json()["code"] == "UNKNOWN_ALIAS_TRACK_ID"


def test_malformed_alias_artifact_returns_typed_422(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    (directory / "player_aliases.json").write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/projects/project-1/player-aliases")

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_PLAYER_ALIASES_JSON"


def test_bundle_returns_typed_422_for_invalid_alias_schema(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    (directory / "player_aliases.json").write_text(
        '{"project_id":"project-1","aliases":[{"player_key":"P1","project_id":"project-1","track_ids":[]}]}',
        encoding="utf-8",
    )

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_PLAYER_ALIASES_SCHEMA"


def test_bundle_includes_aliases_when_present(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(project_id="project-1", aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"])]),
    )

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 200
    assert response.json()["player_aliases"]["aliases"][0]["player_key"] == "P1"
