"""Local recognition baseline feature extraction, training, and model scoring."""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pydantic import TypeAdapter, ValidationError

from app.api.common import api_error
from app.models import (
    Calibration,
    CuratedTrainingSample,
    Detection,
    DetectionBox,
    DetectionRecognitionScore,
    PlayerTrack,
    RecognitionActivationResponse,
    RecognitionDatasetLineage,
    RecognitionEvaluationReport,
    RecognitionEvaluationReportRegistry,
    RecognitionModelComparison,
    RecognitionModelInfo,
    RecognitionModelMetrics,
    RecognitionModelRegistry,
    RecognitionScoreProjectResponse,
    RecognitionScoreSummary,
    RunTrackingResponse,
    TrackRecognitionScore,
)
from app.models.base import utc_now
from app.pipeline.recognition_quality import (
    HIGH_RISK_THRESHOLD,
    _recommended_label,
    extract_detection_features,
    extract_track_features,
)

POSITIVE_LABELS = {"PLAYER", "VALID_PLAYER_TRACK"}
NEGATIVE_LABELS = {"FALSE_POSITIVE", "FALSE_POSITIVE_TRACK"}
FEATURE_SCHEMA_VERSION = "1.0"
TRACK_FEATURES = [
    "point_count",
    "avg_confidence",
    "min_confidence",
    "max_confidence",
    "avg_bbox_area",
    "bbox_area_variance",
    "avg_speed_image",
    "max_jump_distance_image",
    "frame_span",
    "gap_count",
    "projected_inside_court_ratio",
]
DETECTION_FEATURES = [
    "bbox_x",
    "bbox_y",
    "bbox_width",
    "bbox_height",
    "bbox_area",
    "bbox_aspect_ratio",
    "confidence",
    "has_track_id",
    "track_point_count",
]
FEATURE_NAMES = ["is_track", "is_detection", *TRACK_FEATURES, *DETECTION_FEATURES]

_SAMPLES_ADAPTER = TypeAdapter(list[CuratedTrainingSample])


@dataclass(frozen=True)
class FeatureRow:
    sample_id: str
    project_id: str
    sample_type: str
    target_id: str
    label: str
    y: int
    features: dict[str, float | None]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_curated_recognition_samples(datasets_dir: Path) -> list[CuratedTrainingSample]:
    path = datasets_dir / "recognition" / "curated_samples.jsonl"
    try:
        return _SAMPLES_ADAPTER.validate_python(_read_jsonl(path))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise api_error(
            400,
            "CURATED_RECOGNITION_DATASET_INVALID",
            "The curated recognition dataset could not be parsed.",
            {"path": str(path)},
            f"Re-run POST /api/local-lab/datasets/recognition/curate. Parser error: {exc}",
        ) from exc


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty_features(sample_type: str) -> dict[str, float | None]:
    return {
        **{name: None for name in FEATURE_NAMES},
        "is_track": 1.0 if sample_type == "track" else 0.0,
        "is_detection": 1.0 if sample_type == "detection" else 0.0,
    }


def _target_id(sample: CuratedTrainingSample) -> str:
    if sample.sample_type == "track":
        return str(sample.payload.get("track_id") or sample.trace.get("track_id") or sample.sample_id)
    if sample.sample_type == "detection":
        return str(sample.payload.get("detection_id") or sample.trace.get("detection_id") or sample.sample_id)
    return sample.sample_id


def _track_features_from_payload(payload: dict[str, Any], detections_by_id: dict[str, Detection] | None = None) -> dict[str, float | None]:
    track = PlayerTrack.model_validate(payload)
    feature_model = extract_track_features(track, detections_by_id or {}, None)
    data = feature_model.model_dump()
    features = _empty_features("track")
    for name in TRACK_FEATURES:
        features[name] = _float_or_none(data.get(name))
    return features


def _detection_features_from_payload(payload: dict[str, Any], track_point_counts: dict[str, int] | None = None) -> dict[str, float | None]:
    detection = Detection.model_validate(payload)
    feature_model = extract_detection_features(detection, track_point_counts or {}, None)
    data = feature_model.model_dump()
    features = _empty_features("detection")
    for name in DETECTION_FEATURES:
        features[name] = _float_or_none(data.get(name))
    return features


