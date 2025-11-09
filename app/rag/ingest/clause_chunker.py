"""
Hierarchy-aware clause chunker for standards/PDF documents

Splits documents at hierarchical clause headings (e.g., 5.22.1) while preserving
list blocks and maintaining parent hierarchy context.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.rag.types import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClauseHeading:
    """Represents a detected clause heading"""
    section_id: str  # e.g., "5.22.1"
    title: str  # Cleaned title text
    level: int  # Number of dots + 1
    line_number: int  # Line number in original text
    is_merged: bool = False  # True if title and ID were merged (e.g., "Title5.22.1")


@dataclass
class TextBlock:
    """Represents a block of text with metadata"""
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    is_list: bool = False
    is_table: bool = False
    heading: Optional[ClauseHeading] = None
    parent_headings: List[ClauseHeading] = None
    
    def __post_init__(self):
        if self.parent_headings is None:
            self.parent_headings = []


class ClauseChunker:
    """
    Chunks documents based on hierarchical clause structure
    
    Primary split points: clause headings with dotted numeric IDs (e.g., 5.22.1)
    Preserves: lists, tables, and other atomic blocks
    Maintains: parent hierarchy context
    """
    
    # Regex patterns
    NORMAL_HEADING_PATTERN = re.compile(
        r'^(?P<id>\d+(?:\.\d+)+)\s+(?P<title>.+)$',
        re.MULTILINE
    )
    
    MERGED_HEADING_PATTERN = re.compile(
        r'^(?P<title>[A-Za-z][A-Za-z\s]*?)(?P<id>\d+(?:\.\d+)+)$',
        re.MULTILINE
    )
    
    SECTION_LABEL_PATTERN = re.compile(
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*(.+)$',
        re.MULTILINE
    )
    
    # List detection patterns
    BULLET_PATTERN = re.compile(r'^[\s]*[•\-\*\+]\s+', re.MULTILINE)
    NUMBERED_LIST_PATTERN = re.compile(r'^[\s]*\d+[\.\)]\s+', re.MULTILINE)
    TABLE_ROW_PATTERN = re.compile(r'^[\s]*\|.*\|[\s]*$', re.MULTILINE)
    
    # Supporting documents keywords
    SUPPORTING_DOCS_KEYWORDS = [
        'supporting documents',
        'supporting evidence',
        'evidence',
        'indicators',
        'objectives',
        'annex',
        'appendix'
    ]
    
    def __init__(
        self,
        target_tokens: Optional[int] = None,
        overlap_tokens: int = 50,
        model_name: Optional[str] = None
    ):
        """
        Initialize clause chunker
        
        Args:
            target_tokens: Target token count per chunk (default based on model)
            overlap_tokens: Token overlap between sibling chunks (default: 50)
            model_name: Embedding model name for tokenizer selection
        """
        self.model_name = model_name or settings.embedding_model
        
        # Set token targets based on model
        if target_tokens is None:
            if 'mpnet' in self.model_name.lower():
                self.target_tokens = 400  # 300-500 range, use 400 as default
            elif 'mini' in self.model_name.lower():
                self.target_tokens = 400  # Similar range for mini models
            else:
                self.target_tokens = 400  # Default
        else:
            self.target_tokens = target_tokens
        
        self.overlap_tokens = overlap_tokens
        
        # Initialize tokenizer lazily
        self._tokenizer = None
    
    def _get_tokenizer(self):
        """Get or initialize tokenizer for token counting"""
        if self._tokenizer is None:
            try:
                from transformers import AutoTokenizer
                # Use a generic tokenizer that works with most models
                # For sentence-transformers, we can use the base model tokenizer
                tokenizer_name = self.model_name
                if 'mpnet' in tokenizer_name.lower():
                    tokenizer_name = 'sentence-transformers/all-mpnet-base-v2'
                elif 'mini' in tokenizer_name.lower():
                    tokenizer_name = 'sentence-transformers/all-MiniLM-L6-v2'
                
                self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
            except Exception as e:
                logger.warning(f"Failed to load tokenizer {self.model_name}: {e}. Using character-based estimation.")
                self._tokenizer = None
        
        return self._tokenizer
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tokenizer or fallback estimation"""
        tokenizer = self._get_tokenizer()
        if tokenizer:
            try:
                tokens = tokenizer.encode(text, add_special_tokens=False)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Token counting failed: {e}. Using character estimation.")
        
        # Fallback: rough estimation (1 token ≈ 4 characters for English)
        return len(text) // 4
    
    def chunk_document(
        self,
        doc_text: str,
        doc_id: int,
        source_name: str,
        pages: Optional[List[Dict[str, Any]]] = None
    ) -> List[Chunk]:
        """
        Chunk a document with hierarchy-aware clause detection
        
        Args:
            doc_text: Full document text
            doc_id: Document ID
            source_name: Source document name
            pages: Optional list of page dicts with 'page_number' and 'text'
        
        Returns:
            List of Chunk objects with rich metadata
        """
        # Normalize and clean text
        normalized_text = self._normalize_text(doc_text)
        
        # Detect section labels (e.g., "Tenth Section: Research and Innovation")
        section_labels = self._detect_section_labels(normalized_text)
        
        # Detect clause headings
        headings = self._detect_headings(normalized_text)
        
        # Build hierarchy map
        hierarchy_map = self._build_hierarchy(headings, section_labels)
        
        # Split into blocks at clause boundaries
        blocks = self._split_into_blocks(normalized_text, headings, hierarchy_map, pages)
        
        # Process blocks into chunks with token size control
        chunks = self._process_blocks_to_chunks(blocks, doc_id, source_name)
        logger.info(f"Generated {len(chunks)} final chunks")
        
        return chunks
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text: collapse whitespace (but preserve newlines), strip headers/footers"""
        # Collapse repeated spaces/tabs but preserve newlines for structure detection
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Collapse spaces/tabs within the line
            line = re.sub(r'[ \t]+', ' ', line)
            # Remove page numbers at start/end of lines (standalone numbers)
            if re.match(r'^\s*\d+\s*$', line):
                continue
            cleaned_lines.append(line.strip())
        
        text = '\n'.join(cleaned_lines)
        
        # Remove empty lines at start/end
        text = text.strip()
        
        # Preserve original punctuation/casing in text
        # (normalized version stored separately in metadata)
        return text
    
    def _detect_section_labels(self, text: str) -> List[Tuple[int, str, str]]:
        """
        Detect section labels like "Tenth Section: Research and Innovation"
        
        Returns:
            List of (line_number, label, content) tuples
        """
        labels = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            match = self.SECTION_LABEL_PATTERN.match(line.strip())
            if match:
                label = match.group(1)
                content = match.group(2)
                labels.append((i, label, content))
        
        return labels
    
    def _detect_headings(self, text: str) -> List[ClauseHeading]:
        """
        Detect clause headings (both normal and merged formats)
        
        Returns:
            List of ClauseHeading objects
        """
        headings = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Try normal heading pattern first
            match = self.NORMAL_HEADING_PATTERN.match(line_stripped)
            if match:
                section_id = match.group('id')
                title = match.group('title').strip()
                level = section_id.count('.') + 1
                
                # Check if title ends with a section ID (merged artifact)
                title_clean = title
                merged_match = re.search(r'(\d+(?:\.\d+)+)$', title)
                if merged_match:
                    # Title has trailing ID - extract and clean
                    trailing_id = merged_match.group(1)
                    title_clean = title[:-len(trailing_id)].strip()
                    logger.info(f"Detected merged heading artifact: '{title}' -> cleaned to '{title_clean}'")
                
                headings.append(ClauseHeading(
                    section_id=section_id,
                    title=title_clean,
                    level=level,
                    line_number=i,
                    is_merged=False
                ))
                logger.debug(f"Detected heading at line {i}: {section_id} - {title_clean}")
                continue
            
            # Try merged heading pattern
            match = self.MERGED_HEADING_PATTERN.match(line_stripped)
            if match:
                title = match.group('title').strip()
                section_id = match.group('id')
                level = section_id.count('.') + 1
                
                headings.append(ClauseHeading(
                    section_id=section_id,
                    title=title,
                    level=level,
                    line_number=i,
                    is_merged=True
                ))
                logger.info(f"Detected merged heading at line {i}: {title} + {section_id}")
        
        return headings
    
    def _build_hierarchy(
        self,
        headings: List[ClauseHeading],
        section_labels: List[Tuple[int, str, str]]
    ) -> Dict[str, List[ClauseHeading]]:
        """
        Build hierarchy map: section_id -> list of parent headings (outermost first)
        
        Args:
            headings: List of detected clause headings
            section_labels: List of section labels with line numbers
        
        Returns:
            Dictionary mapping section_id to parent headings
        """
        hierarchy = {}
        
        # Sort headings by line number
        sorted_headings = sorted(headings, key=lambda h: h.line_number)
        
        # For each heading, find its parents
        for heading in sorted_headings:
            parents = []
            
            # Find section label that precedes this heading
            for label_line, label_text, label_content in section_labels:
                if label_line < heading.line_number:
                    # Create a pseudo-heading for the section label
                    section_heading = ClauseHeading(
                        section_id='',
                        title=f"{label_text}: {label_content}",
                        level=0,
                        line_number=label_line,
                        is_merged=False
                    )
                    # Only add the most recent section label
                    if not parents or parents[0].line_number < label_line:
                        parents = [section_heading]
            
            # Find numeric parent headings (immediate parent is the one with fewer dots)
            heading_parts = heading.section_id.split('.')
            for parent_heading in sorted_headings:
                if parent_heading.line_number >= heading.line_number:
                    break  # Can't be a parent if it comes after
                
                parent_parts = parent_heading.section_id.split('.')
                # Parent must have fewer parts and match the prefix
                if (len(parent_parts) < len(heading_parts) and
                    heading_parts[:len(parent_parts)] == parent_parts):
                    # This is a parent - add it (replacing any less specific parent)
                    parents = [p for p in parents if p.level != 0]  # Keep section labels
                    parents.append(parent_heading)
            
            hierarchy[heading.section_id] = parents
        
        return hierarchy
    
    def _split_into_blocks(
        self,
        text: str,
        headings: List[ClauseHeading],
        hierarchy_map: Dict[str, List[ClauseHeading]],
        pages: Optional[List[Dict[str, Any]]]
    ) -> List[TextBlock]:
        """
        Split text into blocks at clause boundaries
        
        Returns:
            List of TextBlock objects
        """
        blocks = []
        lines = text.split('\n')
        
        # Create a map of line number to heading
        heading_map = {h.line_number: h for h in headings}
        
        # Group lines by clause
        current_heading = None
        current_lines = []
        current_start_line = 0
        
        for i, line in enumerate(lines):
            # Check if this line is a heading
            if i in heading_map:
                # Save previous block if it has content
                if current_heading and current_lines:
                    block_text = '\n'.join(current_lines).strip()
                    if block_text:
                        # Determine page range
                        page_start, page_end = self._find_page_range(
                            current_start_line, i - 1, pages
                        )
                        
                        # Detect if block contains lists or tables
                        is_list = self._is_list_block(block_text)
                        is_table = self._is_table_block(block_text)
                        
                        blocks.append(TextBlock(
                            text=block_text,
                            page_start=page_start,
                            page_end=page_end,
                            is_list=is_list,
                            is_table=is_table,
                            heading=current_heading,
                            parent_headings=hierarchy_map.get(current_heading.section_id, [])
                        ))
                
                # Start new block
                current_heading = heading_map[i]
                current_lines = [line]
                current_start_line = i
            else:
                current_lines.append(line)
        
        # Handle final block
        if current_heading and current_lines:
            block_text = '\n'.join(current_lines).strip()
            if block_text:
                page_start, page_end = self._find_page_range(
                    current_start_line, len(lines) - 1, pages
                )
                is_list = self._is_list_block(block_text)
                is_table = self._is_table_block(block_text)
                blocks.append(TextBlock(
                    text=block_text,
                    page_start=page_start,
                    page_end=page_end,
                    is_list=is_list,
                    is_table=is_table,
                    heading=current_heading,
                    parent_headings=hierarchy_map.get(current_heading.section_id, [])
                ))
        
        # Handle text before first heading
        if headings and headings[0].line_number > 0:
            pre_text = '\n'.join(lines[:headings[0].line_number]).strip()
            if pre_text:
                page_start, page_end = self._find_page_range(0, headings[0].line_number - 1, pages)
                blocks.insert(0, TextBlock(
                    text=pre_text,
                    page_start=page_start,
                    page_end=page_end,
                    is_list=self._is_list_block(pre_text),
                    is_table=self._is_table_block(pre_text)
                ))
        
        return blocks
    
    def _is_list_block(self, text: str) -> bool:
        """Check if text block contains list items"""
        lines = text.split('\n')
        list_line_count = 0
        
        for line in lines:
            if (self.BULLET_PATTERN.match(line) or
                self.NUMBERED_LIST_PATTERN.match(line)):
                list_line_count += 1
        
        # Consider it a list if >30% of lines are list items (excluding table rows)
        return len(lines) > 0 and (list_line_count / len(lines)) > 0.3
    
    def _is_table_block(self, text: str) -> bool:
        """Check if text block contains table rows"""
        lines = text.split('\n')
        table_line_count = 0
        
        for line in lines:
            if self.TABLE_ROW_PATTERN.match(line):
                table_line_count += 1
        
        # Consider it a table if >30% of lines are table rows
        return len(lines) > 0 and (table_line_count / len(lines)) > 0.3
    
    def _find_page_range(
        self,
        start_line: int,
        end_line: int,
        pages: Optional[List[Dict[str, Any]]]
    ) -> Tuple[Optional[int], Optional[int]]:
        """Find page range for given line range"""
        if not pages:
            return None, None
        
        # Simple heuristic: map line numbers to pages
        # This is approximate - could be improved with more sophisticated mapping
        total_lines = sum(len(page.get('text', '').split('\n')) for page in pages)
        if total_lines == 0:
            return pages[0].get('page_number') if pages else None, pages[-1].get('page_number') if pages else None
        
        # Estimate page based on line position
        line_ratio = start_line / max(total_lines, 1)
        page_start_idx = int(line_ratio * len(pages))
        page_start = pages[min(page_start_idx, len(pages) - 1)].get('page_number')
        
        line_ratio_end = end_line / max(total_lines, 1)
        page_end_idx = int(line_ratio_end * len(pages))
        page_end = pages[min(page_end_idx, len(pages) - 1)].get('page_number')
        
        return page_start, page_end
    
    def _process_blocks_to_chunks(
        self,
        blocks: List[TextBlock],
        doc_id: int,
        source_name: str
    ) -> List[Chunk]:
        """
        Process blocks into chunks with token size control and overlap
        
        If a block exceeds target tokens, split it at subheadings or paragraph boundaries,
        never splitting inside list items.
        """
        chunks = []
        
        for block in blocks:
            block_tokens = self._count_tokens(block.text)
            
            if block_tokens <= self.target_tokens:
                # Block fits in one chunk
                chunk = self._block_to_chunk(block, doc_id, source_name)
                chunks.append(chunk)
            else:
                # Block is too large - split it
                sub_chunks = self._split_large_block(block, doc_id, source_name)
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _block_to_chunk(
        self,
        block: TextBlock,
        doc_id: int,
        source_name: str
    ) -> Chunk:
        """Convert a TextBlock to a Chunk"""
        heading = block.heading
        
        # Extract parent titles
        parent_titles = []
        if block.parent_headings:
            for parent in block.parent_headings:
                if parent.title:
                    parent_titles.append(parent.title)
        
        # Check for supporting documents
        has_supporting_docs = any(
            keyword.lower() in block.text.lower()
            for keyword in self.SUPPORTING_DOCS_KEYWORDS
        )
        
        # Normalize text
        text_norm = block.text.lower()
        text_norm = re.sub(r'\s+', ' ', text_norm).strip()
        
        return Chunk(
            text=block.text,
            doc_id=doc_id,
            source_name=source_name,
            section_id=heading.section_id if heading else None,
            section_id_alias=heading.section_id.replace('.', '_') if heading and heading.section_id else None,
            title=heading.title if heading else None,
            parent_titles=parent_titles,
            level=heading.level if heading else None,
            page_start=block.page_start,
            page_end=block.page_end,
            list_items=block.is_list,
            is_table=block.is_table,
            has_supporting_docs=has_supporting_docs,
            token_count=self._count_tokens(block.text),
            text_norm=text_norm
        )
    
    def _split_large_block(
        self,
        block: TextBlock,
        doc_id: int,
        source_name: str
    ) -> List[Chunk]:
        """
        Split a large block into multiple chunks with overlap
        
        Splits at paragraph boundaries or between list items, never inside them.
        """
        chunks = []
        paragraphs = self._split_into_paragraphs(block.text)
        
        current_chunk_text = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            
            # If adding this paragraph would exceed target, finalize current chunk
            if (current_tokens + para_tokens > self.target_tokens and
                current_chunk_text):
                # Create chunk from accumulated text
                chunk_text = '\n\n'.join(current_chunk_text)
                chunk = self._block_to_chunk(
                    TextBlock(
                        text=chunk_text,
                        page_start=block.page_start,
                        page_end=block.page_end,
                        is_list=block.is_list,
                        is_table=block.is_table,
                        heading=block.heading,
                        parent_headings=block.parent_headings
                    ),
                    doc_id,
                    source_name
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                if self.overlap_tokens > 0:
                    # Add last N tokens from previous chunk as overlap
                    overlap_text = self._get_overlap_text(chunk_text, self.overlap_tokens)
                    current_chunk_text = [overlap_text, para]
                    current_tokens = self._count_tokens(overlap_text) + para_tokens
                else:
                    current_chunk_text = [para]
                    current_tokens = para_tokens
            else:
                current_chunk_text.append(para)
                current_tokens += para_tokens
        
        # Handle final chunk
        if current_chunk_text:
            chunk_text = '\n\n'.join(current_chunk_text)
            chunk = self._block_to_chunk(
                TextBlock(
                    text=chunk_text,
                    page_start=block.page_start,
                    page_end=block.page_end,
                    is_list=block.is_list,
                    is_table=block.is_table,
                    heading=block.heading,
                    parent_headings=block.parent_headings
                ),
                doc_id,
                source_name
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, preserving list items as atomic units"""
        # Split by double newlines first
        paragraphs = text.split('\n\n')
        
        # Further split single paragraphs if they're very long
        result = []
        for para in paragraphs:
            # Check if paragraph is a list item
            if (self.BULLET_PATTERN.match(para.strip()) or
                self.NUMBERED_LIST_PATTERN.match(para.strip())):
                # Keep list items intact
                result.append(para)
            else:
                # For very long paragraphs, split at sentence boundaries
                if len(para) > 2000:  # Character threshold
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current = []
                    for sent in sentences:
                        if len('\n'.join(current) + sent) < 2000:
                            current.append(sent)
                        else:
                            if current:
                                result.append(' '.join(current))
                            current = [sent]
                    if current:
                        result.append(' '.join(current))
                else:
                    result.append(para)
        
        return [p.strip() for p in result if p.strip()]
    
    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Extract last N tokens from text for overlap"""
        tokens = self._count_tokens(text)
        if tokens <= overlap_tokens:
            return text
        
        # Approximate: get last portion of text
        # This is simplified - could be improved with actual token boundaries
        char_ratio = overlap_tokens / tokens
        overlap_chars = int(len(text) * char_ratio)
        return text[-overlap_chars:].strip()

