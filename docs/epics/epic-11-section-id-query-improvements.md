# Epic 11: Section-ID Query Reliability Improvements

## Epic Overview

Improve the reliability and accuracy of section-ID queries (e.g., "what's expected in section 5.22.3") by implementing a section-ID-first retrieval path, expanding synonym coverage for domain terms, and adding graceful fallback mechanisms. This ensures users can reliably retrieve specific clauses by section ID and receive helpful responses even when exact matches aren't found.

## Business Value

- Improves user experience by reliably returning requested sections
- Reduces frustration when users query specific section IDs
- Enhances search quality through better synonym matching
- Provides graceful fallback when exact sections aren't found
- Enables direct section navigation without semantic search overhead

## User Stories

- As a user, I want to query specific section IDs (e.g., "section 5.22.3") and reliably get the corresponding clause, so I can quickly find the information I need
- As a user, I want queries using synonyms (e.g., "requirements" vs "expected") to match correctly, so I don't have to use exact terminology
- As a user, I want helpful error messages when a section ID doesn't exist, so I understand why no results were found
- As a user, I want to use "go to section" commands for direct navigation, so I can quickly access specific sections without semantic search

## Acceptance Criteria

- [ ] Section-ID queries like "what's expected in section 5.22.3" reliably return the corresponding clause
- [ ] Direct database lookup path activates when section IDs are detected in queries
- [ ] Parent section fallback works when exact section ID not found (e.g., 5.22.3 → 5.22)
- [ ] Synonym expansion covers domain terms (requirements, expected, compliance, evidence, indicators)
- [ ] SQLite LIKE search uses term-based matching instead of full query LIKE
- [ ] PostgreSQL search uses synonym variants effectively
- [ ] ChatOrchestrator provides informative error messages for section-ID queries
- [ ] Explicit "go to section" feature works for direct navigation queries
- [ ] All changes maintain backwards compatibility with existing queries
- [ ] Performance is maintained or improved (section-ID lookups are faster than hybrid search)

## Technical Requirements

- Section-ID detection using regex pattern `\d+(?:\.\d+)+`
- Direct database queries using SQLAlchemy ORM with Chunk/Document models
- Parent section fallback logic (strip last segment from section ID)
- Expanded synonym mapping for domain terms
- Term-based SQLite LIKE search with stopword filtering
- Synonym variant processing in PostgreSQL full-text search
- Section-ID detection in ChatOrchestrator error handling
- Explicit section pattern matching in search API route

## Dependencies

- Existing HybridSearchService (Epic 2)
- Existing LexicalSearchService (Epic 2)
- Existing ChatOrchestrator (Epic 9)
- Existing search API endpoint (Epic 5)
- Chunk model with section_id and section_id_alias fields (Epic 6)

## Definition of Done

- [ ] Section-ID-first retrieval path implemented in HybridSearchService
- [ ] Parent section fallback implemented and tested
- [ ] Synonym coverage expanded for domain terms
- [ ] SQLite LIKE search improved with term-based matching
- [ ] ChatOrchestrator error messages enhanced
- [ ] Explicit "go to section" feature implemented in search API
- [ ] All existing functionality regression tested
- [ ] Logging added at INFO level for traceability
- [ ] No breaking changes to existing APIs
- [ ] Documentation updated appropriately

## Priority

Medium - Enhancement to existing MVP functionality

## Estimated Effort

Medium (5-8 story points)

## Implementation Notes

**Files Modified:**

- `app/services/hybrid_search.py` - Added section-ID-first retrieval and parent fallback
- `app/services/lexical_search.py` - Expanded synonyms, improved SQLite LIKE search
- `app/services/chat_orchestrator.py` - Enhanced error messages for section IDs
- `app/api/routes/search.py` - Added explicit "go to section" feature

**Key Design Decisions:**

- Section-ID detection happens early in HybridSearchService.search() before vector/lexical search
- Direct DB lookups use existing Chunk model with section_id/section_id_alias fields
- Synonym expansion processes all matched terms, not just first match
- Term-based SQLite search extracts meaningful terms (excludes stopwords like "what", "in", "the")
- Parent fallback only activates if section ID contains at least one dot
- All changes are additive - existing hybrid search path remains intact as fallback

**Testing Considerations:**

- Unit tests should verify section-ID direct lookup returns correct chunks
- Tests should verify parent fallback when exact section missing
- Tests should verify synonym expansion works for domain terms
- Tests should verify term-based SQLite search matches correctly
- Integration tests should verify end-to-end section-ID query flow
- Regression tests should verify existing queries still work

**Status:** ✅ Completed (2025-11-24)
