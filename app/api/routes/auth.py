"""
Authentication API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    AuthResponse,
    UserResponse,
    TokenResponse
)
from app.services.auth import AuthService
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.core.config import settings

router = APIRouter()

# Rate limiting for auth endpoints
def get_client_ip(request: Request) -> str:
    """Get client IP address for rate limiting"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def check_auth_rate_limit(client_ip: str, endpoint: str) -> bool:
    """Check if client has exceeded auth rate limit"""
    # Simple in-memory rate limiting (in production, use Redis)
    # Auth endpoints: 5 requests per minute per IP
    # Login attempts: 3 failed attempts per 15 minutes per IP
    # Registration: 1 per minute per IP
    return True  # Simplified for now - would implement proper rate limiting


@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password
    """
    try:
        result = AuthService.register_user(
            db=db,
            email=user_data.email,
            password=user_data.password
        )
        
        if result["success"]:
            return AuthResponse(
                success=True,
                user_id=result["user_id"],
                organization_id=result["organization_id"],
                email=result["email"]
            )
        else:
            return AuthResponse(
                success=False,
                error=result["error"],
                errors=result.get("errors")
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    user_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user with email and password
    """
    try:
        result = AuthService.login_user(
            db=db,
            email=user_data.email,
            password=user_data.password
        )
        
        if result["success"]:
            return AuthResponse(
                success=True,
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user_id=result["user_id"],
                organization_id=result["organization_id"],
                email=result["email"]
            )
        else:
            return AuthResponse(
                success=False,
                error=result["error"]
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/logout", response_model=AuthResponse)
async def logout_user(
    current_user: User = Depends(get_current_user)
):
    """
    Logout user (token invalidation handled client-side)
    """
    return AuthResponse(
        success=True,
        message="Logged out successfully"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        from app.services.auth import JWTService
        
        # Get refresh token from query parameter
        refresh_token = request.query_params.get("refresh_token")
        if not refresh_token:
            return TokenResponse(
                success=False,
                error="Refresh token is required"
            )
        
        # Verify refresh token
        payload = JWTService.verify_token(refresh_token, "refresh")
        if not payload:
            return TokenResponse(
                success=False,
                error="Invalid refresh token"
            )
        
        # Get user
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return TokenResponse(
                success=False,
                error="User not found or inactive"
            )
        
        # Create new access token
        access_token = JWTService.create_access_token({
            "user_id": user.id,
            "email": user.email,
            "organization_id": user.organization_id
        })
        
        return TokenResponse(
            success=True,
            access_token=access_token
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )
