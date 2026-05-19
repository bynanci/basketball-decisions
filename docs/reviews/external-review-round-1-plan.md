# ER1 External Review Round 1 Plan & Reviewer Scripts (Issue #118)

Date: 2026-05-19  
Audience: External reviewers evaluating Court IQ v0.1 as a guided local demo.

## 1) Objective

Run a structured external review round that validates whether the v0.1 demo narrative is understandable, trustworthy, and actionable across six reviewer personas without adding product scope beyond v0.1.

This ER1 plan is intentionally documentation-only and does **not** introduce product feature work.

## 2) Scope and inputs used

ER1 scripts are based on these baseline artifacts:

- **S1 sample project** deterministic walkthrough and route expectations.
- **v0.1 demo checklist** startup/verification path and caveats.
- **v0.1 release notes** positioning, known limitations, and what-not-to-claim language.
- **Known limitations** and trust warnings that must be repeated during all sessions.

## 3) Session-wide guardrails (all personas)

1. State upfront: “This is a local-first v0.1 demo with deterministic seeded sample data.”
2. State upfront: “Outputs are decision-support and explainability artifacts, not autonomous decisions or official scouting grades.”
3. Keep to seeded S1 flow; do not evaluate unsupported production expectations.
4. Capture confusion points, trust interpretation errors, and dead-end navigation points as top-priority findings.
5. Do not fix issues live; document findings for post-ER1 triage.

## 4) Standard setup (before each script)

- Follow v0.1 demo checklist environment and startup steps.
- Confirm backend health at `/api/sample-data/status`.
- Seed/reseed deterministic sample project.
- Open frontend and verify core routes are reachable.
- If flow breaks, recover via development dashboard and reseed protocol.

---

## 5) Reviewer Script A — Coach

### Scenario
A coach needs to quickly understand a seeded player’s current priorities, convert recommendations into a practice plan, and verify execution follow-through.

### Starting route
`/development-dashboard`

### Task list
1. Confirm active sample context from dashboard.
2. Open coach report summary (`/coach-reports` or `/reports/coach` depending nav label).
3. Summarize top 2–3 recommendations in plain coaching language.
4. Open drills (`/drills`) and select at least one recommendation-linked drill.
5. Open practice plans (`/practice-plans`) and verify drill flow/blocks are coherent.
6. Open practice executions (`/practice-executions`) to confirm loop closure exists.

### Expected behavior
- Coach can find a readable report without needing technical context.
- Recommendations appear advisory (not absolute mandates).
- Drill and practice plan pages feel connected to report rationale.
- Execution data appears as follow-through evidence, not final truth.

### Questions to ask
- “What decision would you make next after reading this report?”
- “What part felt most/least trustworthy?”
- “Did any wording feel too technical or too absolute?”
- “Could you explain the recommendation to an assistant coach in one sentence?”

### What to observe silently
- Time-to-first-action from dashboard.
- Whether user confuses recommendation with prescription.
- Whether user asks “where did this come from?” (evidence discoverability).
- Whether route labels (coach report vs reports/coach) create hesitation.

### Pass/fail criteria
- **Pass:** Coach can complete the path and state a plausible next practice decision with correct caveat framing.
- **Fail:** Coach cannot map report → drill → plan flow, or interprets outputs as autonomous/final decisions.

### Timebox
20 minutes total (5 min orientation, 12 min tasks, 3 min debrief).

---

## 6) Reviewer Script B — Player

### Scenario
A player wants to understand their value/trend signals and what training focus is being suggested.

### Starting route
`/player-value`

### Task list
1. Open player value summary and identify the seeded player context.
2. Navigate into player value detail (`/player-value/:projectId/:playerKey`).
3. Review trends/evidence links if available (`/player-value/trends`).
4. Identify one strengths signal and one improvement focus.
5. Open drills page and choose one drill aligned to improvement focus.

### Expected behavior
- Player-facing language is interpretable without analyst jargon.
- Trend/value signals are understandable as directional guidance.
- Evidence/trend context can be followed without dead ends.

### Questions to ask
- “What do you think this page is telling you to do this week?”
- “Which metric/signal was hardest to interpret?”
- “Did this feel like a grade, advice, or both?”
- “What wording would make this clearer for players?”

### What to observe silently
- Emotional reaction to scoring/trust indicators.
- Misread risk: treating value as official grade/ranking.
- Whether player can translate signal into a concrete drill choice.
- Navigation friction between summary, details, and trends.

### Pass/fail criteria
- **Pass:** Player can explain one actionable training focus and correctly frame output as guidance.
- **Fail:** Player leaves confused about action, or interprets value as authoritative final rating.

### Timebox
18 minutes total (4 min orientation, 11 min tasks, 3 min debrief).

---

## 7) Reviewer Script C — Analyst / Video Tagger

### Scenario
An analyst/video tagger validates whether evidence lineage and review surfaces support confidence in the seeded outputs.

### Starting route
`/projects/:projectId` (from seeded sample link)

### Task list
1. Inspect project artifact view for expected seeded outputs.
2. Open coach report and cross-check references to player/practice outputs.
3. Open player value detail and inspect evidence/trend linkage.
4. Open review queue (`/review-queue`) and assess actionability or zero-state guidance.
5. Open workflows (`/workflows`) to verify guided handoff coherence.

### Expected behavior
- Artifact lineage appears coherent across report/value/plan/workflow.
- Missing artifact states are either absent (happy path) or clearly explained.
- Review surfaces support human QA rather than implying automatic correctness.

### Questions to ask
- “Where would you challenge this output first?”
- “Which artifact linkage felt weak or hard to verify?”
- “What additional metadata would reduce your QA time?”
- “Did any page overstate certainty?”

