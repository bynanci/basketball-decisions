# ML-Assisted Review Queue Ranking Spec

## 1. Purpose
Define a **design-only specification** for ML-assisted ranking of Review Queue items so reviewers see the highest trust-impact work first. This spec scopes how ranking suggestions may be produced and surfaced, while preserving existing human review authority and current queue resolution behavior.

This spec exists to:
- improve ordering quality for trust-critical review workload,
- reduce reviewer time spent triaging lower-impact items,
- create a governed path to later implementation and offline experimentation,
- establish hard constraints so ML cannot perform resolution actions.

## 2. Non-goals
The following are explicitly out of scope for this issue/spec:
- training or shipping any model,
- adding runtime ML ranking in production,
- changing current Review Queue state transitions or resolution flows,
- mutating artifacts based on model output,
- replacing deterministic/manual sorting modes.

## 3. Ranking Objective
Rank review items by **expected impact on trust-critical downstream outputs**.

Operationally, higher-ranked items should be those where earlier human review is most likely to:
1. prevent or reduce propagation of harmful/incorrect outputs,
2. protect decision quality and explainability,
3. lower downstream rework cost.

Ranking is advisory: it may reorder/suggest priority only, never resolve items.

## 4. Candidate Review Item Types
Initial candidate population for ranking includes:
- `RECOGNITION_TRACK`
- `RECOGNITION_DETECTION`
- `PLAYER_VALUE_ATTRIBUTION`
- `DECISION_PROMPT`
- `DECISION_ATTEMPT`
- `RULE_DRAFT`
- `DATASET_HEALTH_WARNING`
- `ARTIFACT_STALENESS`

## 5. Allowed Features
Only the following feature set is allowed for MVP modeling/experimentation:
- `item_type`
- `current_priority`
- `player_key_known` (known/unknown)
- `has_source_track_ids`
- `has_context_track_ids`
- `unknown_attribution_flag`
- `confidence_value`
- `warning_count`
- `related_decision_event_count`
- `opportunity_cost`
- `stale_artifact_severity`
- `affected_downstream_artifact_count`
- `item_age`
- `previous_similar_feedback_signal_count`

Guidance:
- Prefer normalized/typed features over free text.
- Feature derivations must remain auditable and reproducible.
- Feature availability gaps must degrade gracefully (null-safe defaults).

## 6. Prohibited Features
The following must not be used directly or via derived proxies unless later approved by governance:
- real player identity,
- protected attributes,
- copyright-sensitive source labels as direct quality proxy,
- external scouting data,
- private notes unless explicitly marked eligible,
- free-text coach notes without review.

Implementation note: feature review must include proxy-risk checks to reduce leakage of prohibited information through indirect encodings.

## 7. Labeling Strategy
Because this is ranking, labels should be derived from historical human review outcomes and downstream impact signals.

Proposed labeling approach (offline only):
1. Build historical item cohorts by type and timeframe.
2. Aggregate post-review effects (e.g., corrective actions, severity adjustments, downstream artifact changes).
3. Convert impact signals into ordinal relevance tiers (e.g., high/medium/low trust impact).
4. Validate label consistency with reviewer calibration sessions.
5. Track label freshness and drift over time.

Label generation requirements:
- deterministic transformations,
- versioned label definitions,
- reproducible backfills,
- clear exclusion rules for incomplete/ambiguous histories.

## 8. Target Variable
Primary target: **trust-impact relevance score** suitable for learning-to-rank.

MVP target definition:
- an ordinal or numeric relevance value estimating expected trust-critical downstream impact if item is reviewed now,
- computed only from approved historical outcomes,
- capped/normalized to avoid domination by rare extreme events.

Secondary analysis target (optional, offline): binary "high-impact" indicator for threshold-based diagnostics.

## 9. Evaluation Metrics
Offline ranking evaluation must include:
- **Precision@K**
- **Recall@K**
- **NDCG@K**
- **reviewer time saved proxy**
- **false-prioritization rate**

Metric guidance:
- Report at multiple K values aligned to realistic daily reviewer capacity.
- Slice metrics by item type to detect uneven performance.
- Track confidence intervals where feasible.
- Define alert thresholds for regressions versus deterministic baseline ordering.

## 10. Human-in-the-Loop Requirements
Hard constraints:
- ML may only reorder or suggest priority.
- ML cannot resolve items.
- ML cannot mutate artifacts.
- ML cannot assign aliases.
- ML cannot approve rules.
- ML cannot hide low-ranked items.
- UI must always support deterministic sort fallback.

Reviewer experience requirements:
- visible indication that ordering is ML-assisted (when active),
- one-click fallback to deterministic sort,
- no loss of access to any queue item regardless of rank.

## 11. Fallback Behavior
If ML ranking is unavailable, degraded, or disallowed:
1. Fall back to deterministic sort immediately.
2. Preserve reviewer-selected explicit sort preference when possible.
3. Emit structured telemetry for fallback reason (e.g., unavailable model, missing features, policy block).
4. Never block queue rendering because ranking failed.

Fallback must be safe-by-default and operationally transparent.

## 12. Model Registry Requirements
Any future model artifact considered for this ranking use case must have registry metadata before activation in any environment:
- model identifier and semantic version,
- training data window and lineage,
- feature schema version,
- label definition version,
- evaluation report snapshot (metrics + slices),
- policy/governance approval status,
- rollback pointer to prior approved version,
- owner/on-call contact.

No registry entry => model ineligible for runtime use.

## 13. UI Disclosure Requirements
When ML-assisted ordering is surfaced (future phase), UI must disclose:
- that ranking is ML-assisted,
- that suggestions do not auto-resolve items,
- that users can switch to deterministic sort,
- that all items remain visible/reachable.

Disclosure copy should be concise, persistent enough for awareness, and consistent with trust/safety policy language.

## 14. Data Governance Constraints
Governance requirements for this spec:
- data minimization: include only allowed features,
- purpose limitation: ranking for review prioritization only,
- access controls for sensitive review data,
- audit logs for feature extraction and scoring events,
- retention windows for training/eval artifacts,
- documented handling for prohibited/uncertain fields,
- periodic compliance review for proxy leakage risk.

Any governance violation must disable ML ranking path and force deterministic fallback.

## 15. MVP Experiment Plan
This plan is **offline/spec-driven only** and does not change runtime behavior.

1. **Dataset assembly (offline):** Build historical ranking dataset from candidate item types and allowed features.
2. **Label pipeline:** Implement deterministic label generation for trust-impact relevance with versioning.
3. **Baseline definitions:** Establish deterministic queue-order baselines for comparison.
4. **Model prototyping (offline only):** Evaluate simple ranking candidates (e.g., heuristic score, tree-based ranker) without deployment.
5. **Evaluation:** Report Precision@K, Recall@K, NDCG@K, reviewer time saved proxy, false-prioritization rate, and slice analysis.
6. **Human calibration:** Run reviewer spot checks on ranked samples to validate practical usefulness.
7. **Governance gate:** Review feature compliance, prohibited-feature leakage checks, and documentation completeness.
8. **Go/No-go recommendation:** Produce recommendation memo for a future implementation issue.

Explicit MVP guardrails:
- do not train production models,
- do not integrate runtime ML ranking,
- do not alter Review Queue resolution behavior.
