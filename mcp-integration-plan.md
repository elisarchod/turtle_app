# Turtle App MCP Integration Plan

## Executive Summary

This plan migrates Turtle App to leverage **LangGraph's native MCP support** (v0.2.34+), replacing direct qBittorrent HTTP calls with a clean MCP-based architecture. The migration **completely removes** legacy torrent code and uses MCP tools directly, with no custom wrappers needed.

### Key Features
- ✅ **LangGraph native MCP support** - No custom MCP client wrappers needed
- ✅ **Direct tool binding** - MCP tools automatically converted to LangChain tools via `mcp_client.as_tool()`
- ✅ **Clean architecture** - Complete removal of legacy qBittorrent HTTP code
- ✅ **Better performance** - Persistent MCP connections managed by LangGraph
- ✅ **Less maintenance** - Leverage battle-tested LangGraph MCP client
- ✅ **LLM abstraction** - LLM never sees "qBittorrent" or "torrent" in prompts, only generic "movie download" concepts

## Architecture Overview

### Current (Monolithic)
```
User → FastAPI → LangGraph Supervisor
                       ↓
              Torrent Agent (torrent_tools.py)
                       ↓
              Direct qBittorrent HTTP calls
```

### Target (MCP-Native)
```
User → FastAPI → LangGraph Supervisor
                       ↓
         "Download Manager Agent" (user-facing abstraction)
                       ↓
              MCP Tools (qb_search_torrents, qb_list_torrents, etc.)
                       ↓
              LangGraph MCP Client (built-in)
                       ↓
              MCP Server (subprocess/stdio)
                       ↓
              qBittorrent API (implementation detail)
```

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

## Migration Strategy

### Phase 0: Prerequisites & Setup

**Duration: 1 hour**

#### 0.1 Verify LangGraph Version
```bash
cd /home/pie/git/turtle_app
poetry show langgraph | grep "version"
# Must be >= 0.2.34 for native MCP support
```

If upgrade needed:
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
git checkout -b feat/mcp-native-integration
```

---

### Phase 1: MCP Server Setup

**Duration: 2 hours**

#### 1.1 Update MCP Server Configuration

**File: `packages/qbittorrent-mcp/src/mcp_qbittorrent/config.py`**

Changes:
- Update env prefix from `QB_MCP_` to `TURTLEAPP_QB_`
- Add turtle app specific logging

```python
class Settings(BaseSettings):
    qbittorrent_url: str
    qbittorrent_username: str
    qbittorrent_password: str
    request_timeout: int = 30
    log_level: str = "INFO"

    class Config:
        env_prefix = "TURTLEAPP_QB_"  # Changed from QB_MCP_
```

#### 1.2 Install MCP Server in Dev Mode

```bash
cd packages/qbittorrent-mcp
uv sync --dev

# Test server runs
uv run mcp-qbittorrent
# Should start without errors (Ctrl+C to stop)
```

#### 1.3 Update Root pyproject.toml

**File: `pyproject.toml`** (root)

Add workspace configuration:
```toml
[tool.poetry]
name = "turtleapp-monorepo"
version = "0.1.0"
description = "Turtle App - Multi-agent home theater assistant"

[tool.poetry.dependencies]
python = "^3.11"

# Main app dependencies (existing)
# ... keep all existing dependencies ...

# NEW: MCP server as local dependency
turtleapp-qbittorrent-mcp = {path = "packages/qbittorrent-mcp", develop = true}
```

---

### Phase 2: LangGraph Native MCP Integration

**Duration: 3-4 hours**

This is the core migration - replacing custom tools with MCP-native tools.

#### 2.1 Create MCP Configuration Module

**File: `turtleapp/src/core/mcp/config.py`** (NEW)

```python
"""MCP server configuration for LangGraph native integration."""

