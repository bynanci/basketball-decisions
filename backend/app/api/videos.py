from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)) -> dict[str, str]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    video_id = str(uuid4())
    destination = UPLOAD_DIR / f"{video_id}{suffix}"
    destination.write_bytes(await file.read())
    return {"video_id": video_id, "filename": file.filename or destination.name, "path": str(destination)}
