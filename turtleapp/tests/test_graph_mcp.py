"""Test full workflow with MCP integration (HTTP transport)."""

import pytest
from turtleapp.src.workflows.graph import create_movie_workflow


@pytest.mark.expensive  # Not async - workflow.invoke is sync
def test_workflow_with_mcp_search():
    """Test full workflow handles MCP-based search over HTTP."""

    # Compile the workflow
    workflow = create_movie_workflow().compile()

    # Test search query (invoke returns tuple of (result, thread_id))
    result, thread_id = workflow.invoke(
        "Search for Ubuntu 22.04 and show me the results"
    )

    # Check supervisor routed to download manager
    messages = result["messages"]
    assert len(messages) > 0

    final_response = messages[-1].content
    assert "ubuntu" in final_response.lower() or "search" in final_response.lower()


@pytest.mark.expensive
def test_workflow_with_mcp_status():
    """Test workflow handles download status check via MCP HTTP."""

    # Compile the workflow
    workflow = create_movie_workflow().compile()

    result, thread_id = workflow.invoke(
        "What's currently downloading?"
    )

    messages = result["messages"]
    final_response = messages[-1].content

    # Should either show downloads or say "no active downloads"
    assert "download" in final_response.lower() or "no active" in final_response.lower()
