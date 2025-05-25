from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from turtleapp.config.settings import agent_model
from turtleapp.src.core.agents.base import BaseAgent
from turtleapp.src.core.tools.random_number_gen import rand_gen
from turtleapp.src.core.tools.retriver_movie_summeries import retriever_tool
from turtleapp.src.core.tools.tools_torrent import torrent_info_tool

class ToolAgent(BaseAgent):
    def __init__(self, tool: Tool, name: str):
        super().__init__(ChatOpenAI(temperature=0, model=agent_model))
        self.tool = tool
        self.name = name
        self.agent = create_react_agent(
            self.llm,
            tools=[tool],
            state_modifier=SystemMessage(
                f"you are a super executione tool and you interact with the following tool and assert it gives good results {tool.description}"
            )
        )
        self.agent.name = name

    def process(self, state: MessagesState) -> Command[Literal["supervisor"]]:
        result = self.agent.invoke(state)["messages"][-1].content
        return Command(update={"messages": [HumanMessage(content=result)]}, goto="supervisor")

def retriver_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return ToolAgent(retriever_tool, "data_retriever_agent").process(state)

def coder_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return ToolAgent(rand_gen, "python_functions_agent").process(state)

def torrent_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return ToolAgent(torrent_info_tool, "torrent_download_client_agent").process(state)

if __name__ == '__main__':
    retriver_node({"messages": "recommend 3 comedy movies"}).update["messages"][-1].pretty_print()
    retriver_node({"messages": "explain the plot of terminator 2"}).update["messages"][-1].pretty_print()