def extract_curated_feature_rows(samples: Iterable[CuratedTrainingSample]) -> list[FeatureRow]:
    sample_list = [sample for sample in samples if sample.label in POSITIVE_LABELS | NEGATIVE_LABELS]
    track_point_counts: dict[tuple[str, str], int] = {}
    detections_by_project: dict[str, dict[str, Detection]] = {}
    for sample in sample_list:
        if sample.sample_type == "track":
            try:
                track = PlayerTrack.model_validate(sample.payload)
            except ValidationError:
                continue
            track_point_counts[(sample.project_id, track.track_id)] = len(track.points)
        elif sample.sample_type == "detection":
            try:
                detection = Detection.model_validate(sample.payload)
            except ValidationError:
                continue
            detections_by_project.setdefault(sample.project_id, {})[detection.detection_id] = detection

    rows: list[FeatureRow] = []
    for sample in sample_list:
        try:
            if sample.sample_type == "track":
                features = _track_features_from_payload(sample.payload, detections_by_project.get(sample.project_id, {}))
            elif sample.sample_type == "detection":
                detection = Detection.model_validate(sample.payload)
                counts = dict(track_point_counts)
                per_project_counts = {track_id: count for (project_id, track_id), count in counts.items() if project_id == sample.project_id}
                features = _detection_features_from_payload(sample.payload, per_project_counts)
                if detection.track_id and (sample.project_id, detection.track_id) in track_point_counts:
                    features["track_point_count"] = float(track_point_counts[(sample.project_id, detection.track_id)])
            else:
                continue
        except ValidationError:
            # Review-only false positives can contain just an ID if the raw track/detection is missing.
            features = _empty_features(sample.sample_type)
        rows.append(
            FeatureRow(
                sample_id=sample.sample_id,
                project_id=sample.project_id,
                sample_type=sample.sample_type,
                target_id=_target_id(sample),
                label=sample.label,
                y=1 if sample.label in NEGATIVE_LABELS else 0,
                features=features,
            )
        )
    return rows


def _matrix(rows: list[FeatureRow]) -> list[list[float | None]]:
    return [[row.features.get(name) for name in FEATURE_NAMES] for row in rows]


def validate_training_rows(rows: list[FeatureRow]) -> None:
    positive = sum(1 for row in rows if row.y == 0)
    negative = sum(1 for row in rows if row.y == 1)
    if len(rows) < 100 or positive < 10 or negative < 10:
        raise api_error(
            400,
            "RECOGNITION_DATASET_TOO_SMALL",
            "Curated recognition dataset is too small for baseline training.",
            {"sample_count": len(rows), "positive_sample_count": positive, "negative_sample_count": negative},
            "Curate at least 100 recognition samples with at least 10 positive and 10 negative labels.",
        )


def _split_rows(rows: list[FeatureRow]) -> tuple[list[FeatureRow], list[FeatureRow]]:
    projects = sorted({row.project_id for row in rows})
    if len(projects) >= 2:
        test_project_count = max(1, round(len(projects) * 0.2))
        test_projects = set(projects[-test_project_count:])
        train = [row for row in rows if row.project_id not in test_projects]
        test = [row for row in rows if row.project_id in test_projects]
        if train and test and {row.y for row in train} == {0, 1} and {row.y for row in test} == {0, 1}:
            return train, test

    # Fallback keeps the endpoint deterministic while sklearn performs a stratified row split.
    from sklearn.model_selection import train_test_split  # type: ignore[import-not-found]

    train, test = train_test_split(rows, test_size=0.2, random_state=42, stratify=[row.y for row in rows])
    return list(train), list(test)



def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataset_lineage(datasets_dir: Path) -> RecognitionDatasetLineage:
    recognition_dir = datasets_dir / "recognition"
    manifest_path = recognition_dir / "dataset_manifest.json"
    samples_path = recognition_dir / "curated_samples.jsonl"
    labels_path = recognition_dir / "curated_labels.jsonl"
    manifest_fingerprint = _file_sha256(manifest_path)
    samples_fingerprint = _file_sha256(samples_path)
    labels_fingerprint = _file_sha256(labels_path)
    digest = hashlib.sha256()
    for value in (manifest_fingerprint, samples_fingerprint, labels_fingerprint):
        digest.update((value or "missing").encode("utf-8"))
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    return RecognitionDatasetLineage(
        manifest_path=str(manifest_path),
        samples_path=str(samples_path),
        labels_path=str(labels_path),
        dataset_fingerprint=digest.hexdigest(),
        manifest_fingerprint=manifest_fingerprint,
        samples_fingerprint=samples_fingerprint,
        labels_fingerprint=labels_fingerprint,
        sample_count=int(manifest.get("sample_count") or 0),
        label_count=int(manifest.get("label_count") or 0),
        source_project_ids=list(manifest.get("source_project_ids") or []),
        exported_at=manifest.get("exported_at"),
    )


