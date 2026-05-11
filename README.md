# Basketball Decisions

A minimal runnable monorepo for basketball-video decision experiments. The repo has a Vite + Vue 3 + TypeScript frontend and a FastAPI backend with local JSON storage for projects, uploads, extracted frames, manual calibration, tracking, and projected 2D court paths.

## Repository-level npm scripts

For convenience, root-level npm scripts delegate to the frontend package:

```bash
npm test
npm run build
```

Use `cd frontend && npm install` first when frontend dependencies have not been installed yet.

## Repository layout

```text
frontend/                 # Vite + Vue 3 + TypeScript app
  src/pages/              # Home, project, calibration, tracking pages
  src/components/         # Video, calibration, tracking, and court components
backend/                  # FastAPI app
  app/api/                # Projects, videos, frames, calibration, tracking routers
  app/pipeline/           # OpenCV frame extraction, homography, detector/tracker/projector building blocks
  data/                   # Local project/upload/frame/result storage
```

## 1. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

## 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## Current MVP flow

The frontend now supports the real local MP4 path through the backend APIs and can hydrate project pages from backend local JSON storage after a browser refresh or direct link:

1. Create a backend project.
2. Upload an MP4.
3. Extract frames with the OpenCV-backed frame extractor.
4. Choose an extracted frame for calibration.
5. Mark 4+ manual court keypoints in real image pixel coordinates.
6. Save calibration so the backend computes a `cv2.findHomography` homography.
7. Run backend tracking.
8. Open Tracking Quality Review to exclude false-positive detections or full tracks before using projected paths.
9. View detection / track / projected-track counts and projected 2D court paths returned by the backend. The UI does not substitute demo tracks when backend results are absent.
10. Refresh or open deep links for the project, calibration frame, tracking page, or tracking review page; the frontend reloads available artifacts from backend storage.

Decision Arrow Quiz is available as a small still-frame MVP: build one prompt from an extracted frame, draw decision arrows, save the prompt, and play it back with explanations.

## Refresh-safe hydration and deep links

Project pages are designed to recover from backend storage instead of depending only on in-memory Pinia state. On mount, the project, calibration, and tracking routes call:

```http
GET /api/projects/{project_id}/bundle
```

The bundle returns `project.json` plus any optional artifacts that exist locally: `video.json`, `frames/index.json`, `calibration.json`, `tracking.json`, and `projected_tracks.json`. Missing optional artifacts are returned as `null`, so a partially completed MVP pipeline can still load without crashing. A missing `project.json` returns the typed `PROJECT_NOT_FOUND` API error. If an optional artifact exists but is malformed or does not match its expected schema, hydration stops with a typed 422 response that includes a `debug_hint` naming the artifact to fix or regenerate.

Supported refresh/deep-link recovery paths include:

- `/projects/:projectId` for project metadata, video metadata, frame counts, calibration status, tracking status, and projected-track status.
- `/projects/:projectId/calibration?frameIndex=<frame_index>` for opening a saved extracted frame directly and recovering saved calibration keypoints/homography. If the query parameter is omitted after a calibration has been saved, the page restores the calibration frame from the persisted `frame_id`.
- `/projects/:projectId/tracking` for recovering saved detections, tracks, and projected tracks when tracking has already run.
- `/projects/:projectId/tracking-review` for loading raw tracking plus any saved manual review patch and cleaned tracking artifacts.

The backend video `uri` is metadata only for hydration. The browser preview still uses a session-local object URL after upload; the frontend intentionally does **not** treat backend file paths as browser-playable video URLs until a proper streaming endpoint is added.

Recommended MVP Demo Path:

1. Create project.
2. Upload MP4.
3. Extract frames.
4. Refresh page to verify hydration.
5. Open Pipeline Page.
6. Select calibration frame.
7. Mark 4+ keypoints.
8. Save calibration.
9. Run tracking.
10. Open Tracking Review and save any false-positive exclusions.
11. View 2D court projection.

For coordinate conventions used by calibration, quiz arrows, homography projection, and court rendering, see [Coordinate System Guide](docs/coordinate-system.md).

## 3. Upload a local MP4

