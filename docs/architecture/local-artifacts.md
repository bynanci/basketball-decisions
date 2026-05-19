# Local Artifacts

Court IQ is local-first: most state is persisted as JSON/JSONL artifacts.

## Artifact groups

- **Project-level**: project/source/video/frame and reference metadata.
- **Analysis**: calibration, tracking, review patches, cleaned tracking, projections, quiz/rule artifacts.
- **Dataset/model**: dataset manifests, model registry, decision events, player value outputs.
- **Workflow/training/report**: workflow metadata, drills/recommendations, practice plans/executions, coach reports.

## Storage paths

- Runtime project data: `backend/data/projects/{project_id}/...`
- Shared app data and registries: `backend/app/data/...`
- Review queue and rule sets: `backend/app/data/review_queue/`, `backend/app/data/decision_rules/`
- Dataset and model metadata: `backend/app/data/datasets/`, `backend/app/data/models/`

## Freshness and rebuild references

- Freshness status and dependency checks: [artifact-map.md](./artifact-map.md)
- Storage/performance risks and mitigation priorities: [../reviews/local-artifact-storage-performance-audit.md](../reviews/local-artifact-storage-performance-audit.md)
- Guided recovery flows when artifacts are stale/missing: [../workflows/analyst-workflow.md](../workflows/analyst-workflow.md)
