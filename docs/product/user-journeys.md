# S3 Core User Journeys

This document defines the S3 core user journeys for Court IQ. It is intentionally journey-level product guidance: it maps the existing route surface into role-specific paths without adding a full onboarding wizard or removing any current routes.

## Journey principles

- Start from a clear user intent, then route to the smallest existing surface that can create or inspect the needed artifact.
- Preserve deep links for projects, quizzes, workflows, player details, practice executions, and reference videos.
- Treat `/development-dashboard` as the operational command center and `/` as intake for project/sample creation.
- Prefer recovery paths that reload persisted backend artifacts instead of relying on browser-only state.

## Coach Journey

| Field | Definition |
| --- | --- |
| user | Coach, assistant coach, player-development coach, or team staff member preparing teaching actions. |
| goal | Turn analyzed possessions into coach-readable reports, drills, practice plans, and execution feedback. |
| entry route | `/reports/coach` for existing reports; `/practice-plans` when the immediate intent is practice preparation; `/` or `/projects/:projectId` when starting from new video. |
| step sequence | 1. Open an existing coach report or create/load a project. <br> 2. Confirm the project has video, frames, calibration, tracking, and review artifacts. <br> 3. Inspect report insights and supporting evidence. <br> 4. Review recommended drills. <br> 5. Build or update a practice plan. <br> 6. Track practice execution feedback. |
| route map | `/reports/coach` → `/player-value` or `/player-value/:projectId/:playerKey` for evidence → `/drills` → `/practice-plans` → `/practice-executions` → `/practice-executions/:executionId`. If no analyzed project exists, use `/` → `/projects/:projectId` → `/projects/:projectId/pipeline`. |
| required artifacts | Project metadata, source/video metadata, extracted frames, calibration, tracking or cleaned tracking, projected tracks or cleaned projected tracks, decision events, coach report, drill recommendations, practice plan, and practice execution feedback signals. |
| expected output | A coach-facing report tied to evidence, a prioritized drill list, a practice plan, and a feedback loop for whether practice actions were executed. |
| success criteria | The coach can identify the decision theme, see the evidence trail, select drills, create a practice plan, and inspect execution feedback without needing to understand low-level pipeline details. |
| common blockers | No project exists; video has not been uploaded; frames are missing; calibration is incomplete; tracking review has not cleaned obvious false positives; report or drill artifacts are absent. |
| recovery path | Use `/` to load the sample project or create a project, then continue through `/projects/:projectId/pipeline`. Use `/projects/:projectId/tracking-review` to clean tracking artifacts. Use `/development-dashboard` to find incomplete workflow steps or next-best actions. |

## Analyst Journey

| Field | Definition |
| --- | --- |
| user | Basketball analyst, video coordinator, data analyst, or technical operator validating artifacts and decisions. |
| goal | Move a possession dataset from source intake through calibration, tracking, review, decision rules, and model/source governance so downstream outputs are trustworthy. |
| entry route | `/development-dashboard` for command-center triage; `/review-queue` for human review work; `/local-lab` for local source governance. |
| step sequence | 1. Open the Development Dashboard and inspect health, progress, and navigation groups. <br> 2. Create/load a project or open a project deep link. <br> 3. Extract frames, calibrate court keypoints, run tracking, and inspect projections. <br> 4. Resolve tracking/source items in the review queue. <br> 5. Manage reference videos, decision rules, workflows, and model registry state. <br> 6. Confirm downstream Player Value, report, or training artifacts are ready. |
| route map | `/development-dashboard` → `/` or `/projects/:projectId` → `/projects/:projectId/pipeline` → `/projects/:projectId/calibration` → `/projects/:projectId/tracking` → `/projects/:projectId/tracking-review` → `/review-queue` → `/reference-videos` → `/decision-rules` → `/model-registry` → `/workflows`. |
| required artifacts | Project bundle, source governance metadata, frame index, calibration keypoints/homography, raw tracking, tracking review patch, cleaned tracking, projected tracks, review queue items, reference videos, decision rules, workflow metadata, and registry metadata when model validation is relevant. |
| expected output | A validated project pipeline with auditable source, calibration, tracking, cleaned review outputs, decision/rule context, and workflow status. |
| success criteria | Each stage has a persisted artifact, review exceptions are explicit, route deep links reload successfully, and downstream pages can consume cleaned artifacts without silent demo substitution. |
| common blockers | Source rights are not confirmed; optional YouTube downloader is unavailable; calibration frame is not selected; homography cannot be estimated; tracking output contains non-player false positives; review queue items lack enough context. |
| recovery path | Prefer local MP4 upload when YouTube import is unavailable. Reopen `/projects/:projectId` for project hydration, `/projects/:projectId/calibration?frameIndex=<frame_index>` for saved calibration context, and `/projects/:projectId/tracking-review` to save cleaned artifacts. Use `/workflows/:workflowId` for guided recovery on a specific review action. |

