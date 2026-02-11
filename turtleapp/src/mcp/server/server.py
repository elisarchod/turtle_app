"""FastMCP server for qBittorrent Web API."""

import logging
from fastmcp import FastMCP
from turtleapp.src.mcp.server.config import settings
from turtleapp.src.mcp.server.clients.qbittorrent_client import QBittorrentClient
from turtleapp.src.mcp.server.tools.qbittorrent_tools import register_tools

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


def run_server():
    """Entry point for MCP server (used by uvicorn/fastmcp CLI)."""
    import subprocess
    import sys
    subprocess.run([
        sys.executable, "-m", "fastmcp", "run",
        "turtleapp.src.mcp.server.server:mcp",
        "--transport", "http"
    ])


if __name__ == "__main__":
    mcp.run()
