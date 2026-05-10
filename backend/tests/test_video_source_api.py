from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import common, projects
from app.api.common import write_json_model
from app.main import app
from app.models import Project, VideoAsset


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    return TestClient(app)


def write_project(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Video source test"))
    return directory


def test_video_source_serves_local_project_mp4(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    video_path = directory / "videos" / "video-1.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"fake mp4 bytes")
    write_json_model(
        directory / "video.json",
        VideoAsset(project_id="project-1", asset_id="video-1", source_type="upload", uri=str(video_path), filename="clip.mp4"),
    )

    response = client.get("/api/projects/project-1/video/source")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.content == b"fake mp4 bytes"


def test_video_source_404_when_no_local_mp4(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_json_model(
        directory / "video.json",
        VideoAsset(project_id="project-1", asset_id="video-1", source_type="youtube", uri="https://example.com/watch?v=1"),
    )

    response = client.get("/api/projects/project-1/video/source")

    assert response.status_code == 404
    assert response.json()["code"] == "LOCAL_VIDEO_NOT_FOUND"


def test_video_source_does_not_serve_paths_outside_project(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    outside_video = tmp_path / "outside.mp4"
    outside_video.write_bytes(b"do not serve")
    write_json_model(
        directory / "video.json",
        VideoAsset(project_id="project-1", asset_id="video-1", source_type="upload", uri=str(outside_video), filename="outside.mp4"),
    )

    response = client.get("/api/projects/project-1/video/source")

    assert response.status_code == 404
    assert response.json()["code"] == "LOCAL_VIDEO_NOT_FOUND"
    assert str(outside_video) not in response.text
