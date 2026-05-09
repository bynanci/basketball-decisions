from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import calibration, projects, tracking, videos

app = FastAPI(title="Basketball Decisions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(calibration.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
