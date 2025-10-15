# qBittorrent MCP Server Plan

## Project Status

**Current Phase**: Phase 3 Complete ✅ | Phase 4 Next ⏳

### Completed Phases

- ✅ **Phase 1**: Local development setup complete
  - uv project initialized with all dependencies
  - Project structure created

- ✅ **Phase 2**: Core client implementation complete
  - `config.py`: Settings with required environment variables (38 lines)
  - `qbittorrent_client.py`: Simplified async API client (120 lines, reduced from 198)
  - `schemas.py`: Pydantic models + MCP response models (128 lines)
  - `main.py`: Test script validates client functionality
  - Successfully tested against qBittorrent instance

- ✅ **Phase 3**: MCP Tools Implementation Complete (2025 Best Practices)
  - `server.py`: FastMCP server entry point (37 lines)
  - `qbittorrent_tools.py`: 6 MCP tools with enhanced type annotations (322 lines)
  - All tools use Pydantic Field annotations and Literal types
  - Structured response models for better LLM accuracy
  - Input validation with regex patterns and constraints
  - Enhanced docstrings with use case examples
  - 22/22 tests passing ✅

### Current Phase

- ⏳ **Phase 4**: Containerization (Next - Not Started)
  - Create Dockerfile for MCP server
  - Create docker-compose.yml for standalone deployment
  - Build and test container

### Pending Phases

- ⏳ **Phase 5**: Integration with docker-compose stack

## Overview

Create a FastMCP-based Model Context Protocol server that provides direct interaction with qBittorrent's Web API through Claude. The MCP server will run as a container alongside qbittorrent in the existing docker compose stack.

**Implementation Approach**: Development started locally with Python client and core implementation. Containerization will follow after MCP tools are complete and tested.

## Architecture

### Technology Stack (Implemented)

- **Python 3.11+**: Modern async/await, type hints ✅
- **FastMCP 2.12.4+**: Decorator-based MCP server framework ✅ (installed)
- **aiohttp 3.12.15+**: Async HTTP client for qBittorrent Web API ✅
- **Pydantic v2.11.9+**: Data validation and settings management ✅
- **pydantic-settings 2.11.0+**: Environment variable configuration ✅
- **uv**: Fast Python package manager and project setup ✅

### Container Architecture

```
┌─────────────────────────────────────────┐
│   turtle-mcp-qbittorrent (container)   │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │     FastMCP Server              │  │
│  │  - qBittorrent API Tools        │  │
│  │  - MCP Protocol Handler         │  │
│  └─────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
         │
         │ HTTP (qBittorrent Web API)
         │
         ▼
┌──────────────────┐
│  qbittorrent     │
│  (container)     │
└──────────────────┘
```

## MCP Tools Design

### qBittorrent Web API Tools

#### `qb_search_torrents`
- **Description**: Search for torrents through qBittorrent's search plugins
- **Parameters**: `query`, `category` (optional), `plugins` (optional)
- **Returns**: List of search results with name, size, seeders, link

#### `qb_add_torrent`
- **Description**: Add torrent by URL or magnet link
- **Parameters**: `url`, `save_path` (optional), `category` (optional)
- **Returns**: Torrent hash and status

#### `qb_list_torrents`
- **Description**: List all torrents with status
- **Parameters**: `filter` (all/downloading/completed/paused), `category` (optional)
- **Returns**: List of torrents with progress, speed, ETA

#### `qb_torrent_info`
- **Description**: Get detailed info for specific torrent
- **Parameters**: `hash`
- **Returns**: Full torrent details including files, trackers, peers

#### `qb_control_torrent`
- **Description**: Control torrent (pause/resume/delete)
- **Parameters**: `hash`, `action` (pause/resume/delete), `delete_files` (bool)

#### `qb_get_preferences`
- **Description**: Get qBittorrent settings
- **Returns**: Download limits, default paths, connection settings

## Project Structure