From the UI:

1. Open the home page.
2. In **Local MP4**, enter a project name.
3. Choose an `.mp4` file.
4. Click **Create upload project**.

The frontend creates the project with `POST /api/projects`, uploads the MP4 with `POST /api/projects/{project_id}/video/upload`, stores the returned backend `project_id` and `VideoAsset` in Pinia, and keeps a browser object URL only for local preview.

Backend API example:

```bash
PROJECT_ID="<project id returned by POST /api/projects>"
curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/video/upload" \
  -F "file=@/absolute/path/to/video.mp4"
```

Uploaded files are stored under `backend/data/projects/{project_id}/videos/`. This directory is intended for local development data and is ignored by git except for `.gitkeep` files.

## 4. Extract frames

From the project page, click **Extract Frames** after a video asset exists. The frontend calls:

```http
POST /api/projects/{project_id}/frames/extract
```

with `target_fps: 1` and `max_frames: 120`, then renders a thumbnail strip from the returned frame index. Each thumbnail links to calibration with `?frameIndex=<frame_index>`.

The frame extractor is OpenCV-backed (`cv2.VideoCapture` plus sampled image writes), not a placeholder folder creator.

## 5. Create a project from a YouTube URL

YouTube source processing is only for videos you have the rights or permission to process. For MVP demos, prefer the local MP4 upload flow because it avoids optional downloader setup and third-party source availability issues.

From the UI:

1. Open the home page.
2. In **YouTube URL**, paste a YouTube watch URL.
3. Check **I confirm I have the rights or permission to process this video.**
4. Click **Create YouTube project**.

The frontend creates a backend project first, then calls `POST /api/projects/{project_id}/video/youtube` with `rights_confirmed: true`. If the optional downloader dependency such as `yt-dlp` is not installed, the endpoint returns `501 Not Implemented`; the UI displays a clear message telling the user to use local MP4 upload for the MVP flow.

Backend API example:

```bash
PROJECT_ID="<project id returned by POST /api/projects>"
curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/video/youtube" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","rights_confirmed":true}'
```

## 6. Manually mark court keypoints

1. Create a project and upload an MP4.
2. Extract frames on the project page.
3. Click **Use for calibration** on a frame thumbnail.
4. Mark at least 4 known court keypoints.
5. Click **Save backend calibration**.

Calibration clicks are saved in real image pixel coordinates, while court points remain in court feet on a 94 × 50 ft court. When `homography` is omitted, the backend estimates it with `cv2.findHomography` and returns the calibration plus reprojection error when available.

## 7. Run tracking and view projected court paths

From the UI:

1. Open the tracking page for a project after extracting frames and saving calibration.
2. Click **Run Tracking**.
3. Review backend detection count, track count, projected track count, detector mode, the frame overlay, and the 2D court projection. Before tracking runs, the page shows zero backend results and an explicit empty-state message rather than demo tracks.

The tracking endpoint currently uses deterministic MVP detector/tracker logic, then projects image-space track points through the saved homography when calibration exists. The 2D court view renders backend `court_x` / `court_y` values as court feet in a `0 0 94 50` SVG viewBox.

Backend API example:

```bash
curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/tracking/run" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"'"${PROJECT_ID}"'","confidence_threshold":0.25,"iou_threshold":0.3,"max_players":10}'

curl "http://localhost:8000/api/projects/${PROJECT_ID}/tracks"
```


## 8. Review tracking quality and save cleaned tracks

Tracking Quality Review is a manual QC MVP for removing obvious false positives before relying on 2D court paths. Open `/projects/:projectId/tracking-review` after tracking has run. The review page shows raw detections over the selected frame, labels each bbox with its `track_id`, lists all tracks with point counts, and lets you:

- exclude a single bad detection by `detection_id`;
- exclude an entire false-positive track by `track_id`;
- add optional reviewer notes;
- save the review patch without overwriting `tracking.json`.

Backend artifacts written by `POST /api/projects/{project_id}/tracking/review`:

