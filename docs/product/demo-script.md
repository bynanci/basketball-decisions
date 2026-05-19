# Court IQ Demo Script (S13)

## Short pitch

Court IQ turns basketball video analysis into traceable decision evidence, player value, and training actions.

## Demo setup (deterministic, local, repeatable)

- **Target duration:** under 10 minutes.
- **Baseline:** use the S1 sample project only.
- **No network/external video required:** do not depend on YouTube import or third-party assets.
- **No overclaim policy:** do not present outputs as official scouting grades or objective truth; frame them as explainable, reviewable decision-support artifacts.

---

## 10-minute walkthrough (route-by-route)

> Timeboxing tip: spend ~45–60 seconds per step and ~90 seconds on Player Value/Evidence.

### 1) Load sample project

- **Route:** `/`
- **User goal:** initialize a known-good project state for the demo.
- **Talking point:** "We start from deterministic local sample data so every demo shows the same artifacts."
- **Expected UI result:** a sample project appears and primary navigation into project/report/training surfaces becomes actionable.
- **Fallback if data missing:** click **Load Sample Project** again; if still missing, reseed sample data from local backend (`/api/sample-data/seed`) and refresh.
- **What not to overclaim:** do **not** claim this is live opponent/game ingestion.

### 2) Open Development Dashboard

- **Route:** `/development-dashboard`
- **User goal:** orient stakeholders using command-center status.
- **Talking point:** "This page shows project health, readiness, and where to go next."
- **Expected UI result:** grouped navigation, progress/health signals, and project-level status summaries.
- **Fallback if data missing:** return to `/`, reload sample project, then reopen dashboard.
- **What not to overclaim:** do not claim fully autonomous workflow orchestration.

### 3) Explain next-best-actions

- **Route:** `/development-dashboard` (stay on page)
- **User goal:** explain prioritization logic before drilling into details.
- **Talking point:** "Next-best-actions are transparent suggestions based on missing/stale artifacts, not black-box mandates."
- **Expected UI result:** actionable prompts that route to relevant pipeline/report/workflow pages.
- **Fallback if data missing:** narrate expected behavior and continue to direct route walkthrough.
- **What not to overclaim:** do not claim guaranteed optimal recommendations.

### 4) Open Player Home

- **Route:** `/player-value`
- **User goal:** show player-facing or coach-facing value overview.
- **Talking point:** "Player Home summarizes where each player currently grades strongest/weakest in this project context."
- **Expected UI result:** player list/summary cards with value indicators and links to player detail evidence.
- **Fallback if data missing:** load sample project and refresh; if needed, continue with a single player detail if only partial rows render.
- **What not to overclaim:** do not present as a recruiting ranking across leagues/teams.

### 5) Open Player Value

- **Route:** `/player-value/:projectId/:playerKey` (open any seeded player)
- **User goal:** move from summary to per-player explanation.
- **Talking point:** "Value is decomposed into explainable components tied back to events and evidence."
- **Expected UI result:** player-specific components, evidence links, and traceable rationale.
- **Fallback if data missing:** return to `/player-value` and choose another seeded player key.
- **What not to overclaim:** do not claim model output equals final coach judgment.

### 6) Inspect Evidence

- **Route:** `/player-value/:projectId/:playerKey` (evidence section), optionally `/projects/:projectId/tracking-review`
- **User goal:** prove traceability from conclusion to underlying artifacts.
- **Talking point:** "Every claim should be inspectable through artifact lineage."
- **Expected UI result:** linked possessions/events/diagnostics and artifact references.
- **Fallback if data missing:** jump to tracking review artifacts and explain evidence chain from cleaned tracking forward.
- **What not to overclaim:** do not imply perfect event labeling or zero annotation error.

### 7) Generate or open Coach Report Summary

- **Route:** `/reports/coach`
- **User goal:** show coach-readable synthesis.
- **Talking point:** "This is the translation layer from analysis detail to coach action language."
- **Expected UI result:** report summary with themes, supporting notes, and evidence hooks.
- **Fallback if data missing:** open existing sample report if present; otherwise explain that report requires upstream analyzed artifacts.
- **What not to overclaim:** do not present summary text as exhaustive scouting coverage.

