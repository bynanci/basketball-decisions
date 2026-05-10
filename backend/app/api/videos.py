from __future__ import annotations

import importlib
import importlib.util
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from app.api.common import api_error, assert_path_child, read_json, require_project_dir, write_json_model
from app.models import (
    ExtractFramesRequest,
    ExtractFramesResponse,
    FrameAsset,
    LeagueTag,
    SourceLicenseType,
    SourceType,
    UsageScope,
    VideoAsset,
    VideoSourceRecord,
    YouTubeVideoRequest,
)
from app.pipeline.frame_extractor import FrameExtractionError, extract_frames

router = APIRouter(prefix="/projects/{project_id}/video", tags=["videos"])
frames_router = APIRouter(prefix="/projects/{project_id}/frames", tags=["frames"])


def _write_upload_source(directory: Path, project_id: str, asset_id: str, filename: str | None) -> None:
    source = VideoSourceRecord(
        project_id=project_id,
        source_id=asset_id,
        name=filename or "User upload",
        source_type=SourceType.UPLOAD,
        title=filename,
        license_type=SourceLicenseType.OWNED,
        rights_confirmed=True,
        allowed_for_training=True,
        allowed_for_redistribution=False,
        allowed_for_local_storage=True,
        league_tag=LeagueTag.UNKNOWN,
        usage_scope=UsageScope.TRAINING,
        notes="Default source governance for a user-uploaded local file.",
    )
    write_json_model(directory / "source.json", source)


def _write_youtube_source(
    directory: Path,
    project_id: str,
    asset_id: str,
    payload: YouTubeVideoRequest,
    title: str | None = None,
    downloaded_with_permission: bool = False,
) -> None:
    source = VideoSourceRecord(
        project_id=project_id,
        source_id=asset_id,
        name=title or "YouTube reference",
        source_type=SourceType.YOUTUBE,
        source_url=payload.url,
        title=title,
        license_type=SourceLicenseType.YOUTUBE_REFERENCE_ONLY,
        rights_confirmed=payload.rights_confirmed,
        allowed_for_training=False,
        allowed_for_redistribution=False,
        allowed_for_local_storage=downloaded_with_permission,
        league_tag=LeagueTag.UNKNOWN,
        usage_scope=UsageScope.REFERENCE_ONLY,
        notes="YouTube imports default to reference-only until the user records a training-eligible license or permission.",
    )
    write_json_model(directory / "source.json", source)


def _validate_body_project_id(path_project_id: str, body_project_id: str) -> None:
    if path_project_id != body_project_id:
        raise api_error(
            400,
            "PROJECT_ID_MISMATCH",
            "Request body project_id must match the path project_id.",
            {"path_project_id": path_project_id, "body_project_id": body_project_id},
            "Send the same project id in the URL and Pydantic request body.",
        )


@router.post("/upload", response_model=VideoAsset)
async def upload_video(project_id: str, file: UploadFile = File(...)) -> VideoAsset:
    directory = require_project_dir(project_id)
    suffix = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    allowed_content_types = {"video/mp4", "application/octet-stream", None}
    if suffix != ".mp4" or file.content_type not in allowed_content_types:
        raise api_error(
            415,
            "UNSUPPORTED_VIDEO_TYPE",
            "Only MP4 uploads are supported by the MVP endpoint.",
            {"filename": file.filename, "content_type": file.content_type},
            "Upload a .mp4 file with content type video/mp4.",
        )
    asset_id = str(uuid4())
    video_dir = directory / "videos"
    destination = video_dir / f"{asset_id}.mp4"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    video = VideoAsset(
        project_id=project_id,
        asset_id=asset_id,
        source_type="upload",
        uri=str(destination),
        filename=file.filename or destination.name,
        content_type=file.content_type,
        original_input={"filename": file.filename, "content_type": file.content_type},
        debug_metadata={"todo": "Probe video metadata with ffprobe/OpenCV in a later pipeline step."},
    )
    write_json_model(directory / "video.json", video)
    _write_upload_source(directory, project_id, asset_id, video.filename)
    return video


@router.get("/source")
def get_video_source(project_id: str) -> FileResponse:
    """Serve the current local MP4 without exposing arbitrary filesystem paths."""

    directory = require_project_dir(project_id)
    video_json_path = directory / "video.json"
    if not video_json_path.exists():
        raise api_error(
            404,
            "LOCAL_VIDEO_NOT_FOUND",
            "No local browser-playable video file is available for this project.",
            {"project_id": project_id},
            "Upload a local MP4 before using video-freeze quiz playback.",
        )
    video_doc = VideoAsset.model_validate(read_json(video_json_path))
    if not video_doc.uri:
        raise api_error(
            404,
            "LOCAL_VIDEO_NOT_FOUND",
            "No local browser-playable video file is available for this project.",
            {"project_id": project_id, "asset_id": video_doc.asset_id},
            "Upload a local MP4 before using video-freeze quiz playback.",
        )

    raw_video_path = Path(video_doc.uri)
    video_path = raw_video_path.resolve()
    project_root = directory.resolve()
    if project_root not in video_path.parents or video_path.suffix.lower() != ".mp4" or not video_path.is_file():
        raise api_error(
            404,
            "LOCAL_VIDEO_NOT_FOUND",
            "No local browser-playable video file is available for this project.",
            {"project_id": project_id, "asset_id": video_doc.asset_id},
            "Upload a local MP4 before using video-freeze quiz playback.",
        )

    return FileResponse(video_path, media_type="video/mp4")


