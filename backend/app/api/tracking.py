from __future__ import annotations

from fastapi import APIRouter

from app.api.common import api_error, read_json, require_project_dir, write_json_model
from app.models import (
    Calibration,
    Detection,
    DetectionBox,
    ExtractFramesResponse,
    PlayerTrack,
    ProjectedPlayerTrack,
    ProjectedTrackPoint,
    ProjectTracksResponse,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
)
from app.pipeline.detector import detect_players

router = APIRouter(prefix="/projects/{project_id}", tags=["tracking"])


def _apply_homography(matrix: list[list[float]] | None, x: float, y: float) -> tuple[float, float]:
    if matrix is None:
        return x, y
    denominator = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2]
    if abs(denominator) < 1e-12:
        return x, y
    court_x = (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / denominator
    court_y = (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / denominator
    return court_x, court_y


def _build_tracking(project_id: str, payload: RunTrackingRequest) -> RunTrackingResponse:
    directory = require_project_dir(project_id)
    frames_index_path = directory / "frames" / "index.json"
    frames_response = (
        ExtractFramesResponse.model_validate(read_json(frames_index_path)) if frames_index_path.exists() else None
    )

    frame_assets = frames_response.frames if frames_response else []
    if payload.frame_ids:
        requested_ids = set(payload.frame_ids)
        frame_assets = [frame for frame in frame_assets if frame.frame_id in requested_ids]
    if not frame_assets:
        frame_assets = []

    detections: list[Detection] = []
    tracks_by_id: dict[str, PlayerTrack] = {}
    source_frames = frame_assets or [None]
    max_players = payload.max_players or 10
    for frame_offset, frame in enumerate(source_frames):
        raw_detections = detect_players(None)
        for detection_index, raw in enumerate(raw_detections[:max_players]):
            bbox = raw["bbox"]
            confidence = float(raw["score"])
            if payload.confidence_threshold is not None and confidence < payload.confidence_threshold:
                continue
            frame_id = frame.frame_id if frame else "stub-frame-000000"
            frame_index = frame.frame_index if frame else frame_offset
            timestamp = frame.timestamp_seconds if frame else 0.0
            track_id = f"track-{detection_index + 1}"
            detection_id = f"{frame_id}-det-{detection_index + 1}"
            box = DetectionBox(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
            detections.append(
                Detection(
                    detection_id=detection_id,
                    frame_id=frame_id,
                    frame_index=frame_index,
                    box=box,
                    confidence=confidence,
                    class_name="person",
                    track_id=track_id,
                    metadata={"source": "yolo_person_or_mvp_stub"},
                )
            )
            track = tracks_by_id.setdefault(track_id, PlayerTrack(track_id=track_id, metadata={"source": "mvp_stub"}))
            track.points.append(
                TrackPoint(
                    frame_id=frame_id,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp,
                    image_point_x=box.x + box.width / 2,
                    image_point_y=box.y + box.height,
                    detection_id=detection_id,
                    confidence=confidence,
                )
            )

    response = RunTrackingResponse(
        project_id=project_id,
        request=payload,
        detections=detections,
        tracks=list(tracks_by_id.values()),
        original_input=payload.model_dump(),
        pipeline_output={"detector": payload.model_name or "yolo_person_or_mvp_stub", "track_count": len(tracks_by_id)},
        debug_metadata={"debug_hint": "Install/wire YOLO to replace deterministic MVP stub detections."},
    )
    write_json_model(directory / "tracking.json", response)
    return response


def _project_tracks(project_id: str, tracking: RunTrackingResponse) -> list[ProjectedPlayerTrack]:
    directory = require_project_dir(project_id)
    calibration_path = directory / "calibration.json"
    homography = None
    if calibration_path.exists():
        calibration = Calibration.model_validate(read_json(calibration_path))
        homography = calibration.homography
    projected_tracks: list[ProjectedPlayerTrack] = []
    for track in tracking.tracks:
        points: list[ProjectedTrackPoint] = []
        for point in track.points:
            court_x, court_y = _apply_homography(homography, point.image_point_x, point.image_point_y)
            points.append(
                ProjectedTrackPoint(
                    frame_id=point.frame_id,
                    frame_index=point.frame_index,
                    timestamp_seconds=point.timestamp_seconds,
                    court_x=court_x,
                    court_y=court_y,
                    source_image_point_x=point.image_point_x,
                    source_image_point_y=point.image_point_y,
                    confidence=point.confidence,
                    metadata={"homography_applied": homography is not None},
                )
            )
        projected_tracks.append(ProjectedPlayerTrack(track_id=track.track_id, player_id=track.player_id, points=points))
    return projected_tracks


@router.post("/tracking/run", response_model=RunTrackingResponse)
def run_tracking(project_id: str, payload: RunTrackingRequest) -> RunTrackingResponse:
    if project_id != payload.project_id:
        raise api_error(
            400,
            "PROJECT_ID_MISMATCH",
            "Request body project_id must match the path project_id.",
            {"path_project_id": project_id, "body_project_id": payload.project_id},
            "Send the same project id in the URL and Pydantic request body.",
        )
    tracking = _build_tracking(project_id, payload)
    projected_tracks = _project_tracks(project_id, tracking)
    directory = require_project_dir(project_id)
    write_json_model(directory / "projected_tracks.json", ProjectTracksResponse(project_id=project_id, tracking=tracking, projected_tracks=projected_tracks))
    return tracking


@router.get("/tracks", response_model=ProjectTracksResponse)
def get_tracks(project_id: str) -> ProjectTracksResponse:
    directory = require_project_dir(project_id)
    tracking_path = directory / "tracking.json"
    if not tracking_path.exists():
        raise api_error(
            404,
            "TRACKING_NOT_FOUND",
            "No tracking output exists for this project.",
            {"project_id": project_id},
            "Run POST /api/projects/{project_id}/tracking/run before requesting tracks.",
        )
    tracking = RunTrackingResponse.model_validate(read_json(tracking_path))
    projected_tracks = _project_tracks(project_id, tracking)
    storage_path = directory / "projected_tracks.json"
    response = ProjectTracksResponse(
        project_id=project_id,
        tracking=tracking,
        projected_tracks=projected_tracks,
        storage_paths={"tracking": str(tracking_path), "projected_tracks": str(storage_path)},
    )
    write_json_model(storage_path, response)
    return response
