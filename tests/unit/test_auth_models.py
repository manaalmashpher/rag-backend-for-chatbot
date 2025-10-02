"""
Unit tests for authentication models
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.auth import User, Organization


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestOrganization:
    """Test Organization model"""
    
    def test_create_organization(self, db_session):
        """Test creating an organization"""
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        
        assert org.id is not None
        assert org.name == "Test Organization"
        assert org.created_at is not None
        assert org.updated_at is not None
    
    def test_organization_relationships(self, db_session):
        """Test organization relationships"""
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        
        # Create a user associated with the organization
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            organization_id=org.id
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Test relationship
        assert len(org.users) == 1
        assert org.users[0].email == "test@example.com"


class TestUser:
    """Test User model"""
    
    def test_create_user(self, db_session):
        """Test creating a user"""
        # First create an organization
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            organization_id=org.id
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.organization_id == org.id
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_email_unique(self, db_session):
        """Test that user email must be unique"""
        # First create an organization
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        
        # Create first user
        user1 = User(
            email="test@example.com",
            password_hash="hashed_password",
            organization_id=org.id
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            email="test@example.com",
            password_hash="hashed_password2",
            organization_id=org.id
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            db_session.commit()
    
    def test_user_relationships(self, db_session):
        """Test user relationships"""
        # Create organization
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        
        # Create user
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            organization_id=org.id
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Test relationship
        assert user.organization.id == org.id
        assert user.organization.name == "Test Organization"
