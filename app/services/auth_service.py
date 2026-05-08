# app/services/auth_service.py
from types import Dict, Any
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
from app.schemas.auth import LoginResponse, UserResponse, UserCreateRequest, UserUpdateRequest
from app.repositories.auth_repository import AuthRepository

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuthRepository(db)
    
    def login(self, username: str, password: str) -> LoginResponse:
        """Lógica de login con verificaciones explícitas"""
        
        # 1. Buscar usuario
        user = self.repo.get_user_by_username(username)
        
        # 2. Verificar existencia (mensaje genérico por seguridad)
        if not user:
            logger.warning(f"Login fallido: usuario no existe - {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        # 3. Verificar contraseña (explícitamente)
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Login fallido: contraseña incorrecta - {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos"
            )
        
        # 4. Verificar si está activo
        if not user.is_active:
            logger.warning(f"Login fallido: usuario inactivo - {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario deshabilitado. Contacte al administrador"
            )
        
        # 5. Crear token y devolver respuesta
        token = create_access_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version,
            is_admin=user.is_admin
        )
        
        logger.info(f"Login exitoso: {user.username} (admin={user.is_admin})")
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    
    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """
        Cambiar contraseña del usuario.
        
        Args:
            user: Usuario autenticado (desde CurrentUser)
            current_password: Contraseña actual
            new_password: Nueva contraseña (ya validada por el schema)
        """
        # 1. Verificar que la contraseña actual es correcta
        if not verify_password(current_password, user.hashed_password):
            logger.warning(f"Intento de cambio de contraseña fallido - contraseña actual incorrecta: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta"
            )
        
        # 2. Verificar que la nueva contraseña no sea igual a la actual
        if verify_password(new_password, user.hashed_password):
            logger.warning(f"Intento de cambio de contraseña fallido - nueva contraseña igual a la actual: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nueva contraseña debe ser diferente a la actual"
            )
        
        # 3. Hashear la nueva contraseña
        new_hashed_password = hash_password(new_password)
        new_version = user.password_version + 1
        
        # 4. Actualizar en base de datos usando repository
        self.repo.update_password(user.id, new_hashed_password, new_version)
        
        # 5. Hacer commit de los cambios
        self.db.commit()
        
        logger.info(f"Contraseña cambiada exitosamente para usuario: {user.username} (nueva versión: {new_version})")


    def create_user(self, admin_user: User, user_data: UserCreateRequest) -> User:
        """
        Crear un nuevo usuario (solo para administradores).
        La lógica de negocio está aquí, las operaciones de BD en repository.
        """
        
        # 1. Validaciones de negocio (no van en repository)
        if admin_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes crear un usuario con tu mismo nombre de usuario"
            )
        
        # 2. Verificar unicidad (usa repository)
        if self.repo.get_user_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El nombre de usuario '{user_data.username}' ya existe"
            )
        
        # 3. Verificar email único (usa repository)
        if self.repo.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El email '{user_data.email}' ya existe"
            )
        
        # 4. Preparar datos para el repository
        hashed_password = hash_password(user_data.password)
        
        new_user_data = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name,
            "is_active": user_data.is_active,
            "is_admin": user_data.is_admin,
            "password_version": 1,
            "created_at": datetime.now(timezone.utc)
        }
        
        # 5. Crear usuario usando repository
        try:
            new_user = self.repo.create_user(new_user_data)
            self.db.commit()  # Service controla el commit
            self.db.refresh(new_user)
            
            logger.info(f"Admin {admin_user.username} creó usuario: {new_user.username}")
            
            return new_user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear usuario: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario en la base de datos"
            )
    
    def list_users_paginated(self, page: int = 1, size: int = 50) -> Dict[str, Any]:
            """
            Listar usuarios con paginación.
            
            Returns:
                Dict con: items, total, page, size, pages
            """
            # Calcular offset
            skip = (page - 1) * size
            
            # Logging de auditoría
            logger.info(f"Admin listando usuarios: page={page}, size={size}")
            
            # Obtener datos del repository
            users, total = self.repo.get_users_paginated(skip, size)
            
            # Calcular total de páginas
            pages = (total + size - 1) // size if total > 0 else 1
            
            logger.info(f"Retornando {len(users)} de {total} usuarios (página {page}/{pages})")
            
            return {
                "items": users,  # Lista de objetos User (SQLModel)
                "total": total,
                "page": page,
                "size": size,
                "pages": pages
            }
    
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
    
    def disable_user(self, admin_user: User, user_id: int) -> User:
        """
        Deshabilitar un usuario (borrado lógico).
        Solo administradores pueden hacer esto.
        
        Args:
            admin_user: Usuario administrador que ejecuta la acción
            user_id: ID del usuario a deshabilitar
            
        Returns:
            Usuario deshabilitado
        """
        # 1. Prevenir auto-deshabilitado
        if admin_user.id == user_id:
            logger.warning(f"Admin {admin_user.username} intentó deshabilitarse a sí mismo")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes deshabilitar tu propio usuario"
            )
        
        # 2. Buscar el usuario
        user = self.repo.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Admin {admin_user.username} intentó deshabilitar usuario inexistente: ID={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # 3. Verificar si ya está deshabilitado
        if not user.is_active:
            logger.warning(f"Admin {admin_user.username} intentó deshabilitar usuario ya inactivo: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario {user.username} ya está deshabilitado"
            )
        
        # 4. Deshabilitar usuario
        try:
            disabled_user = self.repo.disable_user(user_id)
            self.db.commit()
            self.db.refresh(disabled_user)
            
            logger.info(f"Admin {admin_user.username} deshabilitó al usuario: {user.username} (ID={user_id})")
            
            return disabled_user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al deshabilitar usuario {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al deshabilitar el usuario"
            )
    
    def enable_user(self, admin_user: User, user_id: int) -> User:
        """Habilitar un usuario previamente deshabilitado"""
        # Similar a disable_user pero al revés
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if user.is_active:
            raise HTTPException(status_code=400, detail="El usuario ya está habilitado")
        
        enabled_user = self.repo.enable_user(user_id)
        self.db.commit()
        self.db.refresh(enabled_user)
        
        logger.info(f"Admin {admin_user.username} habilitó al usuario: {user.username}")
        
        return enabled_user
    

    def update_user(
        self, 
        admin_user: User, 
        user_id: int, 
        user_data: UserUpdateRequest,
        partial: bool = False
    ) -> User:
        """
        Actualizar datos de un usuario (solo admin).
        
        Args:
            admin_user: Admin que ejecuta la acción
            user_id: ID del usuario a actualizar
            user_data: Datos a actualizar
            partial: Si es True, solo actualiza campos no-None
        """
        # 1. Verificar que no se actualice a sí mismo con cambios críticos
        if admin_user.id == user_id:
            # No puede cambiar su propio rol ni deshabilitarse
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
        
        # 2. Buscar el usuario a actualizar
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # 3. Verificar si el admin intenta modificar a otro admin
        if user.is_admin and admin_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar a otro administrador"
            )
        
        # 4. Validar username único (si se está cambiando)
        if user_data.username and user_data.username != user.username:
            existing = self.repo.get_user_by_username(user_data.username)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El username '{user_data.username}' ya está en uso"
                )
        
        # 5. Validar email único (si se está cambiando)
        if user_data.email and user_data.email != user.email:
            existing = self.repo.get_user_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El email '{user_data.email}' ya está en uso"
                )
        
        # 6. Actualizar campos
        try:
            if user_data.username is not None:
                user.username = user_data.username
            
            if user_data.email is not None:
                user.email = user_data.email
            
            if user_data.full_name is not None:
                user.full_name = user_data.full_name
            
            if user_data.is_active is not None:
                user.is_active = user_data.is_active
            
            if user_data.is_admin is not None:
                # Solo permitir cambiar rol si no es el mismo admin
                if admin_user.id != user_id:
                    user.is_admin = user_data.is_admin
                    logger.warning(f"Admin {admin_user.username} cambió rol de {user.username} a admin={user_data.is_admin}")
            
            if user_data.password:
                user.hashed_password = hash_password(user_data.password)
                user.password_version += 1  # Invalida tokens existentes
                logger.info(f"Admin {admin_user.username} cambió contraseña de {user.username}")
            
            user.updated_at = datetime.now(timezone.utc)
            
            # Guardar cambios
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Admin {admin_user.username} actualizó usuario: {user.username}")
            
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar usuario {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar el usuario"
            )