"""FastAPI application factory and Uvicorn entry point."""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .providers import create_provider
from .routers import catalog, mobile, reconciliation, voice
from .service import ApiError, Service
from .store import JsonStore

LOGGER = logging.getLogger("vyapaar.http")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
load_dotenv()


def create_service() -> Service:
    path = None if os.getenv("DATA_FILE") == ":memory:" else os.getenv(
        "DATA_FILE", "data/vyapaar.json"
    )
    return Service(JsonStore(path), provider=create_provider())


def create_app(service: Service | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        LOGGER.info("api_ready provider_mode=%s", _app.state.service.health()["providerMode"])
        yield

    app = FastAPI(
        title="VyapaarPeCharcha API",
        version="0.2.0",
        description=(
            "Laptop-hosted voice-order backend for an Android client. "
            "AI proposals never mutate stock or money before confirmation."
        ),
        lifespan=lifespan,
    )
    app.state.service = service or create_service()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "Content-Disposition"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        started = time.monotonic()
        supplied = request.headers.get("X-Request-Id", "")
        request_id = supplied if REQUEST_ID.fullmatch(supplied) else str(uuid.uuid4())
        request.state.request_id = request_id
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_name = getattr(route, "path", "unmatched")
            LOGGER.info(
                "http_request request_id=%s method=%s route=%s status=%s duration_ms=%s",
                request_id, request.method, route_name, status,
                round((time.monotonic() - started) * 1000),
            )

    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=error.status,
            content={
                "error": {"code": error.code, "message": str(error), "details": error.details},
                "requestId": request_id,
            },
            headers={"X-Request-Id": request_id},
        )

    @app.get("/health", tags=["operations"])
    def health():
        return app.state.service.health()

    app.include_router(catalog.router)
    app.include_router(voice.router)
    app.include_router(reconciliation.router)
    app.include_router(mobile.router)
    return app


app = create_app()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(
        "vyapaar.api:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "0").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