### What to observe silently
- Whether analyst can reconstruct end-to-end provenance quickly.
- Confusion around “artifact” vocabulary.
- Behavior in queue zero-state (dead end vs next action).
- Trust warning visibility before interpretation.

### Pass/fail criteria
- **Pass:** Analyst can trace key outputs across surfaces and identify QA points without route breakdown.
- **Fail:** Analyst cannot verify lineage confidence or encounters unclear/blocked review steps.

### Timebox
25 minutes total (5 min orientation, 16 min tasks, 4 min debrief).

---

## 8) Reviewer Script D — Product Manager

### Scenario
A PM evaluates if the v0.1 walkthrough communicates scope boundaries, value proposition, and caveats consistently.

### Starting route
`/development-dashboard`

### Task list
1. Execute condensed end-to-end narrative: dashboard → coach report → player value → practice plan → workflows.
2. Identify where v0.1 positioning is clear vs ambiguous.
3. Validate that trust caveats appear before high-stakes interpretation points.
4. Identify one high-impact UX/content risk for next release gate.

### Expected behavior
- Demo flow aligns with documented v0.1 narrative.
- Scope boundaries (“local demo/reviewer build”) are reinforced.
- No page contradicts release-note caveats or makes prohibited claims.

### Questions to ask
- “At what point would an external stakeholder overestimate product maturity?”
- “Where should we tighten scope language first?”
- “Did the flow feel coherent for a 10-minute executive walkthrough?”
- “What is the single highest-risk misunderstanding today?”

### What to observe silently
- Moments where PM pauses to reconcile inconsistent terminology.
- Whether PM must provide missing verbal context not present in UI.
- Perceived narrative continuity across roles/surfaces.

### Pass/fail criteria
- **Pass:** PM can deliver a consistent, caveated v0.1 story without contradicting limitations.
- **Fail:** PM repeatedly needs out-of-band explanations to avoid misleading claims.

### Timebox
20 minutes total (4 min orientation, 12 min tasks, 4 min debrief).

---

## 9) Reviewer Script E — UX Usability Tester

### Scenario
A usability specialist evaluates navigation clarity, language comprehension, and recovery behavior for first-time reviewers.

### Starting route
`/`

### Task list
1. Start from Home and load/refresh sample project.
2. Reach development dashboard without facilitator intervention.
3. Complete a “find and explain” task on coach report content.
4. Complete a “find and explain” task on player value/trends.
5. Recover from one induced disruption (stale page or reseed).
6. Return to dashboard and describe current status.

### Expected behavior
- Key routes are discoverable and labels are understandable.
- Empty/fallback states guide next action.
- Recovery path is clear and low stress.

### Questions to ask
- “Which term was most confusing (artifact, value, workflow, trust)?”
- “Where did you expect a different label or button?”
- “Did any page feel like a dead end?”
- “What single copy change would help most?”

### What to observe silently
- Click path detours and hesitation points.
- Terminology misinterpretation rate.
- Whether user can self-recover without facilitator hints.
- Confidence level before and after trust warning exposure.

### Pass/fail criteria
- **Pass:** Tester can complete core path + recovery flow with minor hesitation only.
- **Fail:** Frequent dead ends, label confusion, or inability to recover without intervention.

### Timebox
30 minutes total (5 min orientation, 20 min tasks, 5 min debrief).

---

## 10) Reviewer Script F — Technical / Data Reviewer

### Scenario
A technical/data reviewer validates deterministic behavior, route coverage, and caveat correctness against v0.1 promises.

### Starting route
Backend health endpoint `/api/sample-data/status`, then `/development-dashboard`

### Task list
1. Verify seed status, run seed endpoint, verify status again.
2. Spot-check route chain coverage across:
   - dashboard
   - player value + detail/trends
   - coach reports
   - drills
   - practice plans
   - practice executions
   - workflows
3. Validate deterministic behavior by reseeding and confirming no critical path regression.
4. Validate that known limitations/trust caveats are accurately represented in reviewer narrative.

### Expected behavior
- Seed lifecycle is stable and reproducible for demo use.
- Core demo routes load and remain coherent after reseed.
- Review framing correctly distinguishes decision-support from decision automation.

### Questions to ask
- “Where is determinism strongest/weakest in this walkthrough?”
- “What edge case would you test next before broader review distribution?”
- “Did any UI claim exceed what deterministic sample data supports?”
- “What minimal telemetry/logging would improve reviewer confidence?”

### What to observe silently
- Any divergence after reseed.
- Implicit assumptions that only hold on happy path.
- Mismatch between expected route names and actual navigation labels.
- Whether trust caveats are treated as optional instead of required.

### Pass/fail criteria
- **Pass:** Technical reviewer confirms reproducible seeded path and accurate caveat positioning.
- **Fail:** Determinism/regression issues or materially misleading interpretation framing.

### Timebox
30 minutes total (6 min orientation, 20 min tasks, 4 min debrief).

---

## 11) Evidence capture template (all sessions)

For each session, log:

- Reviewer role and date/time.
- Completed tasks (Y/N).
- Time to complete key milestones.
- Top 3 confusion points (with route).
- Trust/caveat comprehension (correct / partial / incorrect).
- Pass/fail outcome and rationale.
- Severity-tagged findings:
  - **P0** misleading claim or high-risk trust misinterpretation
  - **P1** flow blocker or repeated dead end
  - **P2** clarity/copy/navigation friction

## 12) Exit criteria for ER1

ER1 is complete when:

1. All six persona scripts have at least one completed session.
2. All P0/P1 findings are triaged with owner + target release.
3. A consolidated ER1 findings summary is published.
4. No claims in review collateral violate v0.1 release caveats.

## 13) Explicit non-goals

- No feature implementation.
- No model/scoring redesign.
- No production-readiness certification.
- No expansion beyond deterministic S1 review baseline.
