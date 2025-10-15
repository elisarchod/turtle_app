# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Turtle App is an AI-powered home theater assistant that combines LLMs, RAG, and multi-agent orchestration for managing personal movie collections, discovering content, and controlling downloads. Built with LangGraph supervisor architecture where specialized agents handle different aspects under a central coordinator.

## Core Architecture

### Multi-Agent System (LangGraph)
- **Supervisor Agent** (`turtleapp/src/core/nodes/supervisor.py`): Central router using Claude 3.5 Sonnet that coordinates specialized agents
- **Movie Retriever Agent**: RAG-based agent for querying 42,000+ movie summaries from Pinecone vector DB
- **Download Manager Agent**: Manages movie downloads via qBittorrent Web API
- **Library Manager Agent**: Scans local network shares (Samba/CIFS) for movie files

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

### Tools (`turtleapp/src/core/tools/`)
- `movie_summaries_retriever.py`: Pinecone vector store with OpenAI embeddings
- `torrent_tools.py`: qBittorrent Web API integration (search, status, management)
- `library_manager.py`: SMB/CIFS file scanning via pysmb

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
- Config groups: `pinecone`, `openai`, `qbittorrent`, model settings
- All API keys and external service configs loaded from environment

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
- Services: qBittorrent (port 15080), Samba (ports 1139/1445), Turtle App API (port 8000)
- Default credentials in `.env.example` (qBittorrent: admin/adminadmin, Samba: dave/password)
- Docker overrides internal networking: `QBITTORRENT_HOST=http://qbittorrent:15080` instead of localhost

### External Services
- For external qBittorrent/Samba servers, see `.env.external` example
- Update `QBITTORRENT_HOST`, `SAMBA_SERVER`, `SAMBA_SHARE_PATH` with network addresses

## Project Structure
```
turtleapp/
├── api/routes/endpoints.py          # FastAPI endpoints
├── src/
│   ├── core/
│   │   ├── constants.py             # SUPERVISOR_NODE and other constants
│   │   ├── llm_factory.py           # LLM creation (supervisor vs agent models)
│   │   ├── nodes/
│   │   │   ├── supervisor.py        # SupervisorNodeCreator
│   │   │   └── agents.py            # ToolAgent class & agent instances
│   │   ├── prompts/                 # Specialized prompts for supervisor & agents
│   │   └── tools/                   # Tool implementations
│   ├── workflows/graph.py           # WorkflowGraph & movie_workflow_agent
│   ├── data_pipeline/               # Vector store upload pipeline
│   └── utils/                       # Utilities (logging, error handling, memory)
├── tests/                           # Test suite (pytest)
└── notebooks/                       # Jupyter notebooks for exploration
```

## Notes

- The system avoids technical terms like "torrent" in LLM prompts, using "download manager" and "movie file acquisition" instead
- All agents return to supervisor - no direct agent-to-agent communication
- Thread IDs enable conversation persistence via LangGraph's `MemorySaver`
- Test markers: `@pytest.mark.slow` for slow tests, `@pytest.mark.expensive` for real LLM calls
- LangSmith tracing enabled via `LANGCHAIN_TRACING_V2=true` for debugging workflows
