# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import bcrypt
from app.core.config import settings  # ← importamos tu Settings validado


# ============================================
# JWT usando tu Settings
# ============================================
def create_access_token(
    user_id: int, 
    username: str, 
    password_version: int, 
    is_admin: bool = False
) -> str:
    """
    Crea un token JWT con los datos del usuario.
    """
    payload = {
        "sub": str(user_id),
        "username": username,
        "password_version": password_version,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MIN),
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica y valida un token JWT.
    Retorna el payload si es válido, None si es inválido.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return payload
    except InvalidTokenError:
        return None


def validate_token_and_password_version(token: str, current_password_version: int) -> bool:
    """
    Valida que el token sea válido y que la password_version coincida.
    """
    payload = decode_token(token)
    if not payload:
        return False
    
    if payload.get("type") != "access":
        return False
    
    return payload.get("password_version") == current_password_version


# ============================================
# HASHING DE PASSWORDS
# ============================================
def hash_password(plain_password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash almacenado."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# ============================================
# UTILIDADES ADICIONALES
# ============================================
def get_user_id_from_token(token: str) -> Optional[int]:
    """Extrae el user_id del token sin validar versión."""
    payload = decode_token(token)
    if payload:
        sub = payload.get("sub")
        if sub:
            return int(sub)
    return None


def is_token_expired(token: str) -> bool:
    """Verifica específicamente si el token expiró."""
    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return False
    except ExpiredSignatureError:
        return True
    except InvalidTokenError:
        return True