from math import sqrt

from backend.app.models import CourtPoint, ImagePoint


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("Calibration points do not define a stable homography.")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [value - factor * aug[col][idx] for idx, value in enumerate(aug[row])]
    return [aug[row][-1] for row in range(n)]


def compute_homography(image_points: list[ImagePoint], court_points: list[CourtPoint]) -> list[list[float]]:
    if len(image_points) != len(court_points) or len(image_points) < 4:
        raise ValueError("At least four image/court point pairs are required.")

    ata = [[0.0 for _ in range(8)] for _ in range(8)]
    atb = [0.0 for _ in range(8)]
    for image, court in zip(image_points, court_points, strict=True):
        x, y = image.x, image.y
        u, v = court.x, court.y
        rows = [
            ([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y], u),
            ([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y], v),
        ]
        for row, target in rows:
            for i in range(8):
                atb[i] += row[i] * target
                for j in range(8):
                    ata[i][j] += row[i] * row[j]

    h = _solve_linear_system(ata, atb)
    return [
        [h[0], h[1], h[2]],
        [h[3], h[4], h[5]],
        [h[6], h[7], 1.0],
    ]


def project_point(matrix: list[list[float]], x: float, y: float) -> tuple[float, float]:
    denom = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2]
    if abs(denom) < 1e-12:
        raise ValueError("Point cannot be projected because homogeneous denominator is zero.")
    court_x = (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / denom
    court_y = (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / denom
    return court_x, court_y


def mean_reprojection_error(
    matrix: list[list[float]],
    image_points: list[ImagePoint],
    court_points: list[CourtPoint],
) -> float:
    if not image_points:
        return 0.0
    total = 0.0
    for image, court in zip(image_points, court_points, strict=True):
        px, py = project_point(matrix, image.x, image.y)
        total += sqrt((px - court.x) ** 2 + (py - court.y) ** 2)
    return total / len(image_points)
