"""
Pytest configuration and shared fixtures for turtle-app tests.
"""
import pytest
import os
from dotenv import load_dotenv

# Load environment variables for tests
load_dotenv(override=True)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment once for the entire test session."""
    # Ensure we're in a test environment
    os.environ.setdefault("TESTING", "true")
    
    # Set up any test-specific environment variables here
    # For example, you might want to use test API keys or mock services
    
    yield
    
    # Cleanup after all tests are done
    pass


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for each test."""
    # This fixture runs automatically for each test
    # You can add logging setup here if needed
    pass 