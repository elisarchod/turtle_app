"""MCP tools loader using LangGraph native MCP support (HTTP transport)."""

import asyncio
from typing import Optional
from langchain_mcp.client import MultiServerMCPClient

from turtleapp.src.core.mcp.config import get_qbittorrent_mcp_config


class MCPClientManager:
    """Manages MCP client lifecycle and connection."""

    def __init__(self):
        self._client: Optional[MultiServerMCPClient] = None
        self._initialized = False

    async def get_client(self) -> MultiServerMCPClient:
        """Get or create MCP client connection."""
        if not self._initialized:
            config = get_qbittorrent_mcp_config()
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
    """Get all tools from qBittorrent MCP server."""
    client = asyncio.run(_manager.get_client())
    return asyncio.run(client.get_tools())


async def cleanup_mcp_client():
    """Cleanup MCP client connection on app shutdown."""
    await _manager.cleanup()
