"""
Embedding generation service using Sentence Transformers
"""

from typing import List, Dict
from app.core.config import settings
import hashlib
import time

class EmbeddingService:
    """
    Handles embedding generation using Sentence Transformers with caching
    """
    
    def __init__(self):
        self.model = settings.embedding_model
        self.embed_dim = settings.embed_dim
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_ttl = 3600  # 1 hour cache
        self._cache_timestamps: Dict[str, float] = {}
        self._init_sentence_transformers()
    
    def _init_sentence_transformers(self):
        """Initialize Sentence Transformers model"""
        try:
            from sentence_transformers import SentenceTransformer
            import os
            
            print(f"[INFO] Loading embedding model: {self.model}")
            print(f"[INFO] Model will be cached in: ~/.cache/torch/sentence_transformers/")
            
            self.st_model = SentenceTransformer(self.model)
            
            print(f"[INFO] Model loaded successfully!")
            print(f"[INFO] Embedding dimension: {self.st_model.get_sentence_embedding_dimension()}")
            
        except ImportError:
            raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts with caching
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            # Check cache first
            cached_embeddings = []
            texts_to_generate = []
            text_indices = []
            
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if self._is_cached(cache_key):
                    cached_embeddings.append((i, self._embedding_cache[cache_key]))
                else:
                    texts_to_generate.append(text)
                    text_indices.append(i)
            
            # Generate embeddings for uncached texts
            if texts_to_generate:
                new_embeddings = self.st_model.encode(texts_to_generate, convert_to_tensor=False)
                new_embeddings_list = new_embeddings.tolist()
                
                # Cache the new embeddings
                for text, embedding in zip(texts_to_generate, new_embeddings_list):
                    cache_key = self._get_cache_key(text)
                    self._embedding_cache[cache_key] = embedding
                    self._cache_timestamps[cache_key] = time.time()
            
            # Combine cached and new embeddings in correct order
            all_embeddings = [None] * len(texts)
            
            # Add cached embeddings
            for i, embedding in cached_embeddings:
                all_embeddings[i] = embedding
            
            # Add new embeddings
            for i, embedding in zip(text_indices, new_embeddings_list):
                all_embeddings[i] = embedding
            
            return all_embeddings
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text with caching
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
        """
        cache_key = self._get_cache_key(text)
        
        # Check cache first
        if self._is_cached(cache_key):
            return self._embedding_cache[cache_key]
        
        # Generate new embedding
        embeddings = self.generate_embeddings([text])
        return embeddings[0]
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if embedding is cached and not expired"""
        if cache_key not in self._embedding_cache:
            return False
        
        # Check if cache entry is expired
        if time.time() - self._cache_timestamps.get(cache_key, 0) > self._cache_ttl:
            # Remove expired entry
            del self._embedding_cache[cache_key]
            if cache_key in self._cache_timestamps:
                del self._cache_timestamps[cache_key]
            return False
        
        return True
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self._embedding_cache.clear()
        self._cache_timestamps.clear()
    
    def health_check(self) -> bool:
        """
        Check if embedding service is healthy
        
        Returns:
            True if healthy, raises exception if not
        """
        try:
            # Test with a simple embedding generation
            test_embedding = self.generate_embeddings(["test"])
            if not test_embedding or len(test_embedding) == 0:
                raise RuntimeError("Embedding generation returned empty result")
            return True
        except Exception as e:
            raise RuntimeError(f"Embedding service health check failed: {str(e)}")