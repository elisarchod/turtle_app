"""Tool agent implementation for the turtle app."""

from typing import Literal, List

from langchain.agents import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langgraph.graph import MessagesState
from langgraph.types import Command

from turtleapp.src.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_agent_llm
from turtleapp.src.utils import logger


class ToolAgent:
    """A generic tool agent that wraps one or more tools with a ReAct agent."""

    def __init__(self, tools: List[Tool], name: str = None) -> None:
        self.llm = create_agent_llm()
        self.tools = tools
        self.name = name or f"{tools[0].name}_agent"
            
        logger.info(f"Initializing {self.name}")
        
        tool_descriptions = [f"- {tool.name}: {tool.description}" for tool in self.tools]
        description = (
            f"You are a specialized execution agent with access to the following tools:\n"
            f"{chr(10).join(tool_descriptions)}\n\n"
            f"Instructions:\n"
            f"- Use the appropriate tool based on the user's request\n"
            f"- Provide accurate and complete results\n"
            f"- If multiple tools are available, choose the most relevant one\n"
            f"- Always execute the tool to completion before responding\n\n"
            f"{{input}}\n\n{{agent_scratchpad}}"
        )
        
        prompt = PromptTemplate(
            template=description,
            input_variables=["input", "agent_scratchpad"]
        )
        
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
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
                goto=SUPERVISOR_NODE
            )
        except Exception as e:
            # Use the error handler for consistent logging
            error_msg = f"ToolAgent error in {self.name}: {str(e)}"
            logger.error(error_msg)
            error_message = f"Error processing request with {self.name}: {str(e)}"
            return Command(
                update={"messages": [HumanMessage(content=error_message)]},
                goto=SUPERVISOR_NODE
            )

