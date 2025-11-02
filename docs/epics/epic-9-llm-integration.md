# Epic 9: DeepSeek Chat Integration - MVP Implementation

## ⚠️ ACTIVE IMPLEMENTATION

**Status:** ACTIVE as of 2025-10-28
**Rationale:** Adding minimal chat interface powered by DeepSeek (OpenAI-compatible API) on top of existing RAG stack to provide conversational search functionality.

**Impact:** Users will receive synthesized answers from retrieved chunks instead of raw search results, enabling natural language interaction with the document corpus.

## Epic Goal

Integrate DeepSeek chat functionality into the existing RAG system to transform the current search page into a conversational chat interface that synthesizes answers strictly from retrieved document chunks.

## Epic Description

**Existing System Context:**

- **Current relevant functionality**: Hybrid search system that retrieves and ranks relevant document chunks using semantic vector similarity + lexical keyword matching
- **Technology stack**: Python, FastAPI, uvicorn backend; Vite + React (TypeScript) frontend; Qdrant vector database, Postgres with FTS, cross-encoder reranker
- **Integration points**: Existing hybrid search service, reranker service, search results UI components

**Enhancement Details:**

- **What's being added**: DeepSeek chat integration with OpenAI-compatible API client, chat orchestrator service, and minimal React chat UI
- **How it integrates**: Converts search flow to chat flow: User Question → Hybrid Search → Rerank → Context Building → DeepSeek Chat → Synthesized Answer
- **Success criteria**: Users interact through conversational chat interface that provides grounded answers from document chunks with proper citations

## Stories

1. **Story 9.1: DeepSeek Client Integration** - Create OpenAI-compatible DeepSeek client with environment configuration
2. **Story 9.2: Chat Orchestrator Service** - Implement chat orchestrator that handles retrieval, reranking, context building, and answer synthesis
3. **Story 9.3: Chat API Endpoint** - Create POST /api/chat endpoint for chat interactions
4. **Story 9.4: DeepSeek API Authentication** - Verify and enhance DeepSeek API Bearer token authentication
5. **Story 9.5: React Chat UI** - Convert search page to minimal chat interface with conversation history and citations

## Implementation Requirements

**Backend Components:**

- [ ] DeepSeek client (`app/deps/deepseek_client.py`) with OpenAI-compatible interface
- [ ] Chat orchestrator service (`app/services/chat_orchestrator.py`) with retrieval, reranking, and synthesis
- [ ] Chat API route (`app/api/routes_chat.py`) with POST /api/chat endpoint
- [ ] Environment configuration for DEEPSEEK_API_KEY

**Frontend Components:**

- [ ] React chat UI (convert existing search page or create new Chat.tsx)
- [ ] Message state management with conversation history
- [ ] Citations side panel for displaying source information
- [ ] Input box and send functionality

**Integration Requirements:**

- [ ] No user authentication required for `/api/chat` (MVP scope - public endpoint)
- [ ] DeepSeek API authentication via Bearer token using `DEEPSEEK_API_KEY` environment variable
- [ ] No streaming (simple request/response)
- [ ] No tools or external calls (strict grounding to context)
- [ ] Temperature set to 0.1 for consistent responses
- [ ] Max tokens limited to 700 for concise answers

## Risk Mitigation

- **Primary Risk**: DeepSeek API availability and response quality
- **Mitigation**: Strict grounding to provided context, fallback message when no relevant chunks found
- **Rollback Plan**: Can disable chat endpoint and revert to original search functionality

## Definition of Done

- [ ] DeepSeek client implemented with OpenAI-compatible interface
- [ ] Chat orchestrator service handles retrieval, reranking, and synthesis
- [ ] POST /api/chat endpoint returns proper JSON response with answer and citations
- [ ] React chat UI displays conversation history and citations
- [ ] Environment variable `DEEPSEEK_API_KEY` configured with valid DeepSeek API key
- [ ] DeepSeek API authentication working via Bearer token (handled automatically by OpenAI client)
- [ ] Smoke tests pass: in-scope questions return grounded answers, out-of-scope questions return "couldn't find" response
- [ ] No user authentication required for `/api/chat` endpoint (MVP scope)
- [ ] All answers strictly grounded to provided context chunks

## Technical Implementation Details

**DeepSeek Client (`app/deps/deepseek_client.py`):**

- OpenAI-compatible client with base_url: `https://api.deepseek.com/v1`
- Model: `deepseek-chat`
- Function: `deepseek_chat(messages, temperature=0.1, max_tokens=700)`
- Environment variable: `DEEPSEEK_API_KEY`

**Chat Orchestrator (`app/services/chat_orchestrator.py`):**

- `retrieve_candidates(query: str, top_k: int = 20)` → list of candidate chunks
- `rerank(query: str, candidates: list, top_k: int = 8)` → reranked chunks
- `save_turn()` and `load_history()` (no-ops if no persistence)
- Context building with bracketed indices and metadata
- System prompt: "You are a document QA assistant. You must answer strictly using the provided CONTEXT."
- User message wrapper with explicit grounding instructions

**API Endpoint (`app/api/routes_chat.py`):**

- POST /api/chat
- Request: `{ "conversation_id": string, "message": string }`
- Response: `{ "answer": string, "citations": array }`

**Frontend Chat UI:**

- Message state: `{ role: "user" | "assistant", content: string }`
- Stable conversation_id (UUID generated on mount)
- Citations side panel with rank, doc_id, chunk_id, score, source, page info

## Dependencies

- Existing hybrid search service (no changes required)
- Existing reranker service (no changes required)
- DeepSeek API access and DEEPSEEK_API_KEY configuration
- OpenAI-compatible Python client library
- React frontend with existing styling framework

## Success Metrics

- **Functionality**: POST /api/chat returns valid JSON with answer and citations
- **Grounding**: Answers reference only provided context chunks
- **Fallback**: Out-of-scope questions return "couldn't find" response
- **UI**: Chat interface displays conversation history and citations properly
- **Integration**: No breaking changes to existing search functionality
