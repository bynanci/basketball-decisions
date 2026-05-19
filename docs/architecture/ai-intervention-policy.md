# AI1 ML / LLM Intervention Policy

Status: Draft (Issue #124)  
Owner: Product + Engineering + Review Ops  
Last updated: 2026-05-19

## Purpose and scope

This policy defines where ML and LLM assistance is allowed in Court IQ, where it is explicitly prohibited, and what controls are required to preserve deterministic, explainable basketball decision outputs.

This policy applies to:
- backend workflow services and ranking helpers,
- frontend reviewer and coach-facing UX,
- artifact generation and review workflows,
- any future AI-assisted experiments.

This policy does **not** authorize direct deployment of ML/LLM runtime calls. It sets boundaries and compliance requirements only.

## 1) Deterministic core (non-negotiable)

The following core system behaviors are deterministic and must not be delegated to ML or LLM components:

1. **Player Value formula**
   - The Player Value formula is deterministic and rule-defined.
   - No ML/LLM component may modify coefficients, features, weighting, or outputs.

2. **Decision rule application**
   - Rule evaluation logic and pass/fail outcomes must execute through deterministic rule engines only.
   - AI may not adjudicate correctness for decision rules.

3. **Artifact freshness**
   - Freshness windows, staleness checks, and invalidation rules remain deterministic and configuration-driven.
   - AI may only suggest, never enforce, freshness outcomes.

4. **Source governance**
   - Approved source lists, trust policies, and source eligibility checks remain deterministic.
   - AI cannot whitelist non-approved sources.

5. **Review action log**
   - Review actions (approve/reject/edit/escalate) are logged as immutable user-attributed events.
   - AI may draft text but cannot authoritatively perform or backfill review actions.

6. **Practice feedback signals**
   - Computed practice feedback signals and scoring paths remain deterministic.
   - AI cannot alter signal definitions or score calculations.

7. **Model registry activation**
   - Registry activation/deactivation, version gates, and promotion criteria are human-approved and policy-locked.
   - AI cannot self-activate registry entries.

8. **Dataset eligibility rules**
   - Dataset inclusion/exclusion criteria are deterministic and review-controlled.
   - AI cannot auto-approve dataset eligibility.

## 2) Allowed ML-assisted areas

ML support is limited to non-authoritative ranking, clustering, and anomaly detection tasks:

- tracking quality risk ranking,
- review queue priority ranking,
- recommendation ranking adjustments,
- trend anomaly detection,
- duplicate review item detection.

Controls:
- ML outputs must be marked as advisory.
- Deterministic pipeline outputs remain source-of-truth.
- Every ML suggestion must be reversible and attributable.

## 3) Allowed LLM-assisted areas

LLM support is limited to language and communication quality improvements, not decision authority:

- Coach Report language rewrite,
- reviewer feedback synthesis,
- drill language polish,
- workflow copy simplification,
- warning explanation rewrite,
- demo script explanation draft.

Controls:
- LLM outputs must be marked as generated text drafts.
- Human acceptance is required before publication to official artifacts.
- LLM outputs cannot claim unobserved facts or deterministic score changes.

## 4) Prohibited AI actions

The following actions are forbidden for all ML/LLM components:

- automatically assign real player identity,
- automatically approve decision rules,
- automatically change Player Value,
- automatically decide correct/incorrect decisions,
- automatically label training data without review,
- automatically mutate player aliases,
- automatically hide warnings,
- generate official scouting grades,
- create medical/injury recommendations,
- claim real-world player recognition.

Any attempted implementation of prohibited behavior must fail review and be blocked from merge.

## 5) Human-in-the-loop requirements

1. Any AI-generated recommendation that affects review prioritization, published artifacts, or coach/player-facing language must require explicit human acceptance.
2. Human approver identity, timestamp, and action rationale must be persisted.
3. One-click “accept all” behavior is disallowed for safety-critical or identity-adjacent actions.
4. Human reviewers must have an easy path to reject and edit AI suggestions.

## 6) Evidence-locking rules

1. Inputs used for deterministic decisions must be immutable once a decision artifact is published.
2. AI-generated drafts must retain references to source artifacts and source timestamps.
3. If evidence changes after artifact publication, the system must trigger a re-review path rather than silently mutating prior outputs.
4. Evidence snapshots used in final decisions must be reproducible from stored artifacts.

## 7) Audit logging requirements

For every AI-assisted action, log:
- request context (workflow, artifact IDs, user),
- model/tool identifier and version,
- prompt/template or feature set identifier,
- output summary hash (or structured digest),
- human reviewer action (accepted/rejected/edited),
- timestamps and correlation IDs.

Audit logs must be append-only and queryable for internal reviews.

## 8) Warning and disclosure requirements

1. All AI-assisted outputs shown to users must include clear disclosure (for example: “AI-assisted draft; human-reviewed” when approved).
2. Unreviewed AI drafts must include stronger warnings (for example: “Draft only; not approved for official use”).
3. Any confidence-style indicators must be explicitly labeled as heuristic and non-deterministic.
4. No UI copy may imply verified real-world player identification.

## 9) Testing requirements

Required test coverage for AI-adjacent changes:

- Deterministic regression tests proving Player Value and Decision Engine outputs are unchanged.
- Unit tests proving AI modules cannot invoke prohibited write paths.
- Integration tests for human approval gates.
- Snapshot/contract tests for disclosure labels and warning states.
- Audit log tests validating required fields and immutability semantics.
- Negative tests ensuring prohibited AI actions are blocked.

Release gate: no AI-adjacent feature ships without deterministic regression pass and human-gate integration pass.

## 10) Implementation constraints for issue #124

For this issue and related follow-up work:
- do not implement LLM calls,
- do not implement ML models,
- do not change Player Value formula,
- do not change Decision Engine scoring.

## Related documents

- Artifact freshness and architecture context: [artifact-map.md](./artifact-map.md)
- Local artifact behavior: [local-artifacts.md](./local-artifacts.md)
- Backend workflow context: [backend-services.md](./backend-services.md)
