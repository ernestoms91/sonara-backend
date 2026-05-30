# app/api/routers/profile_router.py
from fastapi import APIRouter, Query, status, UploadFile, File, Form, Path
from app.api.deps import ProfileServiceDep
from app.schemas.common import CommonResponse
from app.core.logging import get_logger
from app.schemas.profile import ProfileResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/profile", tags=["PROFILE"])


@router.post(
    "/new",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear perfil de voz clonada",
)
async def create_profile(
    profile_service: ProfileServiceDep,
    name: str = Form(..., min_length=1, description="Nombre del narrador"),
    ref_text: str = Form(..., min_length=1,
                         description="Texto de referencia para la voz"),
    language: str = Form(default="Spanish"),
    audio_file: UploadFile = File(...)
) -> CommonResponse:
    logger.info(f"Recibida solicitud para crear perfil: {name}")
    audio_bytes = await audio_file.read()

    profile = profile_service.create_profile(
        name=name,
        ref_text=ref_text,
        audio_bytes=audio_bytes,
        filename=audio_file.filename,
        content_type=audio_file.content_type,
        language=language,
    )

    return CommonResponse.success(
        message="Profile created successfully",
        data=ProfileResponse.model_validate(profile)
    )


@router.post(
    "/{profile_id}/deactivate",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Desactivar perfil",
    description="Cambia el estado active=False del perfil. No borra archivos físicos."
)
async def deactivate_profile(
    profile_id: int,
    profile_service: ProfileServiceDep,
) -> CommonResponse:
    """
    Desactiva un perfil existente.

    - **profile_id**: ID numérico del perfil
    """
    profile = profile_service.deactivate_profile(profile_id)

    return CommonResponse.success(
        message=f"Profile '{profile.name}' deactivated successfully",
        data={
            "id": profile.id,
            "name": profile.name,
            "active": profile.active
        }
    )


@router.post(
    "/{profile_id}/verify-and-activate",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar archivos y activar perfil",
)
async def verify_and_activate_profile(
    profile_id: int,
    profile_service: ProfileServiceDep,
) -> CommonResponse:
    profile = profile_service.activate_profile_with_validation(profile_id)

    return CommonResponse.success(
        message=f"Profile '{profile.name}' verified and activated successfully",
        data={
            "id": profile.id,
            "name": profile.name,
            "folder_id": profile.folder_id,
            "active": profile.active,
            "hours_ready": profile.hours_ready,
            "minutes_ready": profile.minutes_ready,
            "connectors_ready": profile.connectors_ready
        }
    )


@router.get(
    "/",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar perfiles con paginación",
)
async def list_profiles(
    profile_service: ProfileServiceDep,
    page: int = Query(default=1, ge=1, description="Número de página"),
    size: int = Query(default=50, ge=1, le=1000, description="Items por página"),
    active_only: bool = Query(default=False, description="Filtrar solo activos")
) -> CommonResponse:
    """
    Lista perfiles con paginación.
    """
    result = profile_service.get_profiles_paginated(
        page=page, 
        size=size, 
        active_only=active_only
    )
    
    return CommonResponse.success(
        message="Profiles retrieved successfully",
        data=result
    )