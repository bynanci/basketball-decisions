import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_recommendation_artifacts(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "datasets" / "decision" / "decision_diagnostics.json",
        {
            "prompt_diagnostics": [
                {
                    "prompt_id": "prompt-1",
                    "project_id": "project-1",
                    "court_role_target": "BALL_HANDLER",
                    "situation_type": "PICK_AND_ROLL",
                    "correct_rate": 0.2,
                    "avg_opportunity_cost": 20,
                    "timeout_rate": 0.4,
                    "difficulty": "TOO_HARD",
                },
                {
                    "prompt_id": "prompt-2",
                    "project_id": "project-1",
                    "court_role_target": "WING",
                    "situation_type": "TRANSITION",
                    "correct_rate": 0.35,
                    "avg_opportunity_cost": 12,
                    "timeout_rate": 0.2,
                    "difficulty": "BALANCED",
                },
            ],
            "role_diagnostics": [],
        },
    )
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_summary.json", {"summaries": [{"project_id": "project-1", "player_key": "P1", "role_hint": "BALL_HANDLER", "avg_role_adjusted_score": 50, "correct_rate": 0.4, "timeout_rate": 0.2}]})
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_build_index.json", {"builds": []})
    _write_json(tmp_path / "review_queue" / "review_queue.json", [])
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text("", encoding="utf-8")


def test_build_practice_plan_creates_timeboxed_exports(client: TestClient, tmp_path: Path) -> None:
    _seed_recommendation_artifacts(tmp_path)

    response = client.post(
        "/api/practice-plans",
        json={"title": "Guard reads", "total_duration_minutes": 75, "project_id": "project-1", "player_key": "P1", "player_keys": ["P2"], "max_drill_blocks": 2, "notes": "Keep groups small."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_id"].startswith("practice-")
    assert payload["total_duration_minutes"] == 75
    assert payload["notes"] == "Keep groups small."
    assert {block["block_type"] for block in payload["blocks"]} == {"warmup", "drill", "scrimmage", "review"}
    drill_blocks = [block for block in payload["blocks"] if block["block_type"] == "drill" and block.get("drill_id")]
    assert drill_blocks
    assert "purpose" in drill_blocks[0]
    assert sum(block["duration_minutes"] for block in payload["blocks"]) == 75
    assert payload["blocks"][0]["start_minute"] == 0
    assert payload["blocks"][-1]["end_minute"] == 75
    drill_blocks = [block for block in payload["blocks"] if block["block_type"] == "drill"]
    assert drill_blocks
    assert drill_blocks[0]["coaching_cues"]
    assert drill_blocks[0]["success_metrics"]
    assert drill_blocks[0]["evidence_refs"]
    assert "P1" in payload["player_keys"]
    assert "P2" in payload["player_keys"]
    assert "No medical or injury advice" in payload["markdown"]
    assert "Keep groups small." in payload["markdown"]

    markdown_response = client.get(f"/api/practice-plans/{payload['plan_id']}/markdown")
    assert markdown_response.status_code == 200
    assert markdown_response.text.startswith("# Guard reads")

    json_response = client.get(f"/api/practice-plans/{payload['plan_id']}/json")
    assert json_response.status_code == 200
    assert json_response.json()["plan_id"] == payload["plan_id"]

    list_response = client.get("/api/practice-plans")
    assert list_response.status_code == 200
    assert list_response.json()["plans"][0]["plan_id"] == payload["plan_id"]


def test_practice_plan_without_recommendations_still_fills_requested_duration(client: TestClient, tmp_path: Path) -> None:
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"prompt_diagnostics": [], "role_diagnostics": []})
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_summary.json", {"summaries": []})
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_build_index.json", {"builds": []})
    _write_json(tmp_path / "review_queue" / "review_queue.json", [])
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text("", encoding="utf-8")

    response = client.post("/api/practice-plans", json={"total_duration_minutes": 60})

    assert response.status_code == 200
    payload = response.json()
    assert sum(block["duration_minutes"] for block in payload["blocks"]) == 60
    assert [block["block_type"] for block in payload["blocks"]] == ["warmup", "drill", "scrimmage", "review"]
    assert payload["blocks"][1]["warnings"]


def test_practice_plan_rejects_unsupported_duration(client: TestClient) -> None:
    response = client.post("/api/practice-plans", json={"total_duration_minutes": 45})

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_missing_practice_plan_returns_typed_error(client: TestClient) -> None:
    response = client.get("/api/practice-plans/practice-missing")

    assert response.status_code == 404
    assert response.json()["code"] == "PRACTICE_PLAN_NOT_FOUND"
