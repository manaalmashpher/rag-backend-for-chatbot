"""
Embedding generation service using Sentence Transformers
"""

from typing import List
from app.core.config import settings

class EmbeddingService:
    """
    Handles embedding generation using Sentence Transformers
    """
    
    def __init__(self):
        self.model = settings.embedding_model
        self.embed_dim = settings.embed_dim
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
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.st_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self.generate_embeddings([text])
        return embeddings[0]
    
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