## Player Journey

| Field | Definition |
| --- | --- |
| user | Player or individual learner training a role-specific read, decision habit, or game situation. |
| goal | Practice decision recognition from a selected on-court role and connect feedback to Player Value evidence or coach-assigned work. |
| entry route | `/start` to choose role and situation context; `/training` when a role profile already exists. |
| step sequence | 1. Choose user role, court role, and optional situation focus. <br> 2. Enter the training lobby for role-aware recommendations. <br> 3. Preview relevant situations. <br> 4. Play a decision quiz when a project prompt exists. <br> 5. Inspect Player Value summaries or evidence when available. <br> 6. Follow practice execution feedback if assigned. |
| route map | `/start` → `/training` → `/situations` → `/projects/:projectId/quiz/:promptId` → `/player-value` → `/player-value/:projectId/:playerKey` → `/practice-executions/:executionId`. Authors or coaches can create prompts through `/projects/:projectId/quiz-builder`. |
| required artifacts | Role profile in browser storage, situation catalog, quiz prompt and saved attempt when quiz play is used, Player Value summary/evidence when value feedback is used, and practice execution feedback when assigned. |
| expected output | A player sees recommended situations, completes or previews decision reps, understands feedback in role language, and can connect that feedback to evidence or practice actions. |
| success criteria | The selected role persists, training routes are reachable without blocking the project workflow, quiz prompts render with explanations, and player-facing evidence links back to a project/player detail when available. |
| common blockers | No role profile has been selected; no quiz prompt exists for the current project; Player Value artifacts are absent; the player opens a deep link for a project/player that has not been seeded or created locally. |
| recovery path | Return to `/start` to reset the role profile, use `/` to load the sample project for demo artifacts, open `/training` for role-aware next steps, or ask a coach/analyst to create quiz prompts through `/projects/:projectId/quiz-builder`. |

## Route mapping table

