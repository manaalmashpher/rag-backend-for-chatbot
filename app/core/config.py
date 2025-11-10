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
    
    # Chunking Configuration
    rag_chunk_target_tokens: Optional[int] = None  # Override default token targets
    rag_chunk_overlap_tokens: int = 50  # Token overlap between sibling chunks
    rag_backfill_batch_size: int = 16  # Batch size for backfill embedding generation
    
    # Upload
    max_upload_mb: int = 20
    storage_path: str = "./uploads"
    
    # Search Configuration
    topk_vec: int = 10  # Vector search top-K (reduced for performance)
    topk_lex: int = 10  # Lexical search top-K (reduced for performance)
    fuse_sem_weight: float = 0.6  # Semantic search weight
    fuse_lex_weight: float = 0.4  # Lexical search weight
    vector_score_threshold: float = 0.05  # Minimum cosine similarity score for vector search results
    
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
    
    # DeepSeek Configuration
    deepseek_api_key: Optional[str] = None
    
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
    
    # RAG Configuration
    rag_enable_hybrid: bool = True  # Enable hybrid search
    rag_enable_rerank: bool = True  # Enable reranking
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Convert storage_path to absolute path to avoid issues with relative paths
# when working directory changes (e.g., in background workers)
if not os.path.isabs(settings.storage_path):
    settings.storage_path = os.path.abspath(settings.storage_path)