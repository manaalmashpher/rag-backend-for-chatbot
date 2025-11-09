"""
Database migration script for adding hierarchy-aware chunking metadata fields

Run this script to add new columns and indexes to the chunks table.
Safe to run multiple times (idempotent).
"""

import logging
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError
from app.core.database import engine, Base
from app.models.database import Chunk

logger = logging.getLogger(__name__)


def migrate_chunks_table():
    """
    Add new metadata columns to chunks table if they don't exist
    
    This migration is idempotent - safe to run multiple times.
    """
    logger.info("Starting chunks table migration...")
    
    inspector = inspect(engine)
    existing_columns = {col['name'] for col in inspector.get_columns('chunks')}
    
    new_columns = {
        'section_id': 'ALTER TABLE chunks ADD COLUMN section_id VARCHAR(100)',
        'section_id_alias': 'ALTER TABLE chunks ADD COLUMN section_id_alias VARCHAR(100)',
        'title': 'ALTER TABLE chunks ADD COLUMN title VARCHAR(500)',
        'parent_titles': 'ALTER TABLE chunks ADD COLUMN parent_titles JSONB',
        'level': 'ALTER TABLE chunks ADD COLUMN level INTEGER',
        'list_items': 'ALTER TABLE chunks ADD COLUMN list_items BOOLEAN DEFAULT FALSE',
        'has_supporting_docs': 'ALTER TABLE chunks ADD COLUMN has_supporting_docs BOOLEAN DEFAULT FALSE',
        'token_count': 'ALTER TABLE chunks ADD COLUMN token_count INTEGER',
        'text_norm': 'ALTER TABLE chunks ADD COLUMN text_norm TEXT'
    }
    
    with engine.connect() as conn:
        # Add columns
        for col_name, sql in new_columns.items():
            if col_name not in existing_columns:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    logger.info(f"Added column: {col_name}")
                except ProgrammingError as e:
                    if 'already exists' not in str(e).lower():
                        logger.error(f"Failed to add column {col_name}: {e}")
                        raise
                    else:
                        logger.info(f"Column {col_name} already exists")
            else:
                logger.info(f"Column {col_name} already exists")
        
        # Create indexes
        indexes_to_create = [
            ('idx_chunks_section_id', 'CREATE INDEX IF NOT EXISTS idx_chunks_section_id ON chunks(section_id)'),
            ('idx_chunks_section_id_alias', 'CREATE INDEX IF NOT EXISTS idx_chunks_section_id_alias ON chunks(section_id_alias)'),
        ]
        
        # Check if we're using Postgres (for GIN index)
        db_url = str(engine.url)
        is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
        
        if is_postgres:
            # GIN index for JSONB parent_titles
            try:
                conn.execute(text(
                    'CREATE INDEX IF NOT EXISTS idx_chunks_parent_titles ON chunks USING GIN (parent_titles)'
                ))
                conn.commit()
                logger.info("Created GIN index on parent_titles")
            except ProgrammingError as e:
                if 'already exists' not in str(e).lower():
                    logger.warning(f"Failed to create GIN index: {e}")
                else:
                    logger.info("GIN index on parent_titles already exists")
        else:
            logger.info("Skipping GIN index (not using Postgres)")
        
        # Create other indexes
        for idx_name, sql in indexes_to_create:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"Created index: {idx_name}")
            except ProgrammingError as e:
                if 'already exists' not in str(e).lower():
                    logger.warning(f"Failed to create index {idx_name}: {e}")
                else:
                    logger.info(f"Index {idx_name} already exists")
    
    logger.info("Migration completed successfully")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    migrate_chunks_table()

