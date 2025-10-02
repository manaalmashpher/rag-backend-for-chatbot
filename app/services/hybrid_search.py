"""
Hybrid search service combining semantic and lexical search
"""

from typing import List, Dict, Any, Optional
import logging
from app.services.vector_search import VectorSearchService
from app.services.lexical_search import LexicalSearchService
from app.core.config import settings

logger = logging.getLogger(__name__)

class HybridSearchService:
    """
    Combines semantic and lexical search results using configurable fusion weights
    """
    
    def __init__(self):
        self.vector_search = VectorSearchService()
        self.lexical_search = LexicalSearchService()
        self.semantic_weight = getattr(settings, 'fuse_sem_weight', 0.6)
        self.lexical_weight = getattr(settings, 'fuse_lex_weight', 0.4)
        self.topk_vec = getattr(settings, 'topk_vec', 20)
        self.topk_lex = getattr(settings, 'topk_lex', 20)
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and lexical results
        
        Args:
            query: Natural language query string
            limit: Maximum number of final results to return
            
        Returns:
            List of fused search results ranked by combined score
        """
        try:
            # Perform both searches in parallel using threading
            import concurrent.futures
            import threading
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both searches to run in parallel
                semantic_future = executor.submit(self.vector_search.search, query, self.topk_vec)
                lexical_future = executor.submit(self.lexical_search.search, query, self.topk_lex)
                
                # Wait for both to complete
                semantic_results = semantic_future.result()
                lexical_results = lexical_future.result()
            
            # Fuse results
            fused_results = self._fuse_results(semantic_results, lexical_results)
            
            # Return top results
            final_results = fused_results[:limit]
            
            logger.info(f"Hybrid search completed: {len(final_results)} results for query: {query[:50]}...")
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise RuntimeError(f"Hybrid search failed: {str(e)}")
    
    def _fuse_results(self, semantic_results: List[Dict[str, Any]], lexical_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fuse semantic and lexical search results using configurable weights
        
        Args:
            semantic_results: Results from vector search
            lexical_results: Results from lexical search
            
        Returns:
            List of fused results ranked by combined score
        """
        # Create a dictionary to store fused results by chunk_id
        fused_dict = {}
        
        # Process semantic results
        for result in semantic_results:
            chunk_id = result.get('chunk_id')
            if chunk_id:
                # Normalize semantic score to 0-1 range
                normalized_score = max(0.0, min(1.0, result.get('score', 0.0)))
                fused_score = normalized_score * self.semantic_weight
                
                fused_dict[chunk_id] = {
                    **result,
                    'semantic_score': normalized_score,
                    'lexical_score': 0.0,
                    'fused_score': fused_score,
                    'sources': ['semantic']
                }
        
        # Process lexical results
        for result in lexical_results:
            chunk_id = result.get('chunk_id')
            if chunk_id:
                # Normalize lexical score to 0-1 range (FTS5 rank is typically 0-1)
                normalized_score = max(0.0, min(1.0, result.get('score', 0.0)))
                lexical_score = normalized_score * self.lexical_weight
                
                if chunk_id in fused_dict:
                    # Combine with existing semantic result
                    fused_dict[chunk_id]['lexical_score'] = normalized_score
                    fused_dict[chunk_id]['fused_score'] += lexical_score
                    fused_dict[chunk_id]['sources'].append('lexical')
                else:
                    # New lexical-only result
                    fused_dict[chunk_id] = {
                        **result,
                        'semantic_score': 0.0,
                        'lexical_score': normalized_score,
                        'fused_score': lexical_score,
                        'sources': ['lexical']
                    }
        
        # Convert to list and sort by fused score
        fused_results = list(fused_dict.values())
        fused_results.sort(key=lambda x: x['fused_score'], reverse=True)
        
        return fused_results
    
    def search_with_metadata(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Perform hybrid search with detailed metadata
        
        Args:
            query: Natural language query string
            limit: Maximum number of final results
            
        Returns:
            Dictionary with results and comprehensive metadata
        """
        try:
            # Get individual search results for metadata
            semantic_metadata = self.vector_search.search_with_metadata(query, self.topk_vec)
            lexical_metadata = self.lexical_search.search_with_metadata(query, self.topk_lex)
            
            # Perform hybrid search
            results = self.search(query, limit)
            
            return {
                'results': results,
                'total_results': len(results),
                'search_type': 'hybrid',
                'query': query,
                'limit': limit,
                'fusion_weights': {
                    'semantic': self.semantic_weight,
                    'lexical': self.lexical_weight
                },
                'individual_results': {
                    'semantic': semantic_metadata['total_results'],
                    'lexical': lexical_metadata['total_results']
                }
            }
            
        except Exception as e:
            logger.error(f"Hybrid search with metadata failed: {str(e)}")
            raise RuntimeError(f"Hybrid search with metadata failed: {str(e)}")
