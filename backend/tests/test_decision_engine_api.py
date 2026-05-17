import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import local_lab
from app.services import decision_engine
from app.api.common import write_json_model
from app.models import Project, QuizAttemptRecord, QuizPrompt


def _option(option_id: str, *, is_correct: bool = False, expected_value: float | None = None) -> dict:
    return {
        "option_id": option_id,
        "label": f"Option {option_id}",
        "action_type": "PASS",
        "start": {"x": 0.25, "y": 0.4},
        "end": {"x": 0.75, "y": 0.6},
        "expected_value": expected_value,
        "is_correct": is_correct,
        "explanation": f"Explanation for {option_id}",
    }


def _prompt(project_id: str = "project-1", **overrides) -> QuizPrompt:
    payload = {
        "project_id": project_id,
        "prompt_id": "prompt-1",
        "question": "What is the best decision?",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "frame_id": "frame-1",
        "frame_index": 7,
        "timestamp_seconds": 2.8,
        "question_mode": "ROLE_READ",
        "options": [
            _option("A", expected_value=1.12),
            _option("C", is_correct=True, expected_value=1.18),
        ],
        "explanation": "Hit the cutter for the highest-value look.",
    }
    payload.update(overrides)
    return QuizPrompt.model_validate(payload)


def _attempt(project_id: str = "project-1", **overrides) -> QuizAttemptRecord:
    payload = {
        "project_id": project_id,
        "attempt_id": "attempt-1",
        "prompt_id": "prompt-1",
        "selected_option_id": "A",
        "correct_option_id": "C",
        "is_correct": False,
        "selected_expected_value": 1.12,
        "correct_expected_value": 1.18,
        "opportunity_cost": 0.06,
        "score": 88,
        "scoring_mode": "EXPECTED_VALUE",
        "selected_explanation": "Explanation for A",
        "correct_explanation": "Explanation for C",
        "selected_role_feedback": "Explanation for A",
        "correct_role_feedback": "Explanation for C",
        "summary_explanation": "Hit the cutter for the highest-value look.",
        "response_time_ms": 1200,
        "timed_out": False,
        "user_role": "PLAYER",
    }
    payload.update(overrides)
    return QuizAttemptRecord.model_validate(payload)


def _write_project_with_quiz(directory: Path, *, prompt: QuizPrompt, attempts: list[QuizAttemptRecord]) -> None:
    write_json_model(directory / "project.json", Project(project_id=prompt.project_id, name="Decision engine test"))
    (directory / "quiz_prompts.json").write_text(json.dumps([prompt.model_dump(mode="json")], indent=2), encoding="utf-8")
    (directory / "quiz_attempts.json").write_text(json.dumps([attempt.model_dump(mode="json") for attempt in attempts], indent=2), encoding="utf-8")


