from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class VideoAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    source_type: Literal["upload", "youtube"]
    filename: str
    content_type: str = "video/mp4"
    path: str
    size_bytes: int | None = None
    status: Literal["ready", "pending", "failed"] = "ready"
    message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class YouTubeVideoRequest(BaseModel):
    url: str = Field(..., min_length=1)
