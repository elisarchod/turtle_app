# Turtle App Tests

This directory contains the test suite for the turtle-app project, converted to use pytest.

## Running Tests

### Using pytest directly

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_torrent.py

# Run tests with coverage
pytest --cov=turtleapp --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Using the test runner script

```bash
# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run specific test file
python run_tests.py turtleapp/tests/test_torrent.py

# Run with verbose output
python run_tests.py --verbose
```

## Test Structure

### Test Files

- `test_torrent.py` - Tests for torrent-related functionality
- `test_retriver.py` - Tests for movie retriever and RAG evaluation
- `test_library_manager.py` - Tests for library management tools

### Configuration

- `conftest.py` - Shared pytest fixtures and configuration
- `pytest.ini` - Pytest configuration settings

## Test Markers

The following pytest markers are available:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.slow` - Slow-running tests

## Fixtures

### Shared Fixtures (in conftest.py)

- `setup_test_environment()` - Sets up the test environment
- `setup_logging()` - Configures logging for tests

### Test-Specific Fixtures

- `torrent_tool()` - Provides a TorrentClientTool instance
- `library_manager_tool()` - Provides a LibraryManagerTool instance
- `test_query()` - Provides test query data
- `retriever_response()` - Provides retriever agent response
- `mock_run()` - Provides mock run data for evaluation tests

## Writing New Tests

When adding new tests:

1. Use descriptive test function names starting with `test_`
2. Add docstrings to explain what each test does
3. Use fixtures for setup and teardown
4. Add appropriate markers for test categorization
5. Use meaningful assertions with clear error messages

Example:

```python
import pytest

@pytest.mark.unit
def test_new_feature():
    """Test that the new feature works correctly."""
    # Arrange
    expected = "expected result"
    
    # Act
    result = some_function()
    
    # Assert
    assert result == expected, f"Expected {expected}, got {result}"
```

## Environment Setup

Tests automatically load environment variables from `.env` files. Make sure you have the necessary environment variables set up for your tests to run properly. 