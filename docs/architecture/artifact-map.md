# Artifact Dependency Map

The Artifact Dependency Map is a read-only Local Lab status surface for stored JSON and JSONL artifacts. It answers two questions without running any rebuilds:

1. Which project, analysis, dataset/model, workflow/training/report artifacts are present?
2. Which derived artifacts are stale because a deterministic upstream dependency was updated later?

## API

`GET /api/local-lab/artifact-map` returns an `ArtifactMapResponse` with:

- `artifacts`: one `ArtifactDependency` per known artifact.
- `status_counts` and `severity_counts`: compact rollups for UI summaries.
- `stale_artifact_count` and `missing_artifact_count`: dashboard-friendly totals.
- `warnings`: human-readable rollup warnings.

The endpoint is intentionally side-effect free. It does not auto-rebuild artifacts, start background jobs, write migrations, or mutate project data.

## Artifact groups

The service tracks four groups:

| Group | Examples |
| --- | --- |
| Project-level | `project.json`, reference drafts, review queue metadata |
| Analysis | calibration, tracking, tracking review patches, cleaned tracking, projected tracks, aliases, quiz prompts and attempts, active decision rules |
| Dataset/model | dataset manifests, recognition model registry, decision events, Player Value summary, Player Value trends |
| Workflow/training/report | drill recommendations, practice plan index, practice feedback signals, coach report index, workflow JSON |

## Freshness rules

Freshness is based on persisted timestamps where available (`updated_at`, `generated_at`, `created_at`, or `last_exported_at`) and file modification time as a fallback. A derived artifact is marked `stale` when a relevant upstream artifact is newer.

Implemented deterministic checks:

- `tracking_cleaned` is stale when `tracking_review_patch` is newer.
- `projected_tracks` is stale when calibration or tracking is newer.
- `decision_events` is stale when quiz prompts, quiz attempts, or the active rule set is newer.
- `player_value_summary` is stale when decision events or player aliases are newer.
- `drill_recommendations` is stale when Player Value, diagnostics, or feedback signals are newer.
- `practice_plan` index is stale when recommendations are newer.
- `coach_report` index is stale when Player Value, trends, diagnostics, or recommendations are newer.
- A workflow is stale when any underlying project, dataset/model, training, or report artifact changed after the workflow `updated_at` timestamp.

## UI surfaces

- Local Lab shows an **Artifact Map / Freshness** section with status counts, category counts, stale artifacts, and action-level missing artifacts.
- Development Dashboard shows an **Artifact Health Summary** rollup so stale or missing artifacts are visible from the command center.

## Non-goals

- No automatic artifact rebuilds.
- No background schedulers or workers.
- No database migration.
- No graph visualization dependency.
- No artifact mutation from freshness checks.
