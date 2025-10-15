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

### Transport: HTTP (streamable_http)

The MCP protocol supports multiple transport mechanisms. This plan uses **HTTP transport** for Docker container communication:

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
- ❌ Requires network configuration in Docker Compose
- ❌ More moving parts (HTTP server, network stack)

---

### Deployment Architecture

This plan uses **separate Docker containers** with HTTP communication:

**Benefits:**
- ✅ Maximum modularity and reusability
- ✅ Can scale MCP server independently
- ✅ Clear separation of concerns
- ✅ MCP server can serve multiple clients
- ✅ Standard HTTP debugging (curl, logs)

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

**Why FastMCP:**
- ✅ Quick development - minimal boilerplate
- ✅ Automatic HTTP server setup
- ✅ Built-in validation and error handling
- ✅ Already used by existing `mcp-qbittorrent` server
- ✅ Sufficient for our needs

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

#### 0.1 Convert from Poetry to uv (Optional but Recommended)

```bash
cd /home/pie/git/turtle_app

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize uv.lock from pyproject.toml
uv lock

# Verify dependencies resolve correctly
uv sync

# Test that existing code works with uv
uv run python -c "import langgraph; print(langgraph.__version__)"
```

**Why uv?**
- ✅ **10-100x faster** than Poetry for dependency resolution
- ✅ **Consistent with MCP server** - already uses uv
- ✅ **Simpler Docker builds** - single tool for dependencies
- ✅ **Better caching** - faster CI/CD pipelines
- ✅ **Works with existing pyproject.toml** - no migration needed

**Note:** You can keep `pyproject.toml` unchanged - uv reads the same format as Poetry.

---

#### 0.2 Verify LangGraph Version & Install MCP Adapters

```bash
cd /home/pie/git/turtle_app

# Check LangGraph version
uv pip list | grep langgraph
# Must be >= 0.2.34 for native MCP support

# Install langchain-mcp-adapters (NEW)
uv add langchain-mcp-adapters
```

If LangGraph upgrade needed:
```bash
uv add langgraph --upgrade
```

---

#### 0.3 Copy MCP Server to Monorepo

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

#### 0.4 Create Feature Branch

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
uv add langchain-mcp-adapters
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

#### 2.6 Remove Specialized Torrent Agent Prompt

**Rationale**: With MCP, tool descriptions fully document agent behavior. No need for domain-specific prompt guidance.

**File: `turtleapp/src/core/prompts/agents.py`**

Remove the `TORRENT_MANAGER_PROMPT` entirely:

```python
# DELETE THIS ENTIRE SECTION (lines 63-101):
# TORRENT_MANAGER_TEMPLATE = """..."""
# TORRENT_MANAGER_PROMPT = PromptTemplate(...)
```

**File: `turtleapp/src/core/nodes/agents.py`**

Update torrent agent to use default `AGENT_BASE_PROMPT`:

```python
# BEFORE:
from turtleapp.src.core.prompts import AGENT_BASE_PROMPT, MOVIE_RETRIEVER_PROMPT, TORRENT_MANAGER_PROMPT
...
torrent_agent = ToolAgent(
    [get_torrent_search_tool(), ...],
    name="movies_download_manager",
    specialized_prompt=TORRENT_MANAGER_PROMPT  # REMOVE THIS
)

# AFTER:
from turtleapp.src.core.prompts import AGENT_BASE_PROMPT, MOVIE_RETRIEVER_PROMPT  # Removed TORRENT_MANAGER_PROMPT
...
torrent_agent = ToolAgent(
    [
        get_torrent_search_tool(),      # qb_search_torrents (from HTTP MCP)
        get_torrent_status_tool(),      # qb_list_torrents (from HTTP MCP)
        get_torrent_add_tool(),         # qb_add_torrent (from HTTP MCP)
        get_torrent_control_tool()      # qb_control_torrent (from HTTP MCP)
    ],
    name="movies_download_manager"
    # No specialized_prompt - uses AGENT_BASE_PROMPT default
)
```

