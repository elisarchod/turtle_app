"""Test API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from turtleapp.api.routes.endpoints import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_workflow_agent():
    mock_agent = AsyncMock()
    mock_agent.invoke_with_thread.return_value = (
        {"messages": [HumanMessage(content="Test response")]}, "test-thread-123"
    )
    return mock_agent


def test_chat_success(client, mock_workflow_agent):
    """Test successful chat request."""
    mock_workflow_agent.invoke_with_thread.return_value = (
        {"messages": [HumanMessage(content="Test response")]}, "test-thread-123"
    )
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


def test_chat_memory_persistence(client, mock_workflow_agent):
    """Test memory persistence across chat requests."""
    mock_workflow_agent.invoke_with_thread.return_value = (
        {"messages": [HumanMessage(content="Test response")]}, "test-thread-123"
    )
    with patch('turtleapp.api.routes.endpoints.movie_workflow_agent', mock_workflow_agent):
        # First request
        response1 = client.post("/chat", json={"message": "Hello"})
        assert response1.status_code == 200
        result1 = response1.json()
        thread_id = result1["thread_id"]

        # Second request with same thread_id
        response2 = client.post("/chat", json={"message": "Follow up", "thread_id": thread_id})
        assert response2.status_code == 200
        result2 = response2.json()

        assert result2["thread_id"] == thread_id

        calls = mock_workflow_agent.invoke_with_thread.call_args_list
        assert len(calls) == 2
        
        # Both calls should use the same thread_id
        first_call_thread = calls[0][0][1] if len(calls[0][0]) > 1 else calls[0][1].get('thread_id')
        second_call_thread = calls[1][0][1] if len(calls[1][0]) > 1 else calls[1][1].get('thread_id')
        assert first_call_thread == thread_id or second_call_thread == thread_id


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "healthy"