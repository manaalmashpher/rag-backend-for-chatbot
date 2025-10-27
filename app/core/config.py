"""
Application configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./ionologybot.db"  # Will be overridden by env var
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"  # Will be overridden by env var
    qdrant_api_key: str = ""  # Will be overridden by env var
    qdrant_collection: str = "corpus_default"
    
    # Embeddings
    embedding_model: str = "all-mpnet-base-v2"  # Free, high quality, 768 dimensions
    embed_dim: int = 768
    
    # Upload
    max_upload_mb: int = 20
    storage_path: str = "./uploads"
    
    # Search Configuration
    topk_vec: int = 10  # Vector search top-K (reduced for performance)
    topk_lex: int = 10  # Lexical search top-K (reduced for performance)
    fuse_sem_weight: float = 0.6  # Semantic search weight
    fuse_lex_weight: float = 0.4  # Lexical search weight
    
    # Reranking Configuration
    rerank_top_k: int = 50  # Number of candidates to rerank
    rerank_top_r: int = 10  # Number of final reranked results
    rerank_batch_size: int = 16  # Batch size for processing
    rerank_max_chars: int = 2000  # Maximum characters per text for memory management
    
    # Authentication Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    bcrypt_rounds: int = 12
    
    # LLM Configuration (not yet implemented)
    # llm_provider: Optional[str] = None
    # llm_model: str = "llama3-8b-8192"
    # llm_api_key: Optional[str] = None
    # llm_max_tokens: int = 1000
    # llm_temperature: float = 0.7
    
    # Embedding Provider Configuration
    embedding_provider: str = "local"  # local, openai, cohere, etc.
    openai_api_key: Optional[str] = None
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json, text
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = True
    rate_limit_qps: int = 20  # Requests per minute per IP
    rate_limit_burst: int = 25  # Burst allowance
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
