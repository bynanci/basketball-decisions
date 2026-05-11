import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.common import write_json_model
from app.models import (
    DecisionDiagnosticsGlobalSummary,
    DecisionDiagnosticsReport,
    DecisionEvent,
    DecisionPromptDiagnostics,
    DecisionRuleDraft,
    Detection,
    DetectionBox,
    PlayerTrack,
    PlayerValueBuildResponse,
    PlayerValueSummary,
    PlayerValueTrace,
    Project,
    RunTrackingRequest,
    RunTrackingResponse,
    TrackPoint,
)


def _write_project(tmp_path: Path, project_id: str = "project-1") -> Path:
    directory = tmp_path / project_id
    write_json_model(directory / "project.json", Project(project_id=project_id, name="Review queue test"))
    return directory


def _write_recognition_artifacts(directory: Path, project_id: str = "project-1") -> None:
    detection = Detection(
        detection_id="det-low-confidence",
        frame_id="frame-1",
        frame_index=1,
        box=DetectionBox(x=100, y=100, width=20, height=40),
        confidence=0.2,
        class_name="person",
        track_id="track-short",
    )
    track = PlayerTrack(
        track_id="track-short",
        points=[TrackPoint(frame_id="frame-1", frame_index=1, timestamp_seconds=0.1, image_point_x=110, image_point_y=140, detection_id="det-low-confidence", confidence=0.2)],
    )
    write_json_model(
        directory / "tracking.json",
        RunTrackingResponse(project_id=project_id, request=RunTrackingRequest(project_id=project_id), detections=[detection], tracks=[track]),
    )


def _write_diagnostics(tmp_path: Path) -> None:
    report = DecisionDiagnosticsReport(
        prompt_diagnostics=[
            DecisionPromptDiagnostics(
                prompt_id="prompt-label-issue",
                project_id="project-1",
                court_role_target="BALL_HANDLER",
                situation_type="PICK_AND_ROLL",
                question_mode="FREEZE_FRAME",
                attempt_count=5,
                correct_rate=0.1,
                avg_score=20,
                avg_role_adjusted_score=25,
                avg_opportunity_cost=0.7,
                timeout_rate=0.0,
                most_selected_wrong_option_id="B",
                difficulty="TOO_HARD",
                suspected_label_issue=True,
                reasons=["Suspected label issue from tests."],
            )
        ],
        role_diagnostics=[],
        situation_diagnostics=[],
        global_summary=DecisionDiagnosticsGlobalSummary(
            prompt_count=1,
            attempt_count=5,
            too_easy_count=0,
            too_hard_count=1,
            balanced_count=0,
            insufficient_data_count=0,
            suspected_label_issue_count=1,
            high_cost_prompt_count=1,
            time_pressure_prompt_count=0,
        ),
    )
    write_json_model(tmp_path / "datasets" / "decision" / "decision_diagnostics.json", report)


def _write_decision_events(tmp_path: Path) -> None:
    event = DecisionEvent(
        project_id="project-1",
        prompt_id="prompt-label-issue",
        attempt_id="attempt-high-cost",
        frame_id="frame-1",
        frame_index=1,
        user_role="PLAYER",
        court_role_target="BALL_HANDLER",
        situation_type="PICK_AND_ROLL",
        question_mode="FREEZE_FRAME",
        selected_option_id="B",
        correct_option_id="A",
        is_correct=False,
        selected_expected_value=0.2,
        best_expected_value=1.0,
        opportunity_cost=0.8,
        raw_score=0,
        role_adjusted_score=0,
        response_time_ms=1000,
        timed_out=False,
        evaluation_source="MANUAL_EXPECTED_VALUE",
        explanations=["High cost attempt."],
    )
    path = tmp_path / "datasets" / "player_value" / "player_decision_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(event.model_dump_json() + "\n", encoding="utf-8")


def _write_player_value(tmp_path: Path) -> None:
    response = PlayerValueBuildResponse(
        summaries=[
            PlayerValueSummary(
                project_id="project-1",
                player_key="UNKNOWN",
                track_ids=["track-short"],
                decision_event_count=1,
                avg_raw_decision_score=0,
                avg_role_adjusted_score=0,
                avg_opportunity_cost=0.8,
                correct_rate=0,
                timeout_rate=0,
                recognition_reliability_score=50,
                consistency_score=50,
                improvement_score=50,
                participation_score=50,
                player_value_score=25,
                confidence=0.2,
                warnings=["Identity is UNKNOWN; no real or inferred player name is claimed."],
                trace=PlayerValueTrace(project_ids=["project-1"], track_ids=["track-short"], decision_event_ids=["project-1:prompt-label-issue:attempt-high-cost"], prompt_ids=["prompt-label-issue"]),
            )
        ]
    )
    write_json_model(tmp_path / "datasets" / "player_value" / "player_value_summary.json", response)


def _write_rule_drafts(tmp_path: Path) -> None:
    draft = DecisionRuleDraft(
        draft_id="draft-1",
        reference_id="ref-1",
        source_note_id="note-1",
        court_role="BALL_HANDLER",
        situation_type="PICK_AND_ROLL",
        condition_text="If the tagger is late, pass to the roller.",
        positive_cue="Hit the roller",
        negative_cue="Dribble into help",
        explanation="Reference-derived rule.",
    )
    path = tmp_path / "reference_videos" / "decision_rule_drafts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([draft.model_dump(mode="json")]), encoding="utf-8")


def test_generate_review_queue_from_all_sources(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    _write_diagnostics(tmp_path)
    _write_decision_events(tmp_path)
    _write_player_value(tmp_path)
    _write_rule_drafts(tmp_path)

    response = client.post("/api/review-queue/generate")

    assert response.status_code == 200
    payload = response.json()
    item_types = {item["item_type"] for item in payload["items"]}
    assert "RECOGNITION_TRACK" in item_types
    assert "RECOGNITION_DETECTION" in item_types
    assert "DECISION_PROMPT" in item_types
    assert "DECISION_ATTEMPT" in item_types
    assert "PLAYER_VALUE_ATTRIBUTION" in item_types
    assert "RULE_DRAFT" in item_types
    assert payload["open_count"] == payload["generated_count"]


def test_resolve_and_dismiss_review_queue_items_without_mutating_sources(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    _write_diagnostics(tmp_path)
    source_tracking_before = (directory / "tracking.json").read_text(encoding="utf-8")

    generated = client.post("/api/review-queue/generate").json()
    item_id = generated["items"][0]["item_id"]

    resolved = client.put(f"/api/review-queue/{item_id}", json={"status": "RESOLVED"})

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolved_at"] is not None
    assert (directory / "tracking.json").read_text(encoding="utf-8") == source_tracking_before

    regenerated = client.post("/api/review-queue/generate")
    persisted = next(item for item in regenerated.json()["items"] if item["item_id"] == item_id)
    assert persisted["status"] == "RESOLVED"
