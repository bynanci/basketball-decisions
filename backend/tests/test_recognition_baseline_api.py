import builtins
import json
import pickle
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import CuratedTrainingSample, Detection, DetectionBox, PlayerTrack, Project, RunTrackingRequest, RunTrackingResponse, TrackPoint
from app.models.base import utc_now


class FakeRandomForestClassifier:
    def __init__(self, *args, **kwargs):
        self.classes_ = [0, 1]
        self.feature_importances_ = [1 / 22] * 22


class FakeSimpleImputer:
    def __init__(self, *args, **kwargs):
        pass


class FakePipeline:
    def __init__(self, steps):
        self.steps = steps
        self.named_steps = dict(steps)
        self.classes_ = [0, 1]

    def fit(self, rows, labels):
        return self

    def predict(self, rows):
        return [1 if (row[1] or 0) > 0 and (row[-3] or 0) < 0.5 else 0 for row in rows]

    def predict_proba(self, rows):
        probabilities = []
        for row in rows:
            risk = 0.8 if (row[1] or 0) > 0 and (row[-3] or 0) < 0.5 else 0.2
            probabilities.append([1 - risk, risk])
        return probabilities


def _write_curated_samples(tmp_path: Path, rows: list[CuratedTrainingSample]) -> None:
    dataset_dir = tmp_path / "datasets" / "recognition"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "curated_samples.jsonl").write_text("".join(row.model_dump_json() + "\n" for row in rows), encoding="utf-8")


def _detection(project_id: str, index: int, label: str) -> CuratedTrainingSample:
    detection_id = f"det-{project_id}-{index}"
    track_id = f"track-{project_id}-{index % 5}"
    detection = Detection(
        detection_id=detection_id,
        frame_id=f"frame-{index}",
        frame_index=index,
        box=DetectionBox(x=10 + index, y=20 + index, width=30, height=60),
        confidence=0.9 if label == "PLAYER" else 0.2,
        track_id=track_id,
    )
    return CuratedTrainingSample(
        sample_id=f"{project_id}:detection:{detection_id}:{label}",
        dataset_type="recognition",
        sample_type="detection",
        project_id=project_id,
        label=label,
        source="TRACKING_REVIEW",
        payload=detection.model_dump(mode="json"),
        trace={"detection_id": detection_id, "track_id": track_id},
        created_at=utc_now(),
    )


def _track(project_id: str, index: int, label: str) -> CuratedTrainingSample:
    track_id = f"track-{project_id}-{index}"
    points = [
        TrackPoint(
            frame_id=f"frame-{frame}",
            frame_index=frame,
            timestamp_seconds=frame / 30,
            image_point_x=100 + frame,
            image_point_y=200 + frame,
            detection_id=f"det-{project_id}-{index}-{frame}",
            confidence=0.9 if label == "VALID_PLAYER_TRACK" else 0.2,
        )
        for frame in range(1, 6 if label == "VALID_PLAYER_TRACK" else 2)
    ]
    track = PlayerTrack(track_id=track_id, points=points)
    return CuratedTrainingSample(
        sample_id=f"{project_id}:track:{track_id}:{label}",
        dataset_type="recognition",
        sample_type="track",
        project_id=project_id,
        label=label,
        source="TRACKING_REVIEW",
        payload=track.model_dump(mode="json"),
        trace={"track_id": track_id},
        created_at=utc_now(),
    )


def _sufficient_rows() -> list[CuratedTrainingSample]:
    rows: list[CuratedTrainingSample] = []
    for project_number in range(5):
        project_id = f"project-{project_number}"
        for index in range(12):
            rows.append(_detection(project_id, index, "PLAYER"))
            rows.append(_track(project_id, index, "VALID_PLAYER_TRACK"))
        for index in range(3):
            rows.append(_detection(project_id, 100 + index, "FALSE_POSITIVE"))
            rows.append(_track(project_id, 100 + index, "FALSE_POSITIVE_TRACK"))
    return rows