- `backend/data/projects/{project_id}/tracking_review_patch.json` for the manual patch;
- `backend/data/projects/{project_id}/tracking_cleaned.json` for cleaned image-space detections/tracks;
- `backend/data/projects/{project_id}/projected_tracks_cleaned.json` for cleaned projected court paths.

Raw and cleaned outputs are intentionally separate. Use raw tracking for audit/debug comparisons, and use cleaned tracking/projection when downstream analysis should ignore referees, coaches, bench players, or spectators.

Backend API example:

```bash
curl "http://localhost:8000/api/projects/${PROJECT_ID}/tracking/review"

curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/tracking/review" \
  -H "Content-Type: application/json" \
  -d '{"excluded_detection_ids":[],"excluded_track_ids":["track-2"],"notes":"false-positive coach near sideline"}'
```

Tracking QC limitations:

- Manual QC only; there is no automatic team classification, jersey recognition, referee detection, or advanced re-identification.
- The UI does not decide whether a detection is a player; reviewers must inspect bboxes and tracks.
- Track aliases are supported by the backend patch schema, but this MVP does not provide an advanced merge/re-id workflow in the UI.
- Cleaned projected tracks are only as accurate as the original detections/tracks and saved calibration homography.

## Decision Arrow Quiz MVP

Decision Arrow Quiz is a small still-image MVP for authoring and playing one decision prompt at a time. It uses extracted frame images rather than video playback.

Builder flow:

1. Open a project that has extracted frames.
2. Click **Build Quiz** on a frame card.
3. Draw 2–5 arrows on the frame; arrow start/end coordinates are stored as normalized `0..1` image coordinates.
4. Label each arrow, choose an action type (`PASS`, `DRIVE`, `SHOT`, `RESET`, or `HOLD`), optionally enter a manual `expected_value`, and write an option explanation.
5. Mark exactly one option as correct.
6. Add the question and summary explanation, then save the prompt.

Player flow:

1. Open a saved prompt from **Existing Quiz Prompts** on the project page.
2. Click one arrow on the freeze frame.
3. Review the selected option, correct option, score, scoring mode, optional expected-value opportunity cost, option explanations, and summary explanation.

Attempt scoring:

- Manual expected values are coach/analyst-entered estimates saved on quiz options. They are not model-generated.
- When all options have manual `expected_value`, attempts use expected-value scoring: `opportunity_cost = max(0, best_expected_value - selected_expected_value)` and `score = max(0, round(100 - opportunity_cost * 200))`.
- When expected values are missing, attempts fall back to correctness-only scoring: score is `100` for the correct option and `0` for an incorrect option, with `opportunity_cost` set to `null`.
- A learned EPV model is future work; no EPV model is implemented in this MVP.

Quiz prompts are stored locally under `backend/data/projects/{project_id}/quiz_prompts.json`; attempts are appended to `backend/data/projects/{project_id}/quiz_attempts.json`. This is local development JSON storage, not a production quiz database.

Limitations intentionally kept out of scope for this MVP:

- Still image only; no video freeze playback yet.
- No EPV model; `expected_value` is manually entered and optional, even though recommended for richer scoring.
- No multi-question sessions.
- No user accounts or respondent identity.
- No coach annotation workflow.

## Training Lobby

The dynamic training lobby is available at `/training` after a user chooses a role profile from `/start`. If no role profile exists, the page shows **Choose your role first** and links back to `/start`.

When a profile is present, the lobby shows the current `UserRole / CourtRole`, lists selected situations, and lets the user choose a project as the prompt source. After a project is selected, the frontend loads that project's quiz prompts with `apiClient.listQuizPrompts(projectId)` and filters recommendations client-side:

- `prompt.court_role_target` must match the selected `courtRole`;
- if selected situations exist, `prompt.situation_type` must be included in the selected `situationTypes`;
- if a prompt declares `user_role_targets`, the selected `userRole` must be included.

The lobby displays two prompt sections: **Recommended for your role** and **All prompts in this project**. Prompt cards show the question, court role, situation type, frame index, option count, and a **Play** button that opens the existing quiz player route at `/projects/:projectId/quiz/:promptId`. If a project has prompts but none match the selected role and situations, the lobby shows a clear empty state such as `No prompts match BALL_HANDLER / PICK_AND_ROLL yet. Build one from an extracted frame.`

