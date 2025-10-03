"""
Embedding generation service using Sentence Transformers
"""

from typing import List, Dict
from app.core.config import settings
import hashlib
import time
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Handles embedding generation using Sentence Transformers with caching
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.model = settings.embedding_model
            self.embed_dim = settings.embed_dim
            self._embedding_cache: Dict[str, List[float]] = {}
            self._cache_ttl = 3600  # 1 hour cache
            self._cache_timestamps: Dict[str, float] = {}
            self._init_sentence_transformers()
            EmbeddingService._initialized = True
    
    def _init_sentence_transformers(self):
        """Initialize Sentence Transformers model with memory optimization"""
        try:
            from sentence_transformers import SentenceTransformer
            import os
            import gc
            
            print(f"[INFO] Loading embedding model: {self.model}")
            print(f"[INFO] Model will be cached in: ~/.cache/torch/sentence_transformers/")
            
            # Memory optimization settings
            os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # Disable tokenizer parallelism to save memory
            os.environ['OMP_NUM_THREADS'] = '1'  # Limit OpenMP threads
            os.environ['TOKENIERS_PARALLELISM'] = 'false'  # Alternative spelling for some libraries
            
            # Load model with memory optimization
            self.st_model = SentenceTransformer(
                self.model,
                device='cpu',  # Force CPU usage to save memory
                cache_folder='/tmp/sentence_transformers'  # Use tmp folder for caching
            )
            
            # Force garbage collection after model loading
            gc.collect()
            
            print(f"[INFO] Model loaded successfully!")
            print(f"[INFO] Embedding dimension: {self.st_model.get_sentence_embedding_dimension()}")
            print(f"[INFO] Model device: {self.st_model.device}")
            
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
                # Process in smaller batches to reduce memory usage
                batch_size = min(32, len(texts_to_generate))  # Process max 32 texts at once
                new_embeddings_list = []
                
                for i in range(0, len(texts_to_generate), batch_size):
                    batch = texts_to_generate[i:i + batch_size]
                    batch_embeddings = self.st_model.encode(batch, convert_to_tensor=False)
                    new_embeddings_list.extend(batch_embeddings.tolist())
                    
                    # Force garbage collection after each batch
                    import gc
                    gc.collect()
                
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
            logger.debug(f"Cache hit for embedding: {text[:50]}...")
            return self._embedding_cache[cache_key]
        
        logger.debug(f"Cache miss for embedding: {text[:50]}...")
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