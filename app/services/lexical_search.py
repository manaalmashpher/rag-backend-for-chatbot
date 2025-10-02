"""
Lexical search service using PostgreSQL full-text search
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LexicalSearchService:
    """
    Handles lexical keyword search using PostgreSQL full-text search
    """
    
    def __init__(self):
        self.topk_lex = getattr(settings, 'topk_lex', 20)
        self.database_url = settings.database_url
    
    def search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform lexical keyword search using PostgreSQL full-text search
        
        Args:
            query: Search query string
            limit: Maximum number of results (defaults to topk_lex)
            
        Returns:
            List of search results with metadata
        """
        # Set limit
        search_limit = limit or self.topk_lex
        
        # Get database connection
        db = next(get_db())
        
        try:
            # Check if we're using PostgreSQL
            if self.database_url.startswith('postgresql://'):
                return self._postgresql_search(query, search_limit, db)
            else:
                # Fallback to LIKE search for SQLite
                return self._sqlite_like_search(query, search_limit, db)
                
        except Exception as e:
            logger.error(f"Lexical search failed: {str(e)}")
            raise RuntimeError(f"Lexical search failed: {str(e)}")
        finally:
            db.close()
    
    def _postgresql_search(self, query: str, search_limit: int, db) -> List[Dict[str, Any]]:
        """PostgreSQL full-text search"""
        try:
            fts_query = """
            SELECT 
                c.id as chunk_id,
                c.doc_id,
                c.method,
                c.page_from,
                c.page_to,
                c.hash,
                d.title as source,
                c.text,
                ts_rank(to_tsvector('english', c.text), plainto_tsquery('english', :query)) as rank_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.id
            WHERE to_tsvector('english', c.text) @@ plainto_tsquery('english', :query)
            ORDER BY rank_score DESC, c.id DESC
            LIMIT :limit
            """
            
            result = db.execute(text(fts_query), {"query": query, "limit": search_limit})
            
            formatted_results = []
            for row in result:
                formatted_result = {
                    'chunk_id': f"ch_{row.chunk_id:05d}",
                    'doc_id': f"doc_{row.doc_id:02X}",
                    'method': int(row.method),
                    'page_from': int(row.page_from) if row.page_from else None,
                    'page_to': int(row.page_to) if row.page_to else None,
                    'hash': str(row.hash),
                    'source': str(row.source),
                    'text': str(row.text),
                    'score': float(row.rank_score),
                    'search_type': 'lexical'
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"PostgreSQL lexical search completed: {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {str(e)}")
            # Fallback to LIKE search
            return self._sqlite_like_search(query, search_limit, db)
    
    def _sqlite_like_search(self, query: str, search_limit: int, db) -> List[Dict[str, Any]]:
        """Fallback LIKE search for SQLite"""
        try:
            like_query = """
            SELECT 
                c.id as chunk_id,
                c.doc_id,
                c.method,
                c.page_from,
                c.page_to,
                c.hash,
                d.title as source,
                c.text,
                1.0 as rank_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.id
            WHERE c.text LIKE :query
            ORDER BY c.id DESC
            LIMIT :limit
            """
            
            result = db.execute(text(like_query), {"query": f"%{query}%", "limit": search_limit})
            
            formatted_results = []
            for row in result:
                # Calculate relevance score for LIKE search
                relevance_score = self._calculate_relevance_score(row.text, query)
                
                formatted_result = {
                    'chunk_id': f"ch_{row.chunk_id:05d}",
                    'doc_id': f"doc_{row.doc_id:02X}",
                    'method': int(row.method),
                    'page_from': int(row.page_from) if row.page_from else None,
                    'page_to': int(row.page_to) if row.page_to else None,
                    'hash': str(row.hash),
                    'source': str(row.source),
                    'text': str(row.text),
                    'score': float(relevance_score),
                    'search_type': 'lexical'
                }
                formatted_results.append(formatted_result)
            
            # Sort by relevance score (highest first)
            formatted_results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"SQLite LIKE search completed: {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"SQLite LIKE search failed: {str(e)}")
            return []
    
    def search_with_metadata(self, query: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform lexical search with additional metadata
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            Dictionary with results and metadata
        """
        try:
            results = self.search(query, limit)
            
            return {
                'results': results,
                'total_results': len(results),
                'search_type': 'lexical',
                'query': query,
                'limit': limit or self.topk_lex
            }
            
        except Exception as e:
            logger.error(f"Lexical search with metadata failed: {str(e)}")
            raise RuntimeError(f"Lexical search with metadata failed: {str(e)}")
    
    def _calculate_relevance_score(self, text: str, query: str) -> float:
        """
        Calculate relevance score based on query term matches
        
        Args:
            text: Text content to score
            query: Search query
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not text or not query:
            return 0.0
        
        text_lower = text.lower()
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        if not query_terms:
            return 0.0
        
        # Simple scoring: count query term matches
        match_count = sum(1 for term in query_terms if term in text_lower)
        relevance_score = min(1.0, match_count / len(query_terms))
        
        return relevance_score
