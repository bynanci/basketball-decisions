"""Explainable analytics for Decision Engine prompt quality."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.models import (
    DecisionDiagnosticsGlobalSummary,
    DecisionDiagnosticsReport,
    DecisionEvent,
    DecisionPromptDiagnostics,
    DecisionPromptDifficulty,
    DecisionRoleDiagnostics,
    DecisionSituationDiagnostics,
    QuizAttemptRecord,
    QuizPrompt,
)
from app.models.base import utc_now

_PROMPTS_ADAPTER = TypeAdapter(list[QuizPrompt])
_ATTEMPTS_ADAPTER = TypeAdapter(list[QuizAttemptRecord])


def _read_json_list(path: Path, adapter):
    if not path.exists():
        return []
    return adapter.validate_json(path.read_text(encoding="utf-8"))


def _read_events(path: Path) -> list[DecisionEvent]:
    if not path.exists():
        return []
    events: list[DecisionEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(DecisionEvent.model_validate_json(line))
    return events


def _average(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _difficulty(attempt_count: int, correct_rate: float) -> DecisionPromptDifficulty:
    if attempt_count < 3:
        return "INSUFFICIENT_DATA"
    if correct_rate > 0.9:
        return "TOO_EASY"
    if correct_rate < 0.35:
        return "TOO_HARD"
    return "BALANCED"


def _event_by_attempt_key(events: list[DecisionEvent]) -> dict[tuple[str, str, str], DecisionEvent]:
    return {(event.project_id, event.prompt_id, event.attempt_id): event for event in events}


def _event_for_attempt(
    events_by_attempt: dict[tuple[str, str, str], DecisionEvent], attempt: QuizAttemptRecord
) -> DecisionEvent | None:
    return events_by_attempt.get((attempt.project_id, attempt.prompt_id, attempt.attempt_id))


def _prompt_reasons(
    *,
    attempt_count: int,
    correct_count: int,
    correct_rate: float,
    avg_opportunity_cost: float,
    timeout_rate: float,
    selections: Counter[str],
    most_selected_wrong_option_id: str | None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    suspected_label_issue = False

    if attempt_count < 3:
        reasons.append("Fewer than 3 attempts; collect more answers before judging difficulty.")
    elif correct_rate > 0.9:
        reasons.append(f"Correct rate {correct_rate:.0%} is above 90%, so the prompt may be too easy.")
    elif correct_rate < 0.35:
        reasons.append(f"Correct rate {correct_rate:.0%} is below 35%, so the prompt may be too hard.")
    else:
        reasons.append(f"Correct rate {correct_rate:.0%} is within the balanced range.")

    if avg_opportunity_cost > 0.3:
        reasons.append(f"Average opportunity cost {avg_opportunity_cost:.2f} is above 0.30; wrong answers are high-cost.")
    if timeout_rate > 0.4:
        reasons.append(f"Timeout rate {timeout_rate:.0%} is above 40%; prompt may create time pressure.")

    if most_selected_wrong_option_id is not None and attempt_count >= 3:
        wrong_count = selections[most_selected_wrong_option_id]
        if correct_count / attempt_count < 0.2 and wrong_count / attempt_count > 0.5 and wrong_count > correct_count:
            suspected_label_issue = True
            reasons.append(
                "Suspected label issue: the correct option was rarely selected while "
                f"non-correct option {most_selected_wrong_option_id} dominated responses."
            )

    return suspected_label_issue, reasons


def _weighted_prompt_average(prompt_diagnostics: list[DecisionPromptDiagnostics], metric: str) -> float:
    weighted_values = [
        getattr(diag, metric) * diag.attempt_count for diag in prompt_diagnostics if diag.attempt_count > 0
    ]
    attempt_count = sum(diag.attempt_count for diag in prompt_diagnostics if diag.attempt_count > 0)
    if attempt_count == 0:
        return 0.0
    return round(sum(weighted_values) / attempt_count, 4)


def _weakest_situations(role_prompts: list[DecisionPromptDiagnostics]) -> list[str]:
    by_situation: dict[str, list[DecisionPromptDiagnostics]] = defaultdict(list)
    for diag in role_prompts:
        by_situation[diag.situation_type].append(diag)

    attempted_situations = {
        situation: diagnostics
        for situation, diagnostics in by_situation.items()
        if sum(diag.attempt_count for diag in diagnostics) > 0
    }
    source = attempted_situations or by_situation
    return sorted(
        source,
        key=lambda situation: (_weighted_prompt_average(source[situation], "avg_score"), situation),
    )[:3]


def build_decision_diagnostics(project_dirs: list[Path], events_path: Path) -> DecisionDiagnosticsReport:
    """Build a JSON-serializable diagnostics report from local quiz artifacts.

    This is analytics-only. It does not train or fit an ML model.
    """

    prompts: list[QuizPrompt] = []
    attempts: list[QuizAttemptRecord] = []
    for directory in project_dirs:
        try:
            prompts.extend(_read_json_list(directory / "quiz_prompts.json", _PROMPTS_ADAPTER))
            attempts.extend(_read_json_list(directory / "quiz_attempts.json", _ATTEMPTS_ADAPTER))
        except ValidationError:
            continue

    events = _read_events(events_path)
    events_by_attempt = _event_by_attempt_key(events)
    attempts_by_prompt: dict[tuple[str, str], list[QuizAttemptRecord]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_prompt[(attempt.project_id, attempt.prompt_id)].append(attempt)

    prompt_diagnostics: list[DecisionPromptDiagnostics] = []
    for prompt in prompts:
        prompt_attempts = attempts_by_prompt.get((prompt.project_id, prompt.prompt_id), [])
        attempt_count = len(prompt_attempts)
        correct_count = sum(1 for attempt in prompt_attempts if attempt.is_correct)
        correct_rate = round(correct_count / attempt_count, 4) if attempt_count else 0.0
        timeout_rate = round(sum(1 for attempt in prompt_attempts if attempt.timed_out) / attempt_count, 4) if attempt_count else 0.0
        attempt_events = [_event_for_attempt(events_by_attempt, attempt) for attempt in prompt_attempts]
        raw_scores = [
            event.raw_score if event is not None else attempt.score
            for attempt, event in zip(prompt_attempts, attempt_events)
        ]
        role_scores = [
            event.role_adjusted_score if event is not None else attempt.score
            for attempt, event in zip(prompt_attempts, attempt_events)
        ]
        opportunity_costs = [
            event.opportunity_cost if event is not None else attempt.opportunity_cost
            for attempt, event in zip(prompt_attempts, attempt_events)
        ]
        numeric_costs = [cost for cost in opportunity_costs if cost is not None]
        selections = Counter(attempt.selected_option_id for attempt in prompt_attempts if attempt.selected_option_id is not None)
        correct_option = next(option for option in prompt.options if option.is_correct)
        wrong_selections = Counter(
            {option_id: count for option_id, count in selections.items() if option_id != correct_option.option_id}
        )
        most_selected_wrong_option_id = wrong_selections.most_common(1)[0][0] if wrong_selections else None
        avg_opportunity_cost = _average(numeric_costs)
        suspected_label_issue, reasons = _prompt_reasons(
            attempt_count=attempt_count,
            correct_count=correct_count,
            correct_rate=correct_rate,
            avg_opportunity_cost=avg_opportunity_cost,
            timeout_rate=timeout_rate,
            selections=selections,
            most_selected_wrong_option_id=most_selected_wrong_option_id,
        )
        prompt_diagnostics.append(
            DecisionPromptDiagnostics(
                prompt_id=prompt.prompt_id,
                project_id=prompt.project_id,
                court_role_target=prompt.court_role_target,
                situation_type=prompt.situation_type,
                question_mode=prompt.question_mode,
                attempt_count=attempt_count,
                correct_rate=correct_rate,
                avg_score=_average(raw_scores),
                avg_role_adjusted_score=_average(role_scores),
                avg_opportunity_cost=avg_opportunity_cost,
                timeout_rate=timeout_rate,
                most_selected_wrong_option_id=most_selected_wrong_option_id,
                difficulty=_difficulty(attempt_count, correct_rate),
                suspected_label_issue=suspected_label_issue,
                reasons=reasons,
            )
        )

    role_diagnostics: list[DecisionRoleDiagnostics] = []
    for role in sorted({prompt.court_role_target for prompt in prompts}):
        role_prompts = [diag for diag in prompt_diagnostics if diag.court_role_target == role]
        role_diagnostics.append(
            DecisionRoleDiagnostics(
                court_role=role,
                prompt_count=len(role_prompts),
                attempt_count=sum(diag.attempt_count for diag in role_prompts),
                avg_score=_weighted_prompt_average(role_prompts, "avg_score"),
                avg_opportunity_cost=_weighted_prompt_average(role_prompts, "avg_opportunity_cost"),
                timeout_rate=_weighted_prompt_average(role_prompts, "timeout_rate"),
                weakest_situation_types=_weakest_situations(role_prompts),
            )
        )

    situation_diagnostics: list[DecisionSituationDiagnostics] = []
    for situation in sorted({prompt.situation_type for prompt in prompts}):
        situation_prompts = [diag for diag in prompt_diagnostics if diag.situation_type == situation]
        situation_diagnostics.append(
            DecisionSituationDiagnostics(
                situation_type=situation,
                prompt_count=len(situation_prompts),
                attempt_count=sum(diag.attempt_count for diag in situation_prompts),
                avg_score=_weighted_prompt_average(situation_prompts, "avg_score"),
                avg_opportunity_cost=_weighted_prompt_average(situation_prompts, "avg_opportunity_cost"),
                timeout_rate=_weighted_prompt_average(situation_prompts, "timeout_rate"),
            )
        )

    return DecisionDiagnosticsReport(
        generated_at=utc_now(),
        prompt_diagnostics=prompt_diagnostics,
        role_diagnostics=role_diagnostics,
        situation_diagnostics=situation_diagnostics,
        global_summary=DecisionDiagnosticsGlobalSummary(
            prompt_count=len(prompt_diagnostics),
            attempt_count=sum(diag.attempt_count for diag in prompt_diagnostics),
            too_easy_count=sum(1 for diag in prompt_diagnostics if diag.difficulty == "TOO_EASY"),
            too_hard_count=sum(1 for diag in prompt_diagnostics if diag.difficulty == "TOO_HARD"),
            balanced_count=sum(1 for diag in prompt_diagnostics if diag.difficulty == "BALANCED"),
            insufficient_data_count=sum(1 for diag in prompt_diagnostics if diag.difficulty == "INSUFFICIENT_DATA"),
            suspected_label_issue_count=sum(1 for diag in prompt_diagnostics if diag.suspected_label_issue),
            high_cost_prompt_count=sum(1 for diag in prompt_diagnostics if diag.avg_opportunity_cost > 0.3),
            time_pressure_prompt_count=sum(1 for diag in prompt_diagnostics if diag.timeout_rate > 0.4),
        ),
    )
