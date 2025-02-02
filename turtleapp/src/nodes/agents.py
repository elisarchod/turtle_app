from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from turtleapp.configuration import agent_model
from turtleapp.src.tools.random_number_gen import rand_gen
from turtleapp.src.tools.retriver_movie_summeries import retriever_tool
from turtleapp.src.tools.tools_torrent import torrent_info_tool

llm = ChatOpenAI(temperature=0, model=agent_model)

def create_node(tool: Tool,
                state: MessagesState,
                name: str) -> Command[Literal["supervisor"]]:
    data_retriever_agent: CompiledGraph = create_react_agent(llm,
                                                       tools=[tool],
                                                       state_modifier=SystemMessage("you are a super executione tool and you interact with "
                                                                                    f"the following tool and assert it gives good results {tool.description}" ))
    data_retriever_agent.name = name
    result = data_retriever_agent.invoke(state)["messages"][-1].content
    return Command(update={"messages": [HumanMessage(content=result)]}, goto="supervisor")


def retriver_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return create_node(retriever_tool,
                       state,
                       "data_retriever_agent")


def coder_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return create_node(rand_gen,
                       state,
                       "python_functions_agent")


def torrent_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    return create_node(torrent_info_tool,
                       state,
                       "torrent_download_client_agent")


data_retriever_agent: CompiledGraph = create_react_agent(llm,
                                                   tools=[retriever_tool],
                                                   state_modifier=SystemMessage(
                                                       "you are a super executione tool and you interact with "
                                                       f"the following tool and assert it gives good results {tool.description}"))
data_retriever_agent.name = "data_retriever_agent"


if __name__ == '__main__':
    retriver_node({"messages": "recommend 3 comedy movies"}).update["messages"][-1].pretty_print()
    retriver_node({"messages": "explain the plot of terminator 2"}).update["messages"][-1].pretty_print()

