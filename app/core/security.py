# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings
from app.schemas.token import TokenData

# Configuración de hashing de contraseñas
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# ============================================
# PASSWORD HASHING
# ============================================

def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Contraseña hasheada
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña almacenado
        
    Returns:
        True si coinciden, False en caso contrario
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================
# JWT TOKEN MANAGEMENT
# ============================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT de acceso.
    
    Args:
        data: Datos a incluir en el token (sub, user_id, is_admin, etc.)
        expires_delta: Tiempo de expiración personalizado (opcional)
        
    Returns:
        Token JWT como string
    """
    to_encode = data.copy()
    
    # Configurar tiempo de expiración
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRES_MIN  # Usando tu variable JWT_EXPIRES_MIN
        )
    
    to_encode.update({"exp": expire})
    
    # Generar token usando tus variables
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,  # Usando JWT_SECRET
        algorithm=settings.JWT_ALG  # Usando JWT_ALG
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decodifica y valida un token JWT.
    
    Args:
        token: Token JWT a decodificar
        
    Returns:
        TokenData si es válido, None en caso contrario
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,  # Usando JWT_SECRET
            algorithms=[settings.JWT_ALG]  # Usando JWT_ALG
        )
        
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        is_admin: bool = payload.get("is_admin", False)
        
        if username is None or user_id is None:
            return None
        
        return TokenData(
            username=username,
            user_id=user_id,
            is_admin=is_admin
        )
        
    except JWTError:
        return None


def verify_token(token: str) -> TokenData:
    """
    Verifica un token JWT y lanza excepción si es inválido.
    
    Args:
        token: Token JWT a verificar
        
    Returns:
        TokenData si es válido
        
    Raises:
        HTTPException: Si el token es inválido o expiró
    """
    token_data = decode_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


def refresh_access_token(refresh_token: str) -> str:
    """
    Genera un nuevo access token a partir de un refresh token.
    
    Args:
        refresh_token: Token de refresco
        
    Returns:
        Nuevo access token
    """
    token_data = verify_token(refresh_token)
    
    # Crear nuevo token con los mismos datos
    new_token = create_access_token(
        data={
            "sub": token_data.username,
            "user_id": token_data.user_id,
            "is_admin": token_data.is_admin
        }
    )
    
    return new_token


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_token_expiration() -> datetime:
    """
    Retorna la fecha/hora de expiración para un nuevo token.
    """
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRES_MIN
    )


def is_token_expired(token: str) -> bool:
    """
    Verifica si un token ya expiró.
    
    Args:
        token: Token JWT a verificar
        
    Returns:
        True si expiró, False en caso contrario
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALG],
            options={"verify_exp": True}
        )
        return False
    except jwt.ExpiredSignatureError:
        return True
    except JWTError:
        return True


# ============================================
# VALIDATE SYSTEM CONFIG
# ============================================

def validate_jwt_config() -> bool:
    """
    Valida que la configuración JWT sea correcta.
    
    Returns:
        True si es válida, False en caso contrario
    """
    try:
        # Probar crear y verificar un token
        test_data = {"sub": "test", "user_id": 1, "is_admin": False}
        token = create_access_token(test_data, expires_delta=timedelta(minutes=1))
        decoded = decode_token(token)
        
        if decoded and decoded.username == "test" and decoded.user_id == 1:
            return True
        return False
    except Exception:
        return False