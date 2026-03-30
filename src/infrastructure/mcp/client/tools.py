"""MCP tools loader using LangGraph native MCP support (HTTP transport)."""

import asyncio
import logging
import warnings
from langchain_mcp_adapters.client import MultiServerMCPClient

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


def _get_qbittorrent_mcp_config() -> dict[str, dict[str, str]]:
    """Build MCP client config from settings."""
    return {
        "qbittorrent": {
            "url": settings.mcp.qbittorrent_url,
            "transport": "streamable_http",
        }
    }


class MCPClientManager:
    """Manages MCP client lifecycle and connection."""

    def __init__(self):
        self._client: MultiServerMCPClient | None = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def get_client(self) -> MultiServerMCPClient:
        """Get or create MCP client connection (thread-safe lazy init)."""
        async with self._lock:
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


async def load_qbittorrent_tools() -> list:
    """Load tools from qBittorrent MCP server, returning [] on failure."""
    try:
        client = await _manager.get_client()
        tools = await client.get_tools()
        logger.info(f"Loaded {len(tools)} qBittorrent MCP tools")
        return tools
    except Exception as exc:
        logger.warning(f"qBittorrent MCP server unavailable, torrent agent disabled: {exc}")
        return []


def get_qbittorrent_tools() -> list:
    """Deprecated: use load_qbittorrent_tools() (async) instead."""
    warnings.warn(
        "get_qbittorrent_tools() is deprecated; use 'await load_qbittorrent_tools()' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    loop = asyncio.get_event_loop()
    if loop.is_running():
        raise RuntimeError(
            "get_qbittorrent_tools() cannot be called from a running event loop. "
            "Use 'await load_qbittorrent_tools()' instead."
        )
    return loop.run_until_complete(_load_tools_sync())


async def _load_tools_sync() -> list:
    """Helper for the sync get_qbittorrent_tools() entry point."""
    client = await _manager.get_client()
    return await client.get_tools()


async def cleanup_mcp_client():
    """Cleanup MCP client connection on app shutdown."""
    await _manager.cleanup()