### 8) Open Drill Recommendations

- **Route:** `/drills`
- **User goal:** show training prescriptions tied to report themes.
- **Talking point:** "Recommendations connect observed decision patterns to teachable drill actions."
- **Expected UI result:** drill list/recommendations with rationale and context.
- **Fallback if data missing:** narrate from available drill catalog and link expected dependency on report/player artifacts.
- **What not to overclaim:** do not claim medical/performance guarantees.

### 9) Build or open Practice Plan

- **Route:** `/practice-plans`
- **User goal:** convert recommended drills into executable session planning.
- **Talking point:** "Planning is where analysis turns into concrete reps, sequencing, and constraints."
- **Expected UI result:** existing plan list and/or plan builder with drill selections.
- **Fallback if data missing:** open any seeded plan; if none, show empty-state flow and dependencies.
- **What not to overclaim:** do not claim automatic optimization for all roster constraints.

### 10) Start or inspect Practice Execution

- **Route:** `/practice-executions` (and optional `/practice-executions/:executionId`)
- **User goal:** demonstrate execution tracking from planned work.
- **Talking point:** "Execution closes the loop: what was planned vs. what happened."
- **Expected UI result:** execution entries with detail links and status/feedback context.
- **Fallback if data missing:** open list view and explain expected execution artifact created after plan run.
- **What not to overclaim:** do not claim sensor-grade tracking unless explicitly instrumented.

### 11) Show Feedback Signals

- **Route:** `/practice-executions/:executionId` (or list-level signal preview)
- **User goal:** connect training execution to measurable feedback.
- **Talking point:** "Feedback signals provide directional learning indicators, not final verdicts."
- **Expected UI result:** signal summaries and notes tied to execution context.
- **Fallback if data missing:** use execution list metadata and explain signal generation prerequisites.
- **What not to overclaim:** do not claim causal proof that one drill alone produced outcomes.

### 12) Open Workflow

- **Route:** `/workflows` (optional `/workflows/:workflowId`)
- **User goal:** show operational recovery and guided tasking.
- **Talking point:** "When artifacts are incomplete, workflows provide explicit recovery paths."
- **Expected UI result:** workflow list/status and detail actions.
- **Fallback if data missing:** return to dashboard next-best-actions and point to the same recovery intent.
- **What not to overclaim:** do not claim every exception can be auto-resolved.

### 13) Explain Artifact Health / trust warnings

- **Route:** `/development-dashboard`
- **User goal:** close on reliability and governance.
- **Talking point:** "Trust comes from visible artifact health, freshness, and warnings—not hidden confidence scores."
- **Expected UI result:** health indicators/warnings tied to missing or stale upstream artifacts.
- **Fallback if data missing:** intentionally reference expected warning states when prerequisites are absent.
- **What not to overclaim:** do not claim perfect accuracy or official scouting certification.

---

## Demo variants by audience

### 1) Coach demo (action-first)

- **Emphasize:** Steps 7–11 (report → drills → practice plan → execution → feedback).
- **Skip quickly:** deep analyst pipeline internals unless asked.
- **Narrative:** "What should we coach this week, and why?"

### 2) Analyst demo (traceability-first)

- **Emphasize:** Steps 2, 3, 6, 12, 13 (dashboard actions, evidence lineage, workflow recovery, health warnings).
- **Include optional detour:** `/projects/:projectId/pipeline` and `/projects/:projectId/tracking-review` for QC context.
- **Narrative:** "How do we know downstream outputs are trustworthy?"

### 3) Player demo (clarity-first)

- **Emphasize:** Steps 4, 5, 11 (player value summary/detail and practice feedback).
- **Optional entry:** `/start` and `/training` for role-based orientation before player value.
- **Narrative:** "What do I improve next, with evidence I can understand?"

---

## Limitations and responsible language (use in every demo)

- Court IQ outputs are **decision-support artifacts**, not final coaching truth.
- Sample-project metrics are **demo fixtures**, not live competition benchmarks.
- Feedback signals are **directional** and should be interpreted with coach/analyst context.
- Do not claim official scouting grades, guaranteed player outcomes, or causal certainty.
