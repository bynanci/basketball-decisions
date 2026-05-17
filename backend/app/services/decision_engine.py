"""Rule-based Decision Engine v2 for quiz attempts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.models.base import utc_now
from app.models.decision_rule import DecisionRule, DecisionRuleSet
from app.models.quiz import (
    DecisionEvent,
    DecisionEvaluationSource,
    DecisionQuizOption,
    DecisionRuleApplicationSummary,
    QuizAttemptRecord,
    QuizPrompt,
    RuleEvaluationResult,
)

DECISION_ENGINE_VERSION = "v2"
RULE_DELTA_MIN = -10.0
RULE_DELTA_MAX = 10.0
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ACTIVE_RULE_SET_PATH = DATA_DIR / "decision_rules" / "active_rule_set.json"
RULE_SETS_PATH = DATA_DIR / "decision_rules" / "rule_sets.json"
_ACTIVE_RULE_SET_ADAPTER = TypeAdapter(DecisionRuleSet)
_RULE_SET_ADAPTER = TypeAdapter(list[DecisionRuleSet])


def _round_cost(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _clip_score(value: float) -> int:
    return max(0, min(100, round(value)))


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


def load_active_rule_set() -> DecisionRuleSet | None:
    """Load the active human-approved rule set from local JSON storage."""

    if ACTIVE_RULE_SET_PATH.exists():
        content = ACTIVE_RULE_SET_PATH.read_text(encoding="utf-8")
        if json.loads(content) is not None:
            return _ACTIVE_RULE_SET_ADAPTER.validate_json(content)

    if not RULE_SETS_PATH.exists():
        return None
    rule_sets = _RULE_SET_ADAPTER.validate_json(RULE_SETS_PATH.read_text(encoding="utf-8"))
    return next((rule_set for rule_set in rule_sets if rule_set.active), None)


def _context_text(option: DecisionQuizOption | None) -> str:
    if option is None:
        return ""
    parts = [option.option_id, option.label, option.action_type, option.explanation]
    if option.role_feedback is not None:
        parts.extend(
            feedback
            for feedback in (
                option.role_feedback.coach,
                option.role_feedback.player,
                option.role_feedback.analyst,
                option.role_feedback.fan,
            )
            if feedback
        )
    return " ".join(str(part) for part in parts if part is not None).lower()


def _cue_matches(cue: str, context: str) -> bool:
    normalized = cue.strip().lower()
    if not normalized:
        return False
    if normalized in context:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized) if len(token) >= 4]
    return bool(tokens) and all(token in context for token in tokens)


def _rule_delta(rule: DecisionRule, selected_option: DecisionQuizOption | None) -> tuple[bool, float, str]:
    if selected_option is None:
        return False, 0.0, "No selected option context was available for rule matching."

    context = _context_text(selected_option)
    positive_match = _cue_matches(rule.positive_cue, context)
    negative_match = _cue_matches(rule.negative_cue, context)
    condition_match = _cue_matches(rule.condition_text, context)

    # The rule's role and situation have already matched. A selected option can
    # match by explicit positive/negative cue or, as a fallback, by condition text.
    if positive_match:
        return True, abs(float(rule.weight)), "Selected option matched the rule positive cue."
    if negative_match:
        return True, -abs(float(rule.weight)), "Selected option matched the rule negative cue."
    if condition_match:
        return True, 0.0, "Selected option matched the rule condition text without a directional cue."
    return False, 0.0, "Rule role/situation matched, but selected option context did not match its cues."


def apply_decision_rules(
    *,
    prompt: QuizPrompt,
    selected_option: DecisionQuizOption | None,
    active_rule_set: DecisionRuleSet | None,
    enabled: bool,
) -> DecisionRuleApplicationSummary:
    if not enabled:
        return DecisionRuleApplicationSummary(enabled=False, notes=["Active decision rules were disabled for this build."])
    if active_rule_set is None:
        return DecisionRuleApplicationSummary(enabled=True, notes=["No active decision rule set was found."])

    applicable_rules = [
        rule
        for rule in active_rule_set.rules
        if rule.status == "ACTIVE"
        and rule.court_role == prompt.court_role_target
        and rule.situation_type == prompt.situation_type
    ]
    results: list[RuleEvaluationResult] = []
    raw_delta = 0.0
    for rule in applicable_rules:
        matched, delta, reason = _rule_delta(rule, selected_option)
        results.append(
            RuleEvaluationResult(
                rule_id=rule.rule_id,
                court_role=rule.court_role,
                situation_type=rule.situation_type,
                matched=matched,
                score_delta=round(delta, 4),
                weight=rule.weight,
                condition_text=rule.condition_text,
                positive_cue=rule.positive_cue,
                negative_cue=rule.negative_cue,
                explanation=rule.explanation,
                reason=reason,
            )
        )
        if matched:
            raw_delta += delta

    bounded_delta = max(RULE_DELTA_MIN, min(RULE_DELTA_MAX, raw_delta))
    notes: list[str] = []
    if raw_delta != bounded_delta:
        notes.append(f"Rule score delta was bounded from {round(raw_delta, 4)} to {round(bounded_delta, 4)}.")
    if not applicable_rules:
        notes.append("No active rules matched this prompt's court role and situation type.")

    return DecisionRuleApplicationSummary(
        enabled=True,
        rule_set_id=active_rule_set.rule_set_id,
        rule_set_version=active_rule_set.version,
        evaluated_rule_count=len(results),
        matched_rule_count=sum(1 for result in results if result.matched),
        missed_rule_count=sum(1 for result in results if not result.matched),
        total_delta=round(bounded_delta, 4),
        delta_bounded=raw_delta != bounded_delta,
        results=results,
        notes=notes,
    )


def evaluate_attempt(
    prompt: QuizPrompt,
    attempt: QuizAttemptRecord,
    *,
    active_rule_set: DecisionRuleSet | None = None,
    use_active_rules: bool = True,
) -> DecisionEvent:
    """Evaluate a persisted quiz attempt into an explainable decision event.

    Decision Engine v2 keeps manually authored expected-value scoring primary,
    then optionally applies a bounded transparent rule delta from the active
    human-approved rule set. It does not run an ML model or black-box EPV.
    """

    if active_rule_set is None and use_active_rules:
        try:
            active_rule_set = load_active_rule_set()
        except (json.JSONDecodeError, ValidationError):
            active_rule_set = None

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

    rule_application = apply_decision_rules(
        prompt=prompt,
        selected_option=selected_option,
        active_rule_set=active_rule_set,
        enabled=use_active_rules,
    )
    base_score = role_adjusted_score
    final_score_unclipped = base_score + rule_application.total_delta
    final_score = _clip_score(final_score_unclipped)
    score_capped = final_score != round(final_score_unclipped)
    if rule_application.enabled:
        explanations.append(
            f"Decision Engine v2 rule delta applied after manual/base scoring: base={base_score}, "
            f"delta={rule_application.total_delta}, final={final_score}."
        )
    else:
        explanations.append("Decision Engine v2 active rule application was disabled for this event build.")

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
        role_adjusted_score=final_score,
        decision_engine_version=DECISION_ENGINE_VERSION,
        active_rule_set_id=rule_application.rule_set_id,
        active_rule_set_version=rule_application.rule_set_version,
        rule_application=rule_application,
        base_score=base_score,
        rule_score_delta=rule_application.total_delta,
        final_score=final_score,
        score_capped=score_capped,
        response_time_ms=attempt.response_time_ms,
        timed_out=attempt.timed_out,
        evaluation_source=evaluation_source,
        context_track_ids=prompt.context_track_ids,
        source_track_ids=_source_track_ids(prompt, attempt.selected_option_id, correct_option.option_id),
        explanations=explanations,
        created_at=utc_now(),
    )
