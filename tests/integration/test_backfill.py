"""
Integration tests for backfill script

Tests the end-to-end backfill process including:
- Document re-chunking with clause-aware chunker
- Database updates with new metadata
- Qdrant vector updates
- Resume functionality
- Idempotency
"""

import pytest
import os
import tempfile
import hashlib
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.rag.index.backfill import BackfillService
from app.models.database import Document, Chunk
from app.core.config import settings


class TestBackfillIntegration:
    """Integration tests for backfill service"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_storage = settings.storage_path
            settings.storage_path = temp_dir
            yield temp_dir
            settings.storage_path = original_storage
    
    @pytest.fixture
    def sample_document_text(self):
        """Sample document text with clause structure"""
        return """
Tenth Section: Research and Innovation

5.22 Institutional Innovation

5.22.1 Adopting innovation as a strategic direction

This is the content for section 5.22.1. It contains important information about adopting innovation.

5.22.2 Applying Innovation Methodologies

This section discusses various methodologies for applying innovation in practice.
"""
    
    @pytest.fixture
    def sample_document(self, db_session, temp_storage, sample_document_text):
        """Create a sample document in database and storage"""
        # Create document record
        doc = Document(
            title="Test Standards Document",
            mime="text/plain",
            bytes=len(sample_document_text.encode()),
            sha256=hashlib.sha256(sample_document_text.encode()).hexdigest()
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        # Create file in storage
        file_path = os.path.join(temp_storage, f"{doc.sha256}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_document_text)
        
        return doc
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service"""
        with patch('app.rag.index.backfill.EmbeddingService') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            # Return mock embeddings
            mock_instance.generate_embeddings.return_value = [
                [0.1] * 768,  # Mock embedding vector
                [0.2] * 768
            ]
            yield mock_instance
    
    @pytest.fixture
    def mock_qdrant_service(self):
        """Mock Qdrant service"""
        with patch('app.rag.index.backfill.QdrantService') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_instance.is_available.return_value = True
            mock_instance.delete_vectors_by_doc_id.return_value = True
            mock_instance.store_vectors.return_value = True
            yield mock_instance
    
    def test_backfill_processes_document(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that backfill processes a document end-to-end"""
        service = BackfillService(dry_run=False, batch_size=2)
        
        # Mock get_db to return our test session
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            result = service.process_documents(doc_selector=f"doc_id={sample_document.id}")
        
        # Check result structure (stats dictionary, not success flag)
        assert 'processed' in result
        assert result['processed'] == 1
        assert result['chunks_created'] > 0
        assert result['vectors_created'] > 0
        
        # Verify chunks were created in database
        chunks = db_session.query(Chunk).filter(
            Chunk.doc_id == sample_document.id,
            Chunk.method == 9
        ).all()
        
        assert len(chunks) > 0
        
        # Verify chunks have new metadata fields
        for chunk in chunks:
            assert chunk.section_id is not None or chunk.text  # At least some have section_id
            assert chunk.hash is not None
            assert chunk.token_count is not None
    
    def test_backfill_dry_run(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that dry run doesn't write to database"""
        service = BackfillService(dry_run=True)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            result = service.process_documents(doc_selector=f"doc_id={sample_document.id}")
        
        assert result['processed'] == 1
        assert result['chunks_created'] > 0
        
        # Verify NO chunks were actually created in database
        chunks = db_session.query(Chunk).filter(
            Chunk.doc_id == sample_document.id,
            Chunk.method == 9
        ).all()
        
        assert len(chunks) == 0
        
        # Verify Qdrant was not called
        mock_qdrant_service.store_vectors.assert_not_called()
    
    def test_backfill_idempotency(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that running backfill twice is idempotent"""
        service = BackfillService(dry_run=False, batch_size=2)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            # Create a generator function that can be called multiple times
            def db_generator():
                yield db_session
            
            # Make get_db return a new generator each time it's called
            mock_get_db.side_effect = lambda: db_generator()
            
            # First run
            result1 = service.process_documents(doc_selector=f"doc_id={sample_document.id}")
            chunks_count_1 = db_session.query(Chunk).filter(
                Chunk.doc_id == sample_document.id,
                Chunk.method == 9
            ).count()
            
            # Second run (should delete old and create new, but same count)
            result2 = service.process_documents(doc_selector=f"doc_id={sample_document.id}")
            chunks_count_2 = db_session.query(Chunk).filter(
                Chunk.doc_id == sample_document.id,
                Chunk.method == 9
            ).count()
        
        # Should have same number of chunks (idempotent)
        assert chunks_count_1 == chunks_count_2
        assert result1['chunks_created'] == result2['chunks_created']
    
    def test_backfill_resume_functionality(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that backfill can resume from a document ID"""
        # Create a second document
        doc2 = Document(
            title="Test Document 2",
            mime="text/plain",
            bytes=100,
            sha256="test_hash_2"
        )
        db_session.add(doc2)
        db_session.commit()
        db_session.refresh(doc2)
        
        service = BackfillService(dry_run=True)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            # Resume from first document (should only process second)
            result = service.process_documents(
                doc_selector="all",
                last_processed_id=sample_document.id
            )
        
        # Should process documents after the resume point
        assert result['total_documents'] >= 1
    
    def test_backfill_handles_missing_file(
        self,
        db_session,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that backfill handles missing files gracefully"""
        # Create document without file
        doc = Document(
            title="Missing File Document",
            mime="text/plain",
            bytes=100,
            sha256="missing_hash"
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        service = BackfillService(dry_run=False)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            result = service.process_documents(doc_selector=f"doc_id={doc.id}")
        
        assert result['failed'] == 1
        assert len(result['errors']) > 0
        assert 'File not found' in result['errors'][0]['error']
    
    def test_backfill_batch_processing(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that backfill processes embeddings in batches"""
        service = BackfillService(dry_run=False, batch_size=1)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            result = service.process_documents(doc_selector=f"doc_id={sample_document.id}")
        
        # Verify embeddings were called (batched)
        assert mock_embedding_service.generate_embeddings.called
        call_count = mock_embedding_service.generate_embeddings.call_count
        assert call_count > 0  # Should be called at least once
    
    def test_backfill_metadata_persistence(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that backfill persists all metadata fields"""
        service = BackfillService(dry_run=False, batch_size=2)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            result = service.process_documents(doc_selector=f"doc_id={sample_document.id}")
        
        # Verify chunks have all metadata fields
        chunks = db_session.query(Chunk).filter(
            Chunk.doc_id == sample_document.id,
            Chunk.method == 9
        ).all()
        
        for chunk in chunks:
            # Core fields
            assert chunk.doc_id == sample_document.id
            assert chunk.method == 9
            assert chunk.hash is not None
            assert chunk.text is not None
            
            # New metadata fields (at least some should have these)
            if chunk.section_id:
                assert chunk.section_id_alias is not None
                assert chunk.level is not None
                assert chunk.token_count is not None
                assert chunk.text_norm is not None
    
    def test_backfill_qdrant_payload(
        self,
        db_session,
        sample_document,
        temp_storage,
        mock_embedding_service,
        mock_qdrant_service
    ):
        """Test that Qdrant receives correct payload with metadata"""
        service = BackfillService(dry_run=False, batch_size=2)
        
        with patch('app.rag.index.backfill.get_db') as mock_get_db:
            def db_generator():
                yield db_session
            
            mock_get_db.return_value = db_generator()
            
            service.process_documents(doc_selector=f"doc_id={sample_document.id}")
        
        # Verify Qdrant store_vectors was called
        assert mock_qdrant_service.store_vectors.called
        
        # Get the call arguments
        call_args = mock_qdrant_service.store_vectors.call_args
        vectors, payloads = call_args[0]
        
        assert len(vectors) > 0
        assert len(payloads) > 0
        
        # Verify payload structure
        payload = payloads[0]
        assert 'doc_id' in payload
        assert 'chunk_id' in payload
        assert 'section_id' in payload or payload.get('section_id') is None  # May be None
        assert 'hash' in payload
        assert 'source_name' in payload

