"""Deterministic local sample project seeding utilities."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.api.common import DATA_DIR, api_error
from app.models.sample_data import (
    SAMPLE_PROJECT_ID,
    SAMPLE_PROJECT_NAME,
    SampleDataArtifactStatus,
    SampleDataMutationResponse,
    SampleDataStatusResponse,
)

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAMPLE_CREATED_AT = "2026-01-15T12:00:00Z"
SAMPLE_UPDATED_AT = "2026-01-15T12:00:00Z"
SAMPLE_MARKER = {"is_sample_data": True, "sample_project_id": SAMPLE_PROJECT_ID}


def _project_dir() -> Path:
    return DATA_DIR / SAMPLE_PROJECT_ID


def _app_data_dir() -> Path:
    return APP_DATA_DIR


def _quick_links() -> list[dict[str, str]]:
    pid = SAMPLE_PROJECT_ID
    return [
        {"label": "Open sample project", "href": f"/projects/{pid}"},
        {"label": "Review sample tracking", "href": f"/projects/{pid}/tracking-review"},
        {"label": "Try sample quiz", "href": "/training"},
        {"label": "Player Value", "href": "/player-value"},
        {"label": "Practice plan", "href": "/practice-plans"},
        {"label": "Coach report", "href": "/coach-reports"},
        {"label": "Workflow", "href": "/workflows"},
    ]


def _artifact_paths() -> dict[str, Path]:
    project = _project_dir()
    app_data = _app_data_dir()
    return {
        "project": project / "project.json",
        "source": project / "source.json",
        "video": project / "video.json",
        "frames": project / "frames" / "index.json",
        "frame_0": project / "frames" / "images" / "sample-frame-000.svg",
        "calibration": project / "calibration.json",
        "tracking": project / "tracking.json",
        "tracking_cleaned": project / "tracking_cleaned.json",
        "projected_tracks": project / "projected_tracks.json",
        "projected_tracks_cleaned": project / "projected_tracks_cleaned.json",
        "tracking_review_patch": project / "tracking_review_patch.json",
        "player_aliases": project / "player_aliases.json",
        "quiz_prompts": project / "quiz_prompts.json",
        "quiz_attempts": project / "quiz_attempts.json",
        "decision_events": app_data / "datasets" / "player_value" / "player_decision_events.jsonl",
        "player_value_summary": app_data / "datasets" / "player_value" / "player_value_summary.json",
        "player_value_build_index": app_data / "datasets" / "player_value" / "player_value_build_index.json",
        "player_value_build_snapshot": app_data / "datasets" / "player_value" / "builds" / "sample-pnr-build.json",
        "drill_recommendations": app_data / "drills" / "latest_recommendations.json",
        "practice_plan_index": app_data / "practice_plans" / "index.json",
        "practice_plan": app_data / "practice_plans" / "sample-pnr-plan.json",
        "practice_plan_markdown": app_data / "practice_plans" / "sample-pnr-plan.md",
        "practice_execution_index": app_data / "practice_executions" / "index.json",
        "practice_execution": app_data / "practice_executions" / "sample-pnr-execution.json",
        "feedback_signals": app_data / "practice_executions" / "practice_feedback_signals.jsonl",
        "coach_report_index": app_data / "reports" / "coach" / "index.json",
        "coach_report": app_data / "reports" / "coach" / "sample-pnr-report.json",
        "coach_report_markdown": app_data / "reports" / "coach" / "sample-pnr-report.md",
        "workflow_index": app_data / "workflows" / "index.json",
        "workflow": app_data / "workflows" / "workflow-sample-pnr.json",
        "review_queue": app_data / "review_queue" / "review_queue.json",
        "review_action_log": app_data / "review_queue" / "review_action_log.json",
    }


def _contains_sample_marker(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("is_sample_data") is True or value.get("sample_project_id") == SAMPLE_PROJECT_ID:
            return True
        return any(_contains_sample_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_sample_marker(item) for item in value)
    return False


def _is_sample_payload(path: Path) -> bool:
    if not path.exists():
        return True
    text = path.read_text(encoding="utf-8", errors="ignore")
    if SAMPLE_PROJECT_ID not in text:
        return False
    if path.suffix == ".jsonl":
        try:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError:
            return False
        return bool(rows) and all(_contains_sample_marker(row) for row in rows)
    try:
        return _contains_sample_marker(json.loads(text))
    except json.JSONDecodeError:
        return False


def _can_replace(paths: dict[str, Path]) -> bool:
    project_json = paths["project"]
    if not project_json.exists():
        return True
    return _is_sample_payload(project_json)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _sample_decision_event() -> dict[str, Any]:
    return {
        "project_id": SAMPLE_PROJECT_ID,
        "prompt_id": "sample-pnr-prompt-1",
        "attempt_id": "sample-attempt-1",
        "frame_id": "sample-frame-001",
        "frame_index": 1,
        "user_role": "PLAYER",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "question_mode": "ROLE_READ",
        "selected_option_id": "force-pocket",
        "correct_option_id": "skip-corner",
        "is_correct": False,
        "selected_expected_value": 0.62,
        "best_expected_value": 1.12,
        "opportunity_cost": 0.5,
        "raw_score": 55,
        "role_adjusted_score": 55,
        "decision_engine_version": "sample-v1",
        "base_score": 55.0,
        "rule_score_delta": 0.0,
        "final_score": 55.0,
        "score_capped": False,
        "response_time_ms": 4200,
        "timed_out": False,
        "evaluation_source": "MANUAL_EXPECTED_VALUE",
        "context_track_ids": ["track-ball-handler", "track-screener", "track-tag-defender"],
        "source_track_ids": ["track-ball-handler"],
        "explanations": ["Synthetic local sample; no training or model generation performed."],
        "created_at": SAMPLE_CREATED_AT,
        "debug_metadata": SAMPLE_MARKER,
    }

def _sample_project_payloads(paths: dict[str, Path]) -> dict[Path, Any]:
    pid = SAMPLE_PROJECT_ID
    video_id = "sample-pnr-synthetic-video"
    frames = [
        {"frame_id": "sample-frame-000", "frame_index": 0, "timestamp_seconds": 4.0, "image_path": str(paths["frame_0"]), "width": 1280, "height": 720, "metadata": {"sample_note": "Synthetic SVG frame; no external or copyrighted footage."}},
        {"frame_id": "sample-frame-001", "frame_index": 1, "timestamp_seconds": 5.0, "image_path": str(paths["frame_0"]), "width": 1280, "height": 720, "metadata": {"sample_note": "Reuses synthetic SVG frame for local demo."}},
        {"frame_id": "sample-frame-002", "frame_index": 2, "timestamp_seconds": 6.0, "image_path": str(paths["frame_0"]), "width": 1280, "height": 720, "metadata": {"sample_note": "Reuses synthetic SVG frame for local demo."}},
    ]
    detections = []
    tracks = []
    cleaned_tracks = []
    aliases = [
        ("track-ball-handler", "player-sample-guard", "Sample Guard", "HOME", "PRIMARY_BALL_HANDLER"),
        ("track-screener", "player-sample-screener", "Sample Screener", "HOME", "SCREENER"),
        ("track-tag-defender", "player-sample-tag", "Sample Tag Defender", "AWAY", "LOW_MAN"),
    ]
    base_points = {
        "track-ball-handler": [(435, 410, 0.82), (475, 395, 0.84), (520, 382, 0.86)],
        "track-screener": [(610, 380, 0.81), (625, 370, 0.83), (645, 360, 0.85)],
        "track-tag-defender": [(755, 455, 0.78), (735, 440, 0.8), (710, 425, 0.82)],
    }
    court_points = {
        "track-ball-handler": [(27.5, 25.5), (30.0, 24.5), (32.5, 23.5)],
        "track-screener": [(38.0, 23.5), (39.0, 23.0), (40.0, 22.0)],
        "track-tag-defender": [(47.0, 31.0), (45.5, 29.5), (44.0, 28.0)],
    }
    for track_id, player_id, *_ in aliases:
        points = []
        for frame, (x, y, conf), (cx, cy) in zip(frames, base_points[track_id], court_points[track_id], strict=True):
            det_id = f"det-{track_id}-{frame['frame_index']}"
            detections.append({"detection_id": det_id, "frame_id": frame["frame_id"], "frame_index": frame["frame_index"], "box": {"x": x - 32, "y": y - 92, "width": 64, "height": 128}, "confidence": conf, "class_name": "player", "track_id": track_id, "metadata": SAMPLE_MARKER})
            points.append({"frame_id": frame["frame_id"], "frame_index": frame["frame_index"], "timestamp_seconds": frame["timestamp_seconds"], "image_point_x": x, "image_point_y": y, "detection_id": det_id, "confidence": conf})
        track = {"track_id": track_id, "player_id": player_id, "points": points, "metadata": SAMPLE_MARKER}
        tracks.append(track)
        cleaned_tracks.append(track)
    projected = []
    for track_id, player_id, *_ in aliases:
        projected.append({"track_id": track_id, "player_id": player_id, "points": [{"frame_id": frames[i]["frame_id"], "frame_index": frames[i]["frame_index"], "timestamp_seconds": frames[i]["timestamp_seconds"], "court_x": court_points[track_id][i][0], "court_y": court_points[track_id][i][1], "source_image_point_x": base_points[track_id][i][0], "source_image_point_y": base_points[track_id][i][1], "confidence": base_points[track_id][i][2], "metadata": SAMPLE_MARKER} for i in range(3)], "metadata": SAMPLE_MARKER})

    tracking_request = {"project_id": pid, "frame_ids": [f["frame_id"] for f in frames], "model_name": "sample-deterministic-tracks", "confidence_threshold": 0.5, "iou_threshold": 0.3, "max_players": 3}
    tracking = {"schema_version": "1.0", "project_id": pid, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "original_input": tracking_request, "pipeline_output": {"sample": True, "detector": "synthetic-local"}, "debug_metadata": SAMPLE_MARKER, "request": tracking_request, "detections": detections, "tracks": tracks}
    project_tracks = {"project_id": pid, "tracking": tracking, "projected_tracks": projected, "storage_paths": {"projected_tracks": str(paths["projected_tracks"])}}

    quiz_prompt = {
        "project_id": pid,
        "prompt_id": "sample-pnr-prompt-1",
        "question": "The low defender tags the roller. What should the ball handler read first?",
        "court_role_target": "BALL_HANDLER",
        "situation_type": "PICK_AND_ROLL",
        "user_role_targets": ["BALL_HANDLER", "LOW_MAN"],
        "role_instruction": "Read the tag defender before committing to the pocket pass.",
        "frame_id": "sample-frame-001",
        "frame_index": 1,
        "timestamp_seconds": 5.0,
        "image_path": str(paths["frame_0"]),
        "video_asset_id": video_id,
        "clip_start_seconds": 3.5,
        "freeze_frame_seconds": 5.0,
        "clip_end_seconds": 6.5,
        "mode": "STILL_FRAME",
        "question_mode": "ROLE_READ",
        "time_limit_ms": 8000,
        "context_track_ids": [a[0] for a in aliases],
        "source_track_ids": ["track-ball-handler"],
        "options": [
            {"option_id": "skip-corner", "label": "Skip to weak-side corner", "action_type": "PASS", "start": {"x": 0.41, "y": 0.55}, "end": {"x": 0.75, "y": 0.36}, "expected_value": 1.12, "is_correct": True, "explanation": "The tag defender has committed to the roller, opening the weak-side skip.", "source_track_ids": ["track-ball-handler"]},
            {"option_id": "force-pocket", "label": "Force pocket pass", "action_type": "PASS", "start": {"x": 0.41, "y": 0.55}, "end": {"x": 0.52, "y": 0.49}, "expected_value": 0.62, "is_correct": False, "explanation": "The tag defender is in the lane and can contest the pocket window.", "source_track_ids": ["track-ball-handler"]},
            {"option_id": "hold-reset", "label": "Hold and reset", "action_type": "RESET", "start": {"x": 0.41, "y": 0.55}, "end": {"x": 0.37, "y": 0.58}, "expected_value": 0.78, "is_correct": False, "explanation": "Resetting is safe but misses the temporary weak-side advantage.", "source_track_ids": ["track-ball-handler"]},
        ],
        "explanation": "This synthetic sample emphasizes pick-and-roll tag reads using local deterministic metadata.",
        "created_at": SAMPLE_CREATED_AT,
        "updated_at": SAMPLE_UPDATED_AT,
    }
    attempt = {"prompt_id": "sample-pnr-prompt-1", "selected_option_id": "force-pocket", "correct_option_id": "skip-corner", "is_correct": False, "selected_expected_value": 0.62, "correct_expected_value": 1.12, "opportunity_cost": 0.5, "score": 55, "scoring_mode": "EXPECTED_VALUE", "selected_explanation": "Forced the pocket pass into the tag.", "correct_explanation": "Skip was the higher value read.", "selected_role_feedback": "Scan the low defender before the pass leaves your hand.", "correct_role_feedback": "Punish the tag with the skip.", "summary_explanation": "Sample attempt demonstrates an opportunity-cost miss.", "response_time_ms": 4200, "timed_out": False, "attempt_id": "sample-attempt-1", "project_id": pid, "user_role": "PLAYER", "attempted_at": SAMPLE_CREATED_AT}

    alias_records = [{"player_key": player_id, "project_id": pid, "track_ids": [track_id], "display_name": name, "team_side": team, "role_hint": role, "confidence": 1.0, "source": "MANUAL", "notes": "Seeded sample alias for local demo.", "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT} for track_id, player_id, name, team, role in aliases]

    plan_blocks = [
        {"block_id": "sample-plan-warmup", "block_type": "warmup", "title": "Warmup / readiness", "start_minute": 0, "end_minute": 10, "duration_minutes": 10, "target_roles": ["BALL_HANDLER"], "target_situations": ["PICK_AND_ROLL"], "player_keys": ["player-sample-guard"], "success_metrics": ["Players call out tag coverage before first pass."]},
        {"block_id": "sample-plan-drill", "block_type": "drill", "title": "Drill: PnR two-read pocket/skip", "start_minute": 10, "end_minute": 35, "duration_minutes": 25, "drill_id": "pnr-two-read-pocket-skip", "recommendation_id": "sample-rec-pnr-read", "priority": "HIGH", "target_roles": ["BALL_HANDLER"], "target_situations": ["PICK_AND_ROLL"], "player_keys": ["player-sample-guard"], "coaching_cues": ["Read the tag defender before the roller.", "Skip when the low defender commits early."], "success_metrics": ["7 of 10 reads identify the tag defender."], "evidence_refs": [{"source": "PLAYER_VALUE", "artifact": "player_value_summary.json", "project_id": pid, "player_key": "player-sample-guard", "prompt_id": "sample-pnr-prompt-1", "detail": "Opportunity cost on forced pocket pass."}]},
        {"block_id": "sample-plan-review", "block_type": "review", "title": "Film review: tag read", "start_minute": 35, "end_minute": 45, "duration_minutes": 10, "target_roles": ["BALL_HANDLER"], "target_situations": ["PICK_AND_ROLL"], "player_keys": ["player-sample-guard"], "success_metrics": ["Player explains skip-vs-pocket trigger."]},
    ]
    plan = {"schema_version": "1.0", "plan_id": "sample-pnr-plan", "title": "Sample PnR Reads Practice Plan", "created_at": SAMPLE_CREATED_AT, "created_by": "sample-data", "notes": "Deterministic sample practice plan.", "project_id": pid, "player_key": "player-sample-guard", "total_duration_minutes": 60, "target_roles": ["BALL_HANDLER"], "target_situations": ["PICK_AND_ROLL"], "player_keys": ["player-sample-guard"], "source_recommendation_ids": ["sample-rec-pnr-read"], "blocks": plan_blocks, "warnings": [], "evidence_refs": plan_blocks[1]["evidence_refs"], "markdown": f"# Sample PnR Reads Practice Plan\n\nLocal deterministic sample plan for {SAMPLE_PROJECT_ID}.\n", "json_path": str(paths["practice_plan"]), "markdown_path": str(paths["practice_plan_markdown"])}
    execution_blocks = [{"block_id": f"exec-{block['block_id']}", "plan_block_id": block["block_id"], "block_type": block["block_type"], "title": block["title"], "planned_start_minute": block["start_minute"], "planned_end_minute": block["end_minute"], "planned_duration_minutes": block["duration_minutes"], "drill_id": block.get("drill_id"), "recommendation_id": block.get("recommendation_id"), "success_metrics": block.get("success_metrics", []), "status": "COMPLETED", "coach_notes": "Sample execution note.", "metric_results": [{"metric": metric, "result": "met in sample", "met": True} for metric in block.get("success_metrics", [])], "outcome_rating": 4, "actual_duration_minutes": block["duration_minutes"]} for block in plan_blocks]

    decision_event = _sample_decision_event()
    decision_event_id = f"{pid}:sample-pnr-prompt-1:sample-attempt-1"
    player_value_summary = {
        "project_id": pid,
        "player_key": "player-sample-guard",
        "display_name": "Sample Guard",
        "team_side": "HOME",
        "role_hint": "PRIMARY_BALL_HANDLER",
        "track_ids": ["track-ball-handler"],
        "decision_event_count": 1,
        "avg_raw_decision_score": 55.0,
        "avg_role_adjusted_score": 55.0,
        "avg_opportunity_cost": 0.5,
        "correct_rate": 0.0,
        "timeout_rate": 0.0,
        "recognition_reliability_score": 92.0,
        "consistency_score": 72.0,
        "improvement_score": 50.0,
        "participation_score": 60.0,
        "player_value_score": 61.8,
        "components": [
            {"name": "Decision score", "value": 55.0, "weight": 0.55, "contribution": 30.25, "explanation": "One sample pick-and-roll decision attempt."},
            {"name": "Recognition reliability", "value": 92.0, "weight": 0.20, "contribution": 18.4, "explanation": "Synthetic sample tracks are fully aliased."},
            {"name": "Participation", "value": 60.0, "weight": 0.25, "contribution": 15.0, "explanation": "One local sample event is available."},
        ],
        "confidence": 0.72,
        "warnings": ["Sample-only Player Value summary; not a trained model output."],
        "trace": {"project_ids": [pid], "track_ids": ["track-ball-handler"], "decision_event_ids": [decision_event_id], "prompt_ids": ["sample-pnr-prompt-1"], "source_ids": ["sample-synthetic-source"]},
        "created_at": SAMPLE_CREATED_AT,
    }
    player_value_response = {"summaries": [player_value_summary], "generated_at": SAMPLE_CREATED_AT, "warnings": ["Deterministic sample data; no model training was run."]}
    player_value_metadata = {"player_value_formula_version": "v1", "recognition_model_version": None, "decision_rule_set_version": None, "dataset_fingerprint": "sample-court-iq-pnr-deterministic"}

    return {
        paths["project"]: {"schema_version": "1.0", "project_id": pid, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "name": SAMPLE_PROJECT_NAME, "description": "Deterministic local sample project for pick-and-roll decision reads.", "metadata": {**SAMPLE_MARKER, "sample_badge": "Sample"}, "original_input": {"sample_seed": True}, "pipeline_output": {"sample_dataset": "synthetic-local"}, "debug_metadata": SAMPLE_MARKER},
        paths["source"]: {"schema_version": "1.0", "project_id": pid, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "original_input": {}, "pipeline_output": {}, "debug_metadata": SAMPLE_MARKER, "source_id": "sample-synthetic-source", "name": "Synthetic local sample source", "source_type": "MANUAL_IMPORT", "source_url": None, "title": "Synthetic pick-and-roll metadata only", "license_type": "OWNED", "rights_confirmed": True, "allowed_for_training": False, "allowed_for_redistribution": True, "allowed_for_local_storage": True, "league_tag": "LOCAL", "usage_scope": "DEMO_ONLY", "notes": "No external videos or copyrighted footage; metadata and SVG frame are synthetic demo-only sample data."},
        paths["video"]: {"schema_version": "1.0", "project_id": pid, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "original_input": {"sample_seed": True}, "pipeline_output": {"sample": True, "no_external_video": True}, "debug_metadata": SAMPLE_MARKER, "asset_id": video_id, "source_type": "upload", "uri": None, "filename": "synthetic-sample-metadata-only.mp4", "content_type": "video/mp4", "duration_seconds": 8.0, "fps": 30.0, "frame_count": 240, "width": 1280, "height": 720},
        paths["frames"]: {"schema_version": "1.0", "project_id": pid, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "original_input": {"project_id": pid, "video_asset_id": video_id, "target_fps": 1, "start_time_seconds": 4, "end_time_seconds": 6, "max_frames": 3}, "pipeline_output": {"frame_count": 3, "extractor": "sample-synthetic"}, "debug_metadata": SAMPLE_MARKER, "request": {"project_id": pid, "video_asset_id": video_id, "target_fps": 1, "start_time_seconds": 4, "end_time_seconds": 6, "max_frames": 3}, "frames": frames},
        paths["calibration"]: {"schema_version": "1.0", "project_id": pid, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "original_input": {}, "pipeline_output": {"homography_source": "sample"}, "debug_metadata": SAMPLE_MARKER, "frame_id": "sample-frame-001", "homography": [[0.07, 0.0, -2.5], [0.0, 0.065, -6.0], [0.0, 0.0, 1.0]], "keypoint_pairs": [{"keypoint_id": "left-corner", "image_point": {"x": 250, "y": 590}, "court_point": {"x": 0, "y": 0, "label": "left corner"}, "confidence": 1.0}, {"keypoint_id": "right-corner", "image_point": {"x": 1030, "y": 590}, "court_point": {"x": 94, "y": 0, "label": "right corner"}, "confidence": 1.0}, {"keypoint_id": "center", "image_point": {"x": 640, "y": 360}, "court_point": {"x": 47, "y": 25, "label": "center"}, "confidence": 1.0}, {"keypoint_id": "rim", "image_point": {"x": 640, "y": 235}, "court_point": {"x": 47, "y": 41.75, "label": "rim"}, "confidence": 1.0}], "reprojection_error": 0.42},
        paths["tracking"]: tracking,
        paths["tracking_cleaned"]: {**tracking, "pipeline_output": {**tracking["pipeline_output"], "cleaned": True}, "tracks": cleaned_tracks},
        paths["projected_tracks"]: project_tracks,
        paths["projected_tracks_cleaned"]: {**project_tracks, "storage_paths": {"projected_tracks_cleaned": str(paths["projected_tracks_cleaned"])}},
        paths["tracking_review_patch"]: {"excluded_detection_ids": [], "excluded_track_ids": [], "track_id_aliases": {"track-ball-handler": "player-sample-guard", "track-screener": "player-sample-screener", "track-tag-defender": "player-sample-tag"}, "notes": "Sample review patch maps synthetic tracks to local aliases."},
        paths["player_aliases"]: {"project_id": pid, "aliases": alias_records},
        paths["quiz_prompts"]: [quiz_prompt],
        paths["quiz_attempts"]: [attempt],
        paths["player_value_summary"]: player_value_response,
        paths["player_value_build_index"]: {"builds": [{"build_id": "sample-pnr-build", "generated_at": SAMPLE_CREATED_AT, "summary_count": 1, "snapshot_path": "builds/sample-pnr-build.json", "warnings": ["Deterministic sample data; no model training was run."], **player_value_metadata}], "updated_at": SAMPLE_UPDATED_AT},
        paths["player_value_build_snapshot"]: {"build_id": "sample-pnr-build", "metadata": player_value_metadata, "build": player_value_response},
        paths["drill_recommendations"]: {"schema_version": "1.0", "generated_at": SAMPLE_CREATED_AT, "project_id": pid, "player_key": "player-sample-guard", "recommendations": [{"recommendation_id": "sample-rec-pnr-read", "drill_id": "pnr-two-read-pocket-skip", "title": "PnR two-read pocket/skip", "priority": "HIGH", "confidence": 0.88, "role": "BALL_HANDLER", "situation": "PICK_AND_ROLL", "reason": "Sample Player Value event shows opportunity cost when forcing the pocket pass.", "coaching_cues": ["Read the low tag before the roller.", "Skip when the tag commits early."], "success_metrics": ["7 of 10 reads identify tag coverage."], "evidence_refs": plan_blocks[1]["evidence_refs"], "feedback_adjusted": True, "feedback_signal_ids": ["sample-feedback-repeat-pnr"], "adjustment_summary": ["Sample execution recommends one repeat before progressing."], "adjustments": []}], "feedback_signal_count": 1, "adjustment_summary": ["Sample feedback connected to recommendation."], "warnings": [], "catalog_path": "backend/app/data/drills/catalog.json", "latest_path": str(paths["drill_recommendations"])},
        paths["practice_plan_index"]: {"plans": [{"plan_id": "sample-pnr-plan", "title": plan["title"], "created_at": SAMPLE_CREATED_AT, "created_by": "sample-data", "notes": plan["notes"], "project_id": pid, "player_key": "player-sample-guard", "total_duration_minutes": 60, "target_roles": ["BALL_HANDLER"], "target_situations": ["PICK_AND_ROLL"], "player_keys": ["player-sample-guard"], "warning_count": 0, "json_path": str(paths["practice_plan"]), "markdown_path": str(paths["practice_plan_markdown"])}], "updated_at": SAMPLE_UPDATED_AT},
        paths["practice_plan"]: plan,
        paths["practice_execution_index"]: {"executions": [{"execution_id": "sample-pnr-execution", "plan_id": "sample-pnr-plan", "plan_title": plan["title"], "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "started_by": "sample coach", "completed_at": SAMPLE_UPDATED_AT, "planned_duration_minutes": 60, "completion_rate": 1.0, "skipped_count": 0, "modified_count": 0, "json_path": str(paths["practice_execution"])}], "updated_at": SAMPLE_UPDATED_AT},
        paths["practice_execution"]: {"schema_version": "1.0", "execution_id": "sample-pnr-execution", "plan_id": "sample-pnr-plan", "plan_title": plan["title"], "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "started_by": "sample coach", "notes": "Sample practice execution with all blocks completed.", "completed_at": SAMPLE_UPDATED_AT, "project_id": pid, "player_key": "player-sample-guard", "player_keys": ["player-sample-guard"], "planned_duration_minutes": 60, "blocks": execution_blocks, "source_plan_json_path": str(paths["practice_plan"]), "json_path": str(paths["practice_execution"])},
        paths["coach_report_index"]: {"reports": [{"report_id": "sample-pnr-report", "title": "Sample PnR Coach Report", "created_at": SAMPLE_CREATED_AT, "created_by": "sample-data", "project_id": pid, "player_key": "player-sample-guard", "section_names": ["Player Value", "Teaching Cases", "Drill Recommendations"], "warning_count": 0, "json_path": str(paths["coach_report"]), "markdown_path": str(paths["coach_report_markdown"])}], "updated_at": SAMPLE_UPDATED_AT},
        paths["coach_report"]: {"schema_version": "1.0", "report_id": "sample-pnr-report", "title": "Sample PnR Coach Report", "created_at": SAMPLE_CREATED_AT, "created_by": "sample-data", "project_id": pid, "player_key": "player-sample-guard", "sections": [{"name": "Player Value", "heading": "Player Value", "markdown": "Sample Guard: average score 55 with 0.50 opportunity cost.", "data": {"project_id": pid}, "warnings": []}, {"name": "Teaching Cases", "heading": "Teaching Cases", "markdown": "Use sample-pnr-prompt-1 to discuss tag defender reads.", "data": {"prompt_id": "sample-pnr-prompt-1"}, "warnings": []}, {"name": "Drill Recommendations", "heading": "Drill Recommendations", "markdown": "Run PnR two-read pocket/skip from the local catalog.", "data": {"recommendation_id": "sample-rec-pnr-read"}, "warnings": []}], "warnings": [], "artifact_status": [], "markdown": f"# Sample PnR Coach Report\n\nSample Guard: average score 55 with 0.50 opportunity cost for {SAMPLE_PROJECT_ID}.\n", "json_path": str(paths["coach_report"]), "markdown_path": str(paths["coach_report_markdown"])},
        paths["workflow_index"]: {"workflows": [{"workflow_id": "workflow-sample-pnr", "template_key": "BUILD_PLAYER_VALUE", "title": "Sample project walkthrough", "status": "COMPLETED", "project_id": pid, "player_key": "player-sample-guard", "source_action_id": None, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "completed_step_count": 3, "total_step_count": 3, "blocked_step_count": 0}], "updated_at": SAMPLE_UPDATED_AT},
        paths["workflow"]: {"schema_version": "1.0", "workflow_id": "workflow-sample-pnr", "template_key": "BUILD_PLAYER_VALUE", "title": "Sample project walkthrough", "description": "Walk through the deterministic sample project artifacts.", "status": "COMPLETED", "project_id": pid, "player_key": "player-sample-guard", "source_action_id": None, "context": {"sample": "true"}, "created_at": SAMPLE_CREATED_AT, "updated_at": SAMPLE_UPDATED_AT, "prerequisites": [], "steps": [{"step_id": "open-project", "title": "Open project", "description": "Open the seeded sample project.", "action_label": "Open project", "href": f"/projects/{pid}", "status": "COMPLETED", "prerequisite_keys": [], "blocking_prerequisite_keys": [], "completion_prerequisite_key": None, "notes": ["Sample artifact is already installed."], "updated_at": SAMPLE_UPDATED_AT}, {"step_id": "review-tracking", "title": "Review sample tracks", "description": "Inspect cleaned tracks and alias patch.", "action_label": "Tracking Review", "href": f"/projects/{pid}/tracking-review", "status": "COMPLETED", "prerequisite_keys": ["has_tracking"], "blocking_prerequisite_keys": [], "completion_prerequisite_key": "has_tracking_review", "notes": [], "updated_at": SAMPLE_UPDATED_AT}, {"step_id": "practice-plan", "title": "Inspect practice plan", "description": "Open the seeded practice plan.", "action_label": "Practice Plans", "href": "/practice-plans", "status": "COMPLETED", "prerequisite_keys": ["has_practice_plan"], "blocking_prerequisite_keys": [], "completion_prerequisite_key": "has_practice_plan", "notes": [], "updated_at": SAMPLE_UPDATED_AT}], "warnings": [], "storage_path": str(paths["workflow"])},
        paths["review_queue"]: [{"item_id": "sample-review-pnr-tag", "item_type": "DECISION_ATTEMPT", "priority": "HIGH", "project_id": pid, "prompt_id": "sample-pnr-prompt-1", "attempt_id": "sample-attempt-1", "player_key": "player-sample-guard", "reason": "Sample prompt demonstrates a tag defender committing to the roller.", "recommended_action": "Inspect the sample teaching case and confirm the skip-vs-pocket cue.", "status": "OPEN", "created_at": SAMPLE_CREATED_AT, "allowed_actions": []}],
        paths["review_action_log"]: [{"action_id": "sample-action-alias-confirmed", "item_id": "sample-review-pnr-tag", "item_type": "DECISION_ATTEMPT", "action_type": "MARK_ATTEMPT_TEACHING_CASE", "project_id": pid, "target_ref": {"prompt_id": "sample-pnr-prompt-1", "attempt_id": "sample-attempt-1"}, "payload": {"sample_project_id": pid}, "note": "Sample action marks the local teaching case.", "status": "APPLIED", "warnings": [], "created_at": SAMPLE_CREATED_AT, "debug_metadata": SAMPLE_MARKER}],
    }


def _write_frame_svg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1280\" height=\"720\" viewBox=\"0 0 1280 720\" role=\"img\" aria-label=\"Synthetic sample basketball half-court diagram\"><rect width=\"1280\" height=\"720\" fill=\"#0f5132\"/><rect x=\"220\" y=\"110\" width=\"840\" height=\"500\" fill=\"#d6a15f\" stroke=\"#fff7ed\" stroke-width=\"8\"/><circle cx=\"640\" cy=\"360\" r=\"82\" fill=\"none\" stroke=\"#fff7ed\" stroke-width=\"6\"/><path d=\"M220 250 H420 V470 H220\" fill=\"none\" stroke=\"#fff7ed\" stroke-width=\"6\"/><path d=\"M1060 250 H860 V470 H1060\" fill=\"none\" stroke=\"#fff7ed\" stroke-width=\"6\"/><circle cx=\"475\" cy=\"395\" r=\"22\" fill=\"#2563eb\"/><text x=\"475\" y=\"401\" text-anchor=\"middle\" fill=\"white\" font-size=\"18\" font-family=\"Arial\">BH</text><circle cx=\"625\" cy=\"370\" r=\"22\" fill=\"#2563eb\"/><text x=\"625\" y=\"376\" text-anchor=\"middle\" fill=\"white\" font-size=\"18\" font-family=\"Arial\">S</text><circle cx=\"735\" cy=\"440\" r=\"22\" fill=\"#dc2626\"/><text x=\"735\" y=\"446\" text-anchor=\"middle\" fill=\"white\" font-size=\"18\" font-family=\"Arial\">TAG</text><path d=\"M475 395 C560 315 650 320 735 440\" fill=\"none\" stroke=\"#facc15\" stroke-width=\"8\" stroke-dasharray=\"18 12\"/><text x=\"640\" y=\"70\" text-anchor=\"middle\" fill=\"#fff7ed\" font-size=\"34\" font-family=\"Arial\" font-weight=\"700\">Synthetic Court IQ Sample — no video footage</text></svg>\n""", encoding="utf-8")


