"""
Chat API endpoints
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import time
import logging
import uuid as uuid_lib

from app.services.chat_orchestrator import ChatOrchestrator
from app.schemas.chat import ChatRequest, ChatResponse, ChatError, Citation
from app.core.config import settings
from app.deps.exceptions import MissingAPIKeyError, InvalidAPIKeyError

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize chat orchestrator service
chat_orchestrator = ChatOrchestrator()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest
):
    """
    Chat endpoint that integrates with chat orchestrator service
    
    Args:
        request: FastAPI request object
        chat_request: Chat request with conversation_id and message
        
    Returns:
        ChatResponse with synthesized answer and citations
    """
    start_time = time.time()
    request_id = request.headers.get("X-Correlation-ID", str(uuid_lib.uuid4()))
    
    try:
        logger.info(f"Chat request received: conversation_id={chat_request.conversation_id}, message_length={len(chat_request.message)}")
        
        # Validate request (validation is handled by Pydantic, but we log it)
        logger.debug(f"Validated request: conversation_id={chat_request.conversation_id}")
        
        # Integrate with chat orchestrator service
        # Step 1: Retrieve candidates
        candidates = chat_orchestrator.retrieve_candidates(chat_request.message, top_k=20)
        logger.info(f"Retrieved {len(candidates)} candidates")
        
        # Step 2: Rerank candidates
        reranked = chat_orchestrator.rerank(chat_request.message, candidates, top_k=8)
        logger.info(f"Reranked to {len(reranked)} candidates")
        
        # Step 3: Synthesize answer
        answer = chat_orchestrator.synthesize_answer(chat_request.message, reranked)
        logger.info("Answer synthesis completed")
        
        # Build citations from reranked chunks
        citations = []
        for chunk in reranked:
            citation = Citation(
                doc_id=str(chunk.get("doc_id", "")),
                chunk_id=str(chunk.get("chunk_id", "")),
                page_from=chunk.get("page_from"),
                page_to=chunk.get("page_to"),
                score=float(chunk.get("score", 0.0)),
                text=str(chunk.get("text", ""))
            )
            citations.append(citation)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Create response
        response = ChatResponse(
            answer=answer,
            citations=citations,
            conversation_id=chat_request.conversation_id,
            latency_ms=latency_ms
        )
        
        logger.info(f"Chat request completed: conversation_id={chat_request.conversation_id}, latency_ms={latency_ms}, citations_count={len(citations)}")
        return response
        
    except MissingAPIKeyError as e:
        # Authentication error - missing API key
        logger.error(f"DeepSeek API key missing: {str(e)}")
        error_response = ChatError.create(
            code="AUTH_ERROR",
            message="DeepSeek API key is not configured. Please configure DEEPSEEK_API_KEY environment variable or Settings.deepseek_api_key",
            details={"error_type": "missing_api_key"},
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())
    except InvalidAPIKeyError as e:
        # Authentication error - invalid API key
        logger.error(f"DeepSeek API key invalid: {str(e)}")
        error_response = ChatError.create(
            code="INVALID_API_KEY",
            message="DeepSeek API key is invalid or authentication failed. Please verify your API key configuration",
            details={"error_type": "invalid_api_key"},
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())
    except ValueError as e:
        # Defensive handler for ValueError (Pydantic validation occurs before this handler,
        # but this provides safety net for any manual validation or edge cases)
        # Note: FastAPI's Pydantic validation happens at request parsing, so this is unlikely to execute
        logger.warning(f"Validation error (defensive handler): {str(e)}")
        error_response = ChatError.create(
            code="VALIDATION_ERROR",
            message=str(e),
            details={"field": "request"},
            request_id=request_id
        )
        raise HTTPException(status_code=400, detail=error_response.model_dump())
        
    except RuntimeError as e:
        # Service error (from chat orchestrator)
        logger.error(f"Chat orchestrator error: {str(e)}")
        error_response = ChatError.create(
            code="CHAT_ERROR",
            message="Failed to process chat request",
            details={"error": str(e)},
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())
        
    except Exception as e:
        # Internal server error
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        error_response = ChatError.create(
            code="INTERNAL_ERROR",
            message="Internal server error",
            details={"message": str(e) if getattr(settings, 'debug', False) else "An unexpected error occurred"},
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=error_response.model_dump())

