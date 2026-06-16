# app/api/routers/audio_router.py
from fastapi import APIRouter, Request, status, Path, Query
from app.api.deps.auth import CurrentAdmin, CurrentUser
from app.api.deps.services import AudioServiceDep
from app.schemas.audio import (
    AudioForBoletinRequest,
    GenerateAudioRequest,
    GenerateDuetRequest,
    ChangeDurationRequest,
    AudioDataResponse,
    DuetAudioDataResponse,
    DurationChangedResponse
)
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
    request: GenerateAudioRequest,
    profile_id: int = Path(..., gt=0, description="ID del perfil"),
) -> CommonResponse:
    """
    Genera un audio usando la voz clonada del perfil.
    """
    result = audio_service.generate_and_save(
        profile_id=profile_id,
        text=request.text,
        created_by=current_user.full_name
    )

    response_data = AudioDataResponse(
        audio_id=result["audio_id"],
        duration=result["duration"],
        character_count=result.get("character_count", 0),
        filename=result["filename"],
        created_at=result.get("created_at")
    )

    return CommonResponse.success(
        message="Audio generated successfully",
        data=response_data.model_dump(mode="json")
    )


@router.post(
    "/generate-duet/{profile_a_id}/{profile_b_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar audio con dos voces alternadas usando marcadores [P1], [P2], etc.",
)
async def generate_duet_audio(
    current_user: CurrentUser,
    audio_service: AudioServiceDep,
    request: GenerateDuetRequest,
    profile_a_id: int = Path(..., gt=0,
                             description="ID del perfil A (voz para párrafos impares)"),
    profile_b_id: int = Path(..., gt=0,
                             description="ID del perfil B (voz para párrafos pares)"),
) -> CommonResponse:
    """
    Genera un audio usando dos voces clonadas alternadas por párrafo.

    El texto debe contener marcadores [P1], [P2], [P3], etc.

    Reglas de asignación:
    - Párrafos impares ([P1], [P3], [P5]...) → Voz del perfil A
    - Párrafos pares ([P2], [P4], [P6]...) → Voz del perfil B
    """
    result = audio_service.generate_duet_and_save(
        profile_a_id=profile_a_id,
        profile_b_id=profile_b_id,
        text_with_markers=request.text,
        created_by=current_user.full_name
    )

    response_data = DuetAudioDataResponse(
        audio_id=result["audio_id"],
        duration=result["duration"],
        character_count=result.get("character_count", 0),
        filename=result["filename"],
        created_at=result.get("created_at"),
        profile_a=result["profile_a"],
        profile_b=result["profile_b"]
    )

    return CommonResponse.success(
        message="Duet audio generated successfully",
        data=response_data.model_dump(mode="json")
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
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)"),
    size: int = Query(50, ge=1, le=100,
                      description="Cantidad de items por página (máx 100)"),
) -> CommonResponse:
    """
    Obtiene todos los audios paginados con nombre del perfil.
    """
    logger.info(f"GET /audio/all - page={page}, size={size}")

    result = audio_service.get_audios_paginated(
        page=page, size=size, request=request)

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
async def get_inactive_audios_paginated(
    current_admin: CurrentAdmin,
    audio_service: AudioServiceDep,
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)"),
    size: int = Query(50, ge=1, le=100,
                      description="Cantidad de items por página (máx 100)"),
) -> CommonResponse:
    """
    Obtiene todos los audios inactivos paginados con nombre del perfil.
    """
    logger.info(f"GET /audio/inactive - page={page}, size={size}")

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
    summary="Activar un audio",
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

@router.post(
    "/generate-boletin",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar audios para un boletín completo",
    description="Genera un audio dueto por cada minuto del boletín",
)
async def generate_boletin_audios(
    current_user: CurrentUser,
    audio_service: AudioServiceDep,
    request: AudioForBoletinRequest,
) -> CommonResponse:
    """
    Genera audios para un boletín completo.
    
    - Cada minuto debe tener texto con formato [P1]... [P2]...
    - El perfil A lee los párrafos P1
    - El perfil B lee los párrafos P2
    - Genera un audio independiente por cada minuto
    """
    result = audio_service.generate_boletin_audios(
        boletin_data=request.model_dump(),
        profile_a_id=request.profile_a_id,
        profile_b_id=request.profile_b_id,
        created_by=current_user.full_name
    )
    
    return CommonResponse.success(
        message=f"Boletín procesado: {result['generados']} de {result['total_minutos']} audios generados",
        data=result
    )