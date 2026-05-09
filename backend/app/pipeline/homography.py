from __future__ import annotations

from typing import Any


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve Ax=b with Gaussian elimination for small MVP homography systems."""

    n = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for pivot_index in range(n):
        pivot_row = max(range(pivot_index, n), key=lambda row: abs(augmented[row][pivot_index]))
        if abs(augmented[pivot_row][pivot_index]) < 1e-12:
            raise ValueError("Keypoints do not produce a solvable homography system.")
        augmented[pivot_index], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_index]
        pivot = augmented[pivot_index][pivot_index]
        augmented[pivot_index] = [value / pivot for value in augmented[pivot_index]]
        for row_index in range(n):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            augmented[row_index] = [
                value - factor * augmented[pivot_index][column_index]
                for column_index, value in enumerate(augmented[row_index])
            ]
    return [row[-1] for row in augmented]


def estimate_homography(image_points: list[dict[str, float]], court_points: list[dict[str, float]]) -> dict[str, Any]:
    """Estimate a 3x3 image-to-court homography from four or more point pairs.

    This pure-Python implementation fixes h33=1 and solves the normal equations
    for the remaining eight coefficients. It is intentionally small so the MVP
    API can calibrate projects without requiring OpenCV or NumPy.
    """

    if len(image_points) != len(court_points):
        raise ValueError("image_points and court_points must contain the same number of points.")
    if len(image_points) < 4:
        raise ValueError("At least four keypoint pairs are required to estimate homography.")

    design_rows: list[list[float]] = []
    targets: list[float] = []
    for image_point, court_point in zip(image_points, court_points, strict=True):
        x = float(image_point["x"])
        y = float(image_point["y"])
        u = float(court_point["x"])
        v = float(court_point["y"])
        design_rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        targets.append(u)
        design_rows.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        targets.append(v)

    normal_matrix = [[0.0 for _ in range(8)] for _ in range(8)]
    normal_vector = [0.0 for _ in range(8)]
    for row, target in zip(design_rows, targets, strict=True):
        for i in range(8):
            normal_vector[i] += row[i] * target
            for j in range(8):
                normal_matrix[i][j] += row[i] * row[j]

    h = _solve_linear_system(normal_matrix, normal_vector)
    matrix = [
        [h[0], h[1], h[2]],
        [h[3], h[4], h[5]],
        [h[6], h[7], 1.0],
    ]
    return {
        "status": "computed",
        "image_points": image_points,
        "court_points": court_points,
        "matrix": matrix,
    }
