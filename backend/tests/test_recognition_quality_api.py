from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import (
    Detection,
    DetectionBox,
    PlayerTrack,
    Project,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
    TrackReviewPatch,
)


def _point(frame_index: int, detection_id: str, confidence: float = 0.9) -> TrackPoint:
    return TrackPoint(
        frame_id=f"frame-{frame_index}",
        frame_index=frame_index,
        timestamp_seconds=frame_index / 30,
        image_point_x=100 + frame_index * 3,
        image_point_y=200 + frame_index * 2,
        detection_id=detection_id,
        confidence=confidence,
    )


def _detection(frame_index: int, detection_id: str, track_id: str, confidence: float = 0.9) -> Detection:
    return Detection(
        detection_id=detection_id,
        frame_id=f"frame-{frame_index}",
        frame_index=frame_index,
        box=DetectionBox(x=90 + frame_index * 3, y=160 + frame_index * 2, width=20, height=40),
        confidence=confidence,
        class_name="person",
        track_id=track_id,
    )


def _write_recognition_project(
    tmp_path: Path,
    *,
    project_id: str = "recognition-project",
    short_confidence: float = 0.5,
    excluded_track_ids: list[str] | None = None,
) -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Recognition scoring test"))
    detections = [_detection(1, "short-det-1", "short-track", short_confidence)]
    short_track = PlayerTrack(track_id="short-track", points=[_point(1, "short-det-1", short_confidence)])

    long_points = []
    for index in range(1, 10):
        detection_id = f"long-det-{index}"
        detections.append(_detection(index, detection_id, "long-track", 0.92))
        long_points.append(_point(index, detection_id, 0.92))
    long_track = PlayerTrack(track_id="long-track", points=long_points)

    write_json_model(
        directory / "tracking.json",
        RunTrackingResponse(
            project_id=project_id,
            request=RunTrackingRequest(project_id=project_id),
            detections=detections,
            tracks=[short_track, long_track],
        ),
    )
    if excluded_track_ids is not None:
        write_json_model(directory / "tracking_review_patch.json", TrackReviewPatch(excluded_track_ids=excluded_track_ids))
    return directory


def _track_score(payload: dict, track_id: str) -> dict:
    return next(score for score in payload["track_scores"] if score["track_id"] == track_id)


def test_short_track_increases_recognition_risk(client: TestClient, tmp_path: Path) -> None:
    _write_recognition_project(tmp_path)

    response = client.post("/api/local-lab/recognition/score-project/recognition-project")

    assert response.status_code == 200
    payload = response.json()
    short_score = _track_score(payload, "short-track")
    long_score = _track_score(payload, "long-track")
    assert short_score["false_positive_risk"] > long_score["false_positive_risk"]
    assert "Track has only one point." in short_score["reasons"]


def test_excluded_track_gets_high_recognition_risk(client: TestClient, tmp_path: Path) -> None:
    _write_recognition_project(tmp_path, excluded_track_ids=["short-track"])

    response = client.post("/api/local-lab/recognition/score-project/recognition-project")

    assert response.status_code == 200
    payload = response.json()
    short_score = _track_score(payload, "short-track")
    assert short_score["false_positive_risk"] == 1.0
    assert short_score["recommended_label"] == "HIGH"
    assert payload["summary"]["high_risk_track_count"] == 1


def test_long_high_confidence_track_gets_low_recognition_risk(client: TestClient, tmp_path: Path) -> None:
    _write_recognition_project(tmp_path)

    response = client.post("/api/local-lab/recognition/score-project/recognition-project")

    assert response.status_code == 200
    long_score = _track_score(response.json(), "long-track")
    assert long_score["recommended_label"] == "LOW"
    assert long_score["false_positive_risk"] < 0.4
    assert "Track is long enough to be stable." in long_score["reasons"]


def test_recognition_scoring_missing_calibration_does_not_crash(client: TestClient, tmp_path: Path) -> None:
    _write_recognition_project(tmp_path)

    response = client.post("/api/local-lab/recognition/score-project/recognition-project")

    assert response.status_code == 200
    payload = response.json()
    assert payload["track_scores"][0]["features"]["projected_inside_court_ratio"] is None
    assert payload["detection_scores"][0]["features"]["inside_projected_court"] is None
