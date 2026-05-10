"""Rule-based recognition quality feature extraction and scoring."""

from __future__ import annotations

import math
from collections.abc import Iterable

from app.models import (
    Calibration,
    Detection,
    DetectionRecognitionFeatures,
    DetectionRecognitionScore,
    PlayerTrack,
    RecognitionScoreProjectResponse,
    RecognitionScoreSummary,
    TrackRecognitionFeatures,
    TrackRecognitionScore,
    TrackReviewPatch,
)
from app.pipeline.homography import image_to_court

COURT_LENGTH_FEET = 94.0
COURT_WIDTH_FEET = 50.0
HIGH_RISK_THRESHOLD = 0.7
MEDIUM_RISK_THRESHOLD = 0.4


def _clamp_risk(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def _recommended_label(risk: float) -> str:
    if risk >= HIGH_RISK_THRESHOLD:
        return "HIGH"
    if risk >= MEDIUM_RISK_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _bbox_area(detection: Detection) -> float:
    return max(0.0, detection.box.width) * max(0.0, detection.box.height)


def _bbox_aspect_ratio(detection: Detection) -> float:
    return detection.box.width / detection.box.height if detection.box.height else 0.0


def _bottom_center(detection: Detection) -> tuple[float, float]:
    return detection.box.x + detection.box.width / 2.0, detection.box.y + detection.box.height


def _inside_court(court_x: float, court_y: float) -> bool:
    return 0.0 <= court_x <= COURT_LENGTH_FEET and 0.0 <= court_y <= COURT_WIDTH_FEET


def _project_inside_court(calibration: Calibration | None, image_x: float, image_y: float) -> bool | None:
    if calibration is None or calibration.homography is None:
        return None
    court_x, court_y = image_to_court((image_x, image_y), calibration.homography)
    return _inside_court(court_x, court_y)


def _variance(values: list[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def extract_detection_features(
    detection: Detection,
    track_point_counts: dict[str, int],
    calibration: Calibration | None,
) -> DetectionRecognitionFeatures:
    inside_court = _project_inside_court(calibration, *_bottom_center(detection))
    return DetectionRecognitionFeatures(
        bbox_x=detection.box.x,
        bbox_y=detection.box.y,
        bbox_width=detection.box.width,
        bbox_height=detection.box.height,
        bbox_area=_bbox_area(detection),
        bbox_aspect_ratio=_bbox_aspect_ratio(detection),
        confidence=detection.confidence,
        frame_index=detection.frame_index,
        has_track_id=detection.track_id is not None,
        track_point_count=track_point_counts.get(detection.track_id) if detection.track_id else None,
        inside_projected_court=inside_court,
    )


def extract_track_features(
    track: PlayerTrack,
    detections_by_id: dict[str, Detection],
    calibration: Calibration | None,
) -> TrackRecognitionFeatures:
    points = sorted(track.points, key=lambda point: (point.frame_index, point.timestamp_seconds))
    confidences = [point.confidence for point in points if point.confidence is not None]
    bbox_areas = [_bbox_area(detections_by_id[point.detection_id]) for point in points if point.detection_id in detections_by_id]
    distances: list[float] = []
    for previous, current in zip(points, points[1:]):
        distances.append(
            _distance(
                (previous.image_point_x, previous.image_point_y),
                (current.image_point_x, current.image_point_y),
            )
        )
    frame_indexes = [point.frame_index for point in points]
    frame_span = max(frame_indexes) - min(frame_indexes) + 1 if frame_indexes else 0
    gap_count = 0
    for previous, current in zip(frame_indexes, frame_indexes[1:]):
        gap_count += max(0, current - previous - 1)

    inside_flags = [
        _project_inside_court(calibration, point.image_point_x, point.image_point_y)
        for point in points
    ]
    known_inside_flags = [flag for flag in inside_flags if flag is not None]
    inside_ratio = None
    if known_inside_flags:
        inside_ratio = sum(1 for flag in known_inside_flags if flag) / len(known_inside_flags)

    return TrackRecognitionFeatures(
        point_count=len(points),
        avg_confidence=_avg([float(value) for value in confidences]),
        min_confidence=min(confidences) if confidences else None,
        max_confidence=max(confidences) if confidences else None,
        avg_bbox_area=_avg(bbox_areas),
        bbox_area_variance=_variance(bbox_areas),
        avg_speed_image=_avg(distances),
        max_jump_distance_image=max(distances) if distances else None,
        frame_span=frame_span,
        gap_count=gap_count,
        projected_inside_court_ratio=inside_ratio,
    )


def score_detection(
    detection: Detection,
    features: DetectionRecognitionFeatures,
    patch: TrackReviewPatch,
    track_score_by_id: dict[str, TrackRecognitionScore],
) -> DetectionRecognitionScore:
    reasons: list[str] = []
    if detection.detection_id in patch.excluded_detection_ids or (detection.track_id and detection.track_id in patch.excluded_track_ids):
        return DetectionRecognitionScore(
            detection_id=detection.detection_id,
            track_id=detection.track_id,
            false_positive_risk=1.0,
            recommended_label="HIGH",
            reasons=["Reviewer previously excluded this detection or its track."],
            features=features,
        )

    risk = 0.2
    if features.confidence < 0.35:
        risk += 0.35
        reasons.append("Low detector confidence below 0.35.")
    elif features.confidence < 0.55:
        risk += 0.18
        reasons.append("Moderate detector confidence below 0.55.")
    else:
        risk -= 0.08
        reasons.append("Detector confidence is healthy.")

    if not features.has_track_id:
        risk += 0.22
        reasons.append("Detection is not associated with a track.")
    elif features.track_point_count is not None and features.track_point_count <= 2:
        risk += 0.22
        reasons.append("Detection belongs to a very short track.")
    elif features.track_point_count is not None and features.track_point_count >= 8:
        risk -= 0.18
        reasons.append("Detection belongs to a long track.")

    if features.inside_projected_court is False:
        risk += 0.28
        reasons.append("Projected foot point is outside the court.")
    elif features.inside_projected_court is True:
        risk -= 0.12
        reasons.append("Projected foot point is inside the court.")
    else:
        reasons.append("Court projection unavailable; image-space rules only.")

    if detection.track_id and detection.track_id in track_score_by_id:
        track_risk = track_score_by_id[detection.track_id].false_positive_risk
        risk = (risk * 0.7) + (track_risk * 0.3)
        reasons.append(f"Blended with track-level risk {track_risk:.2f}.")

    risk = _clamp_risk(risk)
    return DetectionRecognitionScore(
        detection_id=detection.detection_id,
        track_id=detection.track_id,
        false_positive_risk=risk,
        recommended_label=_recommended_label(risk),
        reasons=reasons,
        features=features,
    )


def score_track(track: PlayerTrack, features: TrackRecognitionFeatures, patch: TrackReviewPatch) -> TrackRecognitionScore:
    if track.track_id in patch.excluded_track_ids:
        return TrackRecognitionScore(
            track_id=track.track_id,
            false_positive_risk=1.0,
            recommended_label="HIGH",
            reasons=["Reviewer previously excluded this track."],
            features=features,
        )

    reasons: list[str] = []
    risk = 0.2
    if features.point_count <= 1:
        risk += 0.42
        reasons.append("Track has only one point.")
    elif features.point_count <= 3:
        risk += 0.25
        reasons.append("Track is very short.")
    elif features.point_count >= 8:
        risk -= 0.24
        reasons.append("Track is long enough to be stable.")

    if features.avg_confidence is not None:
        if features.avg_confidence < 0.4:
            risk += 0.28
            reasons.append("Average confidence is low.")
        elif features.avg_confidence >= 0.75:
            risk -= 0.16
            reasons.append("Average confidence is high.")
    else:
        risk += 0.08
        reasons.append("Track has no confidence values.")

    if features.gap_count > 0:
        risk += min(0.18, features.gap_count * 0.04)
        reasons.append("Track has frame gaps.")
    elif features.point_count >= 4:
        risk -= 0.08
        reasons.append("Track is continuous.")

    if features.max_jump_distance_image is not None and features.max_jump_distance_image > 160:
        risk += 0.18
        reasons.append("Track has a large image-space jump.")

    if features.projected_inside_court_ratio is None:
        reasons.append("Court projection unavailable; image-space rules only.")
    elif features.projected_inside_court_ratio < 0.5:
        risk += 0.30
        reasons.append("Most projected track points are outside the court.")
    elif features.projected_inside_court_ratio >= 0.85:
        risk -= 0.14
        reasons.append("Most projected track points are inside the court.")

    risk = _clamp_risk(risk)
    if not reasons:
        reasons.append("No strong risk signals found.")
    return TrackRecognitionScore(
        track_id=track.track_id,
        false_positive_risk=risk,
        recommended_label=_recommended_label(risk),
        reasons=reasons,
        features=features,
    )


def score_project_recognition(
    project_id: str,
    detections: Iterable[Detection],
    tracks: Iterable[PlayerTrack],
    patch: TrackReviewPatch | None = None,
    calibration: Calibration | None = None,
) -> RecognitionScoreProjectResponse:
    patch = patch or TrackReviewPatch()
    detection_list = list(detections)
    track_list = list(tracks)
    detections_by_id = {detection.detection_id: detection for detection in detection_list}
    track_point_counts = {track.track_id: len(track.points) for track in track_list}

    track_scores = [
        score_track(track, extract_track_features(track, detections_by_id, calibration), patch)
        for track in track_list
    ]
    track_score_by_id = {score.track_id: score for score in track_scores}
    detection_scores = [
        score_detection(
            detection,
            extract_detection_features(detection, track_point_counts, calibration),
            patch,
            track_score_by_id,
        )
        for detection in detection_list
    ]
    return RecognitionScoreProjectResponse(
        project_id=project_id,
        detection_scores=detection_scores,
        track_scores=track_scores,
        summary=RecognitionScoreSummary(
            high_risk_detection_count=sum(1 for score in detection_scores if score.false_positive_risk >= HIGH_RISK_THRESHOLD),
            high_risk_track_count=sum(1 for score in track_scores if score.false_positive_risk >= HIGH_RISK_THRESHOLD),
        ),
    )
