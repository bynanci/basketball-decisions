import json
import math
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import (
    PlayerAlias,
    PlayerAliasListResponse,
    PlayerTrack,
    Project,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
)


def _write_project(directory: Path, project_id: str = "project-1") -> None:
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Player Value test"))


def _event(project_id: str = "project-1", attempt_id: str = "attempt-1", prompt_id: str = "prompt-1", score: int = 80, **overrides) -> dict:
    payload = {
        "project_id": project_id,
        "prompt_id": prompt_id,
        "attempt_id": attempt_id,
        "frame_id": "frame-1",
        "frame_index": 1,
        "user_role": "PLAYER",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "question_mode": "FREEZE_FRAME",
        "selected_option_id": "A",
        "correct_option_id": "B",
        "is_correct": score >= 90,
        "selected_expected_value": None,
        "best_expected_value": None,
        "opportunity_cost": None,
        "raw_score": score,
        "role_adjusted_score": score,
        "response_time_ms": 1000,
        "timed_out": False,
        "evaluation_source": "RULE_BASED",
        "explanations": ["test event"],
    }
    payload.update(overrides)
    return payload


def _write_events(tmp_path: Path, events: list[dict]) -> Path:
    path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    return path


def _write_prompt_with_track(directory: Path, project_id: str = "project-1", track_id: str = "track-1") -> None:
    prompt = {
        "project_id": project_id,
        "prompt_id": "prompt-1",
        "question": "What is the read?",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "frame_id": "frame-1",
        "frame_index": 1,
        "timestamp_seconds": 0.5,
        "options": [
            {
                "option_id": "A",
                "label": "Pass",
                "action_type": "PASS",
                "start": {"x": 0.1, "y": 0.1},
                "end": {"x": 0.2, "y": 0.2},
                "is_correct": False,
                "explanation": "No",
                "trace": {"track_id": track_id},
            },
            {
                "option_id": "B",
                "label": "Drive",
                "action_type": "DRIVE",
                "start": {"x": 0.1, "y": 0.1},
                "end": {"x": 0.3, "y": 0.3},
                "is_correct": True,
                "explanation": "Yes",
            },
        ],
        "explanation": "Local prompt trace links this decision to a track.",
    }
    (directory / "quiz_prompts.json").write_text(json.dumps([prompt]), encoding="utf-8")


def _write_tracking(directory: Path, project_id: str = "project-1") -> None:
    def points(count: int) -> list[TrackPoint]:
        return [
            TrackPoint(
                frame_id=f"frame-{index}",
                frame_index=index,
                timestamp_seconds=float(index),
                image_point_x=0.2,
                image_point_y=0.3,
                confidence=0.95,
            )
            for index in range(count)
        ]

    write_json_model(
        directory / "tracking.json",
        RunTrackingResponse(
            project_id=project_id,
            request=RunTrackingRequest(project_id=project_id),
            tracks=[PlayerTrack(track_id="track-1", points=points(10)), PlayerTrack(track_id="track-2", points=points(4))],
            detections=[],
        ),
    )


def test_builds_unknown_summary_if_no_aliases(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_events(tmp_path, [_event()])

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summaries"][0]["player_key"] == "UNKNOWN"
    assert payload["summaries"][0]["display_name"] is None
    assert any("UNKNOWN" in warning for warning in payload["summaries"][0]["warnings"])


def test_uses_alias_when_track_id_maps_to_player_key(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_prompt_with_track(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(
            project_id="project-1",
            aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"], display_name="Local P1", team_side="HOME")],
        ),
    )
    _write_events(tmp_path, [_event()])

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    summary = response.json()["summaries"][0]
    assert summary["player_key"] == "P1"
    assert summary["display_name"] == "Local P1"
    assert summary["track_ids"] == ["track-1"]


def test_uses_alias_when_decision_event_persists_source_track_ids(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(
            project_id="project-1",
            aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"], display_name="Local P1", team_side="HOME")],
        ),
    )
    _write_events(tmp_path, [_event(source_track_ids=["track-1"])])

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    summary = response.json()["summaries"][0]
    assert summary["player_key"] == "P1"
    assert summary["track_ids"] == ["track-1"]


def test_score_components_sum_correctly_and_summary_is_stored(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_prompt_with_track(directory)
    _write_tracking(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(project_id="project-1", aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"])]),
    )
    _write_events(
        tmp_path,
        [
            _event(attempt_id="attempt-1", score=60, opportunity_cost=0.2),
            _event(attempt_id="attempt-2", score=70, opportunity_cost=0.1),
            _event(attempt_id="attempt-3", score=80, opportunity_cost=0.0),
            _event(attempt_id="attempt-4", score=90, opportunity_cost=0.0, is_correct=True),
            _event(attempt_id="attempt-5", score=100, opportunity_cost=0.0, is_correct=True),
        ],
    )

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    summary = response.json()["summaries"][0]
    component_sum = sum(component["contribution"] for component in summary["components"])
    assert math.isclose(summary["player_value_score"], component_sum, abs_tol=0.0001)
    stored_path = tmp_path / "datasets" / "player_value" / "player_value_summary.json"
    assert stored_path.exists()
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert stored["summaries"][0]["player_value_score"] == summary["player_value_score"]


def test_low_confidence_when_insufficient_decision_events(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_prompt_with_track(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(project_id="project-1", aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"])]),
    )
    _write_events(tmp_path, [_event()])

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    summary = response.json()["summaries"][0]
    assert summary["decision_event_count"] == 1
    assert summary["confidence"] < 0.7
    assert any("fewer than 5" in warning for warning in summary["warnings"])