@router.post("/youtube", response_model=VideoAsset)
def create_youtube_video(project_id: str, payload: YouTubeVideoRequest) -> VideoAsset:
    directory = require_project_dir(project_id)
    if not payload.rights_confirmed:
        asset_id = str(uuid4())
        video = VideoAsset(
            project_id=project_id,
            asset_id=asset_id,
            source_type="youtube",
            uri=payload.url,
            original_input=payload.model_dump(),
            pipeline_output={"downloader": None, "reference_only": True},
        )
        write_json_model(directory / "video.json", video)
        _write_youtube_source(directory, project_id, asset_id, payload, downloaded_with_permission=False)
        return video

    if importlib.util.find_spec("yt_dlp") is None:
        raise api_error(
            501,
            "YOUTUBE_DOWNLOADER_UNAVAILABLE",
            "YouTube download is not configured in this environment.",
            {"url": payload.url, "missing_optional_dependency": "yt_dlp"},
            "Install optional YouTube downloader or use local MP4 upload for MVP demo.",
        )

    yt_dlp = importlib.import_module("yt_dlp")
    asset_id = str(uuid4())
    destination_template = str(directory / "videos" / f"{asset_id}.%(ext)s")
    options = {"format": "mp4/bestvideo+bestaudio/best", "outtmpl": destination_template, "quiet": True}
    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(payload.url, download=True)
    downloaded = next((directory / "videos").glob(f"{asset_id}.*"), None)
    video = VideoAsset(
        project_id=project_id,
        asset_id=asset_id,
        source_type="youtube",
        uri=str(downloaded) if downloaded else payload.url,
        filename=downloaded.name if downloaded else None,
        content_type="video/mp4" if downloaded and downloaded.suffix == ".mp4" else None,
        duration_seconds=info.get("duration"),
        original_input=payload.model_dump(),
        pipeline_output={"downloader": "yt_dlp", "title": info.get("title")},
    )
    write_json_model(directory / "video.json", video)
    _write_youtube_source(directory, project_id, asset_id, payload, title=info.get("title"), downloaded_with_permission=True)
    return video


@frames_router.post("/extract", response_model=ExtractFramesResponse)
def extract_project_frames(project_id: str, payload: ExtractFramesRequest) -> ExtractFramesResponse:
    _validate_body_project_id(project_id, payload.project_id)
    directory = require_project_dir(project_id)
    video_doc = VideoAsset.model_validate(read_json(directory / "video.json"))
    if payload.video_asset_id != video_doc.asset_id:
        raise api_error(
            404,
            "VIDEO_ASSET_NOT_FOUND",
            "Requested video_asset_id does not match the project's current video asset.",
            {"requested": payload.video_asset_id, "current": video_doc.asset_id},
            "Use the asset_id returned by the video upload or YouTube endpoint.",
        )
    if not video_doc.uri or not Path(video_doc.uri).exists():
        raise api_error(
            404,
            "VIDEO_FILE_NOT_FOUND",
            "The source video file is not available on disk.",
            {"uri": video_doc.uri},
            "Upload a local MP4 before extracting frames, or configure the YouTube downloader.",
        )

    output_dir = directory / "frames" / "images"
    target_fps = payload.target_fps or 1.0
    every_n_frames = max(1, round((video_doc.fps or 30.0) / target_fps))
    try:
        frame_paths = extract_frames(
            Path(video_doc.uri),
            output_dir,
            every_n_frames=every_n_frames,
            sample_rate=target_fps,
            max_frames=payload.max_frames,
        )
    except FrameExtractionError as exc:
        raise api_error(
            422,
            "FRAME_EXTRACTION_FAILED",
            str(exc),
            {"uri": video_doc.uri},
            "Verify the video path, codec support, and OpenCV installation before retrying.",
        ) from exc

    raw_index = read_json(directory / "frames" / "index.json")
    raw_frames = raw_index.get("frames", [])
    frames = [
        FrameAsset(
            frame_id=item["frame_id"],
            frame_index=int(item["frame_index"]),
            timestamp_seconds=float(item["timestamp_seconds"]),
            image_path=str(item["image_path"]),
            width=item.get("width"),
            height=item.get("height"),
            metadata=item.get("metadata", {}),
        )
        for item in raw_frames[: len(frame_paths)]
    ]
    response = ExtractFramesResponse(
        project_id=project_id,
        request=payload,
        frames=frames,
        original_input=payload.model_dump(),
        pipeline_output={"frame_count": len(frames), "extractor": "opencv", "every_n_frames": every_n_frames},
        debug_metadata={"source_video": video_doc.uri},
    )
    write_json_model(directory / "frames" / "index.json", response)
    return response


@frames_router.get("/{frame_index}")
def get_project_frame(project_id: str, frame_index: int) -> FileResponse:
    directory = require_project_dir(project_id)
    frame_index_doc = ExtractFramesResponse.model_validate(read_json(directory / "frames" / "index.json"))
    frame = next((item for item in frame_index_doc.frames if item.frame_index == frame_index), None)
    if frame is None:
        raise api_error(
            404,
            "FRAME_NOT_FOUND",
            "Requested frame index was not found in the extracted frame index.",
            {"frame_index": frame_index},
            "Call POST /api/projects/{project_id}/frames/extract and request an existing frame_index.",
        )
    frame_path = assert_path_child(Path(frame.image_path), directory)
    if not frame_path.exists():
        raise api_error(
            404,
            "FRAME_IMAGE_NOT_FOUND",
            "Frame metadata exists, but the image file is missing.",
            {"image_path": str(frame_path)},
            "Re-run frame extraction to recreate missing images.",
        )
    return FileResponse(frame_path)
