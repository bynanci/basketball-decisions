# Future Feature Backlog Triage

## 1. Current Product Position

Court IQ has reached a broad, end-to-end product loop that supports core basketball decision workflows:

analysis → player value → evidence → report → drills → practice plan → execution → feedback → dashboard → workflows.

The product now has enough breadth to demonstrate value across coach, analyst, and player contexts. The immediate strategy is to **pause net-new feature expansion** and prioritize product clarity, trust, and repeatability.

## 2. Stabilization Completed

Stabilization work already in motion/complete that supports this pause:

- Deterministic local-first architecture for repeatable development and demos.
- Broad API and workflow coverage across the current loop.
- Sample data support for consistent onboarding and scenario walkthroughs.
- Product documentation for journeys, IA direction, and demo script.

These foundations justify shifting roadmap decisions from "what can we add" to "what should we sequence next."

## 3. Now

Focus: reliability, usability, and demo confidence for the existing loop.

- **Stabilization** (finish remaining hardening tasks)
- **Sample data** improvements and consistency checks
- **E2E tests** for critical coach/analyst/player flows
- **IA cleanup** to reduce navigation friction
- **Reliability hardening** for key endpoints and artifact flows
- **Demo readiness** and script alignment

Rationale: these items directly reduce user confusion, improve trust, and strengthen demoability without expanding scope.

## 4. Next

Focus: high-impact quality upgrades that sit directly on top of current workflows.

- **PDF / printable report**
  - Rationale: improves shareability and coach adoption with low conceptual risk.
- **Video evidence preview**
  - Rationale: strengthens trust in recommendations by exposing visual proof in-context.
- **Better review queue bulk tools**
  - Rationale: reduces analyst effort and improves throughput on existing data curation flow.
- **Coach-facing report polish**
  - Rationale: improves readability and decision speed for the primary consumer.
- **Player dashboard polish**
  - Rationale: improves follow-through and clarity on drills/plan execution.

## 5. Later

Focus: operational scale features that are valuable but not needed before core-loop maturity.

- **Roster management**
  - Rationale: useful for team operations, but not required to validate core decision intelligence loop.
- **Calendar integration**
  - Rationale: enables planning convenience but introduces external dependency and sync complexity.
- **Team season planning**
  - Rationale: meaningful for long-horizon usage, but should come after tighter daily/weekly workflow adoption.
- **Cloud sync**
  - Rationale: expands deployment flexibility, but increases infra/security burden ahead of current priorities.
- **Multi-user collaboration**
  - Rationale: important for team environments, yet adds permissions/state complexity before single-workspace reliability is fully maximized.

## 6. Not Now

Focus: explicitly de-scoped items with high complexity, high claim risk, or weak near-term fit.

- **Automatic jersey OCR**
  - Rationale: high model/error handling burden for limited near-term loop impact.
- **Official scouting grade**
  - Rationale: risks overclaiming objectivity and requires governance/standardization not yet in place.
- **Deep model training**
  - Rationale: heavy ML investment and data requirements before core workflow polish is complete.
- **Live video analytics**
  - Rationale: substantial real-time systems complexity and latency constraints beyond current scope.
- **Cloud ML platform**
  - Rationale: major infrastructure expansion with high cost and operations overhead.
- **Medical / injury recommendations**
  - Rationale: high-stakes domain risk and compliance burden; outside current product promise.

## 7. Decision Criteria

Use these criteria when evaluating any future item:

- Does it reduce user confusion?
- Does it improve trust?
- Does it improve demoability?
- Does it strengthen the core loop?
- Does it require heavy external dependency?
- Does it risk overclaiming?

Scoring guidance:

- Prioritize items with strong positive impact on confusion/trust/demoability/core loop.
- Deprioritize items with heavy external dependencies unless they unlock core-loop reliability.
- Reject or park items that materially increase overclaiming risk.

## 8. Recommended Next Milestone

**Milestone: Core Loop Reliability + Evidence Presentation (Next 1 cycle)**

Proposed scope:

1. Complete remaining stabilization and reliability hardening.
2. Expand critical-path E2E coverage with deterministic sample data scenarios.
3. Deliver coach-consumable report improvements:
   - printable/PDF output,
   - evidence preview in report/review surfaces,
   - report/dashboard readability polish.

Expected outcome:

A more trustworthy, demo-ready Court IQ experience that strengthens adoption of the existing product loop before any platform expansion.
