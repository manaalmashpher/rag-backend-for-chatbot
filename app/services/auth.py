"""
Authentication services for password hashing and validation
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.auth import User, Organization


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordService:
    """Service for password hashing and validation"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength requirements
        Returns dict with 'valid' boolean and 'errors' list
        """
        errors = []
        
        if len(password) < settings.password_min_length:
            errors.append(f"Password must be at least {settings.password_min_length} characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class JWTService:
    """Service for JWT token management"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None


class AuthService:
    """Main authentication service"""
    
    @staticmethod
    def create_organization(db: Session, name: str) -> Organization:
        """Create a new organization"""
        organization = Organization(name=name)
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return organization
    
    @staticmethod
    def get_or_create_default_organization(db: Session) -> Organization:
        """Get or create the default organization for single-tenant setup"""
        organization = db.query(Organization).first()
        if not organization:
            organization = AuthService.create_organization(db, "Default Organization")
        return organization
    
    @staticmethod
    def create_user(db: Session, email: str, password: str, organization_id: int) -> User:
        """Create a new user with hashed password"""
        password_hash = PasswordService.hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            organization_id=organization_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = AuthService.get_user_by_email(db, email)
        if not user:
            return None
        if not PasswordService.verify_password(password, user.password_hash):
            return None
        return user
    
    @staticmethod
    def register_user(db: Session, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        # Check if user already exists
        existing_user = AuthService.get_user_by_email(db, email)
        if existing_user:
            return {"success": False, "error": "User with this email already exists"}
        
        # Validate password strength
        password_validation = PasswordService.validate_password_strength(password)
        if not password_validation["valid"]:
            return {"success": False, "error": "Password validation failed", "errors": password_validation["errors"]}
        
        # Get or create default organization
        organization = AuthService.get_or_create_default_organization(db)
        
        # Create user
        user = AuthService.create_user(db, email, password, organization.id)
        
        return {
            "success": True,
            "user_id": user.id,
            "organization_id": user.organization_id,
            "email": user.email
        }
    
    @staticmethod
    def login_user(db: Session, email: str, password: str) -> Dict[str, Any]:
        """Login user and return tokens"""
        user = AuthService.authenticate_user(db, email, password)
        if not user:
            return {"success": False, "error": "Invalid email or password"}
        
        if not user.is_active:
            return {"success": False, "error": "User account is disabled"}
        
        # Create tokens
        access_token = JWTService.create_access_token({
            "user_id": user.id,
            "email": user.email,
            "organization_id": user.organization_id
        })
        
        refresh_token = JWTService.create_refresh_token({
            "user_id": user.id,
            "email": user.email,
            "organization_id": user.organization_id
        })
        
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user.id,
            "organization_id": user.organization_id,
            "email": user.email
        }
    
    @staticmethod
    def get_current_user(db: Session, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        payload = JWTService.verify_token(token, "access")
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        return db.query(User).filter(User.id == user_id).first()
