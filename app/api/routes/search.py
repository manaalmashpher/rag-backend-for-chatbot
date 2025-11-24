"""
Search API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import time
import logging
import hashlib
from functools import lru_cache
from pydantic import ValidationError

from app.services.hybrid_search import HybridSearchService
from app.services.reranker import RerankerService
from app.schemas.search import SearchRequest, SearchResponse, SearchError, SearchMetadata
from app.core.database import get_db
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models.database import SearchLog, Chunk, Document
import re

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
search_service = HybridSearchService()
reranker_service = RerankerService()

# Search result cache (in-memory for now, could be Redis in production)
_search_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes cache

# Rate limiting is handled by middleware, no need for duplicate implementation here

@router.get("/search", response_model=SearchResponse)
async def search_documents(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="Search query string"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search documents using hybrid search (semantic + lexical) with caching
    
    Args:
        q: Natural language search query
        limit: Maximum number of results to return (1-50)
        db: Database session
        
    Returns:
        SearchResponse with ranked results and metadata
    """
    start_time = time.time()
    
    # Rate limiting is handled by middleware
    
    try:
        # Validate request
        search_request = SearchRequest(q=q, limit=limit)
        
        # Check cache first
        cache_key = _get_cache_key(search_request.q, search_request.limit)
        cached_result = _get_cached_result(cache_key)
        
        if cached_result:
            return cached_result
        
        # EXPLICIT "GO TO SECTION" FEATURE
        # Check if query is a direct section reference (e.g., "section 5.22.3", "show section 5.22.3")
        section_direct_results = _handle_section_direct_lookup(search_request.q, search_request.limit, db)
        if section_direct_results is not None:
            # Direct section lookup succeeded, return results immediately
            latency_ms = int((time.time() - start_time) * 1000)
            
            response = SearchResponse(
                results=section_direct_results,
                total_results=len(section_direct_results),
                query=search_request.q,
                limit=search_request.limit,
                search_type="section-direct",
                metadata=SearchMetadata(
                    semantic_weight=0.0,
                    lexical_weight=0.0,
                    individual_results={"section-direct": len(section_direct_results)},
                    latency_ms=latency_ms
                ),
                latency_ms=latency_ms
            )
            
            # Cache the result
            _cache_result(cache_key, response)
            
            logger.info(f"Section direct lookup completed: {len(section_direct_results)} results in {latency_ms}ms for query: {search_request.q[:50]}...")
            return response
        
        # Perform hybrid search with top_k=50 for reranking
        import asyncio
        try:
            # Run search in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Get top_k candidates for reranking (default 50)
            top_k = getattr(settings, 'rerank_top_k', 50)
            search_metadata = await loop.run_in_executor(
                None, 
                search_service.search_with_metadata,
                search_request.q,
                top_k
            )
        except Exception as e:
            logger.error(f"Search execution failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Search execution failed")
        
        # Apply reranking if service is available
        hybrid_results = search_metadata['results']
        try:
            if reranker_service.is_available():
                # Get top_r from config (default 10)
                top_r = getattr(settings, 'rerank_top_r', 10)
                
                # Rerank the results
                reranked_results = reranker_service.rerank(
                    search_request.q,
                    hybrid_results,
                    top_r
                )
                logger.info(f"Reranked {len(hybrid_results)} candidates to {len(reranked_results)} results")
                search_metadata['results'] = reranked_results
                search_metadata['search_type'] = 'hybrid-reranked'
            else:
                logger.warning("Reranking service not available, using hybrid search results")
                search_metadata['results'] = hybrid_results[:search_request.limit]
                search_metadata['search_type'] = 'hybrid'
        except Exception as e:
            logger.error(f"Reranking failed: {str(e)}, falling back to hybrid search")
            search_metadata['results'] = hybrid_results[:search_request.limit]
            search_metadata['search_type'] = 'hybrid'
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Format results with snippets
        formatted_results = []
        for result in search_metadata['results']:
            # Generate snippet with query highlighting
            result_text = result.get('text', '')
            snippet = _generate_snippet(result_text, search_request.q)
            
            # Ensure method is valid (must be 1-8 per schema)
            method = result.get('method')
            if not method or method < 1 or method > 8:
                method = 1  # Default to 1 if invalid or missing
            
            # Ensure score is within valid range (0.0-1.0 per schema)
            score = float(result.get('fused_score', 0.0))
            score = max(0.0, min(1.0, score))  # Clamp to [0.0, 1.0]
            
            formatted_result = {
                'chunk_id': str(result.get('chunk_id', '')),
                'doc_id': str(result.get('doc_id', '')),
                'method': int(method),
                'page_from': int(result.get('page_from')) if result.get('page_from') else None,
                'page_to': int(result.get('page_to')) if result.get('page_to') else None,
                'hash': str(result.get('hash', '')),
                'source': str(result.get('source', '')),
                'snippet': str(snippet) if snippet else None,
                'score': score,
                'search_type': search_metadata.get('search_type', 'hybrid')
            }
            
            # Add rerank_score if available (from reranking service)
            if 'rerank_score' in result:
                formatted_result['rerank_score'] = float(result['rerank_score'])
            
            formatted_results.append(formatted_result)
        
        # Create response first (before any database operations that might fail)
        try:
            response = SearchResponse(
                results=formatted_results,
                total_results=len(formatted_results),
                query=search_request.q,
                limit=search_request.limit,
                search_type=search_metadata.get('search_type', 'hybrid'),
                metadata=SearchMetadata(
                    semantic_weight=search_metadata['fusion_weights']['semantic'],
                    lexical_weight=search_metadata['fusion_weights']['lexical'],
                    individual_results=search_metadata['individual_results'],
                    latency_ms=latency_ms
                ),
                latency_ms=latency_ms
            )
        except ValidationError as ve:
            logger.error(f"Response validation failed: {str(ve)}")
            error_response = SearchError(
                error="Response validation failed",
                error_code="VALIDATION_ERROR",
                details={"validation_errors": str(ve.errors())}
            )
            raise HTTPException(status_code=400, detail=error_response.model_dump())
        
        # Log search query (async to not block response) - do this after creating response
        # Use background task or just catch errors silently
        try:
            _log_search_query_async(db, search_request.q, search_metadata, latency_ms)
        except Exception as log_error:
            # Don't fail the search if logging fails
            logger.warning(f"Failed to log search query (non-critical): {str(log_error)}")
        
        # Cache the result
        _cache_result(cache_key, response)
        
        logger.info(f"Search completed: {len(formatted_results)} results in {latency_ms}ms for query: {search_request.q[:50]}...")
        return response
        
    except ValidationError as ve:
        # Pydantic validation error
        logger.error(f"Request validation failed: {str(ve)}")
        error_response = SearchError(
            error="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"validation_errors": str(ve.errors())}
        )
        raise HTTPException(status_code=400, detail=error_response.model_dump())
        
    except ValueError as e:
        # Validation error
        error_response = SearchError(
            error=str(e),
            error_code="VALIDATION_ERROR",
            details={"field": "query"}
        )
        raise HTTPException(status_code=400, detail=error_response.model_dump())
        
    except Exception as e:
        # Internal server error
        logger.error(f"Search failed: {str(e)}")
        error_response = SearchError(
            error="Internal search error",
            error_code="SEARCH_ERROR",
            details={"message": str(e)}
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())


