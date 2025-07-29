"""Workflow graph implementation for the turtle app."""

from typing import Dict

from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from turtleapp.src.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_supervisor_llm
from turtleapp.src.nodes.agents import library_manager_agent, movie_retriever_agent, torrent_agent
from turtleapp.src.nodes import SupervisorNodeCreator, ToolAgent
from turtleapp.src.utils import logger
from turtleapp.src.utils.memory_utils import create_thread_id


class WorkflowGraph:
    """Multi-agent workflow graph for home theater management."""

    def __init__(self, tools: Dict[str, ToolAgent], name: str) -> None:
        self.supervisor_llm = create_supervisor_llm()

        self.name: str = name
        self.nodes: Dict[str, ToolAgent] = tools
        self.compiled_graph: CompiledStateGraph = None
    
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
        
        memory_saver = MemorySaver()
        self.compiled_graph = builder.compile(checkpointer=memory_saver)
        self.compiled_graph.name = self.name
        return self.compiled_graph
    
    async def invoke_with_thread(
        self, 
        message: str, 
        thread_id: str = None,
        recursion_limit: int = 10
    ) -> tuple[dict, str]:
        """Invoke the graph with proper config structure and thread management.
        
        Returns:
            Tuple of (result, thread_id) where thread_id is the one used for the request
        """
        if not thread_id:
            thread_id = str(create_thread_id())
        
        result = await self.compiled_graph.ainvoke(
            {"messages": message},
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": recursion_limit
            }
        )
        
        return result, thread_id


agentic_tools = {
    movie_retriever_agent.name: movie_retriever_agent,
    torrent_agent.name: torrent_agent,
    library_manager_agent.name: library_manager_agent
    }

graph_name = "Multi-agent Movie Supervisor"
movie_workflow_agent = WorkflowGraph(tools=agentic_tools, name=graph_name)
movie_workflow_graph: CompiledStateGraph = movie_workflow_agent.compile()

if __name__ == '__main__':
    import asyncio
    
    async def test_workflow():
        result, thread_id = await movie_workflow_agent.invoke_with_thread(
            "tell me the plot of poseidon movie?", 
            thread_id="gen_int_13"
        )
        logger.info(f"Workflow result: {result['messages'][-1].content}")
        logger.info(f"Thread ID: {thread_id}")
    
    asyncio.run(test_workflow())
