# IonologyBot

Document Upload, Ingestion & Search Pipeline with Hybrid Retrieval

A complete document processing system that ingests user-uploaded documents, chunks them using configurable methods, generates embeddings, and provides hybrid search capabilities combining semantic and lexical retrieval.

## 🚀 Current Status

**Backend (Stories 1.1 & 2.1) - ✅ COMPLETE**

- Full document processing pipeline operational
- Hybrid search with semantic + lexical retrieval
- All 8 chunking methods implemented
- Performance targets met (<200ms p95 search latency)

**Frontend (Story 3.1) - 🚧 IN DEVELOPMENT**

- Web UI interface with basic setup and navigation
- Upload, status, and search interfaces planned
- Security considerations identified and documented

## 🏗️ Architecture

- **Backend**: FastAPI with SQLite + Qdrant vector database
- **Search**: Hybrid retrieval (semantic + lexical) with configurable weights
- **Chunking**: 8 predefined methods selectable at upload time
- **File Support**: PDF, DOCX, TXT, MD (up to 20MB, no OCR for scanned PDFs)
- **Language**: English-only for MVP

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Qdrant vector database

### Installation

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**

```bash
cp env.example .env
# Edit .env with your configuration
```

3. **Set up Qdrant vector database:**

```bash
# Start Qdrant (using Docker)
docker run -p 6333:6333 qdrant/qdrant
```

**Note**: SQLite database (`ionologybot.db`) will be created automatically on first run.

4. **Start the API:**

```bash
python run.py
```

The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

## 📡 API Endpoints

### Core Operations

- `POST /api/upload` - Upload documents with chunking method selection
- `GET /api/search?q={query}` - Hybrid search across all documents
- `GET /api/ingestions/{id}` - Get ingestion status and progress
- `GET /api/chunking-methods` - List available chunking methods

### System

- `GET /health` - Health check endpoint
- `GET /` - API status and information

### Document Management

- `DELETE /api/documents/{doc_id}` - Delete document and associated data

## 🔧 Features Implemented

### Document Processing

- **File Upload**: Support for PDF, DOCX, TXT, MD files (max 20MB)
- **File Validation**: Type checking, size limits, scanned PDF detection
- **Text Extraction**: Multi-format text extraction with structure preservation
- **Chunking Methods**: 8 predefined chunking strategies selectable at upload
- **Embedding Generation**: Sentence Transformers for semantic embeddings
- **Vector Storage**: Qdrant integration for efficient similarity search

### Search & Retrieval

- **Hybrid Search**: Combines semantic (vector) and lexical (BM25) search
- **Configurable Weights**: Default 0.6/0.4 semantic/lexical weighting
- **Ranked Results**: Fused scoring with relevance ranking
- **Rich Metadata**: Chunk-level attribution with page numbers and sources
- **Query Highlighting**: Snippet generation with search term highlighting

### System Features

- **Rate Limiting**: Configurable request rate limiting (default 5 QPS)
- **Error Handling**: Comprehensive error responses with detailed messages
- **Logging**: Structured logging for monitoring and debugging
- **CORS Support**: Cross-origin resource sharing for web frontend
- **Database Integration**: SQLite for metadata and lexical search
- **Async Processing**: Non-blocking document processing pipeline

## 🎯 Performance Targets

- **Search Latency**: <200ms p95 response time for hybrid queries
- **Upload Processing**: Real-time processing for documents up to 20MB
- **Concurrency**: Light concurrency support (single-digit users)
- **Throughput**: Optimized for small-scale deployment

## 🔒 Security Considerations

- **File Upload Security**: Type validation, size limits, content scanning
- **Input Sanitization**: XSS protection for user inputs
- **CORS Configuration**: Proper cross-origin request handling
- **Rate Limiting**: Protection against abuse and DoS attacks
- **API Key Security**: DeepSeek API keys are sanitized in logs and error messages

## 🔧 Troubleshooting

### DeepSeek API Authentication Issues

If you encounter errors related to DeepSeek API authentication, check the following:

**Error: `AUTH_ERROR` or `INVALID_API_KEY`**

- Verify your DeepSeek API key is correctly configured
- Check that `DEEPSEEK_API_KEY` environment variable is set, or `Settings.deepseek_api_key` is configured
- Ensure the API key is valid and not expired (get a new key from https://platform.deepseek.com/)
- Note: Settings.deepseek_api_key takes precedence over environment variable if both are set

**Error: Missing API Key**

- Configure `DEEPSEEK_API_KEY` in your `.env` file, or set `Settings.deepseek_api_key`
- The application will log a warning at startup if the key is missing (non-blocking)
- Check the `/readyz` health check endpoint to verify configuration status

**Common Error Codes:**

- `AUTH_ERROR`: API key is not configured
- `INVALID_API_KEY`: API key is invalid or authentication failed
- `CHAT_ERROR`: Generic chat processing error (may include authentication issues)

**Health Check:**

- Visit `GET /readyz` to check DeepSeek configuration status
- The `llm` component will show `"status": "configured"` or `"status": "not_configured"`
- Note: Health checks do NOT make actual API calls to avoid billing costs

## 📊 Chunking Methods

The system supports 8 predefined chunking methods:

1. **Fixed Size** - Uniform chunk sizes
2. **Sentence Boundary** - Split at sentence boundaries
3. **Paragraph Boundary** - Split at paragraph boundaries
4. **Semantic Chunking** - Content-aware splitting
5. **Sliding Window** - Overlapping chunks for context
6. **Hierarchical** - Multi-level document structure
7. **Topic-Based** - Topic-aware segmentation
8. **Custom Rules** - Configurable splitting rules

## 🧪 Testing

The project includes comprehensive testing:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end API testing
- **Performance Tests**: Load and latency testing
- **Security Tests**: Vulnerability and penetration testing

Run tests with:

```bash
pytest
```

## 📈 Monitoring & Observability

- **Health Checks**: System status monitoring
- **Structured Logging**: JSON-formatted logs for analysis
- **Search Analytics**: Query logging and performance metrics
- **Error Tracking**: Comprehensive error reporting and debugging

## 🚧 Upcoming Features (Story 3.1)

- **Web UI Interface**: Modern responsive frontend
- **Real-time Status**: Live ingestion progress updates
- **User Experience**: Intuitive upload and search interfaces
- **Accessibility**: WCAG compliance and keyboard navigation
- **Mobile Support**: Responsive design for all devices

## 📚 Documentation

- **Architecture**: `docs/architecture/` - System design and technical decisions
- **API Contracts**: `docs/architecture/10-api-contracts-examples.md` - Detailed API specifications
- **User Stories**: `docs/stories/` - Feature requirements and acceptance criteria
- **Quality Assurance**: `docs/qa/` - Testing strategies and risk assessments

## 🤝 Contributing

This project follows a structured development process with:

- Story-based development with clear acceptance criteria
- Quality gates with risk assessment and testing requirements
- Comprehensive documentation and architectural decision records

## 📄 License

[License information to be added]
