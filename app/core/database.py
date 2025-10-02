"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Optimize database engine for better performance
engine = create_engine(
    settings.database_url,
    # Connection pool settings for better performance
    pool_size=15,  # Increased pool size for better concurrency
    max_overflow=25,  # More overflow connections for burst traffic
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=1800,  # Recycle connections after 30 minutes (reduced)
    pool_timeout=30,  # Timeout for getting connection from pool
    # Connection timeout settings
    connect_args={
        "connect_timeout": 7,  # Reduced connection timeout
        "application_name": "ionologybot-api",
        "options": "-c statement_timeout=10000"  # 10 second statement timeout
    } if "postgresql" in settings.database_url else {},
    # Query optimization
    echo=False,  # Disable SQL logging for performance
    future=True  # Use SQLAlchemy 2.0 style
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
