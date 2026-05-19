# M27 Guided Workflow Usability Review (Issue #92)

Date: 2026-05-19

Scope reviewed:
- `BUILD_PLAYER_VALUE`
- `IMPROVE_DATA_QUALITY`
- `TRAINING_RECOMMENDATION`
- `COACH_REPORT`
- `MODEL_GOVERNANCE`

Primary source reviewed: `backend/app/services/workflow_orchestrator_service.py` (template definitions, prerequisite evaluation, status computation, and route hydration).

## Review rubric
Each workflow was evaluated for:
- entry condition
- user goal clarity
- step order
- step label clarity
- step description clarity
- prerequisite clarity
- blocking reason clarity
- target route accuracy
- completion check clarity
- warnings/evidence references

Legend: ✅ strong, ⚠️ acceptable with minor issues, ❌ needs fix.

---

## 1) Build Player Value

**Overall:** ✅

- **Entry condition:** ⚠️ Requires tracking artifact (`has_tracking`) for first step to avoid immediate block; this is enforced in step-level blocking and surfaced in prerequisites.
- **User goal clarity:** ✅ Title/description clearly communicates path from tracking review to Player Value.
- **Step order:** ✅ Logical dependency chain: review tracking → aliases → decision events → Player Value.
- **Step label clarity:** ✅ Labels are actionable and concise.
- **Step description clarity:** ✅ Clear and explicit that workflow does not auto-run operations.
- **Prerequisite clarity:** ✅ Step prerequisites map cleanly to artifact checks.
- **Blocking reason clarity:** ✅ Blocked steps derive from missing blocking prerequisites and rendered prerequisite detail messages.
- **Target route accuracy:** ✅ Routes map to expected pages (`/projects/{project_id}/tracking-review`, `/projects/{project_id}`, `/local-lab`, `/player-value`).
- **Completion check clarity:** ✅ Completion keys are explicit (`has_tracking_review`, `has_player_aliases`, `has_decision_events`, `has_player_value`).
- **Warnings/evidence refs:** ✅ Global warning explains no automatic execution; prerequisite artifact paths provide evidence pointers for non-project assets.

## 2) Improve Data Quality

**Overall:** ⚠️

- **Entry condition:** ⚠️ Can start without project context; first step is useful but not mandatory-blocking.
- **User goal clarity:** ✅ Description aligns with review queue + dataset readiness objective.
- **Step order:** ✅ Triage → dataset refresh → model check is appropriate.
- **Step label clarity:** ✅ Clear labels.
- **Step description clarity:** ⚠️ Previously implied required open high-priority items; copy adjusted to clarify “when present” behavior.
- **Prerequisite clarity:** ⚠️ `triage-review` uses `prerequisite_keys` but not `blocking_prerequisite_keys`, so step remains READY even when no high-priority items exist (by design but potentially surprising).
- **Blocking reason clarity:** ✅ Blocking is explicit on model check if dataset health missing.
- **Target route accuracy:** ✅ `/review-queue`, `/local-lab`, `/model-registry` are correct.
- **Completion check clarity:** ✅ Dataset and model checks tied to concrete prerequisite keys.
- **Warnings/evidence refs:** ✅ Shared warning + review queue artifact path are present.

## 3) Training Recommendation

**Overall:** ✅

- **Entry condition:** ✅ Usable from Player Value forward; first step directly validates core readiness.
- **User goal clarity:** ✅ Clear transition from Player Value to drills/plans/execution.
- **Step order:** ✅ Proper progressive chain with strict blocking dependencies from drills onward.
- **Step label clarity:** ✅ Action labels and titles are easy to scan.
- **Step description clarity:** ✅ Non-automation and deterministic behavior are explicit.
- **Prerequisite clarity:** ✅ Strong key mapping (`has_player_value` → `has_drill_recommendations` → `has_practice_plan` → `has_practice_execution`).
- **Blocking reason clarity:** ✅ Blocked states are deterministic from missing prerequisites.
- **Target route accuracy:** ✅ `/player-value`, `/drills`, `/practice-plans`, `/practice-executions` align with task intent.
- **Completion check clarity:** ✅ Completion keys are coherent and artifact-backed.
- **Warnings/evidence refs:** ✅ Shared warning applies; artifact paths available for drill/plan/execution checks.

