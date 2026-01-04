# OpenSubtitles Subtitle Downloader Integration Plan

## Overview
Add on-demand subtitle search and download capability to Turtle App using OpenSubtitles.com API. Users can request subtitles for movies, which will be saved next to movie files on the SMB share for automatic media player loading.

## User Requirements
- **Trigger**: On-demand only (user explicitly requests subtitles)
- **Scope**: Single movie at a time (no batch processing)
- **Languages**: Support English (default) and Hebrew
- **Save Location**: Next to movie files on SMB share (e.g., MovieName.2010.srt)
- **Credentials**: api_key=krlHWoIxsWHwbiA7E4Ffo4t2zOWavOPg, user=elisarchod@gmail.com, password=1213

## Architecture Approach
Create a new **subtitle_manager_agent** following the existing `movie_retriever_agent` pattern with two focused tools (search and download) to support ReAct agent reasoning.

```
User Request: "Find English subtitles for Inception 2010"
    ↓
Supervisor Agent → Routes to subtitle_manager_agent
    ↓
Agent uses:
  - subtitle_search_tool (search OpenSubtitles.com)
  - subtitle_download_tool (download specific subtitle)
    ↓
Returns: Subtitle info or download confirmation
```

## Implementation Steps

### 1. Add Dependencies & Environment Variables

**File: `pyproject.toml`** (MODIFY)
- Add `"opensubtitles-com>=1.0.0"` to dependencies array
- Run `uv sync` after modification

**File: `.env.example`** (MODIFY)
- Add OpenSubtitles configuration section:
  ```
  # OpenSubtitles Configuration
  OPENSUBTITLES_API_KEY=krlHWoIxsWHwbiA7E4Ffo4t2zOWavOPg
  OPENSUBTITLES_USERNAME=elisarchod@gmail.com
  OPENSUBTITLES_PASSWORD=1213
  ```

**File: `.env`** (CREATE/UPDATE - local only)
- Copy the same configuration from .env.example

### 2. Add Settings Configuration

**File: `turtleapp/settings.py`** (MODIFY)

Add after line 72 (after MCPSettings):
```python
class OpenSubtitlesSettings(BaseAppSettings):
    api_key: str = Field(
        alias="OPENSUBTITLES_API_KEY",
        description="OpenSubtitles.com API key"
    )
    username: str = Field(
        alias="OPENSUBTITLES_USERNAME",
        description="OpenSubtitles.com account username"
    )
    password: str = Field(
        alias="OPENSUBTITLES_PASSWORD",
        description="OpenSubtitles.com account password"
    )
    default_languages: List[str] = Field(
        default=["en", "he"],
        description="Default subtitle languages (ISO 639-1 codes): English and Hebrew"
    )
```

Update Settings class (around line 86):
```python
class Settings(BaseAppSettings):
    # ... existing fields ...
    opensubtitles: OpenSubtitlesSettings = Field(default_factory=OpenSubtitlesSettings)
```

Add typing import at top if not present:
```python
from typing import Optional, List
```

### 3. Create Subtitle Manager Core

**File: `turtleapp/src/core/subtitle_manager.py`** (NEW)

Core wrapper around OpenSubtitles API. Key methods:
- `__init__()`: Initialize client with credentials from settings
- `_ensure_authenticated()`: Handle login and token management
- `search_subtitles(query: str, languages: List[str], year: Optional[int])`: Search by title
- `download_subtitle(file_id: int, save_path: str)`: Download subtitle to SMB path
- `_format_subtitle_info(subtitle_data)`: Format results for LLM consumption

Use `@handle_service_errors` decorator for error handling.

**Implementation based on provided SubtitleManager code with modifications:**
- Use `settings.opensubtitles` for credentials (not os.getenv)
- Add year filtering to search results
- Implement SMB path writing for download_subtitle
- Return formatted strings suitable for agent consumption

### 4. Create Subtitle Tools

**File: `turtleapp/src/core/tools/subtitle_tools.py`** (NEW)

