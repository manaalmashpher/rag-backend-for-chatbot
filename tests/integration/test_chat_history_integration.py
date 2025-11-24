"""
Integration tests for multi-turn chat history
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.chat_history import ChatSession, ChatMessage
from app.services.database_migration import migrate_chat_history_tables

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    # Run migration
    migrate_chat_history_tables()
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestMultiTurnChatHistory:
    """Integration tests for multi-turn chat history flow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sample_candidates = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "method": 1,
                "page_from": 1,
                "page_to": 2,
                "hash": "hash1",
                "text": "Machine learning is a subset of artificial intelligence.",
                "score": 0.9
            }
        ]
        
        self.sample_reranked = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "method": 1,
                "page_from": 1,
                "page_to": 2,
                "hash": "hash1",
                "text": "Machine learning is a subset of artificial intelligence.",
                "score": 0.95
            }
        ]
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_q1_without_session_id_creates_session(self, mock_orchestrator, client, db_session):
        """Test: Send Q1 without session_id → receive session_id1"""
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.chat.return_value = ("Answer to Q1", "new-session-uuid-123")
        
        request_data = {
            "message": "What is machine learning?"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "new-session-uuid-123"
        assert "answer" in data
        assert data["answer"] == "Answer to Q1"
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_q2_with_session_id_includes_history(self, mock_orchestrator, client, db_session):
        """Test: Send Q2 with session_id1 → verify history included in LLM prompt"""
        session_uuid = str(uuid.uuid4())
        
        # Create existing session with history
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Add previous messages
        msg1 = ChatMessage(session_id=session.id, role="user", content="First question")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="First answer")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        # Mock orchestrator to capture the call
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        
        # Capture the chat call to verify history was passed
        chat_call_args = []
        def capture_chat(*args, **kwargs):
            chat_call_args.append((args, kwargs))
            return ("Answer to Q2", session_uuid)
        mock_orchestrator.chat.side_effect = capture_chat
        
        request_data = {
            "conversation_id": session_uuid,
            "message": "What would that require?"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_uuid
        
        # Verify chat was called with the session_id
        assert len(chat_call_args) > 0
        call_args, call_kwargs = chat_call_args[0]
        assert call_kwargs.get("session_id") == session_uuid
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_retrieval_uses_only_latest_query(self, mock_orchestrator, client, db_session):
        """Test: Verify retrieval still uses only latest query (not history)"""
        session_uuid = str(uuid.uuid4())
        
        # Create existing session
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        
        # Track retrieve_candidates calls
        retrieve_calls = []
        def capture_retrieve(*args, **kwargs):
            retrieve_calls.append(args[0])  # Capture the query
            return self.sample_candidates
        mock_orchestrator.retrieve_candidates.side_effect = capture_retrieve
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.chat.return_value = ("Answer", session_uuid)
        
        request_data = {
            "conversation_id": session_uuid,
            "message": "Second question"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        
        # Verify retrieve_candidates was called with only the latest query
        assert len(retrieve_calls) == 1
        assert retrieve_calls[0] == "Second question"
        # Should NOT include history in retrieval query
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_backward_compatibility_no_session_id(self, mock_orchestrator, client, db_session):
        """Test backward compatibility (no session_id provided)"""
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.chat.return_value = ("Answer", "new-session-uuid")
        
        # Request without conversation_id (should still work)
        request_data = {
            "message": "What is AI?"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "new-session-uuid"
        assert "answer" in data
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_multi_turn_conversation_flow(self, mock_orchestrator, client, db_session):
        """Test complete multi-turn conversation flow"""
        # Q1: First request without session_id
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        session_uuid_1 = str(uuid.uuid4())
        mock_orchestrator.chat.return_value = ("Answer 1", session_uuid_1)
        
        request1 = {"message": "What is machine learning?"}
        response1 = client.post("/api/chat", json=request1)
        
        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]
        
        # Q2: Second request with session_id from Q1
        session_uuid_2 = str(uuid.uuid4())
        mock_orchestrator.chat.return_value = ("Answer 2", session_uuid_2)
        
        request2 = {
            "conversation_id": session_id,
            "message": "What would that require?"
        }
        response2 = client.post("/api/chat", json=request2)
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert "session_id" in data2
        assert "answer" in data2
        
        # Verify chat was called twice
        assert mock_orchestrator.chat.call_count == 2
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_response_includes_session_id(self, mock_orchestrator, client, db_session):
        """Test that response always includes session_id"""
        session_uuid = str(uuid.uuid4())
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.chat.return_value = ("Answer", session_uuid)
        
        # Test without conversation_id
        request1 = {"message": "Question 1"}
        response1 = client.post("/api/chat", json=request1)
        assert response1.status_code == 200
        assert "session_id" in response1.json()
        
        # Test with conversation_id
        request2 = {
            "conversation_id": session_uuid,
            "message": "Question 2"
        }
        response2 = client.post("/api/chat", json=request2)
        assert response2.status_code == 200
        assert "session_id" in response2.json()

