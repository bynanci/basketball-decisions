# Court IQ Product Overview

Court IQ is a local-first basketball video decision intelligence workspace. It helps teams move from possession footage to explainable coaching outputs using deterministic artifacts, guided workflows, and role-specific pages.

## What Court IQ is

- A monorepo product with a FastAPI backend and Vue frontend for video-to-decision workflows.
- A local artifact system that persists project, analysis, training, and reporting state as JSON/JSONL files.
- A role-aware experience for coaches, analysts, and players that shares the same underlying artifacts.

## Target users

- **Coach**: consume report summaries, choose drills, build practice plans, and inspect execution feedback.
- **Analyst**: run and validate the pipeline, review artifacts, manage governance/rules, and keep workflows unblocked.
- **Player**: follow role-based training paths, complete quiz reps, and connect feedback to evidence.
- **Developer**: iterate on backend/frontend behavior, local artifacts, and deterministic tests.

## Core product loop

1. Start from intake (`/`) or command center (`/development-dashboard`).
2. Create/load a project and generate analysis artifacts (frames, calibration, tracking, review).
3. Produce decision-facing outputs (player value, coach reports, drills, practice plans/executions).
4. Use review/workflow pages to resolve blockers and keep artifacts fresh.
5. Feed outcomes back into next training and coaching actions.

## What Court IQ is not

- Not a hosted SaaS with multi-tenant cloud orchestration.
- Not an automatic model-training platform in this MVP scope.
- Not a copyrighted-media ingestion service; sample/demo flow is deterministic and local.
- Not a replacement for coaching judgment; it supports decision review and planning.

## Next reads

- Product IA: [information-architecture.md](./information-architecture.md)
- User journeys: [user-journeys.md](./user-journeys.md)
- Demo flow: [demo-script.md](./demo-script.md)
