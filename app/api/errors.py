# app/api/errors.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


def http_exception_handler(request: Request, exc: HTTPException):
    """Maneja HTTPException para respuestas consistentes."""
    logger.warning(f"HTTPException en {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_exception",
            "detail": exc.detail,
            "path": str(request.url.path),
        },
    )


def general_exception_handler(request: Request, exc: Exception):
    """Maneja cualquier excepción no capturada."""
    logger.error(f"Error no controlado en {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "Se produjo un error interno. Intente nuevamente más tarde.",
            "path": str(request.url.path),
        },
    )