**Key Design Decisions:**
- ✅ **MCP tool descriptions are self-documenting** - No need for additional prompt guidance
- ✅ **Pure abstraction** - Agent behavior driven entirely by tool descriptions, not hardcoded prompts
- ✅ **ReAct structure preserved** - `AGENT_BASE_PROMPT` still provides "Thought/Action/Observation" structure needed by `create_react_agent()`
- ✅ **Easy to swap implementations** - Change MCP server, agent behavior updates automatically
- ✅ **Less maintenance** - One less prompt to keep in sync with tool changes

---

### Phase 3: Remove ALL Legacy/Redundant Code

**Duration: 1-2 hours**

This phase completely removes all qBittorrent-related code from the main app. After this phase, the main app will be **completely agnostic** to qBittorrent - it only knows about MCP tools via HTTP.

---

#### 3.1 Delete Legacy Torrent Tools File

**File: `turtleapp/src/core/tools/torrent_tools.py`** - **DELETE ENTIRELY**

```bash
rm turtleapp/src/core/tools/torrent_tools.py
```

**What gets deleted:**
- ❌ `api_call()` function - replaced by MCP server's qBittorrent client
- ❌ `get_torrents()` function - replaced by `qb_list_torrents` MCP tool
- ❌ `search_torrents()` function - replaced by `qb_search_torrents` MCP tool
- ❌ `TorrentDownloadsTool` class - replaced by `qb_list_torrents` MCP tool
- ❌ `TorrentSearchTool` class - replaced by `qb_search_torrents` MCP tool
- ❌ All direct HTTP calls to qBittorrent API
- ❌ All qBittorrent-specific logic

**Why delete completely:**
- No deprecation warnings needed - clean break
- MCP provides all functionality (and more)
- Keeping old code creates confusion and maintenance burden
- No backward compatibility needed (internal implementation detail)

---

#### 3.2 Delete Legacy Torrent Tests

**File: `turtleapp/tests/test_torrent.py`** - **DELETE ENTIRELY**

```bash
rm turtleapp/tests/test_torrent.py
```

**What gets deleted:**
- ❌ Tests for `get_torrents()` function
- ❌ Tests for `TorrentDownloadsTool` class
- ❌ Tests for `TorrentSearchTool` class
- ❌ Mock tests for qBittorrent API calls

**Replacement:**
- New tests in Phase 4 will test MCP integration instead
- `test_mcp_integration.py` - tests MCP tools load from HTTP server
- `test_agent_mcp.py` - tests agent uses MCP tools correctly

---

#### 3.3 Remove TORRENT_MANAGER_PROMPT

**File: `turtleapp/src/core/prompts/agents.py`**

Delete the entire torrent manager prompt section (lines 63-101):

```python
# DELETE THESE LINES:
# TORRENT_MANAGER_TEMPLATE = """You are a movie download management expert..."""
# TORRENT_MANAGER_PROMPT = PromptTemplate(
#     template=TORRENT_MANAGER_TEMPLATE,
#     input_variables=[...]
# )
```

**Keep:**
- ✅ `AGENT_BASE_PROMPT` - still used as default
- ✅ `MOVIE_RETRIEVER_PROMPT` - still used by movie retriever agent

---

#### 3.4 Update Prompts Module Exports

**File: `turtleapp/src/core/prompts/__init__.py`**

Remove `TORRENT_MANAGER_PROMPT` from imports and exports:

```python
# BEFORE:
from .agents import (
    AGENT_BASE_PROMPT,
    MOVIE_RETRIEVER_PROMPT,
    TORRENT_MANAGER_PROMPT  # DELETE THIS LINE
)

__all__ = [
    "SUPERVISOR_PROMPT",
    "AGENT_BASE_PROMPT",
    "MOVIE_RETRIEVER_PROMPT",
    "TORRENT_MANAGER_PROMPT"  # DELETE THIS LINE
]

# AFTER:
from .agents import (
    AGENT_BASE_PROMPT,
    MOVIE_RETRIEVER_PROMPT
)

__all__ = [
    "SUPERVISOR_PROMPT",
    "AGENT_BASE_PROMPT",
    "MOVIE_RETRIEVER_PROMPT"
]
```

