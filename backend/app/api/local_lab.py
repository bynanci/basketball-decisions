"""Local Lab dataset registry and export routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fastapi import APIRouter
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.api.common import DATA_DIR, api_error, read_json, write_json_model
from app.api.reference_videos import reference_video_summary
from app.models import (
    DatasetHealthResponse,
    DatasetListResponse,
    DatasetManifest,
    CuratedTrainingLabel,
    CuratedTrainingSample,
    DatasetSummary,
    DecisionAttemptTrainingLabel,
    DecisionEvent,
    DecisionDiagnosticsReport,
    DecisionEventsBuildSummary,
    DecisionTrainingSample,
    DetectionTrainingLabel,
    ExtractFramesResponse,
    LocalLabProjectArtifact,
    LocalLabProjectsResponse,
    PlayerAliasListResponse,
    PlayerValueBuildResponse,
    PlayerValueComponent,
    PlayerValueEvidenceEvent,
    PlayerValueEvidenceResponse,
    PlayerValueSummary,
    PlayerValueTrace,
    RoleBreakdownItem,
    SituationBreakdownItem,
    Calibration,
    Project,
    QuizAttemptRecord,
    QuizPrompt,
    RecognitionActivationRequest,
    RecognitionActivationResponse,
    RecognitionEvaluationReportRegistry,
    RecognitionModelComparison,
    RecognitionModelInfo,
    RecognitionModelRegistry,
    RecognitionScoreProjectResponse,
    RecognitionTrainingSample,
    RunTrackingResponse,
    SkippedProject,
    TrackReviewPatch,
    TrackTrainingLabel,
    VideoSourceRecord,
    ReferenceVideoDraftSummary,
)
from app.models.base import utc_now
from app.models.tracking import Detection, PlayerTrack
from app.pipeline.recognition_quality import score_project_recognition
from app.models.quiz import normalize_track_id_list
from app.services.decision_engine import evaluate_attempt
from app.services.decision_diagnostics import build_decision_diagnostics
from app.services.dataset_health import dataset_health_response
from app.services.recognition_training import activate_model, compare_models, get_model_version, load_evaluation_report_registry, load_recognition_registry, score_project_with_model, train_baseline

router = APIRouter(prefix="/local-lab", tags=["local-lab"])


class RecognitionModelCompareRequest(BaseModel):
    base_version: str
    candidate_version: str

DATASETS_DIR = Path(__file__).resolve().parents[1] / "data" / "datasets"
RECOGNITION_MODELS_DIR = Path(__file__).resolve().parents[1] / "data" / "models" / "recognition"
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


def _player_alias_counts(directory: Path) -> tuple[int, int, int]:
    alias_path = directory / "player_aliases.json"
    alias_count = 0
    aliased_track_ids: set[str] = set()
    if alias_path.exists():
        try:
            aliases = PlayerAliasListResponse.model_validate(read_json(alias_path))
            alias_count = len(aliases.aliases)
            aliased_track_ids = {track_id for alias in aliases.aliases for track_id in alias.track_ids}
        except (json.JSONDecodeError, ValidationError):
            alias_count = 0
            aliased_track_ids = set()

    tracking_path = directory / "tracking_cleaned.json" if (directory / "tracking_cleaned.json").exists() else directory / "tracking.json"
    if not tracking_path.exists():
        return alias_count, len(aliased_track_ids), 0
    try:
        tracking = RunTrackingResponse.model_validate(read_json(tracking_path))
    except (json.JSONDecodeError, ValidationError):
        return alias_count, len(aliased_track_ids), 0

    track_ids = {track.track_id for track in tracking.tracks}
    aliased_existing = aliased_track_ids.intersection(track_ids)
    return alias_count, len(aliased_existing), len(track_ids - aliased_existing)


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

        player_alias_count, aliased_track_count, unaliased_track_count = _player_alias_counts(directory)

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
                player_alias_count=player_alias_count,
                aliased_track_count=aliased_track_count,
                unaliased_track_count=unaliased_track_count,
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


@router.get("/models/recognition", response_model=RecognitionModelRegistry)
def get_recognition_model_registry() -> RecognitionModelRegistry:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return load_recognition_registry(RECOGNITION_MODELS_DIR)


@router.post("/models/recognition/train-baseline", response_model=RecognitionModelInfo)
def train_recognition_baseline(activate: bool = False) -> RecognitionModelInfo:
    _ensure_dataset_dirs()
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return train_baseline(DATASETS_DIR, RECOGNITION_MODELS_DIR, activate=activate)


@router.get("/models/recognition/compare", response_model=RecognitionModelComparison)
def compare_recognition_models(base_version: str, candidate_version: str) -> RecognitionModelComparison:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return compare_models(RECOGNITION_MODELS_DIR, base_version, candidate_version)


@router.post("/models/recognition/compare", response_model=RecognitionModelComparison)
def post_compare_recognition_models(payload: RecognitionModelCompareRequest) -> RecognitionModelComparison:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return compare_models(RECOGNITION_MODELS_DIR, payload.base_version, payload.candidate_version)


@router.get("/models/recognition/evaluations", response_model=RecognitionEvaluationReportRegistry)
def get_recognition_evaluations_alias() -> RecognitionEvaluationReportRegistry:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return load_evaluation_report_registry(RECOGNITION_MODELS_DIR)


@router.get("/models/recognition/evaluation-reports", response_model=RecognitionEvaluationReportRegistry)
def get_recognition_evaluation_reports() -> RecognitionEvaluationReportRegistry:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return load_evaluation_report_registry(RECOGNITION_MODELS_DIR)


@router.get("/models/recognition/{version}", response_model=RecognitionModelInfo)
def get_recognition_model_version(version: str) -> RecognitionModelInfo:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return get_model_version(RECOGNITION_MODELS_DIR, version)


@router.post("/models/recognition/{version}/activate", response_model=RecognitionActivationResponse)
def activate_recognition_model(version: str, payload: RecognitionActivationRequest | None = None) -> RecognitionActivationResponse:
    RECOGNITION_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if payload is not None and not payload.activate:
        raise api_error(
            400,
            "RECOGNITION_ACTIVATION_REQUIRED",
            "Activation requests must set activate=true.",
            {"version": version},
            "Call this endpoint only when intentionally activating or rolling back to a registered model version.",
        )
    return activate_model(RECOGNITION_MODELS_DIR, version, payload.reason if payload else None)


@router.post("/models/recognition/score-project/{project_id}", response_model=RecognitionScoreProjectResponse)
def score_project_recognition_model(project_id: str) -> RecognitionScoreProjectResponse:
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
    calibration_path = _calibration_path(directory)
    calibration = Calibration.model_validate(read_json(calibration_path)) if calibration_path.exists() else None
    return score_project_with_model(project_id, tracking, RECOGNITION_MODELS_DIR, calibration)


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


def _decision_diagnostics_path() -> Path:
    return DATASETS_DIR / "decision" / "decision_diagnostics.json"


@router.post("/decision-diagnostics/build", response_model=DecisionDiagnosticsReport)
def build_decision_diagnostics_report() -> DecisionDiagnosticsReport:
    _ensure_dataset_dirs()
    report = build_decision_diagnostics(list(_project_dirs()), DATASETS_DIR / "player_value" / "player_decision_events.jsonl")
    write_json_model(_decision_diagnostics_path(), report)
    return report


@router.get("/decision-diagnostics", response_model=DecisionDiagnosticsReport)
def get_decision_diagnostics_report() -> DecisionDiagnosticsReport:
    path = _decision_diagnostics_path()
    if not path.exists():
        raise api_error(
            404,
            "DECISION_DIAGNOSTICS_NOT_FOUND",
            "Decision diagnostics have not been built yet.",
            {"path": str(path)},
            "Run POST /api/local-lab/decision-diagnostics/build first.",
        )
    return DecisionDiagnosticsReport.model_validate(read_json(path))


def _player_value_summary_path() -> Path:
    return DATASETS_DIR / "player_value" / "player_value_summary.json"


def _decision_events_path() -> Path:
    return DATASETS_DIR / "player_value" / "player_decision_events.jsonl"


def _read_decision_event_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise api_error(
                422,
                "INVALID_DECISION_EVENTS_JSONL",
                "Player decision events contain invalid JSONL.",
                {"path": str(path), "line": line_number, "error": str(exc)},
                "Rebuild decision events before building Player Value summaries.",
            ) from exc
    return rows


def _identity_track_ids_from_event_trace(
    row: dict[str, Any], event: DecisionEvent, prompt: dict[str, Any]
) -> tuple[set[str], bool]:
    """Return identity-bearing track IDs without treating frame context as identity.

    Migration safety: context_track_ids describe everyone visible in a frame. They
    are intentionally excluded here so Player Value cannot pick the first alias
    from a multi-player frame. The only fallback reads explicit option-level
    source_track_ids from old prompt traces when an older event row lacks its own
    source_track_ids.
    """

    source_track_ids = set(normalize_track_id_list(event.source_track_ids))
    if source_track_ids:
        return source_track_ids, False

    fallback_track_ids: set[str] = set()
    if event.selected_option_id and isinstance(prompt.get("options"), list):
        for option in prompt["options"]:
            if isinstance(option, dict) and option.get("option_id") in {event.selected_option_id, event.correct_option_id}:
                fallback_track_ids.update(
                    str(item).strip()
                    for item in option.get("source_track_ids", [])
                    if str(item).strip()
                )
    if fallback_track_ids:
        return fallback_track_ids, False

    context_track_ids = set(normalize_track_id_list(event.context_track_ids))
    if not context_track_ids and isinstance(row.get("context_track_ids"), list):
        context_track_ids = set(str(item).strip() for item in row["context_track_ids"] if str(item).strip())
    return set(), bool(context_track_ids)

def _raw_prompts_by_project() -> dict[str, dict[str, dict[str, Any]]]:
    prompts_by_project: dict[str, dict[str, dict[str, Any]]] = {}
    for directory in _project_dirs():
        path = directory / "quiz_prompts.json"
        if not path.exists():
            continue
        try:
            raw_prompts = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(raw_prompts, list):
            continue
        for prompt in raw_prompts:
            if not isinstance(prompt, dict):
                continue
            project_id = str(prompt.get("project_id") or directory.name)
            prompt_id = str(prompt.get("prompt_id") or "")
            if prompt_id:
                prompts_by_project.setdefault(project_id, {})[prompt_id] = prompt
    return prompts_by_project


def _source_id_for_project(directory: Path) -> str | None:
    source_path = directory / "source.json"
    if not source_path.exists():
        return None
    try:
        source = VideoSourceRecord.model_validate(read_json(source_path))
    except (json.JSONDecodeError, ValidationError):
        return None
    return source.source_id


def _tracking_for_player_value(directory: Path) -> RunTrackingResponse | None:
    for filename in ("tracking_cleaned.json", "tracking.json"):
        path = directory / filename
        if path.exists():
            try:
                return RunTrackingResponse.model_validate(read_json(path))
            except (json.JSONDecodeError, ValidationError):
                return None
    return None


def _review_patch_for_player_value(directory: Path) -> TrackReviewPatch:
    path = directory / "tracking_review_patch.json"
    if not path.exists():
        return TrackReviewPatch()
    try:
        return TrackReviewPatch.model_validate(read_json(path))
    except (json.JSONDecodeError, ValidationError):
        return TrackReviewPatch()


def _recognition_scores_for_project(project_id: str, directory: Path) -> RecognitionScoreProjectResponse | None:
    tracking_path = directory / "tracking.json"
    if not tracking_path.exists():
        return None
    try:
        tracking = RunTrackingResponse.model_validate(read_json(tracking_path))
        calibration_path = directory / "calibration.json"
        calibration = Calibration.model_validate(read_json(calibration_path)) if calibration_path.exists() else None
        return score_project_recognition(
            project_id=project_id,
            detections=tracking.detections,
            tracks=tracking.tracks,
            patch=_review_patch_for_player_value(directory),
            calibration=calibration,
        )
    except (json.JSONDecodeError, ValidationError):
        return None


def _population_stddev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def _clip_score(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 4)


def _avg_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _component(name: str, value: float, weight: float, explanation: str) -> PlayerValueComponent:
    return PlayerValueComponent(
        name=name,
        value=round(value, 4),
        weight=weight,
        contribution=round(value * weight, 4),
        explanation=explanation,
    )


def _build_player_value_response() -> PlayerValueBuildResponse:
    _ensure_dataset_dirs()
    generated_at = utc_now()
    global_warnings: list[str] = []
    event_rows = _read_decision_event_rows(_decision_events_path())
    if not event_rows:
        global_warnings.append("No player decision events were found; run Decision Engine v1 first.")

    prompts_by_project = _raw_prompts_by_project()
    project_dirs = {directory.name: directory for directory in _project_dirs()}
    alias_by_project_key: dict[tuple[str, str], Any] = {}
    project_has_aliases: dict[str, bool] = {}
    source_ids_by_project: dict[str, str] = {}
    tracking_by_project: dict[str, RunTrackingResponse | None] = {}
    review_by_project: dict[str, TrackReviewPatch] = {}
    recognition_by_project: dict[str, RecognitionScoreProjectResponse | None] = {}

    track_alias_lookup: dict[tuple[str, str], Any] = {}
    for project_id, directory in project_dirs.items():
        source_id = _source_id_for_project(directory)
        if source_id:
            source_ids_by_project[project_id] = source_id
        aliases: PlayerAliasListResponse | None = None
        alias_path = directory / "player_aliases.json"
        if alias_path.exists():
            try:
                aliases = PlayerAliasListResponse.model_validate(read_json(alias_path))
            except (json.JSONDecodeError, ValidationError):
                global_warnings.append(f"Project {project_id} has invalid player_aliases.json; events may be UNKNOWN.")
        project_has_aliases[project_id] = bool(aliases and aliases.aliases)
        if aliases:
            for alias in aliases.aliases:
                alias_by_project_key[(project_id, alias.player_key)] = alias
                for track_id in alias.track_ids:
                    track_alias_lookup[(project_id, track_id)] = alias
        tracking_by_project[project_id] = _tracking_for_player_value(directory)
        review_by_project[project_id] = _review_patch_for_player_value(directory)
        recognition_by_project[project_id] = _recognition_scores_for_project(project_id, directory)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    event_track_ids: dict[tuple[str, str], set[str]] = {}
    link_warnings: dict[tuple[str, str], list[str]] = {}

    for row in event_rows:
        try:
            event = DecisionEvent.model_validate(row)
        except ValidationError as exc:
            raise api_error(
                422,
                "INVALID_DECISION_EVENT_SCHEMA",
                "A player decision event does not match the DecisionEvent schema.",
                {"errors": exc.errors(), "event": row},
                "Rebuild decision events before building Player Value summaries.",
            ) from exc
        project_id = event.project_id
        prompt = prompts_by_project.get(project_id, {}).get(event.prompt_id, {})
        candidate_track_ids, has_context_only_tracks = _identity_track_ids_from_event_trace(row, event, prompt)

        explicit_player_key = row.get("player_key")
        warning_messages: list[str] = []
        if has_context_only_tracks:
            warning_messages.append(
                "Decision event has only frame context tracks and no identity-bearing source_track_ids; assigned to UNKNOWN."
            )
        if isinstance(explicit_player_key, str) and explicit_player_key.strip():
            player_key = explicit_player_key.strip()
        else:
            linked_aliases = [track_alias_lookup[(project_id, track_id)] for track_id in sorted(candidate_track_ids) if (project_id, track_id) in track_alias_lookup]
            unique_aliases = {alias.player_key: alias for alias in linked_aliases}
            if len(unique_aliases) == 1:
                player_key = next(iter(unique_aliases))
            elif len(unique_aliases) > 1:
                player_key = "UNKNOWN"
                alias_keys = ", ".join(sorted(unique_aliases))
                warning_messages.append(
                    f"Decision event {event.attempt_id} matched multiple aliases ({alias_keys}); assigned to UNKNOWN instead of guessing identity."
                )
            else:
                player_key = "UNKNOWN"
                if project_has_aliases.get(project_id):
                    warning_messages.append(
                        f"Decision event {event.attempt_id} could not be linked to an alias from available track trace."
                    )
                else:
                    warning_messages.append(
                        f"Project {project_id} has no player aliases; assigned decision event {event.attempt_id} to UNKNOWN."
                    )

        group_key = (project_id, player_key)
        grouped.setdefault(group_key, []).append(row)
        event_track_ids.setdefault(group_key, set()).update(candidate_track_ids)
        link_warnings.setdefault(group_key, []).extend(warning_messages)

    summaries: list[PlayerValueSummary] = []
    for (project_id, player_key), rows in sorted(grouped.items()):
        directory = project_dirs.get(project_id)
        events = [DecisionEvent.model_validate(row) for row in rows]
        alias = alias_by_project_key.get((project_id, player_key))
        trace_track_ids = set(event_track_ids.get((project_id, player_key), set()))
        alias_track_ids = set(alias.track_ids) if alias is not None else set()
        summary_track_ids = sorted(alias_track_ids | trace_track_ids)
        warnings = list(dict.fromkeys(link_warnings.get((project_id, player_key), [])))

        raw_scores = [float(event.raw_score) for event in events]
        role_scores = [float(event.role_adjusted_score) for event in events]
        opportunity_costs = [float(event.opportunity_cost) for event in events if event.opportunity_cost is not None]
        avg_role_adjusted = _average(role_scores)
        consistency_score = _clip_score(100.0 - _population_stddev(role_scores))
        if len(role_scores) < 4:
            improvement_score = 50.0
            warnings.append("Improvement score fell back to 50 because fewer than 4 decision events were available.")
        else:
            midpoint = len(role_scores) // 2
            first_half = sum(role_scores[:midpoint]) / len(role_scores[:midpoint])
            second_half = sum(role_scores[midpoint:]) / len(role_scores[midpoint:])
            improvement_score = _clip_score(50.0 + ((second_half - first_half) / 2.0))

        tracking = tracking_by_project.get(project_id)
        if tracking is None:
            participation_score = 50.0
            warnings.append("Participation score fell back to 50 because no tracking artifact was available.")
        else:
            point_counts = [len(track.points) for track in tracking.tracks]
            track_points = {track.track_id: len(track.points) for track in tracking.tracks}
            player_point_count = sum(track_points.get(track_id, 0) for track_id in summary_track_ids)
            if not point_counts or player_point_count == 0:
                participation_score = 50.0
                warnings.append("Participation score fell back to 50 because aliased tracks had no tracked points.")
            else:
                participation_score = _clip_score(100.0 * sum(1 for count in point_counts if count <= player_point_count) / len(point_counts))

        recognition = recognition_by_project.get(project_id)
        review_patch = review_by_project.get(project_id, TrackReviewPatch())
        if not summary_track_ids or recognition is None:
            recognition_reliability_score = 50.0
            warnings.append("Recognition reliability fell back to 50 because no alias track recognition score was available.")
        else:
            risk_by_track = {score.track_id: score.false_positive_risk for score in recognition.track_scores}
            per_track_scores: list[float] = []
            for track_id in summary_track_ids:
                score = 100.0
                if track_id in review_patch.excluded_track_ids:
                    score -= 50.0
                risk = risk_by_track.get(track_id)
                if risk is None:
                    score -= 10.0
                elif risk >= 0.7:
                    score -= 30.0
                elif risk >= 0.4:
                    score -= 15.0
                per_track_scores.append(_clip_score(score))
            recognition_reliability_score = _average(per_track_scores)

        components = [
            _component("avg_role_adjusted_score", avg_role_adjusted, 0.45, "Average Decision Engine role-adjusted score for linked events."),
            _component("consistency_score", consistency_score, 0.20, "100 minus population standard deviation of role-adjusted scores, clipped to 0..100."),
            _component("recognition_reliability_score", recognition_reliability_score, 0.15, "Alias track reliability from local recognition/tracking review risk signals."),
            _component("improvement_score", improvement_score, 0.10, "Second-half versus first-half role-adjusted decision score trend; falls back to 50 if sparse."),
            _component("participation_score", participation_score, 0.10, "Aliased track point-count percentile within the local project; falls back to 50 if tracking is missing."),
        ]
        player_value_score = round(sum(component.contribution for component in components), 4)

        confidence = 0.0
        confidence += min(len(events) / 5.0, 1.0) * 0.4
        confidence += (0.0 if player_key == "UNKNOWN" else 0.3)
        confidence += (0.2 if recognition is not None else 0.0)
        confidence += (0.1 if len(events) >= 5 and player_key != "UNKNOWN" else 0.0)
        if len(events) < 5:
            warnings.append("Confidence is reduced because fewer than 5 decision events were linked.")
        if player_key == "UNKNOWN":
            warnings.append("Identity is UNKNOWN; no real or inferred player name is claimed.")
        confidence = round(min(1.0, max(0.0, confidence)), 4)

        source_ids = [source_ids_by_project[project_id]] if project_id in source_ids_by_project else []
        summaries.append(
            PlayerValueSummary(
                project_id=project_id,
                player_key=player_key,
                display_name=alias.display_name if alias is not None else None,
                team_side=alias.team_side if alias is not None else "UNKNOWN",
                role_hint=alias.role_hint if alias is not None else None,
                track_ids=summary_track_ids,
                decision_event_count=len(events),
                avg_raw_decision_score=_average(raw_scores),
                avg_role_adjusted_score=avg_role_adjusted,
                avg_opportunity_cost=_avg_or_none(opportunity_costs),
                correct_rate=_average([1 if event.is_correct else 0 for event in events]),
                timeout_rate=_average([1 if event.timed_out else 0 for event in events]),
                recognition_reliability_score=recognition_reliability_score,
                consistency_score=consistency_score,
                improvement_score=improvement_score,
                participation_score=participation_score,
                player_value_score=player_value_score,
                components=components,
                confidence=confidence,
                warnings=list(dict.fromkeys(warnings)),
                trace=PlayerValueTrace(
                    project_ids=[project_id],
                    track_ids=summary_track_ids,
                    decision_event_ids=[f"{event.project_id}:{event.prompt_id}:{event.attempt_id}" for event in events],
                    prompt_ids=sorted({event.prompt_id for event in events}),
                    source_ids=source_ids,
                ),
                created_at=generated_at,
            )
        )

    response = PlayerValueBuildResponse(summaries=summaries, generated_at=generated_at, warnings=list(dict.fromkeys(global_warnings)))
    write_json_model(_player_value_summary_path(), response)
    return response


def _decision_event_id(project_id: str, prompt_id: str, attempt_id: str) -> str:
    return f"{project_id}:{prompt_id}:{attempt_id}"


def _parse_decision_event_id(decision_event_id: str) -> tuple[str, str, str] | None:
    parts = decision_event_id.split(":", 2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        return None
    return parts[0], parts[1], parts[2]


def _prompt_option_label(prompt: dict[str, Any] | None, option_id: str | None) -> str | None:
    if not prompt or not option_id or not isinstance(prompt.get("options"), list):
        return None
    for option in prompt["options"]:
        if isinstance(option, dict) and option.get("option_id") == option_id:
            label = option.get("label")
            return str(label) if label is not None else None
    return None


def _aliases_for_project(project_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    project_dir = DATA_DIR / project_id
    alias_by_key: dict[str, Any] = {}
    alias_by_track: dict[str, Any] = {}
    alias_path = project_dir / "player_aliases.json"
    if not alias_path.exists():
        return alias_by_key, alias_by_track
    try:
        aliases = PlayerAliasListResponse.model_validate(read_json(alias_path))
    except (json.JSONDecodeError, ValidationError):
        return alias_by_key, alias_by_track
    for alias in aliases.aliases:
        alias_by_key[alias.player_key] = alias
        for track_id in alias.track_ids:
            alias_by_track[track_id] = alias
    return alias_by_key, alias_by_track


def _breakdown_item(name: str | None, rows: list[DecisionEvent], *, role: bool) -> RoleBreakdownItem | SituationBreakdownItem:
    opportunity_costs = [float(event.opportunity_cost) for event in rows if event.opportunity_cost is not None]
    payload = {
        "event_count": len(rows),
        "avg_role_adjusted_score": _average([float(event.role_adjusted_score) for event in rows]),
        "avg_opportunity_cost": _avg_or_none(opportunity_costs),
        "correct_rate": _average([1 if event.is_correct else 0 for event in rows]),
        "timeout_rate": _average([1 if event.timed_out else 0 for event in rows]),
    }
    if role:
        return RoleBreakdownItem(court_role=name, **payload)
    return SituationBreakdownItem(situation_type=name, **payload)


def _role_breakdown(events: list[DecisionEvent]) -> list[RoleBreakdownItem]:
    grouped: dict[str | None, list[DecisionEvent]] = {}
    for event in events:
        grouped.setdefault(str(event.court_role_target) if event.court_role_target is not None else None, []).append(event)
    return [_breakdown_item(role, rows, role=True) for role, rows in sorted(grouped.items(), key=lambda item: item[0] or "")]


def _situation_breakdown(events: list[DecisionEvent]) -> list[SituationBreakdownItem]:
    grouped: dict[str | None, list[DecisionEvent]] = {}
    for event in events:
        grouped.setdefault(str(event.situation_type) if event.situation_type is not None else None, []).append(event)
    return [_breakdown_item(situation, rows, role=False) for situation, rows in sorted(grouped.items(), key=lambda item: item[0] or "")]


def build_player_value_evidence(project_id: str, player_key: str) -> PlayerValueEvidenceResponse:
    path = _player_value_summary_path()
    if not path.exists():
        raise api_error(
            404,
            "PLAYER_VALUE_SUMMARY_NOT_FOUND",
            "Player Value summary was not found for this player.",
            {"project_id": project_id, "player_key": player_key, "path": str(path)},
            "Run POST /api/local-lab/player-value/build first.",
        )

    summary_response = PlayerValueBuildResponse.model_validate(read_json(path))
    summary = next(
        (item for item in summary_response.summaries if item.project_id == project_id and item.player_key == player_key),
        None,
    )
    if summary is None:
        raise api_error(
            404,
            "PLAYER_VALUE_SUMMARY_NOT_FOUND",
            "Player Value summary was not found for this player.",
            {"project_id": project_id, "player_key": player_key},
            "Run POST /api/local-lab/player-value/build first.",
        )

    event_rows = _read_decision_event_rows(_decision_events_path())
    events_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in event_rows:
        try:
            event = DecisionEvent.model_validate(row)
        except ValidationError:
            continue
        events_by_key[(event.project_id, event.prompt_id, event.attempt_id)] = row

    prompts = _raw_prompts_by_project().get(project_id, {})
    alias_by_key, alias_by_track = _aliases_for_project(project_id)
    summary_alias = alias_by_key.get(player_key)
    evidence_events: list[PlayerValueEvidenceEvent] = []
    decision_events: list[DecisionEvent] = []
    warning_summary: list[str] = list(summary.warnings)

    for trace_id in summary.trace.decision_event_ids:
        parsed = _parse_decision_event_id(trace_id)
        if parsed is None:
            warning_summary.append(f"Trace decision event id {trace_id} is not parseable as project_id:prompt_id:attempt_id.")
            continue
        row = events_by_key.get(parsed)
        if row is None:
            warning_summary.append(f"Trace decision event {trace_id} is missing from player_decision_events.jsonl.")
            continue

        event = DecisionEvent.model_validate(row)
        decision_events.append(event)
        prompt = prompts.get(event.prompt_id)
        event_warnings: list[str] = []
        if prompt is None:
            event_warnings.append("Prompt evidence is missing; question, explanation, and option labels are unavailable.")
        source_track_ids, has_context_only_tracks = _identity_track_ids_from_event_trace(row, event, prompt or {})
        normalized_source_track_ids = sorted(source_track_ids)
        context_track_ids = normalize_track_id_list(event.context_track_ids)
        if not normalized_source_track_ids:
            event_warnings.append("Event has no identity-bearing source_track_ids; attribution may be UNKNOWN.")
        if has_context_only_tracks or (context_track_ids and not normalized_source_track_ids):
            event_warnings.append("context_track_ids are frame context only and were not used as alias evidence.")

        linked_aliases = [alias_by_track[track_id] for track_id in normalized_source_track_ids if track_id in alias_by_track]
        unique_aliases = {alias.player_key: alias for alias in linked_aliases}
        event_alias = None
        if len(unique_aliases) == 1:
            event_alias = next(iter(unique_aliases.values()))
        elif len(unique_aliases) > 1:
            event_warnings.append("source_track_ids match multiple aliases; ambiguous identity falls back to UNKNOWN rather than guessing.")
        elif summary_alias is not None and set(normalized_source_track_ids).intersection(set(summary_alias.track_ids)):
            event_alias = summary_alias

        if summary.confidence < 0.7:
            event_warnings.append("Player Value confidence is low; inspect evidence before using this score.")

        warning_summary.extend(event_warnings)
        evidence_events.append(
            PlayerValueEvidenceEvent(
                decision_event_id=_decision_event_id(event.project_id, event.prompt_id, event.attempt_id),
                project_id=event.project_id,
                prompt_id=event.prompt_id,
                attempt_id=event.attempt_id,
                frame_id=event.frame_id,
                frame_index=event.frame_index,
                user_role=str(event.user_role) if event.user_role is not None else None,
                court_role_target=str(event.court_role_target) if event.court_role_target is not None else None,
                situation_type=str(event.situation_type) if event.situation_type is not None else None,
                question_mode=str(event.question_mode) if event.question_mode is not None else None,
                selected_option_id=event.selected_option_id,
                correct_option_id=event.correct_option_id,
                is_correct=event.is_correct,
                raw_score=float(event.raw_score),
                role_adjusted_score=float(event.role_adjusted_score),
                opportunity_cost=float(event.opportunity_cost) if event.opportunity_cost is not None else None,
                response_time_ms=event.response_time_ms,
                timed_out=event.timed_out,
                source_track_ids=normalized_source_track_ids,
                context_track_ids=context_track_ids,
                prompt_question=str(prompt.get("question")) if prompt and prompt.get("question") is not None else None,
                prompt_explanation=str(prompt.get("explanation")) if prompt and prompt.get("explanation") is not None else None,
                selected_option_label=_prompt_option_label(prompt, event.selected_option_id),
                correct_option_label=_prompt_option_label(prompt, event.correct_option_id),
                alias_player_key=event_alias.player_key if event_alias is not None else None,
                alias_display_name=event_alias.display_name if event_alias is not None else None,
                alias_team_side=str(event_alias.team_side) if event_alias is not None else None,
                evidence_warnings=list(dict.fromkeys(event_warnings)),
            )
        )

    return PlayerValueEvidenceResponse(
        summary=summary,
        events=evidence_events,
        role_breakdown=_role_breakdown(decision_events),
        situation_breakdown=_situation_breakdown(decision_events),
        warning_summary=list(dict.fromkeys(warning_summary)),
        generated_at=utc_now(),
    )


@router.post("/player-value/build", response_model=PlayerValueBuildResponse)
def build_player_value() -> PlayerValueBuildResponse:
    return _build_player_value_response()


@router.get("/player-value/{project_id}/{player_key}/evidence", response_model=PlayerValueEvidenceResponse)
def get_player_value_evidence(project_id: str, player_key: str) -> PlayerValueEvidenceResponse:
    return build_player_value_evidence(project_id, player_key)


@router.get("/player-value", response_model=PlayerValueBuildResponse)
def get_player_value() -> PlayerValueBuildResponse:
    path = _player_value_summary_path()
    if not path.exists():
        raise api_error(
            404,
            "PLAYER_VALUE_NOT_FOUND",
            "Player Value summaries have not been built yet.",
            {"path": str(path)},
            "Run POST /api/local-lab/player-value/build first.",
        )
    return PlayerValueBuildResponse.model_validate(read_json(path))

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


@router.get("/datasets/health", response_model=DatasetHealthResponse)
def get_dataset_health() -> DatasetHealthResponse:
    _ensure_dataset_dirs()
    return dataset_health_response(DATASETS_DIR)


@router.get("/reference-video-summary", response_model=ReferenceVideoDraftSummary)
def get_reference_video_summary() -> ReferenceVideoDraftSummary:
    return reference_video_summary()