```
mcp-qbittorrent/
├── Dockerfile                  # MCP server container (create after core implementation)
├── docker-compose.yml          # Standalone deployment config (create after core implementation)
├── pyproject.toml              # Minimal uv config (no PyPI metadata)
├── README.md
├── src/
│   └── mcp_qbittorrent/
│       ├── __init__.py
│       ├── server.py           # FastMCP server entry point
│       ├── config.py           # Pydantic settings
│       ├── tools/
│       │   ├── __init__.py
│       │   └── qbittorrent_tools.py   # qBittorrent API tools
│       ├── clients/
│       │   ├── __init__.py
│       │   └── qbittorrent_client.py  # qBittorrent API client
│       └── models/
│           ├── __init__.py
│           └── schemas.py      # Pydantic models
└── tests/
    ├── __init__.py
    ├── test_qbittorrent_tools.py
    └── fixtures.py
```

## Implementation Details

### FastMCP Server Setup

```python
from fastmcp import FastMCP
from mcp_qbittorrent.tools import qbittorrent_tools

mcp = FastMCP("qbittorrent-manager")

# Register qBittorrent API tools
qbittorrent_tools.register(mcp)

if __name__ == "__main__":
    mcp.run()
```

### qBittorrent Client Wrapper (✅ IMPLEMENTED)

**File**: `src/mcp_qbittorrent/clients/qbittorrent_client.py` (251 lines)

**Implemented Features**:
- Async context manager support (`async with QBittorrentClient(...)`)
- Authentication with session cookie management
- Comprehensive error handling (AuthenticationError, APIError, QBittorrentClientError)
- Timeout handling with configurable timeouts
- 6 core async methods for all MCP tool operations:
  1. `list_torrents(filter, category)` - List torrents with filtering
  2. `get_torrent_info(hash)` - Get detailed torrent properties + files
  3. `add_torrent(urls, savepath, category, paused)` - Add torrents
  4. `control_torrent(hashes, action, delete_files)` - Pause/resume/delete
  5. `search_torrents(query, plugins, category, limit)` - Search with polling
  6. `get_preferences()` - Get qBittorrent settings

**Key Implementation Details**:
- Uses aiohttp.ClientSession for persistent connections
- Automatic re-authentication on 403 responses
- JSON and text response handling
- Proper cleanup in async context manager

### Configuration Management (✅ IMPLEMENTED)

**File**: `src/mcp_qbittorrent/config.py` (38 lines)

**Implemented Features**:
- All connection settings are **REQUIRED** (no defaults)
- Settings fail fast if environment variables are missing
- Environment variable prefix: `QB_MCP_`
- Automatic `.env` file loading
- Case-insensitive environment variables

```python
class Settings(BaseSettings):
    # qBittorrent connection settings (REQUIRED - no defaults)
    qbittorrent_url: str = Field(..., description="qBittorrent Web API URL")
    qbittorrent_username: str = Field(..., description="qBittorrent Web API username")
    qbittorrent_password: str = Field(..., description="qBittorrent Web API password")

    # Timeout settings (optional with default)
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")

    class Config:
        env_file = ".env"
        env_prefix = "QB_MCP_"
        case_sensitive = False
```

**Required Environment Variables**:
- `QB_MCP_QBITTORRENT_URL` (required)
- `QB_MCP_QBITTORRENT_USERNAME` (required)
- `QB_MCP_QBITTORRENT_PASSWORD` (required)
- `QB_MCP_REQUEST_TIMEOUT` (optional, default: 30)

## Dockerfile Design

```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --frozen --no-dev

# Run server
CMD ["uv", "run", "python", "-m", "mcp_qbittorrent.server"]
```

## Docker Compose Integration

Add to existing `build/docker-compose.yml`:

```yaml
services:
  mcp-qbittorrent:
    build:
      context: ../mcp-qbittorrent
      dockerfile: Dockerfile
    container_name: turtle-mcp-qbittorrent
    environment:
      - QB_MCP_QBITTORRENT_URL=http://localhost:15080
      - QB_MCP_QBITTORRENT_USERNAME=${QB_USERNAME:-admin}
      - QB_MCP_QBITTORRENT_PASSWORD=${QB_PASSWORD:-adminadmin}  # qBittorrent WebUI password (username: admin)
    networks:
      - turtle-network
    depends_on:
      - qbittorrent
```

## Development Workflow

### ✅ Phase 1: Local Development Setup (COMPLETE)
**Status**: Completed successfully

**Completed Tasks**:
1. ✅ Created feature branch: `feature/mcp-qbittorrent-server`
2. ✅ Initialized uv project with `pyproject.toml`
3. ✅ Added dependencies:
   - fastmcp >= 2.12.4
   - aiohttp >= 3.12.15
   - pydantic >= 2.11.9
   - pydantic-settings >= 2.11.0
