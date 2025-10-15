"""MCP server configuration for LangGraph native integration."""

from typing import Dict, Any
import os


def get_qbittorrent_mcp_config() -> Dict[str, Any]:
    mcp_server_url = os.getenv(
        "TURTLEAPP_MCP_QBITTORRENT_URL",
        "http://mcp-qbittorrent:8000/mcp"  # Docker default
    )

    return {
        "qbittorrent": {
            "url": mcp_server_url,
            "transport": "streamable_http",
        }
    }
