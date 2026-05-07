# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


# ============================================
# VALIDACIÓN DE CONTRASEÑA (centralizada)
# ============================================
def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Mínimo 8 caracteres")
    if not any(c.isupper() for c in v):
        raise ValueError("Al menos una mayúscula")
    if not any(c.islower() for c in v):
        raise ValueError("Al menos una minúscula")
    if not any(c.isdigit() for c in v):
        raise ValueError("Al menos un número")
    if not any(c in "!@#$%^&*" for c in v):
        raise ValueError("Al menos un carácter especial (!@#$%^&*)")
    return v


# ============================================
# REQUEST SCHEMAS
# ============================================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    
    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)
    
    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.lower()


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)
    
    @field_validator("password")
    @classmethod
    def check_password(cls, v: Optional[str]) -> Optional[str]:
        return validate_password(v) if v else v


# ============================================
# RESPONSE SCHEMAS
# ============================================
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse