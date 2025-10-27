"""
Search API schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import re

class SearchRequest(BaseModel):
    """Search request schema"""
    q: str = Field(..., min_length=1, max_length=500, description="Search query string")
    limit: Optional[int] = Field(10, ge=1, le=50, description="Maximum number of results to return")
    
    @validator('q')
    def validate_query(cls, v):
        """Validate and sanitize query string"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        
        # Remove potentially harmful characters and SQL injection attempts
        sanitized = re.sub(r'[<>"\'\\;]', '', v.strip())
        # Remove SQL comment patterns separately
        sanitized = re.sub(r'--', '', sanitized)
        
        # Additional FTS5-specific sanitization
        # Remove FTS5 operators that could be used maliciously
        sanitized = re.sub(r'[^\w\s\-]', ' ', sanitized)
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        if not sanitized:
            raise ValueError("Query contains only invalid characters")
        
        # Check for suspicious patterns
        if re.search(r'\b(union|select|insert|update|delete|drop|create|alter)\b', sanitized, re.IGNORECASE):
            raise ValueError("Query contains potentially malicious SQL keywords")
        
        return sanitized

class SearchResult(BaseModel):
    """Individual search result schema"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Document identifier")
    method: int = Field(..., ge=1, le=8, description="Chunking method used")
    page_from: Optional[int] = Field(None, ge=1, description="Starting page number")
    page_to: Optional[int] = Field(None, ge=1, description="Ending page number")
    hash: str = Field(..., description="Content hash")
    source: str = Field(..., description="Document title/source")
    snippet: Optional[str] = Field(None, description="Text snippet with highlighting")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    search_type: str = Field(..., description="Type of search (semantic/lexical/hybrid)")
    rerank_score: Optional[float] = Field(None, description="Rerank score from cross-encoder model")

class SearchMetadata(BaseModel):
    """Search metadata schema"""
    semantic_weight: float = Field(..., ge=0.0, le=1.0, description="Weight for semantic search")
    lexical_weight: float = Field(..., ge=0.0, le=1.0, description="Weight for lexical search")
    individual_results: Dict[str, int] = Field(..., description="Results count by search type")
    latency_ms: int = Field(..., ge=0, description="Search latency in milliseconds")

class SearchResponse(BaseModel):
    """Search response schema"""
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results")
    query: str = Field(..., description="Original search query")
    limit: int = Field(..., ge=1, description="Requested result limit")
    search_type: str = Field(..., description="Type of search performed")
    metadata: Optional[SearchMetadata] = Field(None, description="Search metadata")
    latency_ms: int = Field(..., ge=0, description="Total search latency in milliseconds")

class SearchError(BaseModel):
    """Search error response schema"""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