| Route | Primary journey | Journey purpose | Artifact dependency | Recovery notes |
| --- | --- | --- | --- | --- |
| `/development-dashboard` | Analyst | Command center for progress, grouped navigation, health, and next-best actions. | Project/workflow/health summaries when present. | Use when a journey is blocked and the next route is unclear. |
| `/` | Coach, Analyst | Intake for local MP4, YouTube metadata flow, and deterministic sample project. | None to start; creates project/source/video/sample artifacts. | Load the sample project when local artifacts are missing. |
| `/start` | Player | Role-based entry for product perspective, court role, and situations. | Browser role profile after save. | Clear and recreate role profile if recommendations are wrong. |
| `/training` | Player | Role-aware training lobby and next training steps. | Role profile improves recommendations; can still route onward. | Return to `/start` if role context is missing or stale. |
| `/situations` | Player | Situation preview for decision contexts. | Situation catalog and optional role profile. | Use before quiz play when no prompt has been assigned. |
| `/projects/:projectId` | Coach, Analyst | Project workspace with metadata, upload state, frames, and pipeline links. | Project bundle and optional video/frame artifacts. | Reloads from backend project bundle on direct link. |
| `/projects/:projectId/pipeline` | Analyst | Guided project pipeline from calibration into tracking/review. | Project, video, frames, calibration/tracking as available. | Use to resume incomplete project setup. |
| `/projects/:projectId/calibration` | Analyst | Manual keypoint marking and homography save. | Extracted frame and calibration keypoints. | Add `?frameIndex=<frame_index>` to recover the intended frame. |
| `/projects/:projectId/tracking` | Analyst | Run tracking and inspect image/court projections. | Calibration improves projected tracks; tracking output after run. | Re-run after calibration fixes or source/frame changes. |
| `/projects/:projectId/tracking-review` | Analyst | Manual QC for detections/tracks and cleaned outputs. | Raw tracking; optional prior review patch. | Save excluded detections/tracks to regenerate cleaned artifacts. |
| `/review-queue` | Analyst | Triage human review work and action workflows. | Review queue items and linked artifacts. | Open linked workflow or source/project route for context. |
| `/workflows` | Analyst | Operational workflow list. | Workflow metadata. | Use to continue guided recovery tasks. |
| `/workflows/:workflowId` | Analyst | Guided detail for a single workflow. | Specific workflow metadata and linked artifact. | Return to `/workflows` or dashboard if the workflow id is missing. |
| `/local-lab` | Analyst | Local source governance and lab utilities. | Source metadata. | Prefer local MP4 path when external source tooling is unavailable. |
| `/reference-videos` | Analyst | Reference clip management for review/rules/training. | Reference video metadata. | Open detail route for clip-level context. |
| `/reference-videos/:referenceId` | Analyst | Single reference video details. | Reference video id and metadata. | Return to `/reference-videos` when id is unavailable. |
| `/decision-rules` | Analyst | Decision rule set and reference-derived drafts. | Decision rule artifacts. | Use after reference review or before training/report outputs. |
| `/model-registry` | Analyst | Recognition model registry and active metadata. | Registry metadata. | Use for model/source governance checks. |
| `/reports/coach` | Coach | Coach-facing report summaries and evidence. | Coach report artifacts and linked project evidence. | Load sample data or complete analysis pipeline if empty. |
| `/drills` | Coach | Drill catalog and recommendation context. | Drill recommendations and catalog metadata. | Use after report themes are identified. |
| `/practice-plans` | Coach | Practice plan builder and plan inspection. | Drill/player/report artifacts depending on plan. | Start with drills or sample data when no plan context exists. |
| `/practice-executions` | Coach | List practice execution feedback signals. | Practice execution and feedback artifacts. | Use detail route for a specific execution. |
| `/practice-executions/:executionId` | Coach, Player | Execution feedback details. | Practice execution id and feedback signals. | Return to `/practice-executions` if the id is unavailable. |
| `/player-value` | Coach, Player | Player Value summary table. | Player Value summary/build artifacts. | Load sample project or rebuild downstream artifacts if empty. |
| `/player-value/trends` | Coach | Player Value time-series trends. | Player Value trend artifacts. | Use summary route if trend artifacts are unavailable. |
| `/player-value/:projectId/:playerKey` | Coach, Player | Player-specific evidence and component detail. | Project id, player key, Player Value evidence. | Return to `/player-value` when player alias/evidence is missing. |
| `/projects/:projectId/quiz-builder` | Coach, Analyst | Create decision quiz prompts from project/reference artifacts. | Project frames/reference context. | Complete frame extraction first if no still frame is available. |
| `/projects/:projectId/quiz/:promptId` | Player | Play a saved decision quiz prompt. | Quiz prompt and optional attempt history. | Ask coach/analyst to create a prompt if the id is unavailable. |
