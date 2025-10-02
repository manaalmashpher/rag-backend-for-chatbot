# Epic 2: Hybrid Search & Retrieval System

## Epic Overview

Implement a hybrid search system that combines semantic vector similarity with lexical keyword search to provide high-quality, ranked search results with source attributions.

## Business Value

- Delivers the core search capability that makes the RAG system valuable
- Provides balanced recall and precision through hybrid approach
- Enables users to find relevant information quickly and accurately

## User Stories

- As a user, I want to search my documents using natural language queries so I can find relevant information
- As a user, I want to see search results ranked by relevance so I can quickly find the most useful content
- As a user, I want to see source attributions and metadata so I can verify and cite the information
- As a user, I want search results to include both semantic and keyword matches so I get comprehensive results

## Acceptance Criteria

- [ ] Implement semantic vector search using Qdrant
- [ ] Implement lexical keyword search using SQLite FTS5
- [ ] Combine results using configurable fusion weights (0.6 semantic, 0.4 lexical)
- [ ] Return top 10 results with source metadata and snippets
- [ ] Achieve search latency targets (p95 ≤ 1.5s, p99 ≤ 3.0s)
- [ ] Support cosine similarity ranking for semantic search
- [ ] Include chunk method and page references in results
- [ ] Provide query embedding generation

## Technical Requirements

- Vector similarity search (Qdrant)
- Full-text search (SQLite FTS5 with full-text search indexing)
- Result fusion algorithm with configurable weights
- Query embedding generation
- Result ranking and scoring
- Metadata extraction and formatting

## Dependencies

- Qdrant vector database
- SQLite FTS5 configuration
- Embedding provider for query processing
- Document ingestion pipeline (Epic 1)

## Definition of Done

- [ ] Hybrid search returns semantically and lexically relevant results
- [ ] Performance targets are met consistently
- [ ] Results include proper source attributions
- [ ] Fusion algorithm works with configurable weights
- [ ] Search handles various query types effectively
- [ ] Error handling covers search failures

## Priority

High - Core MVP functionality

## Estimated Effort

Large (8-13 story points)

## Implementation Notes

**Current Implementation (Story 2.1):**

- Uses SQLite FTS5 for lexical search instead of Postgres FTS
- This choice was made for MVP simplicity and faster development
- SQLite FTS5 provides excellent full-text search capabilities for the current scale

**Future Considerations:**

- Migration to Postgres FTS may be considered for production scaling
- Current SQLite implementation is fully functional and meets all requirements
- No immediate migration needed for MVP success
