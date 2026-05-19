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


def _item_by_type(payload: dict, item_type: str) -> dict:
    return next(item for item in payload["items"] if item["item_type"] == item_type)


def test_allowed_actions_are_returned_for_review_queue_items(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    _write_diagnostics(tmp_path)
    _write_decision_events(tmp_path)
    _write_player_value(tmp_path)
    _write_rule_drafts(tmp_path)

    payload = client.post("/api/review-queue/generate").json()

    assert "MARK_TRACK_FALSE_POSITIVE" in _item_by_type(payload, "RECOGNITION_TRACK")["allowed_actions"]
    assert "FLAG_PROMPT_LABEL_ISSUE" in _item_by_type(payload, "DECISION_PROMPT")["allowed_actions"]
    assert "MARK_ATTEMPT_TEACHING_CASE" in _item_by_type(payload, "DECISION_ATTEMPT")["allowed_actions"]
    assert "APPROVE_RULE_DRAFT" in _item_by_type(payload, "RULE_DRAFT")["allowed_actions"]
    assert "DISMISS_WITH_NOTE" in _item_by_type(payload, "PLAYER_VALUE_ATTRIBUTION")["allowed_actions"]


def test_mark_track_false_positive_updates_review_patch_and_logs_action(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    generated = client.post("/api/review-queue/generate").json()
    item = _item_by_type(generated, "RECOGNITION_TRACK")
    source_tracking_before = (directory / "tracking.json").read_text(encoding="utf-8")

    response = client.post(f"/api/review-queue/{item['item_id']}/actions", json={"action_type": "MARK_TRACK_FALSE_POSITIVE", "note": "not a player", "payload": {}})

    assert response.status_code == 200
    assert response.json()["item"]["status"] == "RESOLVED"
    patch = json.loads((directory / "tracking_review_patch.json").read_text(encoding="utf-8"))
    assert item["track_id"] in patch["excluded_track_ids"]
    assert (directory / "tracking.json").read_text(encoding="utf-8") == source_tracking_before
    actions = client.get("/api/review-queue/actions", params={"item_id": item["item_id"]}).json()
    assert actions[0]["action_type"] == "MARK_TRACK_FALSE_POSITIVE"
    assert actions[0]["status"] == "APPLIED"


def test_assign_track_to_player_alias_creates_updates_and_rejects_overlaps(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    generated = client.post("/api/review-queue/generate").json()
    item = _item_by_type(generated, "RECOGNITION_TRACK")

    created = client.post(
        f"/api/review-queue/{item['item_id']}/actions",
        json={"action_type": "ASSIGN_TRACK_TO_PLAYER_ALIAS", "note": "assign", "payload": {"player_key": "P1", "track_ids": [item["track_id"]], "team_side": "UNKNOWN"}},
    )

    assert created.status_code == 200
    aliases = json.loads((directory / "player_aliases.json").read_text(encoding="utf-8"))
    assert aliases["aliases"][0]["player_key"] == "P1"
    assert item["track_id"] in aliases["aliases"][0]["track_ids"]

    # Reopen only the queue item so a second explicit action can be attempted.
    client.put(f"/api/review-queue/{item['item_id']}", json={"status": "OPEN"})
    rejected = client.post(
        f"/api/review-queue/{item['item_id']}/actions",
        json={"action_type": "ASSIGN_TRACK_TO_PLAYER_ALIAS", "payload": {"player_key": "P2", "track_ids": [item["track_id"]]}},
    )
    assert rejected.status_code == 409
    actions = client.get("/api/review-queue/actions", params={"item_id": item["item_id"]}).json()
    assert [action["status"] for action in actions] == ["APPLIED", "FAILED"]


def test_prompt_label_issue_and_teaching_case_artifacts_are_written(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_diagnostics(tmp_path)
    _write_decision_events(tmp_path)
    generated = client.post("/api/review-queue/generate").json()
    prompt_item = _item_by_type(generated, "DECISION_PROMPT")
    attempt_item = _item_by_type(generated, "DECISION_ATTEMPT")

    prompt_response = client.post(
        f"/api/review-queue/{prompt_item['item_id']}/actions",
        json={"action_type": "FLAG_PROMPT_LABEL_ISSUE", "note": "label appears reversed", "payload": {"reason": "manual review"}},
    )
    attempt_response = client.post(
        f"/api/review-queue/{attempt_item['item_id']}/actions",
        json={"action_type": "MARK_ATTEMPT_TEACHING_CASE", "note": "good film room example", "payload": {}},
    )

    assert prompt_response.status_code == 200
    assert attempt_response.status_code == 200
    prompt_notes = json.loads((directory / "prompt_review_notes.json").read_text(encoding="utf-8"))
    teaching_cases = json.loads((directory / "teaching_cases.json").read_text(encoding="utf-8"))
    assert prompt_notes[0]["prompt_id"] == "prompt-label-issue"
    assert teaching_cases[0]["attempt_id"] == "attempt-high-cost"


def test_rule_draft_approve_and_dismiss_with_note(client: TestClient, tmp_path: Path) -> None:
    _write_project(tmp_path)
    _write_diagnostics(tmp_path)
    _write_rule_drafts(tmp_path)
    generated = client.post("/api/review-queue/generate").json()
    rule_item = _item_by_type(generated, "RULE_DRAFT")
    prompt_item = _item_by_type(generated, "DECISION_PROMPT")

    approved = client.post(f"/api/review-queue/{rule_item['item_id']}/actions", json={"action_type": "APPROVE_RULE_DRAFT", "payload": {"approved_by": "tester"}})
    missing_note = client.post(f"/api/review-queue/{prompt_item['item_id']}/actions", json={"action_type": "DISMISS_WITH_NOTE", "payload": {}})
    dismissed = client.post(f"/api/review-queue/{prompt_item['item_id']}/actions", json={"action_type": "DISMISS_WITH_NOTE", "note": "duplicate", "payload": {}})

    assert approved.status_code == 200
    assert approved.json()["item"]["status"] == "RESOLVED"
    drafts = json.loads((tmp_path / "reference_videos" / "decision_rule_drafts.json").read_text(encoding="utf-8"))
    assert drafts[0]["status"] == "APPROVED"
    rule_sets = json.loads((tmp_path / "decision_rules" / "rule_sets.json").read_text(encoding="utf-8"))
    assert rule_sets[0]["rules"][0]["source_draft_id"] == "draft-1"
    assert missing_note.status_code == 422
    assert dismissed.status_code == 200
    assert dismissed.json()["item"]["status"] == "DISMISSED"

def test_batch_dismiss_with_note_and_without_note(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    payload = client.post('/api/review-queue/generate').json()
    item_ids = [item['item_id'] for item in payload['items'][:1]]

    missing = client.post('/api/review-queue/batch-actions', json={'item_ids': item_ids, 'action_type': 'DISMISS_WITH_NOTE', 'payload': {}})
    assert missing.status_code == 422

    ok = client.post('/api/review-queue/batch-actions', json={'item_ids': item_ids, 'action_type': 'DISMISS_WITH_NOTE', 'note': 'duplicate', 'payload': {}})
    assert ok.status_code == 200
    assert ok.json()['succeeded_count'] == 1


def test_batch_unsafe_rejected_and_partial_success(client: TestClient, tmp_path: Path) -> None:
    directory = _write_project(tmp_path)
    _write_recognition_artifacts(directory)
    payload = client.post('/api/review-queue/generate').json()
    item = _item_by_type(payload, 'RECOGNITION_TRACK')

    unsafe = client.post('/api/review-queue/batch-actions', json={'item_ids': [item['item_id']], 'action_type': 'ASSIGN_TRACK_TO_PLAYER_ALIAS', 'payload': {}})
    assert unsafe.status_code == 400

    before_tracking = (directory / 'tracking.json').read_text(encoding='utf-8')
    mixed = client.post('/api/review-queue/batch-actions', json={'item_ids': [item['item_id'], 'missing-item'], 'action_type': 'MARK_TRACK_FALSE_POSITIVE', 'payload': {}})
    assert mixed.status_code == 200
    assert mixed.json()['succeeded_count'] == 1
    assert mixed.json()['failed_count'] == 1
    assert any(result['success'] is False for result in mixed.json()['results'])
    actions = client.get('/api/review-queue/actions', params={'item_id': item['item_id']}).json()
    assert actions[0]['status'] == 'APPLIED'
    assert (directory / 'tracking.json').read_text(encoding='utf-8') == before_tracking
