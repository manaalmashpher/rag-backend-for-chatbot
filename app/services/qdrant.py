"""
Qdrant vector storage service
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.services.retry_service import retry_with_backoff, circuit_breaker

class QdrantService:
    """
    Handles vector storage and retrieval using Qdrant
    """
    
    def __init__(self):
        self.client = None
        self.collection_name = settings.qdrant_collection
        self._is_available = False
        
        # Initialize Qdrant client with optional API key for cloud
        try:
            if settings.qdrant_api_key:
                self.client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key
                )
            else:
                self.client = QdrantClient(url=settings.qdrant_url)
            
            self._ensure_collection_exists()
            self._is_available = True
        except Exception as e:
            # Log the error but don't fail initialization
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Qdrant client: {str(e)}")
            self.client = None
            self._is_available = False
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        if not self._is_available or self.client is None:
            return
            
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.embed_dim,
                        distance=Distance.COSINE
                    )
                )
        except ConnectionError as e:
            self._is_available = False
            raise RuntimeError(f"Failed to connect to Qdrant: {str(e)}")
        except Exception as e:
            self._is_available = False
            raise RuntimeError(f"Failed to ensure collection exists: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Qdrant service is available"""
        return self._is_available and self.client is not None
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    @circuit_breaker(failure_threshold=5, timeout=60)
    def store_vectors(self, vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        """
        Store vectors with metadata in Qdrant
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata dictionaries
            
        Returns:
            True if successful
        """
        if not self.is_available():
            raise RuntimeError("Qdrant service is not available")
            
        try:
            points = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads)):
                point = PointStruct(
                    id=i,  # Simple ID for now, should be more sophisticated
                    vector=vector,
                    payload=payload
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to store vectors: {str(e)}")
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    @circuit_breaker(failure_threshold=5, timeout=60)
    def search_vectors(self, query_vector: List[float], limit: int = 10, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results with payloads
        """
        if not self.is_available():
            raise RuntimeError("Qdrant service is not available")
            
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            return [
                {
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                }
                for result in results
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors: {str(e)}")
    
    def delete_vectors(self, ids: List[int]) -> bool:
        """
        Delete vectors by IDs
        
        Args:
            ids: List of vector IDs to delete
            
        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors: {str(e)}")
    
    def delete_vectors_by_hash(self, hashes: List[str]) -> bool:
        """
        Delete vectors by hash values
        
        Args:
            hashes: List of hash values to delete
            
        Returns:
            True if successful
        """
        try:
            # Find vectors by hash and get their IDs
            vector_ids = []
            for hash_value in hashes:
                # Search for vectors with this hash
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter={
                        "must": [
                            {
                                "key": "hash",
                                "match": {"value": hash_value}
                            }
                        ]
                    },
                    limit=1000
                )
                
                for vector in results[0]:
                    vector_ids.append(vector.id)
            
            # Delete found vectors
            if vector_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=vector_ids
                )
                print(f"Deleted {len(vector_ids)} vectors from Qdrant")
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors by hash: {str(e)}")
    
    def delete_vectors_by_doc_id(self, doc_id: int, method: int) -> bool:
        """
        Delete vectors by document ID and method
        
        Args:
            doc_id: Document ID to delete vectors for
            method: Chunking method to delete vectors for
            
        Returns:
            True if successful
        """
        try:
            # Find vectors by doc_id and method
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "doc_id",
                            "match": {"value": doc_id}
                        },
                        {
                            "key": "method",
                            "match": {"value": method}
                        }
                    ]
                },
                limit=10000  # Large limit to get all vectors for this document
            )
            
            vector_ids = [vector.id for vector in results[0]]
            
            # Delete found vectors
            if vector_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=vector_ids
                )
                print(f"Deleted {len(vector_ids)} vectors from Qdrant for doc_id {doc_id}, method {method}")
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors by doc_id: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if Qdrant service is healthy
        
        Returns:
            True if healthy, raises exception if not
        """
        if not self.is_available():
            raise RuntimeError("Qdrant service is not available")
            
        try:
            # Try to get collections to verify connection
            self.client.get_collections()
            return True
        except Exception as e:
            self._is_available = False
            raise RuntimeError(f"Qdrant health check failed: {str(e)}")