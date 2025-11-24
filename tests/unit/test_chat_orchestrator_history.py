"""
Unit tests for ChatOrchestrator history methods
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.chat_history import ChatSession, ChatMessage
from app.services.chat_orchestrator import ChatOrchestrator
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


@pytest.fixture
def sample_session(db_session):
    """Create a sample chat session"""
    session_uuid = str(uuid.uuid4())
    session = ChatSession(uuid=session_uuid)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class TestLoadHistory:
    """Test load_history method"""
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_load_history_returns_correct_sequence(self, mock_get_db, db_session, sample_session):
        """Test load_history returns correct message sequence"""
        # Create messages in order
        msg1 = ChatMessage(session_id=sample_session.id, role="user", content="Hello")
        msg2 = ChatMessage(session_id=sample_session.id, role="assistant", content="Hi there!")
        msg3 = ChatMessage(session_id=sample_session.id, role="user", content="How are you?")
        db_session.add_all([msg1, msg2, msg3])
        db_session.commit()
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        history = orchestrator.load_history(sample_session.uuid, limit=10)
        
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "How are you?"
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_load_history_respects_limit(self, mock_get_db, db_session, sample_session):
        """Test load_history respects limit parameter"""
        # Create 15 messages
        messages = []
        for i in range(15):
            role = "user" if i % 2 == 0 else "assistant"
            msg = ChatMessage(session_id=sample_session.id, role=role, content=f"Message {i}")
            messages.append(msg)
        db_session.add_all(messages)
        db_session.commit()
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        history = orchestrator.load_history(sample_session.uuid, limit=10)
        
        assert len(history) == 10
        # Should return oldest 10 messages
        assert history[0]["content"] == "Message 0"
        assert history[9]["content"] == "Message 9"
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_load_history_returns_empty_list_for_new_session(self, mock_get_db, db_session):
        """Test load_history returns empty list for new session"""
        new_uuid = str(uuid.uuid4())
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        history = orchestrator.load_history(new_uuid, limit=10)
        
        assert history == []
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_load_history_handles_nonexistent_session(self, mock_get_db, db_session):
        """Test load_history handles nonexistent session gracefully"""
        nonexistent_uuid = str(uuid.uuid4())
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        history = orchestrator.load_history(nonexistent_uuid, limit=10)
        
        assert history == []


class TestSaveTurn:
    """Test save_turn method"""
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_save_turn_creates_both_messages(self, mock_get_db, db_session, sample_session):
        """Test save_turn creates both user and assistant messages"""
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        # Store UUID and ID before session gets detached
        session_uuid = sample_session.uuid
        session_id = sample_session.id
        
        orchestrator = ChatOrchestrator()
        orchestrator.save_turn(session_uuid, "User question", "Assistant answer")
        
        # Verify messages were created (query by session_id, not detached object)
        messages = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).all()
        
        assert len(messages) == 2
        user_msg = next((m for m in messages if m.role == "user"), None)
        assistant_msg = next((m for m in messages if m.role == "assistant"), None)
        
        assert user_msg is not None
        assert user_msg.content == "User question"
        assert assistant_msg is not None
        assert assistant_msg.content == "Assistant answer"
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_save_turn_updates_session_timestamp(self, mock_get_db, db_session, sample_session):
        """Test save_turn updates session timestamp"""
        # Store values before session gets detached
        session_uuid = sample_session.uuid
        session_id = sample_session.id
        original_updated_at = sample_session.updated_at
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        orchestrator.save_turn(session_uuid, "Question", "Answer")
        
        # Query fresh session from database (don't use detached sample_session)
        updated_session = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
        assert updated_session is not None
        assert updated_session.updated_at >= original_updated_at
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_save_turn_raises_error_for_nonexistent_session(self, mock_get_db, db_session):
        """Test save_turn raises error for nonexistent session"""
        nonexistent_uuid = str(uuid.uuid4())
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        
        with pytest.raises(ValueError, match="Session.*not found"):
            orchestrator.save_turn(nonexistent_uuid, "Question", "Answer")


class TestGetOrCreateSession:
    """Test _get_or_create_session method"""
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_get_or_create_session_returns_existing(self, mock_get_db, db_session, sample_session):
        """Test _get_or_create_session returns existing session UUID"""
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        result_uuid = orchestrator._get_or_create_session(sample_session.uuid)
        
        assert result_uuid == sample_session.uuid
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_get_or_create_session_creates_new(self, mock_get_db, db_session):
        """Test _get_or_create_session creates new session when UUID is None"""
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        result_uuid = orchestrator._get_or_create_session(None)
        
        assert result_uuid is not None
        # Verify session was created
        session = db_session.query(ChatSession).filter(ChatSession.uuid == result_uuid).first()
        assert session is not None
    
    @patch('app.services.chat_orchestrator.get_db')
    def test_get_or_create_session_creates_new_for_nonexistent_uuid(self, mock_get_db, db_session):
        """Test _get_or_create_session creates new session for nonexistent UUID"""
        nonexistent_uuid = str(uuid.uuid4())
        
        # Mock get_db to return a new generator each time
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        orchestrator = ChatOrchestrator()
        result_uuid = orchestrator._get_or_create_session(nonexistent_uuid)
        
        # Should create new session (different UUID)
        assert result_uuid is not None
        assert result_uuid != nonexistent_uuid


class TestChatFlowWithHistory:
    """Test chat flow with history integration"""
    
    @patch('app.services.chat_orchestrator.get_db')
    @patch('app.services.chat_orchestrator.deepseek_chat')
    def test_chat_flow_with_history(self, mock_deepseek_chat, mock_get_db, db_session, sample_session):
        """Test chat flow includes history in LLM prompt"""
        # Create existing history
        msg1 = ChatMessage(session_id=sample_session.id, role="user", content="First question")
        msg2 = ChatMessage(session_id=sample_session.id, role="assistant", content="First answer")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        # Mock get_db to return a new generator each time (chat() calls it 3 times)
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        # Mock DeepSeek
        mock_deepseek_chat.return_value = "Second answer"
        
        orchestrator = ChatOrchestrator()
        context_chunks = [{"doc_id": "doc1", "chunk_id": "chunk1", "text": "Context", "score": 0.9}]
        
        answer, session_id = orchestrator.chat("Second question", context_chunks, session_id=sample_session.uuid)
        
        assert answer == "Second answer"
        assert session_id == sample_session.uuid
        
        # Verify DeepSeek was called with history
        call_args = mock_deepseek_chat.call_args
        messages = call_args[0][0]
        
        # Should have: system, history user, history assistant, new user
        assert len(messages) >= 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "First question"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "First answer"
        assert messages[3]["role"] == "user"
        assert "Second question" in messages[3]["content"]
        
        # Verify turn was saved
        messages_after = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == sample_session.id
        ).order_by(ChatMessage.created_at.asc()).all()
        assert len(messages_after) == 4  # 2 existing + 2 new
    
    @patch('app.services.chat_orchestrator.get_db')
    @patch('app.services.chat_orchestrator.deepseek_chat')
    def test_chat_flow_creates_new_session(self, mock_deepseek_chat, mock_get_db, db_session):
        """Test chat flow creates new session when session_id is None"""
        # Mock get_db to return a new generator each time (chat() calls it 3 times)
        def mock_db_generator():
            yield db_session
        mock_get_db.side_effect = lambda: mock_db_generator()
        
        # Mock DeepSeek
        mock_deepseek_chat.return_value = "Answer"
        
        orchestrator = ChatOrchestrator()
        context_chunks = [{"doc_id": "doc1", "chunk_id": "chunk1", "text": "Context", "score": 0.9}]
        
        answer, session_id = orchestrator.chat("Question", context_chunks, session_id=None)
        
        assert answer == "Answer"
        assert session_id is not None
        
        # Verify session was created
        session = db_session.query(ChatSession).filter(ChatSession.uuid == session_id).first()
        assert session is not None
        
        # Verify messages were saved
        messages = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).all()
        assert len(messages) == 2  # user + assistant

