# app/api/errors.py
from typing import List, Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import get_logger
from app.schemas.common import CommonResponse

logger = get_logger(__name__)


def _extract_validation_messages(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrae mensajes personalizados de errores de validación.
    """
    extracted = []
    
    for error in errors:
        # Obtener el campo (último elemento de la ubicación)
        field = error.get("loc", ["unknown"])[-1] if error.get("loc") else "unknown"
        
        # Obtener tipo de error
        error_type = error.get("type", "unknown")
        
        # Obtener mensaje base
        msg = error.get("msg", "Invalid value")
        
        # Extraer mensaje personalizado de ValueError
        if "ctx" in error and "error" in error["ctx"]:
            msg = str(error["ctx"]["error"])
        elif msg.startswith("Value error, "):
            msg = msg[12:]  # Quita "Value error, "
        
        extracted.append({
            "field": str(field),
            "message": msg,
            "type": error_type,
            "input": error.get("input")
        })
    
    return extracted


def _determine_status_code(errors: List[Dict[str, Any]]) -> int:
    """
    Determina el status code apropiado según el tipo de error.
    
    - 400: Errores de validación de negocio (ValueError personalizados)
    - 422: Errores de formato/estructura de FastAPI
    """
    for error in errors:
        # Si tiene mensaje personalizado, es error de negocio -> 400
        if "ctx" in error and "error" in error["ctx"]:
            return status.HTTP_400_BAD_REQUEST
        
        # Errores de tipo missing, type_error, etc. -> 422
        error_type = error.get("type", "")
        if error_type in ["missing", "type_error", "value_error"]:
            continue
    
    return status.HTTP_422_UNPROCESSABLE_ENTITY


def http_exception_handler(request: Request, exc: HTTPException):
    """
    Maneja HTTPException para respuestas consistentes.
    
    Status codes: 400, 401, 403, 404, 409, etc.
    """
    logger.warning(
        f"HTTP {exc.status_code} | {request.method} {request.url.path} | {exc.detail}"
    )
    
    response = CommonResponse.fail(
        message=exc.detail,
        data={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode='json')
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Maneja errores de validación de forma profesional.
    
    - Extrae mensajes personalizados de ValueError
    - Retorna estructura limpia con todos los errores
    - Status code dinámico (400 o 422)
    """
    errors = exc.errors()
    
    # Extraer mensajes personalizados
    error_details = _extract_validation_messages(errors)
    
    # Determinar status code apropiado
    status_code = _determine_status_code(errors)
    
    # Logging conciso
    fields_with_errors = [e["field"] for e in error_details]
    logger.warning(
        f"Validación fallida | {request.method} {request.url.path} | "
        f"Campos: {fields_with_errors} | Status: {status_code}"
    )
    
    # Respuesta limpia para el cliente
    response = CommonResponse.fail(
        message="Error de validación en uno o más campos",
        data={
            "path": request.url.path,
            "method": request.method,
            "errors": error_details
        }
    )
    
    # Opcional: Incluir timestamp de la request original en debug
    if logger.isEnabledFor(10):  # DEBUG level
        response.data["request_id"] = getattr(request.state, "request_id", None)
    
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode='json')
    )


def value_error_handler(request: Request, exc: ValueError):
    """
    Maneja errores de lógica de negocio (ValueError).
    
    Status code: 400 Bad Request
    """
    logger.info(
        f"Error de negocio | {request.method} {request.url.path} | {exc}"
    )
    
    response = CommonResponse.fail(
        message=str(exc),
        data={
            "path": request.url.path,
            "method": request.method,
            "error_type": "ValidationError"
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response.model_dump(mode='json')
    )


def general_exception_handler(request: Request, exc: Exception):
    """
    Maneja cualquier excepción no capturada.
    
    Status code: 500 Internal Server Error
    """
    # Log completo con stack trace
    logger.error(
        f"Error no controlado | {request.method} {request.url.path} | "
        f"Tipo: {type(exc).__name__}",
        exc_info=True
    )
    
    # En desarrollo, puedes incluir más detalles
    error_detail = {
        "path": request.url.path,
        "method": request.method,
        "error_type": type(exc).__name__
    }
    
    # Opcional: En debug, incluir mensaje original
    if logger.isEnabledFor(10):  # DEBUG level
        error_detail["debug_message"] = str(exc)
    
    response = CommonResponse.fail(
        message="Error interno del servidor. Contacte al administrador.",
        data=error_detail
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump(mode='json')
    )


# Registrar todos los handlers en la app
def register_exception_handlers(app):
    """Registra todos los exception handlers en la aplicación FastAPI."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    logger.info("Exception handlers registrados correctamente")