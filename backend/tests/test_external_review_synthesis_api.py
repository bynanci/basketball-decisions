from pathlib import Path

from fastapi.testclient import TestClient

from app.services import external_review_synthesis_service


def _payload() -> dict:
    return {
        "provider": "mock",
        "feedback_entries": [
            {"reviewer_id": "r1", "quote": "Release notes are unclear.", "rating": 2, "category": "documentation"},
            {"reviewer_id": "r2", "quote": "Performance dropped in Q4 flow.", "rating": 2, "category": "performance"},
            {"reviewer_id": "r3", "quote": "Release notes are unclear.", "rating": 3, "category": "documentation"},
        ],
        "created_by": "qa-reviewer",
    }


def test_mock_synthesis_is_deterministic_for_the_same_input(client: TestClient) -> None:
    response = client.post("/api/reviews/external-review/synthesize", json=_payload())
    assert response.status_code == 200
    payload = response.json()

    expected_theme_titles = ["Documentation Feedback", "Performance Feedback"]
    assert [theme["title"] for theme in payload["themes"]] == expected_theme_titles
    assert payload["draft_only"] is True
    assert payload["requires_human_approval"] is True
    assert payload["release_decision_automated"] is False


def test_quotes_are_source_preserved_and_ratings_unchanged(client: TestClient) -> None:
    request = _payload()
    response = client.post("/api/reviews/external-review/synthesize", json=request)
    assert response.status_code == 200
    payload = response.json()

    input_quotes = {entry["quote"] for entry in request["feedback_entries"]}
    output_quotes = {
        quote
        for theme in payload["themes"]
        for quote in theme["quote_evidence"]
    }
    assert output_quotes.issubset(input_quotes)

    assert payload["source_feedback_entries"] == request["feedback_entries"]


def test_unsupported_external_provider_returns_clear_error(client: TestClient) -> None:
    request = _payload()
    request["provider"] = "external"
    response = client.post("/api/reviews/external-review/synthesize", json=request)

    assert response.status_code == 400
    assert response.json()["code"] == "LLM_PROVIDER_UNSUPPORTED"


def test_artifact_is_saved_and_fetchable(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(external_review_synthesis_service, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(
        external_review_synthesis_service,
        "EXTERNAL_REVIEW_SYNTHESIS_DIR",
        tmp_path / "reviews" / "external_review_synthesis",
    )

    response = client.post("/api/reviews/external-review/synthesize", json=_payload())
    assert response.status_code == 200
    payload = response.json()

    artifact_path = Path(payload["json_path"])
    assert artifact_path.exists()

    fetched = client.get(f"/api/reviews/external-review/synthesis/{payload['synthesis_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["synthesis_id"] == payload["synthesis_id"]
