from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.projects import router as projects_router
from backend.app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from backend.app.services.storage import ensure_data_dirs

app = FastAPI(title="Basketball Decisions API", version="0.1.0")
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(projects_router)


@app.on_event("startup")
def startup() -> None:
    ensure_data_dirs()
