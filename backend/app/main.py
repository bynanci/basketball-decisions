from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import calibration, decision_rules, development_dashboard, drills, local_lab, player_identity, practice_executions, practice_plans, projects, quiz, reference_videos, reports, review_queue, sources, tracking, videos

app = FastAPI(title="Basketball Decisions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(player_identity.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(videos.frames_router, prefix="/api")
app.include_router(calibration.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")
app.include_router(local_lab.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(reference_videos.router, prefix="/api")
app.include_router(decision_rules.router, prefix="/api")
app.include_router(drills.router, prefix="/api")
app.include_router(practice_plans.router, prefix="/api")
app.include_router(practice_executions.router, prefix="/api")
app.include_router(review_queue.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(development_dashboard.router, prefix="/api")


@app.exception_handler(HTTPException)
async def api_http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"code", "message", "details", "debug_hint"}.issubset(exc.detail):
        payload = exc.detail
    else:
        payload = {
            "code": "HTTP_ERROR",
            "message": str(exc.detail),
            "details": {},
            "debug_hint": "Check the request path, method, headers, and body.",
        }
    return JSONResponse(status_code=exc.status_code, content=payload, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "REQUEST_VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": {"errors": jsonable_encoder(exc.errors())},
            "debug_hint": "Compare the request body and parameters with the endpoint's Pydantic model.",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected API error occurred.",
            "details": {"exception_type": exc.__class__.__name__},
            "debug_hint": "Check backend logs for the stack trace and add a typed api_error for expected failure modes.",
        },
    )


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
