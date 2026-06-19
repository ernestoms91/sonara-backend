# app/api/routers/boletin_router.py
from datetime import datetime

from fastapi import APIRouter, status, Query
from app.api.deps.auth import CurrentUser
from app.api.deps.services import BoletinServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger
from app.schemas.boletin import (
    BoletinCreateRequest,
    BoletinUpdateRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/boletin", tags=["BOLETIN"])

# ============================================
# RUTAS ESPECÍFICAS (sin parámetros de ruta)
# ============================================

@router.get(
    "/all",  # <--- ESTA DEBE IR PRIMERO
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener todos los boletines paginados",
)
async def get_all_boletines(
    current_user: CurrentUser,
    boletin_service: BoletinServiceDep,
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)"),
    size: int = Query(50, ge=1, le=100,
                      description="Cantidad de items por página (máx 100)"),
    active_only: bool = Query(True, description="Solo boletines activos"),
) -> CommonResponse:
    """
    Obtener todos los boletines con paginación y filtros.
    Retorna los audio_ids en orden para cada boletín.
    """
    logger.info(f"Obteniendo boletines: page={page}, size={size}")

    result = boletin_service.get_all(
        page=page,
        size=size,
        active_only=active_only
    )

    return CommonResponse.success(
        message="Boletines obtenidos exitosamente",
        data=result
    )


@router.post(
    "/new",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo boletín con 30 audios",
)
async def create_boletin(
    current_user: CurrentUser,
    boletin_service: BoletinServiceDep,
    request: BoletinCreateRequest,
) -> CommonResponse:
    """Crear un nuevo boletín con exactamente 30 audios"""
    logger.info(f"Recibida solicitud para crear boletín: {request.start_time}")

    result = boletin_service.create(
        start_time=request.start_time,
        audio_ids=request.audio_ids,
        created_by=current_user.full_name
    )

    return CommonResponse.success(
        message="Boletín creado exitosamente",
        data=result
    )


# ============================================
# RUTAS CON PARÁMETROS DE RUTA (van después)
# ============================================

@router.get(
    "/{boletin_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener un boletín por ID",
)
async def get_boletin_by_id(
    current_user: CurrentUser,
    boletin_id: int,
    boletin_service: BoletinServiceDep,
) -> CommonResponse:
    """
    Obtener un boletín específico con toda la información completa de los audios
    """
    logger.info(f"Obteniendo boletín ID: {boletin_id}")
    
    result = boletin_service.get_by_id(boletin_id)
    return CommonResponse.success(
        message="Boletín encontrado exitosamente",
        data=result
    )


@router.put(
    "/{boletin_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar un boletín existente",
)
async def update_boletin(
    current_user: CurrentUser,
    boletin_id: int,
    boletin_service: BoletinServiceDep,
    request: BoletinUpdateRequest,
) -> CommonResponse:
    """
    Actualizar un boletín existente con nuevos audios.
    Solo procesa los minutos donde el audio_id cambió.
    """
    logger.info(f"Recibida solicitud para actualizar boletín ID: {boletin_id}")

    result = boletin_service.update(
        boletin_id=boletin_id,
        new_audio_ids=request.audio_ids,
    )

    return CommonResponse.success(
        message=f"Boletín {boletin_id} actualizado exitosamente",
        data=result
    )


@router.delete(
    "/{boletin_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft delete de un boletín",
)
async def delete_boletin(
    current_user: CurrentUser,
    boletin_id: int,
    boletin_service: BoletinServiceDep,
) -> CommonResponse:
    """Desactiva un boletín (soft delete)"""
    logger.info(f"Recibida solicitud para desactivar boletín ID: {boletin_id}")

    result = boletin_service.soft_delete(boletin_id)

    return CommonResponse.success(
        message=result["message"],
        data=result
    )


@router.patch(
    "/{boletin_id}/activate",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Activar un boletín",
)
async def activate_boletin(
    current_user: CurrentUser,
    boletin_id: int,
    boletin_service: BoletinServiceDep,
) -> CommonResponse:
    """Activa un boletín previamente desactivado"""
    logger.info(f"Recibida solicitud para activar boletín ID: {boletin_id}")

    result = boletin_service.activate_boletin(boletin_id)

    return CommonResponse.success(
        message=result["message"],
        data=result
    )