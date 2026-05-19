# Frontend Routes Map

High-level route mapping for onboarding by intent.

| Route | Page/component | User journey | Purpose |
| --- | --- | --- | --- |
| `/development-dashboard` | `DevelopmentDashboardPage.vue` | Analyst, Developer | Command center: health, progress, grouped navigation |
| `/` | `HomePage.vue` | Coach, Analyst | Intake: create project, upload sources, load sample project |
| `/projects/:projectId` | `ProjectPage.vue` | Coach, Analyst | Project workspace and artifact checkpoint |
| `/projects/:projectId/pipeline` | `PipelinePage.vue` | Analyst | Guided analysis sequence |
| `/projects/:projectId/calibration` | `CalibrationPage.vue` | Analyst | Manual keypoint calibration/homography |
| `/projects/:projectId/tracking` | `TrackingPage.vue` | Analyst | Run tracking and inspect projections |
| `/projects/:projectId/tracking-review` | `TrackingReviewPage.vue` | Analyst | Manual QC and cleaned tracking |
| `/review-queue` | `ReviewQueuePage.vue` | Analyst | Triage review actions and batch operations |
| `/workflows` | `WorkflowsPage.vue` | Analyst | Guided recovery/operations workflows |
| `/reports/coach` | `CoachReportsPage.vue` | Coach | Coach summary outputs and evidence links |
| `/drills` | `DrillsPage.vue` | Coach | Drill catalog and recommendation context |
| `/practice-plans` | `PracticePlansPage.vue` | Coach | Practice planning |
| `/practice-executions` | `PracticeExecutionsPage.vue` | Coach, Player | Execution feedback loop |
| `/player-value` | `PlayerValuePage.vue` | Coach, Player | Player value summary |
| `/player-value/trends` | `PlayerValueTrendsPage.vue` | Coach, Analyst | Player value trends |
| `/start` + `/training` | `RoleEntryPage.vue`, `TrainingLobbyPage.vue` | Player | Role-based onboarding and training |

For full inventory with dynamic detail routes, see [../product/information-architecture.md](../product/information-architecture.md).
