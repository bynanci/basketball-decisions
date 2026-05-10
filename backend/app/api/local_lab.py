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


@router.post("/datasets/recognition/export", response_model=DatasetManifest)
def export_recognition_dataset() -> DatasetManifest:
    _ensure_dataset_dirs()
    samples: list[RecognitionTrainingSample] = []
    labels: list[DetectionTrainingLabel | TrackTrainingLabel] = []
    project_ids: set[str] = set()
    created_at = utc_now()

    eligible_dirs, skipped_projects = _training_eligible_project_dirs()

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
    )


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    return DatasetListResponse(datasets=[_summary_for_dataset(dataset_type) for dataset_type in DATASET_TYPES])
