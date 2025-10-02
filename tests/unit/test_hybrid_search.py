"""
Unit tests for hybrid search service
"""

import pytest
from unittest.mock import Mock, patch
from app.services.hybrid_search import HybridSearchService

class TestHybridSearchService:
    """Test cases for HybridSearchService"""
    
    @pytest.fixture
    def mock_vector_search(self):
        """Mock VectorSearchService"""
        with patch('app.services.hybrid_search.VectorSearchService') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_lexical_search(self):
        """Mock LexicalSearchService"""
        with patch('app.services.hybrid_search.LexicalSearchService') as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def search_service(self, mock_vector_search, mock_lexical_search):
        """Create HybridSearchService instance with mocked dependencies"""
        return HybridSearchService()
    
    def test_search_success(self, search_service, mock_vector_search, mock_lexical_search):
        """Test successful hybrid search"""
        # Setup mocks
        semantic_results = [
            {
                'chunk_id': 'ch_00001',
                'doc_id': 'doc_01',
                'method': 1,
                'page_from': 1,
                'page_to': 2,
                'hash': 'abc123',
                'source': 'test.pdf',
                'score': 0.8
            }
        ]
        
        lexical_results = [
            {
                'chunk_id': 'ch_00001',
                'doc_id': 'doc_01',
                'method': 1,
                'page_from': 1,
                'page_to': 2,
                'hash': 'abc123',
                'source': 'test.pdf',
                'score': 0.6
            }
        ]
        
        mock_vector_search.search.return_value = semantic_results
        mock_lexical_search.search.return_value = lexical_results
        
        # Execute search
        results = search_service.search("test query", limit=10)
        
        # Verify results
        assert len(results) == 1
        assert results[0]['chunk_id'] == 'ch_00001'
        assert 'fused_score' in results[0]
        assert 'sources' in results[0]
        assert 'semantic' in results[0]['sources']
        assert 'lexical' in results[0]['sources']
        
        # Verify method calls
        mock_vector_search.search.assert_called_once_with("test query", 20)  # topk_vec default
        mock_lexical_search.search.assert_called_once_with("test query", 20)  # topk_lex default
    
    def test_search_different_chunks(self, search_service, mock_vector_search, mock_lexical_search):
        """Test search with different chunks from semantic and lexical"""
        # Setup mocks with different chunks
        semantic_results = [
            {
                'chunk_id': 'ch_00001',
                'doc_id': 'doc_01',
                'method': 1,
                'page_from': 1,
                'page_to': 2,
                'hash': 'abc123',
                'source': 'test.pdf',
                'score': 0.8
            }
        ]
        
        lexical_results = [
            {
                'chunk_id': 'ch_00002',
                'doc_id': 'doc_01',
                'method': 2,
                'page_from': 3,
                'page_to': 4,
                'hash': 'def456',
                'source': 'test.pdf',
                'score': 0.6
            }
        ]
        
        mock_vector_search.search.return_value = semantic_results
        mock_lexical_search.search.return_value = lexical_results
        
        # Execute search
        results = search_service.search("test query", limit=10)
        
        # Verify results - should have 2 different chunks
        assert len(results) == 2
        chunk_ids = [r['chunk_id'] for r in results]
        assert 'ch_00001' in chunk_ids
        assert 'ch_00002' in chunk_ids
    
    def test_fusion_weights(self, search_service, mock_vector_search, mock_lexical_search):
        """Test that fusion weights are applied correctly"""
        # Setup mocks with same chunk
        semantic_results = [
            {
                'chunk_id': 'ch_00001',
                'doc_id': 'doc_01',
                'method': 1,
                'page_from': 1,
                'page_to': 2,
                'hash': 'abc123',
                'source': 'test.pdf',
                'score': 1.0  # High semantic score
            }
        ]
        
        lexical_results = [
            {
                'chunk_id': 'ch_00001',
                'doc_id': 'doc_01',
                'method': 1,
                'page_from': 1,
                'page_to': 2,
                'hash': 'abc123',
                'source': 'test.pdf',
                'score': 0.5  # Medium lexical score
            }
        ]
        
        mock_vector_search.search.return_value = semantic_results
        mock_lexical_search.search.return_value = lexical_results
        
        # Execute search
        results = search_service.search("test query", limit=10)
        
        # Verify fusion calculation
        # Expected: 1.0 * 0.6 + 0.5 * 0.4 = 0.6 + 0.2 = 0.8
        assert len(results) == 1
        assert abs(results[0]['fused_score'] - 0.8) < 0.01
    
    def test_search_with_metadata(self, search_service, mock_vector_search, mock_lexical_search):
        """Test search with metadata"""
        # Setup mocks
        mock_vector_search.search_with_metadata.return_value = {
            'results': [],
            'total_results': 0,
            'search_type': 'semantic',
            'query': 'test query',
            'limit': 20
        }
        
        mock_lexical_search.search_with_metadata.return_value = {
            'results': [],
            'total_results': 0,
            'search_type': 'lexical',
            'query': 'test query',
            'limit': 20
        }
        
        mock_vector_search.search.return_value = []
        mock_lexical_search.search.return_value = []
        
        # Execute search with metadata
        result = search_service.search_with_metadata("test query", limit=10)
        
        # Verify metadata structure
        assert 'results' in result
        assert 'total_results' in result
        assert 'search_type' in result
        assert 'query' in result
        assert 'limit' in result
        assert 'fusion_weights' in result
        assert 'individual_results' in result
        assert result['search_type'] == 'hybrid'
        assert result['query'] == 'test query'
        assert result['limit'] == 10
    
    def test_search_error_handling(self, search_service, mock_vector_search, mock_lexical_search):
        """Test search error handling"""
        # Setup mock to raise exception
        mock_vector_search.search.side_effect = Exception("Search error")
        
        # Execute search and expect exception
        with pytest.raises(RuntimeError, match="Hybrid search failed"):
            search_service.search("test query")
