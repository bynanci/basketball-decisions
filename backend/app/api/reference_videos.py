"""Reference-only video breakdown importer routes."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter
from pydantic import TypeAdapter, ValidationError

from app.api.common import api_error
from app.models import (
    CreateReferenceVideoRequest,
    DecisionRuleDraft,
    QuizPromptDraft,
    QuizPromptDraftOption,
    ReferenceBreakdownNote,
    ReferenceVideo,
    ReferenceVideoDraftSummary,
    ReferenceVideoListResponse,
    SourceLicenseType,
    SourceType,
    UpsertReferenceBreakdownNoteRequest,
    UsageScope,
)
from app.models.base import utc_now

router = APIRouter(prefix="/reference-videos", tags=["reference-videos"])

REFERENCE_VIDEO_DIR = Path(__file__).resolve().parents[1] / "data" / "reference_videos"
REFERENCE_VIDEOS_PATH = REFERENCE_VIDEO_DIR / "reference_videos.json"
BREAKDOWN_NOTES_PATH = REFERENCE_VIDEO_DIR / "breakdown_notes.json"
QUIZ_PROMPT_DRAFTS_PATH = REFERENCE_VIDEO_DIR / "quiz_prompt_drafts.json"
DECISION_RULE_DRAFTS_PATH = REFERENCE_VIDEO_DIR / "decision_rule_drafts.json"

_REFERENCE_VIDEO_ADAPTER = TypeAdapter(list[ReferenceVideo])
_BREAKDOWN_NOTE_ADAPTER = TypeAdapter(list[ReferenceBreakdownNote])
_QUIZ_DRAFT_ADAPTER = TypeAdapter(list[QuizPromptDraft])
_RULE_DRAFT_ADAPTER = TypeAdapter(list[DecisionRuleDraft])


def _read_list(path: Path, adapter):
    if not path.exists():
        return []
    try:
        return adapter.validate_json(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise api_error(
            422,
            "INVALID_REFERENCE_VIDEO_STORAGE",
            f"Reference video storage file '{path.name}' is invalid.",
            {"path": str(path), "error": str(exc)},
            "Fix or remove the invalid reference video JSON file, then retry.",
        ) from exc


def _write_list(path: Path, adapter, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(adapter.dump_json(rows, indent=2).decode("utf-8"), encoding="utf-8")


def _read_reference_videos() -> list[ReferenceVideo]:
    return _read_list(REFERENCE_VIDEOS_PATH, _REFERENCE_VIDEO_ADAPTER)


def _write_reference_videos(rows: list[ReferenceVideo]) -> None:
    _write_list(REFERENCE_VIDEOS_PATH, _REFERENCE_VIDEO_ADAPTER, rows)


def _read_notes() -> list[ReferenceBreakdownNote]:
    return _read_list(BREAKDOWN_NOTES_PATH, _BREAKDOWN_NOTE_ADAPTER)


def _write_notes(rows: list[ReferenceBreakdownNote]) -> None:
    _write_list(BREAKDOWN_NOTES_PATH, _BREAKDOWN_NOTE_ADAPTER, rows)


def _read_quiz_drafts() -> list[QuizPromptDraft]:
    return _read_list(QUIZ_PROMPT_DRAFTS_PATH, _QUIZ_DRAFT_ADAPTER)


def _write_quiz_drafts(rows: list[QuizPromptDraft]) -> None:
    _write_list(QUIZ_PROMPT_DRAFTS_PATH, _QUIZ_DRAFT_ADAPTER, rows)


def _read_rule_drafts() -> list[DecisionRuleDraft]:
    return _read_list(DECISION_RULE_DRAFTS_PATH, _RULE_DRAFT_ADAPTER)


def _write_rule_drafts(rows: list[DecisionRuleDraft]) -> None:
    _write_list(DECISION_RULE_DRAFTS_PATH, _RULE_DRAFT_ADAPTER, rows)


def _infer_source_type(url: str) -> SourceType:
    lowered = url.lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return SourceType.YOUTUBE
    return SourceType.URL


def _get_reference(reference_id: str) -> ReferenceVideo:
    for reference in _read_reference_videos():
        if reference.reference_id == reference_id:
            return reference
    raise api_error(
        404,
        "REFERENCE_VIDEO_NOT_FOUND",
        f"Reference video '{reference_id}' was not found.",
        {"reference_id": reference_id},
        "Create the reference video before adding notes or drafts.",
    )


def _get_note(reference_id: str, note_id: str) -> ReferenceBreakdownNote:
    for note in _read_notes():
        if note.reference_id == reference_id and note.note_id == note_id:
            return note
    raise api_error(
        404,
        "BREAKDOWN_NOTE_NOT_FOUND",
        f"Breakdown note '{note_id}' was not found for reference video '{reference_id}'.",
        {"reference_id": reference_id, "note_id": note_id},
        "Create the breakdown note before converting it into a draft.",
    )


def reference_video_summary() -> ReferenceVideoDraftSummary:
    reference_videos = _read_reference_videos()
    return ReferenceVideoDraftSummary(
        reference_only_source_count=sum(1 for video in reference_videos if video.usage_scope == UsageScope.REFERENCE_ONLY),
        quiz_prompt_draft_count=len(_read_quiz_drafts()),
        decision_rule_draft_count=len(_read_rule_drafts()),
    )


@router.get("", response_model=ReferenceVideoListResponse)
def list_reference_videos() -> ReferenceVideoListResponse:
    return ReferenceVideoListResponse(reference_videos=_read_reference_videos())


@router.post("", response_model=ReferenceVideo)
def create_reference_video(request: CreateReferenceVideoRequest) -> ReferenceVideo:
    inferred_source_type = _infer_source_type(request.url)
    source_type = SourceType.YOUTUBE if inferred_source_type == SourceType.YOUTUBE else request.source_type or SourceType.URL
    license_type = request.license_type or (SourceLicenseType.YOUTUBE_REFERENCE_ONLY if source_type == SourceType.YOUTUBE else SourceLicenseType.UNKNOWN)
    usage_scope = request.usage_scope or UsageScope.REFERENCE_ONLY
    allowed_for_training = bool(request.allowed_for_training) if request.allowed_for_training is not None else False
    if usage_scope == UsageScope.REFERENCE_ONLY and allowed_for_training:
        raise api_error(
            422,
            "REFERENCE_ONLY_TRAINING_BLOCKED",
            "Reference-only videos cannot be marked as training data.",
            {"usage_scope": usage_scope, "allowed_for_training": allowed_for_training},
            "Keep the reference as metadata and create approved training samples through source governance instead.",
        )
    now = utc_now()
    reference = ReferenceVideo(
        reference_id=f"ref-{uuid4().hex}",
        source_id=f"source-{uuid4().hex}",
        title=request.title,
        url=request.url,
        source_type=source_type,
        license_type=license_type,
        usage_scope=usage_scope,
        allowed_for_training=allowed_for_training,
        tags=request.tags,
        notes=request.notes,
        created_at=now,
        updated_at=now,
    )
    references = _read_reference_videos()
    references.append(reference)
    _write_reference_videos(references)
    return reference


@router.get("/{reference_id}/notes", response_model=list[ReferenceBreakdownNote])
def list_notes(reference_id: str) -> list[ReferenceBreakdownNote]:
    _get_reference(reference_id)
    return [note for note in _read_notes() if note.reference_id == reference_id]


@router.post("/{reference_id}/notes", response_model=ReferenceBreakdownNote)
def create_note(reference_id: str, request: UpsertReferenceBreakdownNoteRequest) -> ReferenceBreakdownNote:
    _get_reference(reference_id)
    now = utc_now()
    note = ReferenceBreakdownNote(
        note_id=f"note-{uuid4().hex}",
        reference_id=reference_id,
        created_at=now,
        updated_at=now,
        **request.model_dump(),
    )
    notes = _read_notes()
    notes.append(note)
    _write_notes(notes)
    return note


@router.put("/{reference_id}/notes/{note_id}", response_model=ReferenceBreakdownNote)
def update_note(reference_id: str, note_id: str, request: UpsertReferenceBreakdownNoteRequest) -> ReferenceBreakdownNote:
    _get_reference(reference_id)
    notes = _read_notes()
    for index, existing in enumerate(notes):
        if existing.reference_id == reference_id and existing.note_id == note_id:
            updated = ReferenceBreakdownNote(
                note_id=note_id,
                reference_id=reference_id,
                created_at=existing.created_at,
                updated_at=utc_now(),
                **request.model_dump(),
            )
            notes[index] = updated
            _write_notes(notes)
            return updated
    raise api_error(404, "BREAKDOWN_NOTE_NOT_FOUND", "Breakdown note was not found.", {"reference_id": reference_id, "note_id": note_id}, "Check the note ID and retry.")


@router.delete("/{reference_id}/notes/{note_id}", response_model=dict[str, str])
def delete_note(reference_id: str, note_id: str) -> dict[str, str]:
    _get_reference(reference_id)
    notes = _read_notes()
    remaining = [note for note in notes if not (note.reference_id == reference_id and note.note_id == note_id)]
    if len(remaining) == len(notes):
        raise api_error(404, "BREAKDOWN_NOTE_NOT_FOUND", "Breakdown note was not found.", {"reference_id": reference_id, "note_id": note_id}, "Check the note ID and retry.")
    _write_notes(remaining)
    return {"status": "deleted", "note_id": note_id}


@router.post("/{reference_id}/notes/{note_id}/quiz-draft", response_model=QuizPromptDraft)
def convert_note_to_quiz_draft(reference_id: str, note_id: str) -> QuizPromptDraft:
    _get_reference(reference_id)
    note = _get_note(reference_id, note_id)
    now = utc_now()
    draft = QuizPromptDraft(
        draft_id=f"quiz-draft-{uuid4().hex}",
        reference_id=reference_id,
        source_note_id=note_id,
        question=f"In this {note.situation_type}, what is the best read for the {note.court_role}?",
        court_role_target=note.court_role,
        situation_type=note.situation_type,
        role_instruction=f"You are the {note.court_role}. Read the situation and choose the best action.",
        options=[
            QuizPromptDraftOption(option_id="A", label=note.good_read, is_correct=True),
            QuizPromptDraftOption(option_id="B", label=note.bad_read, is_correct=False),
        ],
        explanation=note.coaching_cue,
        status="DRAFT",
        created_at=now,
        updated_at=now,
    )
    drafts = _read_quiz_drafts()
    drafts.append(draft)
    _write_quiz_drafts(drafts)
    return draft


@router.post("/{reference_id}/notes/{note_id}/rule-draft", response_model=DecisionRuleDraft)
def convert_note_to_rule_draft(reference_id: str, note_id: str) -> DecisionRuleDraft:
    _get_reference(reference_id)
    note = _get_note(reference_id, note_id)
    now = utc_now()
    draft = DecisionRuleDraft(
        draft_id=f"rule-draft-{uuid4().hex}",
        reference_id=reference_id,
        source_note_id=note_id,
        court_role=note.court_role,
        situation_type=note.situation_type,
        condition_text=note.concept,
        positive_cue=note.good_read,
        negative_cue=note.bad_read,
        suggested_weight=1.0,
        explanation=note.coaching_cue,
        status="DRAFT",
        created_at=now,
        updated_at=now,
    )
    drafts = _read_rule_drafts()
    drafts.append(draft)
    _write_rule_drafts(drafts)
    return draft


@router.get("/{reference_id}/quiz-drafts", response_model=list[QuizPromptDraft])
def list_quiz_drafts(reference_id: str) -> list[QuizPromptDraft]:
    _get_reference(reference_id)
    return [draft for draft in _read_quiz_drafts() if draft.reference_id == reference_id]


@router.get("/{reference_id}/rule-drafts", response_model=list[DecisionRuleDraft])
def list_rule_drafts(reference_id: str) -> list[DecisionRuleDraft]:
    _get_reference(reference_id)
    return [draft for draft in _read_rule_drafts() if draft.reference_id == reference_id]
