# Turtle App Tests

This directory contains the test suite for the turtle-app project, focused on essential functionality testing with pytest.

## Running Tests

### Using Poetry (Recommended)

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest turtleapp/tests/test_api_endpoints.py

# Run tests with coverage
poetry run pytest --cov=turtleapp

# Run tests in parallel
poetry run pytest -n auto

# Skip slow tests
poetry run pytest -m "not slow"
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest turtleapp/tests/test_torrent.py

# Run tests with coverage
pytest --cov=turtleapp --cov-report=html
```

## Test Structure

### Test Files

- `test_api_endpoints.py` - Tests for FastAPI endpoints (/health, /chat)
- `test_torrent.py` - Tests for torrent management functionality
- `test_retriever.py` - Tests for movie retriever and RAG evaluation
- `test_library_manager.py` - Tests for library scanning functionality

### Configuration

- `conftest.py` - Shared pytest fixtures and configuration
- `pytest.ini` - Pytest configuration settings (in pyproject.toml)

## Test Coverage

The test suite covers:

### API Layer
- **POST /chat endpoint**: Success, error handling, thread ID management
- **GET /health endpoint**: Health check functionality
- **Request validation**: Pydantic model validation
- **Error responses**: Structured error handling

### Core Tools
- **Library Manager**: SMB scanning, file detection, error handling
- **Movie Retriever**: Vector search, response formatting, RAG evaluation
- **Torrent Manager**: Download management, search functionality

### Workflow Integration
- **Async processing**: All agents use async-only processing
- **Error handling**: Standardized error handling decorators
- **Thread management**: Conversation persistence with MemorySaver

## Test Markers

The following pytest markers are available:

- `@pytest.mark.slow` - Slow-running tests (can be skipped with `-m "not slow"`)
- `@pytest.mark.asyncio` - Async tests (automatically handled by pytest-asyncio)

## Fixtures

### Shared Fixtures

- `client()` - FastAPI TestClient for API testing
- `mock_workflow_agent()` - Mock workflow agent with AsyncMock

### Test-Specific Fixtures

- `torrent_tool()` - Provides a TorrentClientTool instance
- `library_manager_tool()` - Provides a LibraryManagerTool instance
- `test_query()` - Provides test query data
- `retriever_response()` - Provides retriever agent response
- `mock_run()` - Provides mock run data for evaluation tests

## Testing Approach

### Simplified Architecture
- **Focused tests**: Essential functionality without over-engineering
- **Async testing**: Uses AsyncMock for async operations
- **JSON responses**: Tests structured API responses
- **Error scenarios**: Comprehensive error handling validation

### Mock Strategy
- **External services**: Mocked for consistent testing
- **AsyncMock usage**: Proper async mocking to avoid serialization issues
- **Realistic responses**: Mock responses match actual API behavior

## Writing New Tests

When adding new tests:

1. Use descriptive test function names starting with `test_`
2. Add docstrings to explain what each test does
3. Use fixtures for setup and teardown
4. Add appropriate markers for test categorization
5. Use meaningful assertions with clear error messages
6. Test both success and error scenarios

Example:

```python
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

def test_new_endpoint_success(client, mock_workflow_agent):
    """Test that the new endpoint works correctly."""
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        response = client.post("/new-endpoint", json={"data": "test"})
        
        assert response.status_code == 200
        result = response.json()
        assert "expected_field" in result
```

## Environment Setup

Tests automatically load environment variables from `.env` files. The test suite is designed to work with mocked external services, so most API keys are not required for testing.

## Recent Improvements

- **Simplified API**: Removed backward compatibility, focused on modern REST design
- **Async-only**: All agents converted to async-only processing
- **Standardized errors**: Consistent error handling with decorators
- **Clean docstrings**: Removed uninformative docstrings
- **Focused coverage**: Essential functionality testing without over-engineering

## Performance

- **Parallel execution**: Tests can run in parallel with `pytest -n auto`
- **Async support**: Proper async testing with pytest-asyncio
- **Fast mocking**: Efficient mocking strategy for external dependencies
- **Selective running**: Skip slow tests during development