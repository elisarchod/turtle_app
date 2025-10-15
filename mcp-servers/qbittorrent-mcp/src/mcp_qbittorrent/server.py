"""FastMCP server for qBittorrent Web API."""

import logging
from fastmcp import FastMCP
from mcp_qbittorrent.config import settings
from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient
from mcp_qbittorrent.tools.qbittorrent_tools import register_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("qbittorrent-manager")

# Create global qBittorrent client instance
qb_client = QBittorrentClient(
    base_url=settings.qbittorrent_url,
    username=settings.qbittorrent_username,
    password=settings.qbittorrent_password,
    timeout=settings.request_timeout
)

# Register qBittorrent tools
register_tools(mcp, qb_client)

logger.info(f"qBittorrent MCP server initialized with URL: {settings.qbittorrent_url}")


if __name__ == "__main__":
    mcp.run()
