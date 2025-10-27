"""
Unit tests for reranking service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from app.services.reranker import RerankerService


class TestRerankerService:
    """Test cases for RerankerService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Reset singleton instance for each test
        RerankerService._instance = None
        RerankerService._model = None
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Reset singleton instance
        RerankerService._instance = None
        RerankerService._model = None
    
    @patch('app.services.reranker.CrossEncoder')
    def test_singleton_pattern(self, mock_cross_encoder):
        """Test that singleton pattern works correctly"""
        # Mock the model
        mock_model = Mock()
        mock_cross_encoder.return_value = mock_model
        
        # Create two instances
        service1 = RerankerService()
        service2 = RerankerService()
        
        # Should be the same instance
        assert service1 is service2
        assert RerankerService._instance is service1
        
        # Model should only be loaded once
        mock_cross_encoder.assert_called_once_with('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    @patch('app.services.reranker.CrossEncoder')
    def test_model_loading_success(self, mock_cross_encoder):
        """Test successful model loading"""
        mock_model = Mock()
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        assert service.is_available() is True
        assert RerankerService._model is mock_model
        
        model_info = service.get_model_info()
        assert model_info['model_name'] == 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        assert model_info['is_loaded'] is True
    
    @patch('app.services.reranker.CrossEncoder')
    def test_model_loading_failure(self, mock_cross_encoder):
        """Test model loading failure handling"""
        mock_cross_encoder.side_effect = Exception("Model loading failed")
        
        with pytest.raises(RuntimeError, match="Failed to load cross-encoder model"):
            RerankerService()
        
        assert RerankerService._model is None
    
    @patch('app.services.reranker.CrossEncoder')
    def test_rerank_empty_candidates(self, mock_cross_encoder):
        """Test reranking with empty candidates list"""
        mock_model = Mock()
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        result = service.rerank("test query", [])
        
        assert result == []
    
    @patch('app.services.reranker.CrossEncoder')
    def test_rerank_successful(self, mock_cross_encoder):
        """Test successful reranking"""
        # Mock model and prediction
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.8, 0.6, 0.9])
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        candidates = [
            {'chunk_id': '1', 'text': 'First document about cats'},
            {'chunk_id': '2', 'text': 'Second document about dogs'},
            {'chunk_id': '3', 'text': 'Third document about birds'}
        ]
        
        result = service.rerank("cats", candidates, top_r=2)
        
        # Should return top 2 results
        assert len(result) == 2
        
        # Should have rerank_score added
        assert 'rerank_score' in result[0]
        assert 'rerank_score' in result[1]
        
        # Should be sorted by rerank_score descending
        assert result[0]['rerank_score'] >= result[1]['rerank_score']
        
        # Should preserve original fields
        assert 'chunk_id' in result[0]
        assert 'text' in result[0]
    
    @patch('app.services.reranker.CrossEncoder')
    def test_text_truncation(self, mock_cross_encoder):
        """Test text truncation to max_chars"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5])
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        # Create text longer than max_chars
        long_text = "a" * 3000  # Longer than default 2000
        candidates = [{'chunk_id': '1', 'text': long_text}]
        
        result = service.rerank("test", candidates)
        
        # Should truncate text internally and still work
        assert len(result) == 1
        assert 'rerank_score' in result[0]
    
    @patch('app.services.reranker.CrossEncoder')
    def test_batch_processing(self, mock_cross_encoder):
        """Test batch processing with large candidate list"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5] * 16)  # Batch size
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        # Create more candidates than batch size
        candidates = [{'chunk_id': str(i), 'text': f'Document {i}'} for i in range(20)]
        
        result = service.rerank("test", candidates)
        
        # Should call predict multiple times for batching
        assert mock_model.predict.call_count >= 2  # At least 2 batches for 20 items
    
    @patch('app.services.reranker.CrossEncoder')
    def test_missing_text_field(self, mock_cross_encoder):
        """Test handling of candidates without text field"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5])
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        candidates = [
            {'chunk_id': '1', 'text': 'Valid text'},
            {'chunk_id': '2'},  # Missing text
            {'chunk_id': '3', 'snippet': 'Alternative text field'}
        ]
        
        result = service.rerank("test", candidates)
        
        # Should handle missing text gracefully
        assert len(result) <= len(candidates)
    
    @patch('app.services.reranker.CrossEncoder')
    def test_rerank_failure_fallback(self, mock_cross_encoder):
        """Test graceful fallback when reranking fails"""
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Prediction failed")
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        candidates = [
            {'chunk_id': '1', 'text': 'First document'},
            {'chunk_id': '2', 'text': 'Second document'}
        ]
        
        result = service.rerank("test", candidates, top_r=1)
        
        # Should fallback to original candidates
        assert len(result) == 1
        assert result[0]['chunk_id'] == '1'
        # Should have rerank_score with default value due to fallback handling
        assert 'rerank_score' in result[0]
        assert result[0]['rerank_score'] == 0.0
    
    @patch('app.services.reranker.CrossEncoder')
    def test_score_mismatch_handling(self, mock_cross_encoder):
        """Test handling when score count doesn't match candidate count"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5])  # Only 1 score for 2 candidates
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        candidates = [
            {'chunk_id': '1', 'text': 'First document'},
            {'chunk_id': '2', 'text': 'Second document'}
        ]
        
        result = service.rerank("test", candidates)
        
        # Should handle mismatch gracefully
        assert len(result) == 2
        assert 'rerank_score' in result[0]
        assert 'rerank_score' in result[1]
    
    @patch('app.services.reranker.CrossEncoder')
    def test_configuration_parameters(self, mock_cross_encoder):
        """Test configuration parameters are properly set"""
        mock_model = Mock()
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        model_info = service.get_model_info()
        assert model_info['batch_size'] == 16
        assert model_info['max_chars'] == 2000
        assert model_info['top_r'] == 10
    
    @patch('app.services.reranker.CrossEncoder')
    def test_alternative_text_fields(self, mock_cross_encoder):
        """Test handling of alternative text fields (snippet, content)"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5])
        mock_cross_encoder.return_value = mock_model
        
        service = RerankerService()
        
        candidates = [
            {'chunk_id': '1', 'snippet': 'Snippet text'},
            {'chunk_id': '2', 'content': 'Content text'},
            {'chunk_id': '3', 'other_field': 'Other text'}  # No recognized text field
        ]
        
        result = service.rerank("test", candidates)
        
        # Should handle alternative text fields
        assert len(result) >= 2  # At least snippet and content should work
