"""
Performance tests for ingestion pipeline
"""

import pytest
import time
import os
from unittest.mock import patch, MagicMock
from app.services.ingestion import IngestionService
from app.services.chunking import ChunkingService
from app.services.file_processor import FileProcessor

@pytest.mark.performance
class TestIngestionPerformance:
    """Performance tests for ingestion pipeline"""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use real Qdrant service since it's running on localhost
        self.ingestion_service = IngestionService()
        self.chunking_service = ChunkingService()
        self.file_processor = FileProcessor()
    
    def generate_large_text(self, pages: int = 250) -> str:
        """Generate large text content simulating multiple pages."""
        # Simulate ~250 words per page (typical for documents)
        words_per_page = 250
        words_per_sentence = 15
        sentences_per_page = words_per_page // words_per_sentence
        
        text_parts = []
        for page in range(pages):
            page_content = []
            for sentence in range(sentences_per_page):
                sentence_text = f"This is sentence {sentence + 1} of page {page + 1}. " * words_per_sentence
                page_content.append(sentence_text.strip())
            
            # Add page break
            page_text = ". ".join(page_content) + "."
            text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def test_chunking_performance_200_pages(self):
        """Test chunking performance for 200 pages within time limit."""
        # Generate text equivalent to ~200 pages
        large_text = self.generate_large_text(pages=200)
        
        # Test all chunking methods
        for method in range(1, 9):
            start_time = time.time()
            chunks = self.chunking_service.chunk_text(large_text, method=method)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Should complete within 5 minutes (300 seconds) for chunking alone
            assert processing_time < 300, f"Chunking method {method} took {processing_time:.2f}s, exceeding 5 minute limit"
            
            # Verify we got reasonable number of chunks
            assert len(chunks) > 0, f"Method {method} produced no chunks"
            assert len(chunks) < len(large_text), f"Method {method} produced too many chunks: {len(chunks)}"
            
            print(f"Method {method}: {len(chunks)} chunks in {processing_time:.2f}s")
    
    @pytest.mark.slow
    def test_chunking_performance_300_pages(self):
        """Test chunking performance for 300 pages within time limit."""
        # Generate text equivalent to ~300 pages
        large_text = self.generate_large_text(pages=300)
        
        # Test with most efficient chunking method (fixed size)
        start_time = time.time()
        chunks = self.chunking_service.chunk_text(large_text, method=1, chunk_size=1000)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within 5 minutes (300 seconds)
        assert processing_time < 300, f"Chunking 300 pages took {processing_time:.2f}s, exceeding 5 minute limit"
        
        # Verify we got reasonable number of chunks
        assert len(chunks) > 0, "No chunks produced"
        assert len(chunks) < len(large_text), f"Too many chunks produced: {len(chunks)}"
        
        print(f"300 pages: {len(chunks)} chunks in {processing_time:.2f}s")
    
    def test_file_processing_performance(self):
        """Test file processing performance with large content."""
        # Generate large text content
        large_text = self.generate_large_text(pages=100)
        text_bytes = large_text.encode('utf-8')
        
        start_time = time.time()
        result = self.file_processor._extract_text_file(text_bytes)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within 1 second for text processing
        assert processing_time < 1.0, f"Text processing took {processing_time:.2f}s, exceeding 1 second limit"
        assert result == large_text, "Text processing result doesn't match input"
        
        print(f"Text processing: {len(text_bytes)} bytes in {processing_time:.2f}s")
    
    @pytest.mark.skip(reason="Requires actual OpenAI API key and Qdrant instance")
    def test_full_ingestion_pipeline_performance(self, db_session, temp_storage):
        """Test full ingestion pipeline performance (requires external services)."""
        # This test would require actual OpenAI API and Qdrant instance
        # Skip in CI/CD but can be run locally with proper configuration
        
        large_text = self.generate_large_text(pages=250)
        
        # Create a test document
        from app.models.database import Document, Ingestion
        import hashlib
        
        doc = Document(
            title="Performance Test Document",
            mime="text/plain",
            bytes=len(large_text.encode()),
            sha256=hashlib.sha256(large_text.encode()).hexdigest()
        )
        db_session.add(doc)
        db_session.flush()
        
        ingestion = Ingestion(
            doc_id=doc.id,
            method=1,
            status="queued"
        )
        db_session.add(ingestion)
        db_session.commit()
        
        # Store file
        file_path = os.path.join(temp_storage, f"{doc.sha256}.txt")
        with open(file_path, 'w') as f:
            f.write(large_text)
        
        start_time = time.time()
        success = self.ingestion_service.process_document(ingestion.id, db_session)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within 20 minutes (1200 seconds) as per requirements
        assert processing_time < 1200, f"Full ingestion took {processing_time:.2f}s, exceeding 20 minute limit"
        assert success, "Ingestion failed"
        
        print(f"Full ingestion: 250 pages in {processing_time:.2f}s")
    
    def test_memory_usage_large_document(self):
        """Test memory usage with large documents."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate very large text
        large_text = self.generate_large_text(pages=500)
        
        # Process the text
        chunks = self.chunking_service.chunk_text(large_text, method=1, chunk_size=1000)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB for 500 pages)
        assert memory_increase < 500, f"Memory usage increased by {memory_increase:.2f}MB, exceeding 500MB limit"
        
        print(f"Memory usage: {memory_increase:.2f}MB increase for 500 pages")
    
    def test_concurrent_chunking_performance(self):
        """Test chunking performance with concurrent processing."""
        import concurrent.futures
        import threading
        
        def chunk_text_worker(text, method):
            return self.chunking_service.chunk_text(text, method=method)
        
        # Generate text for multiple documents
        texts = [self.generate_large_text(pages=50) for _ in range(5)]
        
        start_time = time.time()
        
        # Process concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(chunk_text_worker, text, 1) for text in texts]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within 2 minutes (120 seconds) for 5 documents
        assert processing_time < 120, f"Concurrent processing took {processing_time:.2f}s, exceeding 2 minute limit"
        
        # Verify all results
        assert len(results) == 5, "Not all concurrent tasks completed"
        for result in results:
            assert len(result) > 0, "Some concurrent tasks produced no chunks"
        
        print(f"Concurrent processing: 5 documents in {processing_time:.2f}s")
    
    def test_chunking_method_efficiency_comparison(self):
        """Compare efficiency of different chunking methods."""
        large_text = self.generate_large_text(pages=100)
        
        method_times = {}
        method_chunk_counts = {}
        
        for method in range(1, 9):
            start_time = time.time()
            chunks = self.chunking_service.chunk_text(large_text, method=method)
            end_time = time.time()
            
            processing_time = end_time - start_time
            method_times[method] = processing_time
            method_chunk_counts[method] = len(chunks)
            
            print(f"Method {method}: {len(chunks)} chunks in {processing_time:.2f}s")
        
        # Find most efficient method
        fastest_method = min(method_times, key=method_times.get)
        slowest_method = max(method_times, key=method_times.get)
        
        print(f"Fastest method: {fastest_method} ({method_times[fastest_method]:.2f}s)")
        print(f"Slowest method: {slowest_method} ({method_times[slowest_method]:.2f}s)")
        
        # All methods should complete within reasonable time
        for method, time_taken in method_times.items():
            assert time_taken < 60, f"Method {method} took {time_taken:.2f}s, exceeding 1 minute limit"