Home links to `/training` whenever a role profile exists, and the `/start` continue button now sends users directly into training mode after saving their profile.

## Current limitations / TODO functionality

The following pieces are intentionally minimal:

- **Frontend API integration**: project creation, MP4 upload, YouTube metadata creation, frame extraction, calibration saving, tracking, projected tracks, and route-level hydration are wired for the MVP flow.
- **Video playback source handling**: uploaded videos are previewed with a browser object URL for the current session; backend video file URIs are metadata only unless a streaming endpoint is added.
- **YouTube downloader**: optional `yt-dlp` support may be unavailable in local environments.
- **Detection/tracking models**: `detector.py` and `tracker.py` remain deterministic MVP implementations, not production player models.
- **Tracking QC**: cleanup is reviewer-driven only and does not classify teams, read jerseys, detect referees automatically, or perform advanced re-identification.
- **Persistence model**: project JSON files are local dev storage, not a production database.
- **Decision Quiz**: the MVP is limited to one still-frame arrow prompt at a time; no accounts, sessions, video playback freeze, or learned EPV model are included.

## Role-Based Entry Flow

Court IQ now includes an optional frontend-first role entry flow at `/start`. It does not require authentication and does not block the existing project creation, upload, calibration, tracking, projection, or decision-prompt workflow.

The selected role profile is stored in Pinia and persisted to browser `localStorage` under the `court-iq-role-profile` key so the Home page can restore the current mode after a refresh.

The profile has three parts:

- `UserRole` controls the product perspective and copy shown to the user. Supported values are `COACH`, `PLAYER`, `ANALYST`, and `FAN`.
- `CourtRole` controls the on-court lens for future court situation filtering. Supported values include ball-handler, shooter, roller, screener, defender, low-man, trailer, and weak-side wing roles.
- `SituationType` controls the training or analysis context the user wants to focus on, such as pick-and-roll, short-roll, spot-up, closeout attack, transition advantage, late-clock, post-double, drive-and-kick, help-rotation, low-man decisions, and off-ball relocation.

For now, Home shows the selected mode, links back to the role entry page, links down to the existing project creation flow, and displays a static recommended situations list. EPV and deeper role-based filtering are intentionally not implemented yet.

## Local Data Memory Layer

The Local Lab data memory layer prepares project artifacts for future local ML training without adding a database, cloud service, YOLO training job, or Player Value scoring. The frontend page is available at `/local-lab`, and the backend API is mounted under `/api/local-lab`.

Local dataset files are JSON/JSONL only and are written under `backend/app/data/datasets/` with one folder per future training domain:

- `recognition/` for tracking QC-derived detection and track labels.
- `decision/` for quiz prompt samples and quiz attempt labels.
- `player_value/` as a reserved local dataset registry folder for future Player Value work.

Each dataset folder owns the same three local files:

- `dataset_manifest.json` summarizes sample count, label count, project count, last export time, and storage paths.
- `samples.jsonl` stores exported training examples.
- `labels.jsonl` stores exported labels or attempt outcomes.

Repeated inputs become local artifacts first: uploaded video metadata, extracted frame indexes, calibration, tracking output, tracking review patches, cleaned tracking/projection files, quiz prompts, and quiz attempts remain in `backend/data/projects/{project_id}/`. The Local Lab project index (`GET /api/local-lab/projects`) scans those artifacts and reports availability flags plus frame, prompt, and attempt counts for every project.

Recognition export (`POST /api/local-lab/datasets/recognition/export`) reads each project's `tracking.json` and `tracking_review_patch.json`. Review `excluded_detection_ids` become `DetectionTrainingLabel` rows with `FALSE_POSITIVE`; review `excluded_track_ids` become `TrackTrainingLabel` rows with `FALSE_POSITIVE_TRACK`; non-excluded tracks become heuristic `VALID_PLAYER_TRACK` labels. The exporter writes `recognition/samples.jsonl`, `recognition/labels.jsonl`, and `recognition/dataset_manifest.json`.

