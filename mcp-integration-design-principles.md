# MCP Integration Design Principles

## Overview

This document outlines the key design principles for integrating MCP (Model Context Protocol) into Turtle App while maintaining proper abstraction layers between user intent and implementation details.

## Core Principle: Separation of Concerns

**The LLM should reason about WHAT to do (user intent), not HOW it's done (implementation).**

```
User Intent Layer:     "Find movies", "Check downloads", "Manage queue"
         ↓
Agent Reasoning Layer: "Search for movies", "List downloads", "Control downloads"
         ↓
MCP Tool Layer:        qb_search_torrents, qb_list_torrents, qb_control_torrent
         ↓
Implementation Layer:  qBittorrent API, HTTP calls, authentication
```

## Design Decisions

### 1. Keep MCP Tool Names Technical (`qb_*`)

**Decision**: Keep tool names as `qb_search_torrents`, `qb_list_torrents`, etc. (from mcp-qbittorrent repo)

**Rationale**:
- ✅ Maintains consistency with upstream MCP server source
- ✅ Easier to debug and trace issues (tool names match MCP server logs)
- ✅ Avoids maintaining a fork of mcp-qbittorrent
- ✅ Tool names are just identifiers - descriptions matter more to LLM
- ✅ Allows using the official mcp-qbittorrent package as-is

**Alternatives Considered**:
- ❌ Rename to `search_movies`, `list_downloads` - requires fork, maintenance burden
- ❌ Create wrapper tools with different names - adds complexity, no benefit

### 2. Abstract Away Implementation in Agent Prompts

**Decision**: Agent prompts describe capabilities at the user-intent level, never mention implementation

**Example Prompt Language**:
```python
"""You are a movie download management expert.

Your capabilities:
- Search for movies across multiple sources
- Monitor download progress and status
- Manage download queue operations

Available Tools: {tools}  # LangChain auto-fills with tool descriptions

Focus on user intent: search, status, add, control operations.
Let the tools handle technical details transparently.
"""
```

**What to NEVER include in prompts**:
- ❌ "qBittorrent"
- ❌ "torrent" (use "download" instead)
- ❌ "magnet link" (use "download URL" or let tool description handle it)
- ❌ "seeders/leechers" (use "availability" or omit entirely)
- ❌ Specific tool names like "use qb_search_torrents" (let LLM choose from {tools})

**What to INCLUDE in prompts**:
- ✅ User-facing concepts: "movies", "downloads", "search", "status"
- ✅ High-level guidance: "search with title and year for best results"
- ✅ Reasoning patterns: "check status before searching for duplicates"
- ✅ Template variables: `{tools}`, `{tool_names}` (LangChain fills these)

### 3. Rely on MCP Tool Descriptions for LLM

**Decision**: Let MCP tool descriptions (written for LLMs) guide tool usage, not agent prompts

**Why**:
- The MCP server already has excellent tool descriptions
- LangGraph automatically passes tool descriptions to LLM via `{tools}` template variable
- Avoids duplication and sync issues between prompts and MCP server
- Allows updating tool behavior without changing agent prompts

**Example from mcp-qbittorrent**:
```python
@mcp.tool()
async def qb_search_torrents(
    query: str,
    category: str = "all",
    limit: int = 100
) -> SearchResponse:
    """Search for torrents using qBittorrent's built-in search plugins.

    Use this tool when the user wants to find torrents to download.

    Example uses:
    - "Search for Ubuntu 22.04 torrents"
    - "Find the latest Linux distributions"
    """
```

**What the LLM sees**:
- Tool name: `qb_search_torrents`
- Description: "Search for torrents using qBittorrent's built-in search plugins..."
- Parameters: `query` (str), `category` (str), `limit` (int)

**How the LLM understands it**:
- "This tool searches for things to download"
- "I should use it when user wants to find movies"
- "I need to provide a query string"

The LLM doesn't need to know about qBittorrent implementation - just that this tool searches for downloadable content.

### 4. Agent Naming Strategy

**Decision**: Name agents by capability/role, not by technology

**Examples**:
- ✅ `movies_download_manager` - describes what it does
- ✅ `download_manager_agent` - role-based naming
- ❌ `torrent_agent` - technology-specific naming
- ❌ `qbittorrent_agent` - implementation-specific naming

**Rationale**:
- User-facing names should describe functionality
- Makes it easier to swap implementations (qBittorrent → Transmission)
- More intuitive for understanding system architecture

### 5. Use LangGraph Native MCP Support

**Decision**: Use LangGraph's built-in `get_mcp_client()` instead of custom wrappers

**What we DON'T need**:
- ❌ Custom `QBittorrentMCPClient` class
- ❌ Custom `TorrentSearchTool` extending `BaseTool`
- ❌ Manual session management (connect/disconnect)
- ❌ Custom retry logic or error handling
- ❌ Tool schema mapping code

**What LangGraph provides**:
- ✅ MCP client with subprocess management
- ✅ Automatic tool schema conversion to LangChain tools
- ✅ Connection pooling and session reuse
- ✅ Built-in error handling and retries
- ✅ Stdio communication with MCP servers

**Code simplicity comparison**:
```python
# OLD (v1 plan): Custom wrapper - ~300 lines
class QBittorrentMCPClient:
    def __init__(self, server_command): ...
    async def connect(self): ...
    async def list_torrents(self): ...
    # ... manual protocol handling ...

class TorrentSearchTool(BaseTool):
    async def _arun(self, query): ...
    # ... manual wrapper ...

# NEW (v2 plan): LangGraph native - ~20 lines
mcp_client = get_mcp_client(command="uv", args=["run", "mcp-qbittorrent"])
tools = await mcp_client.list_tools()
langchain_tools = [mcp_client.as_tool(t) for t in tools]
```