def _install_fake_sklearn(monkeypatch) -> None:
    sklearn = types.ModuleType("sklearn")
    ensemble = types.ModuleType("sklearn.ensemble")
    impute = types.ModuleType("sklearn.impute")
    metrics = types.ModuleType("sklearn.metrics")
    model_selection = types.ModuleType("sklearn.model_selection")
    pipeline_module = types.ModuleType("sklearn.pipeline")

    def train_test_split(rows, test_size, random_state, stratify):
        split = max(1, int(len(rows) * (1 - test_size)))
        return rows[:split], rows[split:]

    def _score(y_true, y_pred, **kwargs):
        return 1.0

    def confusion_matrix(y_true, y_pred, labels):
        return [[len(y_true), 0], [0, 0]]

    ensemble.RandomForestClassifier = FakeRandomForestClassifier
    impute.SimpleImputer = FakeSimpleImputer
    metrics.accuracy_score = _score
    metrics.precision_score = _score
    metrics.recall_score = _score
    metrics.f1_score = _score
    metrics.confusion_matrix = confusion_matrix
    model_selection.train_test_split = train_test_split
    pipeline_module.Pipeline = FakePipeline

    for name, module in {
        "sklearn": sklearn,
        "sklearn.ensemble": ensemble,
        "sklearn.impute": impute,
        "sklearn.metrics": metrics,
        "sklearn.model_selection": model_selection,
        "sklearn.pipeline": pipeline_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)


