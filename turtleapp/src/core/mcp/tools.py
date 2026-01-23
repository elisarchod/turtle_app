"""MCP tools loader using LangGraph native MCP support (HTTP transport)."""

import asyncio
from typing import Optional, Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient

from turtleapp.settings import settings


def _get_qbittorrent_mcp_config() -> Dict[str, Any]:
    """Build MCP client config from settings.

    Returns configuration for HTTP-based MCP server running in separate
    Docker container. LangGraph's MultiServerMCPClient handles the
    connection lifecycle and protocol via streamable_http transport.
    """
    return {
        "qbittorrent": {
            "url": settings.mcp.qbittorrent_url,
            "transport": "streamable_http",
        }
    }


class MCPClientManager:
    """Manages MCP client lifecycle and connection."""

    def __init__(self):
        self._client: Optional[MultiServerMCPClient] = None
        self._initialized = False

    async def get_client(self) -> MultiServerMCPClient:
        """Get or create MCP client connection.

        Lazy initialization pattern - the client is only created and connected
        when first requested. The connection is reused for all subsequent calls.
        This is called when loading MCP tools at agent initialization.

        Returns:
            Connected MultiServerMCPClient instance ready for tool access
        """
        if not self._initialized:
            config = _get_qbittorrent_mcp_config()
            self._client = MultiServerMCPClient(config)
            await self._client.__aenter__()
            self._initialized = True

        return self._client

    async def cleanup(self):
        """Cleanup MCP client connection."""
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._initialized = False


# Module-level singleton
_manager = MCPClientManager()


def get_qbittorrent_tools():
    """Get all tools from qBittorrent MCP server.

    IMPORTANT: This function uses blocking asyncio.run() calls and should only
    be called during agent initialization, not in async contexts.

    Performs two synchronous async operations:
    1. Connects to the MCP server via HTTP transport (if not already connected)
    2. Loads all available tools from the server (search, download, status, etc.)

    The tools are loaded once and cached in the agent. Subsequent requests use
    the same tool instances without reconnecting.

    Returns:
        List of LangChain-compatible Tool objects from the qBittorrent MCP server.
        Typically includes 6 tools: search, add_torrent, pause, resume, delete, get_status.

    Network details:
        - Docker: http://turtle-mcp-qbittorrent:8000/mcp (container-to-container)
        - Local dev: http://localhost:9001/mcp (host machine)
    """
    client = asyncio.run(_manager.get_client())
    return asyncio.run(client.get_tools())


async def cleanup_mcp_client():
    """Cleanup MCP client connection on app shutdown."""
    await _manager.cleanup()