## Implementation Checklist

When implementing MCP integration, ensure:

### ✅ Agent Prompts
- [ ] No mention of "qBittorrent" anywhere
- [ ] Use "download" instead of "torrent" in user-facing language
- [ ] Focus on user intent (search, status, manage)
- [ ] Let `{tools}` template variable handle tool descriptions
- [ ] Don't duplicate MCP tool descriptions in prompts

### ✅ Agent Configuration
- [ ] Agent name describes capability: `movies_download_manager`
- [ ] Tools passed as list: `[get_tool_by_name("qb_search_torrents"), ...]`
- [ ] No custom wrapper classes around MCP tools
- [ ] Use LangGraph's native MCP client

### ✅ MCP Server
- [ ] Keep tool names as `qb_*` (don't rename)
- [ ] Tool descriptions written for LLM consumption
- [ ] Tool descriptions focus on WHAT not HOW
- [ ] Return structured responses (Pydantic models)

### ✅ Testing
- [ ] Test that LLM successfully uses tools without explicit guidance
- [ ] Verify LLM doesn't mention "qBittorrent" in responses
- [ ] Check that tool descriptions are clear enough for LLM
- [ ] Test with various user intents (search, status, add, control)

## Example User Interaction

**User**: "Search for The Matrix 1999"

**Supervisor Agent**: Routes to `movies_download_manager` agent

**Download Manager Agent Reasoning**:
```
Thought: User wants to search for a specific movie.
I should use the search tool with the movie title and year.

Action: qb_search_torrents
Action Input: {"query": "The Matrix 1999", "category": "movies", "limit": 10}

Observation: Found 10 results including "The Matrix (1999) 1080p BluRay"...

Thought: Found relevant results. I should present them to the user.

Final Answer: I found several versions of The Matrix (1999) available:
1. The Matrix (1999) 1080p BluRay - 2.5GB
2. The Matrix (1999) 2160p 4K - 8.2GB
...
```

**Key Points**:
- Agent knows to use `qb_search_torrents` from tool descriptions
- Agent understands tool parameters from schema
- Agent presents results in user-friendly language (no "torrent" jargon)
- Implementation details (qBittorrent API) completely hidden

## Benefits of This Design

### For Development
- ✅ **Maintainability**: MCP server is independent, can be updated separately
- ✅ **Testability**: Test MCP server independently, test agent without MCP
- ✅ **Debuggability**: Clear separation of concerns, easy to trace issues
- ✅ **Reusability**: MCP server can be used in other projects

### For LLM Reasoning
- ✅ **Clarity**: LLM reasons about user intent, not implementation
- ✅ **Flexibility**: Can swap implementations without retraining
- ✅ **Robustness**: Tool descriptions guide behavior, not hardcoded prompts
- ✅ **Generalization**: Same reasoning works for different download backends

### For Users
- ✅ **Transparency**: System speaks in user terms ("downloads" not "torrents")
- ✅ **Simplicity**: User doesn't need to know about qBittorrent
- ✅ **Reliability**: Battle-tested MCP protocol and LangGraph integration

## Future Extensibility

This design makes it easy to:

1. **Add new MCP servers**: Plex, Sonarr, Radarr, Jellyfin
   - Just add new MCP config
   - Create new agent with MCP tools
   - No changes to existing agents

2. **Swap download backend**: qBittorrent → Transmission, Deluge
   - Implement new MCP server for Transmission
   - Update MCP config to point to new server
   - No changes to agent prompts or reasoning

3. **Support multiple backends**: Run both qBittorrent and Transmission
   - Add both MCP servers
   - Give agent tools from both servers
   - LLM chooses based on availability/preferences

4. **Add new capabilities**: RSS feeds, automatic downloads, quality profiles
   - Add new tools to MCP server
   - Agent automatically discovers via `list_tools()`
   - No prompt engineering needed

## Anti-Patterns to Avoid

### ❌ Leaking Implementation Details
```python
# BAD: Mentions qBittorrent in prompt
PROMPT = """You are a qBittorrent agent. Use qb_search_torrents to find torrents."""

# GOOD: Abstract capability description
PROMPT = """You are a download manager. Use available tools to search for movies."""
```

### ❌ Hardcoding Tool Usage
```python
# BAD: Tells LLM exactly which tool to use
PROMPT = """
When user asks to search, ALWAYS use qb_search_torrents.
When user asks for status, ALWAYS use qb_list_torrents.
"""

# GOOD: Let LLM choose based on tool descriptions
PROMPT = """
Available tools: {tools}
Choose appropriate tools based on user intent.
"""
```

### ❌ Creating Unnecessary Wrappers
```python
# BAD: Custom wrapper that just forwards to MCP
class MovieSearchTool(BaseTool):
    async def _arun(self, query):
        return await mcp_client.call_tool("qb_search_torrents", query)

# GOOD: Use MCP tool directly via LangGraph
tools = mcp_client.list_tools()
langchain_tools = [mcp_client.as_tool(t) for t in tools]
```

### ❌ Duplicating Tool Descriptions
```python
# BAD: Prompt repeats what MCP already provides
PROMPT = """
Tools:
- qb_search_torrents: Search for torrents with query and category
- qb_list_torrents: List torrents with optional filter
"""

# GOOD: Let LangChain template fill from MCP
PROMPT = """
Tools: {tools}
Tool names: {tool_names}
"""
```

## Conclusion

By keeping these principles in mind, we create a clean separation between:
- **User Intent** (what the user wants)
- **Agent Reasoning** (how to fulfill the intent)
- **Tool Interface** (what capabilities are available)
- **Implementation** (how capabilities work internally)

This makes the system more maintainable, extensible, and robust while keeping the LLM focused on high-level reasoning rather than implementation details.
