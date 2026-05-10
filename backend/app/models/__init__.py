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
from .project import Project, ProjectBundleResponse, ProjectCreateRequest, ProjectCreateResponse
from .quiz import (
    CreateQuizPromptRequest,
    DecisionAnswer,
    DecisionArrowPoint,
    DecisionQuizOption,
    DecisionOption,
    FreezeFrame,
    QuizAttemptRecord,
    QuizAttemptRequest,
    QuizAttemptResponse,
    QuizPrompt,
    QuizPromptMode,
)
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
    "DecisionQuizOption",
    "ExtractFramesRequest",
    "ExtractFramesResponse",
    "FrameAsset",
    "FreezeFrame",
    "ImagePoint",
    "PlayerTrack",
    "Project",
    "ProjectBundleResponse",
    "ProjectCreateRequest",
    "ProjectCreateResponse",
    "ProjectedPlayerTrack",
    "ProjectedTrackPoint",
    "ProjectTracksResponse",
    "CreateQuizPromptRequest",
    "DecisionArrowPoint",
    "QuizAttemptRecord",
    "QuizAttemptRequest",
    "QuizAttemptResponse",
    "QuizPrompt",
    "QuizPromptMode",
    "RunTrackingRequest",
    "RunTrackingResponse",
    "SaveCalibrationRequest",
    "SaveCalibrationResponse",
    "TrackPoint",
    "VideoAsset",
    "YouTubeVideoRequest",
    "VideoSourceType",
]
