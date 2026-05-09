from pathlib import Path


BACKEND_FILES = [
    Path("backend/app/api/projects.py"),
    Path("backend/app/main.py"),
    Path("backend/app/models/__init__.py"),
    Path("backend/app/models/calibration.py"),
    Path("backend/app/models/tracking.py"),
    Path("backend/app/models/video.py"),
]

REQUIRED_ERROR_FIELDS = ["code", "message", "details", "debug_hint"]


def test_conflict_target_files_have_no_merge_markers() -> None:
    for path in BACKEND_FILES:
        text = path.read_text(encoding="utf-8")
        assert "<" * 7 not in text, f"unresolved merge start marker in {path}"
        assert "=" * 7 not in text, f"unresolved merge separator marker in {path}"
        assert ">" * 7 not in text, f"unresolved merge end marker in {path}"


def test_project_router_exposes_requested_routes_and_models() -> None:
    text = Path("backend/app/api/projects.py").read_text(encoding="utf-8")
    for route in [
        '"/projects"',
        '"/projects/{project_id}/video/upload"',
        '"/projects/{project_id}/video/youtube"',
        '"/projects/{project_id}/frames/extract"',
        '"/projects/{project_id}/frames/{frame_index}"',
        '"/projects/{project_id}/calibration"',
        '"/projects/{project_id}/tracking/run"',
        '"/projects/{project_id}/tracks"',
    ]:
        assert route in text

    for model_name in [
        "ProjectCreateRequest",
        "ProjectCreateResponse",
        "VideoAsset",
        "ExtractFramesRequest",
        "ExtractFramesResponse",
        "SaveCalibrationRequest",
        "SaveCalibrationResponse",
        "RunTrackingRequest",
        "RunTrackingResponse",
        "YouTubeVideoRequest",
    ]:
        assert model_name in text


def test_structured_error_response_contract_is_preserved() -> None:
    error_model = Path("backend/app/models/errors.py").read_text(encoding="utf-8")
    error_handler = Path("backend/app/core/errors.py").read_text(encoding="utf-8")

    for field in REQUIRED_ERROR_FIELDS:
        assert field in error_model
        assert field in error_handler


def test_optional_imports_are_guarded_without_import_try_except() -> None:
    text = Path("backend/app/api/projects.py").read_text(encoding="utf-8")
    assert 'find_spec("cv2")' in text
    assert 'find_spec("ultralytics")' in text
    assert "except ImportError" not in text
