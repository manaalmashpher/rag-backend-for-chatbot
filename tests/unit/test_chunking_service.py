"""
Unit tests for ChunkingService
"""

import pytest
from app.services.chunking import ChunkingService

@pytest.mark.unit
class TestChunkingService:
    """Test cases for ChunkingService"""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = ChunkingService()
        self.sample_text = "This is a test document. It contains multiple sentences. Each sentence should be processed correctly. The chunking methods should work properly. This is the end of the test document."
    
    def test_chunking_method_1_fixed_size(self):
        """Test fixed-size chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=1, chunk_size=50, overlap=10)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 1 for chunk in chunks)
        
        # Check that chunks don't exceed size limit (allowing for some flexibility)
        for chunk in chunks:
            assert len(chunk['text']) <= 60  # chunk_size + some buffer
    
    def test_chunking_method_2_sentence_boundary(self):
        """Test sentence boundary chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=2, max_chunk_size=100)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 2 for chunk in chunks)
    
    def test_chunking_method_3_paragraph_boundary(self):
        """Test paragraph boundary chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=3, max_chunk_size=150)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 3 for chunk in chunks)
    
    def test_chunking_method_4_semantic_similarity(self):
        """Test semantic similarity chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=4, chunk_size=100)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 4 for chunk in chunks)
    
    def test_chunking_method_5_sliding_window(self):
        """Test sliding window chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=5, window_size=50, step_size=25)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 5 for chunk in chunks)
    
    def test_chunking_method_6_recursive_split(self):
        """Test recursive split chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=6, max_chunk_size=50)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 6 for chunk in chunks)
    
    def test_chunking_method_7_topic_based(self):
        """Test topic-based chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=7, max_chunk_size=100)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 7 for chunk in chunks)
    
    def test_chunking_method_8_adaptive(self):
        """Test adaptive chunking method."""
        chunks = self.service.chunk_text(self.sample_text, method=8, base_chunk_size=50)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('method' in chunk for chunk in chunks)
        assert all('hash' in chunk for chunk in chunks)
        assert all(chunk['method'] == 8 for chunk in chunks)
    
    def test_invalid_chunking_method(self):
        """Test that invalid chunking method raises error."""
        with pytest.raises(ValueError, match="Invalid chunking method"):
            self.service.chunk_text(self.sample_text, method=99)
    
    def test_empty_text(self):
        """Test chunking with empty text."""
        chunks = self.service.chunk_text("", method=1)
        assert len(chunks) == 0
    
    def test_very_short_text(self):
        """Test chunking with very short text."""
        chunks = self.service.chunk_text("Hi", method=1, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0]['text'] == "Hi"
    
    def test_chunk_metadata_consistency(self):
        """Test that chunk metadata is consistent."""
        chunks = self.service.chunk_text(self.sample_text, method=1)
        
        for i, chunk in enumerate(chunks):
            assert 'chunk_index' in chunk
            assert chunk['chunk_index'] == i
            assert 'start_char' in chunk
            assert 'end_char' in chunk
            assert chunk['start_char'] < chunk['end_char']
    
    def test_hash_uniqueness(self):
        """Test that chunk hashes are unique."""
        chunks = self.service.chunk_text(self.sample_text, method=1)
        hashes = [chunk['hash'] for chunk in chunks]
        assert len(hashes) == len(set(hashes))  # All hashes should be unique
