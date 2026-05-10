"""Local Lab dataset registry and export routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter
from pydantic import TypeAdapter, ValidationError

from app.api.common import DATA_DIR, api_error, read_json, write_json_model
from app.models import (
    DatasetListResponse,
    DatasetManifest,
    CuratedTrainingLabel,
    CuratedTrainingSample,
    DatasetSummary,
    DecisionAttemptTrainingLabel,
    DecisionEvent,
    DecisionEventsBuildSummary,
    DecisionTrainingSample,
    DetectionTrainingLabel,
    ExtractFramesResponse,
    LocalLabProjectArtifact,
    LocalLabProjectsResponse,
    Calibration,
    Project,
    QuizAttemptRecord,
    QuizPrompt,
    RecognitionScoreProjectResponse,
    RecognitionTrainingSample,
    RunTrackingResponse,
    SkippedProject,
    TrackReviewPatch,
    TrackTrainingLabel,
    VideoSourceRecord,
)
from app.models.base import utc_now
from app.models.tracking import Detection, PlayerTrack
from app.pipeline.recognition_quality import score_project_recognition
from app.services.decision_engine import evaluate_attempt

router = APIRouter(prefix="/local-lab", tags=["local-lab"])

DATASETS_DIR = Path(__file__).resolve().parents[1] / "data" / "datasets"
DATASET_TYPES = ("recognition", "decision", "player_value")
_PROMPTS_ADAPTER = TypeAdapter(list[QuizPrompt])
_ATTEMPTS_ADAPTER = TypeAdapter(list[QuizAttemptRecord])


def _ensure_dataset_dirs() -> None:
    for dataset_type in DATASET_TYPES:
        directory = DATASETS_DIR / dataset_type
        directory.mkdir(parents=True, exist_ok=True)
        for filename in ("samples.jsonl", "labels.jsonl"):
            (directory / filename).touch(exist_ok=True)
        manifest_path = directory / "dataset_manifest.json"
        if not manifest_path.exists():
            write_json_model(
                manifest_path,
                DatasetManifest(
                    dataset_type=dataset_type,  # type: ignore[arg-type]
                    storage_paths=_dataset_storage_paths(dataset_type),
                    notes="Initialized local dataset registry; no export has been run yet.",
                ),
            )


def _dataset_storage_paths(dataset_type: str) -> dict[str, str]:
    directory = DATASETS_DIR / dataset_type
    return {
        "manifest": str(directory / "dataset_manifest.json"),
        "samples": str(directory / "samples.jsonl"),
        "labels": str(directory / "labels.jsonl"),
    }


def _project_dirs() -> Iterable[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.parent for path in DATA_DIR.glob("*/project.json"))


def _read_json_list(path: Path, adapter):
    if not path.exists():
        return []
    return adapter.validate_json(path.read_text(encoding="utf-8"))


def _safe_count_json_list(path: Path, adapter) -> int:
    try:
        return len(_read_json_list(path, adapter))
    except (json.JSONDecodeError, ValidationError):
        return 0


def _latest_artifact_timestamp(directory: Path, project: Project) -> datetime:
    latest_datetime = project.updated_at
    for path in directory.rglob("*.json"):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        latest_datetime = max(latest_datetime, modified_at)
    return latest_datetime


@router.get("/projects", response_model=LocalLabProjectsResponse)
def list_local_lab_projects() -> LocalLabProjectsResponse:
    projects: list[LocalLabProjectArtifact] = []
    for directory in _project_dirs():
        project = Project.model_validate_json((directory / "project.json").read_text(encoding="utf-8"))
        frames_path = directory / "frames" / "index.json"
        frame_count = 0
        if frames_path.exists():
            frame_count = len(ExtractFramesResponse.model_validate(read_json(frames_path)).frames)

        projects.append(
            LocalLabProjectArtifact(
                project_id=project.project_id,
                name=project.name,
                has_video=(directory / "video.json").exists(),
                frame_count=frame_count,
                has_calibration=(directory / "calibration.json").exists(),
                has_tracking=(directory / "tracking.json").exists(),
                has_tracking_review=(directory / "tracking_review_patch.json").exists(),
                has_cleaned_tracking=(directory / "tracking_cleaned.json").exists(),
                has_projected_tracks=(directory / "projected_tracks.json").exists() or (directory / "projected_tracks_cleaned.json").exists(),
                quiz_prompt_count=_safe_count_json_list(directory / "quiz_prompts.json", _PROMPTS_ADAPTER),
                quiz_attempt_count=_safe_count_json_list(directory / "quiz_attempts.json", _ATTEMPTS_ADAPTER),
                updated_at=_latest_artifact_timestamp(directory, project),
                source=VideoSourceRecord.model_validate(read_json(directory / "source.json")) if (directory / "source.json").exists() else None,
            )
        )
    return LocalLabProjectsResponse(projects=projects)


def _training_source_skip_reason(directory: Path, project: Project) -> str | None:
    source_path = directory / "source.json"
    if not source_path.exists():
        return "Missing source governance metadata; defaulting to not eligible for training."
    source = VideoSourceRecord.model_validate(read_json(source_path))
    if not source.allowed_for_training:
        return f"Source is not allowed for training (license={source.license_type}, usage_scope={source.usage_scope})."
    return None


def _training_eligible_project_dirs() -> tuple[list[Path], list[SkippedProject]]:
    eligible: list[Path] = []
    skipped: list[SkippedProject] = []
    for directory in _project_dirs():
        project = Project.model_validate_json((directory / "project.json").read_text(encoding="utf-8"))
        reason = _training_source_skip_reason(directory, project)
        if reason is None:
            eligible.append(directory)
        else:
            skipped.append(SkippedProject(project_id=project.project_id, name=project.name, reason=reason))
    return eligible, skipped




def _increment_distribution(distribution: dict[str, int], key: object) -> None:
    distribution[str(key)] = distribution.get(str(key), 0) + 1


def _source_distributions(project_dirs: Iterable[Path]) -> tuple[dict[str, int], dict[str, int]]:
    license_distribution: dict[str, int] = {}
    usage_distribution: dict[str, int] = {}
    for directory in project_dirs:
        source_path = directory / "source.json"
        if not source_path.exists():
            continue
        source = VideoSourceRecord.model_validate(read_json(source_path))
        _increment_distribution(license_distribution, source.license_type)
        _increment_distribution(usage_distribution, source.usage_scope)
    return dict(sorted(license_distribution.items())), dict(sorted(usage_distribution.items()))

def _tracking_path(directory: Path) -> Path:
    return directory / "tracking.json"


def _review_patch_path(directory: Path) -> Path:
    return directory / "tracking_review_patch.json"


def _calibration_path(directory: Path) -> Path:
    return directory / "calibration.json"


@router.post("/recognition/score-project/{project_id}", response_model=RecognitionScoreProjectResponse)
def score_project_recognition_quality(project_id: str) -> RecognitionScoreProjectResponse:
    directory = DATA_DIR / project_id
    tracking_path = _tracking_path(directory)
    if not tracking_path.exists():
        raise api_error(
            404,
            "TRACKING_NOT_FOUND",
            "No tracking output exists for this project.",
            {"project_id": project_id},
            "Run tracking before scoring recognition quality.",
        )

    tracking = RunTrackingResponse.model_validate(read_json(tracking_path))
    review_patch_path = _review_patch_path(directory)
    review_patch = (
        TrackReviewPatch.model_validate(read_json(review_patch_path))
        if review_patch_path.exists()
        else TrackReviewPatch()
    )
    calibration_path = _calibration_path(directory)
    calibration = Calibration.model_validate(read_json(calibration_path)) if calibration_path.exists() else None
    return score_project_recognition(
        project_id=project_id,
        detections=tracking.detections,
        tracks=tracking.tracks,
        patch=review_patch,
        calibration=calibration,
    )


def _write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(row.model_dump_json() + "\n" for row in rows), encoding="utf-8")


def _average(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _source_trace(directory: Path) -> dict:
    source_path = directory / "source.json"
    if not source_path.exists():
        return {"artifact": str(source_path), "allowed_for_training": False}
    source = VideoSourceRecord.model_validate(read_json(source_path))
    return {
        "artifact": str(source_path),
        "source_id": source.source_id,
        "source_type": source.source_type,
        "license_type": source.license_type,
        "usage_scope": source.usage_scope,
        "allowed_for_training": source.allowed_for_training,
        "rights_confirmed": source.rights_confirmed,
        "league_tag": source.league_tag,
    }


def _curated_dataset_storage_paths(dataset_type: str) -> dict[str, str]:
    directory = DATASETS_DIR / dataset_type
    return {
        "manifest": str(directory / "dataset_manifest.json"),
        "samples": str(directory / "curated_samples.jsonl"),
        "labels": str(directory / "curated_labels.jsonl"),
    }


def _label_distribution(labels: Iterable[CuratedTrainingLabel]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for label in labels:
        distribution[label.label] = distribution.get(label.label, 0) + 1
    return dict(sorted(distribution.items()))


def _positive_negative_counts(labels: Iterable[CuratedTrainingLabel]) -> tuple[int, int]:
    positive_labels = {"VALID_PLAYER_TRACK", "PLAYER", "GOOD_DECISION", "GOOD_READ", "ACCEPTABLE_READ"}
    negative_labels = {"FALSE_POSITIVE_TRACK", "FALSE_POSITIVE", "BAD_DECISION", "BAD_READ", "MISSED_READ"}
    positive = 0
    negative = 0
    for label in labels:
        if label.label in positive_labels:
            positive += 1
        elif label.label in negative_labels:
            negative += 1
    return positive, negative


def _positive_negative_ratio(positive: int, negative: int) -> float | None:
    if negative == 0:
        return None
    return round(positive / negative, 4)


def _curated_manifest(
    *,
    dataset_type: str,
    samples: list[CuratedTrainingSample],
    labels: list[CuratedTrainingLabel],
    project_ids: set[str],
    skipped_projects: list[SkippedProject],
    created_at: datetime,
    notes: str,
) -> DatasetManifest:
    positive_count, negative_count = _positive_negative_counts(labels)
    return DatasetManifest(
        dataset_type=dataset_type,  # type: ignore[arg-type]
        sample_count=len(samples),
        label_count=len(labels),
        project_count=len(project_ids),
        included_project_count=len(project_ids),
        skipped_project_count=len(skipped_projects),
        skipped_projects=skipped_projects,
        exported_at=created_at,
        storage_paths=_curated_dataset_storage_paths(dataset_type),
        positive_sample_count=positive_count,
        negative_sample_count=negative_count,
        positive_negative_ratio=_positive_negative_ratio(positive_count, negative_count),
        source_project_ids=sorted(project_ids),
        skipped_project_ids=[project.project_id for project in skipped_projects],
        label_distribution=_label_distribution(labels),
        created_at=created_at,
        notes=notes,
    )


def _add_curated_pair(
    samples: list[CuratedTrainingSample],
    labels: list[CuratedTrainingLabel],
    *,
    sample_id: str,
    dataset_type: str,
    sample_type: str,
    project_id: str,
    target_type: str,
    target_id: str,
    label: str,
    source: str,
    rationale: str,
    trace: dict,
    payload: dict,
    created_at: datetime,
    source_trace: dict | None = None,
) -> None:
    full_trace = {"project_id": project_id, "source_trace": source_trace or {}, **trace}
    samples.append(
        CuratedTrainingSample(
            sample_id=sample_id,
            dataset_type=dataset_type,  # type: ignore[arg-type]
            sample_type=sample_type,
            project_id=project_id,
            label=label,
            source=source,  # type: ignore[arg-type]
            trace=full_trace,
            payload=payload,
            created_at=created_at,
        )
    )
    labels.append(
        CuratedTrainingLabel(
            sample_id=sample_id,
            dataset_type=dataset_type,  # type: ignore[arg-type]
            target_type=target_type,
            target_id=target_id,
            project_id=project_id,
            label=label,
            source=source,  # type: ignore[arg-type]
            rationale=rationale,
            trace=full_trace,
            created_at=created_at,
        )
    )


def _tracking_for_positive_samples(directory: Path) -> tuple[RunTrackingResponse | None, str]:
    cleaned_path = directory / "tracking_cleaned.json"
    if cleaned_path.exists():
        return RunTrackingResponse.model_validate(read_json(cleaned_path)), "tracking_cleaned.json"
    tracking_path = directory / "tracking.json"
    if tracking_path.exists():
        return RunTrackingResponse.model_validate(read_json(tracking_path)), "tracking.json"
    return None, "tracking.json"


def _raw_tracking(directory: Path) -> RunTrackingResponse | None:
    tracking_path = directory / "tracking.json"
    if not tracking_path.exists():
        return None
    return RunTrackingResponse.model_validate(read_json(tracking_path))


@router.post("/datasets/recognition/curate", response_model=DatasetManifest)
def curate_recognition_dataset() -> DatasetManifest:
    _ensure_dataset_dirs()
    samples: list[CuratedTrainingSample] = []
    labels: list[CuratedTrainingLabel] = []
    project_ids: set[str] = set()
    created_at = utc_now()

    eligible_dirs, skipped_projects = _training_eligible_project_dirs()
    for directory in eligible_dirs:
        positive_tracking, positive_artifact = _tracking_for_positive_samples(directory)
        raw_tracking = _raw_tracking(directory)
        if positive_tracking is None and raw_tracking is None:
            continue
        review_path = directory / "tracking_review_patch.json"
        review_patch = TrackReviewPatch.model_validate(read_json(review_path)) if review_path.exists() else TrackReviewPatch()
        project_id = (positive_tracking or raw_tracking).project_id  # type: ignore[union-attr]
        project_ids.add(project_id)
        project_source_trace = _source_trace(directory)

        excluded_track_ids = set(review_patch.excluded_track_ids)
        excluded_detection_ids = set(review_patch.excluded_detection_ids)
        positive_tracks: list[PlayerTrack] = [] if positive_tracking is None else [
            track for track in positive_tracking.tracks if track.track_id not in excluded_track_ids
        ]
        valid_track_ids = {track.track_id for track in positive_tracks}
        source_for_tracks = "TRACKING_REVIEW" if review_path.exists() else "HEURISTIC"

        for track in positive_tracks:
            trace = {
                "artifact": positive_artifact,
                "track_id": track.track_id,
                "review_patch": str(review_path) if review_path.exists() else None,
                "excluded_track_ids": sorted(excluded_track_ids),
            }
            _add_curated_pair(
                samples,
                labels,
                sample_id=f"{project_id}:track:{track.track_id}:VALID_PLAYER_TRACK",
                dataset_type="recognition",
                sample_type="track",
                project_id=project_id,
                target_type="track",
                target_id=track.track_id,
                label="VALID_PLAYER_TRACK",
                source=source_for_tracks,
                rationale="Track is present in the training-eligible tracking artifact and is not excluded by tracking review.",
                trace=trace,
                payload=track.model_dump(mode="json"),
                created_at=created_at,
                source_trace=project_source_trace,
            )

        positive_detections: list[Detection] = [] if positive_tracking is None else [
            detection
            for detection in positive_tracking.detections
            if detection.track_id in valid_track_ids and detection.detection_id not in excluded_detection_ids
        ]
        for detection in positive_detections:
            trace = {
                "artifact": positive_artifact,
                "detection_id": detection.detection_id,
                "track_id": detection.track_id,
                "attached_to_valid_track": True,
            }
            _add_curated_pair(
                samples,
                labels,
                sample_id=f"{project_id}:detection:{detection.detection_id}:PLAYER",
                dataset_type="recognition",
                sample_type="detection",
                project_id=project_id,
                target_type="detection",
                target_id=detection.detection_id,
                label="PLAYER",
                source="HEURISTIC",
                rationale="Detection is attached to a valid non-excluded player track.",
                trace=trace,
                payload=detection.model_dump(mode="json"),
                created_at=created_at,
                source_trace=project_source_trace,
            )

        raw_track_by_id = {track.track_id: track for track in raw_tracking.tracks} if raw_tracking is not None else {}
        for track_id in sorted(excluded_track_ids):
            track_payload = raw_track_by_id.get(track_id).model_dump(mode="json") if track_id in raw_track_by_id else {"track_id": track_id}
            trace = {
                "artifact": "tracking_review_patch.json",
                "tracking_artifact": "tracking.json",
                "excluded_track_ids": sorted(excluded_track_ids),
            }
            _add_curated_pair(
                samples,
                labels,
                sample_id=f"{project_id}:track:{track_id}:FALSE_POSITIVE_TRACK",
                dataset_type="recognition",
                sample_type="track",
                project_id=project_id,
                target_type="track",
                target_id=track_id,
                label="FALSE_POSITIVE_TRACK",
                source="TRACKING_REVIEW",
                rationale="Track ID is explicitly listed in tracking_review_patch.excluded_track_ids.",
                trace=trace,
                payload=track_payload,
                created_at=created_at,
                source_trace=project_source_trace,
            )

        raw_detection_by_id = {detection.detection_id: detection for detection in raw_tracking.detections} if raw_tracking is not None else {}
        for detection_id in sorted(excluded_detection_ids):
            detection = raw_detection_by_id.get(detection_id)
            trace = {
                "artifact": "tracking_review_patch.json",
                "tracking_artifact": "tracking.json",
                "excluded_detection_ids": sorted(excluded_detection_ids),
            }
            _add_curated_pair(
                samples,
                labels,
                sample_id=f"{project_id}:detection:{detection_id}:FALSE_POSITIVE",
                dataset_type="recognition",
                sample_type="detection",
                project_id=project_id,
                target_type="detection",
                target_id=detection_id,
                label="FALSE_POSITIVE",
                source="TRACKING_REVIEW",
                rationale="Detection ID is explicitly listed in tracking_review_patch.excluded_detection_ids.",
                trace=trace,
                payload=detection.model_dump(mode="json") if detection is not None else {"detection_id": detection_id},
                created_at=created_at,
                source_trace=project_source_trace,
            )

    directory = DATASETS_DIR / "recognition"
    _write_jsonl(directory / "curated_samples.jsonl", samples)
    _write_jsonl(directory / "curated_labels.jsonl", labels)
    manifest = _curated_manifest(
        dataset_type="recognition",
        samples=samples,
        labels=labels,
        project_ids=project_ids,
        skipped_projects=skipped_projects,
        created_at=created_at,
        notes="Curated recognition dataset with positive player tracks/detections and reviewer-sourced false positives. No ML training was performed.",
    )
    write_json_model(directory / "dataset_manifest.json", manifest)
    return manifest


def _option_label(prompt: QuizPrompt, option) -> tuple[str | None, str | None, str | None, dict]:
    expected_values = [candidate.expected_value for candidate in prompt.options if candidate.expected_value is not None]
    max_expected_value = max(expected_values) if expected_values else None
    within_best = max_expected_value is not None and option.expected_value is not None and max_expected_value - option.expected_value <= 0.1
    below_best = max_expected_value is not None and option.expected_value is not None and max_expected_value - option.expected_value >= 0.25
    trace = {
        "prompt_id": prompt.prompt_id,
        "option_id": option.option_id,
        "is_correct": option.is_correct,
        "expected_value": option.expected_value,
        "max_expected_value": max_expected_value,
        "within_0_1_of_max_expected_value": within_best,
        "lower_than_max_by_at_least_0_25": below_best,
    }
    if option.is_correct:
        return "GOOD_DECISION", "QUIZ_AUTHOR", "Option is marked correct by the quiz author.", trace
    if within_best:
        return "GOOD_DECISION", "EXPECTED_VALUE", "Option expected value is within 0.1 of the prompt maximum expected value.", trace
    if below_best:
        return "BAD_DECISION", "EXPECTED_VALUE", "Option expected value is lower than the prompt maximum by at least 0.25.", trace
    if not option.is_correct:
        return "BAD_DECISION", "QUIZ_AUTHOR", "Option is not marked correct by the quiz author.", trace
    return None, None, None, trace


def _attempt_read_label(attempt: QuizAttemptRecord) -> tuple[str, str]:
    if attempt.timed_out:
        return "MISSED_READ", "Attempt timed out before a decision was selected."
    if attempt.score >= 80:
        return "GOOD_READ", "Attempt score is at least 80."
    if attempt.score >= 50:
        return "ACCEPTABLE_READ", "Attempt score is between 50 and 79."
    return "BAD_READ", "Attempt score is below 50."


@router.post("/datasets/decision/curate", response_model=DatasetManifest)
def curate_decision_dataset() -> DatasetManifest:
    _ensure_dataset_dirs()
    samples: list[CuratedTrainingSample] = []
    labels: list[CuratedTrainingLabel] = []
    project_ids: set[str] = set()
    created_at = utc_now()

    eligible_dirs, skipped_projects = _training_eligible_project_dirs()
    source_license_distribution, usage_scope_distribution = _source_distributions(eligible_dirs)

    for directory in eligible_dirs:
        prompts = _read_json_list(directory / "quiz_prompts.json", _PROMPTS_ADAPTER)
        attempts = _read_json_list(directory / "quiz_attempts.json", _ATTEMPTS_ADAPTER)
        prompt_by_id = {prompt.prompt_id: prompt for prompt in prompts}
        project_source_trace = _source_trace(directory)

        for prompt in prompts:
            project_ids.add(prompt.project_id)
            for option in prompt.options:
                label, source, rationale, trace = _option_label(prompt, option)
                if label is None or source is None or rationale is None:
                    continue
                _add_curated_pair(
                    samples,
                    labels,
                    sample_id=f"{prompt.project_id}:prompt:{prompt.prompt_id}:option:{option.option_id}:{label}",
                    dataset_type="decision",
                    sample_type="option",
                    project_id=prompt.project_id,
                    target_type="option",
                    target_id=option.option_id,
                    label=label,
                    source=source,
                    rationale=rationale,
                    trace=trace,
                    payload={
                        "prompt": prompt.model_dump(mode="json", exclude={"options"}),
                        "option": option.model_dump(mode="json"),
                    },
                    created_at=created_at,
                    source_trace=project_source_trace,
                )

        for attempt in attempts:
            prompt = prompt_by_id.get(attempt.prompt_id)
            project_ids.add(attempt.project_id)
            label, rationale = _attempt_read_label(attempt)
            trace = {
                "attempt_id": attempt.attempt_id,
                "prompt_id": attempt.prompt_id,
                "selected_option_id": attempt.selected_option_id,
                "correct_option_id": attempt.correct_option_id,
                "score": attempt.score,
                "timed_out": attempt.timed_out,
                "response_time_ms": attempt.response_time_ms,
            }
            _add_curated_pair(
                samples,
                labels,
                sample_id=f"{attempt.project_id}:attempt:{attempt.attempt_id}:{label}",
                dataset_type="decision",
                sample_type="attempt",
                project_id=attempt.project_id,
                target_type="attempt",
                target_id=attempt.attempt_id,
                label=label,
                source="QUIZ_ATTEMPT",
                rationale=rationale,
                trace=trace,
                payload={
                    "attempt": attempt.model_dump(mode="json"),
                    "prompt": prompt.model_dump(mode="json") if prompt is not None else None,
                },
                created_at=created_at,
                source_trace=project_source_trace,
            )

    directory = DATASETS_DIR / "decision"
    _write_jsonl(directory / "curated_samples.jsonl", samples)
    _write_jsonl(directory / "curated_labels.jsonl", labels)
    manifest = _curated_manifest(
        dataset_type="decision",
        samples=samples,
        labels=labels,
        project_ids=project_ids,
        skipped_projects=skipped_projects,
        created_at=created_at,
        notes="Curated decision dataset with good/bad option labels and read-quality attempt labels. No ML training was performed.",
    )
    write_json_model(directory / "dataset_manifest.json", manifest)
    return manifest

@router.post("/datasets/recognition/export", response_model=DatasetManifest)
def export_recognition_dataset() -> DatasetManifest:
    _ensure_dataset_dirs()
    samples: list[RecognitionTrainingSample] = []
    labels: list[DetectionTrainingLabel | TrackTrainingLabel] = []
    project_ids: set[str] = set()
    created_at = utc_now()

    eligible_dirs, skipped_projects = _training_eligible_project_dirs()

    source_license_distribution, usage_scope_distribution = _source_distributions(eligible_dirs)

    for directory in eligible_dirs:
        tracking_path = directory / "tracking.json"
        review_path = directory / "tracking_review_patch.json"
        if not tracking_path.exists() or not review_path.exists():
            continue
        tracking = RunTrackingResponse.model_validate(read_json(tracking_path))
        review_patch = TrackReviewPatch.model_validate(read_json(review_path))
        project_ids.add(tracking.project_id)
        excluded_detection_ids = set(review_patch.excluded_detection_ids)
        excluded_track_ids = set(review_patch.excluded_track_ids)

        for detection in tracking.detections:
            samples.append(
                RecognitionTrainingSample(
                    sample_type="detection",
                    project_id=tracking.project_id,
                    frame_id=detection.frame_id,
                    frame_index=detection.frame_index,
                    detection_id=detection.detection_id,
                    track_id=detection.track_id,
                    payload=detection.model_dump(mode="json"),
                )
            )
            if detection.detection_id in excluded_detection_ids:
                labels.append(
                    DetectionTrainingLabel(
                        project_id=tracking.project_id,
                        frame_id=detection.frame_id,
                        frame_index=detection.frame_index,
                        detection_id=detection.detection_id,
                        track_id=detection.track_id,
                        label="FALSE_POSITIVE",
                        source="TRACKING_REVIEW",
                        created_at=created_at,
                        notes=review_patch.notes,
                    )
                )

        for track in tracking.tracks:
            samples.append(
                RecognitionTrainingSample(
                    sample_type="track",
                    project_id=tracking.project_id,
                    track_id=track.track_id,
                    payload=track.model_dump(mode="json"),
                )
            )
            labels.append(
                TrackTrainingLabel(
                    project_id=tracking.project_id,
                    track_id=track.track_id,
                    label="FALSE_POSITIVE_TRACK" if track.track_id in excluded_track_ids else "VALID_PLAYER_TRACK",
                    source="TRACKING_REVIEW" if track.track_id in excluded_track_ids else "HEURISTIC",
                    created_at=created_at,
                    notes=review_patch.notes if track.track_id in excluded_track_ids else "Generated from non-excluded tracking review artifact.",
                )
            )

    directory = DATASETS_DIR / "recognition"
    _write_jsonl(directory / "samples.jsonl", samples)
    _write_jsonl(directory / "labels.jsonl", labels)
    manifest = DatasetManifest(
        dataset_type="recognition",
        sample_count=len(samples),
        label_count=len(labels),
        project_count=len(project_ids),
        included_project_count=len(project_ids),
        skipped_project_count=len(skipped_projects),
        skipped_projects=skipped_projects,
        exported_at=created_at,
        storage_paths=_dataset_storage_paths("recognition"),
        source_project_ids=sorted(project_ids),
        skipped_project_ids=[project.project_id for project in skipped_projects],
        source_license_distribution=source_license_distribution,
        usage_scope_distribution=usage_scope_distribution,
        notes="Recognition labels are derived from tracking review exclusions plus heuristic valid-track labels.",
    )
    write_json_model(directory / "dataset_manifest.json", manifest)
    return manifest


@router.post("/datasets/decision/export", response_model=DatasetManifest)
def export_decision_dataset() -> DatasetManifest:
    _ensure_dataset_dirs()
    samples: list[DecisionTrainingSample] = []
    labels: list[DecisionAttemptTrainingLabel] = []
    prompt_project_ids: set[str] = set()
    label_project_ids: set[str] = set()
    created_at = utc_now()

    eligible_dirs, skipped_projects = _training_eligible_project_dirs()
    source_license_distribution, usage_scope_distribution = _source_distributions(eligible_dirs)

    for directory in eligible_dirs:
        prompts = _read_json_list(directory / "quiz_prompts.json", _PROMPTS_ADAPTER)
        attempts = _read_json_list(directory / "quiz_attempts.json", _ATTEMPTS_ADAPTER)
        for prompt in prompts:
            correct_option = next(option for option in prompt.options if option.is_correct)
            prompt_project_ids.add(prompt.project_id)
            samples.append(
                DecisionTrainingSample(
                    project_id=prompt.project_id,
                    prompt_id=prompt.prompt_id,
                    frame_id=prompt.frame_id,
                    frame_index=prompt.frame_index,
                    court_role_target=prompt.court_role_target,
                    situation_type=prompt.situation_type,
                    question_mode=prompt.question_mode,
                    option_count=len(prompt.options),
                    correct_option_id=correct_option.option_id,
                    options=prompt.options,
                    explanation=prompt.explanation,
                )
            )
        for attempt in attempts:
            label_project_ids.add(attempt.project_id)
            labels.append(
                DecisionAttemptTrainingLabel(
                    project_id=attempt.project_id,
                    prompt_id=attempt.prompt_id,
                    selected_option_id=attempt.selected_option_id,
                    correct_option_id=attempt.correct_option_id,
                    is_correct=attempt.is_correct,
                    score=attempt.score,
                    opportunity_cost=attempt.opportunity_cost,
                    response_time_ms=attempt.response_time_ms,
                    timed_out=attempt.timed_out,
                    user_role=attempt.user_role,
                    created_at=attempt.attempted_at,
                )
            )

    directory = DATASETS_DIR / "decision"
    _write_jsonl(directory / "samples.jsonl", samples)
    _write_jsonl(directory / "labels.jsonl", labels)
    manifest = DatasetManifest(
        dataset_type="decision",
        sample_count=len(samples),
        label_count=len(labels),
        project_count=len(prompt_project_ids | label_project_ids),
        included_project_count=len(prompt_project_ids | label_project_ids),
        skipped_project_count=len(skipped_projects),
        skipped_projects=skipped_projects,
        exported_at=created_at,
        storage_paths=_dataset_storage_paths("decision"),
        source_project_ids=sorted(prompt_project_ids | label_project_ids),
        skipped_project_ids=[project.project_id for project in skipped_projects],
        source_license_distribution=source_license_distribution,
        usage_scope_distribution=usage_scope_distribution,
        notes="Decision samples come from quiz prompts; labels come from quiz attempts.",
    )
    write_json_model(directory / "dataset_manifest.json", manifest)
    return manifest


@router.post("/decision-events/build", response_model=DecisionEventsBuildSummary)
def build_decision_events() -> DecisionEventsBuildSummary:
    _ensure_dataset_dirs()
    events: list[DecisionEvent] = []

    for directory in _project_dirs():
        prompts = _read_json_list(directory / "quiz_prompts.json", _PROMPTS_ADAPTER)
        attempts = _read_json_list(directory / "quiz_attempts.json", _ATTEMPTS_ADAPTER)
        prompt_by_id = {prompt.prompt_id: prompt for prompt in prompts}

        for attempt in attempts:
            prompt = prompt_by_id.get(attempt.prompt_id)
            if prompt is None:
                continue
            events.append(evaluate_attempt(prompt, attempt))

    output_path = DATASETS_DIR / "player_value" / "player_decision_events.jsonl"
    _write_jsonl(output_path, events)

    opportunity_costs = [event.opportunity_cost for event in events if event.opportunity_cost is not None]
    return DecisionEventsBuildSummary(
        event_count=len(events),
        avg_raw_score=_average([event.raw_score for event in events]),
        avg_role_adjusted_score=_average([event.role_adjusted_score for event in events]),
        opportunity_cost_avg=_average(opportunity_costs),
    )


def _summary_for_dataset(dataset_type: str) -> DatasetSummary:
    _ensure_dataset_dirs()
    manifest_path = DATASETS_DIR / dataset_type / "dataset_manifest.json"
    manifest = DatasetManifest.model_validate(read_json(manifest_path))
    return DatasetSummary(
        dataset_type=manifest.dataset_type,
        sample_count=manifest.sample_count,
        label_count=manifest.label_count,
        project_count=manifest.project_count,
        last_exported_at=manifest.exported_at,
        storage_paths=manifest.storage_paths,
        positive_sample_count=manifest.positive_sample_count,
        negative_sample_count=manifest.negative_sample_count,
        positive_negative_ratio=manifest.positive_negative_ratio,
        label_distribution=manifest.label_distribution,
    )


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    return DatasetListResponse(datasets=[_summary_for_dataset(dataset_type) for dataset_type in DATASET_TYPES])
