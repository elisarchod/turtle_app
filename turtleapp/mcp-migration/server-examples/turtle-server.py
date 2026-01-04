#!/usr/bin/env python3

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from turtleapp.src.core.tools.movie_summaries_retriever import movie_retriever_tool
from turtleapp.src.core.tools.torrent_tools import torrent_search_tool, torrent_download_tool
from turtleapp.src.core.tools.library_manager import library_manager_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("turtle-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="movie_search",
            description="Search the movie database using semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="torrent_search",
            description="Search for movie torrents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Movie title to search"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="torrent_status",
            description="Check download status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="library_scan",
            description="Scan local movie library",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "movie_search":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            result = movie_retriever_tool.invoke({"query": query, "max_results": max_results})
        elif name == "torrent_search":
            query = arguments.get("query", "")
            result = torrent_search_tool.invoke({"search_term": query})
        elif name == "torrent_status":
            result = torrent_download_tool.invoke({"query": ""})
        elif name == "library_scan":
            result = library_manager_tool.invoke({"tool_input": ""})
        else:
            result = f"Unknown tool: {name}"
            
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Tool error in {name}: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    logger.info("Starting Standard Turtle MCP Server")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())