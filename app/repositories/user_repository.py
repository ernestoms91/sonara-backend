# app/repositories/user_repository.py
from sqlmodel import Session, select
from typing import Optional, List, Tuple
from sqlalchemy import func
from datetime import datetime, timezone
from app.models.user_model import User
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # GET BY FIELD
    # ============================================
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)
    
    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.exec(select(User).where(User.username == username)).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.exec(select(User).where(User.email == email)).first()
    
    # ============================================
    # LIST USERS
    # ============================================
    def get_users_paginated(self, skip: int, limit: int) -> Tuple[List[User], int]:
        total = self.db.exec(select(func.count()).select_from(User)).one()
        users = self.db.exec(select(User).offset(skip).limit(limit).order_by(User.id)).all()
        return users, total
    
    # ============================================
    # CREATE
    # ============================================
    def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.db.add(user)
        self.db.flush()
        return user
    
    # ============================================
    # UPDATE
    # ============================================
    def update_password(self, user_id: int, new_hashed_password: str, new_version: int) -> User:
        user = self.get_by_id(user_id)
        if user:
            user.hashed_password = new_hashed_password
            user.password_version = new_version
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
        return user
    
    def update(self, user: User, update_data: dict) -> User:
        for key, value in update_data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        user.updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
    
    # ============================================
    # DISABLE / ENABLE
    # ============================================
    def disable(self, user_id: int) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        return user
    
    def enable(self, user_id: int) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        return user
    
    # ============================================
    # EXISTENCE CHECKS
    # ============================================
    def exists_by_username(self, username: str) -> bool:
        return self.get_by_username(username) is not None
    
    def exists_by_email(self, email: str) -> bool:
        return self.get_by_email(email) is not None
    
    # ============================================
    # COUNTS
    # ============================================
    def count_all(self) -> int:
        return self.db.exec(select(func.count()).select_from(User)).one()