def _next_model_version(models_dir: Path, registry: RecognitionModelRegistry) -> str:
    versions = {model.version for model in registry.models}
    if models_dir.exists():
        versions.update(path.name for path in models_dir.iterdir() if path.is_dir() and path.name.startswith("v"))
    max_version = 0
    for version in versions:
        if len(version) == 4 and version.startswith("v") and version[1:].isdigit():
            max_version = max(max_version, int(version[1:]))
    return f"v{max_version + 1:03d}"

def _load_registry(models_dir: Path) -> RecognitionModelRegistry:
    path = models_dir / "model_registry.json"
    if not path.exists():
        return RecognitionModelRegistry()
    return RecognitionModelRegistry.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_recognition_registry(models_dir: Path) -> RecognitionModelRegistry:
    registry = _load_registry(models_dir)
    active_version = registry.active_version
    for model in registry.models:
        metrics_path = models_dir / model.version / "metrics.json"
        if metrics_path.exists():
            model.metrics = RecognitionModelMetrics.model_validate(json.loads(metrics_path.read_text(encoding="utf-8")))
        lineage_path = models_dir / model.version / "dataset_lineage.json"
        if lineage_path.exists():
            model.dataset_lineage = RecognitionDatasetLineage.model_validate(json.loads(lineage_path.read_text(encoding="utf-8")))
            model.dataset_fingerprint = model.dataset_lineage.dataset_fingerprint
    for model in registry.models:
        model.active = bool(active_version and model.version == active_version)
    registry.active_model = next((model for model in registry.models if model.version == active_version), None)
    return registry


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _scikit_learn_dependency_error(exc: ImportError) -> None:
    raise api_error(
        501,
        "SCIKIT_LEARN_NOT_INSTALLED",
        "Recognition baseline training and scoring require scikit-learn, which is not installed.",
        {},
        "install scikit-learn",
    ) from exc


def train_baseline(datasets_dir: Path, models_dir: Path, activate: bool = False) -> RecognitionModelInfo:
    samples = read_curated_recognition_samples(datasets_dir)
    rows = extract_curated_feature_rows(samples)
    validate_training_rows(rows)

    try:
        from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-not-found]
        from sklearn.impute import SimpleImputer  # type: ignore[import-not-found]
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score  # type: ignore[import-not-found]
        from sklearn.pipeline import Pipeline  # type: ignore[import-not-found]
    except ImportError as exc:
        _scikit_learn_dependency_error(exc)

    train_rows, test_rows = _split_rows(rows)
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
            ("classifier", RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced", n_jobs=1)),
        ]
    )
    model.fit(_matrix(train_rows), [row.y for row in train_rows])
    predictions = model.predict(_matrix(test_rows))
    y_test = [row.y for row in test_rows]
    classifier = model.named_steps["classifier"]
    feature_importance = None
    if hasattr(classifier, "feature_importances_"):
        feature_importance = {
            name: round(float(value), 6)
            for name, value in sorted(zip(FEATURE_NAMES, classifier.feature_importances_), key=lambda item: item[1], reverse=True)
        }

    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    matrix_payload = matrix.tolist() if hasattr(matrix, "tolist") else matrix
    metrics_payload = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 6),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 6),
        "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 6),
        "confusion_matrix": matrix_payload,
        "train_sample_count": len(train_rows),
        "test_sample_count": len(test_rows),
        "feature_importance": feature_importance,
    }

    registry = _load_registry(models_dir)
    version = _next_model_version(models_dir, registry)
    version_dir = models_dir / version
    if version_dir.exists():
        raise api_error(
            409,
            "RECOGNITION_MODEL_VERSION_EXISTS",
            "The next recognition model version folder already exists.",
            {"version": version, "model_dir": str(version_dir)},
            "Inspect model_registry.json and existing model folders before retrying; model folders are immutable.",
        )
    version_dir.mkdir(parents=True, exist_ok=False)
    with (version_dir / "model.pkl").open("wb") as file:
        pickle.dump(model, file)
    _write_json(version_dir / "metrics.json", metrics_payload)
    _write_json(
        version_dir / "feature_schema.json",
        {"schema_version": FEATURE_SCHEMA_VERSION, "feature_names": FEATURE_NAMES, "positive_class": 0, "negative_risk_class": 1},
    )
    lineage = _dataset_lineage(datasets_dir)
    _write_json(version_dir / "dataset_lineage.json", lineage.model_dump(mode="json"))

    created_at = utc_now()
    metrics = RecognitionModelMetrics.model_validate(metrics_payload)
    report = RecognitionEvaluationReport(
        report_id=f"{version}-evaluation",
        model_version=version,
        created_at=created_at,
        metrics_path=str(version_dir / "metrics.json"),
        report_path=str(version_dir / "evaluation_report.json"),
        dataset_fingerprint=lineage.dataset_fingerprint,
        metrics=metrics,
    )
    _write_json(version_dir / "evaluation_report.json", report.model_dump(mode="json"))
    _register_evaluation_report(models_dir, report)

    info = RecognitionModelInfo(
        version=version,
        active=activate,
        created_at=created_at,
        model_path=str(version_dir / "model.pkl"),
        metrics_path=str(version_dir / "metrics.json"),
        feature_schema_path=str(version_dir / "feature_schema.json"),
        lineage_path=str(version_dir / "dataset_lineage.json"),
        evaluation_report_path=str(version_dir / "evaluation_report.json"),
        dataset_fingerprint=lineage.dataset_fingerprint,
        dataset_lineage=lineage,
        metrics=metrics,
    )
    if activate:
        registry.active_version = version
    registry.updated_at = created_at
    registry.models.append(info)
    for model_info in registry.models:
        model_info.active = bool(registry.active_version and model_info.version == registry.active_version)
    registry.active_model = next((model for model in registry.models if model.version == registry.active_version), None)
    _write_json(models_dir / "model_registry.json", registry.model_dump(mode="json"))
    return info



