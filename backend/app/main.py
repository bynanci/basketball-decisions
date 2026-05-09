from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.projects import router as projects_router
from backend.app.core.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from backend.app.services.storage import ensure_data_dirs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_data_dirs()
    yield


app = FastAPI(title="Basketball Decisions API", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(projects_router)
