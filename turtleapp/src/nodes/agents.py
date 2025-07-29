"""Tool agent implementation for the turtle app."""

from typing import Literal, List

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langgraph.graph import MessagesState
from langgraph.types import Command
from langchain import hub

from turtleapp.src.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_agent_llm
from turtleapp.src.core.tools import library_manager_tool, movie_retriever_tool, torrent_download_tool, torrent_search_tool
from turtleapp.src.utils import logger


class ToolAgent:
    """A generic tool agent that wraps one or more tools with a ReAct agent."""

    def __init__(self, tools: List[Tool], name: str = None) -> None:
        self.llm = create_agent_llm()
        self.tools = tools
        self.name = name or f"{tools[0].name}_agent"
            
        logger.info(f"Initializing {self.name}")
        prompt = hub.pull("hwchase17/react")
        
        react_agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        self.agent = AgentExecutor(
            agent=react_agent, 
            tools=self.tools, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
        self.agent.name = self.name

    async def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        logger.info(f"Processing request with {self.name}")
        
        try:
            # Extract the latest message content
            latest_message = state["messages"][-1].content
            
            result = await self.agent.ainvoke({"input": latest_message})
            content = result["output"]
            logger.info(f"ToolAgent {self.name} completed processing")
            
            return Command(
                update={"messages": [HumanMessage(content=content)]},
                goto=SUPERVISOR_NODE
            )
        except Exception as e:
            error_msg = f"ToolAgent error in {self.name}: {str(e)}"
            logger.error(error_msg)
            error_message = f"Error processing request with {self.name}: {str(e)}"
            return Command(
                update={"messages": [HumanMessage(content=error_message)]},
                goto=SUPERVISOR_NODE
            )


movie_retriever_agent = ToolAgent([movie_retriever_tool]) # , "movie_details_retriever"
library_manager_agent = ToolAgent([library_manager_tool]) # , "movie_library_manager"
torrent_agent = ToolAgent([torrent_download_tool, torrent_search_tool], name="movies_download_manager")