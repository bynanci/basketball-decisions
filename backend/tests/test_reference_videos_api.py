from pathlib import Path

from fastapi.testclient import TestClient


def _create_reference(client: TestClient) -> dict:
    response = client.post(
        "/api/reference-videos",
        json={
            "title": "Teaching clip",
            "url": "https://www.youtube.com/watch?v=abc123",
            "tags": ["pnr", "read"],
            "notes": "Metadata only.",
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_note(client: TestClient, reference_id: str) -> dict:
    response = client.post(
        f"/api/reference-videos/{reference_id}/notes",
        json={
            "timestamp_sec": 42.5,
            "timestamp_label": "0:42",
            "court_role": "BALL_HANDLER",
            "situation_type": "PICK_AND_ROLL",
            "concept": "Tag defender is low and weak-side corner is lifted.",
            "good_read": "Hit the lifted weak-side shooter.",
            "bad_read": "Force a contested pull-up into the on-ball defender.",
            "coaching_cue": "See the low tag early and move the ball before the recovery.",
            "tags": ["tag", "skip"],
            "confidence": "HIGH",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_youtube_reference_defaults_to_reference_only(client: TestClient) -> None:
    reference = _create_reference(client)

    assert reference["source_type"] == "YOUTUBE"
    assert reference["license_type"] == "YOUTUBE_REFERENCE_ONLY"
    assert reference["usage_scope"] == "REFERENCE_ONLY"
    assert reference["allowed_for_training"] is False


def test_create_breakdown_note(client: TestClient) -> None:
    reference = _create_reference(client)
    note = _create_note(client, reference["reference_id"])

    assert note["reference_id"] == reference["reference_id"]
    assert note["court_role"] == "BALL_HANDLER"
    assert note["good_read"] == "Hit the lifted weak-side shooter."

    list_response = client.get(f"/api/reference-videos/{reference['reference_id']}/notes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_convert_note_to_quiz_draft(client: TestClient) -> None:
    reference = _create_reference(client)
    note = _create_note(client, reference["reference_id"])

    response = client.post(f"/api/reference-videos/{reference['reference_id']}/notes/{note['note_id']}/quiz-draft")

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "DRAFT"
    assert draft["question"] == "In this PICK_AND_ROLL, what is the best read for the BALL_HANDLER?"
    assert draft["role_instruction"] == "You are the BALL_HANDLER. Read the situation and choose the best action."
    assert draft["options"] == [
        {"option_id": "A", "label": "Hit the lifted weak-side shooter.", "is_correct": True},
        {"option_id": "B", "label": "Force a contested pull-up into the on-ball defender.", "is_correct": False},
    ]
    assert draft["explanation"] == "See the low tag early and move the ball before the recovery."


def test_convert_note_to_rule_draft(client: TestClient) -> None:
    reference = _create_reference(client)
    note = _create_note(client, reference["reference_id"])

    response = client.post(f"/api/reference-videos/{reference['reference_id']}/notes/{note['note_id']}/rule-draft")

    assert response.status_code == 200
    draft = response.json()
    assert draft["status"] == "DRAFT"
    assert draft["court_role"] == "BALL_HANDLER"
    assert draft["condition_text"] == "Tag defender is low and weak-side corner is lifted."
    assert draft["positive_cue"] == "Hit the lifted weak-side shooter."
    assert draft["negative_cue"] == "Force a contested pull-up into the on-ball defender."
    assert draft["suggested_weight"] == 1.0


def test_reference_only_drafts_do_not_appear_in_dataset_export(client: TestClient, tmp_path: Path) -> None:
    reference = _create_reference(client)
    note = _create_note(client, reference["reference_id"])
    assert client.post(f"/api/reference-videos/{reference['reference_id']}/notes/{note['note_id']}/quiz-draft").status_code == 200
    assert client.post(f"/api/reference-videos/{reference['reference_id']}/notes/{note['note_id']}/rule-draft").status_code == 200

    response = client.post("/api/local-lab/datasets/decision/export")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["sample_count"] == 0
    assert manifest["label_count"] == 0
    assert (tmp_path / "datasets" / "decision" / "samples.jsonl").read_text(encoding="utf-8") == ""
