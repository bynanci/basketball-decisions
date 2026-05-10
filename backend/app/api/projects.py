from uuid import uuid4

from fastapi import APIRouter

from app.api.common import DATA_DIR, api_error, project_dir, read_json, require_project_dir, write_json_model
from app.models import (
    Calibration,
    ExtractFramesResponse,
    Project,
    ProjectBundleResponse,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectTracksResponse,
    RunTrackingResponse,
    VideoAsset,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects() -> dict[str, list[dict[str, str | None]]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    projects: list[dict[str, str | None]] = []
    for path in DATA_DIR.glob("*/project.json"):
        project = Project.model_validate_json(path.read_text(encoding="utf-8"))
        projects.append({"id": project.project_id, "name": project.name, "description": project.description})
    return {"projects": projects}


def _read_optional_artifact(directory, relative_path: str, model):
    path = directory / relative_path
    if not path.exists():
        return None
    return model.model_validate(read_json(path))


@router.get("/{project_id}/bundle", response_model=ProjectBundleResponse)
def get_project_bundle(project_id: str) -> ProjectBundleResponse:
    """Return a project plus any persisted local MVP pipeline artifacts."""

    directory = require_project_dir(project_id)
    project = Project.model_validate(read_json(directory / "project.json"))
    return ProjectBundleResponse(
        project=project,
        video=_read_optional_artifact(directory, "video.json", VideoAsset),
        frames=_read_optional_artifact(directory, "frames/index.json", ExtractFramesResponse),
        calibration=_read_optional_artifact(directory, "calibration.json", Calibration),
        tracking=_read_optional_artifact(directory, "tracking.json", RunTrackingResponse),
        projected_tracks=_read_optional_artifact(directory, "projected_tracks.json", ProjectTracksResponse),
    )


@router.post("", response_model=ProjectCreateResponse)
def create_project(payload: ProjectCreateRequest) -> ProjectCreateResponse:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    project_id = str(uuid4())
    directory = project_dir(project_id)
    if directory.exists():
        raise api_error(
            409,
            "PROJECT_ID_COLLISION",
            "Generated project id already exists.",
            {"project_id": project_id},
            "Retry the request; UUID collisions should be exceptionally rare.",
        )
    project = Project(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        metadata=payload.metadata,
        original_input=payload.model_dump(),
    )
    storage_path = directory / "project.json"
    write_json_model(storage_path, project)
    return ProjectCreateResponse(project=project, storage_path=str(storage_path))
