# app/services/user_service.py
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Dict, Any
from app.core.security import hash_password
from app.core.logging import get_logger
from app.models.user_model import User
from app.schemas.auth import UserCreateRequest, UserUpdateRequest
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class UserService:
    def __init__(self, db):
        self.db = db
        self.repo = UserRepository(db)
    
    def create_user(self, admin_user: User, user_data: UserCreateRequest) -> User:
        if self.repo.exists_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El username '{user_data.username}' ya existe"
            )
        
        if self.repo.exists_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El email '{user_data.email}' ya existe"
            )
        
        new_user_data = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hash_password(user_data.password),
            "full_name": user_data.full_name,
            "is_active": user_data.is_active,
            "is_admin": user_data.is_admin,
            "password_version": 1,
            "created_at": datetime.now(timezone.utc)
        }
        
        new_user = self.repo.create(new_user_data)
        self.db.commit()
        self.db.refresh(new_user)
        
        logger.info(f"Admin {admin_user.username} creó usuario: {new_user.username}")
        return new_user
    
    def list_users_paginated(self, page: int = 1, size: int = 50) -> Dict[str, Any]:
        skip = (page - 1) * size
        users, total = self.repo.get_users_paginated(skip, size)
        pages = (total + size - 1) // size if total > 0 else 1
        
        return {
            "items": users,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    
    def disable_user(self, admin_user: User, user_id: int) -> User:
        if admin_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes deshabilitar tu propio usuario"
            )
        
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario {user.username} ya está deshabilitado"
            )
        
        disabled_user = self.repo.disable(user_id)
        self.db.commit()
        self.db.refresh(disabled_user)
        
        logger.info(f"Admin {admin_user.username} deshabilitó a: {user.username}")
        return disabled_user
    
    def enable_user(self, admin_user: User, user_id: int) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario {user.username} ya está habilitado"
            )
        
        enabled_user = self.repo.enable(user_id)
        self.db.commit()
        self.db.refresh(enabled_user)
        
        logger.info(f"Admin {admin_user.username} habilitó a: {user.username}")
        return enabled_user
    
    def update_user(self, admin_user: User, user_id: int, user_data: UserUpdateRequest) -> User:
        # Prevenir auto-modificación crítica
        if admin_user.id == user_id:
            if user_data.is_admin is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes cambiar tu propio rol de administrador"
                )
            if user_data.is_active is not None and not user_data.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes deshabilitar tu propio usuario"
                )
        
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # No modificar a otro admin
        if user.is_admin and admin_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar a otro administrador"
            )
        
        # Validar username único
        if user_data.username and user_data.username != user.username:
            if self.repo.exists_by_username(user_data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El username '{user_data.username}' ya está en uso"
                )
        
        # Validar email único
        if user_data.email and user_data.email != user.email:
            if self.repo.exists_by_email(user_data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El email '{user_data.email}' ya está en uso"
                )
        
        # Preparar datos para actualizar
        update_data = {}
        if user_data.username is not None:
            update_data["username"] = user_data.username
        if user_data.email is not None:
            update_data["email"] = user_data.email
        if user_data.full_name is not None:
            update_data["full_name"] = user_data.full_name
        if user_data.is_active is not None:
            update_data["is_active"] = user_data.is_active
        if user_data.is_admin is not None and admin_user.id != user_id:
            update_data["is_admin"] = user_data.is_admin
            logger.warning(f"Admin {admin_user.username} cambió rol de {user.username}")
        if user_data.password:
            update_data["hashed_password"] = hash_password(user_data.password)
            update_data["password_version"] = user.password_version + 1
            logger.info(f"Admin {admin_user.username} cambió contraseña de {user.username}")
        
        if update_data:
            updated_user = self.repo.update(user, update_data)
            self.db.commit()
            self.db.refresh(updated_user)
            logger.info(f"Admin {admin_user.username} actualizó usuario: {user.username}")
            return updated_user
        
        return user