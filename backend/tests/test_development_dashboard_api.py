import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")


def test_development_dashboard_missing_artifacts_warns(client: TestClient) -> None:
    response = client.get("/api/development-dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["warnings"]
    assert payload["next_best_actions"]
    assert payload["team_summary"]["player_count"] == 0
    assert any(action["artifact"] == "player_value_summaries" for action in payload["next_best_actions"])


def test_development_dashboard_aggregates_available_artifacts(client: TestClient, tmp_path: Path) -> None:
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_summary.json",
        {
            "summaries": [
                {
                    "project_id": "project-1",
                    "player_key": "P1",
                    "display_name": "Local P1",
                    "team_side": "HOME",
                    "role_hint": "guard",
                    "track_ids": [],
                    "decision_event_count": 4,
                    "avg_raw_decision_score": 0.6,
                    "avg_role_adjusted_score": 0.7,
                    "correct_rate": 0.5,
                    "timeout_rate": 0.0,
                    "recognition_reliability_score": 0.8,
                    "consistency_score": 0.7,
                    "improvement_score": 0.6,
                    "participation_score": 0.9,
                    "player_value_score": 0.75,
                    "confidence": 0.8,
                    "warnings": [],
                    "trace": {},
                }
            ],
            "warnings": [],
        },
    )
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_trends.json",
        {
            "trends": [
                {
                    "project_id": "project-1",
                    "player_key": "P1",
                    "points": [
                        {"build_id": "b1", "generated_at": "2026-01-01T00:00:00Z", "project_id": "project-1", "player_key": "P1", "player_value_score": 0.5, "confidence": 0.7, "decision_event_count": 2, "player_value_formula_version": "v1", "dataset_fingerprint": "a"},
                        {"build_id": "b2", "generated_at": "2026-01-02T00:00:00Z", "project_id": "project-1", "player_key": "P1", "player_value_score": 0.75, "confidence": 0.8, "decision_event_count": 4, "player_value_formula_version": "v1", "dataset_fingerprint": "b"},
                    ],
                }
            ]
        },
    )
    _write_json(tmp_path / "drills" / "latest_recommendations.json", {"recommendations": [{"recommendation_id": "rec-1"}]})
    _write_json(tmp_path / "practice_plans" / "index.json", {"plans": [{"plan_id": "plan-1", "title": "Plan", "created_at": "2026-01-01T00:00:00Z", "total_duration_minutes": 60, "player_keys": ["P1"], "target_roles": [], "target_situations": [], "warning_count": 0, "json_path": "plan.json", "markdown_path": "plan.md"}]})
    _write_json(tmp_path / "practice_executions" / "index.json", {"executions": [{"execution_id": "exec-1", "plan_id": "plan-1", "plan_title": "Plan", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "planned_duration_minutes": 60, "completion_rate": 0.5, "skipped_count": 1, "modified_count": 0, "json_path": "exec.json"}]})
    (tmp_path / "practice_executions").mkdir(exist_ok=True)
    (tmp_path / "practice_executions" / "practice_feedback_signals.jsonl").write_text(json.dumps({"signal_type": "REPEAT_DRILL", "execution_id": "exec-1", "reason": "Missed metric", "severity": "action"}) + "\n", encoding="utf-8")
    _write_json(tmp_path / "review_queue" / "review_queue.json", [{"item_id": "rq-1", "item_type": "DECISION_PROMPT", "priority": "HIGH", "status": "OPEN", "reason": "Needs review", "recommended_action": "Review"}])
    _write_json(tmp_path / "review_queue" / "review_action_log.json", [])
    _write_json(tmp_path / "datasets" / "recognition" / "dataset_manifest.json", {"dataset_type": "recognition", "sample_count": 10, "label_count": 8})
    _write_json(tmp_path / "datasets" / "decision" / "dataset_manifest.json", {"dataset_type": "decision", "sample_count": 12, "label_count": 11})
    _write_json(tmp_path / "models" / "recognition" / "model_registry.json", {"active_version": "v1", "models": [{"version": "v1", "active": True, "created_at": "2026-01-01T00:00:00Z", "model_path": "model.pkl", "metrics_path": "metrics.json", "feature_schema_path": "schema.json"}]})
    _write_json(tmp_path / "reports" / "coach" / "index.json", {"reports": [{"report_id": "report-1", "title": "Report", "created_at": "2026-01-01T00:00:00Z", "section_names": [], "warning_count": 0, "json_path": "report.json", "markdown_path": "report.md"}]})
    _write_json(tmp_path / "decision_rules" / "active_rule_set.json", {"rule_set_id": "rules", "rules": []})

    response = client.get("/api/development-dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["team_summary"]["player_count"] == 1
    assert payload["team_summary"]["average_player_value_score"] == 0.75
    assert payload["player_summaries"][0]["latest_trend_delta"] == 0.25
    assert payload["practice_feedback_summary"]["signal_count"] == 1
    assert payload["review_queue_summary"]["open_count"] == 1
    assert payload["model_registry_summary"]["active_version"] == "v1"
