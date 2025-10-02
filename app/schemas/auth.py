"""
Authentication Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List


class UserRegistrationRequest(BaseModel):
    """Request schema for user registration"""
    email: EmailStr
    password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLoginRequest(BaseModel):
    """Request schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response schema for user data"""
    id: int
    email: str
    organization_id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Response schema for authentication"""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    email: Optional[str] = None
    error: Optional[str] = None
    errors: Optional[List[str]] = None
    message: Optional[str] = None


class TokenResponse(BaseModel):
    """Response schema for token refresh"""
    success: bool
    access_token: Optional[str] = None
    error: Optional[str] = None


class PasswordValidationResponse(BaseModel):
    """Response schema for password validation"""
    valid: bool
    errors: List[str]