from typing import Dict, Any
from pydantic import BaseModel
from turtleapp.settings import settings


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection."""
    command: str
    args: list[str]
    env: Dict[str, str]


def get_qbittorrent_mcp_config() -> MCPServerConfig:
    """Get qBittorrent MCP server configuration for LangGraph.

    Returns configuration for stdio-based MCP server subprocess.
    LangGraph will handle the client lifecycle and connection pooling.
    """
    return MCPServerConfig(
        command="uv",
        args=["run", "mcp-qbittorrent"],
        env={
            # Pass through environment variables for MCP server
            "TURTLEAPP_QB_QBITTORRENT_URL": settings.qbittorrent.host,
            "TURTLEAPP_QB_QBITTORRENT_USERNAME": settings.qbittorrent.credentials["username"],
            "TURTLEAPP_QB_QBITTORRENT_PASSWORD": settings.qbittorrent.credentials["password"],
        }
    )
```

**Rationale**: Centralized config makes it easy to add more MCP servers later (Plex, Sonarr, etc.)

#### 2.2 Create MCP Tools Loader

**File: `turtleapp/src/core/mcp/tools.py`** (NEW)

This is the **ONLY** integration code needed - LangGraph does the rest!

```python
"""MCP tools loader using LangGraph native MCP support."""

import asyncio
from typing import List
from langchain_core.tools import BaseTool
from langgraph.prebuilt.mcp import get_mcp_client, ToolSpec

from turtleapp.src.core.mcp.config import get_qbittorrent_mcp_config


# Cache for MCP tools (loaded once at startup)
_mcp_tools_cache: List[BaseTool] = None


async def _load_mcp_tools() -> List[BaseTool]:
    """Load tools from qBittorrent MCP server.

    Uses LangGraph's native MCP client to:
    1. Start MCP server subprocess (stdio communication)
    2. Initialize MCP session
    3. List available tools
    4. Convert MCP tools to LangChain tools

    Returns:
        List of LangChain BaseTool instances wrapping MCP tools
    """
    config = get_qbittorrent_mcp_config()

    # LangGraph native MCP client - handles all protocol details
    mcp_client = get_mcp_client(
        command=config.command,
        args=config.args,
        env=config.env
    )

    # Get tools from MCP server (returns LangChain-compatible tools)
    tools = await mcp_client.list_tools()

    # Convert MCP tool specs to LangChain tools
    langchain_tools = []
    for tool_spec in tools:
        langchain_tool = mcp_client.as_tool(tool_spec)
        langchain_tools.append(langchain_tool)

    return langchain_tools


def get_qbittorrent_tools() -> List[BaseTool]:
    """Get qBittorrent MCP tools (cached, synchronous).

    Loads tools once at module import time and caches them.
    The MCP server subprocess is started by LangGraph and reused
    across all tool invocations for performance.

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


# Optionally expose individual tools by name for convenience
def get_tool_by_name(tool_name: str) -> BaseTool:
    """Get specific MCP tool by name."""
    tools = get_qbittorrent_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    raise ValueError(f"Tool {tool_name} not found in MCP server")


# Export commonly used tools
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
- **No wrapper classes needed** - LangGraph's `mcp_client.as_tool()` handles conversion
- **Subprocess managed by LangGraph** - We just provide command/args
- **Connection pooling automatic** - LangGraph reuses the MCP session
- **Tools are cached** - Loaded once at startup, not per-request

#### 2.3 Update Agent Configuration

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

