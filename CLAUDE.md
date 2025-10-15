# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Turtle App is an AI-powered home theater assistant that combines LLMs, RAG, and multi-agent orchestration for managing personal movie collections, discovering content, and controlling downloads. Built with LangGraph supervisor architecture where specialized agents handle different aspects under a central coordinator.

## Core Architecture

### Multi-Agent System (LangGraph)
- **Supervisor Agent** (`turtleapp/src/core/nodes/supervisor.py`): Central router using Claude 3.5 Sonnet that coordinates specialized agents
- **Movie Retriever Agent**: RAG-based agent for querying 42,000+ movie summaries from Pinecone vector DB
- **Download Manager Agent**: Manages movie downloads via MCP tools (qBittorrent MCP server)
- **Library Manager Agent**: Scans local network shares (Samba/CIFS) for movie files

### MCP Integration

Turtle App uses **LangGraph's native MCP support** with **HTTP transport** for qBittorrent integration:

```
Docker Container: Turtle App
┌────────────────────────────────┐
│ LangGraph Supervisor           │
│        ↓                       │
│ Download Manager Agent         │
│        ↓                       │
│ MCP Tools (LangChain wrappers) │
│        ↓                       │
│ MultiServerMCPClient (HTTP)    │
└────────────────────────────────┘
        ↓ streamable_http
Docker Container: MCP Server
┌────────────────────────────────┐
│ FastMCP HTTP Server            │
│ (Port 8000, /mcp endpoint)     │
│        ↓                       │
│ qBittorrent MCP Tools          │
└────────────────────────────────┘
        ↓ HTTP
Docker Container: qBittorrent
┌────────────────────────────────┐
│ qBittorrent Web API            │
│ (Port 15080)                   │
└────────────────────────────────┘
```

#### MCP Tools

The **download manager agent** uses these MCP tools (implementation: qBittorrent server):

- **qb_search_torrents**: Search for available movie sources
- **qb_list_torrents**: List/filter downloads by status (downloading/completed/paused)
- **qb_add_torrent**: Add a movie to the download queue
- **qb_control_torrent**: Pause/resume/delete downloads
- **qb_torrent_info**: Get detailed download information
- **qb_get_preferences**: Get download client configuration

**Note**: The LLM prompt never mentions "qBittorrent" or "torrent" - it operates at the abstraction level of "movie downloads" and "download management". The MCP tools handle implementation details transparently.

### Workflow Graph (`turtleapp/src/workflows/graph.py`)
- `WorkflowGraph` class: Encapsulates multi-agent workflow with `compile()` and `invoke()` methods
- Uses `MemorySaver` for conversation persistence across thread IDs
- Entry point: `movie_workflow_agent` global instance, or use `create_movie_workflow()` factory
- Interactive: `run('your message')` function for simple sync invocation

### Agent Implementation (`turtleapp/src/core/nodes/agents.py`)
- `ToolAgent` class: Generic wrapper for ReAct agents with specialized prompts
- Uses `AgentExecutor` with `handle_parsing_errors=True` and `max_iterations=3`
- All agents route back to supervisor via `Command(goto=SUPERVISOR_NODE)`
- Specialized prompts in `turtleapp/src/core/prompts/`

### Tools
- **Local tools** (`turtleapp/src/core/tools/`):
  - `movie_summaries_retriever.py`: Pinecone vector store with OpenAI embeddings
  - `library_manager.py`: SMB/CIFS file scanning via pysmb
- **MCP tools** (`turtleapp/src/core/mcp/`):
  - Loaded dynamically from qBittorrent MCP server via HTTP
  - Configuration in `mcp/config.py`, tool loading in `mcp/tools.py`
  - Uses `MultiServerMCPClient` from `langchain-mcp-adapters`

### API Layer (`turtleapp/api/routes/endpoints.py`)
- FastAPI with synchronous execution
- `/chat` POST: Main endpoint with optional thread_id for conversation continuity
- `/health` GET: Health check endpoint

