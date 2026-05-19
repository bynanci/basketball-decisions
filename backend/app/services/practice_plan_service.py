"""Build and persist deterministic practice plans from drill recommendations.

The service does not generate new coaching advice. Drill-block cues and metrics
are copied from human-authored local drill recommendations/catalog entries, and
non-drill blocks use fixed operational placeholders only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.models import (
    DrillEvidenceRef,
    DrillRecommendationRequest,
    PracticePlan,
    PracticePlanBlock,
    PracticePlanBuildRequest,
    PracticePlanListItem,
    PracticePlanListResponse,
)
from app.models.base import utc_now
from app.services.drill_recommendation_service import build_drill_recommendations

APP_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRACTICE_PLANS_DIR = APP_DATA_DIR / "practice_plans"
PRACTICE_PLAN_INDEX_PATH = PRACTICE_PLANS_DIR / "index.json"

DURATION_TEMPLATE: dict[int, dict[str, int]] = {
    60: {"warmup": 8, "scrimmage": 12, "review": 5},
    75: {"warmup": 10, "scrimmage": 15, "review": 8},
    90: {"warmup": 12, "scrimmage": 20, "review": 8},
    120: {"warmup": 15, "scrimmage": 25, "review": 10},
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _plan_id_for(request: PracticePlanBuildRequest, block_seed: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256(_stable_json({"request": request.model_dump(mode="json"), "blocks": block_seed, "nonce": uuid4().hex}).encode("utf-8")).hexdigest()[:12]
    return f"practice-{digest}"


def _unique(items: list[str | None]) -> list[str]:
    return [item for item in dict.fromkeys(item for item in items if item)]


def _distribute(total: int, count: int) -> list[int]:
    base = total // count
    remainder = total % count
    return [base + (1 if index < remainder else 0) for index in range(count)]


def _block(block_type: str, title: str, start: int, duration: int, **kwargs: Any) -> PracticePlanBlock:
    return PracticePlanBlock(block_id=f"{block_type}-{start}-{start + duration}", block_type=block_type, title=title, start_minute=start, end_minute=start + duration, duration_minutes=duration, **kwargs)


def _render_markdown(plan: PracticePlan) -> str:
    lines = [
        f"# {plan.title}",
        "",
        f"Plan ID: `{plan.plan_id}`",
        f"Generated: {plan.created_at.isoformat()}",
        f"Duration: {plan.total_duration_minutes} minutes",
    ]
    if plan.notes:
        lines.extend(["", "## Builder Notes", "", plan.notes])
    lines.extend([
        "",
        "## Safety Notes",
        "",
        "- Built deterministically from local drill recommendations and artifacts.",
        "- Drill coaching cues and success metrics are copied from the human-authored local drill catalog.",
        "- No medical or injury advice, calendar integration, PDF/DOCX export, or season planning is included.",
    ])
    if plan.project_id or plan.player_keys or plan.target_roles or plan.target_situations:
        lines.extend([
            "",
            "## Targets",
            "",
            f"- Project: {plan.project_id or 'Any'}",
            f"- Player keys: {', '.join(plan.player_keys) if plan.player_keys else 'Any'}",
            f"- Roles: {', '.join(plan.target_roles) if plan.target_roles else 'Any'}",
            f"- Situations: {', '.join(plan.target_situations) if plan.target_situations else 'Any'}",
        ])
    if plan.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in plan.warnings)
    lines.extend(["", "## Time-boxed Blocks", ""])
    for block in plan.blocks:
        lines.extend([
            f"### {block.start_minute:02d}-{block.end_minute:02d} min · {block.title}",
            "",
            f"- Type: {block.block_type}",
            f"- Duration: {block.duration_minutes} minutes",
        ])
        if block.target_roles:
            lines.append(f"- Target roles: {', '.join(block.target_roles)}")
        if block.target_situations:
            lines.append(f"- Target situations: {', '.join(block.target_situations)}")
        if block.player_keys:
            lines.append(f"- Player keys: {', '.join(block.player_keys)}")
        if block.coaching_cues:
            lines.extend(["", "Coaching cues:"])
            lines.extend(f"- {cue}" for cue in block.coaching_cues)
        if block.success_metrics:
            lines.extend(["", "Success metrics:"])
            lines.extend(f"- {metric}" for metric in block.success_metrics)
        if block.purpose:
            lines.append(f"- Purpose: {block.purpose}")
        if block.court_area:
            lines.append(f"- Court area: {block.court_area}")
        if block.constraints:
            lines.extend(["", "Constraints:"])
            lines.extend(f"- {item}" for item in block.constraints)
        if block.scoring:
            lines.extend(["", "Scoring:"])
            lines.extend(f"- {item}" for item in block.scoring)
        if block.common_mistakes:
            lines.extend(["", "Common mistakes:"])
            lines.extend(f"- {item}" for item in block.common_mistakes)
        if block.progression:
            lines.extend(["", "Progression:"])
            lines.extend(f"- {item}" for item in block.progression)
        if block.regression:
            lines.extend(["", "Regression:"])
            lines.extend(f"- {item}" for item in block.regression)
        if block.evidence_refs:
            lines.extend(["", "Evidence refs:"])
            lines.extend(f"- {ref.source}: {ref.ref_id or ref.prompt_id or ref.player_key or 'artifact'} — {ref.detail}" for ref in block.evidence_refs)
        if block.warnings:
            lines.extend(["", "Block warnings:"])
            lines.extend(f"- {warning}" for warning in block.warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _read_index() -> PracticePlanListResponse:
    if not PRACTICE_PLAN_INDEX_PATH.exists():
        return PracticePlanListResponse(plans=[])
    try:
        return PracticePlanListResponse.model_validate(json.loads(PRACTICE_PLAN_INDEX_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return PracticePlanListResponse(plans=[])


def build_practice_plan(request: PracticePlanBuildRequest) -> PracticePlan:
    recommendation_response = build_drill_recommendations(
        DrillRecommendationRequest(
            project_id=request.project_id,
            player_key=request.player_key,
            max_recommendations=request.max_drill_blocks,
            include_practice_feedback=request.include_practice_feedback,
            feedback_lookback_limit=request.feedback_lookback_limit,
        )
    )
    recommendations = recommendation_response.recommendations[: request.max_drill_blocks]
    warnings = list(dict.fromkeys(recommendation_response.warnings))
    if not recommendations:
        warnings.append("No drill recommendations crossed deterministic thresholds; only fixed non-drill blocks were scheduled.")

    player_keys = _unique([request.player_key, *request.player_keys, *[ref.player_key for rec in recommendations for ref in rec.evidence_refs]])
    target_roles = _unique([rec.role for rec in recommendations])
    target_situations = _unique([rec.situation for rec in recommendations])
    evidence_refs: list[DrillEvidenceRef] = []
    for recommendation in recommendations:
        evidence_refs.extend(recommendation.evidence_refs)
    evidence_refs = list({(ref.source, ref.artifact, ref.ref_id, ref.project_id, ref.player_key, ref.prompt_id, ref.detail): ref for ref in evidence_refs}.values())

    template = DURATION_TEMPLATE[request.total_duration_minutes]
    drill_total = request.total_duration_minutes - template["warmup"] - template["scrimmage"] - template["review"]
    drill_durations = _distribute(drill_total, len(recommendations)) if recommendations else []

    cursor = 0
    blocks: list[PracticePlanBlock] = [
        _block(
            "warmup",
            "Warmup / readiness",
            cursor,
            template["warmup"],
            target_roles=target_roles,
            target_situations=target_situations,
            player_keys=player_keys,
            success_metrics=["Warmup block completed inside the assigned time box."],
            warnings=["Fixed operational block; no new coaching advice is generated."],
        )
    ]
    cursor += template["warmup"]

    if recommendations:
        for index, (recommendation, duration) in enumerate(zip(recommendations, drill_durations, strict=True), start=1):
            blocks.append(
                _block(
                    "drill",
                    f"Drill {index}: {recommendation.title}",
                    cursor,
                    duration,
                    drill_id=recommendation.drill_id,
                    recommendation_id=recommendation.recommendation_id,
                    priority=recommendation.priority,
                    target_roles=[recommendation.role] if recommendation.role else [],
                    target_situations=[recommendation.situation],
                    player_keys=_unique([request.player_key, *[ref.player_key for ref in recommendation.evidence_refs]]),
                    coaching_cues=recommendation.coaching_cues,
                    success_metrics=recommendation.success_metrics,
                    purpose=recommendation.purpose,
                    court_area=recommendation.court_area,
                    constraints=recommendation.constraints,
                    scoring=recommendation.scoring,
                    common_mistakes=recommendation.common_mistakes,
                    progression=recommendation.progression,
                    regression=recommendation.regression,
                    evidence_refs=recommendation.evidence_refs,
                    warnings=recommendation.adjustment_summary if recommendation.feedback_adjusted else [],
                )
            )
            cursor += duration
    else:
        blocks.append(
            _block(
                "drill",
                "Drill block pending recommendations",
                cursor,
                drill_total,
                target_roles=target_roles,
                target_situations=target_situations,
                player_keys=player_keys,
                success_metrics=["Drill time held for coach-selected catalog work after recommendations are available."],
                warnings=["No deterministic drill recommendation was available for this time box; no generated coaching cues were added."],
            )
        )
        cursor += drill_total

    blocks.append(
        _block(
            "scrimmage",
            "Constrained scrimmage transfer",
            cursor,
            template["scrimmage"],
            target_roles=target_roles,
            target_situations=target_situations,
            player_keys=player_keys,
            evidence_refs=evidence_refs[:8],
            success_metrics=["Scrimmage block completed inside the assigned time box."],
            warnings=["Fixed transfer block; use selected drill cues instead of generated coaching advice."],
        )
    )
    cursor += template["scrimmage"]
    blocks.append(
        _block(
            "review",
            "Review / recap",
            cursor,
            template["review"],
            target_roles=target_roles,
            target_situations=target_situations,
            player_keys=player_keys,
            evidence_refs=evidence_refs[:8],
            success_metrics=["Review block completed inside the assigned time box."],
            warnings=["Fixed recap block; no medical, injury, or season-planning advice is included."],
        )
    )

    plan_id = _plan_id_for(request, [block.model_dump(mode="json") for block in blocks])
    created_at = utc_now()
    json_path = PRACTICE_PLANS_DIR / f"{plan_id}.json"
    markdown_path = PRACTICE_PLANS_DIR / f"{plan_id}.md"
    plan = PracticePlan(
        plan_id=plan_id,
        title=request.title,
        created_at=created_at,
        created_by=request.created_by,
        notes=request.notes,
        project_id=request.project_id,
        player_key=request.player_key,
        total_duration_minutes=request.total_duration_minutes,
        target_roles=target_roles,
        target_situations=target_situations,
        player_keys=player_keys,
        source_recommendation_ids=[rec.recommendation_id for rec in recommendations],
        blocks=blocks,
        warnings=list(dict.fromkeys(warnings)),
        evidence_refs=evidence_refs[:24],
        markdown="",
        json_path=str(json_path),
        markdown_path=str(markdown_path),
    )
    plan.markdown = _render_markdown(plan)
    _write_json(json_path, plan.model_dump(mode="json"))
    markdown_path.write_text(plan.markdown, encoding="utf-8")

    index = _read_index()
    index.plans = [item for item in index.plans if item.plan_id != plan.plan_id]
    index.plans.append(
        PracticePlanListItem(
            plan_id=plan.plan_id,
            title=plan.title,
            created_at=plan.created_at,
            created_by=plan.created_by,
            notes=plan.notes,
            project_id=plan.project_id,
            player_key=plan.player_key,
            total_duration_minutes=plan.total_duration_minutes,
            target_roles=plan.target_roles,
            target_situations=plan.target_situations,
            player_keys=plan.player_keys,
            warning_count=len(plan.warnings),
            json_path=plan.json_path,
            markdown_path=plan.markdown_path,
        )
    )
    index.plans.sort(key=lambda item: item.created_at, reverse=True)
    index.updated_at = utc_now()
    _write_json(PRACTICE_PLAN_INDEX_PATH, index.model_dump(mode="json"))
    return plan


def list_practice_plans() -> PracticePlanListResponse:
    return _read_index()


def get_practice_plan(plan_id: str) -> PracticePlan | None:
    path = PRACTICE_PLANS_DIR / f"{plan_id}.json"
    if not path.exists():
        return None
    try:
        return PracticePlan.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return None
