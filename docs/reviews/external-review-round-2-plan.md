# PM7 External Review Round 2 Preparation Plan (Issue #143)

## Purpose
Prepare and execute External Review Round 2 (ER2) **after PM6 confirms all P0 trust fixes are in place**. This round is focused on validating whether trust-critical interpretation issues are resolved and whether users can move through the core demo flow with less facilitator intervention.

## Scope and Constraints
- **In scope:** research planning, scripts, reviewer mix, success/failure criteria, and decision gates for ER2.
- **Out of scope:** feature implementation, UI text/code changes, or architecture changes.
- **Dependency gate:** ER2 starts only when PM6 verification of P0 trust fixes is complete.

## Round 2 Validation Objectives
ER2 should test:
1. Trust comprehension after P0 fixes.
2. Whether **Player Value** is still interpreted as an official/final grade.
3. Whether confidence meaning is understood.
4. Whether recommendation language feels advisory.
5. Whether users can complete the main demo path with less facilitator guidance.
6. Whether P1 terminology and next-action friction remain acceptable.

## Reviewer Mix
Target reviewers:
- Coach
- Player
- Analyst / video tagger
- PM / UX
- Technical/data reviewer (optional)

### Suggested recruiting target
- Minimum: 1 participant per required role (coach, player, analyst/video tagger, PM/UX).
- Preferred: 2 participants per required role for clearer pattern detection.
- Optional technical/data reviewer can be added if available, especially for edge-case interpretation checks.

## Session Structure
Each ER2 session should include:
1. **Context setup (2–3 min):** explain this is a decision-support tool and ask participant to think aloud.
2. **Main demo path task (10–15 min):** user attempts end-to-end walkthrough with minimal facilitator guidance.
3. **Comprehension probes (5–8 min):** direct interpretation questions (script below).
4. **Debrief (3–5 min):** collect perceived limitations, confidence in understanding, and trust posture.

### Facilitator behavior standard
- Start with no unsolicited clarification.
- If the participant is blocked, provide only the minimum prompt needed to continue.
- Log every facilitator intervention as a friction signal.

## Required Interview Script Questions
All sessions **must** ask the following exact questions:
1. “What does this score mean?”
2. “Is this an official grade?”
3. “What does confidence mean here?”
4. “Is this recommendation a command or suggestion?”
5. “What limitation do you remember?”

## Observation Checklist (Per Participant)
Capture:
- **Score interpretation:** participant’s own definition of Player Value.
- **Official-grade confusion:** whether they frame value as final/official evaluation.
- **Confidence interpretation:** whether confidence is read as certainty, model reliability, data quality, or something else.
- **Recommendation framing:** advisory vs directive interpretation.
- **Main-path autonomy:** completion status and number/type of facilitator interventions.
- **P1 terminology friction:** terms that still confuse users.
- **Next-action friction:** points where users hesitate on what to do next.

## Data Capture Template
For each participant, record:
- Role
- Session date
- Completed main path (Y/N)
- Number of facilitator interventions
- Response summary for each required script question
- Misinterpretation severity:
  - None
  - Mild (self-corrected)
  - Moderate (needed facilitator correction)
  - Severe (persistent misunderstanding)
- Decision-support trust posture:
  - Appropriate trust
  - Over-trust
  - Under-trust
- Notable quotes and observed friction points

## Analysis Approach
After all sessions:
1. Aggregate findings by objective (1–6 above).
2. Segment by reviewer role to detect role-specific misunderstanding.
3. Flag any recurring trust failure patterns.
4. Compare ER2 trends against PM6 expectations for P0-fix impact.

## Decision Criteria and Outcomes
At the end of ER2, choose exactly one outcome:

### 1) PROCEED_TO_BROADER_V0.1_REVIEWER_RELEASE
Use when:
- No severe recurring P0-level trust misunderstanding remains.
- Most participants correctly interpret Player Value and confidence.
- Recommendation language is mostly understood as advisory.
- Main demo path can be completed with materially reduced facilitator guidance.
- Remaining friction is primarily P1-level and acceptable for broader review.

### 2) FIX_REMAINING_P0_AND_REPEAT_ER2
Use when:
- Any recurring P0 trust misunderstanding remains (especially official-grade confusion or command-like recommendation interpretation).
- Confidence meaning is still broadly misread.
- Facilitator intervention remains high due to trust-critical ambiguity.

### 3) HOLD_FOR_PRODUCT_REWORK
Use when:
- Trust model is fundamentally misunderstood across roles.
- Users cannot complete the main path without heavy facilitation.
- P0/P1 issues combine into systemic decision-risk that invalidates broader reviewer release.

## Exit Artifact
Produce an ER2 readout containing:
- Reviewer roster by role
- Objective-by-objective findings
- Script question response patterns
- Facilitation/friction metrics
- Recommended decision outcome (one of the three above)
- Explicit rationale tied to observed evidence
