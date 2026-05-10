"""Dataset health checks for Local Lab curated JSON/JSONL datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.dataset import (
    DatasetHealthResponse,
    DatasetHealthWarning,
    DatasetManifest,
    DecisionDatasetHealth,
    RecognitionDatasetHealth,
)
from app.models.base import utc_now

POSITIVE_LABELS = {"VALID_PLAYER_TRACK", "PLAYER", "GOOD_DECISION", "GOOD_READ", "ACCEPTABLE_READ"}
NEGATIVE_LABELS = {"FALSE_POSITIVE_TRACK", "FALSE_POSITIVE", "BAD_DECISION", "BAD_READ", "MISSED_READ"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _read_manifest(path: Path, dataset_type: str) -> DatasetManifest:
    if not path.exists():
        return DatasetManifest(dataset_type=dataset_type)  # type: ignore[arg-type]
    return DatasetManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _distribution(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        distribution[str(value)] = distribution.get(str(value), 0) + 1
    return dict(sorted(distribution.items()))


def _positive_negative_counts(labels: list[dict[str, Any]]) -> tuple[int, int]:
    positive = 0
    negative = 0
    for label in labels:
        value = label.get("label")
        if value in POSITIVE_LABELS:
            positive += 1
        elif value in NEGATIVE_LABELS:
            negative += 1
    return positive, negative


def _positive_negative_ratio(positive: int, negative: int) -> float | None:
    if negative == 0:
        return None
    return round(positive / negative, 4)


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _warning(code: str, severity: str, message: str, recommendation: str) -> DatasetHealthWarning:
    return DatasetHealthWarning(code=code, severity=severity, message=message, recommendation=recommendation)  # type: ignore[arg-type]


def recognition_health(datasets_dir: Path) -> RecognitionDatasetHealth:
    directory = datasets_dir / "recognition"
    samples = _read_jsonl(directory / "curated_samples.jsonl")
    labels = _read_jsonl(directory / "curated_labels.jsonl")
    manifest = _read_manifest(directory / "dataset_manifest.json", "recognition")

    label_distribution = _distribution(labels, "label")
    positive_count, negative_count = _positive_negative_counts(labels)
    total_labeled = positive_count + negative_count
    ratio = _positive_negative_ratio(positive_count, negative_count)
    source_project_ids = {str(row["project_id"]) for row in samples if row.get("project_id")}
    source_project_count = len(source_project_ids) or len(manifest.source_project_ids)

    warnings: list[DatasetHealthWarning] = []
    if len(samples) < 1000:
        warnings.append(_warning(
            "RECOGNITION_MINIMUM_SAMPLES",
            "HIGH",
            f"Recognition has {len(samples)} curated samples; baseline training target is at least 1,000.",
            "Curate more governed tracking projects and reviewer labels before starting local training.",
        ))
    if total_labeled == 0 or negative_count / total_labeled < 0.2:
        warnings.append(_warning(
            "RECOGNITION_NEGATIVE_COVERAGE",
            "MEDIUM",
            "Recognition negatives are below 20% of labeled positive/negative samples.",
            "Add more false-positive detections and false-positive tracks from tracking review exclusions.",
        ))
    if ratio is None and positive_count > 0 or ratio is not None and ratio > 5:
        warnings.append(_warning(
            "RECOGNITION_POSITIVE_NEGATIVE_IMBALANCE",
            "MEDIUM",
            "Recognition positive/negative ratio is greater than 5:1.",
            "Balance the curated dataset with additional false-positive examples before training.",
        ))
    if source_project_count < 3:
        warnings.append(_warning(
            "RECOGNITION_SOURCE_PROJECT_COVERAGE",
            "MEDIUM",
            f"Recognition uses {source_project_count} source projects; target is at least 3.",
            "Curate eligible samples from more projects to reduce project-specific bias.",
        ))
    missing_required = [label for label in ("FALSE_POSITIVE", "FALSE_POSITIVE_TRACK") if label_distribution.get(label, 0) == 0]
    if missing_required:
        warnings.append(_warning(
            "RECOGNITION_FALSE_POSITIVE_LABELS_MISSING",
            "HIGH",
            f"Recognition label distribution is missing: {', '.join(missing_required)}.",
            "Mark both false-positive detections and false-positive tracks in tracking review before training.",
        ))

    return RecognitionDatasetHealth(
        sample_count=len(samples),
        label_count=len(labels),
        positive_sample_count=positive_count,
        negative_sample_count=negative_count,
        positive_negative_ratio=ratio,
        label_distribution=label_distribution,
        source_project_count=source_project_count,
        skipped_project_count=manifest.skipped_project_count,
        has_minimum_samples=len(samples) >= 1000,
        has_balanced_labels=total_labeled > 0 and negative_count / total_labeled >= 0.2 and (ratio is not None and ratio <= 5),
        warnings=warnings,
    )


def _prompt_id(sample: dict[str, Any]) -> str | None:
    trace = sample.get("trace") if isinstance(sample.get("trace"), dict) else {}
    payload = sample.get("payload") if isinstance(sample.get("payload"), dict) else {}
    prompt = payload.get("prompt") if isinstance(payload.get("prompt"), dict) else {}
    attempt = payload.get("attempt") if isinstance(payload.get("attempt"), dict) else {}
    value = trace.get("prompt_id") or prompt.get("prompt_id") or attempt.get("prompt_id")
    return str(value) if value else None


def _prompt_field(sample: dict[str, Any], field: str) -> str | None:
    payload = sample.get("payload") if isinstance(sample.get("payload"), dict) else {}
    prompt = payload.get("prompt") if isinstance(payload.get("prompt"), dict) else {}
    value = prompt.get(field)
    return str(value) if value else None


def decision_health(datasets_dir: Path) -> DecisionDatasetHealth:
    directory = datasets_dir / "decision"
    samples = _read_jsonl(directory / "curated_samples.jsonl")
    labels = _read_jsonl(directory / "curated_labels.jsonl")

    prompt_ids = {prompt_id for sample in samples if (prompt_id := _prompt_id(sample))}
    option_samples = [sample for sample in samples if sample.get("sample_type") == "option"]
    attempt_samples = [sample for sample in samples if sample.get("sample_type") == "attempt"]
    positive_count, negative_count = _positive_negative_counts(labels)
    total_labeled = positive_count + negative_count
    ratio = _positive_negative_ratio(positive_count, negative_count)

    role_distribution: dict[str, int] = {}
    situation_distribution: dict[str, int] = {}
    for sample in samples:
        role = _prompt_field(sample, "court_role_target")
        situation = _prompt_field(sample, "situation_type")
        if role:
            role_distribution[role] = role_distribution.get(role, 0) + 1
        if situation:
            situation_distribution[situation] = situation_distribution.get(situation, 0) + 1

    missing_expected_values = 0
    for sample in option_samples:
        payload = sample.get("payload") if isinstance(sample.get("payload"), dict) else {}
        option = payload.get("option") if isinstance(payload.get("option"), dict) else {}
        if option.get("expected_value") is None:
            missing_expected_values += 1

    timed_out_attempts = 0
    for sample in attempt_samples:
        payload = sample.get("payload") if isinstance(sample.get("payload"), dict) else {}
        attempt = payload.get("attempt") if isinstance(payload.get("attempt"), dict) else {}
        if attempt.get("timed_out") is True:
            timed_out_attempts += 1

    missing_expected_value_rate = _rate(missing_expected_values, len(option_samples))
    timeout_rate = _rate(timed_out_attempts, len(attempt_samples))

    warnings: list[DatasetHealthWarning] = []
    if len(prompt_ids) < 50:
        warnings.append(_warning(
            "DECISION_MINIMUM_PROMPTS",
            "HIGH",
            f"Decision has {len(prompt_ids)} curated prompts; baseline training target is at least 50.",
            "Author or curate more governed decision prompts before local training.",
        ))
    if len(attempt_samples) < 100:
        warnings.append(_warning(
            "DECISION_MINIMUM_ATTEMPTS",
            "HIGH",
            f"Decision has {len(attempt_samples)} curated attempts; target is at least 100.",
            "Collect more quiz attempts to evaluate read quality across prompts.",
        ))
    if total_labeled == 0 or negative_count / total_labeled < 0.3:
        warnings.append(_warning(
            "DECISION_NEGATIVE_COVERAGE",
            "MEDIUM",
            "Decision negatives are below 30% of labeled positive/negative samples.",
            "Add more bad-decision options and missed or bad-read attempts.",
        ))
    if len(role_distribution) < 3:
        warnings.append(_warning(
            "DECISION_ROLE_COVERAGE",
            "MEDIUM",
            f"Decision role coverage has {len(role_distribution)} roles; target is at least 3.",
            "Curate prompts for more court roles such as ball handler, off-ball shooter, roller, and defenders.",
        ))
    if len(situation_distribution) < 5:
        warnings.append(_warning(
            "DECISION_SITUATION_COVERAGE",
            "MEDIUM",
            f"Decision situation coverage has {len(situation_distribution)} situations; target is at least 5.",
            "Curate prompts across more basketball situations before training.",
        ))
    if missing_expected_value_rate > 0.5:
        warnings.append(_warning(
            "DECISION_EXPECTED_VALUES_MISSING",
            "MEDIUM",
            f"{missing_expected_value_rate:.0%} of decision option samples are missing expected values.",
            "Add expected values to decision options so good/bad labels are more explainable.",
        ))
    if timeout_rate > 0.5:
        warnings.append(_warning(
            "DECISION_TIMEOUT_RATE_HIGH",
            "LOW",
            f"{timeout_rate:.0%} of decision attempts timed out.",
            "Review quiz timing and collect more non-timeout attempts.",
        ))

    return DecisionDatasetHealth(
        sample_count=len(samples),
        label_count=len(labels),
        prompt_count=len(prompt_ids),
        option_count=len(option_samples),
        attempt_count=len(attempt_samples),
        positive_sample_count=positive_count,
        negative_sample_count=negative_count,
        positive_negative_ratio=ratio,
        role_distribution=dict(sorted(role_distribution.items())),
        situation_distribution=dict(sorted(situation_distribution.items())),
        missing_expected_value_rate=missing_expected_value_rate,
        timeout_rate=timeout_rate,
        has_minimum_prompts=len(prompt_ids) >= 50,
        has_role_coverage=len(role_distribution) >= 3,
        has_balanced_labels=total_labeled > 0 and negative_count / total_labeled >= 0.3,
        warnings=warnings,
    )


def dataset_health_response(datasets_dir: Path) -> DatasetHealthResponse:
    return DatasetHealthResponse(
        recognition=recognition_health(datasets_dir),
        decision=decision_health(datasets_dir),
        generated_at=utc_now(),
    )
