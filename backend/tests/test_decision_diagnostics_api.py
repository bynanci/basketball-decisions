import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import Project, QuizAttemptRecord, QuizPrompt


def _option(option_id: str, *, is_correct: bool = False, expected_value: float | None = None) -> dict:
    return {
        "option_id": option_id,
        "label": f"Option {option_id}",
        "action_type": "PASS",
        "start": {"x": 0.2, "y": 0.3},
        "end": {"x": 0.8, "y": 0.7},
        "expected_value": expected_value,
        "is_correct": is_correct,
        "explanation": f"Explanation {option_id}",
    }


def _prompt(prompt_id: str, **overrides) -> QuizPrompt:
    payload = {
        "project_id": "project-1",
        "prompt_id": prompt_id,
        "question": "What should the player do?",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "frame_id": f"frame-{prompt_id}",
        "frame_index": 1,
        "timestamp_seconds": 1.0,
        "question_mode": "FREEZE_FRAME",
        "options": [_option("A", is_correct=True, expected_value=1.0), _option("B", expected_value=0.4)],
        "explanation": "Take the best option.",
    }
    payload.update(overrides)
    return QuizPrompt.model_validate(payload)


def _attempt(prompt: QuizPrompt, attempt_id: str, selected_option_id: str | None, **overrides) -> QuizAttemptRecord:
    correct_option_id = next(option.option_id for option in prompt.options if option.is_correct)
    selected_option = next((option for option in prompt.options if option.option_id == selected_option_id), None)
    correct = selected_option_id == correct_option_id
    payload = {
        "project_id": prompt.project_id,
        "attempt_id": attempt_id,
        "prompt_id": prompt.prompt_id,
        "selected_option_id": selected_option_id,
        "correct_option_id": correct_option_id,
        "is_correct": correct,
        "selected_expected_value": selected_option.expected_value if selected_option else None,
        "correct_expected_value": 1.0,
        "opportunity_cost": 0.0 if correct else 0.6,
        "score": 100 if correct else 0,
        "scoring_mode": "EXPECTED_VALUE",
        "selected_explanation": "Selected explanation",
        "correct_explanation": "Correct explanation",
        "selected_role_feedback": "Selected feedback",
        "correct_role_feedback": "Correct feedback",
        "summary_explanation": "Summary",
        "response_time_ms": 1000,
        "timed_out": False,
        "user_role": "PLAYER",
    }
    payload.update(overrides)
    return QuizAttemptRecord.model_validate(payload)


def _write_project(tmp_path: Path, prompts: list[QuizPrompt], attempts: list[QuizAttemptRecord]) -> None:
    directory = tmp_path / "project-1"
    write_json_model(directory / "project.json", Project(project_id="project-1", name="Diagnostics test"))
    (directory / "quiz_prompts.json").write_text(json.dumps([prompt.model_dump(mode="json") for prompt in prompts]), encoding="utf-8")
    (directory / "quiz_attempts.json").write_text(json.dumps([attempt.model_dump(mode="json") for attempt in attempts]), encoding="utf-8")


def _diagnostics_by_prompt(response_json: dict) -> dict[str, dict]:
    return {diagnostic["prompt_id"]: diagnostic for diagnostic in response_json["prompt_diagnostics"]}


def test_decision_diagnostics_detects_too_easy_prompt(client: TestClient, tmp_path: Path) -> None:
    prompt = _prompt("easy")
    attempts = [_attempt(prompt, f"easy-{index}", "A") for index in range(10)]
    _write_project(tmp_path, [prompt], attempts)

    response = client.post("/api/local-lab/decision-diagnostics/build")

    assert response.status_code == 200
    diagnostic = _diagnostics_by_prompt(response.json())["easy"]
    assert diagnostic["difficulty"] == "TOO_EASY"
    assert diagnostic["correct_rate"] == 1.0
    assert any("above 90%" in reason for reason in diagnostic["reasons"])


def test_decision_diagnostics_detects_too_hard_prompt(client: TestClient, tmp_path: Path) -> None:
    prompt = _prompt("hard")
    attempts = [_attempt(prompt, f"hard-{index}", "B") for index in range(4)] + [_attempt(prompt, "hard-correct", "A")]
    _write_project(tmp_path, [prompt], attempts)

    response = client.post("/api/local-lab/decision-diagnostics/build")

    assert response.status_code == 200
    diagnostic = _diagnostics_by_prompt(response.json())["hard"]
    assert diagnostic["difficulty"] == "TOO_HARD"
    assert diagnostic["avg_opportunity_cost"] > 0.3
    assert any("high-cost" in reason for reason in diagnostic["reasons"])


