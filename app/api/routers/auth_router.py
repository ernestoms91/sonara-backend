# app/api/routers/auth_router.py
from fastapi import APIRouter, status
from app.api.deps.auth import CurrentUser
from app.api.deps.services import AuthServiceDep
from app.schemas.common import CommonResponse
from app.schemas.auth import LoginRequest, ChangePasswordRequest, UserResponse, RefreshTokenRequest

router = APIRouter(prefix="/auth", tags=["AUTHENTICATION"])


@router.post(
    "/login",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión"
)
async def login(
    auth_service: AuthServiceDep,
    login_data: LoginRequest
) -> CommonResponse:
    """Autentica un usuario y devuelve access_token y refresh_token."""
    result = auth_service.login(login_data.username, login_data.password)
    return CommonResponse.success(message="Login exitoso", data=result)


@router.post(
    "/refresh",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Refrescar token de acceso"
)
async def refresh_access_token(
    auth_service: AuthServiceDep,
    request: RefreshTokenRequest
) -> CommonResponse:
    """
    Genera un nuevo access_token usando un refresh_token válido.
    """
    result = auth_service.refresh_token(request.refresh_token)
    return CommonResponse.success(
        message="Token refrescado exitosamente",
        data=result
    )


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