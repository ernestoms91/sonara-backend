# app/services/auth_service.py
from fastapi import HTTPException, status
from app.core.security import (
    create_access_token,
    create_refresh_token,
    refresh_access_token as refresh_access_token_util,
    verify_password,
    hash_password
)
from app.core.logging import get_logger
from app.models.user_model import User
from app.schemas.auth import LoginResponse, UserResponse, RefreshTokenResponse
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db):
        self.db = db
        self.repo = UserRepository(db)
    
    def login(self, username: str, password: str) -> LoginResponse:
        user = self.repo.get_by_username(username)
        
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Login fallido: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        if not user.is_active:
            logger.warning(f"Login fallido: usuario inactivo - {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario deshabilitado. Contacte al administrador"
            )
        
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version,
            is_admin=user.is_admin
        )
        
        refresh_token = create_refresh_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version
        )
        
        logger.info(f"Login exitoso: {user.username}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    
    def refresh_token(self, refresh_token: str) -> RefreshTokenResponse:
        """
        Valida refresh_token y genera un nuevo access_token.
        """
        new_access_token = refresh_access_token_util(refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado"
            )
        
        return RefreshTokenResponse(
            access_token=new_access_token,
            token_type="bearer"
        )
    
    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta"
            )
        
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nueva contraseña debe ser diferente a la actual"
            )
        
        new_hashed_password = hash_password(new_password)
        new_version = user.password_version + 1
        
        self.repo.update_password(user.id, new_hashed_password, new_version)
        self.db.commit()
        
        logger.info(f"Contraseña cambiada para: {user.username}")