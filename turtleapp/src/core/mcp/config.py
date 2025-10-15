"""MCP server configuration for LangGraph native integration."""

from typing import Dict, Any
import os


def get_qbittorrent_mcp_config() -> Dict[str, Any]:
    """Get qBittorrent MCP server configuration for MultiServerMCPClient.

    Returns configuration for HTTP-based MCP server running in separate
    Docker container. LangGraph's MultiServerMCPClient handles the
    connection lifecycle and protocol via streamable_http transport.

    Returns:
        Dict compatible with MultiServerMCPClient format:
        {
            "server_name": {
                "url": "http://mcp-server:8000/mcp",
                "transport": "streamable_http",
                "headers": {...}  # optional
            }
        }
    """
    mcp_server_url = os.getenv(
        "TURTLEAPP_MCP_QBITTORRENT_URL",
        "http://mcp-qbittorrent:8000/mcp"  # Docker default
    )

    return {
        "qbittorrent": {
            "url": mcp_server_url,
            "transport": "streamable_http",
            # Optional: Add auth headers if MCP server requires them
            # "headers": {
            #     "Authorization": f"Bearer {os.getenv('MCP_API_KEY', '')}"
            # }
        }
    }
