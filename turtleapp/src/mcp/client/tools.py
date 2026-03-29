"""MCP tools loader using LangGraph native MCP support (HTTP transport)."""

import asyncio
import logging
import warnings
from typing import Optional, Dict, Any, List
from langchain_mcp_adapters.client import MultiServerMCPClient

from turtleapp.settings import settings

logger = logging.getLogger(__name__)


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


async def load_qbittorrent_tools() -> List:
    """Load tools from qBittorrent MCP server, returning [] on failure."""
    try:
        client = await _manager.get_client()
        tools = await client.get_tools()
        logger.info(f"Loaded {len(tools)} qBittorrent MCP tools")
        return tools
    except Exception as exc:
        logger.warning(f"qBittorrent MCP server unavailable, torrent agent disabled: {exc}")
        return []


def get_qbittorrent_tools() -> List:
    """Deprecated: use load_qbittorrent_tools() (async) instead.

    Kept for backward compatibility. Blocks the event loop via asyncio.run().
    """
    warnings.warn(
        "get_qbittorrent_tools() is deprecated; use 'await load_qbittorrent_tools()' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    client = asyncio.run(_manager.get_client())
    return asyncio.run(client.get_tools())


async def cleanup_mcp_client():
    """Cleanup MCP client connection on app shutdown."""
    await _manager.cleanup()
