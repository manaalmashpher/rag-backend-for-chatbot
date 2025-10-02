"""
Database initialization service for PostgreSQL full-text search
"""

from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseInitService:
    """
    Handles database initialization including PostgreSQL full-text search setup
    """
    
    @staticmethod
    def ensure_fulltext_indexes():
        """
        Ensure full-text search indexes exist for PostgreSQL
        """
        try:
            db = next(get_db())
            
            # Check if we're using PostgreSQL
            if not settings.database_url.startswith('postgresql://'):
                logger.info("Not using PostgreSQL, skipping full-text index creation")
                return
            
            # Create GIN index for full-text search on chunks.text
            create_index_query = """
            CREATE INDEX IF NOT EXISTS idx_chunks_text_gin 
            ON chunks USING gin(to_tsvector('english', text))
            """
            db.execute(text(create_index_query))
            
            # Create hash index for batch fetching chunk text
            hash_index_query = """
            CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(hash)
            """
            db.execute(text(hash_index_query))
            
            db.commit()
            logger.info("PostgreSQL full-text search indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL indexes: {str(e)}")
            # Don't raise error - indexes are optional for basic functionality
            logger.warning("Continuing without full-text search indexes")
        finally:
            db.close()
    
    @staticmethod
    def initialize_search_infrastructure():
        """
        Initialize PostgreSQL search infrastructure
        """
        try:
            DatabaseInitService.ensure_fulltext_indexes()
            logger.info("PostgreSQL search infrastructure initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL search infrastructure: {str(e)}")
            # Don't raise error - search will still work with basic queries
            logger.warning("Continuing without optimized search infrastructure")
