"""
Integration tests for search endpoint
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

class TestSearchEndpoint:
    """Test search endpoint functionality"""
    
    @patch('app.services.hybrid_search.HybridSearchService.search_with_metadata')
    def test_search_success(self, mock_search):
        """Test successful search"""
        # Mock search results
        mock_search.return_value = {
            'results': [
                {
                    'chunk_id': '1',
                    'doc_id': '1',
                    'method': 1,
                    'page_from': 1,
                    'page_to': 1,
                    'hash': 'hash1',
                    'source': 'Test Document',
                    'text': 'This is about machine learning and AI.',
                    'fused_score': 0.9
                },
                {
                    'chunk_id': '2',
                    'doc_id': '1',
                    'method': 1,
                    'page_from': 2,
                    'page_to': 2,
                    'hash': 'hash2',
                    'source': 'Test Document',
                    'text': 'Machine learning is a subset of artificial intelligence.',
                    'fused_score': 0.8
                }
            ],
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 2, 'lexical': 2}
        }
        
        response = client.get("/api/search?q=machine learning")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check search results
        assert len(data['results']) == 2
        assert data['total_results'] == 2
        assert data['query'] == 'machine learning'
        assert data['search_type'] == 'hybrid'
        
        # Check result structure
        result = data['results'][0]
        assert 'chunk_id' in result
        assert 'doc_id' in result
        assert 'method' in result
        assert 'page_from' in result
        assert 'page_to' in result
        assert 'hash' in result
        assert 'source' in result
        assert 'snippet' in result
        assert 'score' in result
        assert 'search_type' in result
    
    @patch('app.services.hybrid_search.HybridSearchService.search_with_metadata')
    def test_search_with_limit(self, mock_search):
        """Test search with custom limit"""
        # Mock search results
        mock_search.return_value = {
            'results': [
                {
                    'chunk_id': '1',
                    'doc_id': '1',
                    'method': 1,
                    'page_from': 1,
                    'page_to': 1,
                    'hash': 'hash1',
                    'source': 'Test Document',
                    'text': 'This is about machine learning.',
                    'fused_score': 0.9
                }
            ],
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 1, 'lexical': 0}
        }
        
        response = client.get("/api/search?q=machine learning&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check search results
        assert len(data['results']) == 1
        assert data['total_results'] == 1
        assert data['limit'] == 5
    
    def test_search_validation_errors(self):
        """Test search endpoint validation errors"""
        # Test empty query
        response = client.get("/api/search?q=")
        assert response.status_code == 422  # Validation error
        
        # Test query too long
        long_query = "a" * 501
        response = client.get(f"/api/search?q={long_query}")
        assert response.status_code == 422  # Validation error
        
        # Test invalid limit
        response = client.get("/api/search?q=test&limit=100")
        assert response.status_code == 422  # Validation error
        
        # Test negative limit
        response = client.get("/api/search?q=test&limit=0")
        assert response.status_code == 422  # Validation error
    
    @patch('app.services.hybrid_search.HybridSearchService.search_with_metadata')
    def test_search_response_structure(self, mock_search):
        """Test search response structure and metadata"""
        # Mock search results
        mock_search.return_value = {
            'results': [
                {
                    'chunk_id': '1',
                    'doc_id': '1',
                    'method': 1,
                    'page_from': 1,
                    'page_to': 1,
                    'hash': 'hash1',
                    'source': 'Test Document',
                    'text': 'This is about machine learning.',
                    'fused_score': 0.9
                }
            ],
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 1, 'lexical': 0}
        }
        
        response = client.get("/api/search?q=machine learning&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert 'results' in data
        assert 'total_results' in data
        assert 'query' in data
        assert 'limit' in data
        assert 'search_type' in data
        assert 'metadata' in data
        assert 'latency_ms' in data
        
        # Check metadata structure
        metadata = data['metadata']
        assert 'semantic_weight' in metadata
        assert 'lexical_weight' in metadata
        assert 'individual_results' in metadata
        assert 'latency_ms' in metadata
        
        # Check result structure
        result = data['results'][0]
        assert 'chunk_id' in result
        assert 'doc_id' in result
        assert 'method' in result
        assert 'page_from' in result
        assert 'page_to' in result
        assert 'hash' in result
        assert 'source' in result
        assert 'snippet' in result
        assert 'score' in result
        assert 'search_type' in result
    
    @patch('app.services.hybrid_search.HybridSearchService.search_with_metadata')
    def test_search_empty_results(self, mock_search):
        """Test search with empty results"""
        # Mock empty search results
        mock_search.return_value = {
            'results': [],
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 0, 'lexical': 0}
        }
        
        response = client.get("/api/search?q=nonexistent")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check empty search results
        assert len(data['results']) == 0
        assert data['total_results'] == 0
        assert data['query'] == 'nonexistent'
    
    @patch('app.services.hybrid_search.HybridSearchService.search_with_metadata')
    def test_search_error_handling(self, mock_search):
        """Test search error handling"""
        # Mock search service error
        mock_search.side_effect = Exception("Search service error")
        
        response = client.get("/api/search?q=test")
        
        assert response.status_code == 500
        data = response.json()
        assert data['detail']['error'] == 'Internal search error'
        assert data['detail']['error_code'] == 'SEARCH_ERROR'
