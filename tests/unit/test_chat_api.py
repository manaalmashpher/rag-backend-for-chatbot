"""
Unit tests for Chat API endpoint
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


class TestChatAPI:
    """Test cases for Chat API endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.valid_conversation_id = str(uuid.uuid4())
        self.sample_message = "What is machine learning?"
        
        self.sample_chat_request = {
            "conversation_id": self.valid_conversation_id,
            "message": self.sample_message
        }
        
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
            },
            {
                "doc_id": "doc2",
                "chunk_id": "chunk2",
                "method": 2,
                "page_from": 5,
                "page_to": 5,
                "hash": "hash2",
                "text": "Deep learning uses neural networks.",
                "score": 0.8
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
        
        self.sample_answer = "Machine learning is a subset of artificial intelligence that enables systems to learn from data."
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_success(self, mock_orchestrator):
        """Test successful chat interaction"""
        # Setup mocks
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.synthesize_answer.return_value = self.sample_answer
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == self.sample_answer
        assert "citations" in data
        assert len(data["citations"]) == 1
        assert "conversation_id" in data
        assert data["conversation_id"] == self.valid_conversation_id
        assert "latency_ms" in data
        assert data["latency_ms"] >= 0
        
        # Verify citations structure
        citation = data["citations"][0]
        assert "doc_id" in citation
        assert "chunk_id" in citation
        assert "page_from" in citation
        assert "page_to" in citation
        assert "score" in citation
        assert "text" in citation
        
        # Verify orchestrator was called correctly
        mock_orchestrator.retrieve_candidates.assert_called_once_with(self.sample_message, top_k=20)
        mock_orchestrator.rerank.assert_called_once_with(self.sample_message, self.sample_candidates, top_k=8)
        mock_orchestrator.synthesize_answer.assert_called_once_with(self.sample_message, self.sample_reranked)
    
    def test_chat_endpoint_invalid_conversation_id_format(self):
        """Test chat endpoint with invalid conversation_id format"""
        invalid_request = {
            "conversation_id": "not-a-valid-uuid",
            "message": self.sample_message
        }
        
        response = client.post("/api/chat", json=invalid_request)
        
        assert response.status_code == 422  # Validation error from Pydantic
    
    def test_chat_endpoint_missing_conversation_id(self):
        """Test chat endpoint with missing conversation_id"""
        invalid_request = {
            "message": self.sample_message
        }
        
        response = client.post("/api/chat", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_empty_message(self):
        """Test chat endpoint with empty message"""
        invalid_request = {
            "conversation_id": self.valid_conversation_id,
            "message": ""
        }
        
        response = client.post("/api/chat", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_message_too_long(self):
        """Test chat endpoint with message exceeding max length"""
        invalid_request = {
            "conversation_id": self.valid_conversation_id,
            "message": "x" * 1001  # Exceeds max_length=1000
        }
        
        response = client.post("/api/chat", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_message_with_special_characters(self):
        """Test chat endpoint with message containing special characters (should be sanitized)"""
        message_with_special = "What is <script>alert('xss')</script> machine learning?"
        
        request_data = {
            "conversation_id": self.valid_conversation_id,
            "message": message_with_special
        }
        
        with patch('app.api.routes.chat.chat_orchestrator') as mock_orchestrator:
            mock_orchestrator.retrieve_candidates.return_value = []
            mock_orchestrator.rerank.return_value = []
            mock_orchestrator.synthesize_answer.return_value = "Answer"
            
            response = client.post("/api/chat", json=request_data)
            
            # Should succeed but message should be sanitized
            assert response.status_code == 200
            # Verify sanitized message was passed to orchestrator
            call_args = mock_orchestrator.retrieve_candidates.call_args
            sanitized_message = call_args[0][0]
            assert "<script>" not in sanitized_message
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_empty_candidates(self, mock_orchestrator):
        """Test chat endpoint with empty candidates from retrieval"""
        # Setup mocks - empty candidates
        mock_orchestrator.retrieve_candidates.return_value = []
        mock_orchestrator.rerank.return_value = []
        mock_orchestrator.synthesize_answer.return_value = "I couldn't find relevant information in the provided documents."
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Should still succeed with no citations
        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 0
        assert "I couldn't find relevant information" in data["answer"]
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_orchestrator_retrieve_failure(self, mock_orchestrator):
        """Test chat endpoint when orchestrator retrieve_candidates fails"""
        # Setup mock to raise RuntimeError
        mock_orchestrator.retrieve_candidates.side_effect = RuntimeError("Failed to retrieve candidates")
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Should return 500 with error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "error" in detail
        assert detail["error"]["code"] == "CHAT_ERROR"
        assert detail["error"]["message"] == "Failed to process chat request"
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_orchestrator_rerank_failure(self, mock_orchestrator):
        """Test chat endpoint when orchestrator rerank fails"""
        # Setup mocks - retrieve succeeds, rerank fails
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.side_effect = RuntimeError("Failed to rerank candidates")
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Should return 500 with error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "error" in detail
        assert detail["error"]["code"] == "CHAT_ERROR"
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_orchestrator_synthesize_failure(self, mock_orchestrator):
        """Test chat endpoint when orchestrator synthesize_answer fails"""
        # Setup mocks - retrieve and rerank succeed, synthesize fails
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.synthesize_answer.side_effect = RuntimeError("Failed to synthesize answer")
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Should return 500 with error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "error" in detail
        assert detail["error"]["code"] == "CHAT_ERROR"
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_unexpected_exception(self, mock_orchestrator):
        """Test chat endpoint with unexpected exception"""
        # Setup mock to raise unexpected exception
        mock_orchestrator.retrieve_candidates.side_effect = ValueError("Unexpected error")
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Should return 400 or 500 depending on exception type
        assert response.status_code in [400, 500]
        data = response.json()
        assert "detail" in data
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_response_format(self, mock_orchestrator):
        """Test chat endpoint response format matches schema"""
        # Setup mocks
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.synthesize_answer.return_value = self.sample_answer
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert "citations" in data
        assert isinstance(data["citations"], list)
        assert "conversation_id" in data
        assert isinstance(data["conversation_id"], str)
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], int)
        assert data["latency_ms"] >= 0
        
        # Verify citation structure if present
        if len(data["citations"]) > 0:
            citation = data["citations"][0]
            assert "doc_id" in citation
            assert "chunk_id" in citation
            assert "page_from" in citation or citation["page_from"] is None
            assert "page_to" in citation or citation["page_to"] is None
            assert "score" in citation
            assert isinstance(citation["score"], float)
            assert 0.0 <= citation["score"] <= 1.0
            assert "text" in citation
            assert isinstance(citation["text"], str)
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_latency_tracking(self, mock_orchestrator):
        """Test that latency is tracked correctly"""
        import time
        
        # Setup mocks with slight delay simulation
        def delayed_retrieve(*args, **kwargs):
            time.sleep(0.01)  # 10ms delay
            return self.sample_candidates
        
        mock_orchestrator.retrieve_candidates.side_effect = delayed_retrieve
        mock_orchestrator.rerank.return_value = self.sample_reranked
        mock_orchestrator.synthesize_answer.return_value = self.sample_answer
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Verify latency is tracked
        assert response.status_code == 200
        data = response.json()
        assert "latency_ms" in data
        assert data["latency_ms"] >= 10  # At least 10ms due to our delay
    
    @patch('app.api.routes.chat.chat_orchestrator')
    def test_chat_endpoint_multiple_citations(self, mock_orchestrator):
        """Test chat endpoint with multiple citations"""
        # Setup mocks with multiple reranked results
        mock_orchestrator.retrieve_candidates.return_value = self.sample_candidates
        mock_orchestrator.rerank.return_value = self.sample_candidates  # Return all candidates
        mock_orchestrator.synthesize_answer.return_value = self.sample_answer
        
        # Make request
        response = client.post("/api/chat", json=self.sample_chat_request)
        
        # Verify multiple citations are returned
        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 2  # Both candidates should be citations

