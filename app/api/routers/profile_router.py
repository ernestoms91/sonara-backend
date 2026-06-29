# app/api/routers/profile_router.py
from fastapi import APIRouter, Query, status, UploadFile, File, Form, Path
from app.api.deps import ProfileServiceDep
from app.api.deps.auth import CurrentAdmin, CurrentUser
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
    current_admin: CurrentAdmin,
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
    current_admin: CurrentAdmin,
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
    current_admin: CurrentAdmin,
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
    current_user: CurrentUser,
    profile_service: ProfileServiceDep,
    page: int = Query(default=1, ge=1, description="Número de página"),
    size: int = Query(default=50, ge=1, le=1000,
                      description="Items por página"),
    active_only: bool = Query(
        default=False, description="Filtrar solo activos")
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


@router.delete(
    "/{profile_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar perfil",
    description="Elimina un perfil de la BD y su carpeta física. Requiere que el perfil esté inactivo."
)
async def delete_profile(
    current_admin: CurrentAdmin,
    profile_service: ProfileServiceDep,
    profile_id: int = Path(..., description="ID del perfil a eliminar"),
    force: bool = Query(
        default=False,
        description="Forzar eliminación aunque el perfil esté activo"
    )
) -> CommonResponse:
    """
    Elimina un perfil de forma permanente.
    
    - Elimina el registro de la base de datos
    - Elimina la carpeta física con todos sus archivos
    
    **Requisitos**: 
    - El perfil debe estar inactivo (active=False)
    - O usar force=true para eliminar aunque esté activo
    """
    result = profile_service.delete_profile(profile_id, force=force)
    
    # Construir mensaje detallado
    profile = result["profile"]
    folder_status = "eliminada" if result["folder_deleted"] else "no encontrada"
    
    message = (
        f"Profile '{profile['name']}' (ID={profile['id']}) deleted successfully. "
        f"Folder {folder_status}. "
        f"Size: {result['folder_size_bytes']} bytes"
    )
    
    return CommonResponse.success(
        message=message,
        data={
            "profile": profile,
            "folder_deleted": result["folder_deleted"],
            "folder_size_bytes": result["folder_size_bytes"]
        }
    )