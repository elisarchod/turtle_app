"""Test API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage
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
        "messages": [HumanMessage(content="Test response")]
    }
    return mock_agent


def test_chat_success(client, mock_workflow_agent):
    """Test successful chat request."""
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        response = client.post("/chat", json={"message": "test"})
        
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "thread_id" in result


def test_chat_missing_message(client):
    """Test chat request without message parameter."""
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_chat_workflow_error(client):
    """Test chat request when workflow fails."""
    mock_agent = AsyncMock()
    mock_agent.ainvoke.side_effect = Exception("Workflow failed")
    
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_agent):
        response = client.post("/chat", json={"message": "test"})
        assert response.status_code == 500


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "healthy"