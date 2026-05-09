"""API error response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    """Consistent error payload returned by API exception handlers."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    debug_hint: str | None = None
