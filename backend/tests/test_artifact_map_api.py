from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, text: str, mtime: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    ts = mtime.timestamp()
    os.utime(path, (ts, ts))


def test_artifact_map_reports_deterministic_staleness(client, tmp_path: Path):
    project_dir = tmp_path / "project-1"
    _write_json(project_dir / "project.json", {"project_id": "project-1", "name": "Project One", "updated_at": "2026-01-01T00:00:00Z"})
    _write_json(project_dir / "calibration.json", {"updated_at": "2026-01-03T00:00:00Z"})
    _write_json(project_dir / "tracking.json", {"updated_at": "2026-01-02T00:00:00Z"})
    _write_json(project_dir / "tracking_cleaned.json", {"updated_at": "2026-01-02T00:00:00"})
    _write_json(project_dir / "tracking_review_patch.json", {"updated_at": "2026-01-04T00:00:00Z"})
    _write_json(project_dir / "projected_tracks.json", {"updated_at": "2026-01-02T12:00:00Z"})
    _write_json(project_dir / "player_aliases.json", {"updated_at": "2026-01-06T00:00:00Z", "aliases": []})
    _write_json(project_dir / "quiz_prompts.json", {"updated_at": "2026-01-05T00:00:00Z"})
    _write_json(project_dir / "quiz_attempts.json", {"updated_at": "2026-01-05T00:00:00Z"})
    _write_json(tmp_path / "decision_rules" / "active_rule_set.json", {"updated_at": "2026-01-05T00:00:00Z", "rules": []})
    _write_text(tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl", '{"event":"old"}\n', datetime(2026, 1, 4, tzinfo=timezone.utc))
    _write_json(tmp_path / "datasets" / "player_value" / "player_value_summary.json", {"updated_at": "2026-01-05T12:00:00Z", "summaries": []})
    _write_json(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", {"updated_at": "2026-01-07T00:00:00Z"})
    _write_json(tmp_path / "drills" / "latest_recommendations.json", {"updated_at": "2026-01-06T00:00:00Z", "recommendations": []})
    _write_json(tmp_path / "practice_plans" / "index.json", {"updated_at": "2026-01-05T00:00:00Z", "plans": []})
    _write_json(tmp_path / "reports" / "coach" / "index.json", {"updated_at": "2026-01-05T00:00:00Z", "reports": []})

    response = client.get("/api/local-lab/artifact-map")

    assert response.status_code == 200
    payload = response.json()
    by_key = {artifact["key"]: artifact for artifact in payload["artifacts"]}
    assert by_key["project:project-1:tracking_cleaned"]["status"] == "stale"
    assert by_key["project:project-1:tracking_cleaned"]["updated_at"].endswith("Z")
    assert by_key["project:project-1:projected_tracks"]["status"] == "stale"
    assert by_key["player_value:decision_events"]["status"] == "stale"
    assert by_key["player_value:summary"]["status"] == "stale"
    assert by_key["drills:recommendations"]["status"] == "stale"
    assert by_key["practice:plans"]["status"] == "stale"
    assert by_key["reports:coach"]["status"] == "stale"
    assert payload["stale_artifact_count"] >= 7
    assert any("stale" in warning for warning in payload["warnings"])