4. ✅ Created complete project structure:
   - `src/mcp_qbittorrent/` with clients/, models/, tools/ subdirectories
   - `tests/` directory with test files
   - `.env.example` for configuration template
   - `main.py` for client testing

### ✅ Phase 2: Core Client Implementation (COMPLETE)
**Status**: Completed successfully | **Lines of Code**: 418 total | **Tests**: 17/17 passing

**Completed Tasks**:
1. ✅ Implemented qBittorrent API client with:
   - Full authentication and session management
   - Async context manager support
   - 6 core API methods (list, get, add, control, search, preferences)
   - Comprehensive error handling (3 exception types)
2. ✅ Tested client against qBittorrent instance:
   - Created `main.py` test script
   - Successfully authenticated and retrieved data
   - Validated all connection settings
   - Created comprehensive unit test suite: 17 tests passing
3. ✅ Created Pydantic models (129 lines):
   - TorrentInfo, TorrentProperties, TorrentFile
   - SearchResult, SearchStatus, SearchResults
   - Preferences, AddTorrentResponse, ControlTorrentResponse
4. ✅ Added comprehensive error handling:
   - Custom exceptions: AuthenticationError, APIError, QBittorrentClientError
   - Timeout handling with configurable timeouts
   - Connection error recovery
   - Detailed logging

**Files Implemented**:
- `config.py`: 38 lines
- `qbittorrent_client.py`: 120 lines (simplified from 198)
- `schemas.py`: 128 lines (added MCP response models)
- `test_qbittorrent_client.py`: 22 passing tests
- Total: 286 lines of production code

### ✅ Phase 3: MCP Tools Implementation (COMPLETE)
**Status**: Complete ✅ | **Lines of Code**: 359 total | **Tests**: 22/22 passing | **MCP Best Practices**: 2025

**Completed Tasks**:
1. ✅ Created FastMCP server entry point (`server.py`): 37 lines
   - Initialized FastMCP with name "qbittorrent-manager"
   - Imported and registered tools
   - Added main entry point
2. ✅ Implemented FastMCP tool decorators (`qbittorrent_tools.py`): 322 lines
   - All 6 tools with `@mcp.tool()` decorator
   - **Enhanced with 2025 MCP Best Practices:**
     - Pydantic `Annotated[Type, Field(...)]` for all parameters
     - `Literal` types for enum values (filter states, actions)
     - Regex patterns for validation (hash, URL)
     - Min/max length constraints
     - Detailed Field descriptions for LLM understanding
   - Structured Pydantic response models (not generic dicts)
   - Enhanced docstrings with use case examples
   - Better error messages with troubleshooting hints
3. ✅ Added MCP Response Models to `schemas.py`:
   - `TorrentListResponse`, `TorrentInfoResponse`, `TorrentActionResponse`
   - `SearchResponse`, `PreferencesResponse`
   - `TorrentFilter` and `TorrentAction` Literal types
4. ✅ Tested tools:
   - All 22 tests passing (17 client + 5 integration)
   - Verified type annotations and validation
   - Confirmed structured responses

**Key Improvements for LLM Accuracy**:
- Input validation prevents invalid parameters
- Literal types constrain values to valid options only
- Structured returns help LLM parse responses
- Enhanced descriptions explain when to use each tool
- Examples in docstrings guide LLM usage

**Dependencies**: QBittorrentClient (✅ complete)

### ⏳ Phase 4: Containerization (PENDING)
**Status**: Not started | **Blocked by**: Phase 3 completion

**Planned Tasks**:
1. ⏳ Create `Dockerfile` for MCP server:
   - Base: python:3.11-slim
   - Copy uv from ghcr.io/astral-sh/uv:latest
   - Install dependencies: `uv sync --frozen --no-dev`
   - CMD: `["uv", "run", "python", "-m", "mcp_qbittorrent.server"]`
2. ⏳ Create `docker-compose.yml` for standalone deployment:
   - Service: mcp-qbittorrent
   - Environment variables for connection settings
   - Health check for service monitoring
3. ⏳ Build and test:
   - Build: `docker-compose build`
   - Start: `docker-compose up`
   - Test connectivity with qBittorrent container
