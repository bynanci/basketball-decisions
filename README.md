# Basketball Decisions

A minimal runnable monorepo for basketball-video decision experiments. The repo has a Vite + Vue 3 + TypeScript frontend and a FastAPI backend with stubbed pipeline modules for frame extraction, homography, player detection, tracking, and 2D court projection.

## Repository layout

```text
frontend/                 # Vite + Vue 3 + TypeScript app
  src/pages/              # Home, project, calibration, tracking pages
  src/components/         # Video and overlay components
backend/                  # FastAPI app
  app/api/                # Projects, videos, calibration, tracking routers
  app/pipeline/           # Stub pipeline building blocks
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

## 3. Upload a local MP4

From the UI:

1. Open the home page.
2. In **Local MP4**, enter a project name.
3. Choose an `.mp4` file.
4. Click **Create upload project**.

Backend API example:

```bash
PROJECT_ID="<project id returned by POST /api/projects>"
curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/video/upload" \
  -F "file=@/absolute/path/to/video.mp4"
```

Uploaded files are stored under the project directory in `backend/app/data/projects/`. This directory is intended for local development data and is ignored by git except for `.gitkeep`.

## 4. Create a project from a YouTube URL

YouTube source processing is only for videos you have the rights or permission to process. For MVP demos, prefer the local MP4 upload flow because it avoids optional downloader setup and third-party source availability issues.

From the UI:

1. Open the home page.
2. In **YouTube URL**, paste a YouTube watch URL.
3. Check **I confirm I have the rights or permission to process this video.**
4. Click **Create YouTube project**. The submit button stays disabled until the checkbox is selected.

Backend API example:

```bash
PROJECT_ID="<project id returned by POST /api/projects>"
curl -X POST "http://localhost:8000/api/projects/${PROJECT_ID}/video/youtube" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","rights_confirmed":true}'
```

If `rights_confirmed` is `false`, the endpoint returns `400 Bad Request`. If the optional downloader dependency such as `yt-dlp` is not installed, the endpoint returns `501 Not Implemented` with `debug_hint: "Install optional YouTube downloader or use local MP4 upload for MVP demo."` instead of pretending the video was processed.

## 5. Manually mark court keypoints

1. Create or open a project in the frontend.
2. Click **Calibrate court**.
3. Use the calibration page as the placeholder interaction surface for court keypoints.
4. Submit keypoints to the backend homography endpoint when wiring the UI to the API.

Backend API example:

```bash
curl -X POST http://localhost:8000/api/calibration/homography \
  -H "Content-Type: application/json" \
  -d '{
    "project_id":"demo",
    "image_points":[{"x":100,"y":200},{"x":500,"y":200},{"x":100,"y":600},{"x":500,"y":600}],
    "court_points":[{"x":0,"y":0},{"x":94,"y":0},{"x":0,"y":50},{"x":94,"y":50}]
  }'
```

The homography module currently returns an identity matrix plus the submitted points.

## 6. Run the tracking demo

From the UI:

1. Open a project.
2. Click **Tracking demo**.
3. Review the placeholder video track overlay and 2D court projection.

Backend API example:

```bash
curl -X POST http://localhost:8000/api/tracking/demo \
  -H "Content-Type: application/json" \
  -d '{"project_id":"demo"}'
```

The endpoint runs deterministic detector, tracker, and projector stubs so downstream UI integration can start before model work is complete.

## 7. Stub / TODO functionality

The following pieces are intentionally minimal placeholders:

- **Frontend API integration**: forms currently create in-memory Pinia projects; wire them to the FastAPI endpoints next.
- **Video playback source handling**: uploaded and YouTube videos are represented as metadata in the UI until storage URLs/streaming are added.
- **Court keypoint editing**: calibration overlay displays seed points; click/drag creation and persistence are TODO.
- **Frame extraction**: `frame_extractor.py` creates output folders but does not call OpenCV or ffmpeg yet.
- **Homography estimation**: `homography.py` returns an identity matrix placeholder.
- **Detection/tracking models**: `detector.py` and `tracker.py` return deterministic demo data.
- **2D projection accuracy**: `projector.py` returns simple demo court coordinates instead of applying a real homography.
- **Persistence model**: project JSON files are local dev storage, not a production database.
