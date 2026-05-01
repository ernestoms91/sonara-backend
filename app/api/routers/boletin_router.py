# app/api/routers/boletin_router.py
from fastapi import APIRouter, status
from app.api.deps.services import BoletinServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger
from app.schemas.boletin import BoletinCreateRequest

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
        audio_ids=request.audio_ids
    )

    return CommonResponse.success(
        message="Boletín creado exitosamente",
    )
