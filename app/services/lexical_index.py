"""
PostgreSQL Full-Text Search service
"""

from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class LexicalIndexService:
    """
    Handles PostgreSQL full-text search index creation and management
    """
    
    def create_fts_index(self, db: Session) -> bool:
        """
        Create full-text search index for chunks table using PostgreSQL
        
        Args:
            db: Database session
            
        Returns:
            True if successful
        """
        try:
            # Check if we're using PostgreSQL
            if not settings.database_url.startswith('postgresql://'):
                logger.info("Not using PostgreSQL, skipping FTS index creation")
                return True
            
            # Create GIN index for full-text search on chunks.text
            create_index_query = """
            CREATE INDEX IF NOT EXISTS idx_chunks_text_gin 
            ON chunks USING gin(to_tsvector('english', text))
            """
            db.execute(text(create_index_query))
            
            # Create additional indexes for performance
            performance_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)",
                "CREATE INDEX IF NOT EXISTS idx_chunks_method ON chunks(method)",
            ]
            
            for index_query in performance_indexes:
                db.execute(text(index_query))
            
            db.commit()
            logger.info("PostgreSQL full-text search indexes created successfully")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create PostgreSQL FTS index: {str(e)}")
            # Don't raise error - indexes are optional for basic functionality
            return True
    
    def update_search_vectors(self, db: Session) -> bool:
        """
        Update search index for all chunks (PostgreSQL doesn't need rebuilding)
        
        Args:
            db: Database session
            
        Returns:
            True if successful
        """
        try:
            # PostgreSQL GIN indexes are automatically updated
            # No need to rebuild like SQLite FTS5
            logger.info("PostgreSQL indexes are automatically maintained")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update search vectors: {str(e)}")
            return True
    
    def search_text(self, query: str, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search chunks using PostgreSQL full-text search
        
        Args:
            query: Search query string
            db: Database session
            limit: Maximum number of results
            
        Returns:
            List of matching chunks with relevance scores
        """
        try:
            # Use PostgreSQL full-text search with ranking
            result = db.execute(text("""
                SELECT 
                    c.id,
                    c.doc_id,
                    c.text,
                    c.method,
                    c.page_from,
                    c.page_to,
                    c.hash,
                    ts_rank(to_tsvector('english', c.text), plainto_tsquery('english', :query)) as rank
                FROM chunks c
                WHERE to_tsvector('english', c.text) @@ plainto_tsquery('english', :query)
                ORDER BY rank DESC
                LIMIT :limit
            """), {"query": query, "limit": limit})
            
            return [
                {
                    'id': row.id,
                    'doc_id': row.doc_id,
                    'text': row.text,
                    'method': row.method,
                    'page_from': row.page_from,
                    'page_to': row.page_to,
                    'hash': row.hash,
                    'rank': float(row.rank) if row.rank else 0.0
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Failed to search text: {str(e)}")
            return []
    
    def add_chunk_to_index(self, chunk_id: str, chunk_text: str, db: Session) -> bool:
        """
        Add a single chunk to the search index (PostgreSQL indexes are automatic)
        
        Args:
            chunk_id: ID of the chunk to index (string)
            chunk_text: Text content of the chunk
            db: Database session
            
        Returns:
            True if successful
        """
        try:
            # PostgreSQL GIN indexes are automatically updated when data is inserted
            # No manual index management needed
            logger.info(f"Chunk {chunk_id} will be automatically indexed by PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add chunk to index: {str(e)}")
            return True
