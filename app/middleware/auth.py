"""
Authentication middleware for JWT token validation
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth import AuthService
from app.models.auth import User

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    Raises HTTPException if authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        user = AuthService.get_current_user(db, token)
        if user is None:
            raise credentials_exception
        return user
    except Exception:
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user
    Raises HTTPException if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_authentication():
    """
    Decorator factory for requiring authentication on endpoints
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This will be handled by FastAPI's dependency injection
            # when the endpoint uses get_current_user as a dependency
            return await func(*args, **kwargs)
        return wrapper
    return decorator
