from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import (
    Detection,
    DetectionBox,
    Project,
    RunTrackingRequest,
    RunTrackingResponse,
    SourceLicenseType,
    SourceType,
    TrackReviewPatch,
    UsageScope,
    VideoSourceRecord,
)


def _create_project(client: TestClient, name: str = "Governance test") -> str:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 200
    return response.json()["project"]["project_id"]


def _write_project(directory: Path, project_id: str, name: str) -> None:
    write_json_model(directory / project_id / "project.json", Project(project_id=project_id, name=name))


def _write_training_artifacts(directory: Path, project_id: str) -> None:
    write_json_model(
        directory / project_id / "tracking.json",
        RunTrackingResponse(
            project_id=project_id,
            request=RunTrackingRequest(project_id=project_id),
            detections=[
                Detection(
                    detection_id="det-1",
                    frame_id="frame-1",
                    frame_index=1,
                    box=DetectionBox(x=1, y=2, width=3, height=4),
                    confidence=0.9,
                    track_id="track-1",
                )
            ],
            tracks=[],
        ),
    )
    write_json_model(directory / project_id / "tracking_review_patch.json", TrackReviewPatch())


def _write_source(directory: Path, project_id: str, allowed: bool, license_type: SourceLicenseType = SourceLicenseType.OWNED) -> None:
    write_json_model(
        directory / project_id / "source.json",
        VideoSourceRecord(
            project_id=project_id,
            source_id=f"source-{project_id}",
            source_type=SourceType.UPLOAD,
            license_type=license_type,
            rights_confirmed=allowed,
            allowed_for_training=allowed,
            allowed_for_local_storage=True,
            usage_scope=UsageScope.TRAINING if allowed else UsageScope.REFERENCE_ONLY,
        ),
    )


def test_upload_creates_training_eligible_source_by_default(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/video/upload",
        files={"file": ("clip.mp4", b"fake mp4", "video/mp4")},
    )

    assert response.status_code == 200
    source_response = client.get(f"/api/projects/{project_id}/source")
    assert source_response.status_code == 200
    source = source_response.json()
    assert source["source_type"] == "UPLOAD"
    assert source["license_type"] == "OWNED"
    assert source["rights_confirmed"] is True
    assert source["allowed_for_training"] is True
    assert source["allowed_for_local_storage"] is True
    assert source["allowed_for_redistribution"] is False
    assert source["usage_scope"] == "TRAINING"


def test_youtube_creates_reference_only_source_by_default(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/video/youtube",
        json={"url": "https://www.youtube.com/watch?v=abc123", "rights_confirmed": False},
    )

    assert response.status_code == 200
    source = client.get(f"/api/projects/{project_id}/source").json()
    assert source["source_type"] == "YOUTUBE"
    assert source["license_type"] == "YOUTUBE_REFERENCE_ONLY"
    assert source["rights_confirmed"] is False
    assert source["allowed_for_training"] is False
    assert source["allowed_for_local_storage"] is False
    assert source["usage_scope"] == "REFERENCE_ONLY"


def test_cannot_set_youtube_reference_only_source_allowed_for_training(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.put(
        f"/api/projects/{project_id}/source",
        json={
            "project_id": project_id,
            "source_id": "source-1",
            "source_type": "YOUTUBE",
            "license_type": "YOUTUBE_REFERENCE_ONLY",
            "rights_confirmed": True,
            "allowed_for_training": True,
            "allowed_for_redistribution": False,
            "allowed_for_local_storage": False,
            "league_tag": "UNKNOWN",
            "usage_scope": "TRAINING",
        },
    )

    assert response.status_code == 422
    assert "YOUTUBE_REFERENCE_ONLY" in response.text


def test_recognition_export_skips_missing_and_reference_only_sources(client: TestClient, tmp_path: Path) -> None:
    _write_project(tmp_path, "missing-source", "Missing source")
    _write_training_artifacts(tmp_path, "missing-source")
    _write_project(tmp_path, "reference-only", "Reference only")
    _write_training_artifacts(tmp_path, "reference-only")
    _write_source(tmp_path, "reference-only", allowed=False, license_type=SourceLicenseType.YOUTUBE_REFERENCE_ONLY)

    response = client.post("/api/local-lab/datasets/recognition/export")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["included_project_count"] == 0
    assert manifest["skipped_project_count"] == 2
    reasons = {item["project_id"]: item["reason"] for item in manifest["skipped_projects"]}
    assert "Missing source governance" in reasons["missing-source"]
    assert "not allowed for training" in reasons["reference-only"]


def test_recognition_export_includes_owned_training_source(client: TestClient, tmp_path: Path) -> None:
    _write_project(tmp_path, "owned-source", "Owned source")
    _write_training_artifacts(tmp_path, "owned-source")
    _write_source(tmp_path, "owned-source", allowed=True)

    response = client.post("/api/local-lab/datasets/recognition/export")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["included_project_count"] == 1
    assert manifest["skipped_project_count"] == 0
    assert manifest["sample_count"] == 1


def test_seed_candidate_sources_creates_global_registry(client: TestClient) -> None:
    response = client.post("/api/sources/seed-candidates")

    assert response.status_code == 200
    sources = response.json()
    names = {source["name"] for source in sources}
    assert "BARD: Basketball Action Recognition Dataset" in names
    assert "E-BARD: Extended Basketball Action Recognition Dataset" in names
    assert "SpaceJam / Basketball Action Recognition" in names
    assert "YouTube / NBA / EuroLeague / NCAA Highlights" in names
    assert any(source["allowed_for_training"] is True for source in sources if source["source_id"] == "candidate-bard")
    assert any(source["usage_scope"] == "REFERENCE_ONLY" for source in sources if source["source_type"] == "YOUTUBE")

    list_response = client.get("/api/sources")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 4
