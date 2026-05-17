"""Player Value trend helpers that preserve project-scoped identities."""

from __future__ import annotations

from app.models import PlayerValueTrendPoint

BASELINE_FIELDS = (
    "player_value_formula_version",
    "recognition_model_version",
    "decision_rule_set_version",
    "dataset_fingerprint",
)


def mixed_baseline_warnings(points: list[PlayerValueTrendPoint]) -> list[str]:
    """Return explicit warnings when a trend spans multiple build baselines."""

    warnings: list[str] = []
    for field in BASELINE_FIELDS:
        values = {getattr(point, field) for point in points}
        if len(values) > 1:
            warnings.append(
                f"Mixed baseline warning: trend points use multiple {field} values ({', '.join(sorted(str(value) for value in values))}). "
                "Compare scores cautiously and do not hide this warning."
            )
    return warnings
