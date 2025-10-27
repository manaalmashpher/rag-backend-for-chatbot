"""
Reranking service using cross-encoder for improved search result quality
"""

from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import CrossEncoder
from app.core.config import settings

logger = logging.getLogger(__name__)

class RerankerService:
    """
    Handles reranking of search results using cross-encoder model
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(RerankerService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the reranking service with singleton model loading"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.batch_size = getattr(settings, 'rerank_batch_size', 16)
            self.max_chars = getattr(settings, 'rerank_max_chars', 2000)
            self.top_r = getattr(settings, 'rerank_top_r', 10)
            self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model once using singleton pattern"""
        try:
            if RerankerService._model is None:
                logger.info("Loading cross-encoder model: cross-encoder/ms-marco-MiniLM-L-6-v2")
                RerankerService._model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {str(e)}")
            raise RuntimeError(f"Failed to load cross-encoder model: {str(e)}")
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_r: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder model
        
        Args:
            query: Search query string
            candidates: List of candidate results from hybrid search
            top_r: Maximum number of results to return (defaults to config)
            
        Returns:
            List of reranked results with rerank_score added
        """
        try:
            if not candidates:
                logger.info("No candidates provided for reranking")
                return []
            
            # Use provided top_r or default from config
            limit = top_r or self.top_r
            
            # Build query-text pairs
            pairs = self._build_query_text_pairs(query, candidates)
            
            if not pairs:
                logger.warning("No valid query-text pairs could be built")
                return candidates[:limit]
            
            # Run model prediction in batches
            scores = self._predict_scores_batched(pairs)
            
            # Add rerank scores to candidates and sort
            reranked_results = self._add_scores_and_sort(candidates, scores)
            
            # Return top results
            final_results = reranked_results[:limit]
            
            logger.info(f"Reranked {len(candidates)} candidates to {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Reranking failed: {str(e)}")
            # Graceful fallback - return original candidates
            logger.warning("Falling back to original candidates due to reranking failure")
            return candidates[:top_r or self.top_r]
    
    def _build_query_text_pairs(self, query: str, candidates: List[Dict[str, Any]]) -> List[tuple]:
        """
        Build query-text pairs for cross-encoder prediction
        
        Args:
            query: Search query string
            candidates: List of candidate results
            
        Returns:
            List of (query, text) tuples
        """
        pairs = []
        
        for candidate in candidates:
            # Extract text from candidate
            text = candidate.get('text', '')
            if not text:
                # Try alternative text fields
                text = candidate.get('snippet', '') or candidate.get('content', '')
            
            if text:
                # Truncate text to max_chars for memory management
                if len(text) > self.max_chars:
                    text = text[:self.max_chars]
                    logger.debug(f"Truncated text from {len(candidate.get('text', ''))} to {self.max_chars} chars")
                
                pairs.append((query, text))
            else:
                logger.warning(f"Candidate missing text field: {candidate.get('chunk_id', 'unknown')}")
        
        return pairs
    
    def _predict_scores_batched(self, pairs: List[tuple]) -> List[float]:
        """
        Run cross-encoder prediction in batches for efficiency
        
        Args:
            pairs: List of (query, text) tuples
            
        Returns:
            List of prediction scores
        """
        if RerankerService._model is None:
            raise RuntimeError("Cross-encoder model not loaded")
        
        all_scores = []
        
        # Process in batches
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i:i + self.batch_size]
            
            try:
                batch_scores = RerankerService._model.predict(batch)
                all_scores.extend(batch_scores.tolist())
                logger.debug(f"Processed batch {i//self.batch_size + 1}: {len(batch)} pairs")
                
            except Exception as e:
                logger.error(f"Batch prediction failed: {str(e)}")
                # Use default scores for failed batch
                all_scores.extend([0.0] * len(batch))
        
        return all_scores
    
    def _add_scores_and_sort(self, candidates: List[Dict[str, Any]], scores: List[float]) -> List[Dict[str, Any]]:
        """
        Add rerank scores to candidates and sort by score descending
        
        Args:
            candidates: Original candidate results
            scores: Prediction scores from cross-encoder
            
        Returns:
            List of candidates with rerank_score added, sorted by score
        """
        if len(scores) != len(candidates):
            logger.warning(f"Score count ({len(scores)}) doesn't match candidate count ({len(candidates)})")
            # Pad or truncate scores to match candidates
            if len(scores) < len(candidates):
                scores.extend([0.0] * (len(candidates) - len(scores)))
            else:
                scores = scores[:len(candidates)]
        
        # Add rerank scores to candidates
        for i, candidate in enumerate(candidates):
            candidate['rerank_score'] = float(scores[i])
        
        # Sort by rerank score descending
        sorted_candidates = sorted(candidates, key=lambda x: x.get('rerank_score', 0.0), reverse=True)
        
        return sorted_candidates
    
    def is_available(self) -> bool:
        """
        Check if the reranking service is available
        
        Returns:
            True if model is loaded and ready
        """
        return RerankerService._model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
            'is_loaded': self.is_available(),
            'batch_size': self.batch_size,
            'max_chars': self.max_chars,
            'top_r': self.top_r
        }