---

#### 3.5 Update Tools Module Exports

**File: `turtleapp/src/core/tools/__init__.py`**

Remove torrent tool exports:

```python
# BEFORE:
from turtleapp.src.core.tools.torrent_tools import (
    torrent_search_tool,
    torrent_download_tool
)

__all__ = [
    "movie_retriever_tool",
    "library_manager_tool",
    "torrent_search_tool",      # DELETE
    "torrent_download_tool"     # DELETE
]

# AFTER:
# Only non-MCP tools - MCP tools loaded separately
from turtleapp.src.core.tools.movie_summaries_retriever import movie_retriever_tool
from turtleapp.src.core.tools.library_manager import library_manager_tool

__all__ = [
    "movie_retriever_tool",
    "library_manager_tool"
]
```

---

#### 3.6 Remove QBittorrentSettings from Settings

**File: `turtleapp/settings.py`**

Delete `QBittorrentSettings` class entirely and replace with `MCPSettings`:

```python
# DELETE THIS ENTIRE CLASS (lines 66-79):
# class QBittorrentSettings(BaseAppSettings):
#     host: Optional[str] = ...
#     username: Optional[str] = ...
#     password: Optional[str] = ...
#     @property
#     def credentials(self) -> dict[str, str]:
#         ...

# ADD THIS NEW CLASS:
class MCPSettings(BaseAppSettings):
    """MCP server configuration (HTTP transport)."""
    qbittorrent_url: str = Field(
        alias="TURTLEAPP_MCP_QBITTORRENT_URL",
        default="http://mcp-qbittorrent:8000/mcp",
        description="HTTP URL for qBittorrent MCP server"
    )

# UPDATE Settings class:
class Settings(BaseAppSettings):
    # ... existing fields ...

    # REMOVE THIS:
    # qbittorrent: QBittorrentSettings = Field(default_factory=QBittorrentSettings)

    # ADD THIS:
    mcp: MCPSettings = Field(default_factory=MCPSettings)
```

**Rationale:**
- qBittorrent credentials belong in MCP server's environment, not main app
- Main app only needs HTTP URL to MCP server
- Cleaner separation of concerns
- Main app becomes agnostic to qBittorrent implementation

---

#### 3.7 Verify No Remaining qBittorrent References

After deletions, verify no qBittorrent imports or usage remains in main app:

```bash
# Search for any remaining qBittorrent references
cd turtleapp
grep -r "qbittorrent" --include="*.py" src/ api/ | grep -v "mcp" | grep -v "MCP"
# Should return NO results (except in comments)

# Search for torrent_tools imports
grep -r "from.*torrent_tools import" --include="*.py" .
# Should return NO results

# Search for TorrentDownloadsTool or TorrentSearchTool
grep -r "TorrentDownloadsTool\|TorrentSearchTool" --include="*.py" .
# Should return NO results
```

**Expected result:** No matches (main app is now qBittorrent-agnostic)

---

#### 3.8 Summary of Deleted Files

**Complete list of files to delete:**
1. ❌ `turtleapp/src/core/tools/torrent_tools.py` - Legacy tool implementations
2. ❌ `turtleapp/tests/test_torrent.py` - Legacy tool tests

**Complete list of code sections to delete:**
1. ❌ `turtleapp/src/core/prompts/agents.py` - `TORRENT_MANAGER_PROMPT` (lines 63-101)
2. ❌ `turtleapp/src/core/prompts/__init__.py` - `TORRENT_MANAGER_PROMPT` import/export
3. ❌ `turtleapp/src/core/tools/__init__.py` - torrent tool imports/exports
4. ❌ `turtleapp/settings.py` - `QBittorrentSettings` class (lines 66-79)
5. ❌ `turtleapp/settings.py` - `qbittorrent: QBittorrentSettings` field in `Settings` class

**Total lines removed:** ~300-400 lines of legacy code

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
uv run pytest turtleapp/tests/test_mcp_integration.py::test_mcp_tools_load -v

