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
8. View detection / track / projected-track counts and projected 2D court paths returned by the backend. The UI does not substitute demo tracks when backend results are absent.
9. Refresh or open deep links for the project, calibration frame, or tracking page; the frontend reloads available artifacts from `GET /api/projects/{project_id}/bundle`.

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

The backend video `uri` is metadata only for hydration. The browser preview still uses a session-local object URL after upload; the frontend intentionally does **not** treat backend file paths as browser-playable video URLs until a proper streaming endpoint is added.

Recommended refresh-safe demo path:

1. Create a project.
2. Upload an MP4.
3. Extract frames.
4. Refresh the project page to verify project/video/frame hydration.
5. Select a calibration frame.
6. Save calibration.
7. Refresh the calibration page to verify keypoint/homography recovery; also try removing `?frameIndex=...` from the URL to confirm the saved calibration frame is restored from backend storage.
8. Run tracking.
9. Refresh the tracking page to verify detection, track, and projected-track recovery.

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
3. Review the selected option, correct option, correctness, optional expected-value opportunity cost, option explanations, and summary explanation.

Quiz prompts are stored locally under `backend/data/projects/{project_id}/quiz_prompts.json`; attempts are appended to `backend/data/projects/{project_id}/quiz_attempts.json`. This is local development JSON storage, not a production quiz database.

Limitations intentionally kept out of scope for this MVP:

- Still image only; no video freeze playback yet.
- No EPV model; `expected_value` is manually entered and optional.
- No multi-question sessions.
- No user accounts or respondent identity.
- No coach annotation workflow.

## Current limitations / TODO functionality

The following pieces are intentionally minimal:

- **Frontend API integration**: project creation, MP4 upload, YouTube metadata creation, frame extraction, calibration saving, tracking, projected tracks, and route-level hydration are wired for the MVP flow.
- **Video playback source handling**: uploaded videos are previewed with a browser object URL for the current session; backend video file URIs are metadata only unless a streaming endpoint is added.
- **YouTube downloader**: optional `yt-dlp` support may be unavailable in local environments.
- **Detection/tracking models**: `detector.py` and `tracker.py` remain deterministic MVP implementations, not production player models.
- **Persistence model**: project JSON files are local dev storage, not a production database.
- **Decision Quiz**: the MVP is limited to one still-frame arrow prompt at a time; no accounts, sessions, video playback freeze, or learned EPV model are included.
