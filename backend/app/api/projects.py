import importlib.util
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from backend.app.core.errors import api_error
from backend.app.models import (
    DetectionTrack,
    ExtractFramesRequest,
    ExtractFramesResponse,
    FrameAsset,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectRecord,
    RunTrackingRequest,
    RunTrackingResponse,
    SaveCalibrationRequest,
    SaveCalibrationResponse,
    TrackPoint,
    VideoAsset,
    YouTubeVideoRequest,
)
from backend.app.services.homography import compute_homography, mean_reprojection_error, project_point
from backend.app.services.storage import (
    PROJECTS_INDEX,
    ensure_data_dirs,
    project_dir,
    read_model,
    read_model_list,
    write_model,
    write_model_list,
)

router = APIRouter(prefix="/api", tags=["projects"])


def _project_meta_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def _video_path(project_id: str) -> Path:
    return project_dir(project_id) / "video.json"


def _frames_path(project_id: str) -> Path:
    return project_dir(project_id) / "frames.json"


def _calibration_path(project_id: str) -> Path:
    return project_dir(project_id) / "calibration.json"


def _tracks_path(project_id: str) -> Path:
    return project_dir(project_id) / "tracks.json"


def _require_project(project_id: str) -> ProjectRecord:
    path = _project_meta_path(project_id)
    if not path.exists():
        raise api_error(
            404,
            "project_not_found",
            "Project was not found.",
            details={"project_id": project_id},
            debug_hint="Create the project with POST /api/projects before calling project-scoped routes.",
        )
    return read_model(path, ProjectRecord)


def _require_video(project_id: str) -> VideoAsset:
    path = _video_path(project_id)
    if not path.exists():
        raise api_error(
            404,
            "video_not_found",
            "No video asset is attached to this project.",
            details={"project_id": project_id},
            debug_hint="Upload an MP4 or import a YouTube video before extracting frames.",
        )
    return read_model(path, VideoAsset)


def _load_calibration_matrix(project_id: str) -> list[list[float]] | None:
    path = _calibration_path(project_id)
    if not path.exists():
        return None
    return read_model(path, SaveCalibrationResponse).homography_matrix


def _media_type_for(path: Path) -> str:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if path.suffix.lower() == ".png":
        return "image/png"
    if path.suffix.lower() == ".svg":
        return "image/svg+xml"
    return "application/octet-stream"


@router.post("/projects", response_model=ProjectCreateResponse, status_code=201)
def create_project(request: ProjectCreateRequest) -> ProjectCreateResponse:
    ensure_data_dirs()
    project = ProjectRecord(
        name=request.name,
        description=request.description,
        metadata=request.metadata,
    )
    write_model(_project_meta_path(project.id), project)

    projects = read_model_list(PROJECTS_INDEX, ProjectRecord)
    projects.append(project)
    write_model_list(PROJECTS_INDEX, projects)
    return ProjectCreateResponse(project=project)


@router.post("/projects/{project_id}/video/upload", response_model=VideoAsset)
async def upload_video(project_id: str, file: UploadFile = File(...)) -> VideoAsset:
    _require_project(project_id)
    filename = file.filename or "upload.mp4"
    if not filename.lower().endswith(".mp4"):
        raise api_error(
            415,
            "unsupported_video_type",
            "Only MP4 uploads are supported.",
            details={"filename": filename, "content_type": file.content_type},
            debug_hint="Send multipart/form-data with a file field whose filename ends in .mp4.",
        )

    videos_dir = project_dir(project_id) / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    destination = videos_dir / "source.mp4"
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            output.write(chunk)

    asset = VideoAsset(
        project_id=project_id,
        source_type="upload",
        filename=filename,
        content_type=file.content_type or "video/mp4",
        path=str(destination),
        size_bytes=size,
    )
    write_model(_video_path(project_id), asset)
    return asset


