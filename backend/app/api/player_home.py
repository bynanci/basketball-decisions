from __future__ import annotations

from fastapi import APIRouter, Query

from app.models import PlayerHomeResponse
from app.services.player_home_service import build_player_home

router = APIRouter(prefix="/player-home", tags=["player-home"])


@router.get("", response_model=PlayerHomeResponse)
def read_player_home(player_key: str = Query(..., min_length=1)) -> PlayerHomeResponse:
    return build_player_home(player_key)
