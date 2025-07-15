"""Test API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from turtleapp.api.routes.endpoints import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_workflow_agent():
    """Mock workflow agent."""
    mock_agent = AsyncMock()
    mock_agent.ainvoke.return_value = {
        "messages": [
            {"content": "Test response from workflow agent"}
        ]
    }
    return mock_agent


def test_chat_success(client, mock_workflow_agent):
    """Test successful chat request."""
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        response = client.post("/chat", json={
            "message": "tell me about terminator 2"
        })
        
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "thread_id" in result
        assert result["response"] == "Test response from workflow agent"


def test_chat_missing_message(client):
    """Test chat request without message parameter."""
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_chat_workflow_error(client):
    """Test chat request when workflow fails."""
    mock_agent = AsyncMock()
    mock_agent.ainvoke.side_effect = Exception("Workflow failed")
    
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_agent):
        response = client.post("/chat", json={"message": "test message"})
        assert response.status_code == 500


def test_chat_thread_id_generation(client, mock_workflow_agent):
    """Test that thread ID is generated for each request."""
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        response = client.post("/chat", json={"message": "test message"})
        
        assert response.status_code == 200
        result = response.json()
        assert "thread_id" in result
        
        # Check that ainvoke was called with a config containing thread_id
        call_args = mock_workflow_agent.ainvoke.call_args
        assert "config" in call_args[1]
        assert "configurable" in call_args[1]["config"]
        assert "thread_id" in call_args[1]["config"]["configurable"]


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "healthy"
    assert result["version"] == "1.0.0"
    assert "uptime" in result


def test_chat_with_thread_id(client, mock_workflow_agent):
    """Test chat endpoint with provided thread ID."""
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        response = client.post("/chat", json={
            "message": "Tell me about movies",
            "thread_id": "test-thread-123"
        })
        
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "thread_id" in result
        assert result["thread_id"] == "test-thread-123"