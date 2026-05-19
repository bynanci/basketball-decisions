"""Simplified player-facing home models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PlayerTrendDirection = Literal["up", "down", "flat", "unknown"]


class PlayerHomeResponse(BaseModel):
    player_key: str
    display_name: str
    latest_player_value: float | None = None
    confidence: float | None = None
    trend_direction: PlayerTrendDirection = "unknown"
    today_focus: str
    current_strength: str
    current_risk: str
    recommended_drill: str
    latest_practice_feedback: str
    next_action: str
    warnings: list[str] = Field(default_factory=list)
