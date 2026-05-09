from pydantic import BaseModel, Field


class ImagePoint(BaseModel):
    x: float
    y: float


class CourtPoint(BaseModel):
    x: float
    y: float


class CalibrationKeypoint(BaseModel):
    image: ImagePoint
    court: CourtPoint
    label: str | None = None


class SaveCalibrationRequest(BaseModel):
    keypoints: list[CalibrationKeypoint] = Field(..., min_length=4)


class SaveCalibrationResponse(BaseModel):
    project_id: str
    keypoints: list[CalibrationKeypoint]
    homography_matrix: list[list[float]]
    reprojection_error: float | None = None
