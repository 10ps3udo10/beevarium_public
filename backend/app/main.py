import asyncio
import logging
import time
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse, RedirectResponse

from app.api_errors import generic_exception_handler, http_exception_handler, validation_exception_handler
from app.config import settings
from app.database import SessionLocal, get_db
from app import models
from app.routers import ateliers, auth, cadres, creation_rapide, events, feedback, ia_vocale, materiel_atelier, recoltes, references, reines, ruchers, ruches, statistiques, users, visites, visites_rucher


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("beevarium.api")


def _set_security_headers(response) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if settings.environment.lower() in {"staging", "prod", "production"}:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    start_time = time.perf_counter()
    response = None

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.max_request_body_bytes:
                request.state.api_error_code = "payload_too_large"
                request.state.api_error_message = "Payload trop volumineux"
                response = JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": f"Payload trop volumineux (max {settings.max_request_body_bytes} octets)",
                    },
                )
                response.headers["X-Request-ID"] = request_id
                return response
        except ValueError:
            request.state.api_error_code = "invalid_content_length"
            request.state.api_error_message = "Header content-length invalide"
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Header content-length invalide"},
            )
            response.headers["X-Request-ID"] = request_id
            return response

    try:
        async with asyncio.timeout(settings.request_timeout_seconds):
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        _set_security_headers(response)
        if not request.url.path.startswith("/app/"):
            response.headers["Cache-Control"] = "no-store"
        return response
    except TimeoutError:
        request.state.api_error_code = "request_timeout"
        request.state.api_error_message = "Request timeout"
        response = JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": f"Request timeout ({settings.request_timeout_seconds}s)"},
        )
        response.headers["X-Request-ID"] = request_id
        _set_security_headers(response)
        response.headers["Cache-Control"] = "no-store"
        return response
    finally:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status_code = response.status_code if response is not None else 500
        current_user_id = getattr(request.state, "current_user_id", None)
        error_code = getattr(request.state, "api_error_code", None)
        error_message = getattr(request.state, "api_error_message", None)
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s user_id=%s",
            request_id,
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            current_user_id or "anonymous",
        )
        db = SessionLocal()
        try:
            db.add(
                models.ApiEvent(
                    request_id=request_id,
                    user_id=current_user_id,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=status_code,
                    duration_ms=duration_ms,
                    error_code=error_code,
                    error_message=error_message,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist api event request_id=%s path=%s", request_id, request.url.path)
        finally:
            db.close()
app.include_router(auth.router)
app.include_router(ateliers.router)
app.include_router(events.router)
app.include_router(feedback.router)
app.include_router(ia_vocale.router)
app.include_router(cadres.router)
app.include_router(materiel_atelier.router)
app.include_router(recoltes.router)
app.include_router(statistiques.router)
app.include_router(references.router)
app.include_router(users.router)
app.include_router(creation_rapide.router)
app.include_router(ruchers.router)
app.include_router(ruches.router)
app.include_router(reines.router)
app.include_router(visites.router)
app.include_router(visites_rucher.router)

static_app_dir = Path(__file__).resolve().parent / "static" / "app"


class RevalidatingStaticFiles(StaticFiles):
    """Force le navigateur a revalider a chaque chargement.

    Sans cela, un index.html garde en cache peut etre servi avec un app.js
    plus recent, ce qui casse l initialisation du client.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        _set_security_headers(response)
        return response


if static_app_dir.exists():
    app.mount("/app", RevalidatingStaticFiles(directory=str(static_app_dir), html=True), name="webapp")


@app.get("/", include_in_schema=False)
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/app/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "connected",
        "app_version": settings.app_version,
        "environment": settings.environment,
    }
