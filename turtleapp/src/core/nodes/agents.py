"""Specialized agents for the turtle app multi-agent system."""

from typing import Literal, List

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langgraph.graph import MessagesState
from langgraph.types import Command

from turtleapp.src.core.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_agent_llm
from turtleapp.src.core.prompts import AGENT_BASE_PROMPT, MOVIE_RETRIEVER_PROMPT, TORRENT_AGENT_PROMPT, SUBTITLE_MANAGER_PROMPT
from turtleapp.src.core.tools import library_manager_tool, movie_retriever_tool, subtitle_search_tool, subtitle_download_tool
from turtleapp.src.core.mcp.tools import get_qbittorrent_tools



class ToolAgent:
    """Specialized agent that uses specific tools to complete tasks."""

    def __init__(self, tools: List[Tool], name: str = None, specialized_prompt: PromptTemplate = None) -> None:
        """Initialize a ReAct-based agent with specific tools and expertise.

        Creates an agent using the ReAct pattern (Reasoning + Acting) which allows
        the LLM to reason about which tool to use, take an action with that tool,
        observe the result, and repeat until the task is complete.

        Args:
            tools: List of LangChain tools this agent can use. Each tool represents
                  a specific capability (e.g., search movies, download torrents).
            name: Agent name for routing and logging. Defaults to "{first_tool}_agent".
            specialized_prompt: Custom prompt template that defines the agent's
                              expertise and behavior. Falls back to AGENT_BASE_PROMPT.

        Configuration details:
            - Uses Claude Haiku for cost-effective reasoning
            - max_iterations=3: Limits reasoning loops to prevent infinite cycles
            - handle_parsing_errors=True: Gracefully handles malformed tool calls
            - After completion, agent always returns control to supervisor
        """
        self.tools = tools
        self.name = name or f"{tools[0].name}_agent"
        self.llm = create_agent_llm()

        prompt = specialized_prompt or AGENT_BASE_PROMPT

        react_agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        self.agent = AgentExecutor(
            agent=react_agent,
            tools=self.tools,
            handle_parsing_errors=True,
            max_iterations=3
        )

    def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        """Execute agent's task and return control to supervisor.

        This is the LangGraph node function that:
        1. Extracts the latest user message from state
        2. Invokes the ReAct agent to complete the task using its tools
        3. Updates the conversation state with the agent's response
        4. Returns control to the supervisor for next routing decision

        The supervisor will decide whether to route to another agent or end
        the conversation based on the updated state.

        Args:
            state: Current conversation state with message history

        Returns:
            Command that updates messages and routes back to SUPERVISOR_NODE
        """
        if not state["messages"]:
            return Command(
                update={"messages": [HumanMessage(content="No message provided")]},
                goto=SUPERVISOR_NODE
            )

        latest_message = state["messages"][-1].content
        result = self.agent.invoke({"input": latest_message})

        return Command(
            update={"messages": [HumanMessage(content=result["output"])]},
            goto=SUPERVISOR_NODE
        )


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

# Download manager agent - uses MCP tools from qBittorrent MCP server
torrent_agent = ToolAgent(
    get_qbittorrent_tools(),  # Returns all MCP tools ready to use
    name="movies_download_manager",
    specialized_prompt=TORRENT_AGENT_PROMPT
)

# Subtitle manager agent - uses search and download tools
subtitle_agent = ToolAgent(
    [subtitle_search_tool, subtitle_download_tool],
    name="subtitle_manager_agent",
    specialized_prompt=SUBTITLE_MANAGER_PROMPT
)