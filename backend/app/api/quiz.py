"""Decision Arrow Quiz MVP routes."""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter
from pydantic import TypeAdapter

from app.api.common import api_error, require_project_dir
from app.models import (
    CreateQuizPromptRequest,
    QuizAttemptRecord,
    QuizAttemptRequest,
    QuizAttemptResponse,
    QuizPrompt,
)
from app.models.base import utc_now
from app.models.video import ExtractFramesResponse

router = APIRouter(prefix="/projects/{project_id}/quiz-prompts", tags=["quiz"])
_PROMPTS_ADAPTER = TypeAdapter(list[QuizPrompt])
_ATTEMPTS_ADAPTER = TypeAdapter(list[QuizAttemptRecord])


def _prompts_path(project_id: str):
    return require_project_dir(project_id) / "quiz_prompts.json"


def _attempts_path(project_id: str):
    return require_project_dir(project_id) / "quiz_attempts.json"


def _read_prompts(project_id: str) -> list[QuizPrompt]:
    path = _prompts_path(project_id)
    if not path.exists():
        return []
    return _PROMPTS_ADAPTER.validate_json(path.read_text(encoding="utf-8"))


def _write_prompts(project_id: str, prompts: list[QuizPrompt]) -> None:
    path = _prompts_path(project_id)
    path.write_text(json.dumps([prompt.model_dump(mode="json") for prompt in prompts], indent=2), encoding="utf-8")


def _read_attempts(project_id: str) -> list[QuizAttemptRecord]:
    path = _attempts_path(project_id)
    if not path.exists():
        return []
    return _ATTEMPTS_ADAPTER.validate_json(path.read_text(encoding="utf-8"))


def _write_attempts(project_id: str, attempts: list[QuizAttemptRecord]) -> None:
    path = _attempts_path(project_id)
    path.write_text(json.dumps([attempt.model_dump(mode="json") for attempt in attempts], indent=2), encoding="utf-8")


def _find_prompt(project_id: str, prompt_id: str) -> QuizPrompt:
    prompt = next((item for item in _read_prompts(project_id) if item.prompt_id == prompt_id), None)
    if prompt is None:
        raise api_error(
            404,
            "QUIZ_PROMPT_NOT_FOUND",
            f"Quiz prompt '{prompt_id}' does not exist for project '{project_id}'.",
            {"project_id": project_id, "prompt_id": prompt_id},
            "Create a prompt first with POST /api/projects/{project_id}/quiz-prompts.",
        )
    return prompt


def _validate_frame_reference(project_id: str, payload: CreateQuizPromptRequest) -> None:
    directory = require_project_dir(project_id)
    index_path = directory / "frames" / "index.json"
    if not index_path.exists():
        return
    frame_index = ExtractFramesResponse.model_validate_json(index_path.read_text(encoding="utf-8"))
    frame = next((item for item in frame_index.frames if item.frame_index == payload.frame_index), None)
    if frame is None:
        raise api_error(
            404,
            "FRAME_NOT_FOUND",
            "Quiz prompt references a frame_index that was not extracted.",
            {"frame_index": payload.frame_index},
            "Use a frame listed in the project frame strip.",
        )
    if frame.frame_id != payload.frame_id:
        raise api_error(
            400,
            "FRAME_REFERENCE_MISMATCH",
            "frame_id does not match the extracted frame_index.",
            {"frame_id": payload.frame_id, "expected_frame_id": frame.frame_id, "frame_index": payload.frame_index},
            "Use the frame metadata returned by project hydration or frame extraction.",
        )


@router.get("", response_model=list[QuizPrompt])
def list_quiz_prompts(project_id: str) -> list[QuizPrompt]:
    return _read_prompts(project_id)


@router.post("", response_model=QuizPrompt)
def create_quiz_prompt(project_id: str, payload: CreateQuizPromptRequest) -> QuizPrompt:
    _validate_frame_reference(project_id, payload)
    now = utc_now()
    prompt = QuizPrompt(
        project_id=project_id,
        prompt_id=str(uuid4()),
        question=payload.question,
        frame_id=payload.frame_id,
        frame_index=payload.frame_index,
        timestamp_seconds=payload.timestamp_seconds,
        image_url=payload.image_url,
        image_path=payload.image_path,
        video_asset_id=payload.video_asset_id,
        clip_start_seconds=payload.clip_start_seconds,
        freeze_frame_seconds=payload.freeze_frame_seconds,
        clip_end_seconds=payload.clip_end_seconds,
        mode=payload.mode,
        options=payload.options,
        explanation=payload.explanation,
        created_at=now,
        updated_at=now,
    )
    prompts = _read_prompts(project_id)
    prompts.append(prompt)
    _write_prompts(project_id, prompts)
    return prompt


@router.get("/{prompt_id}", response_model=QuizPrompt)
def get_quiz_prompt(project_id: str, prompt_id: str) -> QuizPrompt:
    return _find_prompt(project_id, prompt_id)


@router.post("/{prompt_id}/attempts", response_model=QuizAttemptResponse)
def submit_quiz_attempt(project_id: str, prompt_id: str, payload: QuizAttemptRequest) -> QuizAttemptResponse:
    prompt = _find_prompt(project_id, prompt_id)
    selected = next((option for option in prompt.options if option.option_id == payload.selected_option_id), None)
    if selected is None:
        raise api_error(
            400,
            "QUIZ_OPTION_NOT_FOUND",
            "Selected option was not found on this quiz prompt.",
            {"selected_option_id": payload.selected_option_id, "prompt_id": prompt_id},
            "Submit one of the option_id values returned with the prompt.",
        )
    correct = next(option for option in prompt.options if option.is_correct)
    expected_values = [option.expected_value for option in prompt.options]
    has_expected_values = all(value is not None for value in expected_values)
    opportunity_cost = None
    if has_expected_values and selected.expected_value is not None:
        best_expected_value = max(value for value in expected_values if value is not None)
        opportunity_cost = round(max(0.0, best_expected_value - selected.expected_value), 4)
        score = max(0, round(100 - opportunity_cost * 200))
        scoring_mode = "EXPECTED_VALUE"
    else:
        score = 100 if selected.option_id == correct.option_id else 0
        scoring_mode = "CORRECTNESS_ONLY"

    response = QuizAttemptResponse(
        prompt_id=prompt.prompt_id,
        selected_option_id=selected.option_id,
        correct_option_id=correct.option_id,
        is_correct=selected.option_id == correct.option_id,
        selected_expected_value=selected.expected_value,
        correct_expected_value=correct.expected_value,
        opportunity_cost=opportunity_cost,
        score=score,
        scoring_mode=scoring_mode,
        selected_explanation=selected.explanation,
        correct_explanation=correct.explanation,
        summary_explanation=prompt.explanation,
    )
    attempts = _read_attempts(project_id)
    attempts.append(QuizAttemptRecord(project_id=project_id, attempt_id=str(uuid4()), **response.model_dump()))
    _write_attempts(project_id, attempts)
    return response
