# app/api/routers/users_router.py
from fastapi import APIRouter, status, Query, Path
from app.api.deps.auth import CurrentAdmin
from app.api.deps.services import UserServiceDep
from app.schemas.common import CommonResponse
from app.schemas.auth import UserCreateRequest, UserUpdateRequest, UserResponse

router = APIRouter(prefix="/user", tags=["USER"])


@router.post(
    "/",
    response_model=CommonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario (solo admin)"
)
async def create_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    request: UserCreateRequest
) -> CommonResponse:
    new_user = user_service.create_user(current_admin, request)
    return CommonResponse.success(
        message="Usuario creado exitosamente",
        data=UserResponse.model_validate(new_user)
    )


@router.get(
    "/",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios (solo admin)"
)
async def list_users(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> CommonResponse:
    result = user_service.list_users_paginated(page, size)
    return CommonResponse.success(
        message="Usuarios obtenidos exitosamente",
        data={
            "items": [UserResponse.model_validate(u) for u in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "pages": result["pages"]
        }
    )


@router.delete(
    "/{user_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Deshabilitar usuario (solo admin)"
)
async def disable_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    user_id: int = Path(..., ge=1)
) -> CommonResponse:
    user = user_service.disable_user(current_admin, user_id)
    return CommonResponse.success(
        message=f"Usuario '{user.username}' deshabilitado exitosamente",
        data=UserResponse.model_validate(user)
    )


@router.put(
    "/{user_id}/enable",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Habilitar usuario (solo admin)"
)
async def enable_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    user_id: int = Path(..., ge=1)
) -> CommonResponse:
    user = user_service.enable_user(current_admin, user_id)
    return CommonResponse.success(
        message=f"Usuario '{user.username}' habilitado exitosamente",
        data=UserResponse.model_validate(user)
    )


@router.put(
    "/{user_id}",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar usuario (solo admin)"
)
async def update_user(
    request: UserUpdateRequest,
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    user_id: int = Path(..., ge=1)
) -> CommonResponse:
    updated_user = user_service.update_user(current_admin, user_id, request)
    return CommonResponse.success(
        message=f"Usuario '{updated_user.username}' actualizado exitosamente",
        data=UserResponse.model_validate(updated_user)
    )