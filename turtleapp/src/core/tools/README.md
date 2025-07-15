# Turtle App Tools Structure

This directory contains all the tools used by the Turtle app's LangChain agents. The tools are designed for LLM consumption with simple, clean outputs and natural language interfaces.

## Architecture Overview

All tools inherit directly from LangChain's `BaseTool` class and use standardized error handling decorators for consistent behavior across the application.

## Tool Implementations

### 1. Torrent Client Tool (`torrent_tools.py`)

**Purpose**: Manages torrent downloads and searches via qBittorrent Web API with natural language interface

**Usage**: Single `query` parameter that accepts natural language input

**Example Queries**:
- `"check downloads"` - Lists current downloads
- `"search for terminator"` - Searches for torrents
- `"find inception movie"` - Searches for specific content
- `"show current downloads"` - Lists active downloads

**Example Response**:
```
Currently downloading 2 items:
- The Matrix (downloading)
- Inception (completed)
```

**Search Response**:
```
Found torrents for 'terminator':
1. Terminator 2 Judgment Day 1991 1080p BluRay
2. The Terminator 1984 Director's Cut
3. Terminator Dark Fate 2019 4K UHD
4. Terminator 3 Rise of the Machines 2003
5. Terminator Genisys 2015 Extended Cut
... and 15 more available
```

### 2. Library Manager Tool (`library_manager.py`)

**Purpose**: Scans and catalogs local movie library from network shares

**Parameters**:
- `force_refresh`: Boolean to force a fresh scan (optional)

**Example Response**:
```
Library scan completed. Found 150 movies.
File types: .mkv: 100, .mp4: 50
Sample movies:
- The Matrix
- Inception
- Interstellar
- The Dark Knight
- Pulp Fiction
... and 145 more
```

### 3. Movie Retriever Tool (`movie_summaries_retriever.py`)

**Purpose**: Search and retrieve movie information using semantic search

**Parameters**:
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 5)

**Example Response**:
```
Found 3 movies matching 'comedy':

1. The Grand Budapest Hotel (2014)
   A concierge at a famous European hotel between the wars becomes a trusted friend and mentor to a young employee who finds himself at the center of a murder mystery...

2. Superbad (2007)
   Two co-dependent high school seniors are forced to deal with separation anxiety after their plan to stage a booze-soaked party goes awry...

3. Shaun of the Dead (2004)
   A man decides to turn his moribund life around by winning back his ex-girlfriend, reconciling his relationship with his mother, and dealing with an entire community that has returned from the dead...
```

## Best Practices

### 1. LLM-Optimized Design
- Simple, clean output formats
- Natural language interfaces where possible
- Limited result sets to avoid overwhelming LLM
- Human-readable responses without technical jargon

### 2. Error Handling
All tools use standardized error handling decorators:

```python
from turtleapp.src.utils.error_handler import handle_tool_errors, handle_service_errors

@handle_tool_errors(default_return="Tool operation failed")
def _run(self, query: str) -> str:
    # Tool logic here
    return "Success message"

@handle_service_errors(service_name="ServiceName", default_return=[])
def helper_function() -> List[Any]:
    # Service logic here
    return results
```

### 3. Response Format
- Return human-readable strings
- Include relevant information without technical details
- Use clear formatting with newlines and bullet points
- Limit output length for better LLM processing

### 4. Logging
- Use the centralized logger from `log_handler.py`
- Log both success and error cases
- Include relevant context in log messages

## Integration with LangGraph

Tools are integrated into the workflow through:

1. **ToolAgent**: Wraps each tool in a LangGraph agent with async processing
2. **Supervisor**: Routes requests to appropriate tools using natural language understanding
3. **State Management**: Uses `MessagesState` for conversation context
4. **Error Handling**: Standardized error handling with decorators

## Testing

Each tool has corresponding test files:
- `test_torrent.py`: Tests torrent operations with network failure handling
- `test_library_manager.py`: Tests library scanning functionality
- `test_retriever.py`: Tests movie retrieval and RAG evaluation

## Recent Improvements

### Simplified Torrent Tool
- **Before**: Complex parameter system with `operation`, `filter_type`, `search_query`, `magnet_link`
- **After**: Single `query` parameter with natural language processing
- **Benefit**: Much easier for LLM to use and understand

### Standardized Error Handling
- Consistent error decorators across all tools
- Better error messages for users
- Graceful failure handling for network issues

### Clean Documentation
- Removed uninformative docstrings
- Focused on essential information
- Clear examples and usage patterns

## Adding New Tools

To add a new tool:

1. Create a new file in the `tools/` directory
2. Inherit from `BaseTool`
3. Use standardized error handling decorators
4. Design for LLM consumption (simple inputs/outputs)
5. Return human-readable string responses
6. Add the tool to `__init__.py`
7. Create corresponding tests
8. Update the workflow graph if needed

Example template:
```python
from langchain.tools import BaseTool
from turtleapp.src.utils.error_handler import handle_tool_errors

class NewTool(BaseTool):
    name: str = "new_tool"
    description: str = "Simple description of what this tool does"

    @handle_tool_errors(default_return="Tool operation failed")
    def _run(self, query: str) -> str:
        # Tool logic here
        return "Success message with results"

new_tool: Tool = NewTool()
```

## Key Design Principles

1. **LLM-First**: All tools designed for easy LLM consumption
2. **Simplicity**: Avoid complex parameter combinations
3. **Natural Language**: Use conversational interfaces where possible
4. **Consistent Errors**: Standardized error handling across all tools
5. **Clean Output**: Human-readable responses without technical noise