# app/api/errors.py
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import get_logger
from app.schemas.common import CommonResponse

logger = get_logger(__name__)


def http_exception_handler(request: Request, exc: HTTPException):
    """Maneja HTTPException para respuestas consistentes."""
    logger.warning(f"HTTPException en {request.url}: {exc.detail}")
    
    response = CommonResponse.fail(
        message=exc.detail,
        data={
            "path": str(request.url.path),
            "error_type": "http_exception"
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode='json')  # ← Convierte a JSON
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Maneja errores de validación de FastAPI (errores 422)."""
    logger.error(f"Error de validación en {request.url}")
    logger.error(f"Detalles: {exc.errors()}")
    
    response = CommonResponse.fail(
        message="Error de validación. Revise los campos requeridos.",
        data={
            "errors": exc.errors(),
            "path": str(request.url.path)
        }
    )
    
    return JSONResponse(
        status_code=422,
        content=response.model_dump(mode='json')
    )


def general_exception_handler(request: Request, exc: Exception):
    """Maneja cualquier excepción no capturada."""
    logger.error(f"Error no controlado en {request.url}", exc_info=True)
    
    response = CommonResponse.fail(
        message="Se produjo un error interno. Intente nuevamente más tarde.",
        data={
            "path": str(request.url.path),
            "error_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=500,
        content=response.model_dump(mode='json')
    )

def value_error_handler(request: Request, exc: ValueError):
    """Maneja específicamente ValueError (errores de lógica de negocio)"""
    logger.warning(f"ValueError en {request.url}: {exc}")
    
    response = CommonResponse.fail(
        message=str(exc),
        data={
            "path": str(request.url.path),
            "error_type": "ValueError"
        }
    )
    
    return JSONResponse(
        status_code=400,  # Bad Request
        content=response.model_dump(mode='json')
    )