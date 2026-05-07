# app/api/routers/auth_router.py
from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps.auth import CurrentUser, CurrentAdmin
from app.api.deps.services import AuthServiceDep
from app.core.logging import get_logger
from app.schemas.common import CommonResponse
from app.schemas.auth import ChangePasswordRequest, UserCreateRequest, UserResponse

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
    form_data: OAuth2PasswordRequestForm = Depends()
) -> CommonResponse:
    """Login con username y password."""
    result = auth_service.login(form_data.username, form_data.password)
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
    skip: int = 0,
    limit: int = 100
) -> CommonResponse:
    """Lista todos los usuarios. Solo administradores."""
    users = auth_service.list_users(skip, limit)
    return CommonResponse.success(
        message="Usuarios obtenidos",
        data=[UserResponse.model_validate(user) for user in users]
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
    user_id: int
) -> CommonResponse:
    """Deshabilita un usuario. Solo administradores."""
    user = auth_service.disable_user(current_admin, user_id)
    return CommonResponse.success(
        message=f"Usuario {user.username} deshabilitado"
    )