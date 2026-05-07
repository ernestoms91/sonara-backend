# app/services/auth_service.py
from sqlmodel import Session, select
from fastapi import HTTPException, status
from datetime import datetime, timezone
from app.core.security import (
    create_access_token,
    verify_password,
    hash_password
)
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.auth import LoginResponse, UserResponse, UserCreateRequest

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: Session):
        self.session = session
    
    def login(self, username: str, password: str) -> LoginResponse:
        """Lógica de login"""
        # Buscar usuario
        statement = select(User).where(User.username == username)
        user = self.session.exec(statement).first()
        
        # Validar credenciales
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Login fallido: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        if not user.is_active:
            logger.warning(f"Usuario inactivo intenta login: {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario deshabilitado"
            )
        
        # Crear token
        token = create_access_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version,
            is_admin=user.is_admin
        )
        
        logger.info(f"Login exitoso: {user.username}")
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    
    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Cambiar contraseña"""
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta"
            )
        
        user.hashed_password = hash_password(new_password)
        user.password_version += 1
        user.updated_at = datetime.now(timezone.utc)
        
        self.session.add(user)
        self.session.commit()
        
        logger.info(f"Contraseña cambiada para usuario: {user.username}")
    
    def create_user(self, admin_user: User, request: UserCreateRequest) -> User:
        """Crear nuevo usuario (solo admin)"""
        # Verificar username único
        statement = select(User).where(User.username == request.username)
        if self.session.exec(statement).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya existe"
            )
        
        # Verificar email único
        statement = select(User).where(User.email == request.email)
        if self.session.exec(statement).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Crear usuario
        new_user = User(
            username=request.username,
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            is_active=request.is_active,
            is_admin=request.is_admin,
            password_version=0
        )
        
        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
        
        logger.info(f"Usuario creado por admin {admin_user.username}: {new_user.username}")
        
        return new_user
    
    def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Listar usuarios"""
        statement = select(User).offset(skip).limit(limit)
        return self.session.exec(statement).all()
    
    def disable_user(self, admin_user: User, user_id: int) -> User:
        """Deshabilitar usuario"""
        statement = select(User).where(User.id == user_id)
        user = self.session.exec(statement).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes deshabilitarte a ti mismo"
            )
        
        user.is_active = False
        self.session.add(user)
        self.session.commit()
        
        logger.info(f"Usuario {user.username} deshabilitado por admin {admin_user.username}")
        
        return user