from fastapi.testclient import TestClient


def _create_rule_draft(client: TestClient) -> dict:
    reference = client.post(
        "/api/reference-videos",
        json={"title": "Teaching clip", "url": "https://www.youtube.com/watch?v=abc123"},
    ).json()
    note = client.post(
        f"/api/reference-videos/{reference['reference_id']}/notes",
        json={
            "court_role": "BALL_HANDLER",
            "situation_type": "PICK_AND_ROLL",
            "concept": "Low tag leaves weak-side shooter open.",
            "good_read": "Skip to the weak-side shooter.",
            "bad_read": "Drive into the low tag.",
            "coaching_cue": "Read the tag before the second dribble.",
            "confidence": "HIGH",
        },
    ).json()
    response = client.post(f"/api/reference-videos/{reference['reference_id']}/notes/{note['note_id']}/rule-draft")
    assert response.status_code == 200
    return response.json()


def test_approve_rule_draft_adds_rule_to_active_rule_set(client: TestClient) -> None:
    draft = _create_rule_draft(client)

    response = client.post(f"/api/decision-rules/drafts/{draft['draft_id']}/approve", json={"approved_by": "coach"})

    assert response.status_code == 200
    rule = response.json()
    assert rule["source_draft_id"] == draft["draft_id"]
    assert rule["condition_text"] == draft["condition_text"]
    assert rule["positive_cue"] == draft["positive_cue"]
    assert rule["negative_cue"] == draft["negative_cue"]
    assert rule["weight"] == draft["suggested_weight"]
    assert rule["status"] == "ACTIVE"
    assert rule["approved_by"] == "coach"

    rule_sets = client.get("/api/decision-rules/rule-sets").json()
    active_rule_set = rule_sets["active_rule_set"]
    assert active_rule_set["active"] is True
    assert active_rule_set["rules"][0]["rule_id"] == rule["rule_id"]

    drafts = client.get("/api/decision-rules/drafts").json()
    assert drafts[0]["status"] == "APPROVED"


def test_rule_can_be_disabled(client: TestClient) -> None:
    draft = _create_rule_draft(client)
    rule = client.post(f"/api/decision-rules/drafts/{draft['draft_id']}/approve", json={}).json()

    response = client.put(f"/api/decision-rules/rules/{rule['rule_id']}", json={"status": "DISABLED"})

    assert response.status_code == 200
    assert response.json()["status"] == "DISABLED"
    active_rule_set = client.get("/api/decision-rules/rule-sets").json()["active_rule_set"]
    assert active_rule_set["rules"][0]["status"] == "DISABLED"


def test_can_create_and_activate_rule_set(client: TestClient) -> None:
    first = client.post("/api/decision-rules/rule-sets", json={"name": "Experimental rules", "version": 2})
    second = client.post("/api/decision-rules/rule-sets", json={"name": "Game rules", "active": True})
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.put(f"/api/decision-rules/rule-sets/{first.json()['rule_set_id']}/activate")

    assert response.status_code == 200
    assert response.json()["active"] is True
    rule_sets = client.get("/api/decision-rules/rule-sets").json()
    assert rule_sets["active_rule_set"]["rule_set_id"] == first.json()["rule_set_id"]
    assert sum(1 for rule_set in rule_sets["rule_sets"] if rule_set["active"]) == 1


def test_rejected_draft_does_not_create_rule(client: TestClient) -> None:
    draft = _create_rule_draft(client)

    response = client.post(f"/api/decision-rules/drafts/{draft['draft_id']}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert client.get("/api/decision-rules/rule-sets").json()["active_rule_set"] is None
