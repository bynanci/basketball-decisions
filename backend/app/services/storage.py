import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

DATA_ROOT = Path("data")
PROJECTS_ROOT = DATA_ROOT / "projects"
PROJECTS_INDEX = DATA_ROOT / "projects.json"

T = TypeVar("T", bound=BaseModel)


def ensure_data_dirs() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)


def project_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id


def write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def read_model(path: Path, model_type: type[T]) -> T:
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def write_model_list(path: Path, models: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([m.model_dump(mode="json") for m in models], indent=2), encoding="utf-8")


def read_model_list(path: Path, model_type: type[T]) -> list[T]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [model_type.model_validate(item) for item in raw]
