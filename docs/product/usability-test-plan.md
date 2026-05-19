# Court IQ Usability Test Plan

## Purpose

This plan defines practical, role-specific usability tests for Court IQ using the deterministic sample project. It is designed for moderated sessions with coaches, players, analysts, and technical reviewers/PMs.

## Test setup (applies to all groups)

- Seed sample project before each session:
  - `curl -X POST http://localhost:8000/api/sample-data/seed`
- Open app: `http://localhost:5173`
- Recommended start pages by role:
  - Coach: `/workflows` then `/project/:id` or `/practice-plans`
  - Player: `/player-home`
  - Analyst: `/pipeline` then `/tracking-review`, `/review-queue`, `/workflow/:id`
  - Technical reviewer / PM: `/development-dashboard`
- Session length target: 30–45 minutes per participant.
- Facilitation rule: ask participant to think aloud; avoid coaching unless they are blocked >3 minutes.

## Scoring model

For each task:

- **Pass**: completed without moderator intervention and with correct interpretation.
- **Partial pass**: completed with one hint or minor interpretation gap.
- **Fail**: not completed, incorrect result, or major misunderstanding.

For each user group:

- **Group pass**: at least 80% of core tasks are pass/partial pass, and no critical task fails.
- **Group fail**: fewer than 80% pass/partial pass, or any critical task fails.

---

## 1) Coach test group

### Scenario

You are preparing for the next week of team practices. You want to identify one player weakness from the sample project, review the coach-facing summary, and choose a practice plan you can run tomorrow.

### Task list

1. Find/open the sample project.
2. Locate one player weakness from player value/diagnostic artifacts.
3. Generate or open a coach summary/report that explains the weakness.
4. Review recommended drills/practice plans tied to that weakness.
5. Choose one practice plan and explain why it is the best next action.

### Success criteria

- Participant can identify a specific weakness (not generic, e.g., “late weak-side rotation timing”).
- Participant can find a summary artifact and verbally connect evidence to recommendation.
- Participant can choose a plan and explain expected player outcome in one sentence.

### Observation checklist

- Can they find where the project/workflow starts?
- Do they recognize the difference between analysis outputs and coaching outputs?
- Do they trust the explanation for the recommendation?
- How long to decision (first meaningful recommendation selected)?
- Number of navigation dead ends/backtracks.

### Questions to ask

- “What information made you trust this recommendation?”
- “What was hardest to find?”
- “If this were game-week, what is missing before you act?”
- “How confident are you (1–5) in this plan choice?”

### Expected confusion points

- Confusing workflow status screens with final coach deliverables.
- Not knowing whether drills are generated, curated, or both.
- Difficulty distinguishing player-level issue vs team-level issue.

### Pass/fail criteria

- **Critical task**: identify one weakness + choose one practice plan with rationale.
- **Pass**: completes all 5 tasks within 15 minutes and no critical misunderstanding.
- **Fail**: cannot find weakness evidence or selects plan with no defensible link to evidence.

---

## 2) Player test group

### Scenario

You are a player checking your daily training priorities. You open Player Home and need to explain what you should train next and why.

### Task list

1. Open Player Home.
2. Identify top “train next” recommendation.
3. Explain why that recommendation is shown (signal/evidence).
4. Find one supporting drill/quiz/action.
5. State one concrete action for today’s session.

### Success criteria

- Participant states the top next-skill focus in plain language.
- Participant can point to at least one supporting metric/signal.
- Participant can name one executable training action.

### Observation checklist

- Time to first accurate “train next” statement.
- Can participant interpret labels/terminology without help?
- Does participant understand confidence/priority cues?
- Do they notice links to drills, quiz, or execution feedback?

### Questions to ask

- “What do you think the app wants you to do next?”
- “What part of this page feels unclear or too technical?”
- “Do you feel this recommendation is personalized? Why?”
- “What would make this easier to use before practice?”

### Expected confusion points

- Misreading diagnostic metrics as final instructions.
- Unclear distinction between “recommended now” vs “long-term development.”
- Uncertainty whether actions are mandatory or optional.

### Pass/fail criteria

