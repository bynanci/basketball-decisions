"""Project image-space player tracks onto 2D court coordinates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.pipeline.homography import image_to_court


def bbox_bottom_center(bbox: list[float]) -> tuple[float, float]:
    """Return the bottom-center foot point for an ``[x, y, width, height]`` bbox."""

    x, y, width, height = [float(value) for value in bbox]
    return x + width / 2.0, y + height


def project_tracks_to_court(
    tracks: list[dict[str, Any]],
    homography: list[list[float]] | None = None,
) -> list[dict[str, Any]]:
    """Project player track bboxes/points into 2D court coordinates.

    For bbox-based track points, the bottom-center is used as the player's foot
    point before applying the homography.
    """

    projected_tracks: list[dict[str, Any]] = []
    for track in tracks:
        points: list[dict[str, Any]] = []
        source_points = track.get("points")
        if source_points is None and "bbox" in track:
            source_points = [track]
        for point in source_points or []:
            if "bbox" in point:
                image_x, image_y = bbox_bottom_center(point["bbox"])
            else:
                image_x = float(point["image_point_x"])
                image_y = float(point["image_point_y"])
            if homography is None:
                court_x, court_y = image_x, image_y
                homography_applied = False
            else:
                court_x, court_y = image_to_court((image_x, image_y), homography)
                homography_applied = True
            points.append(
                {
                    "frame_id": point.get("frame_id"),
                    "frame_index": point.get("frame_index"),
                    "timestamp_seconds": point.get("timestamp_seconds"),
                    "court_x": court_x,
                    "court_y": court_y,
                    "source_image_point_x": image_x,
                    "source_image_point_y": image_y,
                    "confidence": point.get("confidence") or point.get("score"),
                    "metadata": {"homography_applied": homography_applied},
                }
            )
        projected_tracks.append(
            {
                "track_id": track["track_id"],
                "player_id": track.get("player_id"),
                "points": points,
                "metadata": {"projection_source": "bbox_bottom_center"},
            }
        )
    return projected_tracks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project player tracks onto 2D court coordinates.")
    parser.add_argument("tracks_json", type=Path)
    parser.add_argument("homography_json", type=Path, help="JSON matrix or object containing homography/matrix.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    tracks_data = json.loads(args.tracks_json.read_text(encoding="utf-8"))
    homography_data = json.loads(args.homography_json.read_text(encoding="utf-8"))
    tracks = tracks_data.get("tracks", tracks_data) if isinstance(tracks_data, dict) else tracks_data
    homography = (
        homography_data.get("homography") or homography_data.get("matrix")
        if isinstance(homography_data, dict)
        else homography_data
    )
    result = {"projected_tracks": project_tracks_to_court(tracks, homography)}
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
