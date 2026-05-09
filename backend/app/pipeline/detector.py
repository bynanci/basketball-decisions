from pathlib import Path
from typing import Any


def detect_players(frame_path: Path | None = None) -> list[dict[str, Any]]:
    """Return deterministic demo detections until a model is wired in."""
    _ = frame_path
    return [
        {"id": "det-1", "label": "player", "bbox": [320, 220, 48, 120], "score": 0.91},
        {"id": "det-2", "label": "player", "bbox": [480, 210, 52, 126], "score": 0.88},
    ]
