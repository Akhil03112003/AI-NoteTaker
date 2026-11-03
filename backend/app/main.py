"""FastAPI application factory and safe API error envelopes."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import make_engine, make_session_factory
from app.processing import run_processing
from app.sessions import APIError, action_items_router, router as sessions_router


logger = logging.getLogger(__name__)


def _error_payload(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
    processor=None,
) -> FastAPI:
    app_settings = settings or get_settings()
    engine: Engine | None = None
    if session_factory is None:
        engine = make_engine(app_settings.database_url.get_secret_value())
        session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(title="AI Notetaker API", version="0.1.0", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.processor = processor or run_processing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )
    app.include_router(sessions_router)
    app.include_router(action_items_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo submitted file names, field values, or Pydantic's raw input data.
        return JSONResponse(
            status_code=422,
            content=_error_payload("request_validation_error", "The request fields are invalid."),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = {
            404: ("not_found", "The requested resource was not found."),
            405: ("method_not_allowed", "This method is not allowed for the requested resource."),
        }.get(exc.status_code, ("request_failed", "The request could not be completed."))
        return JSONResponse(status_code=exc.status_code, content=_error_payload(code, message))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled API error", extra={"error_type": type(exc).__name__})
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_error", "The request could not be completed."),
        )

    return app


app = create_app()
