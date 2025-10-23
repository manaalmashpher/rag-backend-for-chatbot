"""
Chunking methods implementation

This module provides a comprehensive chunking service that implements 8 different
document chunking strategies for optimal text segmentation based on content type
and user requirements.

Chunking Methods:
1. Fixed-size chunking with overlap
2. Sentence boundary chunking
3. Paragraph boundary chunking
4. Semantic similarity-driven chunking
5. Sliding window chunking
6. Recursive character/token splitter
7. Topic-based chunking (Markdown/HTML)
8. Adaptive content-aware chunking
"""

from typing import List, Dict, Any
import hashlib
import re
import logging

logger = logging.getLogger(__name__)

class ChunkingService:
    """
    Implements the 8 predefined chunking methods for document text segmentation.
    
    This service provides various chunking strategies optimized for different
    document types and use cases. Each method produces chunks with consistent
    metadata including method ID, chunk index, hash, and optional page information.
    
    Features:
    - 8 different chunking algorithms
    - Dense document handling with automatic size adjustment
    - Page information support for PDF documents
    - Consistent metadata tracking
    - Error handling and validation
    
    Example:
        service = ChunkingService()
        chunks = service.chunk_text(text, method=1, chunk_size=1000, overlap=100)
        chunks_with_pages = service.chunk_text_with_pages(text, method=2, pages=page_list)
    """
    
    def chunk_text(self, text: str, method: int, **kwargs) -> List[Dict[str, Any]]:
        """
        Apply specified chunking method to text.
        
        This is the main entry point for text chunking. It automatically handles
        dense documents by adjusting chunk sizes and applies the selected
        chunking method with appropriate parameters.
        
        Args:
            text (str): Input text to chunk
            method (int): Chunking method ID (1-8)
                - 1: Fixed-size chunking with overlap
                - 2: Sentence boundary chunking
                - 3: Paragraph boundary chunking
                - 4: Semantic similarity-driven chunking
                - 5: Sliding window chunking
                - 6: Recursive character/token splitter
                - 7: Topic-based chunking (Markdown/HTML)
                - 8: Adaptive content-aware chunking
            **kwargs: Additional parameters for specific methods
                - chunk_size (int): Size for fixed-size methods (default: 1000)
                - overlap (int): Overlap for fixed-size methods (default: 100)
                - max_chunk_size (int): Maximum size for boundary methods
                - window_size (int): Window size for sliding window
                - step_size (int): Step size for sliding window
                - base_chunk_size (int): Base size for adaptive method
        
        Returns:
            List[Dict[str, Any]]: List of chunk dictionaries with:
                - text (str): Chunk text content
                - method (int): Chunking method used
                - chunk_index (int): Index of chunk in sequence
                - hash (str): SHA256 hash of chunk content (first 16 chars)
                - start_char (int): Starting character position (if applicable)
                - end_char (int): Ending character position (if applicable)
                - page_from (int): Starting page number (if pages provided)
                - page_to (int): Ending page number (if pages provided)
        
        Raises:
            ValueError: If method is not in range 1-8
        
        Example:
            service = ChunkingService()
            chunks = service.chunk_text("Sample text", method=1, chunk_size=500, overlap=50)
        """
        # Log chunking operation start
        logger.info(f"Starting chunking operation: method={method}, text_length={len(text)}")
        
        # Check if this is a dense document (like markdown) and adjust method
        is_dense = len(text) > 10000 or text.count('\n') > 1000
        if is_dense and method in [1, 2, 3]:  # For fixed-size, sentence, or paragraph methods
            logger.info(f"Dense document detected, adjusting chunk sizes for method {method}")
            # Use much larger chunk sizes for dense documents to reduce total chunks
            if method == 1:
                result = self._method_1_fixed_size(text, chunk_size=3000, overlap=300, **kwargs)
            elif method == 2:
                result = self._method_2_sentence_boundary(text, max_chunk_size=3000, **kwargs)
            elif method == 3:
                result = self._method_3_paragraph_boundary(text, max_chunk_size=3500, **kwargs)
            logger.info(f"Chunking completed: {len(result)} chunks generated")
            return result
        
        # Apply the selected chunking method
        import time
        start_time = time.time()
        
        try:
            if method == 1:
                result = self._method_1_fixed_size(text, **kwargs)
            elif method == 2:
                result = self._method_2_sentence_boundary(text, **kwargs)
            elif method == 3:
                result = self._method_3_paragraph_boundary(text, **kwargs)
            elif method == 4:
                result = self._method_4_semantic_similarity(text, **kwargs)
            elif method == 5:
                result = self._method_5_sliding_window(text, **kwargs)
            elif method == 6:
                result = self._method_6_recursive_split(text, **kwargs)
            elif method == 7:
                result = self._method_7_topic_based(text, **kwargs)
            elif method == 8:
                result = self._method_8_adaptive(text, **kwargs)
            else:
                raise ValueError(f"Invalid chunking method: {method}")
            
            # Log performance metrics
            end_time = time.time()
            processing_time = end_time - start_time
            logger.info(f"Chunking completed: method={method}, chunks={len(result)}, time={processing_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Chunking failed: method={method}, error={str(e)}")
            raise
    
    def chunk_text_with_pages(self, text: str, method: int, pages: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Apply chunking method with page information
        
        Args:
            text: Input text to chunk
            method: Chunking method (1-8)
            pages: List of page dictionaries with page_number and text
            **kwargs: Additional parameters for specific methods
        
        Returns:
            List of chunk dictionaries with text, metadata, and page info
        """
        # Get base chunks
        chunks = self.chunk_text(text, method, **kwargs)
        
        # Add page information to chunks
        for chunk in chunks:
            page_info = self._find_page_for_chunk(chunk['text'], pages)
            chunk['page_from'] = page_info.get('page_from')
            chunk['page_to'] = page_info.get('page_to')
        
        return chunks
    
    def _find_page_for_chunk(self, chunk_text: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Find which page(s) a chunk belongs to based on text content
        """
        chunk_text_clean = chunk_text.strip()
        
        for page in pages:
            page_text = page['text']
            page_num = page['page_number']
            
            # Check if chunk text is contained in this page
            if chunk_text_clean in page_text:
                return {
                    'page_from': page_num,
                    'page_to': page_num
                }
        
        # If not found, try to find partial matches
        for page in pages:
            page_text = page['text']
            page_num = page['page_number']
            
            # Check for significant overlap (at least 50% of chunk text)
            chunk_words = set(chunk_text_clean.lower().split())
            page_words = set(page_text.lower().split())
            
            if chunk_words and page_words:
                overlap = len(chunk_words.intersection(page_words))
                overlap_ratio = overlap / len(chunk_words)
                
                if overlap_ratio >= 0.5:  # 50% overlap
                    return {
                        'page_from': page_num,
                        'page_to': page_num
                    }
        
        # Default to first page if no match found
        return {
            'page_from': pages[0]['page_number'] if pages else 1,
            'page_to': pages[0]['page_number'] if pages else 1
        }
    
    def _method_1_fixed_size(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
        """
        Fixed-size chunking with overlap.
        
        This method splits text into fixed-size chunks with configurable overlap
        to ensure continuity between chunks. It's ideal for documents where
        semantic boundaries are not important and consistent chunk sizes are needed.
        
        Args:
            text (str): Input text to chunk
            chunk_size (int): Size of each chunk in characters (default: 1000)
            overlap (int): Number of characters to overlap between chunks (default: 100)
        
        Returns:
            List[Dict[str, Any]]: List of chunk dictionaries with fixed-size text segments
        
        Example:
            chunks = service._method_1_fixed_size("Long text...", chunk_size=500, overlap=50)
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            chunks.append({
                'text': chunk_text,
                'method': 1,
                'chunk_index': len(chunks),
                'start_char': start,
                'end_char': end,
                'hash': hashlib.sha256(chunk_text.encode()).hexdigest()[:16]
            })
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def _method_2_sentence_boundary(self, text: str, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Sentence boundary chunking.
        
        This method splits text at sentence boundaries while respecting maximum
        chunk size limits. It's ideal for documents where sentence-level
        coherence is important for retrieval and understanding.
        
        Args:
            text (str): Input text to chunk
            max_chunk_size (int): Maximum size of each chunk in characters (default: 1000)
        
        Returns:
            List[Dict[str, Any]]: List of chunk dictionaries with sentence-boundary text segments
        
        Example:
            chunks = service._method_2_sentence_boundary("Text with sentences.", max_chunk_size=500)
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += (" " + sentence) if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk,
                        'method': 2,
                        'chunk_index': chunk_index,
                        'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
                    })
                    chunk_index += 1
                current_chunk = sentence
        
        if current_chunk:
            chunks.append({
                'text': current_chunk,
                'method': 2,
                'chunk_index': chunk_index,
                'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
            })
        
        return chunks
    
    def _method_3_paragraph_boundary(self, text: str, max_chunk_size: int = 1500) -> List[Dict[str, Any]]:
        """
        Paragraph boundary chunking.
        
        This method splits text at paragraph boundaries while respecting maximum
        chunk size limits. It's ideal for documents with clear paragraph structure
        where paragraph-level coherence is important.
        
        Args:
            text (str): Input text to chunk
            max_chunk_size (int): Maximum size of each chunk in characters (default: 1500)
        
        Returns:
            List[Dict[str, Any]]: List of chunk dictionaries with paragraph-boundary text segments
        
        Example:
            chunks = service._method_3_paragraph_boundary("Text with paragraphs.", max_chunk_size=800)
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= max_chunk_size:
                current_chunk += ("\n\n" + paragraph) if current_chunk else paragraph
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk,
                        'method': 3,
                        'chunk_index': chunk_index,
                        'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
                    })
                    chunk_index += 1
                current_chunk = paragraph
        
        if current_chunk:
            chunks.append({
                'text': current_chunk,
                'method': 3,
                'chunk_index': chunk_index,
                'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
            })
        
        return chunks
    
    def _method_4_semantic_similarity(self, text: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Semantic similarity-based chunking (simplified)"""
        # For MVP, fall back to sentence boundary with semantic keywords
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        # Simple keyword-based semantic boundaries
        semantic_keywords = ['however', 'therefore', 'furthermore', 'moreover', 'consequently', 'additionally']
        
        for sentence in sentences:
            current_chunk += (" " + sentence) if current_chunk else sentence
            
            # Check for semantic boundary
            if any(keyword in sentence.lower() for keyword in semantic_keywords) or len(current_chunk) >= chunk_size:
                chunks.append({
                    'text': current_chunk,
                    'method': 4,
                    'chunk_index': chunk_index,
                    'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
                })
                chunk_index += 1
                current_chunk = ""
        
        if current_chunk:
            chunks.append({
                'text': current_chunk,
                'method': 4,
                'chunk_index': chunk_index,
                'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
            })
        
        return chunks
    
    def _method_5_sliding_window(self, text: str, window_size: int = 1000, step_size: int = 500) -> List[Dict[str, Any]]:
        """Sliding window chunking"""
        chunks = []
        
        for i in range(0, len(text), step_size):
            end = min(i + window_size, len(text))
            chunk_text = text[i:end]
            
            chunks.append({
                'text': chunk_text,
                'method': 5,
                'chunk_index': len(chunks),
                'start_char': i,
                'end_char': end,
                'hash': hashlib.sha256(chunk_text.encode()).hexdigest()[:16]
            })
        
        return chunks
    
    def _method_6_recursive_split(self, text: str, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Recursive splitting chunking"""
        def recursive_split(text_part, chunk_index=0):
            if len(text_part) <= max_chunk_size:
                return [{
                    'text': text_part,
                    'method': 6,
                    'chunk_index': chunk_index,
                    'hash': hashlib.sha256(text_part.encode()).hexdigest()[:16]
                }]
            
            # Try to split at paragraph boundary
            paragraphs = text_part.split('\n\n')
            if len(paragraphs) > 1:
                mid = len(paragraphs) // 2
                left_text = '\n\n'.join(paragraphs[:mid])
                right_text = '\n\n'.join(paragraphs[mid:])
            else:
                # Split at sentence boundary
                sentences = re.split(r'(?<=[.!?])\s+', text_part)
                if len(sentences) > 1:
                    mid = len(sentences) // 2
                    left_text = ' '.join(sentences[:mid])
                    right_text = ' '.join(sentences[mid:])
                else:
                    # Force split at character boundary
                    mid = len(text_part) // 2
                    left_text = text_part[:mid]
                    right_text = text_part[mid:]
            
            return recursive_split(left_text, chunk_index) + recursive_split(right_text, chunk_index + len(recursive_split(left_text, chunk_index)))
        
        return recursive_split(text)
    
    def _method_7_topic_based(self, text: str, max_chunk_size: int = 2000) -> List[Dict[str, Any]]:
        """Topic-based chunking using simple heuristics - optimized for markdown"""
        # Simple topic detection based on common topic indicators
        topic_indicators = [
            r'\n\s*#+\s+',  # Markdown headers
            r'\n\s*\d+\.\s+',  # Numbered lists
            r'\n\s*[A-Z][^.!?]*:',  # Title case followed by colon
            r'\n\s*[A-Z][A-Z\s]+:',  # All caps followed by colon
        ]
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        lines = text.split('\n')
        
        for line in lines:
            # Check if line indicates new topic
            is_topic_boundary = any(re.search(pattern, '\n' + line) for pattern in topic_indicators)
            
            if is_topic_boundary and current_chunk and len(current_chunk) > 100:
                chunks.append({
                    'text': current_chunk.strip(),
                    'method': 7,
                    'chunk_index': chunk_index,
                    'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
                })
                chunk_index += 1
                current_chunk = line
            else:
                current_chunk += ("\n" + line) if current_chunk else line
                
                # Force split if chunk gets too large
                if len(current_chunk) >= max_chunk_size:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'method': 7,
                        'chunk_index': chunk_index,
                        'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
                    })
                    chunk_index += 1
                    current_chunk = ""
        
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'method': 7,
                'chunk_index': chunk_index,
                'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
            })
        
        return chunks
    
    def _method_8_adaptive(self, text: str, base_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Adaptive chunking based on content characteristics"""
        chunks = []
        chunk_index = 0
        
        # Analyze text characteristics
        avg_sentence_length = self._get_avg_sentence_length(text)
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
        
        # Adapt chunk size based on content
        if avg_sentence_length > 100:  # Long sentences
            chunk_size = base_chunk_size * 1.5
        elif paragraph_count > 20:  # Many paragraphs
            chunk_size = base_chunk_size * 0.8
        else:
            chunk_size = base_chunk_size
        
        # Use sentence boundary with adaptive size
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += (" " + sentence) if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk,
                        'method': 8,
                        'chunk_index': chunk_index,
                        'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
                    })
                    chunk_index += 1
                current_chunk = sentence
        
        if current_chunk:
            chunks.append({
                'text': current_chunk,
                'method': 8,
                'chunk_index': chunk_index,
                'hash': hashlib.sha256(current_chunk.encode()).hexdigest()[:16]
            })
        
        return chunks
    
    def _get_avg_sentence_length(self, text: str) -> float:
        """Calculate average sentence length"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0
        return sum(len(s) for s in sentences) / len(sentences)
