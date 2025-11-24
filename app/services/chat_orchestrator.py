"""
Chat orchestrator service that handles retrieval, reranking, context building, and answer synthesis
"""

from typing import List, Dict, Any, Optional
import logging
import re
import uuid as uuid_lib
from sqlalchemy.orm import Session
from app.services.hybrid_search import HybridSearchService
from app.services.reranker import RerankerService
from app.deps.deepseek_client import deepseek_chat
from app.deps.exceptions import MissingAPIKeyError, InvalidAPIKeyError
from app.core.database import get_db
from app.models.chat_history import ChatSession, ChatMessage

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
    
    def _extract_section_id(self, text: str) -> Optional[str]:
        """
        Extract section ID pattern from text (e.g., 5.22.3)
        
        Args:
            text: Text to search for section ID pattern
            
        Returns:
            Section ID string (e.g., "5.22.3") or None if not found
        """
        # Use same regex as HybridSearchService: r'\d+(?:\.\d+)+'
        section_id_pattern = re.search(r'\d+(?:\.\d+)+', text)
        return section_id_pattern.group(0) if section_id_pattern else None
    
    def _is_ambiguous_followup(self, query: str) -> bool:
        """
        Detect if query is an ambiguous follow-up that needs section context
        
        Args:
            query: User query string
            
        Returns:
            True if query is short, contains pronouns, and lacks explicit section ID
        """
        query_lower = query.lower()
        
        # Check length (short queries more likely to be follow-ups)
        is_short = len(query) < 80  # Character threshold
        
        # Check for pronouns/phrases
        pronouns = ["this", "that", "it", "them", "those"]
        phrases = ["for this", "for that", "for it", "for these", "for those"]
        has_pronoun = any(pronoun in query_lower for pronoun in pronouns) or \
                      any(phrase in query_lower for phrase in phrases)
        
        # Check if explicit section ID is present
        has_section_id = self._extract_section_id(query) is not None
        
        # Ambiguous if: short AND has pronoun AND no explicit section ID
        return is_short and has_pronoun and not has_section_id
    
    def _get_last_section_id_from_history(self, history_messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Find the most recent section ID from chat history
        
        Args:
            history_messages: List of message dicts from load_history()
            
        Returns:
            Most recent section ID string or None if not found
        """
        # Iterate backwards (most recent first)
        for msg in reversed(history_messages):
            if msg.get("role") == "user":
                section_id = self._extract_section_id(msg.get("content", ""))
                if section_id:
                    return section_id
        return None
    
    def _build_retrieval_query(self, history_messages: List[Dict[str, str]], current_user_message: str) -> str:
        """
        Build effective retrieval query, augmenting ambiguous follow-ups with section context
        
        Args:
            history_messages: List of message dicts from load_history()
            current_user_message: Current user query string
            
        Returns:
            Query string for retrieval (may be augmented or unchanged)
        """
        # If current message has explicit section ID, use as-is
        if self._extract_section_id(current_user_message):
            return current_user_message
        
        # If not ambiguous follow-up, use as-is
        if not self._is_ambiguous_followup(current_user_message):
            return current_user_message
        
        # Ambiguous follow-up: try to get section ID from history
        last_section_id = self._get_last_section_id_from_history(history_messages)
        if last_section_id:
            # Augment query with section context
            augmented = f"For section {last_section_id}, {current_user_message}"
            logger.info(f"Augmented retrieval query with section {last_section_id}: {augmented}")
            return augmented
        
        # No section ID in history, use as-is
        return current_user_message
    
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
    
    def chat(self, query: str, context_chunks: List[Dict[str, Any]], session_id: Optional[str] = None) -> tuple[str, str]:
        """
        Complete chat flow with history support
        
        Args:
            query: User query string
            context_chunks: List of context chunks from retrieval
            session_id: Optional session UUID string
            
        Returns:
            Tuple of (answer, session_id)
        """
        # Get or create session
        session_uuid = self._get_or_create_session(session_id)
        
        # Load history
        history = self.load_history(session_uuid, limit=10)
        
        # Build messages with history
        messages = [{"role": "system", "content": self._create_system_prompt()}]
        
        # Add history messages
        messages.extend(history)
        
        # Build context from chunks
        context = self._build_context(context_chunks)
        
        # Add new user message with context
        messages.append({"role": "user", "content": self._create_user_message(query, context)})
        
        # Call LLM with full conversation
        try:
            answer = deepseek_chat(messages, temperature=0.65, max_tokens=700)
            logger.info(f"Generated answer for session {session_uuid}")
        except (MissingAPIKeyError, InvalidAPIKeyError) as e:
            logger.error(f"DeepSeek authentication error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in chat flow: {str(e)}")
            raise RuntimeError(f"Failed to generate answer: {str(e)}")
        
        # Save turn
        self.save_turn(session_uuid, query, answer)
        
        return answer, session_uuid
    
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
                
                # Extract section_id from query for better error messages
                section_id_pattern = re.search(r'\d+(?:\.\d+)+', query)
                section_id = section_id_pattern.group(0) if section_id_pattern else None
                
                if section_id is not None:
                    # Provide informative message for section-based queries
                    return f"I couldn't find any chunks mapped to section {section_id} in the uploaded documents. It may not exist in this version of the standard or hasn't been ingested yet."
                else:
                    # Generic message for non-section queries
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
    
    def load_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Load conversation history for a session
        
        Args:
            session_id: Session UUID string
            limit: Maximum number of messages to retrieve (default 10)
            
        Returns:
            List of message dicts with role and content: [{"role": "user", "content": "..."}, ...]
        """
        db = next(get_db())
        try:
            # Find session by UUID
            session = db.query(ChatSession).filter(ChatSession.uuid == session_id).first()
            
            if not session:
                logger.info(f"Session {session_id} not found, returning empty history")
                return []
            
            # Query messages ordered by created_at ascending (oldest first)
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
            
            # Convert to list of dicts
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            logger.info(f"Loaded {len(history)} messages from history for session {session_id}")
            return history
            
        except Exception as e:
            logger.error(f"Error loading history for session {session_id}: {str(e)}")
            raise RuntimeError(f"Failed to load history: {str(e)}")
        finally:
            db.close()
    
    def save_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        """
        Save conversation turn (user message and assistant response)
        
        Args:
            session_id: Session UUID string
            user_message: User's message content
            assistant_message: Assistant's response content
        """
        db = next(get_db())
        try:
            # Find session by UUID
            session = db.query(ChatSession).filter(ChatSession.uuid == session_id).first()
            
            if not session:
                logger.error(f"Session {session_id} not found, cannot save turn")
                raise ValueError(f"Session {session_id} not found")
            
            # Create user message
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=user_message
            )
            db.add(user_msg)
            
            # Create assistant message
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=assistant_message
            )
            db.add(assistant_msg)
            
            # Update session timestamp (SQLAlchemy will handle this via onupdate, but we trigger it)
            from datetime import datetime, timezone
            session.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.info(f"Saved turn for session {session_id} (user + assistant messages)")
            
        except ValueError:
            # Re-raise ValueError as-is (e.g., session not found)
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving turn for session {session_id}: {str(e)}")
            raise RuntimeError(f"Failed to save turn: {str(e)}")
        finally:
            db.close()
    
    def _get_or_create_session(self, conversation_id: Optional[str] = None) -> str:
        """
        Get existing session by UUID or create new session
        
        Args:
            conversation_id: Optional UUID string for existing session
            
        Returns:
            Session UUID string
        """
        db = next(get_db())
        try:
            if conversation_id:
                # Try to find existing session
                session = db.query(ChatSession).filter(ChatSession.uuid == conversation_id).first()
                if session:
                    logger.info(f"Found existing session: {conversation_id}")
                    return conversation_id
            
            # Create new session
            new_uuid = str(uuid_lib.uuid4())
            new_session = ChatSession(uuid=new_uuid)
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            
            logger.info(f"Created new chat session: {new_uuid}")
            return new_uuid
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error getting/creating session: {str(e)}")
            raise RuntimeError(f"Failed to get/create session: {str(e)}")
        finally:
            db.close()
