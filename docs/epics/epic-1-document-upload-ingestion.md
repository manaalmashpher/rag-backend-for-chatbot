# Epic 1: Document Upload & Ingestion Pipeline

## Epic Overview

Enable users to upload documents, select chunking methods, and process them through a complete ingestion pipeline that stores both vector embeddings and metadata.

## Business Value

- Provides the foundational capability for document processing and knowledge base creation
- Enables users to test different chunking strategies for optimal retrieval quality
- Establishes the core data pipeline for the RAG system

## User Stories

- As a user, I want to upload documents (PDF, DOCX, TXT, MD) so I can add them to my knowledge base
- As a user, I want to select a chunking method from a predefined list so I can optimize document processing
- As a user, I want to see the ingestion status so I know when my document is ready for searching
- As a user, I want to be notified if my document is a scanned PDF so I can provide a better version

## Acceptance Criteria

- [ ] Support file upload for PDF, DOCX, TXT, MD formats (max 20MB)
- [ ] Block scanned PDFs with clear error messaging
- [ ] Provide 8 predefined chunking methods for selection
- [ ] Implement text preprocessing and normalization
- [ ] Generate embeddings using configurable provider/model
- [ ] Store vectors in Qdrant with proper metadata
- [ ] Build and maintain lexical index for hybrid search
- [ ] Provide real-time ingestion status updates
- [ ] Support ingestion of 200-300 pages within 20 minutes

## Technical Requirements

- File validation and size limits
- Text extraction and preprocessing
- Chunking method implementation (8 methods)
- Embedding generation and storage
- Vector database integration (Qdrant)
- Lexical index creation (Postgres FTS)
- Status tracking and error handling

## Dependencies

- Qdrant vector database setup
- Postgres database for metadata
- Object storage for original files
- Embedding provider configuration

## Definition of Done

- [ ] All file types can be uploaded and processed
- [ ] All 8 chunking methods are implemented and selectable
- [ ] Vectors are stored in Qdrant with proper metadata
- [ ] Lexical index is created and maintained
- [ ] Ingestion status is tracked and visible to users
- [ ] Error handling covers all failure scenarios
- [ ] Performance targets are met (200-300 pages in 20 min)

## Priority

High - Core MVP functionality

## Estimated Effort

Large (8-13 story points)