Decision export (`POST /api/local-lab/datasets/decision/export`) reads `quiz_prompts.json` as `DecisionTrainingSample` rows and reads `quiz_attempts.json` as `DecisionAttemptTrainingLabel` rows. The exporter writes `decision/samples.jsonl`, `decision/labels.jsonl`, and `decision/dataset_manifest.json`.

Dataset summaries are available from `GET /api/local-lab/datasets` and are displayed as Local Lab cards next to export buttons. This layer is intentionally local-only; no real ML training, YOLO fine-tuning, cloud sync, or learned player value model is implemented yet.

### Dataset Health pre-training gate

Dataset health is available from `GET /api/local-lab/datasets/health` and is shown in the Local Lab **Dataset Health** section. It reads only local curated files (`curated_samples.jsonl`, `curated_labels.jsonl`, and `dataset_manifest.json`) for recognition and decision datasets. The health dashboard is a pre-training readiness gate: it explains whether curated data is large, balanced, and diverse enough for a future baseline training run, but it does **not** train a model, write a model registry entry, or block dataset export yet.

Recognition health reports sample and label counts, positive/negative counts, positive-to-negative ratio, label distribution, source project coverage, skipped project count, readiness flags, and warnings. Recommended minimums are:

- at least 1,000 curated recognition samples;
- negative recognition labels should be at least 20% of labeled positive/negative samples;
- positive-to-negative ratio should stay at or below 5:1;
- at least 3 source projects;
- both `FALSE_POSITIVE` and `FALSE_POSITIVE_TRACK` labels should be present.

Decision health reports prompt, option, attempt, sample, and label counts; positive/negative counts; role and situation distributions; missing expected-value rate; timeout rate; readiness flags; and warnings. Recommended minimums are:

- at least 50 curated decision prompts;
- at least 100 decision attempts;
- negative decision labels should be at least 30% of labeled positive/negative samples;
- at least 3 court roles and at least 5 situations;
- no more than 50% of option samples should be missing expected values;
- timeout rate above 50% is surfaced as a low-severity quality warning.

## Decision Engine v1

Decision Engine v1 turns saved quiz attempts into explainable, local JSONL decision events for downstream player-value experiments. It is deterministic and intentionally does **not** train or call a learned EPV model yet.

The engine evaluates each `quiz_attempts.json` record against its matching prompt in `quiz_prompts.json`:

- **Manual expected values first:** when every quiz option has an `expected_value`, the engine uses the selected option value, the best option value, and the opportunity cost to compute the raw score as `max(0, round(100 - opportunity_cost * 200))`.
- **Rule-based fallback:** when expected values are incomplete or absent, the engine falls back to correctness-only scoring (`100` for correct, `0` for incorrect).
- **Role-adjusted score:** the event adds deterministic adjustments for timeouts, `ROLE_READ` correctness, fast responses, and near-optimal incorrect answers with low opportunity cost.
- **Explainability:** every event includes an `explanations` array describing whether manual expected value or rule-based scoring was used and which role/time adjustments were applied.

Build local decision events from the API:

```bash
curl -X POST "http://localhost:8000/api/local-lab/decision-events/build"
```

The endpoint iterates all local projects, reads quiz prompts and attempts, writes JSONL to:

```text
backend/app/data/datasets/player_value/player_decision_events.jsonl
```

and returns a summary with `event_count`, `avg_raw_score`, `avg_role_adjusted_score`, and `opportunity_cost_avg`. The Local Lab page also includes a **Build Decision Events** button and summary card for these values.

## Data Source Governance

Basketball Decisions stores per-project source governance metadata in local JSON at `backend/data/projects/{project_id}/source.json`. This record captures the source type, license, rights confirmation, usage scope, league tag, local-storage permission, redistribution permission, and whether the project is explicitly allowed for ML training. External datasets must be registered before use, either as project-linked `source.json` metadata or in the global candidate registry exposed by `GET /api/sources`.

The global registry is stored at `backend/app/data/source_registry.json`, is metadata only, and is seeded with `POST /api/sources/seed-candidates`; it does **not** download media. Seeded candidates include BARD, E-BARD, SpaceJam / Basketball Action Recognition, and YouTube / NBA / EuroLeague / NCAA highlights. BARD and E-BARD are useful candidate references, and SpaceJam may be useful for action-classification baselines, but users must verify each repository's current license and actual media usage terms before importing or training.

