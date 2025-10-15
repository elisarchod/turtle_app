# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastMCP-based Model Context Protocol server that provides direct interaction with qBittorrent's Web API. The MCP server runs as a container alongside qbittorrent in a docker compose stack.

**Current Status**: Phase 3 complete - MCP tools fully implemented with 2025 best practices (30/30 tests passing). Ready for Phase 4 (Containerization).

## Technology Stack

- **Python 3.11+**: Async/await, type hints
- **FastMCP 2.12.4+**: Decorator-based MCP server framework
- **aiohttp 3.12.15+**: Async HTTP client for qBittorrent Web API
- **Pydantic v2.11.9+**: Data validation, settings management, MCP response models
- **uv**: Fast Python package manager and project setup

## Project Structure

```
mcp-qbittorrent/
├── Dockerfile                  # MCP server container (Phase 4 - pending)
├── docker-compose.yml          # Standalone deployment config (Phase 4 - pending)
├── pyproject.toml              # uv project config ✅
├── main.py                     # Client test script ✅
├── src/mcp_qbittorrent/        # 642 production lines
│   ├── server.py               # FastMCP server entry point ✅ (34 lines)
│   ├── config.py               # Pydantic settings ✅ (38 lines)
│   ├── tools/
│   │   └── qbittorrent_tools.py   # 6 MCP tools with 2025 best practices ✅ (322 lines)
│   ├── clients/
│   │   └── qbittorrent_client.py  # Async API client ✅ (120 lines)
│   └── models/
│       └── schemas.py          # Pydantic models + MCP response models ✅ (128 lines)
└── tests/                      # 716 test lines (111% test-to-code ratio)
    ├── unit/
    │   └── test_client.py      # Unit tests with mocks
    ├── integration/
    │   └── test_qbittorrent_integration.py  # Real instance tests
    ├── test_qbittorrent_client.py
    ├── test_integration.py
    ├── fixtures.py             # Test fixtures and mocks
    └── conftest.py             # pytest configuration

**30 tests passing** (unit + integration)
```

## Development Commands

### Local Development (Current Phase)

```bash
# Test qBittorrent client
uv run python main.py

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Run MCP server (once implemented)
uv run python -m mcp_qbittorrent.server
```

### Container-based Development (Phase 4+)

```bash
# Build container
docker-compose build mcp-qbittorrent

# Start service
docker-compose up mcp-qbittorrent

# Restart after code changes
docker-compose restart mcp-qbittorrent

# Run tests in container
docker-compose exec mcp-qbittorrent uv run pytest

# View logs
docker-compose logs -f mcp-qbittorrent

# Full stack with existing services
cd build && docker-compose up -d
```

## Architecture

### Container Communication

```
turtle-mcp-qbittorrent (container)
    │
    │ HTTP (qBittorrent Web API)
    │
    ▼
qbittorrent (container)
```

### Configuration