## 4) Coach Report

**Overall:** ⚠️

- **Entry condition:** ⚠️ First step is non-blocking completion check for Player Value, while final report step enforces Player Value as a blocker.
- **User goal clarity:** ✅ Goal is clear: readiness then deterministic report export.
- **Step order:** ✅ Player Value context → practice context → report export is sensible.
- **Step label clarity:** ✅ Labels are short and understandable.
- **Step description clarity:** ⚠️ Practice-context wording improved to clarify optionality + documenting gaps when absent.
- **Prerequisite clarity:** ⚠️ `confirm-practice` has `prerequisite_keys` only and no completion key, so it acts as a context prompt rather than a strict gate (acceptable but should be explicit in UX copy).
- **Blocking reason clarity:** ✅ Report-build block on missing Player Value is explicit.
- **Target route accuracy:** ✅ `/player-value`, `/practice-plans`, `/reports/coach` are valid for intended tasks.
- **Completion check clarity:** ⚠️ Practice context step lacks a completion key, which may confuse users expecting measurable completion for every step.
- **Warnings/evidence refs:** ✅ Shared warning present; report index evidence key exists for completion status.

## 5) Model Governance

**Overall:** ⚠️

- **Entry condition:** ✅ Can start from governance view without project lock-in.
- **User goal clarity:** ✅ Description states data health + queue + active model objectives.
- **Step order:** ✅ Health review before model activation is correct.
- **Step label clarity:** ✅ Clear and concise.
- **Step description clarity:** ⚠️ Review-queue step wording adjusted to avoid implying there are always open items.
- **Prerequisite clarity:** ⚠️ Review queue step uses non-blocking prerequisite, similar caveat as Improve Data Quality.
- **Blocking reason clarity:** ✅ Activate-model step clearly blocks on missing dataset health.
- **Target route accuracy:** ✅ `/local-lab`, `/review-queue`, `/model-registry` map correctly.
- **Completion check clarity:** ✅ Dataset/model checks clear; review queue step intentionally informational.
- **Warnings/evidence refs:** ✅ Shared warning + prerequisite artifact references are available.

---

## Cross-workflow observations

1. **Strong pattern:** Templates consistently avoid auto-execution and route users to existing tools.
2. **Usability caveat:** Some steps use `prerequisite_keys` without `blocking_prerequisite_keys` or a completion key; these behave like guidance prompts rather than enforceable milestones.
3. **Evidence quality:** Non-project prerequisites include artifact paths; project-scoped checks (`has_tracking`, `has_tracking_review`, `has_player_aliases`) currently expose `artifact_path=None`, so users rely on detail text rather than clickable paths.

## Follow-up backlog

### P0 (must-fix)
- None identified.

### P1 (important)
1. **Clarify informational vs gated steps in UI**
   - Add explicit badge or copy in workflow detail for steps that are advisory (no blocking keys and/or no completion key) to reduce completion ambiguity.
2. **Expose project-scoped evidence paths**
   - Provide project-relative artifact paths for `has_tracking`, `has_tracking_review`, `has_player_aliases` when `project_id` is known.

### P2 (nice-to-have)
1. **Template authoring guardrails**
   - Add lightweight validation/test that flags steps with prerequisites but no blocking/completion semantics unless intentionally marked “advisory.”
2. **Terminology normalization**
   - Standardize wording across templates for “review queue” vs “quality queue” and “dataset health” vs “dataset/manifests” for scan consistency.
3. **Workflow help text polish**
   - Add one-line rubric hint on detail page explaining how status is computed (`COMPLETED` from completion key, `BLOCKED` from missing blocking prerequisites).

## Low-risk copy improvements applied

Applied in template step descriptions:
- Improve Data Quality: clarified high-priority review step is conditional (“when present”).
- Model Governance: clarified review-queue step is conditional (“when present”).
- Coach Report: clarified practice-context step as strengthening evidence, with guidance to document gaps.

No workflow types were added, no auto-execution behavior was introduced, and no workflow engine redesign was performed.
