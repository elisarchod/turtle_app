# Turtle App Tests

This directory contains the test suite for the turtle-app project, focused on essential functionality testing with pytest.

## Running Tests

### Using Poetry (Recommended)

```bash
# Run with verbose output
poetry run pytest -v

```

```bash
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

- `pyproject.toml` - Pytest configuration settings and test dependencies

## Test Philosophy

The test suite focuses on **integration testing** - testing that components work together correctly. This approach is more valuable than pure unit tests for this application because:

- **Real user scenarios** - Users interact with APIs and tools, not isolated functions
- **External dependencies** - Most functionality involves external services (Pinecone, OpenAI, qBittorrent)
- **Error handling** - The system's key feature is graceful fallbacks when services fail
- **Simpler maintenance** - Less complex mocking, more realistic test scenarios

All tests are designed to:
- Work with or without external services (graceful fallbacks)
- Test actual user workflows
- Validate error handling and resilience
- Be simple and maintainable

## Test Coverage

The test suite covers:

### API Layer (`test_api_endpoints.py`)
- `test_chat_success()` - Chat endpoint with workflow agent integration
- `test_chat_missing_message()` - Input validation
- `test_chat_workflow_error()` - Error handling across API layers
- `test_health_endpoint()` - Health check endpoint

### Core Tools
- **Library Manager** (`test_library_manager.py`):
  - `test_interface()` - Tool interface validation
  - `test_tool_run()` - Tool execution with network share integration
- **Movie Retriever** (`test_retriever.py`):
  - `test_retriever_agent_response()` - Agent + tool + external service integration
  - `test_retriever_tool_interface()` - Tool interface validation
- **Torrent Manager** (`test_torrent.py`):
  - `test_list_torrents()` - Core function with mocked API
  - `test_tool_interface()` - Tool interface with graceful fallbacks
  - `test_error_handling()` - Service error handling validation

## Test Markers

- `@pytest.mark.asyncio` - Async tests (automatically handled by pytest-asyncio)

## Fixtures

### API Testing Fixtures (`test_api_endpoints.py`)
- `client()` - FastAPI TestClient for API testing
- `mock_workflow_agent()` - Mock workflow agent with AsyncMock

### Tool Testing Fixtures
- `torrent_tool()` - TorrentClientTool instance (`test_torrent.py`)
- `library_manager_tool()` - LibraryManagerTool instance (`test_library_manager.py`)
- `retriever_agent()` - ToolAgent with movie retriever (`test_retriever.py`)

## Testing Approach

### Integration-First Strategy
- **Real workflows**: Test actual user scenarios end-to-end
- **External service resilience**: Tests work with or without external services
- **Error scenarios**: Validate graceful fallbacks and error handling
- **Simple and maintainable**: Minimal mocking, focus on essential functionality

### Mock Strategy
- **Only when necessary**: Mock external APIs for consistent testing
- **AsyncMock for async operations**: Proper async mocking to avoid serialization issues
- **Realistic responses**: Mock responses match actual API behavior

## Writing New Tests

When adding new tests:

1. **Focus on user workflows** - Test how users actually interact with the system
2. **Test error handling** - Ensure graceful fallbacks work correctly
3. **Keep it simple** - Avoid overengineering with complex mocks
4. **Use descriptive names** - Clear test function names starting with `test_`
5. **Add brief docstrings** - Explain what the test validates
6. **Use fixtures** - Share setup code efficiently

Example:

```python
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

def test_chat_success(client, mock_workflow_agent):
    """Test successful chat endpoint interaction."""
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        response = client.post("/chat", json={"message": "test"})
        
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "thread_id" in result
```

## Environment Setup

Tests automatically load environment variables from `.env` files. The test suite is designed to work with mocked external services, so most API keys are not required for testing.

## Performance

- **Parallel execution**: Tests can run in parallel with `pytest -n auto`
- **Async support**: Proper async testing with pytest-asyncio
- **Fast execution**: Simple tests without complex setup
- **Resilient**: Work with or without external services

## Test Statistics

- **Total tests**: 11
- **Test files**: 4
- **Coverage**: Essential functionality focused on real user workflows
- **Execution time**: ~30-40 seconds (depends on external service availability)