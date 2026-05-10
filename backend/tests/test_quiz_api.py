from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import common, projects
from app.api.common import write_json_model
from app.main import app
from app.models import ExtractFramesRequest, ExtractFramesResponse, FrameAsset, Project


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    return TestClient(app)


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


def test_can_create_valid_prompt(client: TestClient, tmp_path: Path) -> None:
    write_project(tmp_path)

    response = client.post("/api/projects/project-1/quiz-prompts", json=valid_prompt_payload())

    assert response.status_code == 200
    prompt = response.json()
    assert prompt["project_id"] == "project-1"
    assert prompt["prompt_id"]
    assert prompt["options"][1]["is_correct"] is True
    assert (tmp_path / "project-1" / "quiz_prompts.json").exists()


def test_can_list_prompts(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path)

    response = client.get("/api/projects/project-1/quiz-prompts")

    assert response.status_code == 200
    prompts = response.json()
    assert [item["prompt_id"] for item in prompts] == [prompt["prompt_id"]]


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
        "selected_explanation": "Explanation for A",
        "correct_explanation": "Explanation for C",
        "summary_explanation": "Hit the cutter for the highest-value look.",
    }
    assert (tmp_path / "project-1" / "quiz_attempts.json").exists()


def test_opportunity_cost_null_when_expected_values_missing(client: TestClient, tmp_path: Path) -> None:
    prompt = create_prompt(client, tmp_path, valid_prompt_payload(expected_values=False))

    response = client.post(
        f"/api/projects/project-1/quiz-prompts/{prompt['prompt_id']}/attempts",
        json={"selected_option_id": "A"},
    )

    assert response.status_code == 200
    assert response.json()["opportunity_cost"] is None
