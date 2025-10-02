"""
Test configuration and fixtures
"""

import pytest
import asyncio
import tempfile
import os
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings
from app.models.database import Document, Ingestion, Chunk

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for file uploads."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_storage = settings.storage_path
        settings.storage_path = temp_dir
        yield temp_dir
        settings.storage_path = original_storage

@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    # This would be a minimal PDF in real implementation
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"

@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return "This is a sample document for testing. It contains multiple sentences. Each sentence should be processed correctly by the chunking methods. This is the end of the test document."

@pytest.fixture
def sample_document_data():
    """Sample document data for database testing."""
    return {
        "title": "Test Document",
        "mime": "text/plain",
        "bytes": 100,
        "sha256": "test_hash_123"
    }

@pytest.fixture
def sample_ingestion_data():
    """Sample ingestion data for database testing."""
    return {
        "method": 1,
        "status": "queued"
    }

@pytest.fixture
def mock_openai_embeddings():
    """Mock OpenAI embeddings response."""
    return {
        "data": [
            {"embedding": [0.1] * 1536},
            {"embedding": [0.2] * 1536}
        ]
    }

@pytest.fixture
def mock_qdrant_response():
    """Mock Qdrant search response."""
    return [
        {
            "id": 1,
            "score": 0.95,
            "payload": {
                "doc_id": 1,
                "chunk_id": 0,
                "text": "Sample text",
                "source": "Test Document"
            }
        }
    ]
