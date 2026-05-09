"""Person detector backed by Ultralytics YOLO with a deterministic stub fallback."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any

Detection = dict[str, Any]


def _ultralytics_available() -> bool:
    return importlib.util.find_spec("ultralytics") is not None


def detect_players_in_frame(
    frame_path: Path | str | None,
    confidence_threshold: float = 0.25,
    model_name: str = "yolov8n.pt",
) -> dict[str, Any]:
    """Detect people in one frame.

    When ``ultralytics`` is unavailable, this function returns an empty,
    deterministic detection list and metadata with ``detector_mode: "stub"``.
    """

    if not _ultralytics_available():
        return {
            "detections": [],
            "metadata": {
                "detector_mode": "stub",
                "reason": "ultralytics package is not installed",
                "model_name": model_name,
            },
        }

    if frame_path is None:
        return {
            "detections": [],
            "metadata": {"detector_mode": "yolo", "reason": "frame_path was not provided", "model_name": model_name},
        }

    ultralytics = importlib.import_module("ultralytics")
    model = ultralytics.YOLO(model_name)
    results = model.predict(str(frame_path), conf=confidence_threshold, classes=[0], verbose=False)

    detections: list[Detection] = []
    for result in results:
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for index, box in enumerate(boxes):
            class_id = int(box.cls.item()) if hasattr(box.cls, "item") else int(box.cls[0])
            class_name = names.get(class_id, str(class_id))
            if class_id != 0 and class_name != "person":
                continue
            confidence = float(box.conf.item()) if hasattr(box.conf, "item") else float(box.conf[0])
            if confidence < confidence_threshold:
                continue
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            detections.append(
                {
                    "id": f"det-{len(detections) + 1}",
                    "label": "person",
                    "class_name": "person",
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                    "score": confidence,
                    "metadata": {"class_id": class_id, "source_index": index},
                }
            )
    return {
        "detections": detections,
        "metadata": {"detector_mode": "yolo", "model_name": model_name, "confidence_threshold": confidence_threshold},
    }


def detect_players(frame_path: Path | str | None = None, confidence_threshold: float = 0.25) -> list[Detection]:
    """Backward-compatible helper returning only detection dictionaries."""

    return detect_players_in_frame(frame_path, confidence_threshold=confidence_threshold)["detections"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect person/player bounding boxes in an image frame.")
    parser.add_argument("frame_path", type=Path)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    result = detect_players_in_frame(args.frame_path, confidence_threshold=args.confidence, model_name=args.model)
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
