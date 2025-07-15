"""Tool agent implementation for the turtle app."""

from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langgraph.graph import MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from turtleapp.src.constants import NodeNames
from turtleapp.src.core.llm_factory import create_agent_llm
from turtleapp.src.utils import logger


class ToolAgent:
    """A generic tool agent that wraps any tool with a ReAct agent."""

    def __init__(self, tool: Tool) -> None:
        self.llm = create_agent_llm()
        self.name = f"{tool.name}_agent"
        logger.info(f"Initializing {self.name}")
        
        self.tool = tool
        self.agent = create_react_agent(
            self.llm,
            tools=[tool],
            state_modifier=SystemMessage(
                f"You are a specialized execution agent that interacts with the following tool "
                f"and ensures it provides accurate results: {tool.description}"
            )
        )
        self.agent.name = self.name

    async def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        logger.info(f"Processing request with {self.name}")
        
        try:
            result = await self.agent.ainvoke(state)
            content = result["messages"][-1].content
            logger.info(f"ToolAgent {self.name} completed processing")
            
            return Command(
                update={"messages": [HumanMessage(content=content)]},
                goto=NodeNames.SUPERVISOR.value
            )
        except Exception as e:
            logger.error(f"ToolAgent {self.name} failed: {str(e)}")
            error_message = f"Error processing request with {self.name}: {str(e)}"
            return Command(
                update={"messages": [HumanMessage(content=error_message)]},
                goto=NodeNames.SUPERVISOR.value
            )

