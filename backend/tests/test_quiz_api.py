import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import common, projects
from app.api.common import write_json_model
from app.main import app
from app.models import (
    CreateQuizPromptRequest,
    DecisionArrowPoint,
    ExtractFramesRequest,
    ExtractFramesResponse,
    FrameAsset,
    PlayerTrack,
    Project,
    QuizPrompt,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    return TestClient(app)


def write_project_without_frames(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Quiz test"))
    return directory


def write_project(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Quiz test"))
    frames = ExtractFramesResponse(
        project_id=project_id,
        request=ExtractFramesRequest(project_id=project_id, video_asset_id="video-1"),
        frames=[
            FrameAsset(
                frame_id="frame-1",
                frame_index=7,
                timestamp_seconds=2.8,
                image_path=str(directory / "frames" / "images" / "frame_7.jpg"),
                width=1280,
                height=720,
            )
        ],
    )
    write_json_model(directory / "frames" / "index.json", frames)
    return directory


def write_tracking(directory: Path, project_id: str = "project-1") -> None:
    write_json_model(
        directory / "tracking.json",
        RunTrackingResponse(
            project_id=project_id,
            request=RunTrackingRequest(project_id=project_id),
            tracks=[
                PlayerTrack(
                    track_id="track-1",
                    points=[
                        TrackPoint(
                            frame_id="frame-1",
                            frame_index=7,
                            timestamp_seconds=2.8,
                            image_point_x=0.25,
                            image_point_y=0.4,
                        )
                    ],
                ),
                PlayerTrack(
                    track_id="track-off-frame",
                    points=[
                        TrackPoint(
                            frame_id="frame-2",
                            frame_index=8,
                            timestamp_seconds=3.0,
                            image_point_x=0.5,
                            image_point_y=0.5,
                        )
                    ],
                ),
            ],
            detections=[],
        ),
    )


def option(option_id: str, *, is_correct: bool = False, expected_value: float | None = None) -> dict:
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


def valid_prompt_payload(*, expected_values: bool = True) -> dict:
    return {
        "question": "What is the best decision?",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "user_role_targets": ["BALL_HANDLER"],
        "role_instruction": "You are the ball handler. Read the help defender and choose the best next action.",
        "frame_id": "frame-1",
        "frame_index": 7,
        "timestamp_seconds": 2.8,
        "image_path": "/frames/frame_7.jpg",
        "options": [
            option("A", expected_value=0.82 if expected_values else None),
            option("C", is_correct=True, expected_value=1.18 if expected_values else None),
        ],
        "explanation": "Hit the cutter for the highest-value look.",
    }


def create_prompt(client: TestClient, tmp_path: Path, payload: dict | None = None) -> dict:
    write_project(tmp_path)
    response = client.post("/api/projects/project-1/quiz-prompts", json=payload or valid_prompt_payload())
    assert response.status_code == 200
    return response.json()


def test_quiz_models_reject_non_finite_arrow_coordinates() -> None:
    with pytest.raises(ValidationError):
        DecisionArrowPoint(x=math.nan, y=0.5)


def test_quiz_models_reject_non_finite_expected_values() -> None:
    payload = valid_prompt_payload()
    payload["options"][0]["expected_value"] = math.inf

    with pytest.raises(ValidationError):
        CreateQuizPromptRequest.model_validate(payload)


def test_legacy_prompt_hydrates_default_role_fields() -> None:
    payload = valid_prompt_payload()
    payload.pop("court_role_target")
    payload.pop("situation_type")
    payload.pop("user_role_targets")
    payload.pop("role_instruction")

    prompt = QuizPrompt.model_validate({"project_id": "project-1", "prompt_id": "prompt-1", **payload})

    assert prompt.court_role_target == "BALL_HANDLER"
    assert prompt.situation_type == "PICK_AND_ROLL"
    assert prompt.user_role_targets == []
    assert prompt.role_instruction is None


def test_cannot_create_prompt_without_role_fields(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload.pop("court_role_target")
    payload.pop("situation_type")

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_with_unknown_role_or_situation(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["court_role_target"] = "POINT_GUARD"

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_with_fewer_than_two_options(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["options"] = [option("A", is_correct=True)]

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_with_zero_correct_options(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["options"] = [option("A"), option("B")]

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_with_two_correct_options(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["options"] = [option("A", is_correct=True), option("B", is_correct=True)]

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_with_duplicate_option_ids(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["options"] = [option("A"), option("A", is_correct=True)]

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_with_out_of_range_arrow_coordinates(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["options"][0]["start"]["x"] = 1.25

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_cannot_create_prompt_before_frame_extraction(client: TestClient, tmp_path: Path) -> None:
    write_project_without_frames(tmp_path)

    response = client.post("/api/projects/project-1/quiz-prompts", json=valid_prompt_payload())

    assert response.status_code == 409
    assert response.json()["code"] == "FRAME_INDEX_NOT_FOUND"


def test_can_create_valid_prompt(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)

    response = client.post("/api/projects/project-1/quiz-prompts", json=valid_prompt_payload())

    assert response.status_code == 200
    prompt = response.json()
    assert prompt["project_id"] == "project-1"
    assert prompt["prompt_id"]
    assert prompt["options"][1]["is_correct"] is True
    assert prompt["question_mode"] == "FREEZE_FRAME"
    assert prompt["time_limit_ms"] is None
    assert (tmp_path / "project-1" / "quiz_prompts.json").exists()


def test_create_prompt_keeps_context_and_source_track_links_separate(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_tracking(directory)
    payload = valid_prompt_payload()
    payload["source_track_ids"] = [" manual-track ", "manual-track"]
    payload["options"][0]["source_track_ids"] = [" track-1 ", "track-1"]

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 200
    prompt = response.json()
    assert prompt["context_track_ids"] == ["track-1"]
    assert prompt["source_track_ids"] == ["manual-track"]
    assert prompt["options"][0]["source_track_ids"] == ["track-1"]


def test_create_prompt_defaults_context_track_links_from_frame_tracking(client: TestClient, tmp_path: Path) -> None:
    directory = write_project(tmp_path)
    write_tracking(directory)

    response = client.post("/api/projects/project-1/quiz-prompts", json=valid_prompt_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_track_ids"] == ["track-1"]
    assert payload["source_track_ids"] == []


def test_can_list_prompts(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path)

    response = client.get("/api/projects/project-1/quiz-prompts")

    assert response.status_code == 200
    prompts = response.json()
    assert [item["prompt_id"] for item in prompts] == [prompt["prompt_id"]]


def test_can_filter_prompts_by_court_role_and_situation_type(client: TestClient, tmp_path: Path) -> None:
    first = create_prompt(client, tmp_path)
    second_payload = valid_prompt_payload()
    second_payload["court_role_target"] = "LOW_MAN"
    second_payload["situation_type"] = "LOW_MAN_DECISION"
    second = create_prompt(client, tmp_path, second_payload)

    role_response = client.get("/api/projects/project-1/quiz-prompts?court_role=LOW_MAN")
    situation_response = client.get("/api/projects/project-1/quiz-prompts?situation_type=PICK_AND_ROLL")
    combined_response = client.get("/api/projects/project-1/quiz-prompts?court_role=LOW_MAN&situation_type=PICK_AND_ROLL")

    assert role_response.status_code == 200
    assert [item["prompt_id"] for item in role_response.json()] == [second["prompt_id"]]
    assert situation_response.status_code == 200
    assert [item["prompt_id"] for item in situation_response.json()] == [first["prompt_id"]]
    assert combined_response.status_code == 200
    assert combined_response.json() == []


def test_can_fetch_prompt(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path)

    response = client.get(f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}")

    assert response.status_code == 200
    assert response.json()["prompt_id"] == prompt["prompt_id"]


def test_attempt_returns_correctness_and_explanations(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path)

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A"},
    )

    assert response.status_code == 200
    attempt = response.json()
    assert attempt == {
        "prompt_id": prompt["prompt_id"],
        "selected_option_id": "A",
        "correct_option_id": "C",
        "is_correct": False,
        "selected_expected_value": 0.82,
        "correct_expected_value": 1.18,
        "opportunity_cost": 0.36,
        "score": 28,
        "scoring_mode": "EXPECTED_VALUE",
        "selected_explanation": "Explanation for A",
        "correct_explanation": "Explanation for C",
        "selected_role_feedback": "Explanation for A",
        "correct_role_feedback": "Explanation for C",
        "summary_explanation": "Hit the cutter for the highest-value look.",
        "response_time_ms": None,
        "timed_out": False,
    }
    assert (tmp_path / "project-1" / "quiz_attempts.json").exists()


def test_attempt_returns_role_specific_feedback_for_user_role(client: TestClient, tmp_path: Path) -> None:
    payload = valid_prompt_payload()
    payload["options"][0]["role_feedback"] = {
        "player": "Next time, check the low man before committing to the drive.",
        "coach": "Use this as a skip-pass recognition drill.",
    }
    payload["options"][1]["role_feedback"] = {
        "player": "The cutter is available once the low man steps up.",
        "fan": "This is why the box score misses decision quality.",
    }
    prompt = create_prompt(client, tmp_path, payload)

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A", "user_role": "PLAYER"},
    )

    assert response.status_code == 200
    attempt = response.json()
    assert attempt["selected_role_feedback"] == "Next time, check the low man before committing to the drive."
    assert attempt["correct_role_feedback"] == "The cutter is available once the low man steps up."


def test_attempt_role_feedback_falls_back_to_explanation_when_missing(client: TestClient, tmp_path: Path) -> None:
    payload = valid_prompt_payload()
    payload["options"][0]["role_feedback"] = {"coach": "Use this as a skip-pass recognition drill."}
    prompt = create_prompt(client, tmp_path, payload)

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A", "user_role": "PLAYER"},
    )

    assert response.status_code == 200
    attempt = response.json()
    assert attempt["selected_role_feedback"] == "Explanation for A"
    assert attempt["correct_role_feedback"] == "Explanation for C"


def test_attempt_scores_with_expected_values(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path)

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A"},
    )

    assert response.status_code == 200
    attempt = response.json()
    assert attempt["opportunity_cost"] == 0.36
    assert attempt["score"] == 28
    assert attempt["scoring_mode"] == "EXPECTED_VALUE"


def test_attempt_scores_with_correctness_when_expected_values_missing(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path, valid_prompt_payload(expected_values=False))

    incorrect_response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A"},
    )
    correct_response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "C"},
    )

    assert incorrect_response.status_code == 200
    incorrect_attempt = incorrect_response.json()
    assert incorrect_attempt["opportunity_cost"] is None
    assert incorrect_attempt["score"] == 0
    assert incorrect_attempt["scoring_mode"] == "CORRECTNESS_ONLY"
    assert correct_response.status_code == 200
    correct_attempt = correct_response.json()
    assert correct_attempt["opportunity_cost"] is None
    assert correct_attempt["score"] == 100
    assert correct_attempt["scoring_mode"] == "CORRECTNESS_ONLY"


def test_attempt_opportunity_cost_cannot_be_negative(client: TestClient, tmp_path: Path) -> None:
    payload = valid_prompt_payload()
    payload["options"] = [
        option("A", expected_value=1.35),
        option("C", is_correct=True, expected_value=1.18),
    ]
    prompt = create_prompt(client, tmp_path, payload)

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A"},
    )

    assert response.status_code == 200
    attempt = response.json()
    assert attempt["opportunity_cost"] == 0
    assert attempt["score"] == 100
    assert attempt["scoring_mode"] == "EXPECTED_VALUE"


def test_quick_decision_prompt_requires_positive_time_limit(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload["question_mode"] = "QUICK_DECISION"

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_quick_decision_prompt_persists_time_limit(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload.update({"question_mode": "QUICK_DECISION", "time_limit_ms": 4500})

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 200
    prompt = response.json()
    assert prompt["question_mode"] == "QUICK_DECISION"
    assert prompt["time_limit_ms"] == 4500


def test_timeout_attempt_captures_timing_without_selected_option(client: TestClient, tmp_path: Path) -> None:
    payload = valid_prompt_payload()
    payload.update({"question_mode": "QUICK_DECISION", "time_limit_ms": 3000})
    prompt = create_prompt(client, tmp_path, payload)

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": None, "response_time_ms": 3000, "timed_out": True},
    )

    assert response.status_code == 200
    attempt = response.json()
    assert attempt["selected_option_id"] is None
    assert attempt["correct_option_id"] == "C"
    assert attempt["is_correct"] is False
    assert attempt["score"] == 0
    assert attempt["selected_explanation"] == "Time expired"
    assert attempt["selected_role_feedback"] == "Time expired"
    assert attempt["response_time_ms"] == 3000
    assert attempt["timed_out"] is True


def test_create_video_freeze_prompt_persists_playback_fields(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload.update(
        {
            "mode": "VIDEO_FREEZE",
            "video_asset_id": "video-1",
            "clip_start_seconds": 1.0,
            "freeze_frame_seconds": 2.8,
            "clip_end_seconds": 3.2,
        }
    )

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 200
    prompt = response.json()
    assert prompt["mode"] == "VIDEO_FREEZE"
    assert prompt["video_asset_id"] == "video-1"
    assert prompt["clip_start_seconds"] == 1.0
    assert prompt["freeze_frame_seconds"] == 2.8
    assert prompt["clip_end_seconds"] == 3.2


def test_video_freeze_prompt_rejects_clip_start_after_freeze(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)
    payload = valid_prompt_payload()
    payload.update({"mode": "VIDEO_FREEZE", "clip_start_seconds": 4.0, "freeze_frame_seconds": 2.8})

    response = client.post("/api/projects/project-1/quiz-prompts", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"
