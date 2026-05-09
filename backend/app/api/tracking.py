from __future__ import annotations

from pathlib import Path

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
from app.pipeline.detector import detect_players_in_frame
from app.pipeline.projector import project_tracks_to_court
from app.pipeline.tracker import track_frame_detections

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

    source_frames = frame_assets or [None]
    max_players = payload.max_players or 10
    confidence_threshold = payload.confidence_threshold if payload.confidence_threshold is not None else 0.25
    model_name = payload.model_name or "yolov8n.pt"

    detections: list[Detection] = []
    frame_detections: list[dict[str, object]] = []
    detector_metadata: dict[str, object] = {}

    for frame_offset, frame in enumerate(source_frames):
        frame_path = Path(frame.image_path) if frame else None
        result = detect_players_in_frame(frame_path, confidence_threshold=confidence_threshold, model_name=model_name)
        detector_metadata.update(result.get("metadata", {}))
        raw_detections = result.get("detections", [])[:max_players]
        frame_id = frame.frame_id if frame else "frame-000000"
        frame_index = frame.frame_index if frame else frame_offset
        timestamp = frame.timestamp_seconds if frame else 0.0
        tracker_detections: list[dict[str, object]] = []

        for detection_index, raw in enumerate(raw_detections):
            bbox = raw["bbox"]
            confidence = float(raw["score"])
            detection_id = f"{frame_id}-det-{detection_index + 1}"
            box = DetectionBox(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
            detection = Detection(
                detection_id=detection_id,
                frame_id=frame_id,
                frame_index=frame_index,
                box=box,
                confidence=confidence,
                class_name="person",
                metadata={"source": detector_metadata.get("detector_mode", "unknown"), **raw.get("metadata", {})},
            )
            detections.append(detection)
            tracker_detections.append(
                {
                    "detection_id": detection_id,
                    "bbox": [box.x, box.y, box.width, box.height],
                    "confidence": confidence,
                    "class_name": "person",
                }
            )

        frame_detections.append(
            {
                "frame_id": frame_id,
                "frame_index": frame_index,
                "timestamp_seconds": timestamp,
                "detections": tracker_detections,
            }
        )

    raw_tracks = track_frame_detections(frame_detections, iou_threshold=payload.iou_threshold or 0.3)
    detection_track_ids: dict[str, str] = {}
    tracks: list[PlayerTrack] = []
    for raw_track in raw_tracks:
        track = PlayerTrack(track_id=raw_track["track_id"], metadata=raw_track.get("metadata", {}))
        for point in raw_track.get("points", []):
            bbox = point["bbox"]
            detection_id = point.get("detection_id")
            if detection_id:
                detection_track_ids[str(detection_id)] = raw_track["track_id"]
            track.points.append(
                TrackPoint(
                    frame_id=point["frame_id"],
                    frame_index=point["frame_index"],
                    timestamp_seconds=point["timestamp_seconds"],
                    image_point_x=bbox[0] + bbox[2] / 2,
                    image_point_y=bbox[1] + bbox[3],
                    detection_id=detection_id,
                    confidence=point.get("confidence"),
                )
            )
        tracks.append(track)

    for index, detection in enumerate(detections):
        if detection.detection_id in detection_track_ids:
            detections[index] = detection.model_copy(update={"track_id": detection_track_ids[detection.detection_id]})

    response = RunTrackingResponse(
        project_id=project_id,
        request=payload,
        detections=detections,
        tracks=tracks,
        original_input=payload.model_dump(),
        pipeline_output={
            "detector": model_name,
            "detector_mode": detector_metadata.get("detector_mode", "unknown"),
            "track_count": len(tracks),
        },
        debug_metadata={"detector": detector_metadata, "tracker": {"mode": "iou_centroid_mvp"}},
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

    raw_projected_tracks = project_tracks_to_court([track.model_dump() for track in tracking.tracks], homography)
    projected_tracks: list[ProjectedPlayerTrack] = []
    for raw_track in raw_projected_tracks:
        points = [
            ProjectedTrackPoint(
                frame_id=point["frame_id"],
                frame_index=point["frame_index"],
                timestamp_seconds=point["timestamp_seconds"],
                court_x=point["court_x"],
                court_y=point["court_y"],
                source_image_point_x=point.get("source_image_point_x"),
                source_image_point_y=point.get("source_image_point_y"),
                confidence=point.get("confidence"),
                metadata=point.get("metadata", {}),
            )
            for point in raw_track.get("points", [])
        ]
        projected_tracks.append(
            ProjectedPlayerTrack(
                track_id=raw_track["track_id"],
                player_id=raw_track.get("player_id"),
                points=points,
                metadata=raw_track.get("metadata", {}),
            )
        )
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
