# app/api/routers/audio_router.py
from fastapi import APIRouter, Request, status, Path, Form, Query
from app.api.deps.auth import CurrentAdmin, CurrentUser
from app.api.deps.services import AudioServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/audio", tags=["AUDIO"])


@router.post(
    "/generate/{profile_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar audio a partir de texto usando un perfil de voz clonada",
)
async def generate_audio(
    current_user: CurrentUser,
    audio_service: AudioServiceDep,
    profile_id: int = Path(..., gt=0, description="ID del perfil"),
    text: str = Form(..., min_length=1, max_length=1000,
                     description="Texto a sintetizar"),
) -> CommonResponse:
    """
    Genera un audio usando la voz clonada del perfil.
    """
    result = audio_service.generate_and_save(
        profile_id=profile_id,
        text=text,
        created_by=current_user.full_name
    )

    return CommonResponse.success(
        message="Audio generated successfully",
        data={
            "audio_id": result["audio_id"],
            "duration": result["duration"],
            "filename": result["filename"],
            "created_at": result["created_at"].isoformat() if result["created_at"] else None
        }
    )


@router.post(
    "/{audio_id}/change-duration",
    response_model=CommonResponse,
    summary="Cambiar la duración de un audio existente",
)
async def change_audio_duration(
    current_user: CurrentUser,
    audio_service: AudioServiceDep,
    audio_id: str = Path(..., description="UUID del audio original"),
    target_duration: float = Form(..., gt=0.1, le=60.0,
                                  description="Duración deseada en segundos (0.1 - 60)"),
) -> CommonResponse:
    """
    Cambia la duración de un audio manteniendo el tono.
    """
    result = audio_service.change_audio_duration(
        audio_id=audio_id,
        target_duration=target_duration
    )

    return CommonResponse.success(
        message=f"Audio duration changed to {target_duration} seconds",
        data={
            "audio_id": result["audio_id"],
            "original_audio_id": result["original_audio_id"],
            "original_duration": result["original_duration"],
            "new_duration": result["new_duration"],
            "filename": result["filename"],
            "created_at": result["created_at"].isoformat() if result["created_at"] else None
        }
    )


@router.get(
    "/all",
    response_model=CommonResponse,
    summary="Obtener lista paginada de audios",
    description="Obtiene todos los audios paginados incluyendo el nombre del perfil asociado",
)
async def get_audios_paginated(
    request: Request,
    current_user: CurrentUser,
    audio_service: AudioServiceDep,
    page: int = Query(
        1, ge=1, description="Número de página (empieza en 1)"),
    size: int = Query(
        50, ge=1, le=100, description="Cantidad de items por página (máx 100)"),
) -> CommonResponse:
    """
    Obtiene todos los audios paginados con nombre del perfil.

    - **page**: Número de página (default: 1)
    - **size**: Items por página (default: 50, máx: 100)
    """
    logger.info(f"GET /audio/audios - page={page}, size={size}")

    result = audio_service.get_audios_paginated(page=page, size=size, request=request)

    return CommonResponse.success(
        message="Audios retrieved successfully",
        data={
            "items": result["items"],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "pages": result["pages"]
        }
    )


@router.get(
    "/inactive",
    response_model=CommonResponse,
    summary="Obtener lista paginada de audios inactivos",
    description="Obtiene todos los audios inactivos",
)
async def get_audios_paginated(
    current_admin: CurrentAdmin,
    audio_service: AudioServiceDep,
    page: int = Query(
        1, ge=1, description="Número de página (empieza en 1)"),
    size: int = Query(
        50, ge=1, le=100, description="Cantidad de items por página (máx 100)"),
) -> CommonResponse:
    """
    Obtiene todos los audios inactivos paginados con nombre del perfil.

    - **page**: Número de página (default: 1)
    - **size**: Items por página (default: 50, máx: 100)
    """
    logger.info(f"GET /audio/audios - page={page}, size={size}")

    result = audio_service.get_audios_paginated(
        page=page, size=size, actives=False)

    return CommonResponse.success(
        message="Inactive audios retrieved successfully",
        data={
            "items": result["items"],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "pages": result["pages"]
        }
    )


@router.delete(
    "/{audio_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Desactivar un audio (soft delete)",
    description="Marca un audio como inactivo (active=False) sin eliminarlo físicamente",
)
async def soft_delete_audio(
    current_user: CurrentUser,
    audio_service: AudioServiceDep,
    audio_id: str = Path(..., description="ID del audio a desactivar"),
) -> CommonResponse:
    """
    Desactiva un audio cambiando su estado active a False.
    El audio no se elimina físicamente ni de la base de datos ni del sistema de archivos.
    """

    result = audio_service.soft_delete_audio(audio_id=audio_id)

    logger.info(f"DELETE /audio/{audio_id} - Soft delete")

    return CommonResponse.success(
        message=result["message"],
        data={
            "audio_id": result["audio_id"],
            "profile_id": result["profile_id"],
            "profile_name": result["profile_name"]
        }
    )


@router.post(
    "/activate/{audio_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Activa un audio",
    description="Activa un audio marcado como inactivo (active=True)",
)
async def activate_audio(
    current_admin: CurrentAdmin,
    audio_service: AudioServiceDep,
    audio_id: str = Path(..., description="ID del audio a activar"),
) -> CommonResponse:
    """
    Activa un audio cambiando su estado false a True.
    """

    result = audio_service.activate_audio(audio_id=audio_id)

    logger.info(f"ACTIVATE /audio/{audio_id}")

    return CommonResponse.success(
        message=result["message"],
        data={
            "audio_id": result["audio_id"],
            "profile_id": result["profile_id"],
            "profile_name": result["profile_name"]
        }
    )
