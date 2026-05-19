import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_coach_report_with_missing_artifacts_warns(client: TestClient) -> None:
    response = client.post("/api/reports/coach", json={"title": "Empty Local Report"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Empty Local Report"
    assert payload["warnings"]
    assert "Missing artifact" in payload["markdown"]
    assert any(section["name"] == "Methodology & Limitations" for section in payload["sections"])

    list_response = client.get("/api/reports/coach")
    assert list_response.status_code == 200
    assert list_response.json()["reports"][0]["report_id"] == payload["report_id"]


def test_coach_report_endpoints_return_markdown_and_json(client: TestClient, tmp_path: Path) -> None:
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_summary.json",
        {
            "summaries": [
                {
                    "project_id": "project-1",
                    "player_key": "P1",
                    "display_name": "Local P1",
                    "player_value_score": 0.72,
                    "confidence": 0.81,
                    "decision_event_count": 3,
                }
            ],
            "warnings": [],
        },
    )
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_build_index.json", {"builds": []})
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"global_summary": {"attempt_count": 3, "correct_rate": 0.67, "avg_role_adjusted_score": 0.5}})
    _write_json(tmp_path / "decision_rules" / "active_rule_set.json", {"rule_set_id": "rules", "version": 1, "rules": []})
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text(
        json.dumps({"project_id": "project-1", "prompt_id": "prompt-1", "attempt_id": "attempt-1", "selected_option_id": "A", "correct_option_id": "B", "role_adjusted_score": 0.2}) + "\n",
        encoding="utf-8",
    )
    _write_json(tmp_path / "review_queue" / "review_queue.json", [])
    _write_json(tmp_path / "review_queue" / "review_action_log.json", [])
    _write_json(tmp_path / "reference_videos" / "reference_videos.json", [])
    _write_json(tmp_path / "source_registry.json", [])

    response = client.post("/api/reports/coach", json={"title": "Filtered", "project_id": "project-1", "player_key": "P1"})

    assert response.status_code == 200
    report_id = response.json()["report_id"]
    markdown_response = client.get(f"/api/reports/coach/{report_id}/markdown")
    assert markdown_response.status_code == 200
    assert "Local P1" in markdown_response.text
    assert "No LLM-generated coach advice" in markdown_response.text

    json_response = client.get(f"/api/reports/coach/{report_id}/json")
    assert json_response.status_code == 200
    assert json_response.json()["report_id"] == report_id


def test_unknown_coach_report_returns_typed_error(client: TestClient) -> None:
    response = client.get("/api/reports/coach/missing-report")

    assert response.status_code == 404
    assert response.json()["code"] == "COACH_REPORT_NOT_FOUND"


def test_summary_coach_report_depth_surfaces_compact_warning_sections(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    from app.services import artifact_map_service

    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_summary.json",
        {
            "summaries": [
                {
                    "project_id": "project-1",
                    "player_key": "UNKNOWN",
                    "display_name": None,
                    "player_value_score": 0.44,
                    "confidence": 0.31,
                    "decision_event_count": 2,
                    "correct_rate": 0.5,
                    "timeout_rate": 0.25,
                    "warnings": ["Identity is UNKNOWN; no real or inferred player name is claimed."],
                }
            ],
            "warnings": ["Global Player Value warning"],
        },
    )
    _write_json(
        tmp_path / "datasets" / "player_value" / "player_value_build_index.json",
        {
            "builds": [
                {
                    "build_id": "build-1",
                    "generated_at": "2026-01-01T00:00:00Z",
                    "summary_count": 1,
                    "snapshot_path": "builds/build-1.json",
                    "warnings": [],
                    "player_value_formula_version": "v1",
                    "recognition_model_version": "rec-a",
                    "decision_rule_set_version": "rules-a",
                    "dataset_fingerprint": "fingerprint-a",
                },
                {
                    "build_id": "build-2",
                    "generated_at": "2026-01-02T00:00:00Z",
                    "summary_count": 1,
                    "snapshot_path": "builds/build-2.json",
                    "warnings": [],
                    "player_value_formula_version": "v1",
                    "recognition_model_version": "rec-b",
                    "decision_rule_set_version": "rules-a",
                    "dataset_fingerprint": "fingerprint-a",
                },
            ]
        },
    )
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"global_summary": {"attempt_count": 2, "correct_rate": 0.5, "avg_role_adjusted_score": 0.4}})
    _write_json(tmp_path / "decision_rules" / "active_rule_set.json", {"rules": []})
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text("", encoding="utf-8")
    _write_json(tmp_path / "review_queue" / "review_queue.json", {"items": [{"item_id": "review-1"}]})
    _write_json(tmp_path / "review_queue" / "review_action_log.json", [])
    _write_json(tmp_path / "reference_videos" / "reference_videos.json", [])
    _write_json(
        tmp_path / "source_registry.json",
        [{"source_id": "source-1", "name": "Unconfirmed source", "rights_confirmed": False, "usage_scope": "REFERENCE_ONLY", "allowed_for_training": False}],
    )

    monkeypatch.setattr(
        artifact_map_service,
        "build_artifact_map",
        lambda: type(
            "ArtifactMapStub",
            (),
            {"artifacts": [type("ArtifactStub", (), {"status": "stale", "label": "Coach reports", "stale_reason": "Player Value is newer than coach reports."})()]},
        )(),
    )

    response = client.post("/api/reports/coach", json={"title": "Summary", "report_depth": "SUMMARY"})

    assert response.status_code == 200
    payload = response.json()
    markdown = payload["markdown"]
    assert payload["report_depth"] == "SUMMARY"
    for heading in ["Top Findings", "Player Focus", "Recommended Drills", "Suggested Practice Focus", "Confidence & Warnings", "Evidence References"]:
        assert f"## {heading}" in markdown
    assert "confidence 0.31" in markdown
    assert "Identity is UNKNOWN" in markdown
    assert "Mixed baseline warning" in markdown
    assert "Stale artifact warning" in markdown
    assert "Source governance warning" in markdown

    list_response = client.get("/api/reports/coach")
    assert list_response.status_code == 200
    assert list_response.json()["reports"][0]["report_depth"] == "SUMMARY"


def test_full_coach_report_keeps_source_governance_section_behavior(client: TestClient, tmp_path: Path) -> None:
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_summary.json", {"summaries": []})
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_build_index.json", {"builds": []})
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"global_summary": {}})
    _write_json(tmp_path / "decision_rules" / "active_rule_set.json", {"rules": []})
    (tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").write_text("", encoding="utf-8")
    _write_json(tmp_path / "review_queue" / "review_queue.json", [])
    _write_json(tmp_path / "review_queue" / "review_action_log.json", [])
    _write_json(tmp_path / "reference_videos" / "reference_videos.json", [])
    _write_json(
        tmp_path / "source_registry.json",
        [{"source_id": "source-1", "name": "Unconfirmed source", "rights_confirmed": False, "usage_scope": "REFERENCE_ONLY", "allowed_for_training": False}],
    )

    response = client.post("/api/reports/coach", json={"title": "Full", "report_depth": "FULL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_depth"] == "FULL"
    assert "## Source Governance" in payload["markdown"]
    assert "Source governance warning" not in payload["markdown"]