def load_evaluation_report_registry(models_dir: Path) -> RecognitionEvaluationReportRegistry:
    path = models_dir / "evaluation_reports.json"
    if not path.exists():
        return RecognitionEvaluationReportRegistry()
    return RecognitionEvaluationReportRegistry.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _register_evaluation_report(models_dir: Path, report: RecognitionEvaluationReport) -> None:
    registry = load_evaluation_report_registry(models_dir)
    registry.reports = [existing for existing in registry.reports if existing.report_id != report.report_id]
    registry.reports.append(report)
    registry.updated_at = report.created_at
    _write_json(models_dir / "evaluation_reports.json", registry.model_dump(mode="json"))


def _model_by_version(registry: RecognitionModelRegistry, version: str) -> RecognitionModelInfo:
    model = next((model for model in registry.models if model.version == version), None)
    if model is None:
        raise api_error(
            404,
            "RECOGNITION_MODEL_VERSION_NOT_FOUND",
            "The requested recognition model version is not registered.",
            {"version": version},
            "Choose a version from GET /api/local-lab/models/recognition.",
        )
    return model


def get_model_version(models_dir: Path, version: str) -> RecognitionModelInfo:
    registry = load_recognition_registry(models_dir)
    return _model_by_version(registry, version)


def compare_models(models_dir: Path, base_version: str, candidate_version: str) -> RecognitionModelComparison:
    registry = load_recognition_registry(models_dir)
    base_model = _model_by_version(registry, base_version)
    candidate_model = _model_by_version(registry, candidate_version)
    deltas: dict[str, float] = {}
    if base_model.metrics and candidate_model.metrics:
        for metric in ("accuracy", "precision", "recall", "f1"):
            deltas[metric] = round(float(getattr(candidate_model.metrics, metric)) - float(getattr(base_model.metrics, metric)), 6)
        deltas["train_sample_count"] = float(candidate_model.metrics.train_sample_count - base_model.metrics.train_sample_count)
        deltas["test_sample_count"] = float(candidate_model.metrics.test_sample_count - base_model.metrics.test_sample_count)
    return RecognitionModelComparison(
        base_version=base_version,
        candidate_version=candidate_version,
        base_model=base_model,
        candidate_model=candidate_model,
        metric_deltas=deltas,
    )


def activate_model(models_dir: Path, version: str, reason: str | None = None) -> RecognitionActivationResponse:
    registry = load_recognition_registry(models_dir)
    model = _model_by_version(registry, version)
    model_path = models_dir / version / "model.pkl"
    if not model_path.exists():
        raise api_error(
            404,
            "RECOGNITION_MODEL_FILE_NOT_FOUND",
            "The requested recognition model file is missing.",
            {"version": version, "model_path": str(model_path)},
            "Activate only immutable versions with an existing model.pkl artifact.",
        )
    previous = registry.active_version
    now = utc_now()
    registry.active_version = version
    registry.updated_at = now
    for model_info in registry.models:
        model_info.active = model_info.version == version
    registry.active_model = next((model_info for model_info in registry.models if model_info.version == version), model)
    events_path = models_dir / "model_registry_events.json"
    try:
        events = json.loads(events_path.read_text(encoding="utf-8")) if events_path.exists() else []
    except json.JSONDecodeError:
        events = []
    events.append({
        "event_id": f"recognition-{version}-{now.isoformat()}",
        "model_family": "recognition",
        "event_type": "ACTIVATED",
        "version": version,
        "previous_active_version": previous,
        "reason": reason,
        "created_at": now.isoformat(),
    })
    _write_json(events_path, events)
    _write_json(models_dir / "model_registry.json", registry.model_dump(mode="json"))
    return RecognitionActivationResponse(
        active_version=version,
        previous_active_version=previous,
        activated_version=version,
        updated_at=now,
        reason=reason,
        registry=registry,
    )

