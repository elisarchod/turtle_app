"""Agent instances and node functions for the multi-agent workflow."""

from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langgraph.graph import MessagesState
from langgraph.types import Command

from core.constants import SUPERVISOR_NODE
from infrastructure.vector_store.pinecone_retriever import movie_retriever_tool
from infrastructure.smb.library_manager import library_manager_tool
from infrastructure.subtitles.subtitle_tools import subtitle_search_tool, subtitle_download_tool
from application.agents.tool_agent import ToolAgent
from application.agents.prompts import MOVIE_RETRIEVER_PROMPT, TORRENT_AGENT_PROMPT, SUBTITLE_MANAGER_PROMPT


def library_scan_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    """Direct library scan without ReAct reasoning.

    This node bypasses the ReAct agent pattern and directly invokes the library
    manager tool. This design choice is made because:
    1. Library scanning is deterministic - no tool selection needed
    2. The tool itself handles intelligent parsing of user intent
    3. Avoids unnecessary LLM reasoning overhead for simple operations

    The tool receives the raw user message and performs:
    - Intent parsing (scan all vs search specific movie)
    - Format extraction (mp4, mkv, etc.)
    - Smart search with fuzzy matching
    - Context-aware result formatting
    """
    try:
        # Get user's latest message
        latest_message = state["messages"][-1].content if state["messages"] else ""

        # Tool now receives full message for intelligent parsing
        result = library_manager_tool._run(latest_message)

        return Command(
            update={"messages": [HumanMessage(content=result)]},
            goto=SUPERVISOR_NODE
        )
    except Exception as e:
        error_msg = f"Library scan failed: {str(e)}"
        return Command(
            update={"messages": [HumanMessage(content=error_msg)]},
            goto=SUPERVISOR_NODE
        )


movie_retriever_agent = ToolAgent([movie_retriever_tool], specialized_prompt=MOVIE_RETRIEVER_PROMPT)

# Subtitle manager agent - uses search and download tools
subtitle_agent = ToolAgent(
    [subtitle_search_tool, subtitle_download_tool],
    name="subtitle_manager_agent",
    specialized_prompt=SUBTITLE_MANAGER_PROMPT
)


def create_torrent_agent(tools: list[Tool]) -> ToolAgent:
    """Factory that builds the download manager agent with the given MCP tools."""
    return ToolAgent(
        tools,
        name="movies_download_manager",
        specialized_prompt=TORRENT_AGENT_PROMPT
    )
