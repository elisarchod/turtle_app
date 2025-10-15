# Turtle App MCP Integration Plan

## Executive Summary

This plan migrates Turtle App to leverage **LangGraph's native MCP support** via the `langchain-mcp-adapters` package, replacing direct qBittorrent HTTP calls with a clean MCP-based architecture. The migration **completely removes** legacy torrent code and uses MCP tools directly through LangGraph's `MultiServerMCPClient`.

### Key Features
- ✅ **LangGraph native MCP support** - Uses official `MultiServerMCPClient` from `langchain-mcp-adapters`
- ✅ **HTTP/Network transport** - MCP server runs as separate Docker container via `streamable_http` transport
- ✅ **Direct tool binding** - MCP tools automatically converted to LangChain tools via `.get_tools()`
- ✅ **Clean architecture** - Complete removal of legacy qBittorrent HTTP code
- ✅ **Better performance** - Persistent HTTP connections managed by LangGraph
- ✅ **Less maintenance** - Leverage battle-tested LangGraph MCP client
- ✅ **LLM abstraction** - LLM never sees "qBittorrent" or "torrent" in prompts, only generic "movie download" concepts
- ✅ **Container isolation** - MCP server and main app in separate Docker containers for better scalability

---

## Architecture Overview

### Current (Monolithic)
```
User → FastAPI → LangGraph Supervisor
                       ↓
              Torrent Agent (torrent_tools.py)
                       ↓
              Direct qBittorrent HTTP calls
```

### Target (MCP-Native with HTTP Transport)
```
Docker Container 1: Turtle App
┌────────────────────────────────────┐
│ User → FastAPI → LangGraph         │
│                     ↓               │
│   "Download Manager Agent"         │
│                     ↓               │
│   MCP Tools (LangChain wrappers)   │
│                     ↓               │
│   MultiServerMCPClient (HTTP)      │
└────────────────────────────────────┘
                ↓ streamable_http
Docker Container 2: MCP Server
┌────────────────────────────────────┐
│   FastMCP Server                   │
│   (HTTP endpoint: /mcp)            │
│                     ↓               │
│   qBittorrent MCP Tools            │
│                     ↓               │
│   qBittorrent Web API              │
└────────────────────────────────────┘
                ↓ HTTP
Docker Container 3: qBittorrent
┌────────────────────────────────────┐
│   qBittorrent WebUI                │
│   (Port 15080)                     │
└────────────────────────────────────┘
```

---

## Architecture Considerations

### Transport Options: stdio vs HTTP

The MCP protocol supports multiple transport mechanisms. This plan uses **HTTP transport** for Docker deployments, but other options exist:

#### Option 1: HTTP Transport (streamable_http) - **CHOSEN**

**Configuration:**
```python
{
    "qbittorrent": {
        "url": "http://mcp-qbittorrent:8000/mcp",
        "transport": "streamable_http"
    }
}
```

**Pros:**
- ✅ Works across Docker container boundaries
- ✅ Standard HTTP protocol - easier debugging with curl/Postman
- ✅ Can add authentication headers (Bearer tokens, API keys)
- ✅ Load balancing and horizontal scaling possible
- ✅ MCP server can serve multiple clients simultaneously
- ✅ Can expose MCP server to external consumers (other apps, CLI tools)

**Cons:**
- ❌ Slightly higher latency than stdio (network overhead)
- ❌ Requires network configuration in Docker Compose
- ❌ More moving parts (HTTP server, network stack)

**When to use:**
- Separate Docker containers (production deployments)
- Microservices architecture
- Need to share MCP server across multiple apps
- Cloud deployments (Kubernetes, ECS, etc.)

---

#### Option 2: stdio Transport (subprocess)

**Configuration:**
```python
{
    "qbittorrent": {
        "command": "uv",
        "args": ["run", "mcp-qbittorrent"],
        "transport": "stdio"
    }
}
```

**Pros:**
- ✅ Lower latency (direct process communication)
- ✅ Simpler configuration (no network setup)
- ✅ Automatic lifecycle management (subprocess started/stopped with app)
- ✅ No HTTP server overhead

**Cons:**
- ❌ Cannot work across Docker container boundaries
- ❌ Requires both apps in same container or same filesystem
- ❌ MCP server coupled to main app lifecycle
- ❌ Cannot share MCP server across multiple clients

**When to use:**
- Single-container deployments
- Local development
- CLI tools
- Desktop applications

---

#### Option 3: SSE Transport (Server-Sent Events)

**Configuration:**
```python
{
    "qbittorrent": {
        "url": "http://mcp-qbittorrent:8000/sse",
        "transport": "sse"
    }
}
```

**Pros:**
- ✅ Works across containers like HTTP
- ✅ Supports streaming responses
- ✅ Better for real-time updates

**Cons:**
- ❌ Less common than HTTP (fewer tools support it)
- ❌ Similar overhead to HTTP
- ❌ Not all MCP servers support SSE

**When to use:**
- Need real-time streaming updates from MCP server
- Long-running operations with progress updates

---

### Deployment Topology Alternatives

#### Alternative A: Single Container (stdio transport)

If you want to simplify deployment at the cost of modularity:

```
Docker Container: Turtle App + MCP Server
┌────────────────────────────────────────┐
│  FastAPI + LangGraph                   │
│        ↓ stdio                          │
│  MCP Server (subprocess)                │
│        ↓ HTTP                           │
│  qBittorrent (separate container)      │
└────────────────────────────────────────┘
```

**Trade-offs:**
- ✅ Simpler Docker setup (one less container)
- ✅ Lower latency (stdio is faster than HTTP)
- ✅ Fewer network dependencies
- ❌ MCP server cannot be shared/reused
- ❌ Harder to scale MCP server independently
- ❌ Tighter coupling between app and MCP server

**Implementation changes:**
- Use `stdio` transport in Phase 2.2
- No separate MCP container in docker-compose
- MCP server packaged inside main app container

---

#### Alternative B: Separate HTTP Container (streamable_http transport) - **CHOSEN**

The plan as written uses this approach.

**Trade-offs:**
- ✅ Maximum modularity and reusability
- ✅ Can scale MCP server independently
- ✅ Clear separation of concerns
- ✅ MCP server can serve multiple clients
- ❌ More complex Docker setup
- ❌ Slightly higher latency (network hop)
- ❌ More containers to manage

---

#### Alternative C: Sidecar Pattern

Run MCP server as a sidecar container in the same pod (Kubernetes):

