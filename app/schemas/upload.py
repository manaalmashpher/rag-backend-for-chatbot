"""
Upload API schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import IntEnum

class ChunkingMethod(IntEnum):
    """Predefined chunking methods 1-9"""
    FIXED_TOKEN = 1
    SENTENCE_BASED = 2
    PARAGRAPH_BASED = 3
    MARKDOWN_HTML_BASED = 4
    SEMANTIC_SIMILARITY = 5
    RECURSIVE_SPLITTER = 6
    TABLE_LAYOUT_BASED = 7
    HIERARCHICAL = 8
    CLAUSE_AWARE = 9  # Hierarchy-aware clause chunking for standards/PDFs
    
    def get_description(self) -> str:
        """Get human-readable description of the chunking method"""
        descriptions = {
            ChunkingMethod.FIXED_TOKEN: "Fixed token windows (sliding) - 800 tokens / 120 overlap. Strong baseline; uniform windows.",
            ChunkingMethod.SENTENCE_BASED: "Sentence-based - Merge sentences up to ~800 tokens. Preserves semantics; punctuation-dependent.",
            ChunkingMethod.PARAGRAPH_BASED: "Paragraph-based - Merge paragraphs up to ~1000 tokens. Natural blocks; variable sizes.",
            ChunkingMethod.MARKDOWN_HTML_BASED: "Markdown/HTML based - Cap ~1200 tokens; record heading path. Great for docs/manuals.",
            ChunkingMethod.SEMANTIC_SIMILARITY: "Semantic similarity - Boundary by topic shift; ~700–1000 tokens. Higher quality; tune threshold.",
            ChunkingMethod.RECURSIVE_SPLITTER: "Recursive splitter - Balanced chunk sizes through recursive splitting.",
            ChunkingMethod.TABLE_LAYOUT_BASED: "Table layout based - PDF-specific layout analysis for better chunking.",
            ChunkingMethod.HIERARCHICAL: "Hierarchical - Combines multiple strategies for optimal document segmentation.",
            ChunkingMethod.CLAUSE_AWARE: "Clause-aware - Hierarchy-aware chunking at clause headings (e.g., 5.22.1) with parent context and list preservation."
        }
        return descriptions.get(self, "Unknown chunking method")

class UploadResponse(BaseModel):
    """Response for file upload"""
    ingestion_id: int
    status: str
    message: str

class UploadError(BaseModel):
    """Error response for upload failures"""
    error: str
    detail: Optional[str] = None
    blocked_reason: Optional[str] = None
