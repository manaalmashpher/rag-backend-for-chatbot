"""
Vector search service using Qdrant
"""

from typing import List, Dict, Any, Optional
from app.services.qdrant import QdrantService
from app.services.embeddings import EmbeddingService
from app.core.config import settings
from app.core.database import get_db
from app.models.database import Chunk
import logging

logger = logging.getLogger(__name__)

class VectorSearchService:
    """
    Handles semantic vector search using Qdrant
    """
    
    def __init__(self):
        self.qdrant = QdrantService()
        self.embeddings = EmbeddingService()
        self.topk_vec = getattr(settings, 'topk_vec', 20)
    
    def search(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic vector search with optimized database access and timeout protection
        
        Args:
            query: Natural language query string
            limit: Maximum number of results (defaults to topk_vec)
            
        Returns:
            List of search results with metadata
        """
        try:
            # Check if Qdrant is available first
            if not self.qdrant.is_available():
                logger.warning("Qdrant not available, skipping vector search")
                return []
            
            # Generate query embedding with timeout
            import time
            start_time = time.time()
            
            try:
                query_vector = self.embeddings.generate_single_embedding(query)
                embedding_time = time.time() - start_time
                if embedding_time > 3:  # Reduced timeout for embedding (3 seconds)
                    logger.warning(f"Embedding generation took {embedding_time:.2f}s, skipping vector search")
                    return []
                logger.debug(f"Embedding generated in {embedding_time:.2f}s")
            except Exception as e:
                logger.warning(f"Embedding generation failed: {str(e)}")
                return []
            
            # Set limit
            search_limit = limit or self.topk_vec
            
            # Search vectors in Qdrant with timeout
            try:
                results = self.qdrant.search_vectors(
                    query_vector=query_vector,
                    limit=min(search_limit, 15),  # Cap at 15 for performance
                    score_threshold=0.1  # Higher threshold to filter low-quality results
                )
                
                search_time = time.time() - start_time
                if search_time > 5:  # Reduced total timeout (5 seconds)
                    logger.warning(f"Vector search took {search_time:.2f}s, returning partial results")
                    results = results[:5]  # Return only top 5 results
                else:
                    logger.debug(f"Vector search completed in {search_time:.2f}s")
                    
            except Exception as e:
                logger.warning(f"Qdrant search failed: {str(e)}")
                return []
            
            # Format results and batch fetch text from database
            formatted_results = []
            db = next(get_db())
            
            try:
                # Batch fetch all chunk texts at once for better performance
                chunk_texts = self._batch_fetch_chunk_texts(db, results)
                
                for i, result in enumerate(results):
                    payload = result.get('payload', {})
                    chunk_id = payload.get('chunk_id')
                    
                    # Get pre-fetched text using the actual chunk ID
                    text = chunk_texts.get(chunk_id, '')
                    
                    formatted_result = {
                        'chunk_id': str(payload.get('chunk_id', '')),
                        'doc_id': str(payload.get('doc_id', '')),
                        'method': int(payload.get('method', 0)),
                        'page_from': int(payload.get('page_from')) if payload.get('page_from') else None,
                        'page_to': int(payload.get('page_to')) if payload.get('page_to') else None,
                        'hash': str(payload.get('hash', '')),
                        'source': str(payload.get('source', '')),
                        'text': text,
                        'score': float(result.get('score', 0.0)),
                        'search_type': 'semantic'
                    }
                    formatted_results.append(formatted_result)
            finally:
                db.close()
            
            logger.info(f"Vector search completed: {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []  # Return empty list instead of raising exception
    
    def search_with_metadata(self, query: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform vector search with additional metadata
        
        Args:
            query: Natural language query string
            limit: Maximum number of results
            
        Returns:
            Dictionary with results and metadata
        """
        try:
            results = self.search(query, limit)
            
            return {
                'results': results,
                'total_results': len(results),
                'search_type': 'semantic',
                'query': query,
                'limit': limit or self.topk_vec
            }
            
        except Exception as e:
            logger.error(f"Vector search with metadata failed: {str(e)}")
            raise RuntimeError(f"Vector search with metadata failed: {str(e)}")
    
    def _fetch_chunk_text(self, db, chunk_id, payload):
        """
        Fetch chunk text from database with proper error handling
        
        Args:
            db: Database session
            chunk_id: Chunk identifier
            payload: Qdrant payload data
            
        Returns:
            Chunk text or empty string if not found
        """
        if not chunk_id:
            return ""
        
        try:
            # Convert chunk_id to integer
            if isinstance(chunk_id, str):
                # Handle both "ch_00000" format and raw "0" format
                if chunk_id.startswith('ch_'):
                    chunk_id_int = int(chunk_id.replace('ch_', ''))
                else:
                    chunk_id_int = int(chunk_id)
            else:
                chunk_id_int = int(chunk_id)
            
            chunk = db.query(Chunk).filter(Chunk.id == chunk_id_int).first()
            if chunk:
                logger.debug(f"Found text for chunk_id {chunk_id} -> {chunk_id_int}: {len(chunk.text)} chars")
                return chunk.text
            else:
                logger.warning(f"No chunk found for chunk_id {chunk_id} -> {chunk_id_int}")
                
        except (ValueError, AttributeError) as e:
            logger.warning(f"Chunk ID conversion failed for {chunk_id}: {e}")
            # If chunk_id conversion fails, try to find by hash
            hash_value = payload.get('hash', '')
            if hash_value:
                try:
                    chunk = db.query(Chunk).filter(Chunk.hash == hash_value).first()
                    if chunk:
                        logger.debug(f"Found text by hash {hash_value}: {len(chunk.text)} chars")
                        return chunk.text
                except Exception as hash_e:
                    logger.warning(f"Failed to find chunk by hash {hash_value}: {hash_e}")
        except Exception as e:
            logger.warning(f"Failed to fetch text for chunk {chunk_id}: {e}")
        
        return ""
    
    def _batch_fetch_chunk_texts(self, db, results):
        """
        Batch fetch chunk texts from database for better performance
        
        Args:
            db: Database session
            results: List of Qdrant search results
            
        Returns:
            Dictionary mapping chunk_id to text content
        """
        chunk_texts = {}
        
        if not results:
            return chunk_texts
        
        # Collect all chunk IDs and hashes
        chunk_ids = []
        chunk_hashes = []
        
        for result in results:
            payload = result.get('payload', {})
            chunk_id = payload.get('chunk_id')
            hash_value = payload.get('hash', '')
            
            if chunk_id:
                try:
                    # Convert chunk_id to integer
                    if isinstance(chunk_id, str):
                        if chunk_id.startswith('ch_'):
                            chunk_id_int = int(chunk_id.replace('ch_', ''))
                        else:
                            chunk_id_int = int(chunk_id)
                    else:
                        chunk_id_int = int(chunk_id)
                    chunk_ids.append(chunk_id_int)
                except (ValueError, AttributeError):
                    if hash_value:
                        chunk_hashes.append(hash_value)
            elif hash_value:
                chunk_hashes.append(hash_value)
        
        try:
            # Batch fetch by chunk IDs
            if chunk_ids:
                chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
                for chunk in chunks:
                    chunk_texts[chunk.id] = chunk.text  # Use actual chunk ID as key
                    logger.debug(f"Batch fetched text for chunk_id {chunk.id}: {len(chunk.text)} chars")
            
            # Batch fetch by hashes for any missing chunks
            if chunk_hashes:
                chunks_by_hash = db.query(Chunk).filter(Chunk.hash.in_(chunk_hashes)).all()
                for chunk in chunks_by_hash:
                    chunk_texts[chunk.id] = chunk.text  # Use actual chunk ID as key
                    logger.debug(f"Batch fetched text by hash {chunk.hash}: {len(chunk.text)} chars")
                    
        except Exception as e:
            logger.warning(f"Batch fetch failed: {e}")
            # Fallback to individual fetches
            for result in results:
                payload = result.get('payload', {})
                chunk_id = payload.get('chunk_id')
                if chunk_id and chunk_id not in chunk_texts:
                    chunk_texts[chunk_id] = self._fetch_chunk_text(db, chunk_id, payload)
        
        return chunk_texts
