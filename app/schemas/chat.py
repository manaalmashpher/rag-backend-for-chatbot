"""
Chat API schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import re
import uuid

class Citation(BaseModel):
    """Citation schema for chat response"""
    doc_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Chunk identifier")
    page_from: Optional[int] = Field(None, ge=1, description="Starting page number")
    page_to: Optional[int] = Field(None, ge=1, description="Ending page number")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    text: str = Field(..., description="Chunk text content")

class ChatRequest(BaseModel):
    """Chat request schema"""
    conversation_id: Optional[str] = Field(None, description="Optional UUID string for conversation tracking")
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """Validate conversation_id is a valid UUID format if provided"""
        if v is None or v == "":
            return None  # Allow None/empty for new sessions
        
        try:
            # Validate UUID format
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("conversation_id must be a valid UUID format")
    
    @validator('message')
    def validate_message(cls, v):
        """Validate and sanitize message string"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        
        # Basic sanitization - remove potentially harmful characters
        sanitized = re.sub(r'[<>"\'\\]', '', v.strip())
        
        # Normalize whitespace but preserve line breaks
        sanitized = '\n'.join(line.strip() for line in sanitized.split('\n') if line.strip())
        
        if not sanitized:
            raise ValueError("Message contains only invalid characters")
        
        return sanitized

class ChatResponse(BaseModel):
    """Chat response schema"""
    answer: str = Field(..., description="Synthesized answer from DeepSeek")
    citations: List[Citation] = Field(default_factory=list, description="Array of citation objects")
    session_id: str = Field(..., description="Session ID (created or existing)")
    latency_ms: int = Field(..., ge=0, description="Response latency in milliseconds")

class ChatError(BaseModel):
    """Chat error response schema - follows standardized error model"""
    error: Dict[str, Any] = Field(..., description="Error object with code, message, details, requestId")
    
    @classmethod
    def create(cls, code: str, message: str, details: Optional[Dict[str, Any]] = None, request_id: str = "unknown"):
        """Helper method to create standardized error response"""
        return cls(error={
            "code": code,
            "message": message,
            "details": details or {},
            "requestId": request_id
        })

