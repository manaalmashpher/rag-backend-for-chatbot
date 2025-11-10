"""
Unit tests for lexical search service
"""

import pytest
from unittest.mock import Mock, patch
from app.services.lexical_search import LexicalSearchService

class TestLexicalSearchService:
    """Test cases for LexicalSearchService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        with patch('app.services.lexical_search.get_db') as mock:
            db_session = Mock()
            mock.return_value = iter([db_session])
            yield db_session
    
    @pytest.fixture
    def search_service(self, mock_db):
        """Create LexicalSearchService instance with mocked database"""
        return LexicalSearchService()
    
    def test_search_success(self, search_service, mock_db):
        """Test successful lexical search"""
        # Setup mock database result
        mock_result = Mock()
        mock_row = Mock()
        mock_row.chunk_id = 1
        mock_row.doc_id = 1
        mock_row.method = 2
        mock_row.page_from = 1
        mock_row.page_to = 2
        mock_row.hash = 'def456'
        mock_row.source = 'test.pdf'
        mock_row.text = 'This is test content'
        mock_row.rank_score = 0.75  # This is not used anymore, kept for compatibility
        
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        mock_db.execute.return_value = mock_result
        
        # Execute search
        results = search_service.search("test query")
        
        # Verify results
        assert len(results) == 1
        assert results[0]['chunk_id'] == 'ch_00001'
        assert results[0]['doc_id'] == 'doc_01'
        assert results[0]['method'] == 2
        # Score comes from PostgreSQL ts_rank (not calculated match_count/total_terms)
        # Mock returns rank_score = 0.75
        assert results[0]['score'] == 0.75
        assert results[0]['search_type'] == 'lexical'
        
        # Verify database query was executed
        mock_db.execute.assert_called_once()
    
    def test_search_with_limit(self, search_service, mock_db):
        """Test search with custom limit"""
        # Setup mock database result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_db.execute.return_value = mock_result
        
        # Execute search with limit
        search_service.search("test query", limit=5)
        
        # Verify limit was passed in query
        call_args = mock_db.execute.call_args
        assert 'limit' in str(call_args)
    
    def test_search_database_error(self, search_service, mock_db):
        """Test search when database query fails"""
        # Setup mock to raise exception
        mock_db.execute.side_effect = Exception("Database error")
        
        # Execute search - code gracefully handles errors by returning empty list
        # (PostgreSQL fails, falls back to SQLite, which also fails, returns [])
        results = search_service.search("test query")
        assert results == []
    
    def test_search_with_metadata(self, search_service, mock_db):
        """Test search with metadata"""
        # Setup mock database result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_db.execute.return_value = mock_result
        
        # Execute search with metadata
        result = search_service.search_with_metadata("test query", limit=10)
        
        # Verify metadata structure
        assert 'results' in result
        assert 'total_results' in result
        assert 'search_type' in result
        assert 'query' in result
        assert 'limit' in result
        assert result['search_type'] == 'lexical'
        assert result['query'] == 'test query'
        assert result['limit'] == 10
    
    def test_search_empty_results(self, search_service, mock_db):
        """Test search with empty results"""
        # Setup mock database result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_db.execute.return_value = mock_result
        
        # Execute search
        results = search_service.search("test query")
        
        # Verify empty results
        assert len(results) == 0
    
    def test_expand_query_synonyms_evidence(self, search_service):
        """Test synonym expansion for 'evidence' query"""
        # Test that "evidence" expands to include synonyms
        expanded = search_service._expand_query_synonyms("evidence")
        
        # Should contain original query
        assert "evidence" in expanded.lower()
        # Should contain synonyms
        assert "supporting" in expanded.lower() or "documents" in expanded.lower()
    
    def test_expand_query_synonyms_evidence_with_context(self, search_service):
        """Test synonym expansion for 'evidence for 5.22.1' query"""
        # Test that "evidence for 5.22.1" expands to include synonyms
        expanded = search_service._expand_query_synonyms("evidence for 5.22.1")
        
        # Should contain original query terms
        assert "evidence" in expanded.lower()
        # Should contain synonyms
        assert "supporting" in expanded.lower() or "documents" in expanded.lower()
    
    def test_expand_query_synonyms_supporting_documents(self, search_service):
        """Test synonym expansion for 'supporting documents' query"""
        # Test that "supporting documents" expands to include synonyms
        expanded = search_service._expand_query_synonyms("supporting documents")
        
        # Should contain original query
        assert "supporting" in expanded.lower() and "documents" in expanded.lower()
        # Should contain synonyms
        assert "evidence" in expanded.lower()
    
    def test_expand_query_synonyms_no_synonyms(self, search_service):
        """Test synonym expansion for query with no synonyms"""
        # Test that query with no synonyms returns unchanged
        query = "random query"
        expanded = search_service._expand_query_synonyms(query)
        
        # Should return original query unchanged
        assert expanded == query
    
    def test_expand_query_synonyms_case_insensitive(self, search_service):
        """Test that synonym expansion works case-insensitively"""
        # Test with uppercase
        expanded_upper = search_service._expand_query_synonyms("EVIDENCE")
        # Test with lowercase
        expanded_lower = search_service._expand_query_synonyms("evidence")
        
        # Both should expand (contain synonyms)
        assert "supporting" in expanded_upper.lower() or "documents" in expanded_upper.lower()
        assert "supporting" in expanded_lower.lower() or "documents" in expanded_lower.lower()