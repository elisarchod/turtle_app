# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Turtle App is an AI-powered home theater assistant that uses a multi-agent supervisor architecture built on LangGraph. The system combines LLMs, RAG (Retrieval Augmented Generation), and MCP (Model Context Protocol) to manage movie collections, provide recommendations, and handle downloads.

**Key Architecture**: Supervisor agent (Claude Sonnet) routes requests to specialized agents (Claude Haiku) that use specific tools. The download manager integrates via MCP server using HTTP transport.

## Development Commands

### Environment Setup
```bash
# Install dependencies (requires uv)
uv sync

# Setup environment variables
cp .env.example .env
# Edit .env with required API keys:
# - CLAUDE_API (Anthropic)
# - OPENAI_API_KEY (embeddings)
# - PINECONE_API_KEY (vector DB)
# - LANGCHAIN_API_KEY (optional tracing)
```

### Running the Application

```bash
# Start API server locally
uv run uvicorn turtleapp.api.routes.endpoints:app --host 0.0.0.0 --port 8000

# Alternative: use entry point
uv run turtle-app-server

# Docker deployment (recommended)
cd build
docker-compose up -d

# View logs
docker-compose logs -f turtle-app-api
docker-compose logs -f mcp-qbittorrent
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=turtleapp

# Run tests in parallel
uv run pytest -n auto

# Skip slow/expensive tests
uv run pytest -m "not slow"
uv run pytest -m "not expensive"

# Run specific test files
uv run pytest turtleapp/tests/test_api_endpoints.py
uv run pytest turtleapp/tests/test_mcp_integration.py
uv run pytest turtleapp/tests/test_graph_workflow.py
```

### Data Pipeline

```bash
# Upload movie data to Pinecone vector store
uv run python turtleapp/data_pipeline/vector_store/upload_script.py

# Data source: turtleapp/data_pipeline/data/processed/wiki_movie_plots_cleaned.csv
# Default: 300 documents, configurable in MovieDataLoader
```

### Interactive Development

```bash
# Test workflow directly
python turtleapp/src/workflows/graph.py

# Use in Python REPL
from turtleapp.src.workflows.graph import run
response = run("Tell me about Terminator 2")
```

## Architecture

### Multi-Agent System Structure

```
User Request
    ↓
Supervisor Agent (Claude Sonnet)
    ↓
Routes to → Movie Retriever Agent    [Tool: Pinecone Vector Search]
         → Download Manager Agent    [Tools: MCP qBittorrent Tools]
         → Library Manager Agent     [Tool: SMB/CIFS Scanner]
    ↓
Returns to Supervisor → Response to User
```

### Key Components

1. **Supervisor Node** (`turtleapp/src/core/nodes/supervisor.py`)
   - Uses Claude Sonnet for routing decisions
   - Returns `Command(goto=agent_name)` to route requests
   - Routes to END when conversation is complete
   - Uses structured output with `Router` TypedDict

2. **ToolAgent Class** (`turtleapp/src/core/nodes/agents.py`)
   - Wraps LangChain ReAct agents with tools
   - Uses `AgentExecutor` with `handle_parsing_errors=True`, `max_iterations=3`
   - Returns `Command(update=messages, goto=SUPERVISOR_NODE)`
   - All agents return to supervisor after execution

3. **Workflow Graph** (`turtleapp/src/workflows/graph.py`)
   - `WorkflowGraph` class compiles LangGraph StateGraph with MemorySaver
   - `invoke()` method handles thread management and config structure
   - Thread IDs are auto-generated if not provided
   - Global instance: `movie_workflow_agent`

4. **MCP Integration** (`turtleapp/src/core/mcp/tools.py`)
   - Uses `MultiServerMCPClient` with HTTP transport (`streamable_http`)
   - `MCPClientManager` singleton handles connection lifecycle
   - Tools loaded lazily on first access via `get_qbittorrent_tools()`
   - Cleanup handled in FastAPI lifespan

5. **API Layer** (`turtleapp/api/routes/endpoints.py`)
   - FastAPI with synchronous execution (no async)
   - Thread management handled by `movie_workflow_agent.invoke()`
   - MCP cleanup in lifespan context manager

### Agent Specializations

- **movie_retriever_agent**: Single tool (Pinecone vector search), custom prompt for movie expertise
- **torrent_agent** (download manager): Multiple MCP tools from qBittorrent server, base prompt
- **library_manager_agent**: Direct node function (no ReAct reasoning), SMB/CIFS scanning

### Tool Organization

Tools are direct instances, not factories:
- `movie_retriever_tool` (turtleapp/src/core/tools/movie_summaries_retriever.py)
- `library_manager_tool` (turtleapp/src/core/tools/library_manager.py)
- MCP tools loaded dynamically from qBittorrent server

## Configuration & Settings

### Settings System (`turtleapp/settings.py`)

Pydantic-based settings with nested configuration classes:
- `PineconeSettings`: Vector DB connection
- `OpenAISettings`: Embeddings model
- `ClaudeSettings`: API keys
- `MCPSettings`: HTTP URL for MCP server
- `SMBSettings`: Network share credentials

Access via singleton: `from turtleapp.settings import settings`

### Environment Variables Structure

Models:
- `SUPERVISOR_MODEL`: claude-3-5-sonnet-20241022
- `AGENT_MODEL`: claude-3-5-haiku-20241022
- `EMBEDDINGS_MODEL`: text-embedding-3-large