def test_decision_diagnostics_detects_insufficient_data_prompt(client: TestClient, tmp_path: Path) -> None:
    prompt = _prompt("sparse")
    attempts = [_attempt(prompt, "sparse-1", "A"), _attempt(prompt, "sparse-2", "B")]
    _write_project(tmp_path, [prompt], attempts)

    response = client.post("/api/local-lab/decision-diagnostics/build")

    assert response.status_code == 200
    diagnostic = _diagnostics_by_prompt(response.json())["sparse"]
    assert diagnostic["difficulty"] == "INSUFFICIENT_DATA"
    assert any("Fewer than 3 attempts" in reason for reason in diagnostic["reasons"])


def test_decision_diagnostics_detects_suspected_label_issue(client: TestClient, tmp_path: Path) -> None:
    prompt = _prompt("label-issue")
    attempts = [_attempt(prompt, f"wrong-{index}", "B") for index in range(5)] + [_attempt(prompt, "right-1", "A")]
    _write_project(tmp_path, [prompt], attempts)

    response = client.post("/api/local-lab/decision-diagnostics/build")

    assert response.status_code == 200
    diagnostic = _diagnostics_by_prompt(response.json())["label-issue"]
    assert diagnostic["suspected_label_issue"] is True
    assert diagnostic["most_selected_wrong_option_id"] == "B"
    assert any("Suspected label issue" in reason and "B" in reason for reason in diagnostic["reasons"])
    output_path = tmp_path / "datasets" / "decision" / "decision_diagnostics.json"
    assert output_path.exists()


def test_decision_diagnostics_uses_project_scoped_event_scores(client: TestClient, tmp_path: Path) -> None:
    prompt_a = _prompt("shared-prompt", project_id="project-a")
    prompt_b = _prompt("shared-prompt", project_id="project-b")
    attempt_a = _attempt(prompt_a, "shared-attempt", "A", score=100)
    attempt_b = _attempt(prompt_b, "shared-attempt", "B", score=0)

    for project_id, prompt, attempt in (("project-a", prompt_a, attempt_a), ("project-b", prompt_b, attempt_b)):
        directory = tmp_path / project_id
        write_json_model(directory / "project.json", Project(project_id=project_id, name=f"Diagnostics {project_id}"))
        (directory / "quiz_prompts.json").write_text(json.dumps([prompt.model_dump(mode="json")]), encoding="utf-8")
        (directory / "quiz_attempts.json").write_text(json.dumps([attempt.model_dump(mode="json")]), encoding="utf-8")

    events_path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    events_path.parent.mkdir(parents=True)
    events_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "project_id": "project-a",
                        "prompt_id": "shared-prompt",
                        "attempt_id": "shared-attempt",
                        "frame_id": "frame-shared-prompt",
                        "frame_index": 1,
                        "user_role": "PLAYER",
                        "court_role_target": "BALL_HANDLER",
                        "situation_type": "PICK_AND_ROLL",
                        "question_mode": "FREEZE_FRAME",
                        "selected_option_id": "A",
                        "correct_option_id": "A",
                        "is_correct": True,
                        "selected_expected_value": 1.0,
                        "best_expected_value": 1.0,
                        "opportunity_cost": 0.0,
                        "raw_score": 91,
                        "role_adjusted_score": 92,
                        "response_time_ms": 1000,
                        "timed_out": False,
                        "evaluation_source": "MANUAL_EXPECTED_VALUE",
                        "explanations": ["project-a event"],
                        "created_at": "2026-05-11T00:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "project_id": "project-b",
                        "prompt_id": "shared-prompt",
                        "attempt_id": "shared-attempt",
                        "frame_id": "frame-shared-prompt",
                        "frame_index": 1,
                        "user_role": "PLAYER",
                        "court_role_target": "BALL_HANDLER",
                        "situation_type": "PICK_AND_ROLL",
                        "question_mode": "FREEZE_FRAME",
                        "selected_option_id": "B",
                        "correct_option_id": "A",
                        "is_correct": False,
                        "selected_expected_value": 0.4,
                        "best_expected_value": 1.0,
                        "opportunity_cost": 0.6,
                        "raw_score": 11,
                        "role_adjusted_score": 12,
                        "response_time_ms": 1000,
                        "timed_out": False,
                        "evaluation_source": "MANUAL_EXPECTED_VALUE",
                        "explanations": ["project-b event"],
                        "created_at": "2026-05-11T00:00:00Z",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    response = client.post("/api/local-lab/decision-diagnostics/build")

    assert response.status_code == 200
    diagnostics = {
        (diagnostic["project_id"], diagnostic["prompt_id"]): diagnostic
        for diagnostic in response.json()["prompt_diagnostics"]
    }
    assert diagnostics[("project-a", "shared-prompt")]["avg_score"] == 91.0
    assert diagnostics[("project-a", "shared-prompt")]["avg_role_adjusted_score"] == 92.0
    assert diagnostics[("project-b", "shared-prompt")]["avg_score"] == 11.0
    assert diagnostics[("project-b", "shared-prompt")]["avg_role_adjusted_score"] == 12.0
