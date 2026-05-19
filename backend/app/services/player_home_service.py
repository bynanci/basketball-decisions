from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import PlayerHomeResponse

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATASETS_DIR = APP_DATA_DIR / "datasets"
DRILLS_DIR = APP_DATA_DIR / "drills"
PRACTICE_EXECUTIONS_DIR = APP_DATA_DIR / "practice_executions"


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def build_player_home(player_key: str) -> PlayerHomeResponse:
    warnings: list[str] = []
    summary = _read_json(DATASETS_DIR / "player_value" / "player_value_summary.json") or {}
    trends = _read_json(DATASETS_DIR / "player_value" / "player_value_trends.json") or {}
    recs = _read_json(DRILLS_DIR / "latest_recommendations.json") or {}
    executions = _read_json(PRACTICE_EXECUTIONS_DIR / "index.json") or {}

    row = next((item for item in summary.get("summaries", []) if item.get("player_key") == player_key), None)
    if row is None:
        return PlayerHomeResponse(
            player_key=player_key,
            display_name=player_key,
            today_focus="No player summary yet",
            current_strength="Build Player Value first to reveal your current strength.",
            current_risk="No specific risk identified yet.",
            recommended_drill="No drill recommendation yet.",
            latest_practice_feedback="No practice feedback yet.",
            next_action="Build Player Value and drill recommendations",
            warnings=["No Player Value summary found for this player_key."],
        )

    series = next((item for item in trends.get("trends", []) if item.get("player_key") == player_key), None)
    trend_direction = "unknown"
    if series and len(series.get("points", [])) >= 2:
        points = series["points"]
        delta = float(points[-1].get("player_value_score", 0.0)) - float(points[-2].get("player_value_score", 0.0))
        trend_direction = "up" if delta > 0.01 else "down" if delta < -0.01 else "flat"

    rec = next((item for item in recs.get("recommendations", []) if item.get("player_key") == player_key), None)
    execution_rows = [e for e in executions.get("executions", []) if player_key in e.get("player_keys", [])]
    latest_execution = execution_rows[-1] if execution_rows else None

    confidence = row.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.6:
        warnings.append("Some video identity links need review before this score is fully trusted.")

    return PlayerHomeResponse(
        player_key=player_key,
        display_name=row.get("display_name") or player_key,
        latest_player_value=row.get("player_value_score"),
        confidence=confidence,
        trend_direction=trend_direction,
        today_focus=rec.get("focus_area", "Decision speed and consistency") if rec else "Decision speed and consistency",
        current_strength=rec.get("strength", "Your strongest area is shown once drill evidence is available.") if rec else "Your strongest area is shown once drill evidence is available.",
        current_risk=rec.get("risk", "Inconsistent choices under pressure.") if rec else "Inconsistent choices under pressure.",
        recommended_drill=(rec.get("drill_name") or rec.get("title") or "No drill recommendation yet.") if rec else "No drill recommendation yet.",
        latest_practice_feedback=(latest_execution.get("plan_title") + " completion " + str(round(float(latest_execution.get("completion_rate", 0.0)) * 100)) + "%") if latest_execution else "No practice execution feedback yet.",
        next_action="Review today's suggested drill focus" if rec else "Review practice plan",
        warnings=warnings,
    )
