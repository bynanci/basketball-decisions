"""Shared API helpers for MVP project artifact routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"


def project_dir(project_id: str) -> Path:
    return DATA_DIR / project_id


def require_project_dir(project_id: str) -> Path:
    directory = project_dir(project_id)
    if not (directory / "project.json").exists():
        raise api_error(
            404,
            "PROJECT_NOT_FOUND",
            f"Project '{project_id}' does not exist.",
            {"project_id": project_id},
            "Create the project with POST /api/projects before calling nested project routes.",
        )
    return directory


def write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise api_error(
            404,
            "ARTIFACT_NOT_FOUND",
            f"Required artifact '{path.name}' was not found.",
            {"path": str(path)},
            "Run the preceding pipeline step first, then retry this endpoint.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    debug_hint: str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details or {},
            "debug_hint": debug_hint,
        },
    )


def assert_path_child(path: Path, parent: Path) -> Path:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    if resolved_parent not in resolved_path.parents and resolved_path != resolved_parent:
        raise api_error(
            400,
            "INVALID_PATH",
            "Requested path is outside the project storage directory.",
            {"path": str(path), "project_dir": str(parent)},
            "Use only frame indexes returned by the frame extraction endpoint.",
        )
    return resolved_path
