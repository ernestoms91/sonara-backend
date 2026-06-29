# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import bcrypt
from app.core.config import settings

# ============================================
# JWT - ACCESS TOKEN
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
# JWT - REFRESH TOKEN
# ============================================
def create_refresh_token(user_id: int, username: str, password_version: int) -> str:
    """
    Crea un refresh token con expiración larga.
    """
    payload = {
        "sub": str(user_id),
        "username": username,
        "password_version": password_version,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def validate_refresh_token(token: str, current_password_version: int) -> bool:
    """
    Valida un refresh token.
    """
    payload = decode_token(token)
    if not payload:
        return False
    
    if payload.get("type") != "refresh":
        return False
    
    return payload.get("password_version") == current_password_version


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    Genera un nuevo access token a partir de un refresh token válido.
    """
    payload = decode_token(refresh_token)
    
    if not payload:
        return None
    
    if payload.get("type") != "refresh":
        return None
    
    user_id = payload.get("sub")
    username = payload.get("username")
    password_version = payload.get("password_version")
    is_admin = payload.get("is_admin", False)
    
    if not user_id or not username:
        return None
    
    return create_access_token(
        user_id=int(user_id),
        username=username,
        password_version=password_version,
        is_admin=is_admin
    )


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