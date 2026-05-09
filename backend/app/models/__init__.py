"""Pydantic models for basketball decision project artifacts."""

from .calibration import (
    Calibration,
    CourtKeypointPair,
    CourtPoint,
    ImagePoint,
    SaveCalibrationRequest,
    SaveCalibrationResponse,
)
from .errors import ApiErrorResponse
from .project import Project, ProjectCreateRequest, ProjectCreateResponse
from .projection import ProjectedPlayerTrack, ProjectedTrackPoint
from .tracking import (
    Detection,
    DetectionBox,
    PlayerTrack,
    RunTrackingRequest,
    RunTrackingResponse,
    ProjectTracksResponse,
    TrackPoint,
)
from .video import (
    ExtractFramesRequest,
    ExtractFramesResponse,
    FrameAsset,
    VideoAsset,
    VideoSourceType,
    YouTubeVideoRequest,
)

__all__ = [
    "ApiErrorResponse",
    "Calibration",
    "CourtKeypointPair",
    "CourtPoint",
    "Detection",
    "DetectionBox",
    "ExtractFramesRequest",
    "ExtractFramesResponse",
    "FrameAsset",
    "ImagePoint",
    "PlayerTrack",
    "Project",
    "ProjectCreateRequest",
    "ProjectCreateResponse",
    "ProjectedPlayerTrack",
    "ProjectedTrackPoint",
    "ProjectTracksResponse",
    "RunTrackingRequest",
    "RunTrackingResponse",
    "SaveCalibrationRequest",
    "SaveCalibrationResponse",
    "TrackPoint",
    "VideoAsset",
    "YouTubeVideoRequest",
    "VideoSourceType",
]
