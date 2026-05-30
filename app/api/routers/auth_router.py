# app/api/routers/auth_router.py
from fastapi import APIRouter, status, Query, Path
from app.api.deps.auth import CurrentUser, CurrentAdmin
from app.api.deps.services import AuthServiceDep
from app.core.logging import get_logger
from app.schemas.common import CommonResponse
from app.schemas.auth import LoginRequest
from app.schemas.auth import ChangePasswordRequest, UserCreateRequest, UserResponse, UserUpdateRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["AUTHENTICATION"])


@router.post(
    "/login",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Login de usuario"
)
async def login(
    auth_service: AuthServiceDep,
    login_data: LoginRequest
) -> CommonResponse:
    """Login con username y password."""
    result = auth_service.login(login_data.username, login_data.password)
    return CommonResponse.success(message="Login exitoso", data=result)


@router.post(
    "/change-password",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Cambiar contraseña"
)
async def change_password(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
    request: ChangePasswordRequest
) -> CommonResponse:
    """Cambia la contraseña del usuario autenticado."""
    auth_service.change_password(current_user, request.current_password, request.new_password)
    return CommonResponse.success(message="Contraseña cambiada exitosamente")


@router.post(
    "/users",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario (solo admin)"
)
async def create_user(
    current_admin: CurrentAdmin,
    auth_service: AuthServiceDep,
    request: UserCreateRequest
) -> CommonResponse:
    """Crea un nuevo usuario. Solo administradores."""
    new_user = auth_service.create_user(current_admin, request)
    return CommonResponse.success(
        message="Usuario creado exitosamente",
        data=UserResponse.model_validate(new_user)
    )


@router.get(
    "/me",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario actual"
)
async def get_current_user_profile(
    current_user: CurrentUser
) -> CommonResponse:
    """Retorna la información del usuario autenticado."""
    return CommonResponse.success(
        message="Perfil obtenido",
        data=UserResponse.model_validate(current_user)
    )


@router.get(
    "/users",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar todos los usuarios (solo admin)"
)
async def list_users(
    current_admin: CurrentAdmin,
    auth_service: AuthServiceDep,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(50, ge=1, le=100, description="Elementos por página")
) -> CommonResponse:
    """
    Lista todos los usuarios del sistema con paginación.
    
    **Solo administradores** pueden acceder a este endpoint.
    """
    result = auth_service.list_users_paginated(page, size)
    
    return CommonResponse.success(
        message="Usuarios obtenidos exitosamente",
        data={
            "items": [UserResponse.model_validate(user) for user in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "pages": result["pages"]
        }
    )


@router.delete(
    "/users/{user_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Deshabilitar usuario (solo admin)"
)
async def disable_user(
    current_admin: CurrentAdmin,
    auth_service: AuthServiceDep,
    user_id: int = Path(..., ge=1, description="ID del usuario a deshabilitar")
) -> CommonResponse:
    """
    Deshabilita un usuario (borrado lógico).
    
    **Solo administradores** pueden acceder a este endpoint.
    
    - Un administrador NO puede deshabilitarse a sí mismo
    - Un administrador NO puede deshabilitar a otros administradores
    - El usuario mantiene sus datos pero no puede iniciar sesión
    """
    user = auth_service.disable_user(current_admin, user_id)
    
    return CommonResponse.success(
        message=f"Usuario '{user.username}' deshabilitado exitosamente",
        data=UserResponse.model_validate(user)  # Opcional: devolver el usuario deshabilitado
    )

@router.put(
    "/users/{user_id}/enable",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Habilitar usuario (solo admin)"
)
async def enable_user(
    current_admin: CurrentAdmin,
    auth_service: AuthServiceDep,
    user_id: int = Path(..., ge=1)
) -> CommonResponse:
    """Habilita un usuario previamente deshabilitado."""
    user = auth_service.enable_user(current_admin, user_id)
    
    return CommonResponse.success(
        message=f"Usuario '{user.username}' habilitado exitosamente",
        data=UserResponse.model_validate(user)
    )

@router.put(
    "/users/{user_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar usuario (solo admin)"
)
async def update_user(
    request: UserUpdateRequest,
    current_admin: CurrentAdmin,
    auth_service: AuthServiceDep,
    user_id: int = Path(..., ge=1, description="ID del usuario a actualizar"),  
) -> CommonResponse:
    """
    Actualiza los datos de un usuario.
    
    **Solo administradores** pueden acceder a este endpoint.
    
    Campos actualizables:
    - username
    - email
    - full_name
    - is_active
    - is_admin
    - password (opcional, si se envía se actualiza)
    
    Un administrador NO puede modificar:
    - Su propio rol de admin (para evitar autopromoción/democión)
    - El rol de otro admin (solo superadmin podría)
    """
    updated_user = auth_service.update_user(current_admin, user_id, request)
    
    return CommonResponse.success(
        message=f"Usuario '{updated_user.username}' actualizado exitosamente",
        data=UserResponse.model_validate(updated_user)
    )