import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_drill_catalog_lists_human_authored_drills(client: TestClient) -> None:
    response = client.get("/api/drills/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["drills"]) >= 3
    assert payload["drills"][0]["coaching_cues"]
    assert "generated_at" in payload


def test_build_drill_recommendations_from_local_artifacts(client: TestClient, tmp_path: Path) -> None:
    _write_json(
        tmp_path / "datasets" / "decision" / "decision_diagnostics.json",
        {
            "prompt_diagnostics": [
                {
                    "prompt_id": "prompt-1",
                    "project_id": "project-1",
                    "court_role_target": "BALL_HANDLER",
                    "situation_type": "PICK_AND_ROLL",
                    "correct_rate": 0.25,
                    "avg_opportunity_cost": 18,
                    "timeout_rate": 0.35,
                    "difficulty": "TOO_HARD",
                }
            ],
            "role_diagnostics": [],
            "global_summary": {},
        },
    )
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_summary.json",
        {
            "summaries": [
                {
                    "project_id": "project-1",
                    "player_key": "P1",
                    "display_name": "Local P1",
                    "role_hint": "BALL_HANDLER",
                    "avg_role_adjusted_score": 55,
                    "correct_rate": 0.4,
                    "timeout_rate": 0.2,
                }
            ]
        },
    )
    _write_json(
        tmp_path / "review_queue" / "review_queue.json",
        [
            {
                "item_id": "rq-1",
                "item_type": "DECISION_PROMPT",
                "priority": "HIGH",
                "project_id": "project-1",
                "prompt_id": "prompt-1",
                "reason": "Pick and roll answer pattern needs review.",
                "recommended_action": "Review prompt labels.",
                "status": "OPEN",
            }
        ],
    )
    (tmp_path / "datasets" / "player_value").mkdir(parents=True, exist_ok=True)
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text(
        json.dumps(
            {
                "decision_event_id": "event-1",
                "project_id": "project-1",
                "prompt_id": "prompt-1",
                "attempt_id": "attempt-1",
                "court_role_target": "BALL_HANDLER",
                "situation_type": "PICK_AND_ROLL",
                "is_correct": False,
                "role_adjusted_score": 30,
                "timed_out": True,
                "alias_player_key": "P1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_build_index.json",
        {"builds": []},
    )

    response = client.post("/api/drills/recommendations", json={"project_id": "project-1", "player_key": "P1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    first = payload["recommendations"][0]
    assert first["priority"] in {"HIGH", "MEDIUM"}
    assert first["coaching_cues"]
    assert first["success_metrics"]
    assert {ref["source"] for ref in first["evidence_refs"]} & {"DECISION_DIAGNOSTICS", "PLAYER_VALUE", "TEACHING_CASE", "REVIEW_QUEUE"}

    latest_response = client.get("/api/drills/recommendations/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["generated_at"] == payload["generated_at"]


def test_drill_recommendations_include_player_value_trend_evidence(client: TestClient, tmp_path: Path) -> None:
    player_value_dir = tmp_path / "datasets" / "player_value"
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"prompt_diagnostics": [], "role_diagnostics": []})
    _write_json(player_value_dir / "player_value_summary.json", {"summaries": []})
    _write_json(tmp_path / "review_queue" / "review_queue.json", [])
    (player_value_dir / "player_decision_events.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (player_value_dir / "player_decision_events.jsonl").write_text("", encoding="utf-8")
    _write_json(
        player_value_dir / "player_value_build_index.json",
        {
            "builds": [
                {"build_id": "build-old", "generated_at": "2026-01-01T00:00:00Z"},
                {"build_id": "build-new", "generated_at": "2026-01-02T00:00:00Z"},
            ]
        },
    )
    _write_json(
        player_value_dir / "builds" / "build-old.json",
        {"build": {"summaries": [{"project_id": "project-1", "player_key": "P1", "role_hint": "BALL_HANDLER", "player_value_score": 80}]}},
    )
    _write_json(
        player_value_dir / "builds" / "build-new.json",
        {"build": {"summaries": [{"project_id": "project-1", "player_key": "P1", "role_hint": "BALL_HANDLER", "player_value_score": 68}]}},
    )

    response = client.post("/api/drills/recommendations", json={"project_id": "project-1", "player_key": "P1"})

    assert response.status_code == 200
    refs = [ref for rec in response.json()["recommendations"] for ref in rec["evidence_refs"]]
    assert any(ref["source"] == "PLAYER_VALUE_TRENDS" and ref["ref_id"] == "build-new" for ref in refs)


def test_latest_drill_recommendations_returns_typed_error_before_build(client: TestClient) -> None:
    response = client.get("/api/drills/recommendations/latest")

    assert response.status_code == 404
    assert response.json()["code"] == "DRILL_RECOMMENDATIONS_NOT_FOUND"


def test_drill_recommendations_apply_practice_feedback_adjustments(client: TestClient, tmp_path: Path) -> None:
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"prompt_diagnostics": [], "role_diagnostics": []})
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_summary.json",
        {
            "summaries": [
                {
                    "project_id": "project-1",
                    "player_key": "P1",
                    "role_hint": "BALL_HANDLER",
                    "avg_role_adjusted_score": 55,
                    "correct_rate": 0.4,
                    "timeout_rate": 0.2,
                }
            ]
        },
    )
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_build_index.json", {"builds": []})
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text("", encoding="utf-8")
    _write_json(tmp_path / "review_queue" / "review_queue.json", [])
    signals_path = tmp_path / "practice_executions" / "practice_feedback_signals.jsonl"
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    signals_path.write_text(
        json.dumps(
            {
                "signal_id": "signal-repeat-1",
                "signal_type": "REPEAT_DRILL",
                "execution_id": "execution-1",
                "block_id": "block-1",
                "drill_id": "advantage-read-kickout",
                "recommendation_id": None,
                "project_id": "project-1",
                "player_key": "P1",
                "reason": "Advantage read was skipped in practice.",
                "severity": "action",
                "created_at": "2026-05-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    response = client.post(
        "/api/drills/recommendations",
        json={"project_id": "project-1", "player_key": "P1", "include_practice_feedback": True, "feedback_lookback_limit": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["feedback_signal_count"] == 1
    adjusted = [rec for rec in payload["recommendations"] if rec["feedback_adjusted"]]
    assert adjusted
    assert adjusted[0]["feedback_signal_ids"] == ["signal-repeat-1"]
    assert adjusted[0]["adjustments"][0]["adjustment_type"] == "PRIORITY_UP"
    assert "repeat" in adjusted[0]["adjustment_summary"][0].lower()


def test_drills_feedback_signals_endpoint_reads_jsonl(client: TestClient, tmp_path: Path) -> None:
    signals_path = tmp_path / "practice_executions" / "practice_feedback_signals.jsonl"
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    signals_path.write_text(
        json.dumps(
            {
                "signal_id": "signal-progress-1",
                "signal_type": "PROGRESS_DRILL",
                "execution_id": "execution-1",
                "drill_id": "spacing-drift-lift",
                "reason": "Spacing drill was completed with met metrics.",
                "severity": "info",
                "created_at": "2026-05-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    response = client.get("/api/drills/feedback-signals")

    assert response.status_code == 200
    assert response.json()["signals"][0]["signal_id"] == "signal-progress-1"
