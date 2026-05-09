"""Homography estimation and projection helpers."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Sequence

def _point_xy(point: dict[str, Any] | Sequence[float]) -> tuple[float, float]:
    if isinstance(point, dict):
        return float(point["x"]), float(point["y"])
    return float(point[0]), float(point[1])


def image_to_court(point: dict[str, Any] | Sequence[float], H: list[list[float]] | Any) -> tuple[float, float]:
    """Project one image-space point to court coordinates with homography ``H``."""

    x, y = _point_xy(point)
    h = [[float(value) for value in row] for row in H]
    projected = [
        h[0][0] * x + h[0][1] * y + h[0][2],
        h[1][0] * x + h[1][1] * y + h[1][2],
        h[2][0] * x + h[2][1] * y + h[2][2],
    ]
    denominator = float(projected[2])
    if abs(denominator) < 1e-12:
        raise ValueError("Homography projection denominator is too close to zero.")
    return float(projected[0] / denominator), float(projected[1] / denominator)


def residual_errors(
    image_points: list[dict[str, float] | Sequence[float]],
    court_points: list[dict[str, float] | Sequence[float]],
    H: list[list[float]] | Any,
) -> list[dict[str, float]]:
    """Return per-point reprojection residuals for homography debugging."""

    errors: list[dict[str, float]] = []
    for image_point, court_point in zip(image_points, court_points, strict=True):
        expected_x, expected_y = _point_xy(court_point)
        projected_x, projected_y = image_to_court(image_point, H)
        dx = projected_x - expected_x
        dy = projected_y - expected_y
        errors.append({"dx": dx, "dy": dy, "error": float((dx * dx + dy * dy) ** 0.5)})
    return errors


def estimate_homography(
    image_points: list[dict[str, float] | Sequence[float]],
    court_points: list[dict[str, float] | Sequence[float]],
) -> dict[str, Any]:
    """Estimate a 3x3 image-to-court homography using ``cv2.findHomography``."""

    if len(image_points) != len(court_points):
        raise ValueError("image_points and court_points must contain the same number of points.")
    if len(image_points) < 4:
        raise ValueError("At least four image_point -> court_point pairs are required.")

    if importlib.util.find_spec("cv2") is None or importlib.util.find_spec("numpy") is None:
        raise ValueError("OpenCV and NumPy dependencies are required. Install opencv-python-headless and numpy.")
    cv2 = importlib.import_module("cv2")
    np = importlib.import_module("numpy")
    image_array = np.asarray([_point_xy(point) for point in image_points], dtype=np.float64)
    court_array = np.asarray([_point_xy(point) for point in court_points], dtype=np.float64)
    matrix, mask = cv2.findHomography(image_array, court_array, method=0)
    if matrix is None:
        raise ValueError("cv2.findHomography could not compute a homography for the provided points.")

    matrix_list = matrix.astype(float).tolist()
    residuals = residual_errors(image_points, court_points, matrix_list)
    mean_error = sum(item["error"] for item in residuals) / len(residuals) if residuals else 0.0
    return {
        "status": "computed",
        "image_points": image_points,
        "court_points": court_points,
        "matrix": matrix_list,
        "debug": {
            "residuals": residuals,
            "mean_residual_error": mean_error,
            "inlier_mask": mask.ravel().astype(int).tolist() if mask is not None else None,
        },
    }


def _load_pairs(path: Path) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = data.get("pairs", data) if isinstance(data, dict) else data
    image_points = [pair["image_point"] for pair in pairs]
    court_points = [pair["court_point"] for pair in pairs]
    return image_points, court_points


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate an image-to-court homography from point-pair JSON.")
    parser.add_argument("pairs_json", type=Path, help="JSON list or {pairs: [...]} with image_point and court_point.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        result = estimate_homography(*_load_pairs(args.pairs_json))
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