# 3. Test individual tool execution (requires MCP server)
uv run pytest turtleapp/tests/test_mcp_integration.py -m expensive -v

# 4. Test agent with MCP tools
uv run pytest turtleapp/tests/test_agent_mcp.py -m expensive -v

# 5. Test full workflow
uv run pytest turtleapp/tests/test_graph_mcp.py -m expensive -v

# 6. Run all tests (skip expensive by default)
uv run pytest -m "not expensive" -v

# 7. Run full test suite including MCP
uv run pytest -v
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

# Install system dependencies including uv
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy application code
COPY turtleapp/ ./turtleapp/
COPY pyproject.toml uv.lock ./

# Install dependencies (including langchain-mcp-adapters)
RUN uv sync --frozen

# Expose API port
EXPOSE 8000

# Run FastAPI server
CMD ["uv", "run", "uvicorn", "turtleapp.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Changes:**
- ✅ **Uses `uv` instead of Poetry** - Faster, consistent with MCP server
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

### Transport: HTTP (streamable_http)

This implementation uses **HTTP transport** for MCP communication:

**Benefits:**
- ✅ Works across Docker container boundaries
- ✅ MCP server can be scaled independently
- ✅ Standard HTTP debugging tools (curl, Postman)
- ✅ Can add authentication/authorization later
- ✅ Multiple clients can use same MCP server

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
- [ ] Document current API behavior for regression testing

#### Phase 0: Setup (1-2 hours)
- [ ] **Convert to uv (optional but recommended):**
  - [ ] Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - [ ] Initialize uv.lock: `uv lock`
  - [ ] Verify sync: `uv sync`
  - [ ] Test imports: `uv run python -c "import langgraph; print(langgraph.__version__)"`
- [ ] **Install MCP dependencies:**
  - [ ] Verify LangGraph >= 0.2.34: `uv pip list | grep langgraph`
  - [ ] Install `langchain-mcp-adapters`: `uv add langchain-mcp-adapters`
- [ ] **Copy MCP server:**
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
- [ ] Test tools load: `uv run python -c "from turtleapp.src.core.mcp.tools import get_qbittorrent_tools; print(len(get_qbittorrent_tools()))"`

#### Phase 3: Remove ALL Legacy/Redundant Code (1-2 hours)
- [ ] **Delete files:**
  - [ ] Delete `turtleapp/src/core/tools/torrent_tools.py` entirely
  - [ ] Delete `turtleapp/tests/test_torrent.py` entirely
- [ ] **Update prompts:**
  - [ ] Delete `TORRENT_MANAGER_PROMPT` from `turtleapp/src/core/prompts/agents.py` (lines 63-101)
  - [ ] Remove `TORRENT_MANAGER_PROMPT` import/export from `turtleapp/src/core/prompts/__init__.py`
- [ ] **Update tools:**
  - [ ] Remove torrent tool imports from `turtleapp/src/core/tools/__init__.py`
  - [ ] Remove torrent tool exports from `__all__` in `turtleapp/src/core/tools/__init__.py`
- [ ] **Update settings:**
  - [ ] Delete `QBittorrentSettings` class from `turtleapp/settings.py` (lines 66-79)
  - [ ] Add `MCPSettings` class to `turtleapp/settings.py`
  - [ ] Replace `qbittorrent: QBittorrentSettings` with `mcp: MCPSettings` in `Settings` class
- [ ] **Verify cleanup:**
  - [ ] Run grep to verify no qBittorrent references remain in main app
  - [ ] Run grep to verify no torrent_tools imports remain
  - [ ] Verify ~300-400 lines of code deleted
- [ ] **Update environment variables:**
  - [ ] Update `.env.example` with MCP HTTP transport env vars
  - [ ] Update local `.env` with new env var names

#### Phase 4: Testing (4-5 hours)
- [ ] Create `test_mcp_integration.py` with HTTP tests
- [ ] Create `test_agent_mcp.py`
- [ ] Create `test_graph_mcp.py`
- [ ] Start MCP HTTP server: `cd packages/qbittorrent-mcp && uv run fastmcp run mcp_qbittorrent.server:mcp --transport http`
- [ ] Run unit tests: `uv run pytest -m "not expensive" -v`
- [ ] Run integration tests: `uv run pytest -m expensive -v`
- [ ] Test API endpoints: `curl -X POST http://localhost:8000/chat -d '{"message":"search for ubuntu"}'`

#### Phase 5: Docker (2-3 hours)
- [ ] Update `build/docker-compose.yml` with separate MCP container
- [ ] Update `build/Dockerfile` (use uv, no Poetry, no MCP server code)
- [ ] Test Docker build: `cd build && docker-compose build`
- [ ] Test Docker run: `docker-compose up -d`
- [ ] Test MCP server health: `curl http://localhost:8001/mcp/tools`
- [ ] Test API in Docker: `curl http://localhost:8000/health`
- [ ] Test full workflow: `curl -X POST http://localhost:8000/chat -d '{"message":"what's downloading?"}'`

#### Phase 6: Documentation (1-2 hours)
- [ ] Update CLAUDE.md with MCP HTTP architecture
- [ ] Update README.md with HTTP transport details
- [ ] Document HTTP transport architecture
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
| 0 | Prerequisites & setup (including uv conversion) | 1-2 hours |
| 1 | MCP server HTTP setup | 2-3 hours |
| 2 | LangGraph integration (HTTP) | 3-4 hours |
| 3 | Remove ALL legacy/redundant code | 1-2 hours |
| 4 | Testing | 4-5 hours |
| 5 | Docker & deployment (with uv) | 2-3 hours |
| 6 | Documentation | 1-2 hours |
| **Total** | | **14-21 hours** |

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

### Functional Requirements
- [ ] All existing API endpoints work unchanged
- [ ] All tests pass (unit + integration)
- [ ] Docker Compose deployment works with 3 containers (app, mcp, qbittorrent)
- [ ] MCP server can be tested independently via HTTP: `curl http://localhost:8001/mcp/tools`
- [ ] Performance within 10% of legacy implementation
- [ ] No user-facing regressions

### Code Cleanup (Main App Must Be qBittorrent-Agnostic)
- [ ] **No `torrent_tools.py` file exists** - completely removed
- [ ] **No `test_torrent.py` file exists** - completely removed
- [ ] **No `TORRENT_MANAGER_PROMPT` exists** - completely removed
- [ ] **No `QBittorrentSettings` in main app settings** - replaced with `MCPSettings`
- [ ] **No direct qBittorrent HTTP calls anywhere** in main app code
- [ ] **No qBittorrent imports** in main app (only MCP URL config)
- [ ] **No torrent_tools imports** anywhere in main app
- [ ] **Grep verification passes** - no qBittorrent references in src/ or api/ (except MCP config)
- [ ] **~300-400 lines of legacy code deleted**

### Architecture Goals
- [ ] **Main app is agnostic to download backend** - could swap qBittorrent for Transmission without touching agent code
- [ ] **MCP server is reusable** - can be used by other apps via HTTP
- [ ] **Code is simpler and more maintainable** - less code, clearer separation
- [ ] **Agent uses MCP tool descriptions only** - no specialized prompts needed
- [ ] Documentation accurate and up-to-date

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

## Appendix: Production Deployment Options

### Kubernetes Deployment

For cloud-native deployments, use separate Deployments:

```yaml
# kubernetes/mcp-server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-qbittorrent
spec:
  template:
    spec:
      containers:
      - name: mcp-qbittorrent
        image: mcp-qbittorrent:latest
        ports:
        - containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-qbittorrent
spec:
  selector:
    app: mcp-qbittorrent
  ports:
  - port: 8000

# kubernetes/turtle-app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: turtle-app
spec:
  template:
    spec:
      containers:
      - name: turtle-app
        image: turtle-app:latest
        env:
        - name: TURTLEAPP_MCP_QBITTORRENT_URL
          value: http://mcp-qbittorrent:8000/mcp
```

### Scaling Considerations

- **MCP server**: Can be horizontally scaled with load balancer
- **Main app**: Stateless, can scale independently
- **Communication**: HTTP allows standard cloud load balancing