# Download manager - NOW USES MCP TOOLS
torrent_agent = ToolAgent(
    [
        get_torrent_search_tool(),      # qb_search_torrents
        get_torrent_status_tool(),      # qb_list_torrents
        get_torrent_add_tool(),         # qb_add_torrent
        get_torrent_control_tool()      # qb_control_torrent
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
- Update `torrent_agent` to use 4 MCP tools instead of 2 legacy tools
- All other agents unchanged

#### 2.4 Update Agent Prompt (Keep Tool Names Abstract)

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

**Rationale:**
The MCP server already has excellent tool descriptions (see `/home/pie/git/mcp-qbittorrent/src/mcp_qbittorrent/tools/qbittorrent_tools.py`). LangGraph will automatically pass these to the LLM via the `{tools}` template variable. We don't need to duplicate them in the prompt - just guide the agent's reasoning approach.

#### 2.5 (Optional) Rename MCP Tools for Better Abstraction

**File: `packages/qbittorrent-mcp/src/mcp_qbittorrent/tools/qbittorrent_tools.py`**

If you want to completely hide qBittorrent from the LLM, you can rename the MCP tools:

```python
# BEFORE:
@mcp.tool()
async def qb_search_torrents(...):
    """Search for torrents using qBittorrent's built-in search plugins."""

@mcp.tool()
async def qb_list_torrents(...):
    """List all torrents with optional filtering."""

@mcp.tool()
async def qb_add_torrent(...):
    """Add a torrent by URL or magnet link."""

@mcp.tool()
async def qb_control_torrent(...):
    """Control a torrent: pause, resume, or delete."""

# AFTER (optional renaming):
@mcp.tool()
async def search_movies(...):
    """Search for available movies across configured sources."""

@mcp.tool()
async def list_downloads(...):
    """List current downloads with optional filtering by status."""

@mcp.tool()
async def add_download(...):
    """Add a movie to the download queue."""

@mcp.tool()
async def control_download(...):
    """Control a download: pause, resume, or delete."""
```

**Decision:**
- **Keep `qb_*` names (recommended)**: Maintains consistency with MCP server source, easier to debug
- **Rename to abstract names**: Better abstraction but requires maintaining a fork of mcp-qbittorrent

**Recommendation**: Keep the `qb_*` names. The tool descriptions already abstract away implementation details, and the agent prompt avoids mentioning qBittorrent. The LLM will understand these are download management tools from context.

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
    """MCP server configuration."""
    qbittorrent_server_path: str = "packages/qbittorrent-mcp"
    qbittorrent_command: list[str] = ["uv", "run", "mcp-qbittorrent"]

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
- Main app only needs to know how to start MCP server subprocess
- Cleaner separation of concerns

#### 3.4 Update MCP Config to Use Environment Variables

**File: `turtleapp/src/core/mcp/config.py`**

Since we removed qBittorrent settings from main app, pass them as env vars to MCP server:

```python
"""MCP server configuration for LangGraph native integration."""

import os
from typing import Dict, Any
from pydantic import BaseModel
from turtleapp.settings import settings


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection."""
    command: str
    args: list[str]
    env: Dict[str, str]


def get_qbittorrent_mcp_config() -> MCPServerConfig:
    """Get qBittorrent MCP server configuration for LangGraph.

    The MCP server reads its own configuration from environment variables
    with TURTLEAPP_QB_ prefix. We pass through the host environment or
    use defaults for Docker.
    """
    return MCPServerConfig(
        command="uv",
        args=["run", "mcp-qbittorrent"],
        env={
            # Pass through environment variables for MCP server
            # These should be set in .env or docker-compose.yml
            "TURTLEAPP_QB_QBITTORRENT_URL": os.getenv(
                "TURTLEAPP_QB_QBITTORRENT_URL",
                "http://qbittorrent:15080"  # Docker default
            ),
            "TURTLEAPP_QB_QBITTORRENT_USERNAME": os.getenv(
                "TURTLEAPP_QB_QBITTORRENT_USERNAME",
                "admin"
            ),
            "TURTLEAPP_QB_QBITTORRENT_PASSWORD": os.getenv(
                "TURTLEAPP_QB_QBITTORRENT_PASSWORD",
                "adminadmin"
            ),
        }
    )
```

**Key Changes:**
- Read qBittorrent config from environment directly
- Don't depend on `settings.qbittorrent` (deleted)
- Provide Docker defaults for convenience

#### 3.5 Update Environment Variables

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
# MCP Server Configuration
# ============================================
# qBittorrent MCP Server
TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin

# REMOVED: Old qBittorrent settings (no longer needed)
# QBITTORRENT_HOST=...
# QBITTORRENT_USERNAME=...
# QBITTORRENT_PASSWORD=...
```

**Migration Note:**
- Old env vars (`QBITTORRENT_*`) → New env vars (`TURTLEAPP_QB_*`)
- This matches the MCP server's expected env prefix

---

### Phase 4: Testing Strategy

**Duration: 4-5 hours**

#### 4.1 Unit Tests for MCP Integration

**File: `turtleapp/tests/test_mcp_integration.py`** (NEW)

```python
"""Test MCP integration with LangGraph."""

import pytest
from turtleapp.src.core.mcp.tools import (
    get_qbittorrent_tools,
    get_torrent_search_tool,
    get_tool_by_name
)


def test_mcp_tools_load():
    """Test MCP tools can be loaded."""
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
@pytest.mark.expensive  # Requires running MCP server
async def test_mcp_search_tool_execution():
    """Test MCP search tool can execute."""
    search_tool = get_torrent_search_tool()

    # Test search with legal content
    result = await search_tool.ainvoke({"query": "Ubuntu 22.04", "limit": 5})

    assert "results" in result or "error" in result
    # Should return either results or error (if search plugins not configured)


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_mcp_list_tool_execution():
    """Test MCP list tool can execute."""
    from turtleapp.src.core.mcp.tools import get_torrent_status_tool

    status_tool = get_torrent_status_tool()
    result = await status_tool.ainvoke({"filter": "all"})

    assert "torrents" in result or "count" in result
```

#### 4.2 Integration Test with Agent

**File: `turtleapp/tests/test_agent_mcp.py`** (NEW)

```python
"""Test agents using MCP tools."""

import pytest
from turtleapp.src.core.nodes.agents import torrent_agent
from langgraph.graph import MessagesState


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_torrent_agent_with_mcp():
    """Test torrent agent can use MCP tools."""

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
"""Test full workflow with MCP integration."""

import pytest
from turtleapp.src.workflows.graph import create_movie_workflow


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_workflow_with_mcp_search():
    """Test full workflow handles MCP-based search."""

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
    """Test workflow handles download status check."""

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
# 1. Test MCP tools load correctly
poetry run pytest turtleapp/tests/test_mcp_integration.py::test_mcp_tools_load -v

# 2. Test individual tool execution (requires MCP server)
poetry run pytest turtleapp/tests/test_mcp_integration.py -m expensive -v

# 3. Test agent with MCP tools
poetry run pytest turtleapp/tests/test_agent_mcp.py -m expensive -v

# 4. Test full workflow
poetry run pytest turtleapp/tests/test_graph_mcp.py -m expensive -v

# 5. Run all tests (skip expensive by default)
poetry run pytest -m "not expensive" -v

# 6. Run full test suite including MCP
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

  # Existing NAS service (unchanged)
  nas:
    image: dperson/samba
    # ... existing config ...

  # UPDATED: Turtle App with MCP
  turtle-app:
    build:
      context: ..
      dockerfile: build/Dockerfile
    container_name: turtleapp
    environment:
      # qBittorrent settings (for MCP server env vars)
      - TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
      - TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
      - TURTLEAPP_QB_QBITTORRENT_PASSWORD=${QB_PASSWORD:-adminadmin}

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
      - qbittorrent
      - nas
    restart: unless-stopped
    volumes:
      # Mount MCP server code
      - ../packages/qbittorrent-mcp:/app/packages/qbittorrent-mcp:ro
```

**Key Changes:**
- No separate MCP server container needed (subprocess model)
- Mount MCP server code as volume
- Pass qBittorrent credentials as env vars for MCP server
- Simplified vs v1 plan (no network complexity)

#### 5.2 Update Dockerfile

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

# Install uv (for running MCP server subprocess)
RUN pip install uv

# Copy application code
COPY turtleapp/ ./turtleapp/
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install poetry

# Install dependencies (including MCP server as local dep)
COPY packages/qbittorrent-mcp ./packages/qbittorrent-mcp
RUN poetry install --no-dev

# Expose API port
EXPOSE 8000

# Run FastAPI server
CMD ["poetry", "run", "uvicorn", "turtleapp.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Changes:**
- Install `uv` for running MCP server subprocess
- Copy MCP server code into container
- Install MCP server as local dependency via Poetry

---

### Phase 6: Documentation Updates

**Duration: 1-2 hours**

#### 6.1 Update CLAUDE.md

**File: `CLAUDE.md`**

Add MCP architecture section:

```markdown
## MCP Integration

### Architecture

Turtle App uses **LangGraph's native MCP support** for qBittorrent integration:

```
LangGraph Supervisor
       ↓
Torrent Agent (LangChain tools)
       ↓
LangGraph MCP Client (built-in)
       ↓
MCP Server (subprocess/stdio)
       ↓
qBittorrent Web API
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

### Adding New MCP Tools

1. Add tool to MCP server: `packages/qbittorrent-mcp/src/mcp_qbittorrent/tools/qbittorrent_tools.py`
2. Reload tools: Restart app (tools loaded at startup)
3. Update agent: Add tool to agent in `turtleapp/src/core/nodes/agents.py`
4. Update prompt: Document tool in `turtleapp/src/core/prompts/agents.py`

### MCP Server Development

```bash
# Run MCP server standalone
cd packages/qbittorrent-mcp
uv run mcp-qbittorrent

# Test MCP server
cd packages/qbittorrent-mcp
uv run pytest -v

# Install MCP server changes in main app
cd ../..
poetry install  # Reinstalls local MCP server dependency
```

### Adding More MCP Servers

To add additional MCP servers (Plex, Sonarr, etc.):

1. Add server config to `turtleapp/src/core/mcp/config.py`
2. Create tool loader in `turtleapp/src/core/mcp/tools.py`
3. Create agent using new tools in `turtleapp/src/core/nodes/agents.py`
4. Add agent to workflow in `turtleapp/src/workflows/graph.py`
```

#### 6.2 Update README.md

**File: `README.md`**

Add MCP section to architecture overview:

```markdown
## Architecture

Turtle App uses a **multi-agent architecture** powered by LangGraph and MCP (Model Context Protocol):

### MCP Integration

The app leverages **LangGraph's native MCP support** for modular, reusable integrations:

- **qBittorrent MCP Server**: Standalone server for torrent management
  - Location: `packages/qbittorrent-mcp/`
  - Protocol: MCP via stdio (subprocess)
  - Tools: Search, list, add, control torrents

### Benefits of MCP Architecture

- ✅ **Modular**: MCP servers can be reused in other projects
- ✅ **Maintainable**: Clear separation between app logic and external services
- ✅ **Testable**: MCP servers can be tested independently
- ✅ **Scalable**: Easy to add new MCP servers (Plex, Sonarr, Radarr, etc.)
```

---

### Phase 7: Migration Checklist

#### Pre-Migration
- [ ] Backup current codebase: `git branch backup-pre-mcp-$(date +%Y%m%d)`
- [ ] Create feature branch: `git checkout -b feat/mcp-native-integration`
- [ ] Verify LangGraph >= 0.2.34: `poetry show langgraph`
- [ ] Document current API behavior for regression testing

#### Phase 0: Setup (1 hour)
- [ ] Copy MCP server to `packages/qbittorrent-mcp/`
- [ ] Update MCP server package name
- [ ] Install MCP server in dev mode: `cd packages/qbittorrent-mcp && uv sync`
- [ ] Test MCP server runs: `uv run mcp-qbittorrent`

#### Phase 1: MCP Server Setup (2 hours)
- [ ] Update MCP server config.py env prefix
- [ ] Update root pyproject.toml with workspace
- [ ] Install MCP server as local dependency: `poetry install`

#### Phase 2: LangGraph Integration (3-4 hours)
- [ ] Create `turtleapp/src/core/mcp/config.py`
- [ ] Create `turtleapp/src/core/mcp/tools.py`
- [ ] Update `turtleapp/src/core/nodes/agents.py`
- [ ] Update `turtleapp/src/core/prompts/agents.py`
- [ ] Test tools load: `poetry run python -c "from turtleapp.src.core.mcp.tools import get_qbittorrent_tools; print(len(get_qbittorrent_tools()))"`

#### Phase 3: Remove Legacy Code (1 hour)
- [ ] Delete `turtleapp/src/core/tools/torrent_tools.py` entirely
- [ ] Remove torrent tool exports from `turtleapp/src/core/tools/__init__.py`
- [ ] Remove `QBittorrentSettings` from `turtleapp/settings.py`
- [ ] Add `MCPSettings` to `turtleapp/settings.py`
- [ ] Update MCP config to read env vars directly
- [ ] Update `.env.example` with new `TURTLEAPP_QB_*` env vars
- [ ] Update local `.env` with new env var names

#### Phase 4: Testing (4-5 hours)
- [ ] Create `test_mcp_integration.py`
- [ ] Create `test_agent_mcp.py`
- [ ] Create `test_graph_mcp.py`
- [ ] Run unit tests: `poetry run pytest -m "not expensive" -v`
- [ ] Run integration tests: `poetry run pytest -m expensive -v`
- [ ] Test API endpoints: `curl -X POST http://localhost:8000/chat -d '{"message":"search for ubuntu"}'`

#### Phase 5: Docker (2-3 hours)
- [ ] Update `build/docker-compose.yml`
- [ ] Update `build/Dockerfile`
- [ ] Test Docker build: `docker-compose build`
- [ ] Test Docker run: `docker-compose up -d`
- [ ] Test API in Docker: `curl http://localhost:8000/health`

#### Phase 6: Documentation (1-2 hours)
- [ ] Update CLAUDE.md with MCP architecture
- [ ] Update README.md with MCP overview
- [ ] Create migration notes
- [ ] Document rollback procedure

#### Post-Migration Validation
- [ ] All existing tests pass
- [ ] API endpoints work unchanged
- [ ] Download search works via MCP
- [ ] Download status works via MCP
- [ ] Docker deployment works
- [ ] Performance comparable to legacy
- [ ] No regressions in user-facing features

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 0 | Prerequisites & setup | 1 hour |
| 1 | MCP server setup | 2 hours |
| 2 | LangGraph integration | 3-4 hours |
| 3 | Remove legacy code | 1 hour |
| 4 | Testing | 4-5 hours |
| 5 | Docker & deployment | 2-3 hours |
| 6 | Documentation | 1-2 hours |
| **Total** | | **14-18 hours** |

---

## Risks & Mitigations

### Risk 1: LangGraph MCP API Changes
**Impact**: High - Core integration could break
**Likelihood**: Low - LangGraph MCP is stable (v0.2.34+)
**Mitigation**: Pin LangGraph version, monitor changelog, have rollback plan

### Risk 2: MCP Server Subprocess Failure
**Impact**: Medium - Tools unavailable, graceful degradation needed
**Likelihood**: Low - Subprocess is battle-tested pattern
**Mitigation**: Add health checks, error messages, fallback to error state

### Risk 3: Tool Schema Mismatch
**Impact**: Medium - Agent can't use tools correctly
**Likelihood**: Low - MCP spec is well-defined
**Mitigation**: Add schema validation tests, clear error messages

### Risk 4: Performance Overhead
**Impact**: Low - Slight latency from subprocess communication
**Likelihood**: Medium - Stdio has overhead vs direct HTTP
**Mitigation**: Benchmark vs legacy, optimize if needed, connection pooling

---

## Success Criteria

- [ ] All existing API endpoints work unchanged
- [ ] All tests pass (unit + integration)
- [ ] **No `torrent_tools.py` file exists** - completely removed
- [ ] **No `QBittorrentSettings` in main app settings** - removed
- [ ] **No direct qBittorrent HTTP calls anywhere** in main app code
- [ ] **No qBittorrent imports** in main app (except MCP config passing env vars)
- [ ] MCP server can be tested independently
- [ ] Docker Compose deployment works
- [ ] Documentation accurate and up-to-date
- [ ] Performance within 10% of legacy implementation
- [ ] No user-facing regressions
- [ ] Code is simpler and more maintainable than v1
- [ ] **Main app is agnostic to download backend** - could swap qBittorrent for Transmission without touching agent code

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
   - Revert `docker-compose.yml`
   - Revert `Dockerfile`

4. **Redeploy**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

**Recovery Time Objective (RTO)**: < 15 minutes

---

## Future Enhancements

After successful migration:

1. **Add More MCP Servers**:
   - Plex MCP server for library management
   - Sonarr/Radarr MCP servers for content discovery
   - Jellyfin MCP server as alternative to Plex

2. **Publish MCP Servers**:
   - Package qBittorrent MCP as standalone npm/pip package
   - Add to MCP server registry
   - Open source for community contributions

3. **Advanced Features**:
   - MCP server health monitoring dashboard
   - Multiple MCP server load balancing
   - MCP server hot-reload during development
   - Streaming responses from MCP tools

4. **Observability**:
   - LangSmith tracing for MCP calls
   - MCP latency metrics
   - Error rate monitoring
   - MCP server logs aggregation

---

## References

- [LangGraph MCP Documentation](https://langchain-ai.github.io/langgraph/how-tos/mcp/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [qBittorrent Web API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1))
