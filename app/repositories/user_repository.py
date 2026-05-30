# app/repositories/user_repository.py
from sqlmodel import Session, select
from typing import List, Optional
from app.models.user import User
from app.core.logging import get_logger
from app.schemas.auth import UserCreate

logger = get_logger(__name__)

class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # LIST USERS
    # ============================================
    def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Listar todos los usuarios con paginación"""
        query = select(User).order_by(User.username.asc()).offset(skip).limit(limit)
        return self.db.exec(query).all()
    
    def list_active(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Listar solo usuarios activos"""
        query = select(User).where(User.is_active == True).order_by(User.username.asc()).offset(skip).limit(limit)
        return self.db.exec(query).all()
    
    def list_admins(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Listar solo administradores"""
        query = select(User).where(User.is_admin == True).order_by(User.username.asc()).offset(skip).limit(limit)
        return self.db.exec(query).all()
    
    # ============================================
    # GET SINGLE USER
    # ============================================
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Obtener usuario por ID"""
        return self.db.get(User, user_id)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Obtener usuario por username"""
        query = select(User).where(User.username == username)
        return self.db.exec(query).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        query = select(User).where(User.email == email)
        return self.db.exec(query).first()
    
    def get_by_username_or_email(self, username: str, email: str) -> Optional[User]:
        """Obtener usuario por username o email"""
        query = select(User).where(
            (User.username == username) | (User.email == email)
        )
        return self.db.exec(query).first()
    
    # ============================================
    # CREATE USER
    # ============================================
    def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """Guardar un usuario en la base de datos"""
        from datetime import datetime, timezone
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_admin=user_data.is_admin,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Usuario creado: ID={user.id}, username={user.username}")
        return user
    
    # ============================================
    # UPDATE USER
    # ============================================
    def update(self, user: User, update_data: dict) -> User:
        """Actualizar un usuario existente"""
        from datetime import datetime, timezone
        
        for key, value in update_data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Usuario actualizado: ID={user.id}")
        return user
    
    def update_password(self, user: User, new_hashed_password: str) -> User:
        """Actualizar solo la contraseña"""
        user.hashed_password = new_hashed_password
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Contraseña actualizada: ID={user.id}")
        return user
    
    # ============================================
    # DISABLE / ENABLE USER
    # ============================================
    def disable(self, user_id: int) -> Optional[User]:
        """Deshabilitar un usuario (is_active = False)"""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Usuario deshabilitado: ID={user_id}")
        return user
    
    def enable(self, user_id: int) -> Optional[User]:
        """Habilitar un usuario (is_active = True)"""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Usuario habilitado: ID={user_id}")
        return user
    
    # ============================================
    # DELETE USER
    # ============================================
    def delete(self, user: User) -> None:
        """Eliminar un usuario"""
        self.db.delete(user)
        self.db.commit()
        logger.info(f"Usuario eliminado: ID={user.id}, username={user.username}")
    
    def delete_by_id(self, user_id: int) -> Optional[User]:
        """Eliminar un usuario por ID"""
        user = self.get_by_id(user_id)
        if user:
            self.delete(user)
        return user
    
    # ============================================
    # COUNT METHODS
    # ============================================
    def count_all(self) -> int:
        """Contar total de usuarios"""
        query = select(User)
        return len(self.db.exec(query).all())
    
    def count_active(self) -> int:
        """Contar usuarios activos"""
        query = select(User).where(User.is_active == True)
        return len(self.db.exec(query).all())
    
    def count_admins(self) -> int:
        """Contar administradores"""
        query = select(User).where(User.is_admin == True)
        return len(self.db.exec(query).all())
    
    # ============================================
    # EXISTS METHODS
    # ============================================
    def exists_by_username(self, username: str) -> bool:
        """Verificar si existe un usuario con ese username"""
        return self.get_by_username(username) is not None
    
    def exists_by_email(self, email: str) -> bool:
        """Verificar si existe un usuario con ese email"""
        return self.get_by_email(email) is not None
    
    # ============================================
    # LOGIN / AUTH METHODS
    # ============================================
    def update_last_login(self, user_id: int) -> Optional[User]:
        """Actualizar timestamp de último login"""
        from datetime import datetime, timezone
        
        user = self.get_by_id(user_id)
        if user:
            user.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(user)
        return user