```
Pod:
┌─────────────────────────────────────┐
│  Container 1: Turtle App            │
│       ↓ localhost:8000               │
│  Container 2: MCP Server (sidecar)  │
└─────────────────────────────────────┘
```

**Trade-offs:**
- ✅ Low latency (localhost communication)
- ✅ MCP server lifecycle tied to app
- ✅ Simplifies network security (no external exposure)
- ❌ Only works in Kubernetes
- ❌ Cannot share MCP server across pods

---

### MCP Server Implementation: FastMCP vs Custom

#### FastMCP (Recommended for this project)

```python
from fastmcp import FastMCP

mcp = FastMCP("qbittorrent-server")

@mcp.tool()
async def qb_search_torrents(query: str, limit: int = 10):
    """Search for torrents."""
    # implementation
```

**Pros:**
- ✅ Quick development - minimal boilerplate
- ✅ Automatic HTTP server setup
- ✅ Built-in validation and error handling
- ✅ Supports both stdio and HTTP transports

**Cons:**
- ❌ Less control over HTTP layer
- ❌ Opinionated framework choices

---

#### Custom MCP Server (Official SDK)

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("qbittorrent-server")

@server.list_tools()
async def list_tools():
    return [...]
```

**Pros:**
- ✅ Maximum flexibility
- ✅ Official SDK - guaranteed compatibility
- ✅ More control over protocol details

**Cons:**
- ❌ More boilerplate code
- ❌ Slower development
- ❌ Need to implement HTTP layer manually

**Recommendation:** Use FastMCP for this project. The existing `mcp-qbittorrent` server already uses FastMCP, and it's sufficient for our needs.

---

### LLM Abstraction Strategy

**Key Principle**: The LLM should reason about **user intent** (searching for movies, checking downloads), not **implementation details** (qBittorrent, torrents, magnet links).

**Abstraction Layers:**

1. **Agent Prompt Level** (User-Facing)
   - Agent name: "Download Manager Agent" or "Movie Acquisition Agent"
   - Concepts: "search for movies", "check download status", "manage downloads"
   - ❌ Never mention: "qBittorrent", "torrent", "magnet link", "seeders/leechers"

2. **MCP Tool Level** (Technical Interface)
   - Tool names: `qb_search_torrents`, `qb_list_torrents`, `qb_add_torrent`, `qb_control_torrent`
   - Tool descriptions: Written for LLMs, using natural language
   - The LLM sees these tool names but understands them from descriptions, not implementation

3. **MCP Server Level** (Implementation)
   - Actual qBittorrent API calls
   - HTTP protocol, authentication, error handling
   - Completely hidden from LLM

**Result**: LLM uses tools naturally based on descriptions, without knowing it's using qBittorrent under the hood. This allows swapping implementations (e.g., to Transmission, Deluge) without retraining or changing prompts.

---

## Migration Strategy

### Phase 0: Prerequisites & Setup

**Duration: 1 hour**

#### 0.1 Verify LangGraph Version & Install MCP Adapters

```bash
cd /home/pie/git/turtle_app

# Check LangGraph version
poetry show langgraph | grep "version"
# Must be >= 0.2.34 for native MCP support

# Install langchain-mcp-adapters (NEW)
poetry add langchain-mcp-adapters
```

If LangGraph upgrade needed:
```bash
poetry add langgraph@latest
```

#### 0.2 Copy MCP Server to Monorepo

```bash
# Create packages structure
mkdir -p packages/qbittorrent-mcp

