from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from turtleapp.config.settings import agent_model_name
from turtleapp.src.core.agents.base import BaseAgent
from turtleapp.src.core.tools.retriever_movie_summaries import retriever_tool
from turtleapp.src.core.tools.tools_torrent import torrent_info_tool
from turtleapp.src.core.tools.movie_scanner import movie_scanner_tool

class ToolAgent(BaseAgent):
    def __init__(self, tool: Tool):
        super().__init__(ChatOpenAI(temperature=0, model=agent_model_name))
        self.tool = tool
        # Derive agent name from tool name for consistency
        self.name = f"{tool.name}_agent"
        self.agent = create_react_agent(
            self.llm,
            tools=[tool],
            state_modifier=SystemMessage(
                f"you are a super execution tool and you interact with the following tool and assert it gives good results {tool.description}"
            )
        )
        self.agent.name = self.name

    def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        result = self.agent.invoke(state)["messages"][-1].content
        return Command(update={"messages": [HumanMessage(content=result)]}, goto="supervisor")

def retriever_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return ToolAgent(retriever_tool).process(state)

def torrent_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return ToolAgent(torrent_info_tool).process(state)

def movie_scanner_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return ToolAgent(movie_scanner_tool).process(state)

if __name__ == '__main__':
    retriever_node({"messages": "recommend 3 comedy movies"}).update["messages"][-1].pretty_print()
    retriever_node({"messages": "explain the plot of terminator 2"}).update["messages"][-1].pretty_print()