@router.post("/projects/{project_id}/video/youtube", response_model=VideoAsset)
def import_youtube_video(project_id: str, request: YouTubeVideoRequest) -> VideoAsset:
    _require_project(project_id)
    downloader = shutil.which("yt-dlp")
    if downloader is None:
        raise api_error(
            501,
            "youtube_downloader_unavailable",
            "YouTube import is not configured in this MVP environment.",
            details={
                "url": str(request.url),
                "required_binary": "yt-dlp",
                "todo": "Install/configure yt-dlp or replace this stub with a managed downloader service.",
            },
            debug_hint="MP4 upload is available now; YouTube import is intentionally stubbed until a downloader exists.",
        )

    videos_dir = project_dir(project_id) / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    destination_template = str(videos_dir / "youtube.%(ext)s")
    try:
        subprocess.run(
            [
                downloader,
                "--no-playlist",
                "--merge-output-format",
                "mp4",
                "-o",
                destination_template,
                str(request.url),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.CalledProcessError as exc:
        raise api_error(
            502,
            "youtube_download_failed",
            "The configured YouTube downloader failed.",
            details={"stderr": exc.stderr[-2000:], "stdout": exc.stdout[-2000:]},
            debug_hint="Verify yt-dlp can access the URL and that ffmpeg is available for MP4 merging.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise api_error(
            504,
            "youtube_download_timeout",
            "The YouTube download timed out.",
            details={"timeout_seconds": exc.timeout},
            debug_hint="Retry with a shorter source video or increase the backend timeout.",
        ) from exc

    destination = videos_dir / "youtube.mp4"
    if not destination.exists():
        candidates = sorted(videos_dir.glob("youtube.*"))
        if candidates:
            destination = candidates[0]
    if not destination.exists():
        raise api_error(
            502,
            "youtube_download_missing_output",
            "The YouTube downloader completed without producing a video file.",
            details={"output_template": destination_template},
            debug_hint="Check yt-dlp output naming and merge settings.",
        )

    asset = VideoAsset(
        project_id=project_id,
        source_type="youtube",
        filename=destination.name,
        path=str(destination),
        size_bytes=destination.stat().st_size,
    )
    write_model(_video_path(project_id), asset)
    return asset


def _extract_frames_with_opencv(
    video: VideoAsset,
    output_dir: Path,
    request: ExtractFramesRequest,
) -> list[FrameAsset] | None:
    if importlib.util.find_spec("cv2") is None:
        return None

    import cv2  # type: ignore[import-not-found]

    capture = cv2.VideoCapture(video.path)
    if not capture.isOpened():
        raise api_error(
            422,
            "video_open_failed",
            "OpenCV could not open the project video.",
            details={"video_path": video.path},
            debug_hint="Confirm the uploaded file is a valid MP4 and the runtime has the required codecs.",
        )

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    start_frame = int(request.start_seconds * fps)
    step = max(1, int(request.every_n_seconds * fps))
    frames: list[FrameAsset] = []
    frame_number = start_frame
    while len(frames) < request.max_frames:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, image = capture.read()
        if not ok:
            break
        frame_index = len(frames)
        path = output_dir / f"{frame_index:06d}.jpg"
        cv2.imwrite(str(path), image)
        height, width = image.shape[:2]
        frames.append(
            FrameAsset(
                project_id=video.project_id,
                frame_index=frame_index,
                timestamp_seconds=frame_number / fps,
                path=str(path),
                width=width,
                height=height,
            )
        )
        frame_number += step
    capture.release()
    return frames


def _extract_frames_with_ffmpeg(
    video: VideoAsset,
    output_dir: Path,
    request: ExtractFramesRequest,
) -> list[FrameAsset] | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None

    output_pattern = output_dir / "%06d.jpg"
    vf = f"fps=1/{request.every_n_seconds}"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(request.start_seconds),
        "-i",
        video.path,
        "-vf",
        vf,
        "-frames:v",
        str(request.max_frames),
        str(output_pattern),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
    except subprocess.CalledProcessError as exc:
        raise api_error(
            422,
            "frame_extraction_failed",
            "ffmpeg could not extract frames from the project video.",
            details={"stderr": exc.stderr[-2000:], "stdout": exc.stdout[-2000:]},
            debug_hint="Confirm the uploaded file is a valid MP4 and ffmpeg supports its codec.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise api_error(
            504,
            "frame_extraction_timeout",
            "Frame extraction timed out.",
            details={"timeout_seconds": exc.timeout},
            debug_hint="Retry with a larger every_n_seconds value or a smaller max_frames value.",
        ) from exc

    paths = sorted(output_dir.glob("*.jpg"))[: request.max_frames]
    return [
        FrameAsset(
            project_id=video.project_id,
            frame_index=index,
            timestamp_seconds=request.start_seconds + index * request.every_n_seconds,
            path=str(path),
        )
        for index, path in enumerate(paths)
    ]


@router.post("/projects/{project_id}/frames/extract", response_model=ExtractFramesResponse)
def extract_frames(project_id: str, request: ExtractFramesRequest) -> ExtractFramesResponse:
    _require_project(project_id)
    video = _require_video(project_id)
    output_dir = project_dir(project_id) / "frames"
    if output_dir.exists() and any(output_dir.iterdir()) and not request.overwrite:
        frames = read_model_list(_frames_path(project_id), FrameAsset)
        return ExtractFramesResponse(project_id=project_id, video_id=video.id, frames=frames, count=len(frames))

    if request.overwrite and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = _extract_frames_with_opencv(video, output_dir, request)
    if frames is None:
        frames = _extract_frames_with_ffmpeg(video, output_dir, request)
    if frames is None:
        raise api_error(
            501,
            "frame_extractor_unavailable",
            "Frame extraction requires OpenCV or ffmpeg, but neither is available.",
            details={
                "project_id": project_id,
                "video_path": video.path,
                "required_options": ["opencv-python", "ffmpeg"],
                "todo": "Install opencv-python or provide an ffmpeg binary in PATH for frame extraction.",
            },
            debug_hint="Unlike tracking, frame extraction does not return placeholder images because downstream calibration needs real video frames.",
        )

    write_model_list(_frames_path(project_id), frames)
    return ExtractFramesResponse(project_id=project_id, video_id=video.id, frames=frames, count=len(frames))


@router.get("/projects/{project_id}/frames/{frame_index}")
def get_frame(project_id: str, frame_index: int) -> FileResponse:
    _require_project(project_id)
    frames = read_model_list(_frames_path(project_id), FrameAsset)
    for frame in frames:
        if frame.frame_index == frame_index:
            path = Path(frame.path)
            if not path.exists():
                raise api_error(
                    404,
                    "frame_file_not_found",
                    "The frame metadata exists but the image file is missing.",
                    details={"project_id": project_id, "frame_index": frame_index, "path": frame.path},
                    debug_hint="Re-run POST /api/projects/{project_id}/frames/extract with overwrite=true.",
                )
            return FileResponse(path, media_type=_media_type_for(path), filename=path.name)
    raise api_error(
        404,
        "frame_not_found",
        "Frame was not found for this project.",
        details={"project_id": project_id, "frame_index": frame_index},
        debug_hint="Extract frames first and use one of the returned frame_index values.",
    )


@router.post("/projects/{project_id}/calibration", response_model=SaveCalibrationResponse)
def save_calibration(project_id: str, request: SaveCalibrationRequest) -> SaveCalibrationResponse:
    _require_project(project_id)
    image_points = [keypoint.image for keypoint in request.keypoints]
    court_points = [keypoint.court for keypoint in request.keypoints]
    try:
        matrix = compute_homography(image_points, court_points)
        error = mean_reprojection_error(matrix, image_points, court_points)
    except ValueError as exc:
        raise api_error(
            422,
            "homography_failed",
            "Could not compute a homography from the supplied keypoints.",
            details={"reason": str(exc)},
            debug_hint="Provide at least four non-collinear image/court point pairs.",
        ) from exc

    response = SaveCalibrationResponse(
        project_id=project_id,
        keypoints=request.keypoints,
        homography_matrix=matrix,
        reprojection_error=error,
    )
    write_model(_calibration_path(project_id), response)
    return response


def _run_yolo_tracking(project_id: str, request: RunTrackingRequest) -> list[DetectionTrack] | None:
    if importlib.util.find_spec("ultralytics") is None:
        return None

    from ultralytics import YOLO  # type: ignore[import-not-found]

    frames = read_model_list(_frames_path(project_id), FrameAsset)
    if not frames:
        return []
    model = YOLO("yolov8n.pt")
    matrix = _load_calibration_matrix(project_id)
    points: list[TrackPoint] = []
    selected_frames = frames[:: request.frame_stride]
    if request.max_frames is not None:
        selected_frames = selected_frames[: request.max_frames]

    for frame in selected_frames:
        results = model(frame.path, classes=[0], conf=request.confidence_threshold, verbose=False)
        if not results:
            continue
        for box in results[0].boxes:
            xyxy = [float(value) for value in box.xyxy[0].tolist()]
            center_x = (xyxy[0] + xyxy[2]) / 2
            foot_y = xyxy[3]
            court_x = court_y = None
            if matrix is not None:
                court_x, court_y = project_point(matrix, center_x, foot_y)
            points.append(
                TrackPoint(
                    frame_index=frame.frame_index,
                    timestamp_seconds=frame.timestamp_seconds,
                    bbox_xyxy=xyxy,
                    confidence=float(box.conf[0]) if box.conf is not None else None,
                    court_x=court_x,
                    court_y=court_y,
                )
            )
    return [DetectionTrack(track_id="person-0", points=points)] if points else []


def _stub_tracking(project_id: str, request: RunTrackingRequest) -> list[DetectionTrack]:
    frames = read_model_list(_frames_path(project_id), FrameAsset)
    if request.max_frames is not None:
        frames = frames[: request.max_frames]
    matrix = _load_calibration_matrix(project_id)
    points: list[TrackPoint] = []
    for frame in frames[:: request.frame_stride]:
        width = frame.width or 1280
        height = frame.height or 720
        x1 = width * 0.45
        y1 = height * 0.35
        x2 = width * 0.55
        y2 = height * 0.85
        court_x = court_y = None
        if matrix is not None:
            court_x, court_y = project_point(matrix, (x1 + x2) / 2, y2)
        points.append(
            TrackPoint(
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                bbox_xyxy=[x1, y1, x2, y2],
                confidence=0.0,
                court_x=court_x,
                court_y=court_y,
            )
        )
    return [DetectionTrack(track_id="stub-person-0", points=points)]


@router.post("/projects/{project_id}/tracking/run", response_model=RunTrackingResponse)
def run_tracking(project_id: str, request: RunTrackingRequest) -> RunTrackingResponse:
    _require_project(project_id)
    if not _frames_path(project_id).exists():
        raise api_error(
            404,
            "frames_not_found",
            "No extracted frames are available for tracking.",
            details={"project_id": project_id},
            debug_hint="Run POST /api/projects/{project_id}/frames/extract before tracking.",
        )

    tracks = _run_yolo_tracking(project_id, request)
    status = "completed"
    message = "Tracking completed with YOLO person class."
    details = {"detector": "ultralytics-yolo", "class": "person"}
    if tracks is None:
        if not request.use_stub_when_unavailable:
            raise api_error(
                501,
                "tracker_unavailable",
                "YOLO tracking is not configured and stub fallback was disabled.",
                details={"required_package": "ultralytics"},
                debug_hint="Install ultralytics or set use_stub_when_unavailable=true for MVP stub output.",
            )
        tracks = _stub_tracking(project_id, request)
        status = "stubbed"
        message = "YOLO is unavailable; returned deterministic MVP stub person tracks."
        details = {"detector": "stub", "todo": "Install/configure ultralytics YOLO for production person detection."}

    response = RunTrackingResponse(
        project_id=project_id,
        status=status,
        tracks=tracks,
        message=message,
        details=details,
    )
    write_model(_tracks_path(project_id), response)
    return response


@router.get("/projects/{project_id}/tracks", response_model=RunTrackingResponse)
def get_tracks(project_id: str) -> RunTrackingResponse:
    _require_project(project_id)
    path = _tracks_path(project_id)
    if not path.exists():
        raise api_error(
            404,
            "tracks_not_found",
            "No tracking output is available for this project.",
            details={"project_id": project_id},
            debug_hint="Run POST /api/projects/{project_id}/tracking/run before requesting tracks.",
        )
    return read_model(path, RunTrackingResponse)
