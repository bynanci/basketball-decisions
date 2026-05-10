from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import common, projects
from app.api.common import write_json_model
from app.main import app
from app.models import ExtractFramesRequest, ExtractFramesResponse, FrameAsset, Project, VideoAsset


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
