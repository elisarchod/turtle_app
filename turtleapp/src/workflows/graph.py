"""Workflow graph implementation for the turtle app."""

from typing import Dict, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph_storage.checkpoint import InMemorySaver

from turtleapp.src.core.tools import library_manager, movie_retriever,torrent_agent
from turtleapp.src.nodes import ToolAgent, SupervisorNodeCreator

from turtleapp.src.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_supervisor_llm
from turtleapp.src.utils import logger


class WorkflowGraph:
    """Multi-agent workflow graph for home theater management."""

    def __init__(self, tools: Dict[str, ToolAgent], name: str) -> None:
        self.supervisor_llm = create_supervisor_llm()

        self.name: str = name
        self.nodes: Dict[str, ToolAgent] = tools
    
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
        compiled_graph.name = self.name
        return compiled_graph


agentic_tools = {
    movie_retriever.name: movie_retriever,
    torrent_agent.name:   torrent_agent,
    library_manager.name: library_manager
    }

graph_name = "Multi-agent Movie Supervisor"
movie_workflow_graph: CompiledStateGraph = WorkflowGraph(tools=agentic_tools,
                                                         name=graph_name).compile()

if __name__ == '__main__':

    result = movie_workflow_graph.ainvoke(
        {"messages": "tell me the plot of terminator 2 ?"},
        config={"configurable": {"thread_id": "gen_int_13"}}
    )
    logger.info(f"Workflow result: {result['messages'][-1].content}")
