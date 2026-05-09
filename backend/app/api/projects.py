from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(default="Untitled Project")
    youtube_url: str | None = None


@router.get("")
def list_projects() -> dict[str, list[dict[str, str]]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    projects = [{"id": path.stem, "name": path.stem} for path in DATA_DIR.glob("*.json")]
    return {"projects": projects}


@router.post("")
def create_project(payload: ProjectCreate) -> dict[str, str | None]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    project_id = str(uuid4())
    project_file = DATA_DIR / f"{project_id}.json"
    project_file.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    return {"id": project_id, "name": payload.name, "youtube_url": payload.youtube_url}
