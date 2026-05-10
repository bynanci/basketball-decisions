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
    TrackReviewPatch,
    TrackReviewResponse,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
)
from app.pipeline.detector import detect_players_in_frame
from app.pipeline.projector import project_tracks_to_court
from app.pipeline.tracker import track_frame_detections

router = APIRouter(prefix="/projects/{project_id}", tags=["tracking"])


def _tracking_path(directory: Path) -> Path:
    return directory / "tracking.json"


def _review_patch_path(directory: Path) -> Path:
    return directory / "tracking_review_patch.json"


def _cleaned_tracking_path(directory: Path) -> Path:
    return directory / "tracking_cleaned.json"


def _cleaned_projected_tracks_path(directory: Path) -> Path:
    return directory / "projected_tracks_cleaned.json"


def _read_review_patch(directory: Path) -> TrackReviewPatch:
    path = _review_patch_path(directory)
    if not path.exists():
        return TrackReviewPatch()
    return TrackReviewPatch.model_validate(read_json(path))


def _load_tracking_for_review(project_id: str) -> RunTrackingResponse:
    directory = require_project_dir(project_id)
    tracking_path = _tracking_path(directory)
    if not tracking_path.exists():
        raise api_error(
            404,
            "TRACKING_NOT_FOUND",
            "No tracking output exists for this project.",
            {"project_id": project_id},
            "Run POST /api/projects/{project_id}/tracking/run before reviewing tracking quality.",
        )
    return RunTrackingResponse.model_validate(read_json(tracking_path))


def _apply_review_patch(tracking: RunTrackingResponse, patch: TrackReviewPatch) -> RunTrackingResponse:
    excluded_detection_ids = set(patch.excluded_detection_ids)
    excluded_track_ids = set(patch.excluded_track_ids)
    aliases = patch.track_id_aliases

    cleaned_detections: list[Detection] = []
    for detection in tracking.detections:
        if detection.detection_id in excluded_detection_ids:
            continue
        original_track_id = detection.track_id
        if original_track_id in excluded_track_ids:
            continue
        track_id = aliases.get(original_track_id, original_track_id) if original_track_id else None
        metadata = {**detection.metadata, "tracking_review_status": "cleaned"}
        if original_track_id and track_id != original_track_id:
            metadata["original_track_id"] = original_track_id
        cleaned_detections.append(detection.model_copy(update={"track_id": track_id, "metadata": metadata}))

    cleaned_tracks: list[PlayerTrack] = []
    for track in tracking.tracks:
        if track.track_id in excluded_track_ids:
            continue
        points = [point for point in track.points if point.detection_id not in excluded_detection_ids]
        if not points:
            continue
        track_id = aliases.get(track.track_id, track.track_id)
        metadata = {**track.metadata, "tracking_review_status": "cleaned"}
        if track_id != track.track_id:
            metadata["original_track_id"] = track.track_id
        cleaned_tracks.append(
            track.model_copy(update={"track_id": track_id, "points": points, "metadata": metadata})
        )

    return tracking.model_copy(
        update={
            "detections": cleaned_detections,
            "tracks": cleaned_tracks,
            "original_input": {**tracking.original_input, "review_patch": patch.model_dump()},
            "pipeline_output": {
                **tracking.pipeline_output,
                "raw_detection_count": len(tracking.detections),
                "raw_track_count": len(tracking.tracks),
                "cleaned_detection_count": len(cleaned_detections),
                "cleaned_track_count": len(cleaned_tracks),
                "excluded_detection_count": len(excluded_detection_ids),
                "excluded_track_count": len(excluded_track_ids),
            },
            "debug_metadata": {**tracking.debug_metadata, "tracking_review": patch.model_dump()},
        }
    )


def _build_review_response(
    project_id: str, tracking: RunTrackingResponse, patch: TrackReviewPatch
) -> TrackReviewResponse:
    directory = require_project_dir(project_id)
    cleaned_path = _cleaned_tracking_path(directory)
    cleaned_tracking = RunTrackingResponse.model_validate(read_json(cleaned_path)) if cleaned_path.exists() else None
    cleaned_projected_tracks: list[ProjectedPlayerTrack] = []
    cleaned_projection_path = _cleaned_projected_tracks_path(directory)
    if cleaned_projection_path.exists():
        cleaned_projection = ProjectTracksResponse.model_validate(read_json(cleaned_projection_path))
        cleaned_projected_tracks = cleaned_projection.projected_tracks

    return TrackReviewResponse(
        project_id=project_id,
        tracking=tracking,
        review_patch=patch,
        cleaned_tracking=cleaned_tracking,
        cleaned_projected_tracks=cleaned_projected_tracks,
        storage_paths={
            "tracking": str(_tracking_path(directory)),
            "review_patch": str(_review_patch_path(directory)),
            "tracking_cleaned": str(cleaned_path),
            "projected_tracks_cleaned": str(cleaned_projection_path),
        },
    )


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

    if homography is None:
        return []

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


@router.get("/tracking/review", response_model=TrackReviewResponse)
def get_tracking_review(project_id: str) -> TrackReviewResponse:
    tracking = _load_tracking_for_review(project_id)
    directory = require_project_dir(project_id)
    patch = _read_review_patch(directory)
    return _build_review_response(project_id, tracking, patch)


@router.post("/tracking/review", response_model=TrackReviewResponse)
def save_tracking_review(project_id: str, payload: TrackReviewPatch) -> TrackReviewResponse:
    tracking = _load_tracking_for_review(project_id)
    directory = require_project_dir(project_id)
    cleaned_tracking = _apply_review_patch(tracking, payload)
    cleaned_projected_tracks = _project_tracks(project_id, cleaned_tracking)

    write_json_model(_review_patch_path(directory), payload)
    write_json_model(_cleaned_tracking_path(directory), cleaned_tracking)
    write_json_model(
        _cleaned_projected_tracks_path(directory),
        ProjectTracksResponse(
            project_id=project_id,
            tracking=cleaned_tracking,
            projected_tracks=cleaned_projected_tracks,
            storage_paths={
                "tracking_cleaned": str(_cleaned_tracking_path(directory)),
                "projected_tracks_cleaned": str(_cleaned_projected_tracks_path(directory)),
            },
        ),
    )
    return _build_review_response(project_id, tracking, payload)


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
