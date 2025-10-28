"""
Unit tests for Chat Orchestrator Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.chat_orchestrator import ChatOrchestrator


class TestChatOrchestrator:
    """Test cases for ChatOrchestrator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.orchestrator = ChatOrchestrator()
        
        # Sample test data
        self.sample_query = "What is machine learning?"
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
                "text": "Deep learning uses neural networks for pattern recognition.",
                "score": 0.8
            }
        ]
    
    def test_chat_orchestrator_initialization(self):
        """Test ChatOrchestrator class initialization"""
        orchestrator = ChatOrchestrator()
        
        assert orchestrator.hybrid_search is not None
        assert orchestrator.reranker is not None
        assert hasattr(orchestrator, 'retrieve_candidates')
        assert hasattr(orchestrator, 'rerank')
        assert hasattr(orchestrator, 'synthesize_answer')
        assert hasattr(orchestrator, 'save_turn')
        assert hasattr(orchestrator, 'load_history')
    
    @patch('app.services.chat_orchestrator.HybridSearchService')
    def test_retrieve_candidates_success(self, mock_hybrid_search_class):
        """Test successful candidate retrieval"""
        # Setup mock
        mock_hybrid_search = Mock()
        mock_hybrid_search_class.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1", 
                "method": 1,
                "page_from": 1,
                "page_to": 2,
                "hash": "hash1",
                "text": "Sample text",
                "score": 0.9
            }
        ]
        
        # Create new orchestrator with mocked service
        orchestrator = ChatOrchestrator()
        orchestrator.hybrid_search = mock_hybrid_search
        
        # Test
        result = orchestrator.retrieve_candidates(self.sample_query, top_k=10)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["doc_id"] == "doc1"
        assert result[0]["chunk_id"] == "chunk1"
        assert result[0]["score"] == 0.9
        mock_hybrid_search.search.assert_called_once_with(self.sample_query, limit=10)
    
    @patch('app.services.chat_orchestrator.HybridSearchService')
    def test_retrieve_candidates_empty_results(self, mock_hybrid_search_class):
        """Test candidate retrieval with empty results"""
        # Setup mock
        mock_hybrid_search = Mock()
        mock_hybrid_search_class.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = []
        
        # Create new orchestrator with mocked service
        orchestrator = ChatOrchestrator()
        orchestrator.hybrid_search = mock_hybrid_search
        
        # Test
        result = orchestrator.retrieve_candidates(self.sample_query)
        
        # Assertions
        assert result == []
        mock_hybrid_search.search.assert_called_once()
    
    @patch('app.services.chat_orchestrator.HybridSearchService')
    def test_retrieve_candidates_error_handling(self, mock_hybrid_search_class):
        """Test error handling in candidate retrieval"""
        # Setup mock
        mock_hybrid_search = Mock()
        mock_hybrid_search_class.return_value = mock_hybrid_search
        mock_hybrid_search.search.side_effect = Exception("Search failed")
        
        # Create new orchestrator with mocked service
        orchestrator = ChatOrchestrator()
        orchestrator.hybrid_search = mock_hybrid_search
        
        # Test
        with pytest.raises(RuntimeError, match="Failed to retrieve candidates"):
            orchestrator.retrieve_candidates(self.sample_query)
    
    @patch('app.services.chat_orchestrator.RerankerService')
    def test_rerank_success(self, mock_reranker_class):
        """Test successful reranking"""
        # Setup mock
        mock_reranker = Mock()
        mock_reranker_class.return_value = mock_reranker
        mock_reranker.rerank.return_value = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "method": 1,
                "page_from": 1,
                "page_to": 2,
                "hash": "hash1",
                "text": "Sample text",
                "score": 0.95
            }
        ]
        
        # Create new orchestrator with mocked service
        orchestrator = ChatOrchestrator()
        orchestrator.reranker = mock_reranker
        
        # Test
        result = orchestrator.rerank(self.sample_query, self.sample_candidates, top_k=5)
        
        # Assertions
        assert len(result) == 1
        assert result[0]["score"] == 0.95
        mock_reranker.rerank.assert_called_once_with(self.sample_query, self.sample_candidates, top_r=5)
    
    @patch('app.services.chat_orchestrator.RerankerService')
    def test_rerank_empty_candidates(self, mock_reranker_class):
        """Test reranking with empty candidates"""
        # Setup mock
        mock_reranker = Mock()
        mock_reranker_class.return_value = mock_reranker
        
        # Create new orchestrator with mocked service
        orchestrator = ChatOrchestrator()
        orchestrator.reranker = mock_reranker
        
        # Test
        result = orchestrator.rerank(self.sample_query, [])
        
        # Assertions
        assert result == []
        mock_reranker.rerank.assert_not_called()
    
    @patch('app.services.chat_orchestrator.RerankerService')
    def test_rerank_error_handling(self, mock_reranker_class):
        """Test error handling in reranking"""
        # Setup mock
        mock_reranker = Mock()
        mock_reranker_class.return_value = mock_reranker
        mock_reranker.rerank.side_effect = Exception("Rerank failed")
        
        # Create new orchestrator with mocked service
        orchestrator = ChatOrchestrator()
        orchestrator.reranker = mock_reranker
        
        # Test
        with pytest.raises(RuntimeError, match="Failed to rerank candidates"):
            orchestrator.rerank(self.sample_query, self.sample_candidates)
    
    def test_build_context_single_chunk(self):
        """Test context building with single chunk"""
        chunks = [self.sample_candidates[0]]
        
        result = self.orchestrator._build_context(chunks)
        
        assert "[1] Document: doc1 (Page 1-2)" in result
        assert "Machine learning is a subset of artificial intelligence." in result
    
    def test_build_context_multiple_chunks(self):
        """Test context building with multiple chunks"""
        result = self.orchestrator._build_context(self.sample_candidates)
        
        assert "[1] Document: doc1 (Page 1-2)" in result
        assert "[2] Document: doc2 (Page 5)" in result
        assert "Machine learning is a subset of artificial intelligence." in result
        assert "Deep learning uses neural networks for pattern recognition." in result
    
    def test_build_context_missing_metadata(self):
        """Test context building with missing metadata"""
        chunks = [
            {
                "doc_id": "doc1",
                "chunk_id": "chunk1",
                "text": "Sample text without page info",
                "score": 0.9
            }
        ]
        
        result = self.orchestrator._build_context(chunks)
        
        assert "[1] Document: doc1" in result
        assert "Sample text without page info" in result
    
    def test_build_context_empty_chunks(self):
        """Test context building with empty chunks"""
        result = self.orchestrator._build_context([])
        
        assert result == ""
    
    def test_create_system_prompt(self):
        """Test system prompt creation"""
        result = self.orchestrator._create_system_prompt()
        
        assert "You are a document QA assistant" in result
        assert "strictly using the provided CONTEXT" in result
        assert "I couldn't find relevant information" in result
    
    def test_create_user_message(self):
        """Test user message creation"""
        context = "[1] Document: doc1 (Page 1)\nSample text"
        query = "What is AI?"
        
        result = self.orchestrator._create_user_message(query, context)
        
        assert "Question: What is AI?" in result
        assert "Context:" in result
        assert "[1] Document: doc1 (Page 1)" in result
        assert "Include citations using the bracketed numbers" in result
    
    @patch('app.services.chat_orchestrator.deepseek_chat')
    def test_synthesize_answer_success(self, mock_deepseek_chat):
        """Test successful answer synthesis"""
        # Setup mock
        mock_deepseek_chat.return_value = "Machine learning is a subset of AI that enables computers to learn."
        
        # Test
        result = self.orchestrator.synthesize_answer(self.sample_query, self.sample_candidates)
        
        # Assertions
        assert result == "Machine learning is a subset of AI that enables computers to learn."
        mock_deepseek_chat.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_deepseek_chat.call_args
        messages = call_args[0][0]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Question: What is machine learning?" in messages[1]["content"]
    
    @patch('app.services.chat_orchestrator.deepseek_chat')
    def test_synthesize_answer_empty_chunks(self, mock_deepseek_chat):
        """Test answer synthesis with empty chunks"""
        result = self.orchestrator.synthesize_answer(self.sample_query, [])
        
        assert result == "I couldn't find relevant information in the provided documents."
        mock_deepseek_chat.assert_not_called()
    
    @patch('app.services.chat_orchestrator.deepseek_chat')
    def test_synthesize_answer_error_handling(self, mock_deepseek_chat):
        """Test error handling in answer synthesis"""
        # Setup mock
        mock_deepseek_chat.side_effect = Exception("DeepSeek API failed")
        
        # Test
        with pytest.raises(RuntimeError, match="Failed to synthesize answer"):
            self.orchestrator.synthesize_answer(self.sample_query, self.sample_candidates)
    
    def test_save_turn_no_op(self):
        """Test save_turn method (no-op)"""
        # Should not raise any exceptions
        self.orchestrator.save_turn()
    
    def test_load_history_no_op(self):
        """Test load_history method (no-op)"""
        # Should not raise any exceptions
        self.orchestrator.load_history()
    
    @patch('app.services.chat_orchestrator.HybridSearchService')
    @patch('app.services.chat_orchestrator.RerankerService')
    @patch('app.services.chat_orchestrator.deepseek_chat')
    def test_integration_flow(self, mock_deepseek_chat, mock_reranker_class, mock_hybrid_search_class):
        """Test complete integration flow"""
        # Setup mocks
        mock_hybrid_search = Mock()
        mock_hybrid_search_class.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = self.sample_candidates
        
        mock_reranker = Mock()
        mock_reranker_class.return_value = mock_reranker
        mock_reranker.rerank.return_value = [self.sample_candidates[0]]
        
        mock_deepseek_chat.return_value = "Machine learning is a subset of AI."
        
        # Create orchestrator with mocked services
        orchestrator = ChatOrchestrator()
        orchestrator.hybrid_search = mock_hybrid_search
        orchestrator.reranker = mock_reranker
        
        # Test complete flow
        candidates = orchestrator.retrieve_candidates(self.sample_query)
        reranked = orchestrator.rerank(self.sample_query, candidates)
        answer = orchestrator.synthesize_answer(self.sample_query, reranked)
        
        # Assertions
        assert len(candidates) == 2
        assert len(reranked) == 1
        assert answer == "Machine learning is a subset of AI."
        
        # Verify all services were called
        mock_hybrid_search.search.assert_called_once()
        mock_reranker.rerank.assert_called_once()
        mock_deepseek_chat.assert_called_once()