# Copy MCP server
cp -r /home/pie/git/mcp-qbittorrent/* packages/qbittorrent-mcp/

# Update package name in pyproject.toml
cd packages/qbittorrent-mcp
# Change: name = "mcp-qbittorrent"
# To:     name = "turtleapp-qbittorrent-mcp"
```

#### 0.3 Create Feature Branch

```bash
git checkout -b feat/mcp-http-integration
```

---

### Phase 1: MCP Server HTTP Setup

**Duration: 2-3 hours**

#### 1.1 Update MCP Server for HTTP Transport

**File: `packages/qbittorrent-mcp/src/mcp_qbittorrent/server.py`**

Ensure FastMCP server is configured for HTTP:

```python
"""MCP server for qBittorrent integration with HTTP transport."""

from fastmcp import FastMCP
from mcp_qbittorrent.tools.qbittorrent_tools import (
    qb_list_torrents,
    qb_search_torrents,
    qb_add_torrent,
    qb_control_torrent,
    qb_torrent_info,
    qb_get_preferences
)

# Initialize FastMCP server
mcp = FastMCP("qbittorrent-server")

# Register tools (already decorated with @mcp.tool())
# Tools are automatically registered when imported

# HTTP server will be started by FastMCP CLI
if __name__ == "__main__":
    # This allows running as: python -m mcp_qbittorrent.server
    mcp.run()
```

**Verify HTTP endpoint:**
```bash
cd packages/qbittorrent-mcp

# Start HTTP server
uv run fastmcp run mcp_qbittorrent.server:mcp --transport http --port 8000

# Test in another terminal
curl http://localhost:8000/mcp/tools
```

#### 1.2 Update MCP Server Configuration

**File: `packages/qbittorrent-mcp/src/mcp_qbittorrent/config.py`**

Changes:
- Update env prefix from `QB_MCP_` to `TURTLEAPP_QB_`
- Add turtle app specific logging

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    qbittorrent_url: str
    qbittorrent_username: str
    qbittorrent_password: str
    request_timeout: int = 30
    log_level: str = "INFO"

    class Config:
        env_prefix = "TURTLEAPP_QB_"  # Changed from QB_MCP_
```

#### 1.3 Create Dockerfile for MCP Server

**File: `packages/qbittorrent-mcp/Dockerfile`** (NEW)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy MCP server code
COPY pyproject.toml .
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen

# Expose HTTP port
EXPOSE 8000

# Run FastMCP server with HTTP transport
CMD ["uv", "run", "fastmcp", "run", "mcp_qbittorrent.server:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.4 Test MCP Server Standalone

```bash
cd packages/qbittorrent-mcp

# Set environment variables
export TURTLEAPP_QB_QBITTORRENT_URL=http://localhost:15080
export TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
export TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin

# Run HTTP server
uv run fastmcp run mcp_qbittorrent.server:mcp --transport http

# In another terminal, test tools endpoint
curl http://localhost:8000/mcp/tools | jq
```

---

### Phase 2: LangGraph Native MCP Integration (HTTP-Based)

**Duration: 3-4 hours**

This is the core migration - replacing custom tools with MCP-native tools over HTTP.

#### 2.1 Install Dependencies

Ensure `langchain-mcp-adapters` is installed:

```bash
poetry add langchain-mcp-adapters
```

#### 2.2 Create MCP Configuration Module

**File: `turtleapp/src/core/mcp/config.py`** (NEW)

```python
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
```

**Rationale**:
- Centralized config makes it easy to add more MCP servers later (Plex, Sonarr, etc.)
- Uses `streamable_http` transport (LangGraph's recommended transport for HTTP)
- Configuration matches `MultiServerMCPClient` API exactly

---

#### 2.3 Create MCP Tools Loader

**File: `turtleapp/src/core/mcp/tools.py`** (NEW)

This is the **ONLY** integration code needed - LangGraph does the rest!

```python
"""MCP tools loader using LangGraph native MCP support (HTTP transport)."""

import asyncio
from typing import List
from langchain_core.tools import BaseTool
from langchain_mcp.client import MultiServerMCPClient

from turtleapp.src.core.mcp.config import get_qbittorrent_mcp_config


# Cache for MCP client and tools (loaded once at startup)
_mcp_client: MultiServerMCPClient = None
_mcp_tools_cache: List[BaseTool] = None


async def _initialize_mcp_client() -> MultiServerMCPClient:
    """Initialize MCP client connection to remote HTTP servers.

    Uses LangGraph's MultiServerMCPClient to:
    1. Connect to remote MCP server via HTTP (streamable_http transport)
    2. Handle connection lifecycle and retries
    3. Manage protocol communication over HTTP

    Returns:
        Initialized MultiServerMCPClient instance
    """
    config = get_qbittorrent_mcp_config()

    # LangGraph native MCP client - handles all HTTP/protocol details
    client = MultiServerMCPClient(config)

    # Initialize connection (required before get_tools)
    await client.__aenter__()

    return client


async def _load_mcp_tools() -> List[BaseTool]:
    """Load tools from qBittorrent MCP server via HTTP.

    Uses LangGraph's native MCP client to:
    1. Connect to remote HTTP MCP server
    2. List available tools via MCP protocol over HTTP
    3. Convert MCP tools to LangChain tools automatically

    Returns:
        List of LangChain BaseTool instances wrapping MCP tools
    """
    global _mcp_client

    # Initialize client if not already done
    if _mcp_client is None:
        _mcp_client = await _initialize_mcp_client()

    # Get tools from MCP server (returns LangChain-compatible tools)
    tools = await _mcp_client.get_tools()

    return tools


def get_qbittorrent_tools() -> List[BaseTool]:
    """Get qBittorrent MCP tools (cached, synchronous).

    Loads tools once at module import time and caches them.
    The MCP server HTTP connection is managed by MultiServerMCPClient
    and reused across all tool invocations for performance.

    Returns:
        List of LangChain tools for qBittorrent operations:
        - qb_list_torrents: List/filter torrents
        - qb_torrent_info: Get detailed torrent info
        - qb_add_torrent: Add torrents by URL/magnet
        - qb_control_torrent: Pause/resume/delete torrents
        - qb_search_torrents: Search for torrents
        - qb_get_preferences: Get qBittorrent settings
    """
    global _mcp_tools_cache

    if _mcp_tools_cache is None:
        # Load tools synchronously at module import
        _mcp_tools_cache = asyncio.run(_load_mcp_tools())

    return _mcp_tools_cache


# Cleanup handler for graceful shutdown
async def cleanup_mcp_client():
    """Cleanup MCP client connection on app shutdown."""
    global _mcp_client
    if _mcp_client is not None:
        await _mcp_client.__aexit__(None, None, None)
        _mcp_client = None


# Convenience functions for individual tools
def get_tool_by_name(tool_name: str) -> BaseTool:
    """Get specific MCP tool by name."""
    tools = get_qbittorrent_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    raise ValueError(f"Tool {tool_name} not found in MCP server")


def get_torrent_search_tool() -> BaseTool:
    """Get qb_search_torrents tool."""
    return get_tool_by_name("qb_search_torrents")


def get_torrent_status_tool() -> BaseTool:
    """Get qb_list_torrents tool."""
    return get_tool_by_name("qb_list_torrents")


def get_torrent_add_tool() -> BaseTool:
    """Get qb_add_torrent tool."""
    return get_tool_by_name("qb_add_torrent")


def get_torrent_control_tool() -> BaseTool:
    """Get qb_control_torrent tool."""
    return get_tool_by_name("qb_control_torrent")
```

**Key Points:**
- ✅ **Uses `MultiServerMCPClient`** - LangGraph's built-in HTTP MCP client
- ✅ **No custom wrappers needed** - `.get_tools()` returns LangChain tools
- ✅ **Connection pooling automatic** - Client reuses HTTP connections
- ✅ **Works across Docker containers** - Pure HTTP, no subprocess needed
- ✅ **Graceful cleanup** - `cleanup_mcp_client()` for app shutdown

---

#### 2.4 Update Agent Configuration

**File: `turtleapp/src/core/nodes/agents.py`**

Replace torrent tool imports with MCP tools:

```python
"""Specialized agents (UPDATED for MCP)."""

from typing import Literal, List

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langgraph.graph import MessagesState
from langgraph.types import Command

from turtleapp.src.core.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_agent_llm
from turtleapp.src.core.prompts import (
    AGENT_BASE_PROMPT,
    MOVIE_RETRIEVER_PROMPT,
    TORRENT_MANAGER_PROMPT
)
from turtleapp.src.core.tools import library_manager_tool, movie_retriever_tool
# REMOVED: from turtleapp.src.core.tools import torrent_download_tool, torrent_search_tool

# NEW: Import MCP tools
from turtleapp.src.core.mcp.tools import (
    get_torrent_search_tool,
    get_torrent_status_tool,
    get_torrent_add_tool,
    get_torrent_control_tool
)


# ... ToolAgent class unchanged ...


# Movie retriever - unchanged
movie_retriever_agent = ToolAgent(
    [movie_retriever_tool],
    specialized_prompt=MOVIE_RETRIEVER_PROMPT
)

# Download manager - NOW USES MCP TOOLS (via HTTP)
torrent_agent = ToolAgent(
    [
        get_torrent_search_tool(),      # qb_search_torrents (from HTTP MCP)
        get_torrent_status_tool(),      # qb_list_torrents (from HTTP MCP)
        get_torrent_add_tool(),         # qb_add_torrent (from HTTP MCP)
        get_torrent_control_tool()      # qb_control_torrent (from HTTP MCP)
    ],
    name="movies_download_manager",
    specialized_prompt=TORRENT_MANAGER_PROMPT
)

# Library manager - unchanged
# (library_scan_node remains as-is)
```

**Changes:**
- Remove imports of old `torrent_download_tool`, `torrent_search_tool`
- Import MCP tool getters from `turtleapp.src.core.mcp.tools`
- Update `torrent_agent` to use 4 MCP tools (from HTTP server) instead of 2 legacy tools
- All other agents unchanged

---

#### 2.5 Update FastAPI Startup/Shutdown Hooks

**File: `turtleapp/api/main.py`**

Add cleanup for MCP client on shutdown:

```python
"""FastAPI application with MCP lifecycle management."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from turtleapp.api.routes.endpoints import router
from turtleapp.src.core.mcp.tools import cleanup_mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    # MCP client initializes lazily on first tool use
    yield

    # Shutdown - cleanup MCP HTTP connections
    await cleanup_mcp_client()


app = FastAPI(
    title="Turtle App",
    description="AI-powered home theater assistant with MCP integration",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(router)
```

---

#### 2.6 Update Agent Prompt (Keep Tool Names Abstract)

**File: `turtleapp/src/core/prompts/agents.py`**

**IMPORTANT**: Do NOT mention qBittorrent or technical tool names in prompts. Let the MCP tool descriptions handle the details. The LLM should only know about movie download concepts:

```python
TORRENT_MANAGER_PROMPT = PromptTemplate.from_template("""
You are a movie download management expert specializing in movie file acquisition.

Your capabilities:
- Search across multiple movie sources and repositories
- Monitor download progress and status
- Manage download queue and operations
- Handle download troubleshooting

**Available Tools:** {tools}

**Tool Usage Guidelines:**
- The tools provided handle all download operations automatically
- Search for movies by title and year for best results
- Check download status before searching for duplicates
- Use appropriate filters when checking download status
- Provide clear, user-friendly responses to users

**Task:** {input}

**Approach:**
1. Determine if user wants to search for new movies or check existing downloads
2. For searches: extract movie title and year if provided
3. For status checks: get current download information with appropriate filter
4. For managing downloads: identify the specific download and action needed
5. Provide clear, actionable information

**Important:**
- Let the tools handle the technical details (you don't need to know implementation)
- Focus on user intent: search, status, add, or control operations
- Avoid technical jargon in responses - speak in terms of "movies" and "downloads"
- Return control to supervisor after completing your task

Use this format:
Thought: What do I need to do?
Action: {tool_names}
Action Input: the input for the action
Observation: the result of the action
Thought: What's the result and what should I do next?
Final Answer: Complete response for the user

Begin!
{agent_scratchpad}
""")
```

**Key Design Decisions:**
- ❌ **Don't list specific tool names** (`qb_search_torrents`, etc.) - LangChain provides this via `{tools}` variable
- ❌ **Don't mention qBittorrent** - Keep abstraction at "movie download manager" level
- ✅ **Rely on MCP tool descriptions** - They already have good descriptions for the LLM
- ✅ **Focus on user intent** - Search, status, add, control are the concepts LLM needs
- ✅ **Keep existing user-friendly language** - "downloads" not "torrents", "movie files" not "magnet links"

---

### Phase 3: Remove Legacy Code

**Duration: 1 hour**

#### 3.1 Delete Legacy Torrent Tools

**File: `turtleapp/src/core/tools/torrent_tools.py`** - **DELETE ENTIRELY**

```bash
# Remove the file completely
rm turtleapp/src/core/tools/torrent_tools.py
```

**What to remove:**
- ❌ `api_call()` function - replaced by MCP server's qBittorrent client
- ❌ `get_torrents()` function - replaced by `qb_list_torrents` MCP tool
- ❌ `search_torrents()` function - replaced by `qb_search_torrents` MCP tool
- ❌ `TorrentDownloadsTool` class - replaced by `qb_list_torrents` MCP tool
- ❌ `TorrentSearchTool` class - replaced by `qb_search_torrents` MCP tool
- ❌ All direct HTTP calls to qBittorrent API

**Rationale:**
- No need for deprecation warnings - clean break
- MCP provides all functionality (and more)
- Keeping old code creates confusion and maintenance burden
- No backward compatibility needed (internal implementation detail)

#### 3.2 Update Tools Module Exports

**File: `turtleapp/src/core/tools/__init__.py`**

Remove torrent tool exports:

```python
"""Tool exports for turtle app agents."""

# Existing tools (keep)
from turtleapp.src.core.tools.movie_summaries_retriever import movie_retriever_tool
from turtleapp.src.core.tools.library_manager import library_manager_tool

# REMOVED: torrent tool exports
# from turtleapp.src.core.tools.torrent_tools import (
#     torrent_search_tool,
#     torrent_download_tool
# )

# Export only non-MCP tools
__all__ = [
    "movie_retriever_tool",
    "library_manager_tool",
]
```

#### 3.3 Simplify Settings - Remove qBittorrent Config

**File: `turtleapp/settings.py`**

Remove qBittorrent settings entirely - MCP server has its own config:

```python
# BEFORE: (DELETE THIS)
# class QBittorrentSettings(BaseModel):
#     host: str
#     credentials: dict

# NEW: Only MCP config needed
class MCPSettings(BaseModel):
    """MCP server configuration (HTTP-based)."""
    qbittorrent_url: str = "http://mcp-qbittorrent:8000/mcp"

class Settings(BaseSettings):
    # Existing settings
    pinecone: PineconeSettings
    openai: OpenAISettings
    models: ModelSettings

    # NEW: MCP configuration
    mcp: MCPSettings = MCPSettings()

    # REMOVED: qbittorrent settings (now in MCP server's .env)
    # qbittorrent: QBittorrentSettings  # DELETE THIS
```

**Rationale:**
- qBittorrent credentials belong in MCP server's environment, not main app
- Main app only needs to know the HTTP URL of MCP server
- Cleaner separation of concerns

#### 3.4 Update Environment Variables

**File: `.env.example`**

Update env var documentation:

```bash
# OpenAI API (for embeddings)
OPENAI_API_KEY=your_openai_key

# Anthropic API (for LLMs)
CLAUDE_API=your_anthropic_key

# Pinecone Vector DB
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=your_index

# LangSmith (optional)
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true

# ============================================
# MCP Server Configuration (HTTP Transport)
# ============================================
# Main app only needs MCP server URL
TURTLEAPP_MCP_QBITTORRENT_URL=http://mcp-qbittorrent:8000/mcp

# MCP server environment variables (set in mcp-qbittorrent container)
# These are NOT read by main app, only by MCP server
TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin

# REMOVED: Old qBittorrent settings (no longer needed in main app)
# QBITTORRENT_HOST=...
# QBITTORRENT_USERNAME=...
# QBITTORRENT_PASSWORD=...
```

**Migration Note:**
- Main app: Only needs `TURTLEAPP_MCP_QBITTORRENT_URL` (MCP server HTTP endpoint)
- MCP server: Needs `TURTLEAPP_QB_*` vars (qBittorrent credentials)
- Clean separation - main app never touches qBittorrent directly

---

### Phase 4: Testing Strategy

**Duration: 4-5 hours**

#### 4.1 Unit Tests for MCP Integration

**File: `turtleapp/tests/test_mcp_integration.py`** (NEW)

```python
"""Test MCP integration with LangGraph (HTTP transport)."""

import pytest
from turtleapp.src.core.mcp.tools import (
    get_qbittorrent_tools,
    get_torrent_search_tool,
    get_tool_by_name
)


def test_mcp_tools_load():
    """Test MCP tools can be loaded from HTTP server."""
    tools = get_qbittorrent_tools()

    assert len(tools) == 6  # Expected number of MCP tools
    assert all(tool.name.startswith("qb_") for tool in tools)


def test_get_tool_by_name():
    """Test individual tool retrieval."""
    search_tool = get_tool_by_name("qb_search_torrents")
    assert search_tool is not None
    assert search_tool.name == "qb_search_torrents"


def test_tool_name_mapping():
    """Test convenience functions return correct tools."""
    search_tool = get_torrent_search_tool()
    assert search_tool.name == "qb_search_torrents"


@pytest.mark.asyncio
@pytest.mark.expensive  # Requires running MCP HTTP server
async def test_mcp_search_tool_execution():
    """Test MCP search tool can execute over HTTP."""
    search_tool = get_torrent_search_tool()

    # Test search with legal content
    result = await search_tool.ainvoke({"query": "Ubuntu 22.04", "limit": 5})

    assert "results" in result or "error" in result
    # Should return either results or error (if search plugins not configured)


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_mcp_list_tool_execution():
    """Test MCP list tool can execute over HTTP."""
    from turtleapp.src.core.mcp.tools import get_torrent_status_tool

    status_tool = get_torrent_status_tool()
    result = await status_tool.ainvoke({"filter": "all"})

    assert "torrents" in result or "count" in result
```

#### 4.2 Integration Test with Agent

**File: `turtleapp/tests/test_agent_mcp.py`** (NEW)

```python
"""Test agents using MCP tools (HTTP transport)."""

import pytest
from turtleapp.src.core.nodes.agents import torrent_agent
from langgraph.graph import MessagesState


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_torrent_agent_with_mcp():
    """Test torrent agent can use MCP tools over HTTP."""

    # Create test state
    state = MessagesState(
        messages=["Search for Ubuntu 22.04 torrents"]
    )

    # Invoke agent
    command = await torrent_agent.process(state)

    # Check response
    assert command.goto == "supervisor"
    assert len(command.update["messages"]) > 0

    response = command.update["messages"][-1].content
    assert "ubuntu" in response.lower() or "search" in response.lower()
```

#### 4.3 End-to-End Workflow Test

**File: `turtleapp/tests/test_graph_mcp.py`** (NEW)

```python
"""Test full workflow with MCP integration (HTTP transport)."""

import pytest
from turtleapp.src.workflows.graph import create_movie_workflow


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_workflow_with_mcp_search():
    """Test full workflow handles MCP-based search over HTTP."""

    workflow = create_movie_workflow()

    # Test search query
    result, thread_id = workflow.invoke(
        "Search for Ubuntu 22.04 and show me the results"
    )

    # Check supervisor routed to download manager
    messages = result["messages"]
    assert len(messages) > 0

    final_response = messages[-1].content
    assert "ubuntu" in final_response.lower() or "search" in final_response.lower()


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_workflow_with_mcp_status():
    """Test workflow handles download status check via MCP HTTP."""

    workflow = create_movie_workflow()

    result, thread_id = workflow.invoke(
        "What's currently downloading?"
    )

    messages = result["messages"]
    final_response = messages[-1].content

    # Should either show downloads or say "no active downloads"
    assert "download" in final_response.lower() or "no active" in final_response.lower()
```

#### 4.4 Test Execution Plan

```bash
# 1. Start MCP HTTP server (in separate terminal)
cd packages/qbittorrent-mcp
export TURTLEAPP_QB_QBITTORRENT_URL=http://localhost:15080
export TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
export TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin
uv run fastmcp run mcp_qbittorrent.server:mcp --transport http

# 2. Test MCP tools load correctly (main terminal)
poetry run pytest turtleapp/tests/test_mcp_integration.py::test_mcp_tools_load -v

# 3. Test individual tool execution (requires MCP server)
poetry run pytest turtleapp/tests/test_mcp_integration.py -m expensive -v

# 4. Test agent with MCP tools
poetry run pytest turtleapp/tests/test_agent_mcp.py -m expensive -v

# 5. Test full workflow
poetry run pytest turtleapp/tests/test_graph_mcp.py -m expensive -v

# 6. Run all tests (skip expensive by default)
poetry run pytest -m "not expensive" -v

# 7. Run full test suite including MCP
poetry run pytest -v
```

---

### Phase 5: Docker & Deployment

**Duration: 2-3 hours**

#### 5.1 Update Docker Compose

**File: `build/docker-compose.yml`**

```yaml
version: '3.8'

services:
  # Existing qBittorrent service (unchanged)
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    container_name: qbittorrent
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - WEBUI_PORT=15080
    volumes:
      - ./qbittorrent_config:/config
      - ./downloads:/downloads
    ports:
      - 15080:15080
      - 6881:6881
      - 6881:6881/udp
    restart: unless-stopped

  # NEW: MCP Server (separate container with HTTP endpoint)
  mcp-qbittorrent:
    build:
      context: ../packages/qbittorrent-mcp
      dockerfile: Dockerfile
    container_name: mcp-qbittorrent
    environment:
      # MCP server connects to qBittorrent
      - TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
      - TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
      - TURTLEAPP_QB_QBITTORRENT_PASSWORD=${QB_PASSWORD:-adminadmin}
    ports:
      - "8001:8000"  # Expose HTTP endpoint for debugging
    depends_on:
      - qbittorrent
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/mcp/tools"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Existing NAS service (unchanged)
  nas:
    image: dperson/samba
    # ... existing config ...

  # UPDATED: Turtle App (connects to MCP server via HTTP)
  turtle-app:
    build:
      context: ..
      dockerfile: build/Dockerfile
    container_name: turtleapp
    environment:
      # MCP server URL (HTTP transport)
      - TURTLEAPP_MCP_QBITTORRENT_URL=http://mcp-qbittorrent:8000/mcp

      # Other existing env vars
      - CLAUDE_API=${CLAUDE_API}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT}
      - PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME}
      - SAMBA_SHARE_PATH=${SAMBA_SHARE_PATH:-daves}

    ports:
      - "8000:8000"
    depends_on:
      mcp-qbittorrent:
        condition: service_healthy
      nas:
        condition: service_started
    restart: unless-stopped
```

**Key Changes:**
- ✅ **Separate MCP server container** - Runs FastMCP HTTP server
- ✅ **HTTP communication** - Main app connects via `http://mcp-qbittorrent:8000/mcp`
- ✅ **Health checks** - Ensures MCP server is ready before starting main app
- ✅ **Clean separation** - MCP server only knows qBittorrent, main app only knows MCP URL
- ✅ **Port 8001** - Exposed for debugging MCP server (optional)

#### 5.2 Update Main App Dockerfile

**File: `build/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY turtleapp/ ./turtleapp/
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install poetry

# Install dependencies (including langchain-mcp-adapters)
RUN poetry install --no-dev

# Expose API port
EXPOSE 8000

# Run FastAPI server
CMD ["poetry", "run", "uvicorn", "turtleapp.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Changes:**
- ❌ **No `uv` needed** - MCP server is separate container, not subprocess
- ❌ **No MCP server code copied** - Clean separation
- ✅ **Only `langchain-mcp-adapters` needed** - For HTTP MCP client

#### 5.3 Verify Deployment

```bash
# Build all containers
cd build
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f mcp-qbittorrent  # Should show HTTP server started
docker-compose logs -f turtle-app       # Should show FastAPI started

# Test MCP server directly
curl http://localhost:8001/mcp/tools | jq

# Test main app
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What's currently downloading?"}'
```

---

### Phase 6: Documentation Updates

**Duration: 1-2 hours**

#### 6.1 Update CLAUDE.md

**File: `CLAUDE.md`**

Add MCP architecture section:

```markdown
## MCP Integration

### Architecture

Turtle App uses **LangGraph's native MCP support** with **HTTP transport** for qBittorrent integration:

```
Docker Container: Turtle App
┌────────────────────────────┐
│ LangGraph Supervisor       │
│        ↓                   │
│ Torrent Agent              │
│        ↓                   │
│ MultiServerMCPClient       │
│ (langchain-mcp-adapters)   │
└────────────────────────────┘
        ↓ HTTP (streamable_http)
Docker Container: MCP Server
┌────────────────────────────┐
│ FastMCP HTTP Server        │
│ (Port 8000, /mcp endpoint) │
│        ↓                   │
│ qBittorrent MCP Tools      │
└────────────────────────────┘
        ↓ HTTP
Docker Container: qBittorrent
┌────────────────────────────┐
│ qBittorrent Web API        │
│ (Port 15080)               │
└────────────────────────────┘
```

### MCP Tools

The **download manager agent** uses these MCP tools (implementation: qBittorrent server):

- **qb_search_torrents**: Search for available movie sources
- **qb_list_torrents**: List/filter downloads by status (downloading/completed/paused)
- **qb_add_torrent**: Add a movie to the download queue
- **qb_control_torrent**: Pause/resume/delete downloads
- **qb_torrent_info**: Get detailed download information
- **qb_get_preferences**: Get download client configuration

**Note**: The LLM prompt never mentions "qBittorrent" or "torrent" - it operates at the abstraction level of "movie downloads" and "download management". The MCP tools handle implementation details transparently.

### Transport: HTTP vs stdio

This implementation uses **HTTP transport** (`streamable_http`) for MCP communication:

**Benefits:**
- ✅ Works across Docker container boundaries
- ✅ MCP server can be scaled independently
- ✅ Standard HTTP debugging tools (curl, Postman)
- ✅ Can add authentication/authorization later
- ✅ Multiple clients can use same MCP server

**Trade-offs:**
- ❌ Slightly higher latency than stdio (network overhead)
- ❌ More complex Docker setup (separate container)

**Alternative**: For single-container deployments, use `stdio` transport (subprocess model). See `mcp-integration-plan.md` for details.

### Adding New MCP Tools

1. Add tool to MCP server: `packages/qbittorrent-mcp/src/mcp_qbittorrent/tools/qbittorrent_tools.py`
2. Restart MCP server container: `docker-compose restart mcp-qbittorrent`
3. Tools auto-reload in main app (loaded at startup)
4. Update agent: Add tool to agent in `turtleapp/src/core/nodes/agents.py`
5. Update prompt: Document tool in `turtleapp/src/core/prompts/agents.py`

### MCP Server Development

```bash
# Run MCP HTTP server locally
cd packages/qbittorrent-mcp
export TURTLEAPP_QB_QBITTORRENT_URL=http://localhost:15080
export TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
export TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin
uv run fastmcp run mcp_qbittorrent.server:mcp --transport http

# Test MCP server
curl http://localhost:8000/mcp/tools | jq

# Test tool execution
curl -X POST http://localhost:8000/mcp/tools/qb_list_torrents \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"filter": "all"}}'
```

### Adding More MCP Servers

To add additional MCP servers (Plex, Sonarr, etc.):

1. Deploy new MCP server as Docker container with HTTP endpoint
2. Add server config to `turtleapp/src/core/mcp/config.py`:
   ```python
   def get_plex_mcp_config() -> Dict[str, Any]:
       return {
           "plex": {
               "url": "http://mcp-plex:8000/mcp",
               "transport": "streamable_http"
           }
       }
   ```
3. Create tool loader in `turtleapp/src/core/mcp/tools.py`
4. Create agent using new tools in `turtleapp/src/core/nodes/agents.py`
5. Add agent to workflow in `turtleapp/src/workflows/graph.py`
6. Update `docker-compose.yml` with new MCP server container
```

#### 6.2 Update README.md

**File: `README.md`**

Add MCP section to architecture overview:

```markdown
## Architecture

Turtle App uses a **multi-agent architecture** powered by LangGraph and MCP (Model Context Protocol):

### MCP Integration

The app leverages **LangGraph's native MCP support** with **HTTP transport** for modular, reusable integrations:

- **qBittorrent MCP Server**: Standalone HTTP server for torrent management
  - Location: `packages/qbittorrent-mcp/`
  - Protocol: MCP via HTTP (streamable_http transport)
  - Endpoint: `http://mcp-qbittorrent:8000/mcp`
  - Tools: Search, list, add, control torrents
  - Deployment: Separate Docker container

### Benefits of MCP Architecture

- ✅ **Modular**: MCP servers can be reused in other projects
- ✅ **Maintainable**: Clear separation between app logic and external services
- ✅ **Testable**: MCP servers can be tested independently via HTTP
- ✅ **Scalable**: Easy to add new MCP servers (Plex, Sonarr, Radarr, etc.)
- ✅ **Container-native**: Each MCP server in its own container for isolation
- ✅ **Standard protocol**: HTTP transport allows debugging with curl/Postman

### Running with Docker Compose

```bash
cd build
docker-compose up -d

# Services started:
# - qbittorrent (port 15080)
# - mcp-qbittorrent (port 8001) - HTTP MCP server
# - turtle-app (port 8000) - FastAPI app
# - nas (ports 1139, 1445) - Samba server
```

### Environment Variables

```bash
# Main app only needs MCP server URL
TURTLEAPP_MCP_QBITTORRENT_URL=http://mcp-qbittorrent:8000/mcp

# MCP server needs qBittorrent credentials (set in docker-compose)
TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin
```
```

---

### Phase 7: Migration Checklist

#### Pre-Migration
- [ ] Backup current codebase: `git branch backup-pre-mcp-$(date +%Y%m%d)`
- [ ] Create feature branch: `git checkout -b feat/mcp-http-integration`
- [ ] Verify LangGraph >= 0.2.34: `poetry show langgraph`
- [ ] Document current API behavior for regression testing

#### Phase 0: Setup (1 hour)
- [ ] Install `langchain-mcp-adapters`: `poetry add langchain-mcp-adapters`
- [ ] Copy MCP server to `packages/qbittorrent-mcp/`
- [ ] Update MCP server package name in its `pyproject.toml`
- [ ] Test MCP HTTP server runs: `cd packages/qbittorrent-mcp && uv run fastmcp run mcp_qbittorrent.server:mcp --transport http`

#### Phase 1: MCP Server HTTP Setup (2-3 hours)
- [ ] Update MCP server config.py env prefix to `TURTLEAPP_QB_`
- [ ] Create `packages/qbittorrent-mcp/Dockerfile`
- [ ] Test MCP server Docker build: `cd packages/qbittorrent-mcp && docker build -t mcp-qbittorrent .`
- [ ] Test MCP HTTP endpoint: `curl http://localhost:8000/mcp/tools`

#### Phase 2: LangGraph Integration (3-4 hours)
- [ ] Create `turtleapp/src/core/mcp/config.py` with HTTP config
- [ ] Create `turtleapp/src/core/mcp/tools.py` using `MultiServerMCPClient`
- [ ] Update `turtleapp/src/core/nodes/agents.py` to use MCP tools
- [ ] Update `turtleapp/src/core/prompts/agents.py` with abstracted prompt
- [ ] Update `turtleapp/api/main.py` with MCP cleanup lifecycle
- [ ] Test tools load: `poetry run python -c "from turtleapp.src.core.mcp.tools import get_qbittorrent_tools; print(len(get_qbittorrent_tools()))"`

#### Phase 3: Remove Legacy Code (1 hour)
- [ ] Delete `turtleapp/src/core/tools/torrent_tools.py` entirely
- [ ] Remove torrent tool exports from `turtleapp/src/core/tools/__init__.py`
- [ ] Remove `QBittorrentSettings` from `turtleapp/settings.py`
- [ ] Add `MCPSettings` to `turtleapp/settings.py`
- [ ] Update `.env.example` with HTTP transport env vars
- [ ] Update local `.env` with new env var names

#### Phase 4: Testing (4-5 hours)
- [ ] Create `test_mcp_integration.py` with HTTP tests
- [ ] Create `test_agent_mcp.py`
- [ ] Create `test_graph_mcp.py`
- [ ] Start MCP HTTP server: `cd packages/qbittorrent-mcp && uv run fastmcp run mcp_qbittorrent.server:mcp --transport http`
- [ ] Run unit tests: `poetry run pytest -m "not expensive" -v`
- [ ] Run integration tests: `poetry run pytest -m expensive -v`
- [ ] Test API endpoints: `curl -X POST http://localhost:8000/chat -d '{"message":"search for ubuntu"}'`

#### Phase 5: Docker (2-3 hours)
- [ ] Update `build/docker-compose.yml` with separate MCP container
- [ ] Update `build/Dockerfile` (remove uv, no MCP server code)
- [ ] Test Docker build: `cd build && docker-compose build`
- [ ] Test Docker run: `docker-compose up -d`
- [ ] Test MCP server health: `curl http://localhost:8001/mcp/tools`
- [ ] Test API in Docker: `curl http://localhost:8000/health`
- [ ] Test full workflow: `curl -X POST http://localhost:8000/chat -d '{"message":"what's downloading?"}'`

#### Phase 6: Documentation (1-2 hours)
- [ ] Update CLAUDE.md with MCP HTTP architecture
- [ ] Update README.md with HTTP transport details
- [ ] Document alternative deployments (stdio vs HTTP)
- [ ] Create migration notes
- [ ] Document rollback procedure

#### Post-Migration Validation
- [ ] All existing tests pass
- [ ] API endpoints work unchanged
- [ ] Download search works via MCP HTTP
- [ ] Download status works via MCP HTTP
- [ ] Docker deployment works with 3 containers
- [ ] MCP server can be accessed independently (curl)
- [ ] Performance comparable to legacy
- [ ] No regressions in user-facing features

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 0 | Prerequisites & setup | 1 hour |
| 1 | MCP server HTTP setup | 2-3 hours |
| 2 | LangGraph integration (HTTP) | 3-4 hours |
| 3 | Remove legacy code | 1 hour |
| 4 | Testing | 4-5 hours |
| 5 | Docker & deployment | 2-3 hours |
| 6 | Documentation | 1-2 hours |
| **Total** | | **14-19 hours** |

---

## Risks & Mitigations

### Risk 1: HTTP Latency Higher Than Legacy
**Impact**: Medium - Slower response times for download operations
**Likelihood**: Low - HTTP overhead minimal for this use case
**Mitigation**:
- Use HTTP keep-alive (handled by `MultiServerMCPClient`)
- Benchmark vs legacy (should be <50ms added latency)
- Cache tool metadata to avoid repeated HTTP calls
- Consider connection pooling if latency is issue

### Risk 2: MCP Server Container Failure
**Impact**: High - All download operations fail
**Likelihood**: Low - Container restarts automatically
**Mitigation**:
- Health checks in docker-compose
- Graceful error handling in main app
- Fallback message to user: "Download service temporarily unavailable"
- Retry logic in `MultiServerMCPClient`

### Risk 3: Network Configuration Issues
**Impact**: Medium - Services can't communicate
**Likelihood**: Low - Docker networking is reliable
**Mitigation**:
- Use explicit Docker network in compose file
- Test with `docker network inspect`
- Add logging for network errors
- Document troubleshooting steps

### Risk 4: Tool Schema Mismatch
**Impact**: Medium - Agent can't use tools correctly
**Likelihood**: Low - MCP spec is well-defined
**Mitigation**:
- Add schema validation tests
- Test tool execution in isolation
- Clear error messages from MCP server
- Version MCP protocol if schema changes

---

## Success Criteria

- [ ] All existing API endpoints work unchanged
- [ ] All tests pass (unit + integration)
- [ ] **No `torrent_tools.py` file exists** - completely removed
- [ ] **No `QBittorrentSettings` in main app settings** - removed
- [ ] **No direct qBittorrent HTTP calls anywhere** in main app code
- [ ] **No qBittorrent imports** in main app (only MCP URL config)
- [ ] MCP server can be tested independently via HTTP: `curl http://localhost:8001/mcp/tools`
- [ ] Docker Compose deployment works with 3 containers (app, mcp, qbittorrent)
- [ ] Documentation accurate and up-to-date
- [ ] Performance within 10% of legacy implementation
- [ ] No user-facing regressions
- [ ] Code is simpler and more maintainable
- [ ] **Main app is agnostic to download backend** - could swap qBittorrent for Transmission without touching agent code
- [ ] **MCP server is reusable** - can be used by other apps via HTTP

---

## Rollback Plan

If migration fails:

1. **Revert to backup branch**:
   ```bash
   git checkout main
   git reset --hard backup-pre-mcp-$(date +%Y%m%d)
   ```

2. **Restore legacy tools**:
   - Un-deprecate `torrent_tools.py`
   - Restore imports in `agents.py`

3. **Restore Docker config**:
   - Revert `docker-compose.yml` (remove MCP container)
   - Revert `Dockerfile`

4. **Redeploy**:
   ```bash
   cd build
   docker-compose down
   docker-compose up -d --build
   ```

**Recovery Time Objective (RTO)**: < 15 minutes

---

## Future Enhancements

After successful migration:

1. **Add More MCP Servers**:
   - Plex MCP server for library management (HTTP transport)
   - Sonarr/Radarr MCP servers for content discovery
   - Jellyfin MCP server as alternative to Plex

2. **Publish MCP Servers**:
   - Package qBittorrent MCP as standalone Docker image
   - Push to Docker Hub for community use
   - Add to MCP server registry
   - Open source for community contributions

3. **Advanced Features**:
   - MCP server health monitoring dashboard
   - Load balancing multiple MCP server instances
   - MCP server hot-reload during development
   - Streaming responses from MCP tools (SSE transport)
   - Authentication/authorization for MCP HTTP endpoints

4. **Observability**:
   - LangSmith tracing for MCP calls
   - MCP HTTP latency metrics (Prometheus)
   - Error rate monitoring per MCP tool
   - MCP server logs aggregation (ELK stack)
   - Distributed tracing (OpenTelemetry)

5. **Performance Optimization**:
   - HTTP/2 or gRPC for MCP transport (if supported)
   - Redis cache for frequent MCP tool calls
   - Batch MCP tool invocations
   - Connection pooling tuning

---

## References

- [LangGraph MCP Documentation](https://langchain-ai.github.io/langgraph/agents/mcp/)
- [LangChain MCP Adapters (GitHub)](https://github.com/langchain-ai/langchain-mcp-adapters)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [qBittorrent Web API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1))
- [LangChain Changelog: MCP with streamable HTTP transport](https://changelog.langchain.com/announcements/mcp-with-streamable-http-transport)

---

## Appendix: Alternative Architectures

### A. Single Container (stdio transport)

**Use case:** Simplified deployment, local development

```yaml
# docker-compose.yml (simplified)
services:
  qbittorrent:
    # ... same as main plan ...

  turtle-app:
    build: .
    environment:
      - TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
      - TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
      - TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin
    depends_on:
      - qbittorrent
    # No separate MCP container
```

**Code changes:**
```python
# turtleapp/src/core/mcp/config.py
def get_qbittorrent_mcp_config() -> Dict[str, Any]:
    return {
        "qbittorrent": {
            "command": "uv",
            "args": ["run", "mcp-qbittorrent"],
            "transport": "stdio",
            "env": {
                "TURTLEAPP_QB_QBITTORRENT_URL": os.getenv(...),
                "TURTLEAPP_QB_QBITTORRENT_USERNAME": os.getenv(...),
                "TURTLEAPP_QB_QBITTORRENT_PASSWORD": os.getenv(...),
            }
        }
    }
```

---

### B. Kubernetes Sidecar

**Use case:** Cloud-native deployment

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: turtle-app
        image: turtle-app:latest
        env:
        - name: TURTLEAPP_MCP_QBITTORRENT_URL
          value: http://localhost:8000/mcp

      - name: mcp-qbittorrent  # Sidecar
        image: mcp-qbittorrent:latest
        ports:
        - containerPort: 8000
```

---

### C. Serverless (AWS Lambda + API Gateway)

**Use case:** Serverless, event-driven

- Main app: AWS Lambda function
- MCP server: ECS Fargate container (long-running)
- Communication: HTTP via API Gateway + VPC Link

**Trade-offs:**
- ✅ Auto-scaling, pay-per-use
- ❌ Cold start latency
- ❌ Complex network setup
