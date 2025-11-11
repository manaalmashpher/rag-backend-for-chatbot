"""
Chat orchestrator service that handles retrieval, reranking, context building, and answer synthesis
"""

from typing import List, Dict, Any, Optional
import logging
from app.services.hybrid_search import HybridSearchService
from app.services.reranker import RerankerService
from app.deps.deepseek_client import deepseek_chat
from app.deps.exceptions import MissingAPIKeyError, InvalidAPIKeyError

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Orchestrates the complete chat flow: retrieval -> reranking -> context building -> answer synthesis
    """
    
    def __init__(self):
        """Initialize the chat orchestrator with required services"""
        self.hybrid_search = HybridSearchService()
        self.reranker = RerankerService()
        
    def retrieve_candidates(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve candidate chunks using hybrid search
        
        Args:
            query: User query string
            top_k: Maximum number of candidates to retrieve
            
        Returns:
            List of candidate chunks with metadata
        """
        try:
            logger.info(f"Retrieving candidates for query: {query[:50]}...")
            
            # Use hybrid search to get candidates
            results = self.hybrid_search.search(query, limit=top_k)
            
            # Ensure results have the expected structure
            candidates = []
            for result in results:
                candidate = {
                    "doc_id": result.get("doc_id", ""),
                    "chunk_id": result.get("chunk_id", ""),
                    "method": result.get("method", 0),
                    "page_from": result.get("page_from"),
                    "page_to": result.get("page_to"),
                    "hash": result.get("hash", ""),
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0)
                }
                candidates.append(candidate)
            
            logger.info(f"Retrieved {len(candidates)} candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Error retrieving candidates: {str(e)}")
            raise RuntimeError(f"Failed to retrieve candidates: {str(e)}")
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: User query string
            candidates: List of candidate chunks
            top_k: Maximum number of reranked results to return
            
        Returns:
            List of reranked chunks
        """
        try:
            logger.info(f"Reranking {len(candidates)} candidates")
            
            if not candidates:
                logger.warning("No candidates to rerank")
                return []
            
            # Use reranker service to rerank candidates
            reranked_results = self.reranker.rerank(query, candidates, top_r=top_k)
            
            # Ensure results maintain expected structure
            reranked_candidates = []
            for result in reranked_results:
                candidate = {
                    "doc_id": result.get("doc_id", ""),
                    "chunk_id": result.get("chunk_id", ""),
                    "method": result.get("method", 0),
                    "page_from": result.get("page_from"),
                    "page_to": result.get("page_to"),
                    "hash": result.get("hash", ""),
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0)
                }
                reranked_candidates.append(candidate)
            
            logger.info(f"Reranked to {len(reranked_candidates)} candidates")
            return reranked_candidates
            
        except Exception as e:
            logger.error(f"Error reranking candidates: {str(e)}")
            raise RuntimeError(f"Failed to rerank candidates: {str(e)}")
    
    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Build context string with bracketed indices and metadata
        
        Args:
            chunks: List of chunks to include in context
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            # Extract metadata
            doc_id = chunk.get("doc_id", "Unknown Document")
            page_from = chunk.get("page_from")
            page_to = chunk.get("page_to")
            text = chunk.get("text", "")
            
            # Build page info
            page_info = ""
            if page_from is not None and page_to is not None:
                if page_from == page_to:
                    page_info = f" (Page {page_from})"
                else:
                    page_info = f" (Page {page_from}-{page_to})"
            elif page_from is not None:
                page_info = f" (Page {page_from})"
            
            # Format chunk with bracketed index
            context_part = f"[{i}] Document: {doc_id}{page_info}\n{text}"
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for grounding instructions
        
        Returns:
            System prompt string
        """
        return (
            "You are a document QA assistant. You must answer strictly using the provided CONTEXT. "
            "Do not use any irrelevant external knowledge. If relevant matches are not found in the context, infer based on related sections or similar terms. "
            "If the answer cannot be found in the provided context, "
            "respond with \"I couldn't find relevant information in the provided documents.\""
        )
    
    def _create_user_message(self, query: str, context: str) -> str:
        """
        Create user message with context
        
        Args:
            query: User query
            context: Formatted context string
            
        Returns:
            User message string
        """
        return (
            f"Question: {query}\n\n"
            f"Context:\n{context}\n\n"
            "Please provide a comprehensive answer based only on the context above. "
            "Include citations using the bracketed numbers [1], [2], etc."
        )
    
    def synthesize_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Synthesize answer using DeepSeek client with context chunks
        
        Args:
            query: User query
            context_chunks: List of context chunks
            
        Returns:
            Synthesized answer string
        """
        try:
            logger.info(f"Synthesizing answer for query: {query[:50]}...")
            
            if not context_chunks:
                logger.warning("No context chunks provided for synthesis")
                return "I couldn't find relevant information in the provided documents."
            
            # Build context from chunks
            context = self._build_context(context_chunks)
            
            # Create messages for DeepSeek
            messages = [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": self._create_user_message(query, context)}
            ]
            
            # Call DeepSeek client
            answer = deepseek_chat(messages, temperature=0.65, max_tokens=700)
            
            logger.info("Answer synthesis completed successfully")
            return answer
            
        except (MissingAPIKeyError, InvalidAPIKeyError) as e:
            # Re-raise authentication errors - let caller handle with proper error codes
            logger.error(f"DeepSeek authentication error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error synthesizing answer: {str(e)}")
            raise RuntimeError(f"Failed to synthesize answer: {str(e)}")
    
    def save_turn(self) -> None:
        """
        Save conversation turn (no-op for MVP)
        """
        pass
    
    def load_history(self) -> None:
        """
        Load conversation history (no-op for MVP)
        """
        pass
