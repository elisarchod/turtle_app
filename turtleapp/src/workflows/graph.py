"""Workflow graph implementation for the turtle app."""

from typing import Dict, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph_storage.checkpoint import InMemorySaver

from turtleapp.src.nodes import ToolAgent, SupervisorNodeCreator
from turtleapp.src.core.tools import movie_retriever_tool, torrent_downloads_tool, torrent_search_tool, library_manager_tool
from turtleapp.src.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_supervisor_llm
from turtleapp.src.utils import logger


class MovieWorkflowGraph:
    """Multi-agent workflow graph for home theater management."""

    def __init__(self) -> None:
        self.supervisor_llm = create_supervisor_llm()
        
        self.nodes: Dict[str, ToolAgent] = {
            movie_retriever_tool.name: ToolAgent([movie_retriever_tool]),
            "torrent_manager": ToolAgent([torrent_downloads_tool, torrent_search_tool], name="torrent_manager_agent"),
            library_manager_tool.name: ToolAgent([library_manager_tool])
        }
    
    def compile(self) -> CompiledStateGraph:
        builder = StateGraph(MessagesState)
        supervisor_node = SupervisorNodeCreator(
            self.supervisor_llm,
            members=list(self.nodes.keys())
        )
        
        builder.add_edge(START, SUPERVISOR_NODE)
        builder.add_node(SUPERVISOR_NODE, supervisor_node)
        
        for agent_name, agent in self.nodes.items():
            builder.add_node(agent_name, agent.process)
        
        compiled_graph = builder.compile(checkpointer=InMemorySaver())
        compiled_graph.name = "Multi-agent Movie Supervisor"
        return compiled_graph

movie_workflow_agent: CompiledStateGraph = MovieWorkflowGraph().compile()


if __name__ == '__main__':
    config = {"configurable": {"thread_id": "gen_int_13"}}
    result = movie_workflow_agent.invoke(
        {"messages": "tell me the plot of terminator 2 ?"},
        config=config
    )
    logger.info(f"Workflow result: {result['messages'][-1].content}")
