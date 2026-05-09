from typing import Any


def project_tracks_to_court(tracks: list[dict[str, Any]], homography: list[list[float]] | None = None) -> list[dict[str, Any]]:
    """Project track foot points onto a 2D court using a placeholder transform."""
    _ = homography
    projected = []
    for index, track in enumerate(tracks):
        projected.append(
            {
                "track_id": track["track_id"],
                "court_x": 10 + index * 12,
                "court_y": 20 + index * 4,
            }
        )
    return projected
