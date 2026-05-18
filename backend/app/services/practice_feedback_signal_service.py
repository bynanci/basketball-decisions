"""Practice feedback signal persistence and lookup helpers.

Signals are deterministic records from practice executions. This module only
reads/writes local JSONL artifacts; it does not retrain models or generate new
coaching advice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models import PracticeFeedbackSignal, PracticeFeedbackSignalsResponse
from app.models.base import utc_now

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRACTICE_EXECUTIONS_DIR = APP_DATA_DIR / "practice_executions"
PRACTICE_FEEDBACK_SIGNALS_PATH = PRACTICE_EXECUTIONS_DIR / "practice_feedback_signals.jsonl"


def _read_jsonl(path: Path, warnings: list[str] | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                if warnings is not None:
                    warnings.append(f"Unreadable practice feedback signal line {line_number} at {path} ({exc.__class__.__name__}).")
                continue
            if isinstance(row, dict):
                rows.append(row)
    except OSError as exc:
        if warnings is not None:
            warnings.append(f"Unreadable practice feedback signals at {path} ({exc.__class__.__name__}).")
    return rows


def read_practice_feedback_signals(
    *,
    limit: int | None = None,
    project_id: str | None = None,
    player_key: str | None = None,
    warnings: list[str] | None = None,
) -> list[PracticeFeedbackSignal]:
    """Read recent practice feedback signals from the M24 JSONL artifact."""

    signals: list[PracticeFeedbackSignal] = []
    for row in _read_jsonl(PRACTICE_FEEDBACK_SIGNALS_PATH, warnings):
        try:
            signal = PracticeFeedbackSignal.model_validate(row)
        except ValidationError as exc:
            if warnings is not None:
                warnings.append(f"Invalid practice feedback signal in {PRACTICE_FEEDBACK_SIGNALS_PATH} ({exc.__class__.__name__}).")
            continue
        if project_id and signal.project_id and signal.project_id != project_id:
            continue
        if player_key and signal.player_key and signal.player_key != player_key:
            continue
        signals.append(signal)

    signals.sort(key=lambda item: item.created_at, reverse=True)
    return signals[:limit] if limit is not None else signals


def write_practice_feedback_signals(signals: list[PracticeFeedbackSignal]) -> None:
    """Rewrite the JSONL artifact with stable, validated signal payloads."""

    PRACTICE_FEEDBACK_SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(signal.model_dump(mode="json"), sort_keys=True, default=str) for signal in signals]
    PRACTICE_FEEDBACK_SIGNALS_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def list_practice_feedback_signals(limit: int | None = None) -> PracticeFeedbackSignalsResponse:
    """Return practice feedback signals from the JSONL artifact."""

    return PracticeFeedbackSignalsResponse(signals=read_practice_feedback_signals(limit=limit), updated_at=utc_now())
