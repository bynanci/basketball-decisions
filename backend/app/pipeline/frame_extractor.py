from pathlib import Path


def extract_frames(video_path: Path, output_dir: Path, every_n_frames: int = 30) -> list[Path]:
    """Stub frame extractor.

    TODO: Use OpenCV or ffmpeg to extract frames from ``video_path`` into
    ``output_dir``. The current implementation creates the output directory and
    returns an empty list so the API can be exercised without media tooling.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return []
