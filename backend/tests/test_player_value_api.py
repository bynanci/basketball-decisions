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
                "source_track_ids": [track_id],
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


def test_context_only_event_does_not_use_alias_track_for_player_value(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(
            project_id="project-1",
            aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"], display_name="Local P1", team_side="HOME")],
        ),
    )
    _write_events(tmp_path, [_event(context_track_ids=["track-1"], source_track_ids=[])])

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    summary = response.json()["summaries"][0]
    assert summary["player_key"] == "UNKNOWN"
    assert summary["track_ids"] == []
    assert any("only frame context tracks" in warning for warning in summary["warnings"])


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



def test_ambiguous_source_tracks_fall_back_to_unknown_with_warning(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(
            project_id="project-1",
            aliases=[
                PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"], display_name="Local P1"),
                PlayerAlias(project_id="project-1", player_key="P2", track_ids=["track-2"], display_name="Local P2"),
            ],
        ),
    )
    _write_events(tmp_path, [_event(source_track_ids=["track-1", "track-2"])])

    response = client.post("/api/local-lab/player-value/build")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["summaries"]) == 1
    summary = payload["summaries"][0]
    assert summary["player_key"] == "UNKNOWN"
    assert summary["display_name"] is None
    assert summary["track_ids"] == ["track-1", "track-2"]
    assert any("matched multiple aliases" in warning and "UNKNOWN" in warning for warning in summary["warnings"])

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


def test_evidence_endpoint_returns_summary_and_linked_events(client: TestClient, tmp_path: Path) -> None:
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
    _write_events(tmp_path, [_event(source_track_ids=["track-1"], opportunity_cost=0.25)])
    client.post("/api/local-lab/player-value/build")

    response = client.get("/api/local-lab/player-value/project-1/P1/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["player_key"] == "P1"
    assert payload["events"][0]["prompt_question"] == "What is the read?"
    assert payload["events"][0]["selected_option_label"] == "Pass"
    assert payload["events"][0]["correct_option_label"] == "Drive"
    assert payload["events"][0]["source_track_ids"] == ["track-1"]
    assert payload["events"][0]["alias_player_key"] == "P1"


def test_evidence_missing_summary_returns_404(client: TestClient) -> None:
    response = client.get("/api/local-lab/player-value/project-1/P1/evidence")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == "PLAYER_VALUE_SUMMARY_NOT_FOUND"
    assert "Run POST /api/local-lab/player-value/build first" in payload["debug_hint"]


def test_evidence_missing_prompt_adds_warning_without_crashing(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_events(tmp_path, [_event(source_track_ids=["track-1"])])
    client.post("/api/local-lab/player-value/build")

    response = client.get("/api/local-lab/player-value/project-1/UNKNOWN/evidence")

    assert response.status_code == 200
    event = response.json()["events"][0]
    assert event["prompt_question"] is None
    assert any("Prompt evidence is missing" in warning for warning in event["evidence_warnings"])


def test_evidence_context_tracks_are_not_used_as_alias_evidence(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    write_json_model(
        directory / "player_aliases.json",
        PlayerAliasListResponse(
            project_id="project-1",
            aliases=[PlayerAlias(project_id="project-1", player_key="P1", track_ids=["track-1"], display_name="Local P1")],
        ),
    )
    _write_events(tmp_path, [_event(context_track_ids=["track-1"], source_track_ids=[])])
    client.post("/api/local-lab/player-value/build")

    response = client.get("/api/local-lab/player-value/project-1/UNKNOWN/evidence")

    assert response.status_code == 200
    event = response.json()["events"][0]
    assert event["context_track_ids"] == ["track-1"]
    assert event["source_track_ids"] == []
    assert event["alias_player_key"] is None
    assert any("context_track_ids are frame context only" in warning for warning in event["evidence_warnings"])


def test_evidence_missing_trace_event_adds_warning(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_events(tmp_path, [_event()])
    client.post("/api/local-lab/player-value/build")
    summary_path = tmp_path / "datasets" / "player_value" / "player_value_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["summaries"][0]["trace"]["decision_event_ids"].append("project-1:prompt-1:missing-attempt")
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    response = client.get("/api/local-lab/player-value/project-1/UNKNOWN/evidence")

    assert response.status_code == 200
    assert any("missing from player_decision_events.jsonl" in warning for warning in response.json()["warning_summary"])


def test_evidence_role_and_situation_breakdowns_compute_averages(client: TestClient, tmp_path: Path) -> None:
    directory = tmp_path / "project-1"
    _write_project(directory)
    _write_events(
        tmp_path,
        [
            _event(attempt_id="a1", score=80, opportunity_cost=0.2, is_correct=False, timed_out=False),
            _event(attempt_id="a2", score=100, opportunity_cost=0.0, is_correct=True, timed_out=True),
        ],
    )
    client.post("/api/local-lab/player-value/build")

    response = client.get("/api/local-lab/player-value/project-1/UNKNOWN/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_breakdown"][0]["court_role"] == "BALL_HANDLER"
    assert payload["role_breakdown"][0]["event_count"] == 2
    assert math.isclose(payload["role_breakdown"][0]["avg_role_adjusted_score"], 90.0)
    assert math.isclose(payload["role_breakdown"][0]["avg_opportunity_cost"], 0.1)
    assert math.isclose(payload["role_breakdown"][0]["correct_rate"], 0.5)
    assert math.isclose(payload["role_breakdown"][0]["timeout_rate"], 0.5)
    assert payload["situation_breakdown"][0]["situation_type"] == "PICK_AND_ROLL"
