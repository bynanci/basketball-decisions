from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str = Field(..., examples=["not_found"])
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    debug_hint: str | None = None
