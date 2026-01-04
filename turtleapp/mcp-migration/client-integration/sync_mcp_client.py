import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ToolSelection(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str

TOOL_SELECTION_PROMPT = """You are a home theater management system that helps users with their movie collection. You have access to these tools:

**Available Tools:**
- movie_search: Search the movie database (42k+ movies) for plot, cast, director, genre info
  Parameters: {"query": str, "max_results": int (default 5)}
  
- torrent_search: Search for movie files to download
  Parameters: {"query": str}
  
- torrent_status: Check current download status and progress
  Parameters: {} (no parameters needed)
  
- library_scan: Scan SMB network shares for existing movie files
  Parameters: {} (no parameters needed)

**Tool Selection Rules:**
1. Use movie_search when user asks about:
   - Movie plots, summaries, or details
   - Cast, director, or crew information
   - Movie recommendations or similar films
   - Genre-based queries

2. Use torrent_search when user wants to:
   - Download or find movies
   - Search for available movie files

3. Use torrent_status when user asks about:
   - Download status/progress
   - Current downloads
   - What's downloading

4. Use library_scan when user asks about:
   - What movies they already own
   - Library organization or scanning
   - Local file management

Analyze the user's request: "{user_message}"

Return your tool selection as JSON:
{{
  "tool_name": "selected_tool_name",
  "arguments": {{"param": "value"}},
  "reasoning": "Brief explanation of why this tool was selected"
}}"""

class SyncMCPClient:
    def __init__(self, server_script_path: Optional[str] = None, anthropic_api_key: Optional[str] = None):
        if server_script_path is None:
            current_dir = Path(__file__).parent
            server_script_path = current_dir.parent / "server-examples" / "turtle-server.py"
        
        self.server_script_path = str(server_script_path)
        self.available_tools = ["movie_search", "torrent_search", "torrent_status", "library_scan"]
        
        # Initialize Anthropic client for LLM-based tool selection
        if anthropic_api_key:
            self.anthropic = Anthropic(api_key=anthropic_api_key)
        else:
            import os
            api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.anthropic = Anthropic(api_key=api_key)
            else:
                logger.warning("No Anthropic API key found. Falling back to manual routing.")
                self.anthropic = None
    
    def process_message(self, message: str, thread_id: Optional[str] = None) -> str:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._async_process_message(message, thread_id))
                return future.result()
        except RuntimeError:
            return asyncio.run(self._async_process_message(message, thread_id))
    
    async def _async_process_message(self, message: str, thread_id: Optional[str] = None) -> str:
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path]
        )
        
        try:
            # Select tool using LLM or fallback to manual routing
            tool_selection = await self._select_tool(message)
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(tool_selection.tool_name, tool_selection.arguments)
                    
                    if hasattr(result, 'content') and result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            return content.text
                        elif isinstance(content, dict) and 'text' in content:
                            return content['text']
                        else:
                            return str(content)
                    else:
                        return str(result)
                        
        except Exception as e:
            logger.error(f"MCP client error: {e}")
            return f"Error processing request: {str(e)}"
    
    async def _select_tool(self, user_message: str) -> ToolSelection:
        """Select the appropriate tool using LLM reasoning or fallback to manual routing."""
        if self.anthropic:
            try:
                # Use LLM for intelligent tool selection
                response = self.anthropic.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=500,
                    messages=[
                        {"role": "user", "content": TOOL_SELECTION_PROMPT.format(user_message=user_message)}
                    ]
                )
                
                # Parse the JSON response
                response_text = response.content[0].text
                try:
                    # Try to extract JSON from the response
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        json_str = response_text[json_start:json_end].strip()
                    elif "{" in response_text and "}" in response_text:
                        json_start = response_text.find("{")
                        json_end = response_text.rfind("}") + 1
                        json_str = response_text[json_start:json_end]
                    else:
                        raise ValueError("No JSON found in response")
                    
                    selection_data = json.loads(json_str)
                    return ToolSelection(**selection_data)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse LLM response: {e}. Falling back to manual routing.")
                    return self._manual_tool_selection(user_message)
                    
            except Exception as e:
                logger.warning(f"LLM tool selection failed: {e}. Falling back to manual routing.")
                return self._manual_tool_selection(user_message)
        else:
            return self._manual_tool_selection(user_message)
    
    def _manual_tool_selection(self, user_message: str) -> ToolSelection:
        """Fallback manual tool selection using keyword matching."""
        message_lower = user_message.lower()
        
        if any(keyword in message_lower for keyword in ['library', 'collection', 'own', 'have']) and 'scan' in message_lower:
            return ToolSelection(
                tool_name="library_scan",
                arguments={},
                reasoning="Manual routing: Library scan keywords detected"
            )
        elif any(keyword in message_lower for keyword in ['download', 'torrent']) and not any(keyword in message_lower for keyword in ['movie', 'film']):
            if any(keyword in message_lower for keyword in ['status', 'progress', 'downloading']):
                return ToolSelection(
                    tool_name="torrent_status",
                    arguments={},
                    reasoning="Manual routing: Download status keywords detected"
                )
            else:
                return ToolSelection(
                    tool_name="torrent_search",
                    arguments={"query": user_message},
                    reasoning="Manual routing: Download search keywords detected"
                )
        else:
            return ToolSelection(
                tool_name="movie_search",
                arguments={"query": user_message, "max_results": 5},
                reasoning="Manual routing: Default to movie search"
            )
    
    def get_available_tools(self) -> List[str]:
        return self.available_tools.copy()