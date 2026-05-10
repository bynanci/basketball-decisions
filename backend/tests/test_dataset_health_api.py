import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _write_manifest(path: Path, dataset_type: str, **overrides) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_type": dataset_type,
        "schema_version": "1.0",
        "sample_count": 0,
        "label_count": 0,
        "project_count": 0,
        "included_project_count": 0,
        "skipped_project_count": 0,
        "skipped_projects": [],
        "exported_at": "2026-01-01T00:00:00Z",
        "storage_paths": {},
        "positive_sample_count": 0,
        "negative_sample_count": 0,
        "positive_negative_ratio": None,
        "source_project_ids": [],
        "skipped_project_ids": [],
        "label_distribution": {},
        "source_license_distribution": {},
        "usage_scope_distribution": {},
        "created_at": "2026-01-01T00:00:00Z",
        "notes": None,
        **overrides,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_empty_datasets_produce_high_warnings(client: TestClient) -> None:
    response = client.get("/api/local-lab/datasets/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["recognition"]["sample_count"] == 0
    assert payload["decision"]["prompt_count"] == 0
    recognition_warnings = {warning["code"]: warning for warning in payload["recognition"]["warnings"]}
    decision_warnings = {warning["code"]: warning for warning in payload["decision"]["warnings"]}
    assert recognition_warnings["RECOGNITION_MINIMUM_SAMPLES"]["severity"] == "HIGH"
    assert recognition_warnings["RECOGNITION_FALSE_POSITIVE_LABELS_MISSING"]["severity"] == "HIGH"
    assert decision_warnings["DECISION_MINIMUM_PROMPTS"]["severity"] == "HIGH"
    assert decision_warnings["DECISION_MINIMUM_ATTEMPTS"]["severity"] == "HIGH"


def test_imbalanced_recognition_labels_produce_imbalance_warning(client: TestClient, tmp_path: Path) -> None:
    recognition_dir = tmp_path / "datasets" / "recognition"
    samples = [{"sample_id": f"s-{index}", "project_id": "p1", "sample_type": "track"} for index in range(12)]
    labels = [
        {"sample_id": f"pos-{index}", "project_id": "p1", "label": "VALID_PLAYER_TRACK"}
        for index in range(11)
    ] + [{"sample_id": "neg-1", "project_id": "p1", "label": "FALSE_POSITIVE"}]
    _write_jsonl(recognition_dir / "curated_samples.jsonl", samples)
    _write_jsonl(recognition_dir / "curated_labels.jsonl", labels)
    _write_manifest(recognition_dir / "dataset_manifest.json", "recognition", source_project_ids=["p1"])

    response = client.get("/api/local-lab/datasets/health")

    assert response.status_code == 200
    warnings = {warning["code"]: warning for warning in response.json()["recognition"]["warnings"]}
    assert warnings["RECOGNITION_NEGATIVE_COVERAGE"]["severity"] == "MEDIUM"
    assert warnings["RECOGNITION_POSITIVE_NEGATIVE_IMBALANCE"]["severity"] == "MEDIUM"
    assert response.json()["recognition"]["positive_negative_ratio"] == 11


def test_decision_dataset_with_insufficient_prompts_produces_prompt_warning(client: TestClient, tmp_path: Path) -> None:
    decision_dir = tmp_path / "datasets" / "decision"
    _write_jsonl(
        decision_dir / "curated_samples.jsonl",
        [
            {
                "sample_id": "s-1",
                "project_id": "p1",
                "sample_type": "option",
                "trace": {"prompt_id": "prompt-1"},
                "payload": {
                    "prompt": {"prompt_id": "prompt-1", "court_role_target": "BALL_HANDLER", "situation_type": "PICK_AND_ROLL"},
                    "option": {"option_id": "a", "expected_value": 1.0},
                },
            }
        ],
    )
    _write_jsonl(decision_dir / "curated_labels.jsonl", [{"sample_id": "s-1", "project_id": "p1", "label": "GOOD_DECISION"}])

    response = client.get("/api/local-lab/datasets/health")

    assert response.status_code == 200
    decision = response.json()["decision"]
    warnings = {warning["code"]: warning for warning in decision["warnings"]}
    assert decision["prompt_count"] == 1
    assert warnings["DECISION_MINIMUM_PROMPTS"]["severity"] == "HIGH"


def test_missing_expected_values_produce_warning(client: TestClient, tmp_path: Path) -> None:
    decision_dir = tmp_path / "datasets" / "decision"
    samples = []
    labels = []
    for index in range(4):
        samples.append(
            {
                "sample_id": f"s-{index}",
                "project_id": "p1",
                "sample_type": "option",
                "trace": {"prompt_id": f"prompt-{index}"},
                "payload": {
                    "prompt": {"prompt_id": f"prompt-{index}", "court_role_target": "BALL_HANDLER", "situation_type": "PICK_AND_ROLL"},
                    "option": {"option_id": f"o-{index}", "expected_value": None},
                },
            }
        )
        labels.append({"sample_id": f"s-{index}", "project_id": "p1", "label": "BAD_DECISION"})
    _write_jsonl(decision_dir / "curated_samples.jsonl", samples)
    _write_jsonl(decision_dir / "curated_labels.jsonl", labels)

    response = client.get("/api/local-lab/datasets/health")

    assert response.status_code == 200
    decision = response.json()["decision"]
    warnings = {warning["code"]: warning for warning in decision["warnings"]}
    assert decision["missing_expected_value_rate"] == 1
    assert warnings["DECISION_EXPECTED_VALUES_MISSING"]["severity"] == "MEDIUM"
