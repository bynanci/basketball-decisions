"""OpenCV-backed video frame extraction utilities and CLI."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any


class FrameExtractionError(RuntimeError):
    """Raised when a video cannot be opened or decoded for extraction."""


def _frame_filename(frame_index: int) -> str:
    return f"frame-{frame_index:06d}.jpg"


def extract_frames(
    video_path: Path,
    output_dir: Path,
    every_n_frames: int | None = None,
    sample_rate: float | None = None,
    max_frames: int | None = None,
) -> list[Path]:
    """Extract sampled frames from ``video_path`` into ``output_dir``.

    Args:
        video_path: Source video file readable by OpenCV ``cv2.VideoCapture``.
        output_dir: Directory where frame JPG files will be written.
        every_n_frames: Save one frame every N decoded frames. Used when
            ``sample_rate`` is not provided.
        sample_rate: Target samples per second. Converted to ``every_n_frames``
            using the video's FPS metadata.
        max_frames: Optional cap on the number of saved frames.

    Returns:
        Paths to the image files that were written.

    Raises:
        FrameExtractionError: If the video file is missing, cannot be opened, or
            OpenCV fails to write a sampled frame.
    """

    video_path = Path(video_path)
    output_dir = Path(output_dir)
    if not video_path.exists():
        raise FrameExtractionError(f"Video file does not exist: {video_path}")

    if importlib.util.find_spec("cv2") is None:
        raise FrameExtractionError("OpenCV dependency is not installed. Install opencv-python-headless to extract frames.")
    cv2 = importlib.import_module("cv2")
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FrameExtractionError(f"Unable to open video with OpenCV VideoCapture: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    if sample_rate is not None:
        if sample_rate <= 0:
            raise FrameExtractionError("sample_rate must be greater than 0.")
        step = max(1, round((fps or sample_rate) / sample_rate))
    else:
        step = max(1, int(every_n_frames or 1))

    saved_paths: list[Path] = []
    index_frames: list[dict[str, Any]] = []
    source_frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if source_frame_index % step == 0:
                image_path = output_dir / _frame_filename(source_frame_index)
                if not cv2.imwrite(str(image_path), frame):
                    raise FrameExtractionError(f"OpenCV failed to write extracted frame: {image_path}")
                timestamp_seconds = source_frame_index / fps if fps > 0 else 0.0
                saved_paths.append(image_path)
                index_frames.append(
                    {
                        "frame_id": f"frame-{source_frame_index:06d}",
                        "frame_index": source_frame_index,
                        "timestamp_seconds": timestamp_seconds,
                        "image_path": str(image_path),
                        "width": int(frame.shape[1]),
                        "height": int(frame.shape[0]),
                        "metadata": {"source_frame_index": source_frame_index, "sample_step": step},
                    }
                )
                if max_frames is not None and len(saved_paths) >= max_frames:
                    break
            source_frame_index += 1
    finally:
        capture.release()

    index = {
        "video_path": str(video_path),
        "output_dir": str(output_dir),
        "sample_rate": sample_rate,
        "every_n_frames": step,
        "max_frames": max_frames,
        "source_metadata": {"fps": fps, "frame_count": frame_count, "width": width, "height": height},
        "frame_count": len(saved_paths),
        "frames": index_frames,
    }
    (output_dir.parent / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return saved_paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract sampled frames from a video with OpenCV.")
    parser.add_argument("video_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--sample-rate", type=float, default=None, help="Target samples per second.")
    parser.add_argument("--every-n-frames", type=int, default=None, help="Save one frame every N frames.")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum frames to save.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        paths = extract_frames(
            args.video_path,
            args.output_dir,
            every_n_frames=args.every_n_frames,
            sample_rate=args.sample_rate,
            max_frames=args.max_frames,
        )
    except FrameExtractionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"ok": True, "frame_count": len(paths), "frames": [str(path) for path in paths]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