**SubtitleSearchTool** (extends BaseTool):
- `name`: "search_subtitles"
- `description`: Detailed usage guide for searching subtitles
- `_run(query: str)`:
  - Parse query for title, year, language (default to English and Hebrew)
  - Call SubtitleManager.search_subtitles()
  - Format top 5 results with file_id, language, downloads, rating
  - Use `@handle_tool_errors` decorator

**SubtitleDownloadTool** (extends BaseTool):
- `name`: "download_subtitle"
- `description`: Guide for downloading specific subtitle
- `_run(input_str: str)`:
  - Parse input: "file_id|movie_path" format
  - Extract directory and build .srt path
  - Call SubtitleManager.download_subtitle()
  - Return confirmation with file location
  - Use `@handle_tool_errors` decorator

**Module exports**:
```python
subtitle_search_tool = SubtitleSearchTool()
subtitle_download_tool = SubtitleDownloadTool()
```

**File: `turtleapp/src/core/tools/__init__.py`** (MODIFY)
- Import: `from .subtitle_tools import subtitle_search_tool, subtitle_download_tool`
- Add to `__all__`: `"subtitle_search_tool", "subtitle_download_tool"`

### 5. Create Specialized Agent Prompt

**File: `turtleapp/src/core/prompts/agents.py`** (MODIFY)

Add after MOVIE_RETRIEVER_PROMPT (around line 50+):
```python
SUBTITLE_MANAGER_TEMPLATE = """You are a subtitle management expert with access to OpenSubtitles.com database.

Your expertise:
- Searching subtitles by movie title, year, and language
- Evaluating subtitle quality (downloads, ratings)
- Downloading subtitles to correct movie directory
- Supporting English and Hebrew languages (default to English)

**Available Tools:** {tools}

**Tool Usage Guidelines:**

1. For search requests:
   - Extract movie title, year, language from user request
   - Default to English unless Hebrew specified
   - Use search_subtitles tool
   - Present top 3-5 results with quality indicators (downloads, rating)

2. For download requests:
   - First search if not done already
   - Ask user to confirm subtitle choice if multiple options
   - Use download_subtitle tool with file_id and movie path
   - Confirm download with file location

3. Quality indicators:
   - Higher download count = more popular
   - Rating/score from uploaders
   - Release format should match movie file (1080p, BluRay, etc.)

**Task:** {input}

{agent_scratchpad}"""

SUBTITLE_MANAGER_PROMPT = PromptTemplate(
    template=SUBTITLE_MANAGER_TEMPLATE,
    input_variables=["tools", "tool_names", "input", "agent_scratchpad"]
)
```

**File: `turtleapp/src/core/prompts/__init__.py`** (MODIFY)
- Import: `from .agents import AGENT_BASE_PROMPT, MOVIE_RETRIEVER_PROMPT, SUBTITLE_MANAGER_PROMPT`
- Add to `__all__`: `"SUBTITLE_MANAGER_PROMPT"`

### 6. Create Subtitle Agent

**File: `turtleapp/src/core/nodes/agents.py`** (MODIFY)

Add imports at top:
```python
from turtleapp.src.core.tools import subtitle_search_tool, subtitle_download_tool
from turtleapp.src.core.prompts import SUBTITLE_MANAGER_PROMPT
```

Add after torrent_agent (around line 82):
```python
# Subtitle manager agent - uses search and download tools
subtitle_agent = ToolAgent(
    [subtitle_search_tool, subtitle_download_tool],
    name="subtitle_manager_agent",
    specialized_prompt=SUBTITLE_MANAGER_PROMPT
)
```

**File: `turtleapp/src/core/nodes/__init__.py`** (MODIFY - if it exists)
- Export subtitle_agent if __init__.py exists

### 7. Register Agent in Workflow

**File: `turtleapp/src/workflows/graph.py`** (MODIFY)

Add import (around line 8):
```python
from turtleapp.src.core.nodes import (
    library_scan_node,
    movie_retriever_agent,
    torrent_agent,
    subtitle_agent  # Add this
)
```

Update `create_movie_workflow()` function (around line 25):
```python
def create_movie_workflow() -> WorkflowGraph:
    agentic_tools = {
        movie_retriever_agent.name: movie_retriever_agent,
        torrent_agent.name: torrent_agent,
        "library_manager_agent": library_scan_node,
        subtitle_agent.name: subtitle_agent,  # Add this line
    }

    return (WorkflowGraph(tools=agentic_tools, name="Multi-agent Movie Supervisor")
            .compile())
```

