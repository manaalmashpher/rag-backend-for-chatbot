"""
Unit tests for vector search service
"""

import pytest
from unittest.mock import Mock, patch
from app.services.vector_search import VectorSearchService

class TestVectorSearchService:
    """Test cases for VectorSearchService"""
    
    @pytest.fixture
    def mock_qdrant(self):
        """Mock QdrantService"""
        with patch('app.services.vector_search.QdrantService') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_embeddings(self):
        """Mock EmbeddingService"""
        with patch('app.services.vector_search.EmbeddingService') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def search_service(self, mock_qdrant, mock_embeddings):
        """Create VectorSearchService instance with mocked dependencies"""
        return VectorSearchService()
    
    def test_search_success(self, search_service, mock_qdrant, mock_embeddings):
        """Test successful vector search"""
        # Setup mocks
        mock_embeddings.generate_single_embedding.return_value = [0.1, 0.2, 0.3]
        mock_qdrant.search_vectors.return_value = [
            {
                'id': 1,
                'score': 0.85,
                'payload': {
                    'chunk_id': 'ch_00001',
                    'doc_id': 'doc_01',
                    'method': 1,
                    'page_from': 1,
                    'page_to': 2,
                    'hash': 'abc123',
                    'source': 'test.pdf'
                }
            }
        ]
        
        # Execute search
        results = search_service.search("test query")
        
        # Verify results
        assert len(results) == 1
        assert results[0]['chunk_id'] == 'ch_00001'
        assert results[0]['score'] == 0.85
        assert results[0]['search_type'] == 'semantic'
        
        # Verify method calls
        mock_embeddings.generate_single_embedding.assert_called_once_with("test query")
        mock_qdrant.search_vectors.assert_called_once()
    
    def test_search_with_limit(self, search_service, mock_qdrant, mock_embeddings):
        """Test search with custom limit"""
        # Setup mocks
        mock_embeddings.generate_single_embedding.return_value = [0.1, 0.2, 0.3]
        mock_qdrant.search_vectors.return_value = []
        
        # Execute search with limit
        search_service.search("test query", limit=5)
        
        # Verify limit was passed
        call_args = mock_qdrant.search_vectors.call_args
        assert call_args[1]['limit'] == 5
    
    def test_search_embedding_error(self, search_service, mock_embeddings):
        """Test search when embedding generation fails"""
        # Setup mock to raise exception
        mock_embeddings.generate_single_embedding.side_effect = Exception("Embedding error")
        mock_qdrant = search_service.qdrant
        mock_qdrant.is_available.return_value = True
        
        # Execute search - code gracefully handles errors by returning empty list
        results = search_service.search("test query")
        assert results == []
    
    def test_search_qdrant_error(self, search_service, mock_qdrant, mock_embeddings):
        """Test search when Qdrant search fails"""
        # Setup mocks
        mock_embeddings.generate_single_embedding.return_value = [0.1, 0.2, 0.3]
        mock_qdrant.search_vectors.side_effect = Exception("Qdrant error")
        mock_qdrant.is_available.return_value = True
        
        # Execute search - code gracefully handles errors by returning empty list
        results = search_service.search("test query")
        assert results == []
    
    def test_search_with_metadata(self, search_service, mock_qdrant, mock_embeddings):
        """Test search with metadata"""
        # Setup mocks
        mock_embeddings.generate_single_embedding.return_value = [0.1, 0.2, 0.3]
        mock_qdrant.search_vectors.return_value = []
        
        # Execute search with metadata
        result = search_service.search_with_metadata("test query", limit=10)
        
        # Verify metadata structure
        assert 'results' in result
        assert 'total_results' in result
        assert 'search_type' in result
        assert 'query' in result
        assert 'limit' in result
        assert result['search_type'] == 'semantic'
        assert result['query'] == 'test query'
        assert result['limit'] == 10
    
    def test_search_uses_default_score_threshold(self, search_service, mock_qdrant, mock_embeddings):
        """Test that search uses default score threshold of 0.05"""
        # Setup mocks
        mock_embeddings.generate_single_embedding.return_value = [0.1, 0.2, 0.3]
        mock_qdrant.search_vectors.return_value = []
        mock_qdrant.is_available.return_value = True
        
        # Execute search
        search_service.search("test query")
        
        # Verify score_threshold parameter was passed with default value 0.05
        call_args = mock_qdrant.search_vectors.call_args
        assert call_args[1]['score_threshold'] == 0.05
    
    def test_search_uses_configurable_score_threshold(self, search_service, mock_qdrant, mock_embeddings):
        """Test that search uses configurable score threshold from settings"""
        from app.core.config import settings
        
        # Setup mocks
        mock_embeddings.generate_single_embedding.return_value = [0.1, 0.2, 0.3]
        mock_qdrant.search_vectors.return_value = []
        mock_qdrant.is_available.return_value = True
        
        # Temporarily override settings
        original_threshold = getattr(settings, 'vector_score_threshold', 0.05)
        settings.vector_score_threshold = 0.08
        
        try:
            # Execute search
            search_service.search("test query")
            
            # Verify score_threshold parameter was passed with overridden value
            call_args = mock_qdrant.search_vectors.call_args
            assert call_args[1]['score_threshold'] == 0.08
        finally:
            # Restore original value
            settings.vector_score_threshold = original_threshold