4. ⏳ Verify container communication:
   - Test API calls from container to qBittorrent
   - Verify authentication and session management
   - Check error handling in containerized environment

### ⏳ Phase 5: Integration with Existing Stack (PENDING)
**Status**: Not started | **Blocked by**: Phase 4 completion

**Planned Tasks**:
1. ⏳ Update `build/docker-compose.yml`:
   - Add mcp-qbittorrent service
   - Configure environment variables
   - Set up depends_on: qbittorrent
2. ⏳ Configure networking:
   - Add to turtle-network
   - Set proper container names
   - Configure service discovery
3. ⏳ Test full stack:
   - Start: `cd build && docker-compose up -d`
   - Verify all services healthy
   - Test MCP server functionality in stack
   - Validate Claude Desktop integration

### ✅ Phase 6: Documentation (PARTIALLY COMPLETE)
**Status**: Core documentation complete | **Remaining**: Usage examples

**Completed Tasks**:
1. ✅ Updated README.md with:
   - Current project status and phase tracking
   - Configuration requirements (no defaults)
   - qBittorrent client features
   - Installation and testing instructions
   - Project structure with completion markers
2. ✅ Updated CLAUDE.md with:
   - Current phase status
   - Actual workflow and implementation details
   - Development commands for local and container modes
   - Phase-by-phase progress tracking
3. ✅ Created `.env.example`:
   - Clear labeling of required vs optional settings
   - Inline documentation for each variable

**Remaining Tasks**:
- ⏳ Create usage examples for Claude Desktop
- ⏳ Document all MCP tools with examples
- ⏳ Document docker-compose deployment steps

## Security Considerations

1. **Credentials**: Never hardcode qBittorrent credentials, use environment variables
2. **Input Validation**: Validate all torrent URLs and hashes before passing to qBittorrent
3. **Rate Limiting**: Implement rate limiting for API calls to prevent abuse
4. **Container Isolation**: Run MCP server with minimal privileges
5. **Network Isolation**: Only expose MCP server on internal docker network

## Testing Strategy

```python
# Example test structure
import pytest
from mcp_qbittorrent.clients.qbittorrent_client import QBittorrentClient

@pytest.mark.asyncio
async def test_qbittorrent_login(mock_qb_client):
    client = QBittorrentClient(
        base_url="http://localhost:15080",
        username="admin",
        password="adminadmin"  # qBittorrent WebUI password (username: admin)
    )
    await client.login()
    assert client.cookie is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_qbittorrent_search(real_qb_client):
    results = await real_qb_client.search_torrents("ubuntu")
    assert len(results) > 0
    assert all("name" in r and "size" in r for r in results)
```

## Success Metrics

### Completed Metrics ✅
1. ✅ **Code Quality**: 418 lines of well-structured, typed Python code
2. ✅ **Error Handling**: 3 custom exception types with comprehensive coverage
3. ✅ **Configuration**: Strict validation with required environment variables
4. ✅ **Documentation**: README and CLAUDE.md fully updated with current status

### Pending Metrics ⏳
1. ⏳ **Functionality**: All 6 qBittorrent API MCP tools working correctly
2. ⏳ **Performance**: API calls respond in <500ms
3. ⏳ **Reliability**: 99%+ uptime for MCP server
4. ⏳ **Integration**: Runs alongside qbittorrent in docker compose stack
5. ⏳ **User Experience**: Claude can interact with qBittorrent without direct API knowledge
6. ⏳ **Test Coverage**: >80% code coverage with unit and integration tests

## Future Enhancements

1. **Advanced Monitoring**: Grafana/Prometheus metrics for torrent activity
2. **Notification Tools**: MCP tools for torrent completion events
3. **Multi-Instance Support**: Manage multiple qBittorrent instances
4. **Batch Operations**: Add multiple torrents, bulk pause/resume
5. **Smart Categories**: Auto-categorization based on content analysis
6. **Storage Management**: Tools for managing download paths and disk usage

## References

- FastMCP Documentation: https://github.com/jlowin/fastmcp
- qBittorrent Web API: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
- Docker SDK for Python: https://docker-py.readthedocs.io/
- MCP Protocol Specification: https://spec.modelcontextprotocol.io/