### Model Configuration
- **Supervisor**: Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`) - complex routing decisions
- **Agents**: Claude 3.5 Haiku (`claude-3-5-haiku-20241022`) - cost-efficient for focused tasks
- **Embeddings**: OpenAI `text-embedding-3-large` (3072 dimensions)

### Settings (`turtleapp/settings.py`)
- Pydantic Settings from `.env` file
- Config groups: `pinecone`, `openai`, `mcp`, model settings
- All API keys and external service configs loaded from environment
- MCP configuration: HTTP URL to MCP server (default: `http://mcp-qbittorrent:8000/mcp`)

## Development Commands

### Running the Application
```bash
# Start with Docker Compose (recommended - includes qBittorrent and Samba)
cd build && docker-compose up -d

# Start API only (requires external services)
poetry run turtle-app-server

# Interactive debugging
python turtleapp/src/workflows/graph.py
# Then use: run('your message')
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=turtleapp

# Run in parallel
poetry run pytest -n auto

# Skip slow/expensive tests
poetry run pytest -m "not slow" -m "not expensive"

# Specific test files
poetry run pytest turtleapp/tests/test_api_endpoints.py
poetry run pytest turtleapp/tests/test_graph_workflow.py
```

### Data Pipeline
```bash
# Upload movie data to Pinecone vector store
python turtleapp/src/data_pipeline/vector_store/upload_script.py
```
- Data source: `turtleapp/data_pipeline/data/processed/wiki_movie_plots_cleaned.csv`
- Default: 300 documents per upload (configurable in `MovieDataLoader`)
- Batch processing: 100 docs/batch with 4 concurrent workers

### API Testing
```bash
# Chat endpoint
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Terminator 2"}'

# With thread continuity
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What about the sequel?", "thread_id": "thread-123"}'
```

## Key Implementation Patterns

### Adding New Agents
1. Create tool(s) in `turtleapp/src/core/tools/`
2. Create specialized prompt in `turtleapp/src/core/prompts/`
3. Instantiate `ToolAgent` in `turtleapp/src/core/nodes/agents.py`
4. Add to workflow in `create_movie_workflow()` function

### Supervisor Routing
- Supervisor uses structured output with `Router` TypedDict
- Returns `"next"` field with agent name or `"FINISH"` (mapped to `END`)
- Routing prompt in `turtleapp/src/core/prompts/supervisor.py`

### Message Flow
1. User message → FastAPI `/chat` endpoint
2. → `movie_workflow_agent.invoke(message, thread_id)`
3. → Supervisor routes to specialized agent
4. → Agent executes with tools, returns to supervisor
5. → Supervisor decides: route to another agent or END
6. → Final response extracted from `messages[-1].content`

### Error Handling
- `@handle_tool_errors` decorator for tool failures (returns default message)
- `@handle_service_errors` decorator for external API failures
- Agent executors have `handle_parsing_errors=True` for LLM response issues

## Configuration

### Environment Setup
1. Copy `.env.example` to `.env`
2. Required API keys:
   - `CLAUDE_API` (Anthropic)
   - `OPENAI_API_KEY` (embeddings)
   - `PINECONE_API_KEY` (vector DB)
   - `LANGCHAIN_API_KEY` (optional, for LangSmith tracing)

### Docker Compose Setup
- **Services**:
  - qBittorrent (port 15080) - Download client
  - mcp-qbittorrent (port 8001) - HTTP MCP server
  - Samba (ports 1139/1445) - File sharing
  - Turtle App API (port 8000) - FastAPI application
- Default credentials in `.env.example` (qBittorrent: admin/adminadmin, Samba: dave/password)
- **MCP Architecture**: Main app connects to MCP server via HTTP (`TURTLEAPP_MCP_QBITTORRENT_URL`)
- MCP server credentials set in `mcp-qbittorrent` container environment

### Environment Variables
```bash
# Main app only needs MCP server URL
TURTLEAPP_MCP_QBITTORRENT_URL=http://mcp-qbittorrent:8000/mcp

# MCP server needs qBittorrent credentials (set in docker-compose)
TURTLEAPP_QB_QBITTORRENT_URL=http://qbittorrent:15080
TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin
```

