from fastapi import APIRouter

from app.api.common import api_error, require_project_dir, write_json_model
from app.models import Calibration, SaveCalibrationRequest, SaveCalibrationResponse
from app.pipeline.homography import estimate_homography

router = APIRouter(prefix="/projects/{project_id}/calibration", tags=["calibration"])


@router.post("", response_model=SaveCalibrationResponse)
def save_calibration(project_id: str, payload: SaveCalibrationRequest) -> SaveCalibrationResponse:
    if project_id != payload.project_id:
        raise api_error(
            400,
            "PROJECT_ID_MISMATCH",
            "Request body project_id must match the path project_id.",
            {"path_project_id": project_id, "body_project_id": payload.project_id},
            "Send the same project id in the URL and Pydantic request body.",
        )
    directory = require_project_dir(project_id)
    homography = payload.homography
    reprojection_error = None
    if homography is None:
        try:
            result = estimate_homography(
                [pair.image_point.model_dump() for pair in payload.keypoint_pairs],
                [pair.court_point.model_dump() for pair in payload.keypoint_pairs],
            )
        except ValueError as exc:
            raise api_error(
                422,
                "HOMOGRAPHY_ESTIMATION_FAILED",
                str(exc),
                {"keypoint_pair_count": len(payload.keypoint_pairs)},
                "Provide at least four non-degenerate image/court keypoint pairs or pass a precomputed homography.",
            ) from exc
        homography = result["matrix"]
        reprojection_error = 0.0

    calibration = Calibration(
        project_id=project_id,
        frame_id=payload.frame_id,
        homography=homography,
        keypoint_pairs=payload.keypoint_pairs,
        reprojection_error=reprojection_error,
        original_input=payload.model_dump(),
        debug_metadata=payload.debug_metadata,
    )
    storage_path = directory / "calibration.json"
    write_json_model(storage_path, calibration)
    return SaveCalibrationResponse(calibration=calibration, storage_path=str(storage_path))
