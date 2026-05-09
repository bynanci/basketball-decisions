from typing import Any


def build_tracks(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign placeholder track IDs to detector outputs."""
    return [
        {
            "track_id": f"track-{index + 1}",
            "bbox": detection["bbox"],
            "label": detection["label"],
            "score": detection["score"],
        }
        for index, detection in enumerate(detections)
    ]
