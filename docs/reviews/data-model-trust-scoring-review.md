# R5 Data / Model Trust & Scoring Methodology Review (Issue #105)

## Scope and constraints
- Reviewed current trust/scoring behavior only.
- No scoring formula changes were made.
- No model training changes were made.
- No new metrics were introduced.

## 1) Player Value formula clarity
**Assessment:** Clear and auditable.

The formula is explicitly decomposed into five weighted components with plain-language explanations attached to each component. Final score is the sum of component contributions, and component lineage is persisted in summary outputs.

What is strong:
- Named components and fixed weights are explicit (`0.45`, `0.20`, `0.15`, `0.10`, `0.10`).
- Each component has an explanation string describing how it is computed.
- Test coverage asserts component contributions sum to `player_value_score`.

Residual risk:
- Confidence and score can be conflated by downstream consumers if UI copy does not keep them separate.

## 2) Confidence and warning behavior
**Assessment:** Generally robust; warning-first behavior is consistent.

Confidence is bounded and built from deterministic factors (event count, UNKNOWN identity, recognition availability). Explicit warnings are added for low-sample and UNKNOWN conditions.

What is strong:
- Confidence is clipped to `[0, 1]`.
- Low-data scenario warning (`fewer than 5 decision events`) is explicit.
- UNKNOWN attribution warning is explicit and non-overclaiming.
- Evidence endpoint repeats low-confidence caution at event inspection layer.

Residual risk:
- Confidence remains a compact scalar; readers may miss *why* confidence is low unless warning panels are always visible.

## 3) `source_track_ids` vs `context_track_ids` integrity
**Assessment:** Strong separation and integrity.

Prompt payload generation keeps `context_track_ids` separate from identity-bearing `source_track_ids`; source linkage is attached per option. Evidence logic explicitly states context IDs are not alias evidence.

What is strong:
- Frontend payload builder always emits empty top-level `source_track_ids` and maps per-option source IDs.
- Unit tests assert the split contract.
- Evidence warnings explicitly state context tracks are frame context only.

Residual risk:
- If future clients bypass helper utilities and write raw payloads, separation could regress unless server-side validation remains strict.

## 4) UNKNOWN attribution handling
**Assessment:** Conservative and appropriate.

System falls back to `UNKNOWN` instead of guessing when alias evidence is absent or ambiguous, and records warnings.

What is strong:
- UNKNOWN is explicit when no aliases exist.
- Ambiguous multi-alias track matches resolve to UNKNOWN with warning.
- Coach report and player value surfaces include language that no real/inferred identity is claimed.

Residual risk:
- Operational teams may perceive UNKNOWN-heavy outputs as low utility; this is a governance/labeling throughput issue, not a scoring flaw.

## 5) Mixed baseline warnings
**Assessment:** Strong and correctly cautionary.

Trend and coach-report paths detect mixed baseline metadata (formula/model/rule/dataset fingerprint) and emit explicit “compare cautiously” warnings.

What is strong:
- Baseline field set is centralized and reused.
- Warning text explicitly instructs not to hide the warning.

Residual risk:
- Warning-only mitigation still allows visual comparison; some teams may require hard gating for mixed baselines.

## 6) Artifact freshness warnings
**Assessment:** Strong for detection; medium risk for operational follow-through.

Artifact map computes freshness from timestamps/mtimes and dependencies, then coach report summary pulls stale artifact warnings.

What is strong:
- Read-only freshness map prevents silent mutation.
- Stale warnings are propagated into trust-facing report summaries.

Residual risk:
- Detection is robust, but trust depends on operators actually resolving stale upstream artifacts before using outputs.

## 7) Recognition model active version behavior
**Assessment:** Sound activation semantics.

Model registry tracks `active_version`; tests cover activation, switching, rollback, and non-activation defaults.

What is strong:
- Explicit activate endpoints with previous/next active version transitions.
- Baseline training can optionally activate; otherwise registry can remain with no active version.

Residual risk:
- If active model artifacts become unreadable in environment mismatch scenarios, trust can degrade without immediate operator intervention.

## 8) Decision rule contribution transparency
**Assessment:** Good transparency for scoring lineage.

Evidence model includes base score, rule score delta, final score, cap flag, and full rule application payload, enabling audit of contribution mechanics.

What is strong:
- Per-event fields expose pre/post rule scoring.
- Coach report rule section surfaces rule IDs, role/situation, and weights.

Residual risk:
- Human readability of deeply nested rule application objects may require better UI rendering to avoid misinterpretation.

## 9) Coach Report warning language
**Assessment:** Strong; language is appropriately constrained.

Coach report builder consistently degrades to warnings (missing/unreadable artifacts) rather than crashing, and uses non-overclaim wording across sections.

What is strong:
- Missing/unreadable artifact warnings are explicit with affected artifact labels.
- Report copy avoids claiming official grades or generated coaching authority.
- Summary mode aggregates mixed-baseline, stale-artifact, and source-governance warnings.

Residual risk:
- Warning volume can grow noisy in degraded states, potentially hiding highest-priority risks.

## 10) Player Home simplified warnings
**Assessment:** Adequate but intentionally coarse.

Player Home surfaces a simplified trust warning when confidence is below threshold.

What is strong:
- Clear player-friendly caution for low trust.
- Safe fallback content when summary data is missing.

Residual risk:
- Simplification may obscure root-cause categories (identity ambiguity vs sparse data vs stale artifacts).

## 11) Source governance boundaries
**Assessment:** Strong and enforceable.

Governance constraints (rights, scope, training eligibility) are enforced in source creation/update and dataset export inclusion rules.

What is strong:
- YouTube reference-only defaults are non-training.
- Invalid governance combinations are rejected.
- Dataset export skips projects with missing governance or non-training scopes.
- Coach report source-governance warnings flag unsafe/unknown scopes and rights states.

Residual risk:
- Governance correctness still depends on truthful upstream metadata entry.

## 12) Overclaim risks
**Assessment:** Managed but still policy-dependent.

The codebase repeatedly includes anti-overclaim language and warning surfaces; UNKNOWN and low-confidence pathways are explicit.

What is strong:
- UNKNOWN identity and local-only claim boundaries are surfaced in output text.
- Report and product docs emphasize decision-support positioning.

Residual risk:
- Human presentation layers (demo scripts, stakeholder slides) can still overstate certainty if warnings are omitted.

---

## Final verdict
**TRUST_READY_WITH_WARNINGS**

### Rationale
The current implementation is methodologically transparent, deterministic, and warning-forward across scoring, evidence, governance, and freshness dimensions. It is suitable for decision-support use **with explicit warning visibility preserved**. The remaining risks are primarily operational/comms risks (warning fatigue, stale-artifact follow-through, potential overclaim in external narration), not hidden formula or attribution defects.

### Recommended guardrails (non-formula, non-metric)
1. Preserve warning visibility in all trust-facing views (do not collapse by default).
2. Keep UNKNOWN attribution and mixed-baseline warnings non-dismissable in summary/report exports.
3. Treat stale artifact warnings as pre-use checklist items for coach-facing distribution.
