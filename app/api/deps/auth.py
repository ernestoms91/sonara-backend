# app/api/deps/auth.py
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from app.api.deps.db import DBSession
from app.models.user import User
from app.core.security import decode_token, validate_token_and_password_version

security = HTTPBearer(auto_error=False)

Credentials = Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]


async def get_current_user(
    session: DBSession,  
    credentials: Credentials,
) -> Optional[User]:
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    statement = select(User).where(User.id == int(user_id))
    user = session.exec(statement).first()
    
    if not user:
        return None
    
    if not validate_token_and_password_version(token, user.password_version):
        return None
    
    return user


async def get_current_active_user(
    current_user: Annotated[Optional[User], Depends(get_current_user)]
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


# Type aliases
CurrentUser = Annotated[User, Depends(get_current_active_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]
OptionalUser = Annotated[Optional[User], Depends(get_current_user)]