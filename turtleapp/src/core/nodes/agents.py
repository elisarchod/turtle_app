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
from turtleapp.src.core.prompts import AGENT_BASE_PROMPT, MOVIE_RETRIEVER_PROMPT
from turtleapp.src.core.tools import library_manager_tool, movie_retriever_tool
from turtleapp.src.core.mcp.tools import get_qbittorrent_tools



class ToolAgent:
    """Specialized agent that uses specific tools to complete tasks."""

    def __init__(self, tools: List[Tool], name: str = None, specialized_prompt: PromptTemplate = None) -> None:
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
    """Direct library scan without ReAct reasoning."""
    try:
        result = library_manager_tool._run("")
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
    name="movies_download_manager"
    # No specialized_prompt - uses AGENT_BASE_PROMPT default
)