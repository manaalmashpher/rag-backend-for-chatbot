"""
Type definitions for RAG chunks with rich metadata
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import hashlib
import json


@dataclass
class Chunk:
    """
    Rich chunk metadata for hierarchy-aware RAG system
    """
    # Core content
    text: str
    doc_id: int
    source_name: str
    
    # Clause identification
    section_id: Optional[str] = None  # e.g., "5.22.1"
    section_id_alias: Optional[str] = None  # e.g., "5_22_1"
    title: Optional[str] = None  # Cleaned clause title
    
    # Hierarchy
    parent_titles: List[str] = None  # Outermost → immediate parent
    
    # Structure
    level: Optional[int] = None  # Dot count + 1
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    
    # Content flags
    list_items: bool = False
    is_table: bool = False
    has_supporting_docs: bool = False
    
    # Token and hash
    token_count: Optional[int] = None
    hash: Optional[str] = None
    
    # Normalized text for lexical search
    text_norm: Optional[str] = None
    
    # Legacy fields for compatibility
    method: Optional[int] = None
    chunk_index: Optional[int] = None
    
    def __post_init__(self):
        """Initialize default values and compute derived fields"""
        if self.parent_titles is None:
            self.parent_titles = []
        
        # Compute section_id_alias if section_id exists
        if self.section_id and not self.section_id_alias:
            self.section_id_alias = self.section_id.replace('.', '_')
        
        # Compute level from section_id
        if self.section_id and self.level is None:
            self.level = self.section_id.count('.') + 1
        
        # Normalize text if not provided
        if self.text_norm is None and self.text:
            self.text_norm = self._normalize_text(self.text)
        
        # Compute hash if not provided
        if self.hash is None:
            self.hash = self._compute_hash()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for lexical search (lowercase, collapse whitespace)"""
        import re
        normalized = text.lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()
    
    def _compute_hash(self) -> str:
        """Compute stable hash for idempotency"""
        hash_input = {
            'text': self.text_norm or self._normalize_text(self.text),
            'section_id': self.section_id or '',
            'parent_titles': tuple(self.parent_titles),
            'doc_id': self.doc_id
        }
        hash_str = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        # Convert parent_titles list to JSON-compatible format
        result['parent_titles'] = self.parent_titles
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chunk':
        """Create Chunk from dictionary"""
        # Ensure parent_titles is a list
        if 'parent_titles' in data and isinstance(data['parent_titles'], str):
            import json
            data['parent_titles'] = json.loads(data['parent_titles'])
        elif 'parent_titles' not in data:
            data['parent_titles'] = []
        
        return cls(**data)
    
    def to_qdrant_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format"""
        return {
            'doc_id': self.doc_id,
            'chunk_id': getattr(self, 'chunk_id', None),  # Will be set after DB insert
            'section_id': self.section_id,
            'section_id_alias': self.section_id_alias,
            'title': self.title,
            'parent_titles': self.parent_titles,
            'level': self.level,
            'page_from': self.page_start,
            'page_to': self.page_end,
            'list_items': self.list_items,
            'is_table': self.is_table,
            'has_supporting_docs': self.has_supporting_docs,
            'source_name': self.source_name,
            'token_count': self.token_count,
            'hash': self.hash,
            'text_norm': self.text_norm,
            'method': self.method
        }

