# app/api/routers/boletin_router.py
from fastapi import APIRouter, status
from app.api.deps.services import BoletinServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger
from app.schemas.boletin import BoletinCreateRequest, BoletinUpdateRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/boletin", tags=["BOLETIN"])


@router.post(
    "/new",    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo boletín con 30 audios",
)
async def create_boletin(
    boletin_service: BoletinServiceDep,
    request: BoletinCreateRequest,
) -> CommonResponse:
    """Crear un nuevo boletín con exactamente 30 audios"""
    logger.info(f"Recibida solicitud para crear boletín: {request.start_time}")

    boletin_service.create(
        start_time=request.start_time,
        audio_ids=request.audio_ids,
        bol_date=request.bol_date
    )

    return CommonResponse.success(
        message="Boletín creado exitosamente",
    )


@router.put(
    "/{boletin_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar un boletín existente",
)
async def update_boletin(
    boletin_id: int,
    boletin_service: BoletinServiceDep,
    request: BoletinUpdateRequest,
) -> CommonResponse:
    """
    Actualizar un boletín existente con nuevos audios.
    Solo procesa los minutos donde el audio_id cambió.
    """
    logger.info(f"Recibida solicitud para actualizar boletín ID: {boletin_id}")

    boletin_service.update(
        boletin_id=boletin_id,
        new_audio_ids=request.audio_ids,
    )

    return CommonResponse.success(
        message=f"Boletín {boletin_id} actualizado exitosamente",
    )

@router.delete(
    "/{boletin_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft delete de un boletín",
)
async def delete_boletin(
    boletin_id: int,
    boletin_service: BoletinServiceDep,
) -> CommonResponse:
    """Desactiva un boletín (soft delete)"""
    logger.info(f"Recibida solicitud para desactivar boletín ID: {boletin_id}")
    
    result = boletin_service.soft_delete(boletin_id)
    
    return CommonResponse.success(
        message=result["message"],
        data={"boletin_id": result["boletin_id"], "start_time": result["start_time"]}
    )


@router.patch(
    "/{boletin_id}/activate",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Activar un boletín",
)
async def activate_boletin(
    boletin_id: int,
    boletin_service: BoletinServiceDep,
) -> CommonResponse:
    """Activa un boletín previamente desactivado"""
    logger.info(f"Recibida solicitud para activar boletín ID: {boletin_id}")
    
    result = boletin_service.activate_boletin(boletin_id)
    
    return CommonResponse.success(
        message=result["message"],
        data={"boletin_id": result["boletin_id"], "start_time": result["start_time"]}
    )