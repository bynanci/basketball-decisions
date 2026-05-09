from typing import Any


def estimate_homography(image_points: list[dict[str, float]], court_points: list[dict[str, float]]) -> dict[str, Any]:
    """Return a placeholder homography payload for manually marked keypoints."""
    return {
        "status": "stub",
        "image_points": image_points,
        "court_points": court_points,
        "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    }
