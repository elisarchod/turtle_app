# Turtle App Tools Structure

This directory contains all the tools used by the Turtle app's LangChain agents. The tools follow LangChain best practices and provide a simple interface for external service interactions.

## Architecture Overview

All tools inherit directly from LangChain's `BaseTool` class, providing a simple and direct approach without unnecessary abstraction layers.

## Tool Implementations

### 1. Torrent Client Tool (`torrent_tools.py`)

**Purpose**: Manages torrent downloads and searches via qBittorrent Web API

**Operations**:
- `list`: List currently downloading torrents (with optional filter)
- `search`: Search for torrents across multiple providers
- `add`: Add torrents via magnet links

**Parameters**:
- `operation`: "list", "search", or "add"
- `filter_type`: "downloading" or "all" (for list operation)
- `search_query`: Query string (for search operation)
- `magnet_link`: Magnet link URL (for add operation)

**Example Response**:
```
Found 3 torrents (filter: downloading):
- The Matrix (45.2%)
- Inception (78.9%)
- Interstellar (12.1%)
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

### 1. Tool Structure
- All tools inherit from `BaseTool`
- Return simple string responses
- Implement proper error handling
- Keep responses human-readable

### 2. Error Handling
```python
def _run(self, *args, **kwargs) -> str:
    try:
        # Tool logic here
        return "Success message"
    except Exception as e:
        logger.error(f"Tool failed: {str(e)}")
        return f"Error: {str(e)}"
```

### 3. Response Format
- Return human-readable strings
- Include relevant information
- Keep responses concise but informative
- Use clear formatting with newlines and bullet points

### 4. Logging
- Use the centralized logger from `log_handler.py`
- Log both success and error cases
- Include relevant context in log messages

## Integration with LangGraph

Tools are integrated into the workflow through:

1. **ToolAgent**: Wraps each tool in a LangGraph agent
2. **Supervisor**: Routes requests to appropriate tools
3. **State Management**: Uses `MessagesState` for conversation context

## Testing

Each tool has corresponding test files:
- `test_torrent.py`: Tests torrent operations
- `test_library_manager.py`: Tests library scanning
- `test_retriever.py`: Tests movie retrieval

## Adding New Tools

To add a new tool:

1. Create a new file in the `tools/` directory
2. Inherit from `BaseTool`
3. Implement the `_run()` method with proper error handling
4. Return simple string responses
5. Add the tool to `__init__.py`
6. Create corresponding tests
7. Update the workflow graph if needed

Example template:
```python
from langchain.tools import BaseTool

class NewTool(BaseTool):
    name: str = "new_tool"
    description: str = "Description of what this tool does"

    def _run(self, parameter: str) -> str:
        try:
            # Tool logic here
            return "Success message with results"
        except Exception as e:
            logger.error(f"Tool failed: {str(e)}")
            return f"Error: {str(e)}"

new_tool: Tool = NewTool()
``` 