def test_build_decision_events_writes_explainable_jsonl(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    prompt = _prompt()
    attempt = _attempt()
    _write_project_with_quiz(tmp_path / "project-1", prompt=prompt, attempts=[attempt])

    response = client.post("/api/local-lab/decision-events/build")

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_count"] == 1
    assert payload["avg_raw_score"] == 88.0
    assert payload["avg_role_adjusted_score"] == 88.0
    assert payload["opportunity_cost_avg"] == 0.06
    assert payload["decision_engine_version"] == "v2"
    assert payload["use_active_rules"] is True
    output_path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    event = rows[0]
    assert event["evaluation_source"] == "MANUAL_EXPECTED_VALUE"
    assert event["selected_expected_value"] == 1.12
    assert event["best_expected_value"] == 1.18
    assert event["opportunity_cost"] == 0.06
    assert event["role_adjusted_score"] == 88
    assert event["explanations"]


def test_decision_events_persist_prompt_and_option_source_track_links(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    prompt = _prompt(
        context_track_ids=["frame-track"],
        source_track_ids=["prompt-actor-track"],
        options=[
            _option("A", expected_value=1.12) | {"source_track_ids": ["selected-track"]},
            _option("C", is_correct=True, expected_value=1.18) | {"source_track_ids": ["correct-track"]},
        ],
    )
    attempt = _attempt()
    _write_project_with_quiz(tmp_path / "project-1", prompt=prompt, attempts=[attempt])

    response = client.post("/api/local-lab/decision-events/build")

    assert response.status_code == 200
    output_path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    event = json.loads(output_path.read_text(encoding="utf-8").strip())
    assert event["context_track_ids"] == ["frame-track"]
    assert event["source_track_ids"] == ["prompt-actor-track", "selected-track", "correct-track"]


def test_decision_events_use_rule_based_fallback_and_role_bonuses(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    prompt = _prompt(options=[_option("A"), _option("C", is_correct=True)], time_limit_ms=3000)
    attempt = _attempt(
        selected_option_id="C",
        is_correct=True,
        selected_expected_value=None,
        correct_expected_value=None,
        opportunity_cost=None,
        score=100,
        scoring_mode="CORRECTNESS_ONLY",
        response_time_ms=1000,
    )
    _write_project_with_quiz(tmp_path / "project-1", prompt=prompt, attempts=[attempt])

    response = client.post("/api/local-lab/decision-events/build")

    assert response.status_code == 200
    assert response.json()["avg_role_adjusted_score"] == 100.0
    output_path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    event = json.loads(output_path.read_text(encoding="utf-8").strip())
    assert event["evaluation_source"] == "RULE_BASED"
    assert event["raw_score"] == 100
    assert "ROLE_READ correct-answer bonus applied: +5, capped at 100." in event["explanations"]
    assert "Fast response bonus applied: +3 for answering faster than half the time limit, capped at 100." in event["explanations"]


def _write_active_rule_set(path: Path, *, weight: float = 4.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "rule_set_id": "rules-playoff",
                "name": "Playoff reads",
                "version": 2,
                "active": True,
                "rules": [
                    {
                        "rule_id": "rule-pass",
                        "court_role": "BALL_HANDLER",
                        "situation_type": "PICK_AND_ROLL",
                        "condition_text": "hit the pass",
                        "positive_cue": "Option A",
                        "negative_cue": "forced shot",
                        "weight": weight,
                        "explanation": "Reward the selected pass read.",
                        "status": "ACTIVE",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_decision_events_apply_active_rules_with_bounded_delta(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    active_rule_path = tmp_path / "decision_rules" / "active_rule_set.json"
    _write_active_rule_set(active_rule_path, weight=12.0)
    monkeypatch.setattr(decision_engine, "ACTIVE_RULE_SET_PATH", active_rule_path)
    monkeypatch.setattr(decision_engine, "RULE_SETS_PATH", tmp_path / "decision_rules" / "rule_sets.json")

    prompt = _prompt()
    attempt = _attempt()
    _write_project_with_quiz(tmp_path / "project-1", prompt=prompt, attempts=[attempt])

    response = client.post("/api/local-lab/decision-events/build")

    assert response.status_code == 200
    summary = response.json()
    assert summary["active_rule_set_id"] == "rules-playoff"
    assert summary["rule_matched_count"] == 1
    assert summary["avg_rule_score_delta"] == 10.0

    output_path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    event = json.loads(output_path.read_text(encoding="utf-8").strip())
    assert event["decision_engine_version"] == "v2"
    assert event["base_score"] == 88
    assert event["rule_score_delta"] == 10.0
    assert event["final_score"] == 98
    assert event["rule_application"]["delta_bounded"] is True
    assert event["rule_application"]["results"][0]["matched"] is True


def test_decision_events_can_disable_active_rules(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    active_rule_path = tmp_path / "decision_rules" / "active_rule_set.json"
    _write_active_rule_set(active_rule_path)
    monkeypatch.setattr(decision_engine, "ACTIVE_RULE_SET_PATH", active_rule_path)

    prompt = _prompt()
    attempt = _attempt()
    _write_project_with_quiz(tmp_path / "project-1", prompt=prompt, attempts=[attempt])

    response = client.post("/api/local-lab/decision-events/build?use_active_rules=false")

    assert response.status_code == 200
    assert response.json()["use_active_rules"] is False
    event = json.loads((tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl").read_text(encoding="utf-8").strip())
    assert event["rule_score_delta"] == 0.0
    assert event["final_score"] == 88
    assert event["rule_application"]["enabled"] is False
