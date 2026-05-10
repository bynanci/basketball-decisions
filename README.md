# Basketball Decisions

A minimal runnable monorepo for basketball-video decision experiments. The repo has a Vite + Vue 3 + TypeScript frontend and a FastAPI backend with local JSON storage for projects, uploads, extracted frames, manual calibration, tracking, and projected 2D court paths.

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
