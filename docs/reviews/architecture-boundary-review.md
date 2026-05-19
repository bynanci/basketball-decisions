# R4 Architecture Boundary & Service Responsibility Review

## Scope and constraints

This review checks boundary clarity across backend API/service/model layers and frontend route/page/client layers after recent milestones. It identifies coupling and refactor candidates only; **no broad refactor is implemented in this issue**.

---

## 1) Backend `app/api` responsibilities

### Expected boundary
- `app/api/*` should focus on HTTP concerns: request parsing, response shaping, status codes, and delegation.
- Domain rules and artifact orchestration should stay in `app/services/*`.

### Current observations
- The route aggregation and global error envelope in `app/main.py` are consistent and centralized, which is healthy for API boundary consistency.
- `app/api/common.py` contains shared path/error helpers (`require_project_dir`, `api_error`, `assert_path_child`) and basic JSON read/write helpers used by API modules and services.

### Boundary risk
- `common.py` combines API error semantics and low-level artifact I/O helpers, which creates a mixed concern layer (transport + persistence utility).

---

## 2) Backend `app/services` responsibilities

### Service responsibility table

| Service | Primary responsibility | Boundary quality | Notes |
| --- | --- | --- | --- |
| `sample_data_service.py` | Seed/remove deterministic sample project artifacts | Clear | Mostly orchestration over multiple artifact groups. |
| `artifact_map_service.py` | Read-only freshness/dependency map generation | Clear | Good domain-specific read model. |
| `workflow_orchestrator_service.py` | Workflow creation/state progression | Medium | Touches multiple domains; risk of becoming god-service. |
| `coach_report_service.py` | Coach summary build/read and evidence links | Medium | Aggregates Player Value + diagnostics + recommendations. |
| `player_home_service.py` | Player-facing home aggregation | Medium | Cross-cuts drill/recommendation/execution artifacts. |
| `practice_plan_service.py` | Plan creation/read over recommendation context | Clear | Reasonably bounded training-planning concern. |
| `practice_execution_service.py` | Execution feedback and signal persistence | Clear | Owns training execution lifecycle artifacts. |
| `drill_recommendation_service.py` | Recommendation generation/read | Medium | Depends on Player Value and diagnostics signals. |
| `decision_engine.py` + `decision_diagnostics.py` | Decision event derivation + diagnostics | Medium | Split is good, but shared artifact contracts are implicit. |
| `dataset_health.py` + `recognition_training.py` | Dataset manifest quality + model registry updates | Medium | Dataset and model lifecycle concerns partially overlap. |
| `development_dashboard_service.py` | Health/progress/action command-center aggregates | Medium | Aggregator role is useful but naturally coupling-prone. |
| `player_value_trends.py` | Player-value trend calculations | Clear | Narrow analytical scope. |
| `practice_feedback_signal_service.py` | Practice signal derivation/read | Clear | Focused service with clear artifact ownership. |
| `recognition_training.py` | Training/registry management | Medium | Registry + training metadata lifecycle intertwined. |

---

## 3) Backend `app/models` consistency

### Positive patterns
- A broad set of explicit model modules exists (`project.py`, `video.py`, `workflow.py`, `reference_video.py`, etc.), indicating intent to keep schema contracts typed.
- Naming is mostly domain-oriented and understandable.

### Inconsistencies / risks
- Local artifact JSON contracts likely evolve faster than model modules, which risks schema drift unless every read/write path instantiates typed models consistently.
- Some cross-domain aggregates (dashboard/player-home/report outputs) are likely represented as ad-hoc dict payloads rather than explicit aggregate models.

---

## 4) Local artifact ownership

### Current pattern
- Project-specific artifacts under `backend/data/projects/{project_id}/...`.
- Shared/global registries under `backend/app/data/...` (rules, review queue, dataset manifests, model registry, reference artifacts).

### Ownership issues
- Ownership boundaries between project-scoped and global-scoped artifacts are clear at path level, but business ownership is less explicit for shared artifacts that influence project outcomes (for example, active rule sets and reference-derived drafts).
- Cross-service writes to shared global artifacts can increase accidental coupling and race-risk if write conventions are not centralized.

---

## 5) Duplicated file read/write logic

### Duplicated patterns likely present
- Repeated `Path` existence checks and `json.loads`/`write_text` flows across services.
- Repeated timestamp update patterns for artifact mutation.
- Repeated not-found / stale-artifact response assembly patterns.