YouTube and official league highlights are **reference-only by default**. Importing a YouTube URL does not make that clip training-eligible; users must confirm they have the rights or permission and update the source governance record to a training-compatible license and usage scope before it can be exported for ML datasets. Do not bulk-download NBA, EuroLeague, NCAA, YouTube, or official league highlight clips.

Local Lab dataset exports for recognition and decision training include only projects where `source.allowed_for_training` is `true`. Projects with missing source metadata, unknown licenses, YouTube reference-only licenses, unconfirmed rights, or reference-only usage scopes are skipped and listed in the export manifest with a reason. Export manifests also summarize included/skipped project counts plus source license and usage-scope distributions.

The user is responsible for confirming rights, license terms, and permitted use before training, local storage, redistribution, or import. NBA, EuroLeague, NCAA, and YouTube highlight clips should not be bulk-trained or redistributed unless permission or a license explicitly allows that use.

## Reference Video Breakdown Importer

The M8 Reference Video Breakdown Importer lets users register online teaching, breakdown, and highlight videos as source-governed reference metadata, then manually extract basketball concepts into authoring drafts. The frontend routes are `/reference-videos` for the library and create form, and `/reference-videos/:referenceId` for notes and draft conversion. The backend API is mounted under `/api/reference-videos`.

Reference video storage is local JSON only under `backend/app/data/reference_videos/`:

- `reference_videos.json` stores metadata such as title, URL, source type, license, usage scope, tags, notes, and training eligibility.
- `breakdown_notes.json` stores manually authored timestamped concepts, good reads, bad reads, coaching cues, role/situation context, tags, and confidence.
- `quiz_prompt_drafts.json` stores draft quiz prompts generated from breakdown notes.
- `decision_rule_drafts.json` stores draft decision-rule candidates generated from breakdown notes.

Important governance behavior:

- YouTube videos are stored as metadata only.
- The importer does **not** download YouTube videos or other remote media.
- YouTube reference videos default to `license_type=YOUTUBE_REFERENCE_ONLY`, `usage_scope=REFERENCE_ONLY`, and `allowed_for_training=false`.
- Reference-only videos, breakdown notes, quiz prompt drafts, and decision rule drafts are **not** training data and are not included in Local Lab dataset exports.
- Drafts are authoring aids only. Human review and approval are required before any concept becomes a governed training sample through the existing source-governed training workflow.

Breakdown notes can be converted into draft assets:

- Quiz drafts ask: `In this {situation_type}, what is the best read for the {court_role}?` They include at least option A from the note's `good_read`, option B from the note's `bad_read`, and an explanation from `coaching_cue`.
- Rule drafts copy the note's role and situation, use `concept` as the condition, use `good_read` and `bad_read` as positive/negative cues, set `suggested_weight=1.0`, and keep `coaching_cue` as the explanation.

Local Lab also displays reference-only source, prompt draft, and rule draft counts so users can see authoring progress without confusing drafts with exportable training data.

## Recognition Baseline Trainer

The M10 Recognition Baseline Trainer adds a lightweight local classifier for false-positive detection/track risk. It is intentionally scoped as a CPU-friendly baseline, not a detector training pipeline.

Key properties:

- **Local model only:** training reads the curated recognition JSONL dataset from `backend/app/data/datasets/recognition/` and writes model artifacts to `backend/app/data/models/recognition/`.
- **CPU-friendly:** the backend uses scikit-learn when it is installed and returns a clear `501` error with `debug_hint: install scikit-learn` when it is not available.
- **Not YOLO:** the trainer does not train YOLO, download weights, require CUDA, or require a GPU.
- **Recommendations only:** model scoring returns false-positive risk recommendations per detection/track and does not delete, clean, or mutate tracking artifacts.

Train the baseline from curated recognition samples:

```bash
curl -X POST "http://localhost:8000/api/local-lab/models/recognition/train-baseline"
```

