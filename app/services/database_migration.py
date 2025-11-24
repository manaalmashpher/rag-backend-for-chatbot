"""
Database migration script for database schema updates

Run this script to apply database migrations.
Safe to run multiple times (idempotent).

Migrations included:
- Hierarchy-aware chunking metadata fields (chunks table)
- Chat history tables (chat_sessions, chat_messages)
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
    
    logger.info("Chunks table migration completed successfully")


def migrate_chat_history_tables():
    """
    Create chat_sessions and chat_messages tables if they don't exist
    
    This migration is idempotent - safe to run multiple times.
    """
    logger.info("Starting chat history tables migration...")
    
    # Check database type for SQL compatibility
    db_url = str(engine.url)
    is_postgres = 'postgresql' in db_url.lower() or 'postgres' in db_url.lower()
    timestamp_type = "TIMESTAMPTZ" if is_postgres else "DATETIME"
    default_now = "now()" if is_postgres else "CURRENT_TIMESTAMP"
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    with engine.connect() as conn:
        # Create chat_sessions table
        if 'chat_sessions' not in existing_tables:
            try:
                conn.execute(text(f"""
                    CREATE TABLE chat_sessions (
                        id INTEGER PRIMARY KEY,
                        uuid VARCHAR(36) UNIQUE,
                        created_at {timestamp_type} NOT NULL DEFAULT {default_now},
                        updated_at {timestamp_type} NOT NULL DEFAULT {default_now},
                        user_id INTEGER REFERENCES users(id)
                    )
                """))
                conn.commit()
                logger.info("Created table: chat_sessions")
            except ProgrammingError as e:
                logger.error(f"Failed to create chat_sessions table: {e}")
                raise
        else:
            logger.info("Table chat_sessions already exists")
            # Check if uuid column exists, add it if missing
            existing_columns = {col['name'] for col in inspector.get_columns('chat_sessions')}
            if 'uuid' not in existing_columns:
                try:
                    conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN uuid VARCHAR(36) UNIQUE"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_uuid ON chat_sessions(uuid)"))
                    conn.commit()
                    logger.info("Added uuid column to chat_sessions table")
                except ProgrammingError as e:
                    logger.warning(f"Failed to add uuid column: {e}")
        
        # Create chat_messages table
        if 'chat_messages' not in existing_tables:
            try:
                conn.execute(text(f"""
                    CREATE TABLE chat_messages (
                        id INTEGER PRIMARY KEY,
                        session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        role VARCHAR(20) NOT NULL,
                        content TEXT NOT NULL,
                        created_at {timestamp_type} NOT NULL DEFAULT {default_now}
                    )
                """))
                conn.commit()
                logger.info("Created table: chat_messages")
            except ProgrammingError as e:
                logger.error(f"Failed to create chat_messages table: {e}")
                raise
        else:
            logger.info("Table chat_messages already exists")
        
        # Create indexes
        indexes_to_create = [
            ('idx_chat_sessions_uuid', 'CREATE INDEX IF NOT EXISTS idx_chat_sessions_uuid ON chat_sessions(uuid)'),
            ('idx_chat_messages_session_id', 'CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)'),
            ('idx_chat_messages_created_at', 'CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at)'),
        ]
        
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
    
    logger.info("Chat history migration completed successfully")


def run_all_migrations():
    """
    Run all database migrations in order
    
    This is the main entry point for applying all migrations.
    """
    logger.info("Starting all database migrations...")
    migrate_chunks_table()
    migrate_chat_history_tables()
    logger.info("All database migrations completed successfully")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_all_migrations()