### 8. Update Supervisor Routing

**File: `turtleapp/src/core/prompts/supervisor.py`** (MODIFY)

Update SUPERVISOR_SYSTEM_MESSAGE to include subtitle_manager_agent in routing rules:

Add to "Available Agents" section:
```
- subtitle_manager_agent: Expert in searching and downloading subtitles from OpenSubtitles.com (English and Hebrew)
```

Add to routing rules (after library_manager rule):
```
4. Route to subtitle_manager_agent when user wants to:
   - Search for subtitles
   - Download subtitle files
   - Find subtitles for specific movies
   - Check subtitle availability or quality
```

### 9. Testing (Optional but Recommended)

**File: `turtleapp/tests/test_subtitle_manager.py`** (NEW)

Create basic tests:
- Test SubtitleManager initialization
- Test subtitle search tool with mocked API
- Test subtitle download tool with mocked paths
- Mark real API tests with `@pytest.mark.expensive`

**File: `turtleapp/tests/test_subtitle_integration.py`** (NEW)

Create integration tests:
- Test agent workflow with MessagesState
- Test supervisor routing to subtitle_agent
- Test full search + download flow

## Critical Files to Modify

1. **turtleapp/settings.py** - Add OpenSubtitlesSettings class
2. **turtleapp/src/core/tools/subtitle_tools.py** (NEW) - Two tools for search/download
3. **turtleapp/src/core/subtitle_manager.py** (NEW) - Core API wrapper
4. **turtleapp/src/core/prompts/agents.py** - Add SUBTITLE_MANAGER_PROMPT
5. **turtleapp/src/core/nodes/agents.py** - Create subtitle_agent
6. **turtleapp/src/workflows/graph.py** - Register agent in workflow
7. **turtleapp/src/core/prompts/supervisor.py** - Add routing rules
8. **pyproject.toml** - Add opensubtitles-com dependency
9. **.env.example** - Add OpenSubtitles credentials template

## Implementation Order

1. **Dependencies & Settings** (Low risk)
   - Update pyproject.toml and run `uv sync`
   - Add OpenSubtitlesSettings to settings.py
   - Update .env files

2. **Core Infrastructure** (Medium risk)
   - Create subtitle_manager.py with API wrapper
   - Test authentication manually

3. **Tools** (Medium risk)
   - Create subtitle_tools.py with both tools
   - Update tools/__init__.py
   - Create basic unit tests

4. **Agent & Prompt** (Low risk)
   - Create SUBTITLE_MANAGER_PROMPT in prompts/agents.py
   - Create subtitle_agent in nodes/agents.py
   - Update __init__.py exports

5. **Workflow Integration** (Medium risk)
   - Update graph.py to register agent
   - Update supervisor.py routing rules

6. **Testing & Validation** (High risk - requires real API)
   - Test search with real API calls
   - Test download to SMB share
   - Test full workflow through supervisor

## Example User Interactions

**Search Only:**
```
User: "Find English subtitles for Inception 2010"
Agent: [Returns top 5 subtitle options with quality metrics]
```

**Search + Download:**
```
User: "Download Hebrew subtitles for The Matrix"
Agent: [Searches, presents options, asks for confirmation, downloads]
```

**Direct Download:**
```
User: "Download English subtitles for Terminator 2 in my library"
Agent: [May coordinate with library_manager to find movie path, then downloads]
```

## Error Handling

All tools use `@handle_tool_errors` decorator to:
- Log errors appropriately
- Return user-friendly error messages
- Gracefully degrade (search succeeds but download fails = show search results)

Common error scenarios:
- OpenSubtitles API authentication failure
- No subtitles found for movie
- SMB write permission denied
- Invalid movie path
- API rate limiting

## Notes

- Subtitle files saved as `MovieName.Year.srt` next to movie files
- Media players will auto-detect and load subtitles
- SMB write access required (already configured in settings)
- Agent will handle year extraction from movie titles
- Default to English, support Hebrew when specified
- No automatic triggering - user must explicitly request
