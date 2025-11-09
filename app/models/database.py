"""
Database models for the application
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    mime = Column(String(100), nullable=False)
    bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ingestions = relationship("Ingestion", back_populates="document")
    chunks = relationship("Chunk", back_populates="document")

class Ingestion(Base):
    __tablename__ = "ingestions"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    method = Column(Integer, nullable=False)  # Chunking method 1-8
    status = Column(String(50), nullable=False, default="queued")
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="ingestions")

class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    method = Column(Integer, nullable=False)  # Chunking method used
    page_from = Column(Integer, nullable=True)
    page_to = Column(Integer, nullable=True)
    hash = Column(String(64), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # New hierarchy-aware metadata fields
    section_id = Column(String(100), nullable=True, index=True)  # e.g., "5.22.1"
    section_id_alias = Column(String(100), nullable=True, index=True)  # e.g., "5_22_1"
    title = Column(String(500), nullable=True)  # Cleaned clause title
    parent_titles = Column(JSON, nullable=True)  # List of parent titles (outermost → immediate)
    level = Column(Integer, nullable=True)  # Dot count + 1
    list_items = Column(Boolean, nullable=False, default=False)
    has_supporting_docs = Column(Boolean, nullable=False, default=False)
    token_count = Column(Integer, nullable=True)
    text_norm = Column(Text, nullable=True)  # Normalized text for lexical search
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes for efficient querying
    # Note: GIN index for parent_titles is created via migration script for Postgres
    __table_args__ = (
        Index('idx_chunks_section_id', 'section_id'),
        Index('idx_chunks_section_id_alias', 'section_id_alias'),
    )

class SearchLog(Base):
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    params_json = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
