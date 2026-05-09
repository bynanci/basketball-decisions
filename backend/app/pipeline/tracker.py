"""Simple IoU/centroid player tracker for MVP basketball pipelines.

TODO: This MVP tracker does not handle occlusion, jersey ID, or team assignment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

Detection = dict[str, Any]
FrameDetections = dict[str, Any]


def _bbox_xywh(detection: Detection) -> list[float]:
    if "bbox" in detection:
        return [float(value) for value in detection["bbox"]]
    box = detection["box"]
    return [float(box["x"]), float(box["y"]), float(box["width"]), float(box["height"])]


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


def _centroid_distance(a: list[float], b: list[float]) -> float:
    ax, ay = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx, by = b[0] + b[2] / 2, b[1] + b[3] / 2
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def track_frame_detections(
    frame_detections: list[FrameDetections],
    iou_threshold: float = 0.3,
    max_centroid_distance: float = 80.0,
) -> list[dict[str, Any]]:
    """Assign track IDs across ordered frame detections using greedy matching."""

    tracks: dict[str, dict[str, Any]] = {}
    active_boxes: dict[str, list[float]] = {}
    next_track_number = 1

    for frame in sorted(frame_detections, key=lambda item: int(item.get("frame_index", 0))):
        frame_id = str(frame.get("frame_id", f"frame-{int(frame.get('frame_index', 0)):06d}"))
        frame_index = int(frame.get("frame_index", 0))
        timestamp_seconds = float(frame.get("timestamp_seconds", 0.0))
        assigned_tracks: set[str] = set()

        for detection in frame.get("detections", []):
            bbox = _bbox_xywh(detection)
            best_track_id: str | None = None
            best_iou = 0.0
            best_distance = float("inf")
            for track_id, previous_box in active_boxes.items():
                if track_id in assigned_tracks:
                    continue
                overlap = _iou(bbox, previous_box)
                distance = _centroid_distance(bbox, previous_box)
                if overlap > best_iou or (best_iou == 0.0 and distance < best_distance):
                    best_track_id = track_id
                    best_iou = overlap
                    best_distance = distance

            if best_track_id is None or (best_iou < iou_threshold and best_distance > max_centroid_distance):
                best_track_id = f"track-{next_track_number}"
                next_track_number += 1
                tracks[best_track_id] = {"track_id": best_track_id, "points": [], "metadata": {"tracker": "iou_centroid_mvp"}}

            assigned_tracks.add(best_track_id)
            active_boxes[best_track_id] = bbox
            tracks.setdefault(best_track_id, {"track_id": best_track_id, "points": [], "metadata": {"tracker": "iou_centroid_mvp"}})
            tracks[best_track_id]["points"].append(
                {
                    "frame_id": frame_id,
                    "frame_index": frame_index,
                    "timestamp_seconds": timestamp_seconds,
                    "bbox": bbox,
                    "detection_id": detection.get("detection_id") or detection.get("id"),
                    "confidence": detection.get("confidence") or detection.get("score"),
                }
            )

    return list(tracks.values())


def build_tracks(detections: list[Detection]) -> list[dict[str, Any]]:
    """Backward-compatible single-frame track assignment helper."""

    return [
        {
            "track_id": f"track-{index + 1}",
            "bbox": _bbox_xywh(detection),
            "label": detection.get("label") or detection.get("class_name", "person"),
            "score": detection.get("score") or detection.get("confidence"),
        }
        for index, detection in enumerate(detections)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Track frame detections with greedy IoU/centroid matching.")
    parser.add_argument("detections_json", type=Path, help="JSON list of frame detection objects.")
    parser.add_argument("--iou-threshold", type=float, default=0.3)
    parser.add_argument("--max-centroid-distance", type=float, default=80.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    data = json.loads(args.detections_json.read_text(encoding="utf-8"))
    frame_detections = data.get("frames", data) if isinstance(data, dict) else data
    result = {"tracks": track_frame_detections(frame_detections, args.iou_threshold, args.max_centroid_distance)}
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
