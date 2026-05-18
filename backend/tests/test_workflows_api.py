import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_create_workflow_from_template_checks_prerequisites(client: TestClient, tmp_path: Path) -> None:
    project_dir = tmp_path / "project-1"
    _write_json(project_dir / "project.json", {"project_id": "project-1", "name": "Project"})
    _write_json(project_dir / "tracks.json", {"tracks": []})
    _write_json(project_dir / "tracking_review_patch.json", {"excluded_track_ids": []})
    _write_json(project_dir / "player_aliases.json", {"project_id": "project-1", "aliases": [{"player_key": "P1"}]})
    events_path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(json.dumps({"event_id": "e1"}) + "\n", encoding="utf-8")

    response = client.post("/api/workflows", json={"template_key": "BUILD_PLAYER_VALUE", "project_id": "project-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["template_key"] == "BUILD_PLAYER_VALUE"
    assert payload["steps"][0]["status"] == "COMPLETED"
    assert payload["steps"][-1]["status"] == "READY"
    assert any(item["key"] == "has_player_value" and item["satisfied"] is False for item in payload["prerequisites"])
    assert (tmp_path / "workflows" / f"{payload['workflow_id']}.json").exists()


def test_workflow_from_dashboard_action_and_refresh(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/workflows/from-action", json={"action_id": "build-drill-recommendations"})
    assert response.status_code == 200
    workflow = response.json()
    assert workflow["template_key"] == "TRAINING_RECOMMENDATION"
    assert workflow["source_action_id"] == "build-drill-recommendations"

    _write_json(tmp_path / "datasets" / "player_value" / "player_value_summary.json", {"summaries": [{"project_id": "p", "player_key": "P1"}]})
    refreshed = client.put(f"/api/workflows/{workflow['workflow_id']}/refresh")

    assert refreshed.status_code == 200
    steps = {step["step_id"]: step for step in refreshed.json()["steps"]}
    assert steps["confirm-player-value"]["status"] == "COMPLETED"
    assert steps["build-drills"]["status"] == "READY"


def test_update_workflow_step_is_manual_only(client: TestClient, tmp_path: Path) -> None:
    workflow = client.post("/api/workflows", json={"template_key": "MODEL_GOVERNANCE"}).json()

    response = client.put(f"/api/workflows/{workflow['workflow_id']}/steps/review-queue", json={"status": "SKIPPED", "note": "No review items for this demo."})

    assert response.status_code == 200
    payload = response.json()
    step = next(item for item in payload["steps"] if item["step_id"] == "review-queue")
    assert step["status"] == "SKIPPED"
    assert step["notes"] == ["No review items for this demo."]
    assert not (tmp_path / "models" / "recognition" / "model_registry.json").exists()
