# app/models/user.py
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    username: str = Field(max_length=50, unique=True, index=True, nullable=False)
    email: str = Field(max_length=100, unique=True, index=True, nullable=False)
    hashed_password: str = Field(max_length=255, nullable=False)
    full_name: Optional[str] = Field(default=None, max_length=100)
    
    # Control de usuario
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    
    # Timestamps - versión timezone-aware
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))