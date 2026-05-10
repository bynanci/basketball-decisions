import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import (
    Detection,
    DetectionBox,
    PlayerTrack,
    Project,
    QuizAttemptRecord,
    QuizPrompt,
    RunTrackingRequest,
    RunTrackingResponse,
    SourceLicenseType,
    SourceType,
    TrackPoint,
    TrackReviewPatch,
    UsageScope,
    VideoSourceRecord,
)


def _write_source(directory: Path, project_id: str, *, allowed: bool = True) -> None:
    write_json_model(
        directory / project_id / "source.json",
        VideoSourceRecord(
            project_id=project_id,
            source_id=f"source-{project_id}",
            source_type=SourceType.UPLOAD,
            license_type=SourceLicenseType.OWNED if allowed else SourceLicenseType.YOUTUBE_REFERENCE_ONLY,
            rights_confirmed=allowed,
            allowed_for_training=allowed,
            allowed_for_local_storage=True,
            usage_scope=UsageScope.TRAINING if allowed else UsageScope.REFERENCE_ONLY,
        ),
    )


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


def _prompt(project_id: str = "curation-project") -> QuizPrompt:
    return QuizPrompt.model_validate(
        {
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
                _option("A", expected_value=0.72),
                _option("B", expected_value=1.12),
                _option("C", is_correct=True, expected_value=1.18),
            ],
            "explanation": "Hit the cutter for the highest-value look.",
        }
    )


def _attempt(project_id: str = "curation-project", **overrides) -> QuizAttemptRecord:
    payload = {
        "project_id": project_id,
        "attempt_id": "attempt-1",
        "prompt_id": "prompt-1",
        "selected_option_id": "A",
        "correct_option_id": "C",
        "is_correct": False,
        "selected_expected_value": 0.72,
        "correct_expected_value": 1.18,
        "opportunity_cost": 0.46,
        "score": 42,
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


def test_curate_recognition_dataset_writes_positive_and_negative_samples(client: TestClient, tmp_path: Path) -> None:
    project_id = "curation-project"
    project_dir = tmp_path / project_id
    write_json_model(project_dir / "project.json", Project(project_id=project_id, name="Curation"))
    _write_source(tmp_path, project_id)
    write_json_model(
        project_dir / "tracking.json",
        RunTrackingResponse(
            project_id=project_id,
            request=RunTrackingRequest(project_id=project_id),
            detections=[
                Detection(
                    detection_id="det-good",
                    frame_id="frame-1",
                    frame_index=1,
                    box=DetectionBox(x=1, y=2, width=3, height=4),
                    confidence=0.9,
                    track_id="track-good",
                ),
                Detection(
                    detection_id="det-bad",
                    frame_id="frame-1",
                    frame_index=1,
                    box=DetectionBox(x=5, y=6, width=7, height=8),
                    confidence=0.8,
                    track_id="track-bad",
                ),
            ],
            tracks=[
                PlayerTrack(
                    track_id="track-good",
                    points=[TrackPoint(frame_id="frame-1", frame_index=1, timestamp_seconds=0.1, image_point_x=2, image_point_y=4, detection_id="det-good")],
                ),
                PlayerTrack(
                    track_id="track-bad",
                    points=[TrackPoint(frame_id="frame-1", frame_index=1, timestamp_seconds=0.1, image_point_x=6, image_point_y=8, detection_id="det-bad")],
                ),
            ],
        ),
    )
    write_json_model(
        project_dir / "tracking_review_patch.json",
        TrackReviewPatch(excluded_detection_ids=["det-bad"], excluded_track_ids=["track-bad"]),
    )

    response = client.post("/api/local-lab/datasets/recognition/curate")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["positive_sample_count"] == 2
    assert manifest["negative_sample_count"] == 2
    assert manifest["label_distribution"] == {
        "FALSE_POSITIVE": 1,
        "FALSE_POSITIVE_TRACK": 1,
        "PLAYER": 1,
        "VALID_PLAYER_TRACK": 1,
    }
    samples = [json.loads(line) for line in (tmp_path / "datasets" / "recognition" / "curated_samples.jsonl").read_text().splitlines()]
    labels = [json.loads(line) for line in (tmp_path / "datasets" / "recognition" / "curated_labels.jsonl").read_text().splitlines()]
    assert {sample["project_id"] for sample in samples} == {project_id}
    assert all(sample["source"] in {"HEURISTIC", "TRACKING_REVIEW"} for sample in samples)
    assert all(sample["trace"]["source_trace"]["allowed_for_training"] is True for sample in samples)
    assert all(sample["trace"]["source_trace"]["source_id"] == f"source-{project_id}" for sample in samples)
    assert all(label["trace"]["source_trace"]["allowed_for_training"] is True for label in labels)


def test_curate_decision_dataset_labels_options_attempts_and_skips_reference_only(client: TestClient, tmp_path: Path) -> None:
    project_id = "curation-project"
    project_dir = tmp_path / project_id
    write_json_model(project_dir / "project.json", Project(project_id=project_id, name="Curation"))
    _write_source(tmp_path, project_id)
    (project_dir / "quiz_prompts.json").write_text(json.dumps([_prompt(project_id).model_dump(mode="json")]), encoding="utf-8")
    (project_dir / "quiz_attempts.json").write_text(
        json.dumps([_attempt(project_id).model_dump(mode="json"), _attempt(project_id, attempt_id="attempt-2", score=82).model_dump(mode="json")]),
        encoding="utf-8",
    )

    reference_id = "reference-project"
    write_json_model(tmp_path / reference_id / "project.json", Project(project_id=reference_id, name="Reference"))
    _write_source(tmp_path, reference_id, allowed=False)
    (tmp_path / reference_id / "quiz_prompts.json").write_text(json.dumps([_prompt(reference_id).model_dump(mode="json")]), encoding="utf-8")

    response = client.post("/api/local-lab/datasets/decision/curate")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["source_project_ids"] == [project_id]
    assert manifest["skipped_project_ids"] == [reference_id]
    assert manifest["label_distribution"] == {
        "BAD_DECISION": 1,
        "BAD_READ": 1,
        "GOOD_DECISION": 2,
        "GOOD_READ": 1,
    }
    assert manifest["positive_sample_count"] == 3
    assert manifest["negative_sample_count"] == 2
    samples = [json.loads(line) for line in (tmp_path / "datasets" / "decision" / "curated_samples.jsonl").read_text().splitlines()]
    assert all(sample["project_id"] == project_id for sample in samples)
    assert all(sample["trace"]["source_trace"]["allowed_for_training"] is True for sample in samples)
    assert all(sample["trace"]["source_trace"]["usage_scope"] == "TRAINING" for sample in samples)