Training validates that the curated dataset has at least 100 total positive/negative recognition samples, at least 10 positive samples (`PLAYER`, `VALID_PLAYER_TRACK`), and at least 10 negative samples (`FALSE_POSITIVE`, `FALSE_POSITIVE_TRACK`). When possible, the train/test split is grouped by `project_id` so test rows come from held-out projects rather than random rows.

The active model registry is available at:

```bash
curl "http://localhost:8000/api/local-lab/models/recognition"
```

The registry records the active model version and points to the versioned artifacts:

```text
backend/app/data/models/recognition/model_registry.json
backend/app/data/models/recognition/v001/model.pkl
backend/app/data/models/recognition/v001/metrics.json
backend/app/data/models/recognition/v001/feature_schema.json
```

`metrics.json` includes accuracy, precision, recall, F1, confusion matrix, train/test sample counts, and feature importance when exposed by the fitted classifier.

Score a project with the active trained model:

```bash
curl -X POST "http://localhost:8000/api/local-lab/models/recognition/score-project/{project_id}"
```

The response mirrors the recognition quality scoring shape and includes `model_version` plus model-based false-positive risk for each detection and track. Raw tracking, review patches, cleaned tracking, and projected-track artifacts are left unchanged.

## Decision Diagnostics

Decision Diagnostics are explainable, JSON-only analytics for Decision Engine quiz quality. They do **not** train an ML model. The report combines saved `quiz_prompts.json`, `quiz_attempts.json`, and `player_value/player_decision_events.jsonl` artifacts to identify:

- prompt difficulty (`TOO_EASY`, `BALANCED`, `TOO_HARD`, `INSUFFICIENT_DATA`),
- high opportunity-cost misses,
- time-pressure warnings,
- role and situation coverage gaps,
- suspected label issues where the authored correct answer is rarely selected while one wrong option dominates.

Build diagnostics with:

```bash
curl -X POST http://localhost:8000/api/local-lab/decision-diagnostics/build
```

Read the latest report with:

```bash
curl http://localhost:8000/api/local-lab/decision-diagnostics
```

The report is stored at `backend/app/data/datasets/decision/decision_diagnostics.json`. Local Lab shows the global summary, and prompt cards display difficulty badges after diagnostics have been built.

## Player Identity & Track Alias

M12 adds a local, manual Player Identity layer so reviewers can associate one or more `track_id` values with a stable project-scoped `player_key` such as `P1`, `P2`, or `P3`.

- Aliases are stored per project at `backend/data/projects/{project_id}/player_aliases.json`.
- Alias assignment is reviewer-driven from Tracking Review; the MVP does not perform jersey recognition, team classification, or automatic re-identification.
- `player_key` is a local identifier intended for future Player Value features and is not a claim about a real-world player identity.
- Raw tracking artifacts remain unchanged. Cleaned tracking review artifacts and player aliases are stored separately.
- Project bundles include `player_aliases` when the artifact exists, allowing refresh-safe hydration of manual alias assignments.

## Player Value v1

M13 adds an explainable, local-only Player Value Engine that aggregates Decision Engine events by Player Identity aliases. It is available in the UI at `/player-value` and through:

```bash
curl -X POST http://localhost:8000/api/local-lab/player-value/build
curl http://localhost:8000/api/local-lab/player-value
```

The build reads local JSON artifacts only:

- `backend/app/data/datasets/player_value/player_decision_events.jsonl` from Decision Engine v1;
- per-project `player_aliases.json` from Player Identity & Track Alias;
- `tracking_cleaned.json` or `tracking.json` for participation scoring;
- `tracking_review_patch.json` and local recognition quality scoring signals for reliability checks;
- optional per-project `source.json` for trace metadata.

Summaries are stored at:

```text
backend/app/data/datasets/player_value/player_value_summary.json
```

The v1 formula is intentionally transparent and deterministic:

```text
Player Value =
  0.45 * avg_role_adjusted_score
+ 0.20 * consistency_score
+ 0.15 * recognition_reliability_score
+ 0.10 * improvement_score
+ 0.10 * participation_score
```

Component definitions:

