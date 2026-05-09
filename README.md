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

The frontend now supports the real local MP4 path through the backend APIs:

1. Create a backend project.
2. Upload an MP4.
3. Extract frames with the OpenCV-backed frame extractor.
4. Choose an extracted frame for calibration.
5. Mark 4+ manual court keypoints in real image pixel coordinates.
6. Save calibration so the backend computes a `cv2.findHomography` homography.
7. Run backend tracking.
8. View detection / track / projected-track counts and projected 2D court paths.

Decision Quiz scoring and quiz-builder workflows are intentionally not part of this MVP milestone.

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
3. Review backend detection count, track count, projected track count, detector mode, the frame overlay, and the 2D court projection.

The tracking endpoint currently uses deterministic MVP detector/tracker logic, then projects image-space track points through the saved homography when calibration exists. The 2D court view renders backend `court_x` / `court_y` values as court feet in a `0 0 94 50` SVG viewBox.

Backend API example:

```bash
curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/tracking/run" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"'"${PROJECT_ID}"'","confidence_threshold":0.25,"iou_threshold":0.3,"max_players":10}'

curl "http://localhost:8000/api/projects/${PROJECT_ID}/tracks"
```

## Future: Decision Quiz

Decision Quiz is a traceable extension point for future basketball decision prompts, not an MVP-complete feature. The backend model surface is reserved in `backend/app/models/quiz.py`, with future local JSON storage expected at `backend/data/projects/{project_id}/quiz_prompts.json`. The frontend includes a placeholder `DecisionQuizOverlay.vue` that only renders a freeze frame and direction-arrow placeholder.

The following Decision Quiz work is intentionally deferred beyond the MVP:

- Scoring answers or selecting correct decisions.
- Wiring quiz prompts to coach annotations.
- Handling multi-player decision contexts.

## Current limitations / TODO functionality

The following pieces are intentionally minimal:

- **Frontend API integration**: project creation, MP4 upload, YouTube metadata creation, frame extraction, calibration saving, tracking, and projected tracks are wired for the MVP flow; broader persistence/reload behavior is still limited by in-memory Pinia state.
- **Video playback source handling**: uploaded videos are previewed with a browser object URL for the current session; production video streaming is not implemented.
- **YouTube downloader**: optional `yt-dlp` support may be unavailable in local environments.
- **Detection/tracking models**: `detector.py` and `tracker.py` remain deterministic MVP implementations, not production player models.
- **Persistence model**: project JSON files are local dev storage, not a production database.
- **Decision Quiz**: scoring, prompt authoring, and quiz-builder flows are intentionally deferred.
