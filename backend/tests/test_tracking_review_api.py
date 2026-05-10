from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import common, projects
from app.api.common import write_json_model
from app.main import app
from app.models import (
    Calibration,
    Detection,
    DetectionBox,
    PlayerTrack,
    Project,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    return TestClient(app)


def write_tracking_project(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Tracking QC test"))
    tracking_response = RunTrackingResponse(
        project_id=project_id,
        request=RunTrackingRequest(project_id=project_id),
        detections=[
            Detection(
                detection_id="det-1",
                frame_id="frame-1",
                frame_index=1,
                box=DetectionBox(x=10, y=20, width=30, height=40),
                confidence=0.9,
                class_name="person",
                track_id="track-1",
            ),
            Detection(
                detection_id="det-2",
                frame_id="frame-1",
                frame_index=1,
                box=DetectionBox(x=100, y=120, width=30, height=40),
                confidence=0.8,
                class_name="person",
                track_id="track-2",
            ),
        ],
        tracks=[
            PlayerTrack(
                track_id="track-1",
                points=[
                    TrackPoint(
                        frame_id="frame-1",
                        frame_index=1,
                        timestamp_seconds=0.1,
                        image_point_x=25,
                        image_point_y=60,
                        detection_id="det-1",
                        confidence=0.9,
                    )
                ],
            ),
            PlayerTrack(
                track_id="track-2",
                points=[
                    TrackPoint(
                        frame_id="frame-1",
                        frame_index=1,
                        timestamp_seconds=0.1,
                        image_point_x=115,
                        image_point_y=160,
                        detection_id="det-2",
                        confidence=0.8,
                    )
                ],
            ),
        ],
    )
    write_json_model(directory / "tracking.json", tracking_response)
    return directory


def test_get_tracking_review_returns_raw_tracking_and_empty_patch(client: TestClient, tmp_path: Path) -> None:
    write_tracking_project(tmp_path)

    response = client.get("/api/projects/project-1/tracking/review")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tracking"]["tracks"]) == 2
    assert payload["review_patch"] == {
        "excluded_detection_ids": [],
        "excluded_track_ids": [],
        "track_id_aliases": {},
        "notes": None,
    }
    assert payload["cleaned_tracking"] is None


def test_save_tracking_review_writes_cleaned_artifacts_without_mutating_raw_tracking(client: TestClient, tmp_path: Path) -> None:
    directory = write_tracking_project(tmp_path)

    response = client.post(
        "/api/projects/project-1/tracking/review",
        json={"excluded_detection_ids": [], "excluded_track_ids": ["track-2"], "notes": "false positive coach"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [track["track_id"] for track in payload["cleaned_tracking"]["tracks"]] == ["track-1"]
    assert [detection["detection_id"] for detection in payload["cleaned_tracking"]["detections"]] == ["det-1"]
    assert payload["cleaned_projected_tracks"] == []
    assert (directory / "tracking_cleaned.json").exists()
    assert (directory / "projected_tracks_cleaned.json").exists()
    raw_tracking = RunTrackingResponse.model_validate_json((directory / "tracking.json").read_text(encoding="utf-8"))
    assert [track.track_id for track in raw_tracking.tracks] == ["track-1", "track-2"]


def test_save_tracking_review_excludes_single_detection_and_applies_alias(client: TestClient, tmp_path: Path) -> None:
    write_tracking_project(tmp_path)

    response = client.post(
        "/api/projects/project-1/tracking/review",
        json={
            "excluded_detection_ids": ["det-2"],
            "excluded_track_ids": [],
            "track_id_aliases": {"track-1": "player-a"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [track["track_id"] for track in payload["cleaned_tracking"]["tracks"]] == ["player-a"]
    assert payload["cleaned_tracking"]["detections"][0]["track_id"] == "player-a"


def test_save_tracking_review_uses_calibration_for_cleaned_projection(client: TestClient, tmp_path: Path) -> None:
    directory = write_tracking_project(tmp_path)
    write_json_model(
        directory / "calibration.json",
        Calibration(
            project_id="project-1",
            keypoint_pairs=[],
            homography=[[1, 0, 10], [0, 1, 20], [0, 0, 1]],
        ),
    )

    response = client.post(
        "/api/projects/project-1/tracking/review",
        json={"excluded_detection_ids": [], "excluded_track_ids": ["track-2"]},
    )

    assert response.status_code == 200
    point = response.json()["cleaned_projected_tracks"][0]["points"][0]
    assert point["court_x"] == 35
    assert point["court_y"] == 80


def test_get_tracks_returns_empty_projection_without_calibration(client: TestClient, tmp_path: Path) -> None:
    directory = write_tracking_project(tmp_path)

    response = client.get("/api/projects/project-1/tracks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tracking"]["tracks"][0]["track_id"] == "track-1"
    assert payload["projected_tracks"] == []
    assert (directory / "projected_tracks.json").exists()


def test_get_tracks_uses_calibration_for_projection(client: TestClient, tmp_path: Path) -> None:
    directory = write_tracking_project(tmp_path)
    write_json_model(
        directory / "calibration.json",
        Calibration(
            project_id="project-1",
            keypoint_pairs=[],
            homography=[[1, 0, 10], [0, 1, 20], [0, 0, 1]],
        ),
    )

    response = client.get("/api/projects/project-1/tracks")

    assert response.status_code == 200
    point = response.json()["projected_tracks"][0]["points"][0]
    assert point["court_x"] == 35
    assert point["court_y"] == 80


def test_tracking_review_projection_remains_empty_without_calibration(client: TestClient, tmp_path: Path) -> None:
    write_tracking_project(tmp_path)

    response = client.post(
        "/api/projects/project-1/tracking/review",
        json={"excluded_detection_ids": [], "excluded_track_ids": ["track-2"]},
    )

    assert response.status_code == 200
    assert response.json()["cleaned_projected_tracks"] == []