- **Critical task**: accurately explain “what to train next” from Player Home.
- **Pass**: completes all 5 tasks within 10 minutes with no moderator hint.
- **Fail**: cannot identify top recommendation or explains it incorrectly.

---

## 3) Analyst test group

### Scenario

You are validating project quality before coaches and players consume outputs. You must verify artifact freshness, resolve at least one blocker, and confirm workflow readiness.

### Task list

1. Open pipeline/workflow pages for the sample project.
2. Check stage status (calibration, tracking, review, downstream artifacts).
3. Identify one warning/blocker in review queue or workflow detail.
4. Resolve or route the blocker using the available action(s).
5. Confirm the project is ready for coach/player consumption.

### Success criteria

- Participant can describe current pipeline state accurately.
- Participant can perform one concrete governance/review action.
- Participant can articulate go/no-go readiness decision and reason.

### Observation checklist

- Can they differentiate warnings vs blockers?
- Do they understand artifact dependencies/freshness?
- Can they recover quickly from a failed/blocked step?
- How many context switches between pages are required?

### Questions to ask

- “How clear is the root cause of this blocker?”
- “What extra evidence do you need before marking ready?”
- “Which page felt most/least actionable?”
- “What would reduce handoff friction to coaches?”

### Expected confusion points

- Ambiguity in dependency chains (what unblocks what).
- Unclear action ownership for review queue items.
- Overlap between workflow detail and dashboard summaries.

### Pass/fail criteria

- **Critical task**: resolve or correctly route one blocker and issue readiness decision.
- **Pass**: completes all 5 tasks within 20 minutes with correct dependency reasoning.
- **Fail**: marks ready despite unresolved blocker, or cannot identify blocking artifact.

---

## 4) Technical reviewer / PM test group

### Scenario

You are reviewing product usability and release readiness. You need to verify whether the role journeys are understandable and whether the system supports a coherent demo-to-production narrative.

### Task list

1. Start at Development Dashboard and identify role entry points.
2. Follow one coach journey and one player journey end-to-end at high level.
3. Confirm that artifacts and statuses appear consistent across pages.
4. Identify one UX risk and one product gap affecting adoption.
5. Summarize release recommendation (ship, ship with caveats, or hold).

### Success criteria

- Participant can navigate cross-role flows without getting lost.
- Participant can identify consistency/inconsistency of core status signals.
- Participant produces a clear release recommendation with rationale.

### Observation checklist

- Time to locate key role routes.
- Clarity of IA labels and dashboard affordances.
- Whether page-level language matches user mental model.
- Friction points in cross-role traceability.

### Questions to ask

- “Where did the IA feel strongest/weakest?”
- “What would block stakeholder demo confidence?”
- “Which usability issue is most important before next milestone?”
- “Does the current flow support clear ownership across roles?”

### Expected confusion points

- Route naming that may be intuitive to builders but not evaluators.
- Difficulty tracing one recommendation across multiple artifacts.
- Unclear boundary between MVP-complete and backlog functionality.

### Pass/fail criteria

- **Critical task**: provide defensible ship/hold recommendation tied to observed UX evidence.
- **Pass**: completes all 5 tasks within 25 minutes and surfaces at least one high-impact risk.
- **Fail**: cannot complete cross-role walkthrough or gives unsupported recommendation.

---

## Session capture template

Use this table for each participant:

| Field | Value |
|---|---|
| Participant role |  |
| Date |  |
| Moderator |  |
| Sample project seeded? | Yes/No |
| Task completion summary |  |
| Critical task outcome | Pass/Fail |
| Top confusion points |  |
| Severity tags (Low/Med/High) |  |
| Suggested product changes |  |

## Run order recommendation

1. Technical reviewer / PM (validate framing and script quality).
2. Analyst (validate pipeline and blocker handling clarity).
3. Coach (validate decision/action value).
4. Player (validate last-mile clarity and motivation).

## Exit criteria for this test cycle

- Minimum participants: 2 per role (8 total).
- No unresolved **high-severity** issue in critical tasks.
- At least one validated improvement item captured per role.
- Findings documented and linked into the next product/review milestone notes.