def _generate_snippet(text: str, query: str, max_length: int = 200) -> str:
    """
    Generate a text snippet with query highlighting
    
    Args:
        text: Full text content
        query: Search query for highlighting
        max_length: Maximum snippet length
        
    Returns:
        Highlighted snippet string
    """
    if not text:
        return ""
    
    # If no query provided, return beginning of text
    if not query:
        return text[:max_length] + "..." if len(text) > max_length else text
    
    # Clean and prepare text
    text = text.strip()
    if len(text) <= max_length:
        return text
    
    # Try to find exact query terms first
    query_terms = query.lower().split()
    text_lower = text.lower()
    
    # Find the first occurrence of any query term
    best_position = 0
    found_terms = False
    
    for term in query_terms:
        pos = text_lower.find(term)
        if pos != -1:
            if not found_terms or pos < best_position:
                best_position = pos
            found_terms = True
    
    # If exact terms found, extract snippet around them
    if found_terms:
        start = max(0, best_position - max_length // 2)
        end = min(len(text), start + max_length)
        snippet = text[start:end]
        
        # Add ellipsis if needed
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    # If no exact terms found, try partial word matches
    for term in query_terms:
        for i in range(len(term), 3, -1):  # Try shorter substrings
            partial_term = term[:i]
            pos = text_lower.find(partial_term)
            if pos != -1:
                start = max(0, pos - max_length // 2)
                end = min(len(text), start + max_length)
                snippet = text[start:end]
                
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                
                return snippet
    
    # If no matches at all, return the beginning of the text
    # This handles semantic matches where the concept is related but words don't match
    return text[:max_length] + "..."

def _get_cache_key(query: str, limit: int) -> str:
    """Generate cache key for search query"""
    return hashlib.md5(f"{query.lower().strip()}:{limit}".encode()).hexdigest()

def _get_cached_result(cache_key: str) -> Optional[SearchResponse]:
    """Get cached search result if valid"""
    if cache_key in _search_cache:
        cached_data = _search_cache[cache_key]
        if time.time() - cached_data['timestamp'] < CACHE_TTL:
            return cached_data['response']
        else:
            # Remove expired cache entry
            del _search_cache[cache_key]
    return None

def _cache_result(cache_key: str, response: SearchResponse):
    """Cache search result"""
    _search_cache[cache_key] = {
        'response': response,
        'timestamp': time.time()
    }
    
    # Simple cache cleanup - remove old entries if cache gets too large
    if len(_search_cache) > 1000:
        current_time = time.time()
        expired_keys = [
            key for key, data in _search_cache.items()
            if current_time - data['timestamp'] > CACHE_TTL
        ]
        for key in expired_keys:
            del _search_cache[key]

def _handle_section_direct_lookup(query: str, limit: int, db: Session) -> Optional[List[Dict[str, Any]]]:
    """
    Handle explicit "go to section" queries with direct DB lookup
    
    Detects patterns like:
    - "section 5.22.3"
    - "show section 5.22.3"
    - "go to section 5.22.3"
    - "5.22.3" (if query is mostly just the section ID)
    
    This is for explicit navigation queries, not semantic queries about sections.
    For queries like "what's expected in section 5.22.3", the HybridSearchService
    will handle the section-id-first path.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        db: Database session
        
    Returns:
        List of SearchResult dictionaries if section query detected and found, None otherwise
    """
    try:
        # Pattern to match explicit section references
        # Matches: "section 5.22.3", "show section 5.22.3", "go to section 5.22.3"
        explicit_patterns = [
            r'^(?:show\s+|go\s+to\s+)?section\s+(\d+(?:\.\d+)+)\s*$',  # "section 5.22.3" or "show section 5.22.3"
            r'^(\d+(?:\.\d+)+)\s*$',  # Just "5.22.3"
        ]
        
        section_id = None
        for pattern in explicit_patterns:
            match = re.match(pattern, query.strip(), re.IGNORECASE)
            if match:
                section_id = match.group(1)
                break
        
        # If no explicit pattern matched, check if query is very short and contains a section ID
        if not section_id:
            # Pattern to extract section ID from query
            section_pattern = r'(\d+(?:\.\d+)+)'
            match = re.search(section_pattern, query)
            if match:
                section_id = match.group(1)
                # Only treat as direct lookup if query is very short (mostly just section ID + minimal words)
                query_words = re.findall(r'\b\w+\b', query.lower())
                # Remove common navigation words
                navigation_words = {'section', 'show', 'go', 'to', 'the'}
                meaningful_words = [w for w in query_words if w not in navigation_words and not w.isdigit()]
                
                # If there are more than 2 meaningful words beyond the section ID, use normal search
                if len(meaningful_words) > 2:
                    return None
        
        if not section_id:
            return None
        
        section_id_alias = section_id.replace('.', '_')
        
        # Direct DB lookup: first try exact section_id
        chunks = db.query(Chunk).join(Document).filter(
            (Chunk.section_id == section_id) | (Chunk.section_id_alias == section_id_alias)
        ).order_by(Chunk.page_from.asc(), Chunk.id.asc()).limit(limit).all()
        
        # If no exact match, try parent section fallback
        if not chunks and '.' in section_id:
            segments = section_id.split('.')
            if len(segments) >= 2:
                parent_section_id = '.'.join(segments[:-1])
                parent_section_id_alias = parent_section_id.replace('.', '_')
                
                logger.info(f"Section {section_id} not found, trying parent section {parent_section_id}")
                
                chunks = db.query(Chunk).join(Document).filter(
                    (Chunk.section_id == parent_section_id) | (Chunk.section_id_alias == parent_section_id_alias)
                ).order_by(Chunk.page_from.asc(), Chunk.id.asc()).limit(limit).all()
        
        if not chunks:
            return None
        
        # Build SearchResult list
        results = []
        for idx, chunk in enumerate(chunks):
            # Generate snippet from chunk text
            snippet = _generate_snippet(chunk.text, query)
            
            # Use high score for direct section matches (1.0 for first, slightly decreasing)
            score = 1.0 - (idx * 0.01)
            score = max(0.9, score)
            
            result = {
                'chunk_id': f"ch_{chunk.id:05d}",
                'doc_id': f"doc_{chunk.doc_id:02X}",
                'method': int(chunk.method),
                'page_from': int(chunk.page_from) if chunk.page_from else None,
                'page_to': int(chunk.page_to) if chunk.page_to else None,
                'hash': str(chunk.hash),
                'source': chunk.document.title if chunk.document else '',
                'snippet': snippet if snippet else None,
                'score': score,
                'search_type': 'section-direct'
            }
            results.append(result)
        
        logger.info(f"Section direct lookup found {len(results)} chunks for section {section_id}")
        return results
        
    except Exception as e:
        logger.error(f"Section direct lookup failed: {str(e)}")
        return None

def _log_search_query_async(db: Session, query: str, metadata: dict, latency_ms: int):
    """
    Log search query to database asynchronously to not block response
    
    Args:
        db: Database session
        query: Search query string
        metadata: Search metadata
        latency_ms: Search latency in milliseconds
    """
    try:
        # Check if session is still valid before using it
        from sqlalchemy.exc import InvalidRequestError
        try:
            # Try to refresh the session to check if it's still valid
            db.expire_all()
        except (InvalidRequestError, Exception) as session_error:
            logger.warning(f"Database session invalid for logging, skipping: {str(session_error)}")
            return
        
        search_log = SearchLog(
            query=query,
            params_json={
                'limit': metadata.get('limit', 10),
                'fusion_weights': metadata.get('fusion_weights', {}),
                'individual_results': metadata.get('individual_results', {})
            },
            latency_ms=latency_ms
        )
        db.add(search_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log search query: {str(e)}")
        # Don't fail the search if logging fails
        try:
            db.rollback()
        except:
            pass
