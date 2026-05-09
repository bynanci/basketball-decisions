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
from .quiz import DecisionAnswer, DecisionOption, FreezeFrame, QuizPrompt
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
    "DecisionAnswer",
    "DecisionOption",
    "ExtractFramesRequest",
    "ExtractFramesResponse",
    "FrameAsset",
    "FreezeFrame",
    "ImagePoint",
    "PlayerTrack",
    "Project",
    "ProjectCreateRequest",
    "ProjectCreateResponse",
    "ProjectedPlayerTrack",
    "ProjectedTrackPoint",
    "ProjectTracksResponse",
    "QuizPrompt",
    "RunTrackingRequest",
    "RunTrackingResponse",
    "SaveCalibrationRequest",
    "SaveCalibrationResponse",
    "TrackPoint",
    "VideoAsset",
    "YouTubeVideoRequest",
    "VideoSourceType",
]
