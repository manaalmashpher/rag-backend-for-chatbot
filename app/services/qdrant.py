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
                # Create indexes for payload fields to enable filtering
                self._create_payload_indexes()
        except ConnectionError as e:
            self._is_available = False
            raise RuntimeError(f"Failed to connect to Qdrant: {str(e)}")
        except Exception as e:
            self._is_available = False
            raise RuntimeError(f"Failed to ensure collection exists: {str(e)}")
    
    def _create_payload_indexes(self):
        """Create indexes for payload fields to enable filtering"""
        if not self._is_available or self.client is None:
            return
            
        try:
            from qdrant_client.models import PayloadSchemaType, CreateFieldIndex
            
            # Create indexes only for fields actually used in filtering
            payload_fields = [
                ("doc_id", PayloadSchemaType.INTEGER),
                ("hash", PayloadSchemaType.KEYWORD)
            ]
            
            for field_name, field_type in payload_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_type
                    )
                except Exception as e:
                    # Index might already exist, which is fine
                    if "already exists" not in str(e).lower():
                        print(f"Warning: Failed to create index for {field_name}: {e}")
                        
        except Exception as e:
            print(f"Warning: Failed to create payload indexes: {e}")
    
    def create_missing_indexes(self):
        """Create missing indexes on existing collection"""
        if not self._is_available or self.client is None:
            return False
            
        try:
            from qdrant_client.models import PayloadSchemaType
            
            # Create indexes only for fields actually used in filtering
            payload_fields = [
                ("doc_id", PayloadSchemaType.INTEGER),
                ("hash", PayloadSchemaType.KEYWORD)
            ]
            
            created_count = 0
            for field_name, field_type in payload_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_type
                    )
                    created_count += 1
                    print(f"Created index for {field_name}")
                except Exception as e:
                    # Index might already exist, which is fine
                    if "already exists" not in str(e).lower():
                        print(f"Warning: Failed to create index for {field_name}: {e}")
            
            if created_count > 0:
                print(f"Successfully created {created_count} indexes")
                return True
            else:
                print("All indexes already exist")
                return True
                
        except Exception as e:
            print(f"Failed to create missing indexes: {e}")
            return False
    
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
            for vector, payload in zip(vectors, payloads):
                # Use chunk_id from payload as the unique point ID
                chunk_id = payload.get('chunk_id')
                if chunk_id is None:
                    raise ValueError("Payload must contain 'chunk_id' for unique point identification")
                
                point = PointStruct(
                    id=chunk_id,
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
            # Try using indexed filtering first
            vector_ids = []
            for hash_value in hashes:
                try:
                    # Search for vectors with this hash using indexed filtering
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
                        
                except Exception as filter_error:
                    # If indexed filtering fails, try brute force approach
                    if "Index required" in str(filter_error):
                        print(f"Index not available for hash filtering, using brute force for hash: {hash_value}")
                        vector_ids.extend(self._find_vectors_by_hash_brute_force(hash_value))
                    else:
                        raise filter_error
            
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
    
    def _find_vectors_by_hash_brute_force(self, hash_value: str) -> List[int]:
        """
        Find vectors by hash using brute force (scroll all vectors)
        This is a fallback when indexes are not available
        """
        vector_ids = []
        try:
            # Scroll through all vectors and check payload
            offset = None
            while True:
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset
                )
                
                vectors, next_offset = results
                if not vectors:
                    break
                    
                for vector in vectors:
                    if vector.payload and vector.payload.get('hash') == hash_value:
                        vector_ids.append(vector.id)
                
                if next_offset is None:
                    break
                offset = next_offset
                
        except Exception as e:
            print(f"Warning: Brute force hash search failed: {e}")
            
        return vector_ids
    
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
            # Try using indexed filtering first (only doc_id, filter method in Python)
            try:
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter={
                        "must": [
                            {
                                "key": "doc_id",
                                "match": {"value": doc_id}
                            }
                        ]
                    },
                    limit=10000  # Large limit to get all vectors for this document
                )
                
                # Filter by method in Python since we don't have method index
                vector_ids = []
                for vector in results[0]:
                    if vector.payload and vector.payload.get('method') == method:
                        vector_ids.append(vector.id)
                
            except Exception as filter_error:
                # If indexed filtering fails, try brute force approach
                if "Index required" in str(filter_error):
                    print(f"Index not available for doc_id filtering, using brute force for doc_id: {doc_id}, method: {method}")
                    vector_ids = self._find_vectors_by_doc_id_brute_force(doc_id, method)
                else:
                    raise filter_error
            
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
    
    def _find_vectors_by_doc_id_brute_force(self, doc_id: int, method: int) -> List[int]:
        """
        Find vectors by doc_id and method using brute force (scroll all vectors)
        This is a fallback when indexes are not available
        """
        vector_ids = []
        try:
            # Scroll through all vectors and check payload
            offset = None
            while True:
                results = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset
                )
                
                vectors, next_offset = results
                if not vectors:
                    break
                    
                for vector in vectors:
                    if (vector.payload and 
                        vector.payload.get('doc_id') == doc_id and 
                        vector.payload.get('method') == method):
                        vector_ids.append(vector.id)
                
                if next_offset is None:
                    break
                offset = next_offset
                
        except Exception as e:
            print(f"Warning: Brute force doc_id search failed: {e}")
            
        return vector_ids
    
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