Configuration is managed via environment variables with `QB_MCP_` prefix:
- `QB_MCP_QBITTORRENT_URL`: qBittorrent Web API URL (default: http://qbittorrent:15080)
- `QB_MCP_QBITTORRENT_USERNAME`: qBittorrent username (default: admin)
- `QB_MCP_QBITTORRENT_PASSWORD`: qBittorrent password (default: adminadmin)

Settings are defined in `src/mcp_qbittorrent/config.py` using Pydantic BaseSettings.

## MCP Tools (✅ Phase 3 Complete - 2025 Best Practices)

The server exposes 6 qBittorrent Web API tools with enhanced LLM accuracy:

1. **`qb_list_torrents`**: List torrents with filtering (Literal types for states, Field annotations)
2. **`qb_add_torrent`**: Add torrent by URL/magnet (URL validation, category support)
3. **`qb_torrent_info`**: Get detailed info (hash validation with regex pattern)
4. **`qb_control_torrent`**: Control torrents (Literal types for pause/resume/delete)
5. **`qb_search_torrents`**: Search torrents (query validation, limit constraints)
6. **`qb_get_preferences`**: Get qBittorrent settings

**2025 MCP Best Practices Applied:**
- `Annotated[Type, Field(description="...", pattern="...")]` on all parameters
- `Literal` types for enum values (filter states, actions)
- Regex patterns for validation (40-char hex hashes, URLs)
- Structured Pydantic response models (not generic dicts)
- Enhanced docstrings with use case examples
- Input constraints (min/max length, ranges)

Tools are fully implemented in `src/mcp_qbittorrent/tools/qbittorrent_tools.py` (322 lines).

### qBittorrent Client (✅ Implementation Details)

The `QBittorrentClient` class in `clients/qbittorrent_client.py` provides:
- Async implementation with aiohttp (120 lines)
- Session-based authentication (cookie management)
- Async context manager support (`async with` for automatic cleanup)
- 6 core methods mapped to MCP tools:
  - `list_torrents(filter, category)` → `qb_list_torrents`
  - `get_torrent_info(hash)` → `qb_torrent_info` (**uses asyncio.gather for parallel API calls**)
  - `add_torrent(urls, savepath, category, paused)` → `qb_add_torrent`
  - `control_torrent(hashes, action, delete_files)` → `qb_control_torrent`
  - `search_torrents(query, plugins, category, limit)` → `qb_search_torrents` (polls for completion)
  - `get_preferences()` → `qb_get_preferences`
- Custom exception hierarchy (AuthenticationError, APIError)
- Configurable timeout handling (prevents hanging requests)
- Unified `_request()` method eliminates code duplication

## Implementation Pattern

### FastMCP Server Entry Point (server.py)
```python
from fastmcp import FastMCP
from mcp_qbittorrent.config import settings
from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient
from mcp_qbittorrent.tools.qbittorrent_tools import register_tools

# Initialize FastMCP server
mcp = FastMCP("qbittorrent-manager")

# Create global qBittorrent client instance
qb_client = QBittorrentClient(
    base_url=settings.qbittorrent_url,
    username=settings.qbittorrent_username,
    password=settings.qbittorrent_password,
    timeout=settings.request_timeout
)

# Register qBittorrent tools
register_tools(mcp, qb_client)

if __name__ == "__main__":
    mcp.run()
```

**Key Architecture Decisions:**
- Global client instance shared across all tool invocations
- Session reuse for all requests (TCP connection pooling)
- Environment-based configuration via Pydantic BaseSettings
- Tools registered via function that takes mcp and client as parameters


### Testing Strategy
- Unit tests: Mock qBittorrent API responses
- Integration tests: Use real qBittorrent instance in container (marked with `@pytest.mark.integration`)
- E2E tests: Test via MCP protocol from host to container

## Development Workflow

### Phase Order (Actual Workflow)

**✅ Phase 1: Project Setup (Complete)**
- uv project initialized with pyproject.toml
- Dependencies added: fastmcp, aiohttp, pydantic, pydantic-settings
- Project structure created with src/ and tests/ directories
- Feature branch created: `feature/mcp-qbittorrent-server`

**✅ Phase 2: Core Client Implementation (Complete)**
- config.py: Pydantic settings with environment variable support (38 lines)
- qbittorrent_client.py: Async API client with session management (120 lines)
- schemas.py: Pydantic models for all API responses (128 lines with MCP response models)
- main.py: Test script for validating client functionality
- Comprehensive unit and integration tests (30 tests passing)

**✅ Phase 3: MCP Tools Implementation (Complete - 2025 Best Practices)**
1. ✅ `server.py` with FastMCP initialization (34 lines)
2. ✅ FastMCP tool decorators in `qbittorrent_tools.py` for all 6 operations (322 lines)
3. ✅ Tools use QBittorrentClient methods with comprehensive error handling
4. ✅ 2025 MCP best practices applied:
   - Literal types for enum values (prevents LLM hallucinations)
   - Regex patterns for validation (40-char hashes, URLs)
   - Structured Pydantic response models (consistent success/error/data format)
   - Enhanced docstrings with natural language examples
   - Input constraints (min/max length, ranges)

**⏳ Phase 4: Containerization (Next - Not Started)**
1. Create `Dockerfile` for MCP server (use python:3.11-slim base)
2. Create `docker-compose.yml` for standalone deployment
3. Configure environment variables for container
4. Build and test: `docker-compose build && docker-compose up`
5. Verify container-to-container communication with qBittorrent

**⏳ Phase 5: Integration (After Phase 4)**
1. Update `build/docker-compose.yml` to include mcp-qbittorrent service
2. Configure networking between mcp-qbittorrent and qbittorrent containers
3. Test full stack: `cd build && docker-compose up -d`
4. Verify MCP server accessible via Claude Desktop

**✅ Phase 6: Documentation (Complete)**
- README.md: Portfolio-focused with technical rationale
- CLAUDE.md: LLM-focused implementation guidance

### Branching
Use feature branch: `feature/mcp-qbittorrent-server`

## Security Considerations

1. **Never hardcode credentials** - use environment variables with Pydantic BaseSettings
2. **Validate all inputs** - Pydantic Field validation on all MCP tool parameters (regex patterns, min/max length)
3. **Timeout handling** - Configurable timeout prevents resource exhaustion from hanging requests
4. **Session management** - Cookie-based authentication with automatic error handling (403 = token expired)
5. **Container isolation** (Phase 4) - run MCP server with minimal privileges
6. **Network isolation** (Phase 4) - only expose MCP server on internal docker network

## Important Implementation Notes for Claude Code

When working on this codebase:
- **DO NOT** modify line counts in documentation unless verifying with `wc -l`
- **DO NOT** add new features without updating both README.md and CLAUDE.md
- **DO NOT** change MCP tool signatures without updating type annotations and docstrings
- **DO** run tests after any changes: `uv run pytest -v`
- **DO** verify qBittorrent API compatibility: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
- **DO** follow 2025 MCP best practices for any new tools (Literal types, regex patterns, structured responses)

## References

- FastMCP: https://github.com/jlowin/fastmcp
- qBittorrent Web API: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
- MCP Protocol: https://spec.modelcontextprotocol.io/
