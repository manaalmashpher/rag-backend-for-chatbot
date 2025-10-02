# IonologyBot Test Suite

This directory contains comprehensive tests for the IonologyBot document upload and ingestion pipeline.

## Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── unit/                       # Unit tests for individual components
│   ├── test_chunking_service.py
│   ├── test_file_processor.py
│   └── test_scanned_pdf_detector.py
├── integration/                # Integration tests for API endpoints
│   └── test_upload_api.py
├── performance/                # Performance tests
│   └── test_ingestion_performance.py
├── utils/                      # Test utilities and mocks
│   └── mock_services.py
└── README.md                   # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Or run with pytest directly
pytest tests/ -v
```

### Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance tests (fast)
pytest tests/performance/ -v -m "not slow"

# Performance tests (including slow tests)
pytest tests/performance/ -v -m slow

# API tests only
pytest tests/ -v -m api

# Service tests only
pytest tests/ -v -m service
```

### Coverage Reports

```bash
# Generate coverage report
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

## Test Categories

### Unit Tests (`tests/unit/`)

- **Purpose**: Test individual components in isolation
- **Coverage**: All service classes and utility functions
- **Mocking**: Heavy use of mocks for external dependencies
- **Speed**: Fast execution (< 1 second per test)

### Integration Tests (`tests/integration/`)

- **Purpose**: Test API endpoints and component interactions
- **Coverage**: Full request/response cycles
- **Database**: Uses test database with transactions
- **Speed**: Medium execution (1-5 seconds per test)

### Performance Tests (`tests/performance/`)

- **Purpose**: Validate performance requirements
- **Coverage**: 200-300 pages in 20 minutes requirement
- **Markers**:
  - `@pytest.mark.performance` - All performance tests
  - `@pytest.mark.slow` - Tests that take > 1 minute
- **Speed**: Slow execution (1-20 minutes per test)

## Test Fixtures

### Database Fixtures

- `db_session`: Fresh database session for each test
- `client`: FastAPI test client with database override

### File Fixtures

- `temp_storage`: Temporary directory for file uploads
- `sample_pdf_content`: Mock PDF content for testing
- `sample_text_content`: Sample text for chunking tests

### Mock Fixtures

- `mock_openai_embeddings`: Mock OpenAI API responses
- `mock_qdrant_response`: Mock Qdrant search results

## Performance Requirements

The test suite validates these performance requirements:

1. **Chunking Performance**: All 8 chunking methods must complete within 5 minutes for 200-300 pages
2. **Full Pipeline**: Complete ingestion (chunking + embeddings + storage) within 20 minutes for 200-300 pages
3. **Memory Usage**: Memory increase < 500MB for 500-page documents
4. **Concurrent Processing**: 5 documents processed concurrently within 2 minutes

## Test Data

### Sample Documents

- **Small**: 1-5 pages for unit tests
- **Medium**: 50-100 pages for integration tests
- **Large**: 200-300 pages for performance tests
- **Very Large**: 500+ pages for stress tests

### File Formats

- PDF (text-based and scanned)
- DOCX
- TXT
- MD

## Mock Services

### OpenAI Mock (`MockOpenAIService`)

- Simulates embedding generation
- Configurable error conditions (rate limit, auth, connection)
- Deterministic responses for consistent testing

### Qdrant Mock (`MockQdrantService`)

- In-memory vector storage simulation
- Search and upsert operations
- Configurable connection errors

## Continuous Integration

### GitHub Actions (Recommended)

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Local Development

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_chunking_service.py -v

# Run tests matching pattern
pytest tests/ -k "test_chunking" -v
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root directory
2. **Database Errors**: Check that test database is properly configured
3. **Performance Test Failures**: Ensure sufficient system resources (RAM, CPU)
4. **Mock Failures**: Verify mock configurations match actual service interfaces

### Debug Mode

```bash
# Run with debug output
pytest tests/ -v -s --tb=long

# Run single test with debug
pytest tests/unit/test_chunking_service.py::TestChunkingService::test_chunking_method_1_fixed_size -v -s
```

### Test Environment Variables

```bash
# Set test environment
export TESTING=true
export DATABASE_URL=sqlite:///./test.db
export QDRANT_URL=http://localhost:6333
export OPENAI_API_KEY=test_key
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` files, `test_*` functions
2. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
3. **Add docstrings**: Explain what each test validates
4. **Use fixtures**: Leverage existing fixtures for consistency
5. **Mock external services**: Don't make real API calls in tests
6. **Test edge cases**: Include boundary conditions and error scenarios

## Coverage Goals

- **Unit Tests**: 90%+ coverage for service classes
- **Integration Tests**: 80%+ coverage for API endpoints
- **Overall**: 80%+ total code coverage

Current coverage can be viewed by running:

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```
