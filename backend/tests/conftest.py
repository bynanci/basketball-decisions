from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api import common, decision_rules, local_lab, projects, reference_videos, review_queue, sources  # noqa: E402
from app.services import coach_report_service, drill_recommendation_service, practice_execution_service, practice_feedback_signal_service, practice_plan_service  # noqa: E402
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
    monkeypatch.setattr(coach_report_service, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(coach_report_service, "PROJECTS_DATA_DIR", tmp_path)
    monkeypatch.setattr(coach_report_service, "DATASETS_DIR", tmp_path / "datasets")
    monkeypatch.setattr(coach_report_service, "REPORTS_DIR", tmp_path / "reports" / "coach")
    monkeypatch.setattr(coach_report_service, "DECISION_RULES_DIR", tmp_path / "decision_rules")
    monkeypatch.setattr(coach_report_service, "REVIEW_QUEUE_DIR", tmp_path / "review_queue")
    monkeypatch.setattr(coach_report_service, "SOURCE_GOVERNANCE_DIR", tmp_path / "reference_videos")
    monkeypatch.setattr(coach_report_service, "SOURCE_REGISTRY_PATH", tmp_path / "source_registry.json")
    monkeypatch.setattr(coach_report_service, "REPORT_INDEX_PATH", tmp_path / "reports" / "coach" / "index.json")
    monkeypatch.setattr(drill_recommendation_service, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(drill_recommendation_service, "DATASETS_DIR", tmp_path / "datasets")
    monkeypatch.setattr(drill_recommendation_service, "REVIEW_QUEUE_DIR", tmp_path / "review_queue")
    monkeypatch.setattr(drill_recommendation_service, "DRILLS_DIR", tmp_path / "drills")
    monkeypatch.setattr(drill_recommendation_service, "CATALOG_PATH", BACKEND_ROOT / "app" / "data" / "drills" / "catalog.json")
    monkeypatch.setattr(drill_recommendation_service, "LATEST_RECOMMENDATIONS_PATH", tmp_path / "drills" / "latest_recommendations.json")
    monkeypatch.setattr(practice_plan_service, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(practice_plan_service, "PRACTICE_PLANS_DIR", tmp_path / "practice_plans")
    monkeypatch.setattr(practice_plan_service, "PRACTICE_PLAN_INDEX_PATH", tmp_path / "practice_plans" / "index.json")
    monkeypatch.setattr(practice_execution_service, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(practice_execution_service, "PRACTICE_EXECUTIONS_DIR", tmp_path / "practice_executions")
    monkeypatch.setattr(practice_execution_service, "PRACTICE_EXECUTION_INDEX_PATH", tmp_path / "practice_executions" / "index.json")
    monkeypatch.setattr(practice_feedback_signal_service, "APP_DATA_DIR", tmp_path)
    monkeypatch.setattr(practice_feedback_signal_service, "PRACTICE_EXECUTIONS_DIR", tmp_path / "practice_executions")
    monkeypatch.setattr(practice_feedback_signal_service, "PRACTICE_FEEDBACK_SIGNALS_PATH", tmp_path / "practice_executions" / "practice_feedback_signals.jsonl")
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
