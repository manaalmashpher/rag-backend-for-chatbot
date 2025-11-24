# Epic 12: Multi-turn Chat History Support

## Epic Overview

Implement persistent chat history to enable multi-turn conversations where the assistant remembers previous messages and can handle follow-up questions like "what would that require?" that reference earlier interactions. This epic adds database-backed session management while maintaining backward compatibility with existing single-turn flows.

## Business Value

- Enables natural conversational interactions with follow-up questions
- Improves user experience by maintaining context across multiple turns
- Reduces user frustration from having to repeat context in each message
- Enables more sophisticated query patterns that build on previous answers

## User Stories

- As a user, when I ask a follow-up question like "what would that require?" immediately after a previous answer, the system should use my earlier question and answer to interpret the new query.
- As a user, I can refresh the page and still see the previous messages for a given session id.
- As a user, I can start a "new conversation" which doesn't reuse old context.

## Acceptance Criteria

- [ ] Follow-up questions correctly use contextual chat history
- [ ] New sessions are created when session_id is missing
- [ ] Retrieval remains grounded in latest query
- [ ] Tests cover history retrieval and turn persistence
- [ ] System remains backward compatible (no session_id still works)
- [ ] Chat history is bounded (limited to last N messages or tokens)
- [ ] Frontend displays conversation history correctly
- [ ] "New Conversation" button clears history and starts fresh session

## Technical Requirements

### Database Models

- **ChatSession**: id (UUID/Integer), created_at, updated_at, optional user_id
- **ChatMessage**: id, session_id (FK), role (user/assistant), content, created_at

### ChatOrchestrator Updates

- Implement `load_history(session_id, limit=N)`: return last N messages ordered by creation time
- Implement `save_turn(session_id, user_message, assistant_message)`: persist both messages and update session timestamp
- Update chat flow to:
  1. Create new session if session_id missing
  2. Load history
  3. Build LLM input: system prompt + history + new user message + RAG context
  4. Call LLM
  5. Save the turn
  6. Return answer + session_id

### API Changes

- Make `conversation_id` optional in ChatRequest (rename to `session_id` for clarity)
- Return `session_id` in ChatResponse
- Backward compatible: absence of session_id creates new session

### Frontend Changes

- Maintain `session_id` in component state
- Store `session_id` in localStorage for persistence across page reloads
- Send `session_id` with each chat request
- Display conversation history in UI
- Add "New Conversation" button to clear history and reset session_id

## Dependencies

- Existing ChatOrchestrator (Epic 9)
- Existing chat API endpoint (Epic 9)
- Existing database infrastructure (Epic 6)
- Existing frontend chat UI (Epic 9)

## Definition of Done

- [ ] Database models created and migrated
- [ ] ChatOrchestrator.load_history() implemented and tested
- [ ] ChatOrchestrator.save_turn() implemented and tested
- [ ] Chat flow updated to use history
- [ ] API route updated to handle optional session_id
- [ ] Frontend updated to manage session_id and display history
- [ ] "New Conversation" button implemented
- [ ] Logging added for session creation, history loading, and turn saving
- [ ] Unit tests for models and ChatOrchestrator methods
- [ ] Integration tests for multi-turn conversation flow
- [ ] Backward compatibility verified
- [ ] No breaking changes to existing APIs

## Priority

High - Enhancement to existing MVP functionality that significantly improves user experience

## Estimated Effort

Medium (5-8 story points)

## Implementation Notes

**Files to Create:**

- `app/models/chat_history.py` - ChatSession and ChatMessage models
- `app/services/database_migration_chat_history.py` - Migration script for chat tables

**Files to Modify:**

- `app/services/chat_orchestrator.py` - Implement load_history and save_turn, update chat flow
- `app/schemas/chat.py` - Make conversation_id optional, add session_id to response
- `app/api/routes/chat.py` - Handle optional session_id, create sessions
- `src/components/ChatInterface.tsx` - Add session management and history display
- `src/services/api.ts` - Update types for optional session_id

**Key Design Decisions:**

- Use `session_id` terminology instead of `conversation_id` for clarity
- Limit history to last 10 messages to keep prompts manageable
- Retrieval still uses only the latest query (not history) to stay grounded
- Session creation happens automatically if session_id missing (backward compatible)
- History stored in chronological order (oldest first) for LLM context

**Testing Considerations:**

- Unit tests for ChatSession and ChatMessage creation
- Tests for load_history returning correct sequence
- Tests for save_turn persisting messages correctly
- Integration test: Q1 → get session_id → Q2 with session_id → verify history included
- Test backward compatibility (no session_id provided)
- Test "New Conversation" clears history

**Status:** 🚧 In Progress
