# app/repositories/auth_repository.py
from sqlmodel import Session, select
from typing import Optional, List, Tuple
from sqlalchemy import func
from app.models.user import User
from typing import Optional
from datetime import datetime, timezone


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Obtener usuario por nombre de usuario"""
        statement = select(User).where(User.username == username)
        return self.db.exec(statement).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        statement = select(User).where(User.email == email)
        return self.db.exec(statement).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtener usuario por ID"""
        statement = select(User).where(User.id == user_id)
        return self.db.exec(statement).first()
    
    def create_user(self, user_data: dict) -> User:
        """Crear un nuevo usuario en BD"""
        user = User(**user_data)
        self.db.add(user)
        self.db.flush()  # Para obtener el ID sin commit
        return user
    
    def update_password(self, user_id: int, new_hashed_password: str, new_version: int) -> User:
        """Actualizar contraseña del usuario"""
        user = self.get_user_by_id(user_id)
        if user:
            user.hashed_password = new_hashed_password
            user.password_version = new_version
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
        return user
    
    def user_exists(self, username: str = None, email: str = None) -> bool:
        """Verificar si existe usuario por username o email"""
        if username and self.get_user_by_username(username):
            return True
        if email and self.get_user_by_email(email):
            return True
        return False
    
    def get_users_paginated(self, skip: int, limit: int) -> Tuple[List[User], int]:
        """
        Obtener usuarios paginados.
        
        Returns:
            Tuple: (lista_de_usuarios, total_de_usuarios)
        """
        # Contar total
        count_statement = select(func.count()).select_from(User)
        total = self.db.exec(count_statement).one()
        
        # Obtener usuarios paginados
        statement = select(User).offset(skip).limit(limit).order_by(User.id)
        users = self.db.exec(statement).all()
        
        return users, total
    
    def disable_user(self, user_id: int) -> Optional[User]:
        """
        Deshabilitar usuario (borrado lógico).
        Retorna el usuario deshabilitado o None si no existe.
        """
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
        return user
    
    def enable_user(self, user_id: int) -> Optional[User]:
        """Habilitar usuario (reactivar)"""
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
        return user