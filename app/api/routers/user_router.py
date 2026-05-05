# app/api/routers/user_router.py
from fastapi import APIRouter, status, Depends, Query, Body
from typing import Optional
from app.core.logging import get_logger
from app.schemas.common import CommonResponse
from app.schemas.user import UserCreate, UserPublic, UserUpdate, UserLogin
from app.schemas.token import Token
from app.api.deps import UserServiceDep, CurrentUserDep, CurrentAdminDep

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["USERS"])


# ============================================
# PUBLIC ENDPOINTS (no auth)
# ============================================

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Login de usuario"
)
async def login(
    login_data: UserLogin,
    user_service: UserServiceDep
) -> Token:
    """Autenticar usuario y obtener token JWT"""
    logger.info(f"Intento de login: {login_data.username}")
    return user_service.login(login_data)


# ============================================
# ADMIN ONLY ENDPOINTS
# ============================================

@router.post(
    "/new",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario (solo admin)"
)
async def create_user(
    user_data: UserCreate,
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep  # Solo admin puede crear usuarios
) -> CommonResponse:
    """Crear un nuevo usuario. Solo administradores."""
    logger.info(f"Admin {current_admin.username} creando usuario: {user_data.username}")
    
    user = user_service.create_user(user_data, created_by_admin=True)
    
    return CommonResponse.success(
        message="User created successfully",
        data=UserPublic.model_validate(user)
    )


@router.get(
    "/",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar todos los usuarios (solo admin)"
)
async def list_users(
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    active_only: bool = Query(False, description="Mostrar solo usuarios activos")
) -> CommonResponse:
    """Listar todos los usuarios. Solo administradores."""
    logger.info(f"Admin {current_admin.username} listando usuarios")
    
    if active_only:
        users = user_service.list_active_users(skip, limit)
    else:
        users = user_service.list_all_users(skip, limit)
    
    return CommonResponse.success(
        message="Users retrieved successfully",
        data=[UserPublic.model_validate(user) for user in users]
    )


@router.get(
    "/stats",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Estadísticas de usuarios (solo admin)"
)
async def get_user_stats(
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep
) -> CommonResponse:
    """Obtener estadísticas de usuarios. Solo administradores."""
    logger.info(f"Admin {current_admin.username} consultando estadísticas")
    
    stats = user_service.get_stats(current_admin)
    
    return CommonResponse.success(
        message="Statistics retrieved successfully",
        data=stats
    )


@router.get(
    "/{user_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario por ID (solo admin)"
)
async def get_user_by_id(
    user_id: int,
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep
) -> CommonResponse:
    """Obtener usuario por ID. Solo administradores."""
    logger.info(f"Admin {current_admin.username} consultando usuario ID={user_id}")
    
    user = user_service.get_user_by_id(user_id)
    
    return CommonResponse.success(
        message="User retrieved successfully",
        data=UserPublic.model_validate(user)
    )


@router.put(
    "/{user_id}/disable",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Deshabilitar usuario (solo admin)"
)
async def disable_user(
    user_id: int,
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep
) -> CommonResponse:
    """Deshabilitar un usuario. Solo administradores."""
    logger.info(f"Admin {current_admin.username} deshabilitando usuario ID={user_id}")
    
    user = user_service.disable_user(user_id, current_admin)
    
    return CommonResponse.success(
        message=f"User '{user.username}' disabled successfully",
        data=UserPublic.model_validate(user)
    )


@router.put(
    "/{user_id}/enable",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Habilitar usuario (solo admin)"
)
async def enable_user(
    user_id: int,
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep
) -> CommonResponse:
    """Habilitar un usuario. Solo administradores."""
    logger.info(f"Admin {current_admin.username} habilitando usuario ID={user_id}")
    
    user = user_service.enable_user(user_id, current_admin)
    
    return CommonResponse.success(
        message=f"User '{user.username}' enabled successfully",
        data=UserPublic.model_validate(user)
    )


@router.delete(
    "/{user_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario (solo admin)"
)
async def delete_user(
    user_id: int,
    user_service: UserServiceDep,
    current_admin: CurrentAdminDep
) -> CommonResponse:
    """Eliminar un usuario. Solo administradores."""
    logger.info(f"Admin {current_admin.username} eliminando usuario ID={user_id}")
    
    user_service.delete_user(user_id, current_admin)
    
    return CommonResponse.success(
        message=f"User with ID {user_id} deleted successfully"
    )


# ============================================
# AUTHENTICATED USER ENDPOINTS (admin or same user)
# ============================================

@router.get(
    "/me/info",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener mi información"
)
async def get_my_info(
    current_user: CurrentUserDep,
    user_service: UserServiceDep
) -> CommonResponse:
    """Obtener información del usuario autenticado."""
    logger.info(f"Usuario {current_user.username} consultando su propia información")
    
    user = user_service.get_user_by_id(current_user.id)
    
    return CommonResponse.success(
        message="User info retrieved successfully",
        data=UserPublic.model_validate(user)
    )


@router.put(
    "/me/update",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar mi información"
)
async def update_my_info(
    update_data: UserUpdate,
    current_user: CurrentUserDep,
    user_service: UserServiceDep
) -> CommonResponse:
    """Actualizar información del usuario autenticado."""
    logger.info(f"Usuario {current_user.username} actualizando su información")
    
    # Filtrar solo campos permitidos para el propio usuario
    allowed_fields = {k: v for k, v in update_data.dict(exclude_unset=True).items() 
                     if k not in ["is_admin"]}  # No puede cambiar is_admin
    
    if allowed_fields:
        user = user_service.update_user(current_user.id, allowed_fields, current_user)
    else:
        user = user_service.get_user_by_id(current_user.id)
    
    return CommonResponse.success(
        message="User info updated successfully",
        data=UserPublic.model_validate(user)
    )


@router.post(
    "/me/change-password",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Cambiar mi contraseña"
)
async def change_my_password(
    old_password: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True, min_length=6),
    current_user: CurrentUserDep,
    user_service: UserServiceDep
) -> CommonResponse:
    """Cambiar la contraseña del usuario autenticado."""
    logger.info(f"Usuario {current_user.username} cambiando su contraseña")
    
    user_service.change_password(current_user.id, old_password, new_password, current_user)
    
    return CommonResponse.success(
        message="Password changed successfully"
    )