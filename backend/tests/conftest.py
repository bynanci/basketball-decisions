from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import common, decision_rules, local_lab, projects, reference_videos, review_queue, sources  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    monkeypatch.setattr(local_lab, "DATA_DIR", tmp_path)
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    monkeypatch.setattr(review_queue, "DATA_DIR", tmp_path)
    monkeypatch.setattr(review_queue, "DATASETS_DIR", tmp_path / "datasets")
    monkeypatch.setattr(review_queue, "REVIEW_QUEUE_PATH", tmp_path / "review_queue.json")
    monkeypatch.setattr(review_queue, "REVIEW_ACTION_LOG_PATH", tmp_path / "review_queue" / "review_action_log.json")
    monkeypatch.setattr(review_queue, "DECISION_RULE_DRAFTS_PATH", tmp_path / "reference_videos" / "decision_rule_drafts.json")
    monkeypatch.setattr(local_lab, "RECOGNITION_MODELS_DIR", tmp_path / "models" / "recognition")
    monkeypatch.setattr(sources, "SOURCE_REGISTRY_PATH", tmp_path / "source_registry.json")
    monkeypatch.setattr(reference_videos, "REFERENCE_VIDEO_DIR", tmp_path / "reference_videos")
    monkeypatch.setattr(reference_videos, "REFERENCE_VIDEOS_PATH", tmp_path / "reference_videos" / "reference_videos.json")
    monkeypatch.setattr(reference_videos, "BREAKDOWN_NOTES_PATH", tmp_path / "reference_videos" / "breakdown_notes.json")
    monkeypatch.setattr(reference_videos, "QUIZ_PROMPT_DRAFTS_PATH", tmp_path / "reference_videos" / "quiz_prompt_drafts.json")
    monkeypatch.setattr(reference_videos, "DECISION_RULE_DRAFTS_PATH", tmp_path / "reference_videos" / "decision_rule_drafts.json")
    monkeypatch.setattr(decision_rules, "REFERENCE_VIDEO_DIR", tmp_path / "reference_videos")
    monkeypatch.setattr(decision_rules, "DECISION_RULE_DRAFTS_PATH", tmp_path / "reference_videos" / "decision_rule_drafts.json")
    monkeypatch.setattr(decision_rules, "DECISION_RULES_DIR", tmp_path / "decision_rules")
    monkeypatch.setattr(decision_rules, "RULE_SETS_PATH", tmp_path / "decision_rules" / "rule_sets.json")
    monkeypatch.setattr(decision_rules, "ACTIVE_RULE_SET_PATH", tmp_path / "decision_rules" / "active_rule_set.json")
    return TestClient(app)
