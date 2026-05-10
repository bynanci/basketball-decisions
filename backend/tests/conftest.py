from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import common, local_lab, projects, reference_videos, sources  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    monkeypatch.setattr(local_lab, "DATA_DIR", tmp_path)
    monkeypatch.setattr(local_lab, "DATASETS_DIR", tmp_path / "datasets")
    monkeypatch.setattr(sources, "SOURCE_REGISTRY_PATH", tmp_path / "source_registry.json")
    monkeypatch.setattr(reference_videos, "REFERENCE_VIDEO_DIR", tmp_path / "reference_videos")
    monkeypatch.setattr(reference_videos, "REFERENCE_VIDEOS_PATH", tmp_path / "reference_videos" / "reference_videos.json")
    monkeypatch.setattr(reference_videos, "BREAKDOWN_NOTES_PATH", tmp_path / "reference_videos" / "breakdown_notes.json")
    monkeypatch.setattr(reference_videos, "QUIZ_PROMPT_DRAFTS_PATH", tmp_path / "reference_videos" / "quiz_prompt_drafts.json")
    monkeypatch.setattr(reference_videos, "DECISION_RULE_DRAFTS_PATH", tmp_path / "reference_videos" / "decision_rule_drafts.json")
    return TestClient(app)
