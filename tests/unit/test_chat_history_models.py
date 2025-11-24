"""
Unit tests for chat history models
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.chat_history import ChatSession, ChatMessage
import uuid


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestChatSession:
    """Test ChatSession model"""
    
    def test_create_chat_session(self, db_session):
        """Test creating a chat session"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        assert session.id is not None
        assert session.uuid == session_uuid
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.user_id is None
    
    def test_chat_session_without_uuid(self, db_session):
        """Test creating a chat session without UUID (nullable)"""
        session = ChatSession()
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        assert session.id is not None
        assert session.uuid is None
    
    def test_chat_session_timestamps(self, db_session):
        """Test that timestamps are set correctly"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.created_at == session.updated_at  # Initially same
    
    def test_chat_session_relationships(self, db_session):
        """Test chat session relationships with messages"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create messages
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Hello"
        )
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Hi there!"
        )
        db_session.add(user_msg)
        db_session.add(assistant_msg)
        db_session.commit()
        db_session.refresh(session)
        
        # Test relationship
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"


class TestChatMessage:
    """Test ChatMessage model"""
    
    def test_create_chat_message(self, db_session):
        """Test creating a chat message"""
        # First create a session
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create message
        message = ChatMessage(
            session_id=session.id,
            role="user",
            content="Test message"
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)
        
        assert message.id is not None
        assert message.session_id == session.id
        assert message.role == "user"
        assert message.content == "Test message"
        assert message.created_at is not None
    
    def test_chat_message_foreign_key_relationship(self, db_session):
        """Test chat message foreign key relationship"""
        # Create session
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create message
        message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Response message"
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)
        
        # Test relationship
        assert message.session.id == session.id
        assert message.session.uuid == session_uuid
    
    def test_chat_message_role_validation(self, db_session):
        """Test that role can be user or assistant"""
        # Create session
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create user message
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="User message"
        )
        db_session.add(user_msg)
        db_session.commit()
        
        # Create assistant message
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Assistant message"
        )
        db_session.add(assistant_msg)
        db_session.commit()
        
        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"
    
    def test_chat_message_cascade_delete(self, db_session):
        """Test that messages are deleted when session is deleted"""
        # Create session
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create messages
        message1 = ChatMessage(
            session_id=session.id,
            role="user",
            content="Message 1"
        )
        message2 = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Message 2"
        )
        db_session.add(message1)
        db_session.add(message2)
        db_session.commit()
        
        message1_id = message1.id
        message2_id = message2.id
        
        # Delete session
        db_session.delete(session)
        db_session.commit()
        
        # Verify messages are deleted
        assert db_session.query(ChatMessage).filter(ChatMessage.id == message1_id).first() is None
        assert db_session.query(ChatMessage).filter(ChatMessage.id == message2_id).first() is None