- `avg_role_adjusted_score` is the average Decision Engine role-adjusted score for linked decision events, falling back to `0` when there are no events.
- `consistency_score` is `100 - stddev(role_adjusted_score)`, clipped to `0..100`.
- `recognition_reliability_score` starts from local alias tracks and tracking-review/recognition risk signals. It falls back to `50` when no recognition score is available.
- `improvement_score` compares first-half and second-half role-adjusted decision scores. Sparse summaries fall back to `50`.
- `participation_score` uses the aliased track point-count percentile within the project and falls back to `50` when tracking is unavailable.

Identity limitations are important:

- Player Value v1 uses only the local `player_key` from `player_aliases.json`.
- It does **not** claim real player names, jersey identities, or scouting-grade identity resolution.
- If a decision event already includes `player_key`, that key is used. Otherwise, Player Value maps only identity-bearing `source_track_ids` through local aliases.
- If no alias can be found, the summary uses `player_key="UNKNOWN"` and includes warnings rather than inventing an identity.

### Player Value Link Integrity

Quiz prompts separate frame context from player identity links:

- `context_track_ids` are frame context only. They may contain every reviewed/cleaned track visible in the freeze frame so the prompt can keep local scene context.
- `source_track_ids` are identity-bearing links. Prompt-level source links, and especially option-level source links, identify the player track(s) directly involved in a decision.
- Quiz Builder links option source tracks by comparing normalized arrow starts to image-space track points. Pixel track points are normalized with the frame dimensions before distance matching, and reviewed `tracking_cleaned.json` tracks are preferred over raw tracking when review artifacts are present.
- Player Value alias attribution uses only `source_track_ids`; it does not use `context_track_ids` to resolve aliases. This prevents multi-player frames from being assigned to the first sorted alias just because every visible track was stored with the prompt.
- Prompts without identity-bearing source links can still train and evaluate decision logic. Their Player Value summaries may fall back to `UNKNOWN` attribution with a warning instead of guessing a player.
- If identity-bearing source tracks map to multiple aliases, Player Value assigns the event to `UNKNOWN` with a warning instead of choosing the first sorted alias.

Player Value v1 is not a learned Player Value model and is not scouting-grade. It is a local analytics summary intended to make decision-event quality, recognition reliability, trend, and participation assumptions inspectable before any future model work.

## Player Value Evidence Dashboard

M14 adds a per-player evidence dashboard for inspecting the local trace behind each Player Value summary. From the `/player-value` table, choose **View Evidence** for a row, or open the route directly:

```text
/player-value/{project_id}/{player_key}
```

The detail route reads the stored Player Value summary and expands `summary.trace.decision_event_ids` into the underlying local artifacts:

- `backend/app/data/datasets/player_value/player_value_summary.json` for the selected summary and component breakdown;
- `backend/app/data/datasets/player_value/player_decision_events.jsonl` for linked Decision Engine events;
- per-project `quiz_prompts.json` for question text, prompt explanation, and selected/correct option labels;
- per-project `player_aliases.json` for local alias metadata;
- optional per-project `source.json` trace metadata already captured by the summary build.

The evidence page shows:

- header metrics such as `player_key`, display name if present, team side, role hint, score, confidence, and warnings;
- the unchanged Player Value component breakdown;
- role and situation breakdown tables with event count, average role-adjusted score, average opportunity cost, correct rate, and timeout rate;
- a decision-event evidence table showing prompt/frame context, selected and correct options, scores, `source_track_ids`, `context_track_ids`, warnings, and links back to the project or prompt route when available;
- an evidence warning panel for missing prompts, missing events, UNKNOWN attribution, absent `source_track_ids`, ambiguous alias fallback, and low confidence.

Track-link semantics remain strict:

- `source_track_ids` are identity-bearing evidence and are the only track IDs used for alias resolution.
- `context_track_ids` are displayed for frame context only and are never promoted into alias evidence.
- UNKNOWN attribution is intentionally visible rather than hidden when source evidence is missing or ambiguous.

Player Value remains a local, explainable aggregation over saved JSON artifacts. It is not a learned model, does not perform jersey OCR, does not claim real player identity, and is not scouting-grade.
