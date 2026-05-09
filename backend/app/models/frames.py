from pydantic import BaseModel, Field


class ExtractFramesRequest(BaseModel):
    every_n_seconds: float = Field(default=1.0, gt=0)
    start_seconds: float = Field(default=0.0, ge=0)
    max_frames: int = Field(default=300, gt=0, le=10_000)
    overwrite: bool = False


class FrameAsset(BaseModel):
    project_id: str
    frame_index: int
    timestamp_seconds: float
    path: str
    width: int | None = None
    height: int | None = None


class ExtractFramesResponse(BaseModel):
    project_id: str
    video_id: str
    frames: list[FrameAsset]
    count: int
