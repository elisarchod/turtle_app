from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from turtleapp.settings import settings
from turtleapp.src.core.agents.base import BaseAgent
from turtleapp.src.utils import logger

class ToolAgent(BaseAgent):
    def __init__(self, tool: Tool):
        super().__init__(ChatOpenAI(temperature=0, model=settings.openai.embedding_model))
        self.tool = tool
        self.name = f"{tool.name}_agent"
        logger.info(f"Initializing ToolAgent for tool: {tool.name}")
        self.agent = create_react_agent(
            self.llm,
            tools=[tool],
            state_modifier=SystemMessage(
                f"you are a super execution tool and you interact with the following tool and assert it gives good results {tool.description}"
            )
        )
        self.agent.name = self.name

    def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        logger.info(f"Processing request with {self.name}")
        result = self.agent.invoke(state)["messages"][-1].content
        logger.info(f"ToolAgent {self.name} completed processing")
        return Command(update={"messages": [HumanMessage(content=result)]}, goto="supervisor")

