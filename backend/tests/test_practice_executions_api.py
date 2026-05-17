import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_practice_plan(tmp_path: Path) -> str:
    plan_id = "practice-seeded"
    payload = {
        "schema_version": "1.0",
        "plan_id": plan_id,
        "title": "Seeded practice",
        "created_at": "2026-05-17T00:00:00Z",
        "created_by": "Coach",
        "notes": "Do not mutate me.",
        "project_id": "project-1",
        "player_key": "P1",
        "total_duration_minutes": 60,
        "target_roles": ["BALL_HANDLER"],
        "target_situations": ["PICK_AND_ROLL"],
        "player_keys": ["P1"],
        "source_recommendation_ids": ["rec-1"],
        "blocks": [
            {
                "block_id": "warmup-0-8",
                "block_type": "warmup",
                "title": "Warmup",
                "start_minute": 0,
                "end_minute": 8,
                "duration_minutes": 8,
                "target_roles": [],
                "target_situations": [],
                "player_keys": [],
                "coaching_cues": [],
                "success_metrics": ["Warmup complete"],
                "evidence_refs": [],
                "warnings": [],
            },
            {
                "block_id": "drill-8-35",
                "block_type": "drill",
                "title": "PNR reads",
                "start_minute": 8,
                "end_minute": 35,
                "duration_minutes": 27,
                "drill_id": "pnr-read",
                "recommendation_id": "rec-1",
                "target_roles": ["BALL_HANDLER"],
                "target_situations": ["PICK_AND_ROLL"],
                "player_keys": ["P1"],
                "coaching_cues": ["Read the tag"],
                "success_metrics": ["Hit roller on time", "Reject poor angle"],
                "evidence_refs": [],
                "warnings": [],
            },
        ],
        "warnings": [],
        "evidence_refs": [],
        "markdown": "# Seeded practice\n",
        "json_path": str(tmp_path / "practice_plans" / f"{plan_id}.json"),
        "markdown_path": str(tmp_path / "practice_plans" / f"{plan_id}.md"),
    }
    _write_json(tmp_path / "practice_plans" / f"{plan_id}.json", payload)
    return plan_id


def test_create_update_and_summarize_practice_execution(client: TestClient, tmp_path: Path) -> None:
    plan_id = _seed_practice_plan(tmp_path)

    create_response = client.post("/api/practice-executions", json={"plan_id": plan_id, "started_by": "Coach A", "notes": "After school"})

    assert create_response.status_code == 200
    execution = create_response.json()
    assert execution["execution_id"].startswith("execution-")
    assert execution["plan_id"] == plan_id
    assert len(execution["blocks"]) == 2
    assert execution["blocks"][1]["status"] == "PLANNED"
    assert execution["blocks"][1]["metric_results"][0]["metric"] == "Hit roller on time"

    execution["blocks"][0]["status"] = "COMPLETED"
    execution["blocks"][0]["outcome_rating"] = 5
    execution["blocks"][0]["actual_duration_minutes"] = 8
    execution["blocks"][0]["metric_results"][0]["met"] = True
    execution["blocks"][1]["status"] = "MODIFIED"
    execution["blocks"][1]["coach_notes"] = "Alias attribution looked off for P1."
    execution["blocks"][1]["player_notes"] = "Need one more rep."
    execution["blocks"][1]["outcome_rating"] = 2
    execution["blocks"][1]["actual_duration_minutes"] = 35
    execution["blocks"][1]["metric_results"][0]["met"] = True
    execution["blocks"][1]["metric_results"][1]["met"] = False
    execution["blocks"][1]["modified_notes"] = "Used smaller groups."

    update_response = client.put(f"/api/practice-executions/{execution['execution_id']}", json={"blocks": execution["blocks"], "notes": "Updated notes"})

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["notes"] == "Updated notes"
    assert updated["blocks"][1]["status"] == "MODIFIED"
    assert updated["blocks"][1]["planned_duration_minutes"] == 27

    plan_response = client.get(f"/api/practice-plans/{plan_id}")
    assert plan_response.status_code == 200
    assert plan_response.json()["blocks"][1]["title"] == "PNR reads"
    assert "status" not in plan_response.json()["blocks"][1]

    summary_response = client.get(f"/api/practice-executions/{execution['execution_id']}/feedback-summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["completion_rate"] == 0.5
    assert summary["average_block_rating"] == 3.5
    assert summary["modified_count"] == 1
    assert summary["met_metrics"] == ["Warmup complete", "Hit roller on time"]
    assert summary["missed_metrics"] == ["Reject poor angle"]
    assert {signal["signal_type"] for signal in summary["signals"]} >= {"SIMPLIFY_DRILL", "SHORTEN_PLAN", "REVIEW_ALIAS_ATTRIBUTION"}

    list_response = client.get("/api/practice-executions")
    assert list_response.status_code == 200
    assert list_response.json()["executions"][0]["completion_rate"] == 0.5

    signals_response = client.get("/api/practice-executions/signals")
    assert signals_response.status_code == 200
    assert any(signal["signal_type"] == "REVIEW_ALIAS_ATTRIBUTION" for signal in signals_response.json()["signals"])


def test_create_execution_requires_existing_plan(client: TestClient) -> None:
    response = client.post("/api/practice-executions", json={"plan_id": "practice-missing"})

    assert response.status_code == 404
    assert response.json()["code"] == "PRACTICE_PLAN_NOT_FOUND"
