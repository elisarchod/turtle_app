from typing import Callable
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from turtleapp.config.settings import supervisor_model_name
from turtleapp.src.nodes.agents import retriever_node, torrent_node, movie_scanner_node
from turtleapp.src.nodes.supervisor import SupervisorNodeCreator
from turtleapp.src.core.tools.retriever_movie_summaries import retriever_tool
from turtleapp.src.core.tools.tools_torrent import torrent_info_tool
from turtleapp.src.core.tools.movie_scanner import movie_scanner_tool

NODE_FUNCTIONS = {node.name: node for node in [retriever_node, torrent_node, movie_scanner_node]}

class MovieWorkflowGraph:
    def __init__(self, supervisor_model_name: str = supervisor_model_name):
        self.supervisor_llm = ChatOpenAI(temperature=0, model=supervisor_model_name)
        
        # Use tool names directly - they're now descriptive enough
        self.node_functions = {
            retriever_tool.name: retriever_node,
            torrent_info_tool.name: torrent_node,
            movie_scanner_tool.name: movie_scanner_node
        }
    
    def compile(self) -> CompiledStateGraph:
        builder = StateGraph(MessagesState)
        
        supervisor_node = SupervisorNodeCreator(self.supervisor_llm, members=list(self.node_functions.keys()))
        builder.add_edge(START, "supervisor")
        builder.add_node("supervisor", supervisor_node)
        
        for agent_name, agent_function in self.node_functions.items():
            builder.add_node(agent_name, agent_function)
        
        compiled_graph = builder.compile(checkpointer=MemorySaver())
        compiled_graph.name = "Multi-agent Movie Supervisor"
        return compiled_graph


def create_movie_workflow() -> CompiledStateGraph:
    return MovieWorkflowGraph().compile()


home_agent = create_movie_workflow()