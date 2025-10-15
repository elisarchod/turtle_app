# Turtle App MCP Integration - Modern Migration Plan v2

## Executive Summary

This plan modernizes the Turtle App migration to leverage **LangGraph's native MCP support** (introduced in langgraph v0.2.34), eliminating the need for custom wrapper layers. The new architecture directly binds MCP tools as LangChain tools, dramatically simplifying the integration.

### Key Improvements Over v1
- ✅ **No custom MCP client wrappers** - LangGraph handles MCP communication natively
- ✅ **No LangChain tool wrappers** - Direct MCP tool binding via `mcp.get_tools()`
- ✅ **Simpler architecture** - Remove ~300 lines of unnecessary abstraction code
- ✅ **Better performance** - Persistent MCP connections managed by LangGraph
- ✅ **Less maintenance** - Leverage battle-tested LangGraph MCP client

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
              Torrent Agent (MCP tools)
                       ↓
              LangGraph MCP Client (built-in)
                       ↓
              MCP Server (subprocess/stdio)
                       ↓
              qBittorrent API
```

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

#### 2.4 Update Prompts for New Tool Names

**File: `turtleapp/src/core/prompts/agents.py`**

Update torrent manager prompt to reference new tool names:

```python
TORRENT_MANAGER_PROMPT = PromptTemplate.from_template("""
You are a specialized download manager agent with access to these tools:

**Available Tools:**
- qb_search_torrents: Search for torrents using natural language queries
  - Takes: query (movie title, year, keywords)
  - Returns: List of torrent results with seeders, size, magnet links

- qb_list_torrents: Check status of downloads in the queue
  - Takes: filter (optional: downloading/completed/paused/all)
  - Returns: List of torrents with progress, speed, ETA

- qb_add_torrent: Add a torrent to the download queue
  - Takes: url (magnet link or .torrent URL), category (optional)
  - Returns: Confirmation of added torrent

- qb_control_torrent: Control torrent (pause/resume/delete)
  - Takes: hash (torrent hash), action (pause/resume/delete)
  - Returns: Confirmation of action

**Your Role:**
Help users find and download movies. When users ask about downloads:
1. Use qb_list_torrents to check current download status
2. Use qb_search_torrents to find new content
3. Use qb_add_torrent to start downloads
4. Use qb_control_torrent to manage existing downloads

**Important:**
- Always search with specific movie titles and years for best results
- Check download status before searching for duplicates
- Provide clear, user-friendly responses (avoid technical jargon)
- Return control to supervisor after completing your task

{agent_scratchpad}

User request: {input}
""")
```

**Changes:**
- Updated tool names from `movie_search`/`movie_download_status` to `qb_search_torrents`/`qb_list_torrents`
- Added descriptions for all 4 MCP tools
- Kept user-friendly language (no "torrent" jargon)

---

### Phase 3: Remove Legacy Code

**Duration: 1 hour**

#### 3.1 Mark Legacy Tools as Deprecated

**File: `turtleapp/src/core/tools/torrent_tools.py`**

Add deprecation notice at top:
```python
"""
DEPRECATED: Legacy qBittorrent HTTP tools.

This module is replaced by MCP-based tools in:
    turtleapp/src/core/mcp/tools.py

These tools will be removed after successful MCP migration.
DO NOT USE IN NEW CODE.
"""
import warnings
warnings.warn(
    "torrent_tools.py is deprecated. Use turtleapp.src.core.mcp.tools instead",
    DeprecationWarning,
    stacklevel=2
)

# ... rest of file unchanged for now ...
```

#### 3.2 Remove Legacy Settings

**File: `turtleapp/settings.py`**

Update settings to move qBittorrent config responsibility to MCP server:

```python
# BEFORE: (keep for now during migration)
class QBittorrentSettings(BaseModel):
    host: str
    credentials: dict

# NEW: Add MCP config
class MCPSettings(BaseModel):
    """MCP server paths and commands."""
    qbittorrent_server_path: str = "packages/qbittorrent-mcp"

class Settings(BaseSettings):
    # ... existing settings ...

    # Keep for MCP env vars (used in mcp/config.py)
    qbittorrent: QBittorrentSettings

    # NEW
    mcp: MCPSettings = MCPSettings()
```

**Note:** We keep qBittorrent settings temporarily since MCP config needs them. After migration stabilizes, these can move to MCP server's `.env` only.

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

The download manager agent uses these MCP tools from the qBittorrent server:

- **qb_search_torrents**: Search for torrents
- **qb_list_torrents**: List/filter torrents by status
- **qb_add_torrent**: Add torrent by URL/magnet
- **qb_control_torrent**: Pause/resume/delete torrents
- **qb_torrent_info**: Get detailed torrent info
- **qb_get_preferences**: Get qBittorrent settings

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
- [ ] Mark `torrent_tools.py` as deprecated
- [ ] Add deprecation warnings
- [ ] Update settings for MCP config

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

## Comparison: v1 vs v2 Plan

| Aspect | v1 (Custom Wrappers) | v2 (LangGraph Native) |
|--------|---------------------|----------------------|
| **MCP Client** | Custom `QBittorrentMCPClient` class | LangGraph built-in `get_mcp_client()` |
| **Tool Wrappers** | Custom `TorrentSearchTool` classes extending `BaseTool` | Direct MCP tool binding via `mcp_client.as_tool()` |
| **Lines of Code** | ~300 lines of wrapper code | ~100 lines of config/loader code |
| **Maintenance** | Custom protocol handling, error handling | Leverage LangGraph's battle-tested MCP |
| **Performance** | Manual connection management | Automatic connection pooling |
| **Session Handling** | Manual `connect()`/`disconnect()` | Managed by LangGraph |
| **Error Handling** | Custom retry logic | Built-in MCP error handling |
| **Tool Schema** | Manual TypedDict mapping | Automatic from MCP tool spec |

**Key Simplifications in v2:**
- ❌ No `QBittorrentMCPClient` class - use `get_mcp_client()`
- ❌ No `TorrentSearchTool`/`TorrentStatusTool` wrappers - use `mcp_client.as_tool()`
- ❌ No `get_mcp_client()` singleton factory - LangGraph handles it
- ❌ No custom session management - LangGraph handles it
- ✅ Just `get_qbittorrent_tools()` loader function

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

**Comparison:** v1 plan estimated 20-30 hours vs v2 at 14-18 hours (30-40% faster)

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
- [ ] No direct qBittorrent HTTP calls in graph code
- [ ] MCP server can be tested independently
- [ ] Docker Compose deployment works
- [ ] Documentation accurate and up-to-date
- [ ] Performance within 10% of legacy implementation
- [ ] No user-facing regressions
- [ ] Code is simpler and more maintainable than v1

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
