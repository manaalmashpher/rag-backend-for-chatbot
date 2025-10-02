"""
Mock services for testing
"""

from unittest.mock import MagicMock, patch
from typing import List, Dict, Any
import json

class MockOpenAIService:
    """Mock OpenAI service for testing"""
    
    def __init__(self):
        self.embeddings = []
        self.rate_limit_hit = False
        self.auth_error = False
        self.connection_error = False
    
    def create_embeddings(self, model: str, input: List[str]) -> Dict[str, Any]:
        """Mock OpenAI embeddings creation"""
        if self.rate_limit_hit:
            from openai import RateLimitError
            raise RateLimitError("Rate limit exceeded", response=None, body=None)
        
        if self.auth_error:
            from openai import AuthenticationError
            raise AuthenticationError("Invalid API key", response=None, body=None)
        
        if self.connection_error:
            from openai import APIConnectionError
            raise APIConnectionError("Connection failed", request=None)
        
        # Generate mock embeddings
        mock_embeddings = []
        for i, text in enumerate(input):
            # Create a deterministic mock embedding based on text content
            mock_embedding = [0.1 * (i + 1) + 0.01 * j for j in range(1536)]
            mock_embeddings.append({
                "embedding": mock_embedding,
                "index": i
            })
        
        return {
            "data": mock_embeddings,
            "model": model,
            "usage": {
                "prompt_tokens": sum(len(text.split()) for text in input),
                "total_tokens": sum(len(text.split()) for text in input)
            }
        }
    
    def set_rate_limit_error(self):
        """Configure mock to return rate limit error"""
        self.rate_limit_hit = True
    
    def set_auth_error(self):
        """Configure mock to return authentication error"""
        self.auth_error = True
    
    def set_connection_error(self):
        """Configure mock to return connection error"""
        self.connection_error = True

class MockQdrantService:
    """Mock Qdrant service for testing"""
    
    def __init__(self):
        self.collections = {}
        self.points = {}
        self.connection_error = False
    
    def get_collections(self):
        """Mock get collections"""
        if self.connection_error:
            raise ConnectionError("Failed to connect to Qdrant")
        
        collections = []
        for name, config in self.collections.items():
            collection = MagicMock()
            collection.name = name
            collections.append(collection)
        
        result = MagicMock()
        result.collections = collections
        return result
    
    def create_collection(self, collection_name: str, vectors_config: Any):
        """Mock create collection"""
        if self.connection_error:
            raise ConnectionError("Failed to connect to Qdrant")
        
        self.collections[collection_name] = {
            "vectors_config": vectors_config
        }
        self.points[collection_name] = []
    
    def upsert(self, collection_name: str, points: List[Any]):
        """Mock upsert points"""
        if self.connection_error:
            raise ConnectionError("Failed to connect to Qdrant")
        
        if collection_name not in self.points:
            self.points[collection_name] = []
        
        for point in points:
            self.points[collection_name].append({
                "id": point.id,
                "vector": point.vector,
                "payload": point.payload
            })
    
    def search(self, collection_name: str, query_vector: List[float], 
               limit: int = 10, score_threshold: float = 0.0):
        """Mock search vectors"""
        if self.connection_error:
            raise ConnectionError("Failed to connect to Qdrant")
        
        if collection_name not in self.points:
            return []
        
        # Return mock search results
        results = []
        for i, point in enumerate(self.points[collection_name][:limit]):
            result = MagicMock()
            result.id = point["id"]
            result.score = 0.9 - (i * 0.1)  # Decreasing scores
            result.payload = point["payload"]
            results.append(result)
        
        return results
    
    def delete(self, collection_name: str, points_selector: List[int]):
        """Mock delete points"""
        if self.connection_error:
            raise ConnectionError("Failed to connect to Qdrant")
        
        if collection_name in self.points:
            # Remove points with specified IDs
            self.points[collection_name] = [
                point for point in self.points[collection_name]
                if point["id"] not in points_selector
            ]
    
    def set_connection_error(self):
        """Configure mock to return connection error"""
        self.connection_error = True

def create_mock_openai_patch():
    """Create a patch for OpenAI service"""
    mock_service = MockOpenAIService()
    
    def mock_embeddings_create(*args, **kwargs):
        return mock_service.create_embeddings(
            model=kwargs.get('model', 'text-embedding-3-small'),
            input=kwargs.get('input', [])
        )
    
    return patch('openai.embeddings.create', side_effect=mock_embeddings_create), mock_service

def create_mock_qdrant_patch():
    """Create a patch for Qdrant service"""
    mock_service = MockQdrantService()
    
    def mock_qdrant_client(*args, **kwargs):
        return mock_service
    
    return patch('app.services.qdrant.QdrantClient', side_effect=mock_qdrant_client), mock_service

def create_mock_file_processor_patch():
    """Create a patch for file processor"""
    def mock_extract_text(file_content: bytes, mime_type: str) -> str:
        if mime_type == 'application/pdf':
            return "Mock PDF text content"
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return "Mock DOCX text content"
        elif mime_type in ['text/plain', 'text/markdown']:
            return file_content.decode('utf-8', errors='ignore')
        return None
    
    return patch('app.services.file_processor.FileProcessor.extract_text', side_effect=mock_extract_text)

def create_mock_scanned_pdf_detector_patch(is_scanned: bool = False):
    """Create a patch for scanned PDF detector"""
    return patch('app.services.scanned_pdf_detector.ScannedPDFDetector.is_scanned_pdf', return_value=is_scanned)