MCP Server:
- `TURTLEAPP_MCP_QBITTORRENT_URL`: http://turtle-mcp-qbittorrent:8000/mcp (Docker) or http://localhost:9001/mcp

Infrastructure (Docker overrides):
- `QBITTORRENT_HOST`, `SAMBA_SERVER`, `SAMBA_SHARE_PATH`

## MCP qBittorrent Server

Located in `mcp-servers/qbittorrent-mcp/`:
- **Transport**: HTTP (FastMCP with streamable_http)
- **Server**: `src/mcp_qbittorrent/server.py`
- **Client**: `src/mcp_qbittorrent/clients/qbittorrent_client.py`
- **Tools**: `src/mcp_qbittorrent/tools/qbittorrent_tools.py` (6 tools)
- **Models**: `src/mcp_qbittorrent/models/schemas.py` (Pydantic validation)

Running standalone:
```bash
cd mcp-servers/qbittorrent-mcp
uv run fastmcp run mcp_qbittorrent.server:mcp --transport http
```

## Docker Architecture

### Build Structure
- `build/docker-compose.yml`: All services (main app, MCP server, qBittorrent, Samba)
- `build/Dockerfile_api`: Turtle App container
- `mcp-servers/qbittorrent-mcp/Dockerfile`: MCP server container

### Services
- **turtle-api-server**: Port 9002 (maps to internal 8000)
- **turtle-mcp-qbittorrent**: Port 9001 (HTTP MCP endpoint)
- **qbittorrent**: Port 15080 (commented out - external deployment)
- **nas (Samba)**: Ports 1139/1445 (commented out - external deployment)

### Network
- Bridge network `turtle-network` with service discovery (containers reference by name)
- MCP server URL in container: `http://turtle-mcp-qbittorrent:8000/mcp`

## Code Patterns

### Creating New Agents

```python
from turtleapp.src.core.nodes.agents import ToolAgent
from langchain_core.tools import Tool

# Create tool instance
my_tool = Tool(name="my_tool", func=my_function, description="...")

# Create agent (uses base prompt by default)
my_agent = ToolAgent([my_tool], name="my_agent_name")

# Or with specialized prompt
from langchain_core.prompts import PromptTemplate
custom_prompt = PromptTemplate(...)
my_agent = ToolAgent([my_tool], specialized_prompt=custom_prompt)
```

### Adding Agents to Workflow

In `turtleapp/src/workflows/graph.py`:
```python
def create_movie_workflow() -> WorkflowGraph:
    agentic_tools = {
        "agent_name": agent_instance,  # ToolAgent or Callable
    }
    return WorkflowGraph(tools=agentic_tools, name="...").compile()
```

### Tool Error Handling

Use the decorator for consistent error handling:
```python
from turtleapp.src.utils import handle_tool_errors

@handle_tool_errors(default_return="Operation failed")
def _run(self, input: str) -> str:
    # Tool implementation
```

### Supervisor Prompts

Supervisor uses structured output routing (`turtleapp/src/core/prompts/supervisor.py`):
- Returns `{"next": "agent_name"}` for routing
- Returns `{"next": "FINISH"}` to end conversation
- Agent names must match keys in workflow tools dict

## Testing Guidelines

### Markers
- `@pytest.mark.slow`: Tests with significant runtime
- `@pytest.mark.expensive`: Tests making real LLM API calls

### Test Structure
- `test_api_endpoints.py`: FastAPI endpoint tests
- `test_mcp_integration.py`: MCP client/server integration
- `test_graph_workflow.py`: Multi-agent workflow tests
- `test_agent_mcp.py`, `test_graph_mcp.py`: MCP-specific agent tests
- `test_retriever.py`: Pinecone vector search tests
- `test_library_manager.py`: SMB/CIFS integration tests

### Async Testing
- `pytest-asyncio` configured with `asyncio_mode = "auto"`
- MCP tests require async fixtures

## Vocabulary & Terminology

The codebase deliberately uses neutral terminology to keep LLM agents focused on legitimate home theater management:
- "Download manager" instead of "torrent client"
- "Movie file acquisition" instead of "torrenting"
- Tools avoid technical protocol terms in descriptions

## LangGraph Specifics

### State Management
- Uses `MessagesState` for conversation history
- `MemorySaver` provides conversation persistence
- Thread IDs track conversation context

### Command Pattern
Nodes return `Command` objects:
```python
from langgraph.types import Command

return Command(
    update={"messages": [HumanMessage(content=result)]},
    goto=SUPERVISOR_NODE  # or END
)
```

### Graph Structure
- START → SUPERVISOR_NODE (entry point)
- Supervisor routes dynamically to agents
- Agents always return to SUPERVISOR_NODE
- Supervisor decides when to goto END

## Common Troubleshooting

### MCP Connection Issues
- Verify `TURTLEAPP_MCP_QBITTORRENT_URL` is correct
- Check MCP server health: `curl http://localhost:9001/mcp/tools`
- Ensure qBittorrent is accessible from MCP container

### Vector Store Issues
- Confirm Pinecone index exists: check `INDEX_NAME` in .env
- Verify OpenAI API key for embeddings
- Run upload script if index is empty

### Agent Routing Issues
- Check supervisor prompt includes all agent names
- Verify agent names match workflow tools dict keys
- Review LangSmith traces for routing decisions (if enabled)

### Docker Network Issues
- Services must reference each other by container name
- External URLs (host machine) vs internal URLs (container network)
- Check `.env.local` vs `.env` for Docker-specific config
