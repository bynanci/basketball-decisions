# Backend Services

This page summarizes the main backend service modules and how they map to API behavior.

| Service/module | Responsibility | Key artifacts | Related routes |
| --- | --- | --- | --- |
| `sample_data_service.py` | Seed/remove deterministic sample project and dependent artifacts. | Project seed bundle, sample metadata | `/api/sample-data/*` |
| `artifact_map_service.py` | Build read-only artifact dependency/freshness map. | Artifact map response, freshness rollups | `/api/local-lab/artifact-map` |
| `workflow_orchestrator_service.py` | Build/track guided workflow records and status. | Workflow JSON metadata | `/api/workflows*` |
| `coach_report_service.py` | Build/read coach report summaries and evidence links. | Coach report index/output artifacts | `/api/reports/coach*` |
| `player_home_service.py` | Aggregate player-facing home summary data. | Player home summary artifacts | `/api/player-home*` |
| `practice_plan_service.py` | Create/read practice plans from recommendation context. | Practice plan index/items | `/api/practice-plans*` |
| `practice_execution_service.py` | Persist and inspect execution feedback state. | Practice execution + signals | `/api/practice-executions*` |
| `drill_recommendation_service.py` | Generate/read drill recommendation outputs. | Drill recommendation artifacts | `/api/drills/recommendations*` |
| `decision_engine.py` / `decision_diagnostics.py` | Derive decision events and diagnostics context. | Decision events, diagnostics artifacts | `/api/decision-*`, diagnostics endpoints |
| `dataset_health.py` / `recognition_training.py` | Dataset/manifests and recognition training/registry support. | Dataset manifests, model registry | dataset/model endpoints |
| `development_dashboard_service.py` | Aggregate dashboard health, progress, and actions. | Dashboard summary payloads | `/api/development-dashboard*` |

## Notes

- Services persist mostly to local JSON/JSONL artifacts under backend data directories.
- Routes live under `backend/app/api/` and call these services for domain logic.
- For artifact freshness dependencies, see [artifact-map.md](./artifact-map.md).
