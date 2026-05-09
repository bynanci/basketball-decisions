from fastapi import APIRouter
from pydantic import BaseModel

from app.pipeline.detector import detect_players
from app.pipeline.projector import project_tracks_to_court
from app.pipeline.tracker import build_tracks

router = APIRouter(prefix="/tracking", tags=["tracking"])


class TrackingRequest(BaseModel):
    project_id: str


@router.post("/demo")
def run_tracking_demo(payload: TrackingRequest) -> dict[str, object]:
    detections = detect_players()
    tracks = build_tracks(detections)
    projected = project_tracks_to_court(tracks)
    return {
        "project_id": payload.project_id,
        "status": "stub",
        "detections": detections,
        "tracks": tracks,
        "projected": projected,
    }
