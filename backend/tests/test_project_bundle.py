from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import common, projects
from app.api.common import write_json_model
from app.main import app
from app.models import (
    ExtractFramesRequest,
    ExtractFramesResponse,
    FrameAsset,
    Project,
    ProjectedPlayerTrack,
    ProjectTracksResponse,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackReviewPatch,
    VideoAsset,
)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    return TestClient(app)


def write_project(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Hydration test"))
    return directory


def test_missing_project_bundle_returns_404(client: TestClient) -> None:
    response = client.get("/api/projects/missing/bundle")

    assert response.status_code == 404
    assert response.json()["code"] == "PROJECT_NOT_FOUND"


def test_bundle_returns_project_with_null_optional_artifacts(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["project_id"] == "project-1"
    assert payload["video"] is None
    assert payload["frames"] is None
    assert payload["calibration"] is None
    assert payload["tracking"] is None
    assert payload["projected_tracks"] is None
    assert payload["tracking_review"] is None


def test_bundle_returns_video_when_video_json_exists(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_json_model(
        directory / "video.json",
        VideoAsset(project_id="project-1", asset_id="video-1", source_type="upload", uri="/tmp/video.mp4", filename="video.mp4"),
    )

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 200
    assert response.json()["video"]["asset_id"] == "video-1"


def test_bundle_returns_frames_when_frame_index_exists(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    frames = ExtractFramesResponse(
        project_id="project-1",
        request=ExtractFramesRequest(project_id="project-1", video_asset_id="video-1"),
        frames=[
            FrameAsset(
                frame_id="frame-1",
                frame_index=42,
                timestamp_seconds=1.4,
                image_path=str(directory / "frames" / "images" / "frame_42.jpg"),
                width=1920,
                height=1080,
            )
        ],
    )
    write_json_model(directory / "frames" / "index.json", frames)

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 200
    assert response.json()["frames"]["frames"][0]["frame_index"] == 42


def test_bundle_does_not_crash_when_some_optional_files_are_missing(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_json_model(
        directory / "video.json",
        VideoAsset(project_id="project-1", asset_id="video-1", source_type="youtube", uri="https://example.com/watch?v=1"),
    )

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["video"]["source_type"] == "youtube"
    assert payload["frames"] is None
    assert payload["tracking"] is None


def test_bundle_returns_typed_422_for_invalid_optional_json(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    (directory / "video.json").write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "INVALID_ARTIFACT_JSON"
    assert payload["details"]["artifact"] == "video.json"
    assert "fix or regenerate" in payload["debug_hint"]


def test_bundle_returns_typed_422_for_invalid_optional_schema(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    (directory / "video.json").write_text('{"project_id":"project-1"}', encoding="utf-8")

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "INVALID_ARTIFACT_SCHEMA"
    assert payload["details"]["artifact"] == "video.json"
    assert "VideoAsset" in payload["debug_hint"]


def test_bundle_returns_tracking_review_metadata_when_cleaned_artifacts_exist(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    raw_tracking = RunTrackingResponse(
        project_id="project-1",
        request=RunTrackingRequest(project_id="project-1"),
        detections=[],
        tracks=[],
    )
    cleaned_tracking = RunTrackingResponse(
        project_id="project-1",
        request=RunTrackingRequest(project_id="project-1"),
        detections=[],
        tracks=[],
    )
    write_json_model(directory / "tracking.json", raw_tracking)
    write_json_model(directory / "tracking_review_patch.json", TrackReviewPatch(excluded_track_ids=["track-2"]))
    write_json_model(directory / "tracking_cleaned.json", cleaned_tracking)
    write_json_model(
        directory / "projected_tracks_cleaned.json",
        ProjectTracksResponse(
            project_id="project-1",
            tracking=cleaned_tracking,
            projected_tracks=[ProjectedPlayerTrack(track_id="track-1")],
        ),
    )

    response = client.get("/api/projects/project-1/bundle")

    assert response.status_code == 200
    review = response.json()["tracking_review"]
    assert review["review_patch"]["excluded_track_ids"] == ["track-2"]
    assert review["cleaned_tracking"] is not None
    assert review["cleaned_projected_tracks"][0]["track_id"] == "track-1"
