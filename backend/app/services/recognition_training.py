"""Local recognition baseline feature extraction, training, and model scoring."""

from __future__ import annotations

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
MODEL_VERSION = "v001"
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
    registry.active_model = next((model for model in registry.models if model.version == active_version), None)
    return registry


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def train_baseline(datasets_dir: Path, models_dir: Path) -> RecognitionModelInfo:
    samples = read_curated_recognition_samples(datasets_dir)
    rows = extract_curated_feature_rows(samples)
    validate_training_rows(rows)

    try:
        from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-not-found]
        from sklearn.impute import SimpleImputer  # type: ignore[import-not-found]
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score  # type: ignore[import-not-found]
        from sklearn.pipeline import Pipeline  # type: ignore[import-not-found]
    except ImportError as exc:
        raise api_error(
            501,
            "SCIKIT_LEARN_NOT_INSTALLED",
            "Recognition baseline training requires scikit-learn, which is not installed.",
            {},
            "install scikit-learn",
        ) from exc

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

    version_dir = models_dir / MODEL_VERSION
    version_dir.mkdir(parents=True, exist_ok=True)
    with (version_dir / "model.pkl").open("wb") as file:
        pickle.dump(model, file)
    _write_json(version_dir / "metrics.json", metrics_payload)
    _write_json(
        version_dir / "feature_schema.json",
        {"schema_version": FEATURE_SCHEMA_VERSION, "feature_names": FEATURE_NAMES, "positive_class": 0, "negative_risk_class": 1},
    )

    created_at = utc_now()
    info = RecognitionModelInfo(
        version=MODEL_VERSION,
        active=True,
        created_at=created_at,
        model_path=str(version_dir / "model.pkl"),
        metrics_path=str(version_dir / "metrics.json"),
        feature_schema_path=str(version_dir / "feature_schema.json"),
        metrics=RecognitionModelMetrics.model_validate(metrics_payload),
    )
    registry = _load_registry(models_dir)
    registry.active_version = MODEL_VERSION
    registry.updated_at = created_at
    registry.models = [model for model in registry.models if model.version != MODEL_VERSION]
    registry.models.append(info)
    for model_info in registry.models:
        model_info.active = model_info.version == MODEL_VERSION
    registry.active_model = info
    _write_json(models_dir / "model_registry.json", registry.model_dump(mode="json"))
    return info


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
    with model_path.open("rb") as file:
        return registry.active_version, pickle.load(file)


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
