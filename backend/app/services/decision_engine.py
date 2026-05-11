"""Rule-based Decision Engine v1 for quiz attempts."""

from __future__ import annotations

from app.models.base import utc_now
from app.models.quiz import DecisionEvent, DecisionEvaluationSource, QuizAttemptRecord, QuizPrompt


def _round_cost(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _source_track_ids(prompt: QuizPrompt, selected_option_id: str | None, correct_option_id: str) -> list[str]:
    # Identity-bearing links only. Frame context tracks are persisted separately
    # on DecisionEvent.context_track_ids and must never be promoted to source links.
    track_ids = list(prompt.source_track_ids)
    option_ids = {correct_option_id}
    if selected_option_id is not None:
        option_ids.add(selected_option_id)
    for option in prompt.options:
        if option.option_id in option_ids:
            track_ids.extend(option.source_track_ids)
    return list(dict.fromkeys(track_ids))


def evaluate_attempt(prompt: QuizPrompt, attempt: QuizAttemptRecord) -> DecisionEvent:
    """Evaluate a persisted quiz attempt into an explainable decision event.

    Decision Engine v1 is intentionally deterministic: it uses manually authored
    expected values when all options have them, otherwise it falls back to
    correctness-only rule scoring.
    """

    correct_option = next(option for option in prompt.options if option.is_correct)
    selected_option = None
    if attempt.selected_option_id is not None:
        selected_option = next(
            (option for option in prompt.options if option.option_id == attempt.selected_option_id),
            None,
        )

    expected_values = [option.expected_value for option in prompt.options]
    has_expected_values = all(value is not None for value in expected_values)
    explanations: list[str] = []

    selected_expected_value = selected_option.expected_value if selected_option is not None else None
    best_expected_value: float | None = None
    opportunity_cost: float | None = None

    if has_expected_values:
        best_expected_value = max(value for value in expected_values if value is not None)
        selected_value_for_cost = selected_expected_value if selected_expected_value is not None else 0.0
        opportunity_cost = _round_cost(max(0.0, best_expected_value - selected_value_for_cost))
        raw_score = max(0, round(100 - (opportunity_cost or 0.0) * 200))
        evaluation_source: DecisionEvaluationSource = "MANUAL_EXPECTED_VALUE"
        explanations.append(
            f"Manual expected values used: selected={selected_expected_value if selected_expected_value is not None else 'none'}, "
            f"best={best_expected_value}, opportunity_cost={opportunity_cost}."
        )
        explanations.append("Raw score = max(0, round(100 - opportunity_cost * 200)).")
    else:
        raw_score = 100 if attempt.is_correct else 0
        evaluation_source = "RULE_BASED"
        explanations.append("Expected values were not available for every option, so correctness-only rule scoring was used.")
        explanations.append(
            f"Raw score is {'100' if attempt.is_correct else '0'} "
            f"because the attempt was {'correct' if attempt.is_correct else 'incorrect'}."
        )

    role_adjusted_score = raw_score
    explanations.append("Role adjustment started with weight=1.0.")

    if prompt.question_mode == "QUICK_DECISION" and attempt.timed_out:
        role_adjusted_score = 0
        explanations.append("QUICK_DECISION attempt timed out, so role-adjusted score was set to 0.")
    else:
        if prompt.question_mode == "ROLE_READ" and attempt.is_correct:
            role_adjusted_score = min(100, role_adjusted_score + 5)
            explanations.append("ROLE_READ correct-answer bonus applied: +5, capped at 100.")

        if (
            prompt.time_limit_ms is not None
            and attempt.response_time_ms is not None
            and attempt.response_time_ms < prompt.time_limit_ms * 0.5
        ):
            role_adjusted_score = min(100, role_adjusted_score + 3)
            explanations.append(
                "Fast response bonus applied: +3 for answering faster than half the time limit, capped at 100."
            )

        if not attempt.is_correct and opportunity_cost is not None and opportunity_cost <= 0.1:
            previous_score = role_adjusted_score
            role_adjusted_score = max(role_adjusted_score, 70)
            explanations.append(
                "Near-optimal incorrect answer partial-credit floor applied because "
                f"opportunity_cost <= 0.1: {previous_score} -> {role_adjusted_score}."
            )

    return DecisionEvent(
        project_id=prompt.project_id,
        prompt_id=prompt.prompt_id,
        attempt_id=attempt.attempt_id,
        frame_id=prompt.frame_id,
        frame_index=prompt.frame_index,
        user_role=attempt.user_role,
        court_role_target=prompt.court_role_target,
        situation_type=prompt.situation_type,
        question_mode=prompt.question_mode,
        selected_option_id=attempt.selected_option_id,
        correct_option_id=correct_option.option_id,
        is_correct=attempt.is_correct,
        selected_expected_value=selected_expected_value,
        best_expected_value=best_expected_value,
        opportunity_cost=opportunity_cost,
        raw_score=raw_score,
        role_adjusted_score=role_adjusted_score,
        response_time_ms=attempt.response_time_ms,
        timed_out=attempt.timed_out,
        evaluation_source=evaluation_source,
        context_track_ids=prompt.context_track_ids,
        source_track_ids=_source_track_ids(prompt, attempt.selected_option_id, correct_option.option_id),
        explanations=explanations,
        created_at=utc_now(),
    )
