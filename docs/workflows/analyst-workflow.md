# Analyst Workflow

## Primary goal
Produce reliable analysis artifacts and keep downstream coaching/training workflows unblocked.

## Route path
`/development-dashboard` → `/projects/:projectId/pipeline` → `/projects/:projectId/calibration` → `/projects/:projectId/tracking` → `/projects/:projectId/tracking-review` → `/review-queue` → `/workflows`

## Inputs
- Source/video/project metadata
- Frame extraction outputs
- Calibration and tracking artifacts
- Review queue actions and workflow records

## Outputs
- Cleaned tracking/projection artifacts
- Resolved review actions
- Fresh downstream artifacts for reports/training

## If blocked
- Prefer local MP4 flow from `/`
- Use artifact freshness map in `/local-lab`
- Follow workflow detail route recovery steps
