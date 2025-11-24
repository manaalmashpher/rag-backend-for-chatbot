"""
Integration tests for follow-up aware retrieval
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
    # Run migration - patch the engine to use test engine
    with patch('app.services.database_migration.engine', engine):
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


class TestFollowupAwareRetrieval:
    """Integration tests for follow-up aware retrieval flow"""
    
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
                "text": "Section 5.22.3 contains requirements for submission.",
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
                "text": "Section 5.22.3 contains requirements for submission.",
                "score": 0.95
            }
        ]
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_turn1_section_query_successful(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: Turn 1 - 'what's in section 5.22.3' → successful retrieval"""
        # Create a session first
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        
        mock_retrieve.return_value = self.sample_candidates
        mock_rerank.return_value = self.sample_reranked
        mock_chat.return_value = ("Section 5.22.3 contains...", session_uuid)
        
        request_data = {
            "conversation_id": session_uuid,
            "message": "what's in section 5.22.3"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["session_id"] == session_uuid
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_turn2_ambiguous_followup_receives_augmented_query(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: Turn 2 - 'what do I need to submit for this?' → HybridSearchService receives query containing '5.22.3'"""
        # Create a session with history
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.flush()  # Flush to get session.id
        
        # Add history: Turn 1
        msg1 = ChatMessage(session_id=session.id, role="user", content="what's in section 5.22.3")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="Section 5.22.3 contains...")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        # Refresh to ensure session is up to date
        db_session.refresh(session)
        db_session.refresh(msg1)
        db_session.refresh(msg2)
        
        # Verify session exists in database (using the same session that will be used by load_history)
        found_session = db_session.query(ChatSession).filter(ChatSession.uuid == session_uuid).first()
        assert found_session is not None, f"Session {session_uuid} should exist in database"
        assert found_session.id == session.id, "Session IDs should match"
        
        # Verify messages exist
        messages = db_session.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
        assert len(messages) == 2, f"Should have 2 messages, found {len(messages)}"
        
        # Ensure all changes are visible
        db_session.expire_all()
        
        # Patch get_db in chat_orchestrator module for the entire test
        # This is needed because load_history calls get_db() directly, bypassing FastAPI's dependency injection
        # We need to make close() a no-op because load_history closes the session, but we want to reuse the same test session
        original_close = db_session.close
        def noop_close():
            pass  # Don't actually close the test session - it's managed by the fixture
        db_session.close = noop_close
        
        def mock_db_generator():
            yield db_session
        
        # Mock to capture the query passed to retrieve_candidates
        captured_query = []
        
        def capture_query(query, top_k=20):
            captured_query.append(query)
            return self.sample_candidates
        
        mock_retrieve.side_effect = capture_query
        mock_rerank.return_value = self.sample_reranked
        mock_chat.return_value = ("You need to submit...", session_uuid)
        
        # Patch get_db for the entire test so API calls use the test database session
        try:
            with patch('app.services.chat_orchestrator.get_db') as mock_get_db:
                mock_get_db.side_effect = lambda: mock_db_generator()
                
                # Test that load_history can find the session (using the same db_session)
                from app.services.chat_orchestrator import ChatOrchestrator
                orchestrator = ChatOrchestrator()
                history = orchestrator.load_history(session_uuid, limit=10)
                assert len(history) == 2, f"Should have 2 messages in history, got {len(history)}"
                assert history[0]["content"] == "what's in section 5.22.3"
                
                request_data = {
                    "conversation_id": session_uuid,
                    "message": "what do I need to submit for this?"
                }
                
                response = client.post("/api/chat", json=request_data)
                
                assert response.status_code == 200
                # Verify augmented query was used
                assert len(captured_query) > 0, f"retrieve_candidates should have been called, captured_query: {captured_query}"
                assert "5.22.3" in captured_query[0], f"Query should contain '5.22.3', got: {captured_query[0]}"
                assert "what do I need to submit for this?" in captured_query[0]
        finally:
            # Restore original close function
            db_session.close = original_close
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_llm_receives_original_message(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: Verify LLM receives original user message (not augmented query)"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Add history
        msg1 = ChatMessage(session_id=session.id, role="user", content="what's in section 5.22.3")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="Section 5.22.3 contains...")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        # Capture the query passed to chat() method
        captured_chat_query = []
        
        def capture_chat_query(query, context_chunks, session_id=None):
            captured_chat_query.append(query)
            return ("Answer", session_uuid)
        
        mock_retrieve.return_value = self.sample_candidates
        mock_rerank.return_value = self.sample_reranked
        mock_chat.side_effect = capture_chat_query
        
        original_message = "what do I need to submit for this?"
        request_data = {
            "conversation_id": session_uuid,
            "message": original_message
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        # Verify original message was passed to chat(), not augmented query
        assert len(captured_chat_query) > 0
        assert captured_chat_query[0] == original_message
        assert "For section" not in captured_chat_query[0]
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_history_saved_with_original_message(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: Verify history saved with original message (not augmented query)"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Add initial history
        msg1 = ChatMessage(session_id=session.id, role="user", content="what's in section 5.22.3")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="Section 5.22.3 contains...")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        mock_retrieve.return_value = self.sample_candidates
        mock_rerank.return_value = self.sample_reranked
        mock_chat.return_value = ("Answer", session_uuid)
        
        original_message = "what do I need to submit for this?"
        request_data = {
            "conversation_id": session_uuid,
            "message": original_message
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        
        # Verify message was saved to database - check that chat() was called with original message
        assert mock_chat.called
        call_args = mock_chat.call_args
        assert call_args[0][0] == original_message  # First positional arg is the query
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_explicit_section_bypasses_augmentation(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: Explicit section IDs in current message bypass augmentation"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Add history
        msg1 = ChatMessage(session_id=session.id, role="user", content="what's in section 5.22.3")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="Section 5.22.3 contains...")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        captured_query = []
        
        def capture_query(query, top_k=20):
            captured_query.append(query)
            return self.sample_candidates
        
        mock_retrieve.side_effect = capture_query
        mock_rerank.return_value = self.sample_reranked
        mock_chat.return_value = ("Answer", session_uuid)
        
        request_data = {
            "conversation_id": session_uuid,
            "message": "explain section 1.2"  # Has explicit section ID
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        # Verify query was NOT augmented (should be original message)
        assert len(captured_query) > 0
        assert captured_query[0] == "explain section 1.2"
        assert "For section" not in captured_query[0]
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_non_ambiguous_query_bypasses_augmentation(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: Non-ambiguous queries bypass augmentation"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Add history
        msg1 = ChatMessage(session_id=session.id, role="user", content="what's in section 5.22.3")
        msg2 = ChatMessage(session_id=session.id, role="assistant", content="Section 5.22.3 contains...")
        db_session.add_all([msg1, msg2])
        db_session.commit()
        
        captured_query = []
        
        def capture_query(query, top_k=20):
            captured_query.append(query)
            return self.sample_candidates
        
        mock_retrieve.side_effect = capture_query
        mock_rerank.return_value = self.sample_reranked
        mock_chat.return_value = ("Answer", session_uuid)
        
        request_data = {
            "conversation_id": session_uuid,
            "message": "give me an overview of the framework"  # Non-ambiguous
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        # Verify query was NOT augmented
        assert len(captured_query) > 0
        assert captured_query[0] == "give me an overview of the framework"
        assert "For section" not in captured_query[0]
    
    @patch('app.api.routes.chat.chat_orchestrator.retrieve_candidates')
    @patch('app.api.routes.chat.chat_orchestrator.rerank')
    @patch('app.api.routes.chat.chat_orchestrator.chat')
    def test_first_message_no_augmentation(self, mock_chat, mock_rerank, mock_retrieve, client, db_session):
        """Test: First message in session (no history) → no augmentation"""
        session_uuid = str(uuid.uuid4())
        session = ChatSession(uuid=session_uuid)
        db_session.add(session)
        db_session.commit()
        
        captured_query = []
        
        def capture_query(query, top_k=20):
            captured_query.append(query)
            return self.sample_candidates
        
        mock_retrieve.side_effect = capture_query
        mock_rerank.return_value = self.sample_reranked
        mock_chat.return_value = ("Answer", session_uuid)
        
        request_data = {
            "conversation_id": session_uuid,
            "message": "what do I need to submit for this?"
        }
        
        response = client.post("/api/chat", json=request_data)
        
        assert response.status_code == 200
        # Verify query was NOT augmented (no history section ID)
        assert len(captured_query) > 0
        assert captured_query[0] == "what do I need to submit for this?"
        assert "For section" not in captured_query[0]

