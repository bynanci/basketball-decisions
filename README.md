# Court IQ

Court IQ is a local-first basketball decision intelligence workspace. It helps coaches, analysts, players, and developers move from project intake to explainable coaching/training artifacts using deterministic local data.

- Current version: **v0.1 demo/reviewer build**
- Readiness: **READY_WITH_RISKS**

## Product intro

- **Coach**: consume reports, pick drills, build plans, review practice execution.
- **Analyst**: run calibration/tracking/review pipeline and maintain artifact quality.
- **Player**: follow role-based training and decision quiz reps.
- **Developer**: iterate on Vue + FastAPI workflows and deterministic tests.

Start at **Development Dashboard** (`/development-dashboard`) for command-center navigation, or **Home** (`/`) for project/sample intake.

## Quick start

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## Sample project

Court IQ ships with a deterministic local sample project for demos and smoke tests.

```bash
curl http://localhost:8000/api/sample-data/status
curl -X POST http://localhost:8000/api/sample-data/seed
curl -X DELETE http://localhost:8000/api/sample-data
```

Recommended demo walkthrough: [docs/product/demo-script.md](docs/product/demo-script.md).

## Demo walkthrough

- v0.1 readiness: **READY_WITH_RISKS**
- v0.1 release notes: [docs/product/v0.1-release-notes.md](docs/product/v0.1-release-notes.md)
- v0.1 demo checklist: [docs/product/v0.1-demo-checklist.md](docs/product/v0.1-demo-checklist.md)
- v0.1 readiness audit: [docs/reviews/v0.1-readiness-audit.md](docs/reviews/v0.1-readiness-audit.md)
- v0.1 release checklist: [docs/product/v0.1-release-checklist.md](docs/product/v0.1-release-checklist.md)
- Repeatable 10-minute script: [docs/product/demo-script.md](docs/product/demo-script.md)

## Main workflows

- Coach workflow: [docs/workflows/coach-workflow.md](docs/workflows/coach-workflow.md)
- Analyst workflow: [docs/workflows/analyst-workflow.md](docs/workflows/analyst-workflow.md)
- Player workflow: [docs/workflows/player-workflow.md](docs/workflows/player-workflow.md)

## Development commands

From repo root:

```bash
npm test
npm run build
npm run test:e2e
```

## Documentation map

### Product

- Overview: [docs/product/overview.md](docs/product/overview.md)
- User journeys: [docs/product/user-journeys.md](docs/product/user-journeys.md)
- Demo script: [docs/product/demo-script.md](docs/product/demo-script.md)
- Information architecture: [docs/product/information-architecture.md](docs/product/information-architecture.md)
- Terminology reference: [docs/product/terminology.md](docs/product/terminology.md)
- Drill template standard: [docs/product/drill-template-standard.md](docs/product/drill-template-standard.md)
- Future backlog triage: [docs/product/future-backlog-triage.md](docs/product/future-backlog-triage.md)
- Product positioning review: [docs/product/product-positioning-review.md](docs/product/product-positioning-review.md)
- Usability test plan: [docs/product/usability-test-plan.md](docs/product/usability-test-plan.md)
- v0.1 release notes: [docs/product/v0.1-release-notes.md](docs/product/v0.1-release-notes.md)
- v0.1 demo checklist: [docs/product/v0.1-demo-checklist.md](docs/product/v0.1-demo-checklist.md)
- v0.1 reviewer feedback template: [docs/product/v0.1-reviewer-feedback-template.md](docs/product/v0.1-reviewer-feedback-template.md)
- v0.1 release readiness checklist: [docs/product/v0.1-release-readiness-checklist.md](docs/product/v0.1-release-readiness-checklist.md)

### Architecture

- Artifact map and freshness rules: [docs/architecture/artifact-map.md](docs/architecture/artifact-map.md)
- Backend services: [docs/architecture/backend-services.md](docs/architecture/backend-services.md)
- Frontend routes: [docs/architecture/frontend-routes.md](docs/architecture/frontend-routes.md)
- Local artifacts: [docs/architecture/local-artifacts.md](docs/architecture/local-artifacts.md)
- AI intervention policy: [docs/architecture/ai-intervention-policy.md](docs/architecture/ai-intervention-policy.md)

### Reviews

- Storage/performance audit: [docs/reviews/local-artifact-storage-performance-audit.md](docs/reviews/local-artifact-storage-performance-audit.md)
- Guided workflow usability review: [docs/reviews/m27-guided-workflow-usability-review.md](docs/reviews/m27-guided-workflow-usability-review.md)


## Manual release tagging

If GitHub release tagging is not automated, run:

```bash
git tag v0.1.0
git push origin v0.1.0
```