def get_sample_data_status() -> SampleDataStatusResponse:
    paths = _artifact_paths()
    artifacts = [SampleDataArtifactStatus(key=key, path=str(path), installed=path.exists()) for key, path in paths.items()]
    installed = paths["project"].exists() and all(item.installed for item in artifacts if item.key in {"project", "source", "video", "frames", "calibration", "tracking", "projected_tracks", "player_aliases", "quiz_prompts"})
    protected = paths["project"].exists() and not _can_replace(paths)
    return SampleDataStatusResponse(
        installed=installed,
        can_seed=not protected,
        protected_existing_project=protected,
        artifact_count=sum(1 for item in artifacts if item.installed),
        artifacts=artifacts,
        quick_links=_quick_links() if installed else [],
        message="Sample project is installed." if installed else ("A non-sample project already uses the sample id; seeding is blocked." if protected else "Sample project is not installed."),
    )


def seed_sample_data() -> SampleDataMutationResponse:
    paths = _artifact_paths()
    if not _can_replace(paths):
        raise api_error(409, "SAMPLE_PROJECT_ID_IN_USE", "A non-sample project already uses the deterministic sample project id.", {"project_id": SAMPLE_PROJECT_ID, "path": str(paths["project"])}, "Rename or move the existing project before installing the sample dataset; the sample seeder never overwrites user data.")
    payloads = _sample_project_payloads(paths)
    for path in payloads:
        if path.exists() and not _is_sample_payload(path):
            raise api_error(409, "SAMPLE_ARTIFACT_PATH_IN_USE", "A non-sample artifact exists at a sample output path.", {"path": str(path)}, "Move the existing artifact before installing the sample dataset; the sample seeder never overwrites user data.")
    for path, payload in payloads.items():
        _write_json(path, payload)
    _write_jsonl(paths["decision_events"], [_sample_decision_event()])
    _write_jsonl(paths["feedback_signals"], [{"signal_id": "sample-feedback-repeat-pnr", "signal_type": "REPEAT_DRILL", "execution_id": "sample-pnr-execution", "block_id": "exec-sample-plan-drill", "drill_id": "pnr-two-read-pocket-skip", "recommendation_id": "sample-rec-pnr-read", "reason": "Sample execution repeats the two-read drill before progression.", "severity": "action", "project_id": SAMPLE_PROJECT_ID, "player_key": "player-sample-guard", "created_at": SAMPLE_CREATED_AT, "debug_metadata": SAMPLE_MARKER}])
    _write_frame_svg(paths["frame_0"])
    paths["practice_plan_markdown"].write_text(f"# Sample PnR Reads Practice Plan\n\nLocal deterministic sample plan for {SAMPLE_PROJECT_ID}.\n", encoding="utf-8")
    paths["coach_report_markdown"].write_text(f"# Sample PnR Coach Report\n\nSample Guard: average score 55 with 0.50 opportunity cost for {SAMPLE_PROJECT_ID}.\n", encoding="utf-8")
    status = get_sample_data_status()
    payload = status.model_dump()
    payload["message"] = "Sample project installed."
    return SampleDataMutationResponse(**payload, changed=True)


def delete_sample_data() -> SampleDataMutationResponse:
    paths = _artifact_paths()
    changed = False
    if paths["project"].exists():
        if not _can_replace(paths):
            raise api_error(409, "SAMPLE_PROJECT_DELETE_BLOCKED", "The deterministic sample id belongs to a non-sample project, so it was not deleted.", {"project_id": SAMPLE_PROJECT_ID, "path": str(paths["project"])}, "Only sample-owned artifacts can be removed by DELETE /api/sample-data.")
        shutil.rmtree(_project_dir())
        changed = True
    for key, path in paths.items():
        if key in {"project", "source", "video", "frames", "frame_0", "calibration", "tracking", "tracking_cleaned", "projected_tracks", "projected_tracks_cleaned", "tracking_review_patch", "player_aliases", "quiz_prompts", "quiz_attempts"}:
            continue
        if path.exists() and _is_sample_payload(path):
            path.unlink()
            changed = True
    status = get_sample_data_status()
    payload = status.model_dump()
    payload["message"] = "Sample project removed." if changed else "Sample project was not installed."
    return SampleDataMutationResponse(**payload, changed=changed)
