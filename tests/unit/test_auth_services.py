"""
Unit tests for authentication services
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.auth import User, Organization
from app.services.auth import PasswordService, JWTService, AuthService


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestPasswordService:
    """Test password hashing and validation"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = PasswordService.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt format
    
    def test_verify_password(self):
        """Test password verification"""
        password = "testpassword123"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(password, hashed) is True
        assert PasswordService.verify_password("wrongpassword", hashed) is False
    
    def test_validate_password_strength(self):
        """Test password strength validation"""
        # Valid password
        valid_password = "TestPassword123!"
        result = PasswordService.validate_password_strength(valid_password)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid passwords
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
        ]
        
        for weak_password in weak_passwords:
            result = PasswordService.validate_password_strength(weak_password)
            assert result["valid"] is False
            assert len(result["errors"]) > 0


class TestJWTService:
    """Test JWT token management"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = JWTService.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = JWTService.create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self):
        """Test token verification"""
        data = {"user_id": 1, "email": "test@example.com"}
        token = JWTService.create_access_token(data)
        
        # Verify valid token
        payload = JWTService.verify_token(token, "access")
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        
        # Verify invalid token
        invalid_payload = JWTService.verify_token("invalid_token", "access")
        assert invalid_payload is None
    
    def test_verify_token_wrong_type(self):
        """Test token verification with wrong type"""
        data = {"user_id": 1, "email": "test@example.com"}
        access_token = JWTService.create_access_token(data)
        refresh_token = JWTService.create_refresh_token(data)
        
        # Try to verify access token as refresh token
        payload = JWTService.verify_token(access_token, "refresh")
        assert payload is None
        
        # Try to verify refresh token as access token
        payload = JWTService.verify_token(refresh_token, "access")
        assert payload is None


class TestAuthService:
    """Test authentication service"""
    
    def test_create_organization(self, db_session):
        """Test creating an organization"""
        org = AuthService.create_organization(db_session, "Test Organization")
        
        assert org.id is not None
        assert org.name == "Test Organization"
        
        # Verify it's in the database
        db_org = db_session.query(Organization).filter(Organization.id == org.id).first()
        assert db_org is not None
        assert db_org.name == "Test Organization"
    
    def test_get_or_create_default_organization(self, db_session):
        """Test getting or creating default organization"""
        # First call should create organization
        org1 = AuthService.get_or_create_default_organization(db_session)
        assert org1.id is not None
        assert org1.name == "Default Organization"
        
        # Second call should return same organization
        org2 = AuthService.get_or_create_default_organization(db_session)
        assert org2.id == org1.id
        assert org2.name == org1.name
    
    def test_create_user(self, db_session):
        """Test creating a user"""
        # Create organization first
        org = AuthService.create_organization(db_session, "Test Organization")
        
        user = AuthService.create_user(
            db_session, 
            "test@example.com", 
            "testpassword123", 
            org.id
        )
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.organization_id == org.id
        assert user.password_hash is not None
        assert user.password_hash != "testpassword123"  # Should be hashed
    
    def test_get_user_by_email(self, db_session):
        """Test getting user by email"""
        # Create organization and user
        org = AuthService.create_organization(db_session, "Test Organization")
        user = AuthService.create_user(
            db_session, 
            "test@example.com", 
            "testpassword123", 
            org.id
        )
        
        # Test getting existing user
        found_user = AuthService.get_user_by_email(db_session, "test@example.com")
        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == "test@example.com"
        
        # Test getting non-existing user
        not_found = AuthService.get_user_by_email(db_session, "nonexistent@example.com")
        assert not_found is None
    
    def test_authenticate_user(self, db_session):
        """Test user authentication"""
        # Create organization and user
        org = AuthService.create_organization(db_session, "Test Organization")
        user = AuthService.create_user(
            db_session, 
            "test@example.com", 
            "testpassword123", 
            org.id
        )
        
        # Test valid authentication
        auth_user = AuthService.authenticate_user(
            db_session, 
            "test@example.com", 
            "testpassword123"
        )
        assert auth_user is not None
        assert auth_user.id == user.id
        
        # Test invalid email
        auth_user = AuthService.authenticate_user(
            db_session, 
            "wrong@example.com", 
            "testpassword123"
        )
        assert auth_user is None
        
        # Test invalid password
        auth_user = AuthService.authenticate_user(
            db_session, 
            "test@example.com", 
            "wrongpassword"
        )
        assert auth_user is None
    
    def test_register_user_success(self, db_session):
        """Test successful user registration"""
        result = AuthService.register_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        assert result["success"] is True
        assert result["user_id"] is not None
        assert result["organization_id"] is not None
        assert result["email"] == "test@example.com"
        
        # Verify user was created
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert user is not None
        assert user.email == "test@example.com"
    
    def test_register_user_duplicate_email(self, db_session):
        """Test registration with duplicate email"""
        # Create first user
        AuthService.register_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        # Try to create second user with same email
        result = AuthService.register_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        assert result["success"] is False
        assert "already exists" in result["error"]
    
    def test_register_user_weak_password(self, db_session):
        """Test registration with weak password"""
        result = AuthService.register_user(
            db_session, 
            "test@example.com", 
            "weak"
        )
        
        assert result["success"] is False
        assert "validation failed" in result["error"]
        assert len(result["errors"]) > 0
    
    def test_login_user_success(self, db_session):
        """Test successful user login"""
        # Register user first
        AuthService.register_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        result = AuthService.login_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        assert result["success"] is True
        assert result["access_token"] is not None
        assert result["refresh_token"] is not None
        assert result["user_id"] is not None
        assert result["organization_id"] is not None
        assert result["email"] == "test@example.com"
    
    def test_login_user_invalid_credentials(self, db_session):
        """Test login with invalid credentials"""
        result = AuthService.login_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        assert result["success"] is False
        assert "Invalid email or password" in result["error"]
    
    def test_get_current_user(self, db_session):
        """Test getting current user from token"""
        # Register and login user
        AuthService.register_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        login_result = AuthService.login_user(
            db_session, 
            "test@example.com", 
            "TestPassword123!"
        )
        
        # Get current user using token
        current_user = AuthService.get_current_user(
            db_session, 
            login_result["access_token"]
        )
        
        assert current_user is not None
        assert current_user.email == "test@example.com"
