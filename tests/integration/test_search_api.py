"""
Integration tests for search API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app

client = TestClient(app)

class TestSearchAPI:
    """Test cases for search API endpoints"""
    
    @patch('app.api.routes.search.search_service')
    def test_search_endpoint_success(self, mock_search_service):
        """Test successful search API call"""
        # Setup mock - search_service is already the mock instance
        mock_search_service.search_with_metadata.return_value = {
            'results': [
                {
                    'chunk_id': 'ch_00001',
                    'doc_id': 'doc_01',
                    'method': 1,
                    'page_from': 1,
                    'page_to': 2,
                    'hash': 'abc123',
                    'source': 'test.pdf',
                    'text': 'This is test content',
                    'fused_score': 0.85,
                    'sources': ['semantic', 'lexical']
                }
            ],
            'total_results': 1,
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 1, 'lexical': 1}
        }
        
        # Make API call with unique query to avoid cache hits
        response = client.get("/api/search?q=unique_test_query_123&limit=10")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert 'total_results' in data
        assert 'query' in data
        assert 'search_type' in data
        assert data['query'] == 'unique_test_query_123'
        # search_type can be 'hybrid' or 'hybrid-reranked' depending on reranking availability
        assert data['search_type'] in ['hybrid', 'hybrid-reranked']
        assert len(data['results']) == 1
        assert data['results'][0]['chunk_id'] == 'ch_00001'
    
    def test_search_endpoint_validation_error(self):
        """Test search API with invalid parameters"""
        # Test empty query
        response = client.get("/api/search?q=")
        assert response.status_code == 422  # FastAPI validation error
        
        # Test query too long
        long_query = "x" * 501
        response = client.get(f"/api/search?q={long_query}")
        assert response.status_code == 422  # FastAPI validation error
        
        # Test invalid limit
        response = client.get("/api/search?q=test&limit=0")
        assert response.status_code == 422
        
        response = client.get("/api/search?q=test&limit=51")
        assert response.status_code == 422
    
    @patch('app.api.routes.search.search_service')
    def test_search_endpoint_server_error(self, mock_search_service):
        """Test search API with server error"""
        # Setup mock to raise exception
        mock_search_service.search_with_metadata.side_effect = Exception("Search service error")
        
        # Make API call with unique query to avoid cache hits
        response = client.get("/api/search?q=unique_error_test_456")
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert 'detail' in data
        assert data['detail']['error_code'] == 'SEARCH_ERROR'
    
    @patch('app.api.routes.search.search_service')
    def test_search_endpoint_empty_results(self, mock_search_service):
        """Test search API with empty results"""
        # Setup mock
        mock_search_service.search_with_metadata.return_value = {
            'results': [],
            'total_results': 0,
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 0, 'lexical': 0}
        }
        
        # Make API call with unique query to avoid cache hits
        response = client.get("/api/search?q=unique_empty_test_789")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data['total_results'] == 0
        assert len(data['results']) == 0
    
    @patch('app.api.routes.search.search_service')
    def test_search_endpoint_with_metadata(self, mock_search_service):
        """Test search API response includes metadata"""
        # Setup mock
        mock_search_service.search_with_metadata.return_value = {
            'results': [],
            'total_results': 0,
            'fusion_weights': {'semantic': 0.6, 'lexical': 0.4},
            'individual_results': {'semantic': 5, 'lexical': 3}
        }
        
        # Make API call with unique query to avoid cache hits
        response = client.get("/api/search?q=unique_metadata_test_101&limit=10")
        
        # Verify response includes metadata
        assert response.status_code == 200
        data = response.json()
        assert 'metadata' in data
        assert 'semantic_weight' in data['metadata']
        assert 'lexical_weight' in data['metadata']
        assert 'individual_results' in data['metadata']
        assert data['metadata']['semantic_weight'] == 0.6
        assert data['metadata']['lexical_weight'] == 0.4
        assert data['metadata']['individual_results']['semantic'] == 5
        assert data['metadata']['individual_results']['lexical'] == 3
    
    def test_search_endpoint_missing_query(self):
        """Test search API without query parameter"""
        response = client.get("/api/search")
        assert response.status_code == 422  # Validation error for missing required parameter