def _block_sklearn_imports(monkeypatch) -> None:
    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "sklearn" or name.startswith("sklearn."):
            raise ImportError("No module named 'sklearn'")
        return real_import(name, *args, **kwargs)

    for module_name in list(sys.modules):
        if module_name == "sklearn" or module_name.startswith("sklearn."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.setattr(builtins, "__import__", blocked_import)


def _write_active_model_with_missing_sklearn_import(tmp_path: Path, monkeypatch) -> None:
    sklearn = types.ModuleType("sklearn")
    pipeline_module = types.ModuleType("sklearn.pipeline")
    MissingModel = type("MissingModel", (), {})
    MissingModel.__module__ = "sklearn.pipeline"
    pipeline_module.MissingModel = MissingModel
    monkeypatch.setitem(sys.modules, "sklearn", sklearn)
    monkeypatch.setitem(sys.modules, "sklearn.pipeline", pipeline_module)

    model_dir = tmp_path / "models" / "recognition" / "v001"
    model_dir.mkdir(parents=True, exist_ok=True)
    with (model_dir / "model.pkl").open("wb") as file:
        pickle.dump(MissingModel(), file)
    (model_dir / "metrics.json").write_text(
        json.dumps(
            {
                "accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "confusion_matrix": [[1, 0], [0, 1]],
                "train_sample_count": 100,
                "test_sample_count": 20,
                "feature_importance": {},
            }
        ),
        encoding="utf-8",
    )
    (model_dir / "feature_schema.json").write_text(json.dumps({"feature_names": []}), encoding="utf-8")
    (tmp_path / "models" / "recognition" / "model_registry.json").write_text(
        json.dumps(
            {
                "active_version": "v001",
                "models": [
                    {
                        "version": "v001",
                        "active": True,
                        "model_path": str(model_dir / "model.pkl"),
                        "metrics_path": str(model_dir / "metrics.json"),
                        "feature_schema_path": str(model_dir / "feature_schema.json"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delitem(sys.modules, "sklearn", raising=False)
    monkeypatch.delitem(sys.modules, "sklearn.pipeline", raising=False)


def _write_tracking_project(tmp_path: Path, project_id: str) -> bytes:
    project_dir = tmp_path / project_id
    write_json_model(project_dir / "project.json", Project(project_id=project_id, name="Score me"))
    tracking = RunTrackingResponse(
        project_id=project_id,
        request=RunTrackingRequest(project_id=project_id),
        detections=[
            Detection(
                detection_id="det-score-1",
                frame_id="frame-1",
                frame_index=1,
                box=DetectionBox(x=1, y=2, width=3, height=4),
                confidence=0.2,
                track_id="track-score-1",
            )
        ],
        tracks=[
            PlayerTrack(
                track_id="track-score-1",
                points=[TrackPoint(frame_id="frame-1", frame_index=1, timestamp_seconds=0.1, image_point_x=2, image_point_y=4, detection_id="det-score-1")],
            )
        ],
    )
    write_json_model(project_dir / "tracking.json", tracking)
    return (project_dir / "tracking.json").read_bytes()


def test_training_fails_cleanly_when_dataset_too_small(client: TestClient, tmp_path: Path) -> None:
    _write_curated_samples(tmp_path, [_detection("small-project", 1, "PLAYER")])

    response = client.post("/api/local-lab/models/recognition/train-baseline")

    assert response.status_code == 400
    assert response.json()["code"] == "RECOGNITION_DATASET_TOO_SMALL"
    assert response.json()["details"]["sample_count"] == 1


def test_training_without_sklearn_returns_dependency_error(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _block_sklearn_imports(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())

    response = client.post("/api/local-lab/models/recognition/train-baseline")

    assert response.status_code == 501
    assert response.json()["code"] == "SCIKIT_LEARN_NOT_INSTALLED"
    assert response.json()["debug_hint"] == "install scikit-learn"


def test_training_writes_registry_and_metrics_when_data_sufficient(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _install_fake_sklearn(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())

    response = client.post("/api/local-lab/models/recognition/train-baseline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v001"
    assert payload["active"] is False
    assert payload["dataset_fingerprint"]
    assert payload["dataset_lineage"]["dataset_fingerprint"] == payload["dataset_fingerprint"]
    assert payload["metrics"]["train_sample_count"] > 0
    assert (tmp_path / "models" / "recognition" / "model_registry.json").exists()
    assert (tmp_path / "models" / "recognition" / "v001" / "model.pkl").exists()
    assert (tmp_path / "models" / "recognition" / "v001" / "dataset_lineage.json").exists()
    assert (tmp_path / "models" / "recognition" / "v001" / "evaluation_report.json").exists()
    assert (tmp_path / "models" / "recognition" / "evaluation_reports.json").exists()
    registry = json.loads((tmp_path / "models" / "recognition" / "model_registry.json").read_text(encoding="utf-8"))
    assert registry["active_version"] is None
    metrics = json.loads((tmp_path / "models" / "recognition" / "v001" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["f1"] == 1.0


def test_registry_read_normalizes_active_flags(client: TestClient, tmp_path: Path) -> None:
    model_root = tmp_path / "models" / "recognition"
    for version in ("v001", "v002"):
        version_dir = model_root / version
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "accuracy": 1.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                    "confusion_matrix": [[1, 0], [0, 1]],
                    "train_sample_count": 100,
                    "test_sample_count": 20,
                    "feature_importance": {},
                }
            ),
            encoding="utf-8",
        )
    (model_root / "model_registry.json").write_text(
        json.dumps(
            {
                "active_version": "v002",
                "models": [
                    {
                        "version": "v001",
                        "active": True,
                        "model_path": str(model_root / "v001" / "model.pkl"),
                        "metrics_path": str(model_root / "v001" / "metrics.json"),
                        "feature_schema_path": str(model_root / "v001" / "feature_schema.json"),
                    },
                    {
                        "version": "v002",
                        "active": False,
                        "model_path": str(model_root / "v002" / "model.pkl"),
                        "metrics_path": str(model_root / "v002" / "metrics.json"),
                        "feature_schema_path": str(model_root / "v002" / "feature_schema.json"),
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/api/local-lab/models/recognition")

    assert response.status_code == 200
    models = {model["version"]: model for model in response.json()["models"]}
    assert models["v001"]["active"] is False
    assert models["v002"]["active"] is True
    assert response.json()["active_model"]["version"] == "v002"


def test_scoring_without_active_model_returns_clear_error(client: TestClient, tmp_path: Path) -> None:
    _write_tracking_project(tmp_path, "score-project")

    response = client.post("/api/local-lab/models/recognition/score-project/score-project")

    assert response.status_code == 404
    assert response.json()["code"] == "NO_ACTIVE_RECOGNITION_MODEL"


def test_model_scoring_missing_sklearn_returns_dependency_error(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _write_tracking_project(tmp_path, "score-project")
    _write_active_model_with_missing_sklearn_import(tmp_path, monkeypatch)

    response = client.post("/api/local-lab/models/recognition/score-project/score-project")

    assert response.status_code == 501
    assert response.json()["code"] == "SCIKIT_LEARN_NOT_INSTALLED"
    assert response.json()["debug_hint"] == "install scikit-learn"


def test_model_scoring_does_not_mutate_project_artifacts(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _install_fake_sklearn(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())
    train_response = client.post("/api/local-lab/models/recognition/train-baseline?activate=true")
    assert train_response.status_code == 200
    before = _write_tracking_project(tmp_path, "score-project")

    response = client.post("/api/local-lab/models/recognition/score-project/score-project")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "v001"
    assert payload["detection_scores"][0]["scoring_source"] == "MODEL"
    after = (tmp_path / "score-project" / "tracking.json").read_bytes()
    assert after == before
    assert not (tmp_path / "score-project" / "tracking_cleaned.json").exists()



def test_training_creates_incrementing_immutable_versions_without_auto_activation(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _install_fake_sklearn(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())

    first = client.post("/api/local-lab/models/recognition/train-baseline")
    second = client.post("/api/local-lab/models/recognition/train-baseline")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["version"] == "v001"
    assert second.json()["version"] == "v002"
    assert first.json()["active"] is False
    assert second.json()["active"] is False
    assert (tmp_path / "models" / "recognition" / "v001" / "model.pkl").exists()
    assert (tmp_path / "models" / "recognition" / "v002" / "model.pkl").exists()
    registry = client.get("/api/local-lab/models/recognition").json()
    assert registry["active_version"] is None
    assert [model["version"] for model in registry["models"]] == ["v001", "v002"]


def test_activation_and_rollback_workflow_controls_active_model(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _install_fake_sklearn(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())
    assert client.post("/api/local-lab/models/recognition/train-baseline?activate=true").status_code == 200
    assert client.post("/api/local-lab/models/recognition/train-baseline").status_code == 200

    registry = client.get("/api/local-lab/models/recognition").json()
    assert registry["active_version"] == "v001"

    activate_v2 = client.post("/api/local-lab/models/recognition/v002/activate", json={"activate": True, "reason": "candidate passed review"})
    assert activate_v2.status_code == 200
    assert activate_v2.json()["previous_active_version"] == "v001"
    assert activate_v2.json()["active_version"] == "v002"

    rollback = client.post("/api/local-lab/models/recognition/v001/activate", json={"activate": True, "reason": "rollback"})
    assert rollback.status_code == 200
    assert rollback.json()["previous_active_version"] == "v002"
    assert rollback.json()["active_version"] == "v001"


def test_model_comparison_and_evaluation_report_registry(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _install_fake_sklearn(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())
    assert client.post("/api/local-lab/models/recognition/train-baseline?activate=true").status_code == 200
    assert client.post("/api/local-lab/models/recognition/train-baseline").status_code == 200

    comparison = client.get("/api/local-lab/models/recognition/compare?base_version=v001&candidate_version=v002")
    assert comparison.status_code == 200
    assert comparison.json()["base_version"] == "v001"
    assert comparison.json()["candidate_version"] == "v002"
    assert "f1" in comparison.json()["metric_deltas"]

    reports = client.get("/api/local-lab/models/recognition/evaluation-reports")
    assert reports.status_code == 200
    assert [report["model_version"] for report in reports.json()["reports"]] == ["v001", "v002"]
    assert all(report["dataset_fingerprint"] for report in reports.json()["reports"])


def test_scoring_uses_active_model_not_latest_model(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    _install_fake_sklearn(monkeypatch)
    _write_curated_samples(tmp_path, _sufficient_rows())
    assert client.post("/api/local-lab/models/recognition/train-baseline?activate=true").status_code == 200
    assert client.post("/api/local-lab/models/recognition/train-baseline").status_code == 200
    _write_tracking_project(tmp_path, "score-project")

    response = client.post("/api/local-lab/models/recognition/score-project/score-project")

    assert response.status_code == 200
    assert response.json()["model_version"] == "v001"