## Project Structure
```
turtle_app/
├── mcp-servers/                     # MCP server implementations
│   └── qbittorrent-mcp/            # qBittorrent MCP server (FastMCP)
│       ├── src/mcp_qbittorrent/    # Server code
│       ├── Dockerfile              # MCP server container
│       └── pyproject.toml          # uv dependencies
├── turtleapp/
│   ├── api/routes/endpoints.py     # FastAPI endpoints
│   ├── src/
│   │   ├── core/
│   │   │   ├── constants.py        # SUPERVISOR_NODE and other constants
│   │   │   ├── llm_factory.py      # LLM creation (supervisor vs agent models)
│   │   │   ├── mcp/                # MCP integration (NEW)
│   │   │   │   ├── config.py       # MCP server configuration
│   │   │   │   └── tools.py        # MCP tools loader with MultiServerMCPClient
│   │   │   ├── nodes/
│   │   │   │   ├── supervisor.py   # SupervisorNodeCreator
│   │   │   │   └── agents.py       # ToolAgent class & agent instances
│   │   │   ├── prompts/            # Specialized prompts for supervisor & agents
│   │   │   └── tools/              # Local tool implementations
│   │   ├── workflows/graph.py      # WorkflowGraph & movie_workflow_agent
│   │   ├── data_pipeline/          # Vector store upload pipeline
│   │   └── utils/                  # Utilities (logging, error handling, memory)
│   ├── tests/                      # Test suite (pytest)
│   │   ├── test_mcp_integration.py # MCP integration tests (NEW)
│   │   ├── test_agent_mcp.py       # Agent with MCP tools tests (NEW)
│   │   └── test_graph_mcp.py       # Workflow with MCP tests (NEW)
│   └── notebooks/                  # Jupyter notebooks for exploration
├── build/
│   ├── docker-compose.yml          # Multi-container deployment
│   └── Dockerfile_api              # Main app container (uv-based)
└── pyproject.toml                  # Main app dependencies (uv format)
```

## MCP Server Development

### Adding New MCP Tools
1. Add tool to MCP server: `mcp-servers/qbittorrent-mcp/src/mcp_qbittorrent/tools/qbittorrent_tools.py`
2. Restart MCP server container: `docker-compose restart mcp-qbittorrent`
3. Tools auto-reload in main app (loaded at startup via `get_qbittorrent_tools()`)

### Testing MCP Server Locally
```bash
# Run MCP HTTP server locally
cd mcp-servers/qbittorrent-mcp
export TURTLEAPP_QB_QBITTORRENT_URL=http://localhost:15080
export TURTLEAPP_QB_QBITTORRENT_USERNAME=admin
export TURTLEAPP_QB_QBITTORRENT_PASSWORD=adminadmin
uv run fastmcp run mcp_qbittorrent.server:mcp --transport http

# Test MCP server
curl http://localhost:8000/mcp/tools | jq
```

### Adding More MCP Servers
To add additional MCP servers (Plex, Sonarr, etc.):
1. Create new MCP server in `mcp-servers/` directory
2. Add server config to `turtleapp/src/core/mcp/config.py`
3. Create tool loader function in `turtleapp/src/core/mcp/tools.py`
4. Create agent using new tools in `turtleapp/src/core/nodes/agents.py`
5. Add agent to workflow in `turtleapp/src/workflows/graph.py`
6. Update `docker-compose.yml` with new MCP server container

## Notes

- The system avoids technical terms like "torrent" in LLM prompts, using "download manager" and "movie file acquisition" instead
- All agents return to supervisor - no direct agent-to-agent communication
- Thread IDs enable conversation persistence via LangGraph's `MemorySaver`
- Test markers: `@pytest.mark.slow` for slow tests, `@pytest.mark.expensive` for real LLM calls
- LangSmith tracing enabled via `LANGCHAIN_TRACING_V2=true` for debugging workflows
