from fastapi import APIRouter
from pydantic import BaseModel

from app.pipeline.homography import estimate_homography

router = APIRouter(prefix="/calibration", tags=["calibration"])


class Point(BaseModel):
    x: float
    y: float


class CalibrationRequest(BaseModel):
    project_id: str
    image_points: list[Point]
    court_points: list[Point]


@router.post("/homography")
def calculate_homography(payload: CalibrationRequest) -> dict[str, object]:
    result = estimate_homography(
        [point.model_dump() for point in payload.image_points],
        [point.model_dump() for point in payload.court_points],
    )
    return {"project_id": payload.project_id, "homography": result}
