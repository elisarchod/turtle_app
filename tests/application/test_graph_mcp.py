"""Test full workflow with MCP integration (HTTP transport)."""

import pytest
from application.workflows.graph import create_movie_workflow
from infrastructure.mcp.client.tools import load_qbittorrent_tools


@pytest.mark.expensive
async def test_workflow_with_mcp_search():
    """Test full workflow handles MCP-based search over HTTP."""

    torrent_tools = await load_qbittorrent_tools()
    workflow = create_movie_workflow(torrent_tools=torrent_tools)

    result, thread_id = workflow.invoke(
        "Search for Ubuntu 22.04 and show me the results"
    )

    messages = result["messages"]
    assert len(messages) > 0

    final_response = messages[-1].content
    assert "ubuntu" in final_response.lower() or "search" in final_response.lower()


@pytest.mark.expensive
async def test_workflow_with_mcp_status():
    """Test workflow handles download status check via MCP HTTP."""

    torrent_tools = await load_qbittorrent_tools()
    workflow = create_movie_workflow(torrent_tools=torrent_tools)

    result, thread_id = workflow.invoke(
        "What's currently downloading?"
    )

    messages = result["messages"]
    final_response = messages[-1].content

    assert "download" in final_response.lower() or "no active" in final_response.lower()
