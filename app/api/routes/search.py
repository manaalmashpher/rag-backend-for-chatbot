"""
Search API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from typing import Optional
import time
import logging

from app.services.hybrid_search import HybridSearchService
from app.schemas.search import SearchRequest, SearchResponse, SearchError
from app.core.database import get_db
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models.database import SearchLog

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
search_service = HybridSearchService()

# Rate limiting is handled by middleware, no need for duplicate implementation here

@router.get("/search", response_model=SearchResponse)
async def search_documents(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="Search query string"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search documents using hybrid search (semantic + lexical)
    
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
        
        # Perform hybrid search
        search_metadata = search_service.search_with_metadata(
            query=search_request.q,
            limit=search_request.limit
        )
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Format results with snippets
        formatted_results = []
        for result in search_metadata['results']:
            # Generate snippet with query highlighting
            snippet = _generate_snippet(result.get('text', ''), search_request.q)
            
            formatted_result = {
                'chunk_id': str(result.get('chunk_id', '')),
                'doc_id': str(result.get('doc_id', '')),
                'method': int(result.get('method', 0)),
                'page_from': int(result.get('page_from')) if result.get('page_from') else None,
                'page_to': int(result.get('page_to')) if result.get('page_to') else None,
                'hash': str(result.get('hash', '')),
                'source': str(result.get('source', '')),
                'snippet': str(snippet) if snippet else None,
                'score': float(result.get('fused_score', 0.0)),
                'search_type': 'hybrid'
            }
            formatted_results.append(formatted_result)
        
        # Log search query
        _log_search_query(db, search_request.q, search_metadata, latency_ms)
        
        # Create response
        response = SearchResponse(
            results=formatted_results,
            total_results=len(formatted_results),
            query=search_request.q,
            limit=search_request.limit,
            search_type='hybrid',
            metadata={
                'semantic_weight': search_metadata['fusion_weights']['semantic'],
                'lexical_weight': search_metadata['fusion_weights']['lexical'],
                'individual_results': search_metadata['individual_results'],
                'latency_ms': latency_ms
            },
            latency_ms=latency_ms
        )
        
        logger.info(f"Search completed: {len(formatted_results)} results in {latency_ms}ms for query: {search_request.q[:50]}...")
        return response
        
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

def _log_search_query(db: Session, query: str, metadata: dict, latency_ms: int):
    """
    Log search query to database
    
    Args:
        db: Database session
        query: Search query string
        metadata: Search metadata
        latency_ms: Search latency in milliseconds
    """
    try:
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
