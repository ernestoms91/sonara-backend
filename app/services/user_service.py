# app/services/user_service.py
from fastapi import HTTPException, status
from sqlmodel import Session
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.core.logging import get_logger
from app.schemas.user import UserCreate, UserLogin, UserPublic
from app.schemas.token import Token
from app.models.user import User

logger = get_logger(__name__)

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    # ============================================
    # CREATE USER (solo admin)
    # ============================================
    def create_user(self, user_data: UserCreate, created_by_admin: bool = False) -> User:
        """Crear un nuevo usuario (solo admin puede crear admins)"""
        
        # Verificar si ya existe username o email
        if self.user_repo.exists_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_data.username}' already exists"
            )
        
        if self.user_repo.exists_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' already exists"
            )
        
        # Si no es admin, no puede crear usuarios con is_admin=True
        if not created_by_admin and user_data.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can create admin users"
            )
        
        # Hashear password
        hashed_password = hash_password(user_data.password)
        
        # Crear usuario
        user = self.user_repo.create(user_data, hashed_password)
        
        logger.info(f"Usuario creado: {user.username} (admin={user.is_admin}) by admin={created_by_admin}")
        return user
    
    # ============================================
    # LOGIN
    # ============================================
    def login(self, login_data: UserLogin) -> Token:
        """Autenticar usuario y generar token JWT"""
        
        # Buscar usuario por username
        user = self.user_repo.get_by_username(login_data.username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar si está activo
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar password
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Actualizar último login
        self.user_repo.update_last_login(user.id)
        
        # Crear token
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "is_admin": user.is_admin
            }
        )
        
        logger.info(f"Usuario logueado: {user.username}")
        
        return Token(access_token=access_token, token_type="bearer")
    
    # ============================================
    # GET USERS
    # ============================================
    def get_user_by_id(self, user_id: int) -> User:
        """Obtener usuario por ID"""
        user = self.user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        return user
    
    def get_user_by_username(self, username: str) -> User:
        """Obtener usuario por username"""
        user = self.user_repo.get_by_username(username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with username '{username}' not found"
            )
        
        return user
    
    def list_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Listar todos los usuarios"""
        return self.user_repo.list_all(skip, limit)
    
    def list_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Listar usuarios activos"""
        return self.user_repo.list_active(skip, limit)
    
    # ============================================
    # UPDATE USER
    # ============================================
    def update_user(self, user_id: int, update_data: dict, current_user: User) -> User:
        """Actualizar usuario (solo admin o el mismo usuario)"""
        
        user = self.get_user_by_id(user_id)
        
        # Verificar permisos: solo admin o el mismo usuario
        if not current_user.is_admin and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this user"
            )
        
        # Si no es admin, no puede cambiar is_admin
        if not current_user.is_admin and "is_admin" in update_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can change admin status"
            )
        
        # Verificar si username ya existe (si está cambiando)
        if "username" in update_data and update_data["username"] != user.username:
            if self.user_repo.exists_by_username(update_data["username"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Username '{update_data['username']}' already exists"
                )
        
        # Verificar si email ya existe (si está cambiando)
        if "email" in update_data and update_data["email"] != user.email:
            if self.user_repo.exists_by_email(update_data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{update_data['email']}' already exists"
                )
        
        # Actualizar
        updated_user = self.user_repo.update(user, update_data)
        
        logger.info(f"Usuario actualizado: ID={user_id} by user={current_user.username}")
        return updated_user
    
    # ============================================
    # CHANGE PASSWORD
    # ============================================
    def change_password(self, user_id: int, old_password: str, new_password: str, current_user: User) -> User:
        """Cambiar contraseña"""
        
        user = self.get_user_by_id(user_id)
        
        # Verificar permisos: solo admin o el mismo usuario
        if not current_user.is_admin and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to change this user's password"
            )
        
        # Si no es admin, verificar contraseña actual
        if not current_user.is_admin:
            if not verify_password(old_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )
        
        # Hashear nueva contraseña
        new_hashed_password = hash_password(new_password)
        
        # Actualizar
        updated_user = self.user_repo.update_password(user, new_hashed_password)
        
        logger.info(f"Contraseña cambiada: ID={user_id} by user={current_user.username}")
        return updated_user
    
    # ============================================
    # DISABLE / ENABLE USER
    # ============================================
    def disable_user(self, user_id: int, current_user: User) -> User:
        """Deshabilitar usuario (solo admin)"""
        
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can disable users"
            )
        
        user = self.user_repo.disable(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        logger.info(f"Usuario deshabilitado: ID={user_id} by admin={current_user.username}")
        return user
    
    def enable_user(self, user_id: int, current_user: User) -> User:
        """Habilitar usuario (solo admin)"""
        
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can enable users"
            )
        
        user = self.user_repo.enable(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        logger.info(f"Usuario habilitado: ID={user_id} by admin={current_user.username}")
        return user
    
    # ============================================
    # DELETE USER
    # ============================================
    def delete_user(self, user_id: int, current_user: User) -> None:
        """Eliminar usuario (solo admin)"""
        
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can delete users"
            )
        
        user = self.user_repo.delete_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        logger.info(f"Usuario eliminado: ID={user_id} by admin={current_user.username}")
    
    # ============================================
    # STATS
    # ============================================
    def get_stats(self, current_user: User) -> dict:
        """Obtener estadísticas de usuarios (solo admin)"""
        
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can view user stats"
            )
        
        return {
            "total_users": self.user_repo.count_all(),
            "active_users": self.user_repo.count_active(),
            "admin_users": self.user_repo.count_admins()
        }