def _load_active_model(models_dir: Path) -> tuple[str, Any]:
    registry = _load_registry(models_dir)
    if not registry.active_version:
        raise api_error(
            404,
            "NO_ACTIVE_RECOGNITION_MODEL",
            "No active recognition baseline model is registered.",
            {},
            "Train a baseline with POST /api/local-lab/models/recognition/train-baseline first.",
        )
    model_path = models_dir / registry.active_version / "model.pkl"
    if not model_path.exists():
        raise api_error(
            404,
            "ACTIVE_RECOGNITION_MODEL_NOT_FOUND",
            "The active recognition model file is missing.",
            {"version": registry.active_version, "model_path": str(model_path)},
            "Re-train the recognition baseline to rebuild model.pkl.",
        )
    try:
        with model_path.open("rb") as file:
            return registry.active_version, pickle.load(file)
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("sklearn"):
            _scikit_learn_dependency_error(exc)
        raise


def _risk_scores(model: Any, rows: list[list[float | None]]) -> list[float]:
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(rows)
        classes = list(getattr(model, "classes_", []))
        if not classes and hasattr(model, "named_steps"):
            classes = list(getattr(model.named_steps.get("classifier"), "classes_", []))
        risk_index = classes.index(1) if 1 in classes else min(1, len(probabilities[0]) - 1)
        return [round(float(row[risk_index]), 6) for row in probabilities]
    predictions = model.predict(rows)
    return [float(value) for value in predictions]


def score_project_with_model(project_id: str, tracking: RunTrackingResponse, models_dir: Path, calibration: Calibration | None = None) -> RecognitionScoreProjectResponse:
    version, model = _load_active_model(models_dir)
    detections_by_id = {detection.detection_id: detection for detection in tracking.detections}
    track_point_counts = {track.track_id: len(track.points) for track in tracking.tracks}

    track_rows: list[list[float | None]] = []
    track_features = []
    for track in tracking.tracks:
        features_model = extract_track_features(track, detections_by_id, calibration)
        features = _empty_features("track")
        for name, value in features_model.model_dump().items():
            if name in features:
                features[name] = _float_or_none(value)
        track_features.append(features_model)
        track_rows.append([features.get(name) for name in FEATURE_NAMES])

    detection_rows: list[list[float | None]] = []
    detection_features = []
    for detection in tracking.detections:
        features_model = extract_detection_features(detection, track_point_counts, calibration)
        features = _empty_features("detection")
        for name, value in features_model.model_dump().items():
            if name in features:
                features[name] = _float_or_none(value)
        detection_features.append(features_model)
        detection_rows.append([features.get(name) for name in FEATURE_NAMES])

    track_risks = _risk_scores(model, track_rows) if track_rows else []
    detection_risks = _risk_scores(model, detection_rows) if detection_rows else []

    track_scores = [
        TrackRecognitionScore(
            track_id=track.track_id,
            false_positive_risk=risk,
            recommended_label=_recommended_label(risk),
            reasons=[f"Model baseline {version} estimated false-positive risk."],
            features=features,
            model_version=version,
            scoring_source="MODEL",
        )
        for track, risk, features in zip(tracking.tracks, track_risks, track_features)
    ]
    detection_scores = [
        DetectionRecognitionScore(
            detection_id=detection.detection_id,
            track_id=detection.track_id,
            false_positive_risk=risk,
            recommended_label=_recommended_label(risk),
            reasons=[f"Model baseline {version} estimated false-positive risk."],
            features=features,
            model_version=version,
            scoring_source="MODEL",
        )
        for detection, risk, features in zip(tracking.detections, detection_risks, detection_features)
    ]
    return RecognitionScoreProjectResponse(
        project_id=project_id,
        detection_scores=detection_scores,
        track_scores=track_scores,
        summary=RecognitionScoreSummary(
            high_risk_detection_count=sum(1 for score in detection_scores if score.false_positive_risk >= HIGH_RISK_THRESHOLD),
            high_risk_track_count=sum(1 for score in track_scores if score.false_positive_risk >= HIGH_RISK_THRESHOLD),
            model_version=version,
            scoring_source="MODEL",
        ),
        model_version=version,
        scoring_source="MODEL",
    )
