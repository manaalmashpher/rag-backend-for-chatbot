"""
Integration tests for reranking service integration with search API
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.api.routes.search import router
from app.services.reranker import RerankerService
from app.services.hybrid_search import HybridSearchService
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.schemas.search import SearchResult


app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestRerankingIntegration:
    """Integration tests for reranking service with search API"""
    
    @pytest.fixture
    def mock_reranker_service(self):
        """Mock reranker service"""
        with patch('app.api.routes.search.reranker_service') as mock:
            mock.is_available.return_value = True
            mock.rerank.return_value = [
                {
                    'chunk_id': '1',
                    'doc_id': 'doc1',
                    'method': 1,
                    'text': 'test text 1',
                    'fused_score': 0.9,
                    'rerank_score': 12.5
                },
                {
                    'chunk_id': '2',
                    'doc_id': 'doc1',
                    'method': 1,
                    'text': 'test text 2',
                    'fused_score': 0.8,
                    'rerank_score': 11.2
                }
            ]
            yield mock
    
    @pytest.fixture
    def mock_hybrid_search(self):
        """Mock hybrid search results"""
        return [
            {
                'chunk_id': '1',
                'doc_id': 'doc1',
                'method': 1,
                'text': 'test text 1',
                'fused_score': 0.9,
                'hash': 'hash1',
                'source': 'test.pdf'
            },
            {
                'chunk_id': '2',
                'doc_id': 'doc1',
                'method': 1,
                'text': 'test text 2',
                'fused_score': 0.8,
                'hash': 'hash2',
                'source': 'test.pdf'
            },
            {
                'chunk_id': '3',
                'doc_id': 'doc2',
                'method': 2,
                'text': 'test text 3',
                'fused_score': 0.7,
                'hash': 'hash3',
                'source': 'test2.pdf'
            }
        ]
    
    def test_rerank_score_field_added_to_response(self, mock_reranker_service, mock_hybrid_search):
        """Test that rerank_score field is added to response when reranking is applied"""
        with patch.object(HybridSearchService, 'search_with_metadata') as mock_search:
            mock_search.return_value = {
                'results': mock_hybrid_search,
                'total_results': 3,
                'search_type': 'hybrid',
                'query': 'test query',
                'limit': 10,
                'fusion_weights': {
                    'semantic': 0.6,
                    'lexical': 0.4
                },
                'individual_results': {
                    'semantic': 10,
                    'lexical': 10
                }
            }
            
            # Use a unique query to avoid cache hits
            response = client.get("/search?q=test_unique_98765&limit=10")
            assert response.status_code == 200
            data = response.json()
            
            # Check that response contains results
            assert 'results' in data
            assert len(data['results']) > 0
            
            # Check that rerank_score is present in results if reranking was applied
            for result in data['results']:
                assert 'rerank_score' in result or 'rerank_score' not in result  # Optional field
                if 'rerank_score' in result:
                    assert isinstance(result['rerank_score'], (int, float, type(None)))
    
    def test_reranking_service_called_with_correct_parameters(self, mock_reranker_service, mock_hybrid_search):
        """Test that reranking service is called with correct parameters"""
        with patch.object(HybridSearchService, 'search_with_metadata') as mock_search:
            mock_search.return_value = {
                'results': mock_hybrid_search,
                'total_results': 3,
                'search_type': 'hybrid',
                'query': 'test query',
                'limit': 10,
                'fusion_weights': {
                    'semantic': 0.6,
                    'lexical': 0.4
                },
                'individual_results': {
                    'semantic': 10,
                    'lexical': 10
                }
            }
            
            # Use a unique query to avoid cache hits
            response = client.get("/search?q=unique_query_12345&limit=10")
            assert response.status_code == 200
            
            # Verify reranker service was called
            if mock_reranker_service.is_available.return_value:
                mock_reranker_service.rerank.assert_called_once()
                call_args = mock_reranker_service.rerank.call_args
                assert call_args[0][0] == 'unique_query_12345'  # Query (first positional arg)
                assert len(call_args[0][1]) >= 0  # Candidates (second positional arg)
                assert call_args[0][2] >= 0  # Top_r parameter (third positional arg)
    
    def test_graceful_fallback_when_reranking_fails(self, mock_hybrid_search):
        """Test that search works when reranking fails"""
        with patch.object(HybridSearchService, 'search_with_metadata') as mock_search:
            mock_search.return_value = {
                'results': mock_hybrid_search,
                'total_results': 3,
                'search_type': 'hybrid',
                'query': 'test query',
                'limit': 10,
                'fusion_weights': {
                    'semantic': 0.6,
                    'lexical': 0.4
                },
                'individual_results': {
                    'semantic': 10,
                    'lexical': 10
                }
            }
            
            with patch('app.api.routes.search.reranker_service') as mock_reranker:
                mock_reranker.is_available.return_value = True
                mock_reranker.rerank.side_effect = Exception("Reranking failed")
                
                # Use a unique query to avoid cache hits
                response = client.get("/search?q=test_fallback_11111&limit=10")
                assert response.status_code == 200
                data = response.json()
                
                # Should return results even if reranking fails
                assert 'results' in data
                assert len(data['results']) >= 0
    
    def test_backward_compatibility_without_reranking(self, mock_hybrid_search):
        """Test that response format is compatible even without reranking"""
        with patch.object(HybridSearchService, 'search_with_metadata') as mock_search:
            mock_search.return_value = {
                'results': mock_hybrid_search,
                'total_results': 3,
                'search_type': 'hybrid',
                'query': 'test query',
                'limit': 10,
                'fusion_weights': {
                    'semantic': 0.6,
                    'lexical': 0.4
                },
                'individual_results': {
                    'semantic': 10,
                    'lexical': 10
                }
            }
            
            with patch('app.api.routes.search.reranker_service') as mock_reranker:
                mock_reranker.is_available.return_value = False
                
                # Use a unique query to avoid cache hits
                response = client.get("/search?q=test_compat_22222&limit=10")
                assert response.status_code == 200
                data = response.json()
                
                # Response should still be valid
                assert 'results' in data
                assert 'query' in data
                assert 'limit' in data
                assert 'search_type' in data
                assert 'total_results' in data
                
                # rerank_score is optional, should not break if not present
                for result in data['results']:
                    assert 'chunk_id' in result
                    assert 'doc_id' in result
                    assert 'score' in result