### Why it matters
- Duplication makes migrations, validation hardening, and atomic-write improvements expensive and inconsistent.

---

## 6) Frontend page responsibilities

### Current pattern
- Router and navigation definitions are comprehensive, but many top-level pages appear to serve as both container orchestration and UI rendering hubs.

### Boundary risk
- Page components can become overloaded with: data fetching, error-state branching, workflow state transitions, and rendering.
- Absence of module-level feature folders (by bounded context) may increase cross-page coupling over time.

---

## 7) API client type growth

### Current pattern
- `frontend/src/api/client.ts` includes error classes, request/response types, many domain interfaces, and endpoint functions in one large module.

### Boundary risk
- Type surface growth in a single file increases merge conflicts and weakens discoverability.
- Shared interfaces for unrelated domains can cause accidental import coupling and increase rebuild/test blast radius.

---

## 8) Navigation structure

### Current pattern
- Route declarations (`router/index.ts`) and product navigation metadata (`navigation.ts`) are both maintained and reasonably intentional.

### Coupling risk
- Route metadata duplication (path/name/descriptions in two places) introduces drift risk.
- Detail-route handling in `navigation.ts` and explicit route definitions in router can diverge without a shared source of truth.

---

## 9) Test coverage by module

### Backend
- Strong route-level API coverage exists for many modules (decision rules, dashboard, player home, practice plans/executions, quiz, reference videos, reports, review queue, sample data, tracking, videos, workflows).
- Gaps appear for direct API tests in: calibration, drills, local lab, projects, sources.

### Frontend
- Focused tests exist for key pages/workflows (development dashboard, player home, review queue actions, workflows, source governance, reliability states).
- Coverage appears thinner for many route pages (training, practice planning detail flows, model registry deep behavior, several project subpages).

---

## Areas of coupling

1. **Dashboard/report/player-home aggregators depend on many service outputs**, creating fan-in hotspots and broad change impact.
2. **Global artifact registries** (rules/review queue/model registry/reference metadata) influence multiple user flows and services.
3. **Router + navigation dual declarations** create a frontend coupling seam with drift potential.
4. **Single-file API client type expansion** couples unrelated features at compile/import level.

---

## Suggested refactors (ranked)

### P0 (high priority, low-medium risk)
1. **Extract a shared artifact repository utility layer** (`read_json`, `write_json`, safe-write, timestamp normalization) and migrate services incrementally.
2. **Split `frontend/src/api/client.ts` by bounded domains** (projects, tracking, training, reports, governance) with a thin shared HTTP core.
3. **Define route metadata source-of-truth strategy** (generate nav from router meta, or router from typed nav schema).

### P1 (medium priority)
1. **Introduce explicit aggregate models** for dashboard/player-home/report payloads to reduce ad-hoc dict contracts.
2. **Create service boundary docs per aggregate service** (inputs/outputs/dependencies) to prevent expansion into god-service patterns.
3. **Add missing route API tests** for calibration/drills/local-lab/projects/sources.

### P2 (lower priority / larger change)
1. **Reorganize frontend by feature modules** (feature folder boundaries for pages + composables + API adapters).
2. **Introduce domain event or job abstraction** for cross-service derived artifact recomputation.
3. **Separate global governance artifacts into clearer ownership modules** (rules vs source-governance vs model-registry lifecycle).

---

## Duplicated logic summary

- JSON file read/write helpers repeated outside shared boundary.
- Similar error payload patterns repeated across endpoint handlers.
- Route metadata duplicated across router and navigation map.
- API type declarations centralized and repeated in a monolithic client module.

---

## Do-not-refactor-yet list

1. **Do not replace local artifact JSON storage with a database in this phase.**
2. **Do not collapse all aggregator services into one orchestrator.**
3. **Do not redesign all frontend routes/pages before extracting API/type boundaries first.**
4. **Do not introduce async worker infrastructure solely for architectural purity without concrete throughput pain.**
5. **Do not bulk-rename artifact files/paths until repository abstraction and tests are in place.**

---

## Recommended sequencing

1. P0-1 repository utility extraction (backend).
2. P0-2 API client/domain type split (frontend).
3. P0-3 router/navigation source-of-truth alignment.
4. P1 typed aggregate contracts + missing API tests.
5. Re-evaluate P2 items after blast-radius reduction from P0/P1.

