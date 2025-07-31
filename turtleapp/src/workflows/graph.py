"""Workflow graph implementation for the turtle app."""

from typing import Dict, Union, Callable

from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from turtleapp.src.core.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_supervisor_llm
from turtleapp.src.core.nodes import library_scan_node, movie_retriever_agent, torrent_agent
from turtleapp.src.core.nodes import SupervisorNodeCreator, ToolAgent
from turtleapp.src.utils.memory_utils import create_thread_id


class WorkflowGraph:
    """Multi-agent workflow graph for home theater management."""

    def __init__(self, tools: Dict[str, Union[ToolAgent, Callable]], name: str) -> None:
        self.supervisor_llm = create_supervisor_llm()
        self.name: str = name
        self.nodes: Dict[str, Union[ToolAgent, Callable]] = tools
        
        # Add workflow context to ToolAgent instances only
        workflow_context = f"""
        You are part of the '{name}' multi-agent system.
        Available specialists: {', '.join(tools.keys())}
        
        After completing your task, control returns to the supervisor who may:
        - Route to another specialist if more work is needed
        - End the conversation if the task is complete
        
        Focus on your expertise and provide complete, helpful responses.
        """
        
        for agent in tools.values():
            if isinstance(agent, ToolAgent):
                agent.workflow_context = workflow_context
        
        self.compiled_graph: CompiledStateGraph = None
    
    def compile(self):
        """Compile the workflow graph and return self for chaining."""
        builder = StateGraph(MessagesState)
        supervisor_node = SupervisorNodeCreator(
            self.supervisor_llm,
            members=list(self.nodes.keys())
        )
        
        builder.add_edge(START, SUPERVISOR_NODE)
        builder.add_node(SUPERVISOR_NODE, supervisor_node)
        
        for agent_name, agent in self.nodes.items():
            if isinstance(agent, ToolAgent):
                builder.add_node(agent_name, agent.process)
            else:
                # Direct node function
                builder.add_node(agent_name, agent)
        
        memory_saver = MemorySaver()
        self.compiled_graph = builder.compile(checkpointer=memory_saver)
        self.compiled_graph.name = self.name
        return self
    
    def invoke(
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
        
        result = self.compiled_graph.invoke(
            {"messages": message},
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": recursion_limit
            }
        )
        
        return result, thread_id


def create_movie_workflow() -> WorkflowGraph:
    """Create movie workflow graph"""
    agentic_tools = {
        movie_retriever_agent.name: movie_retriever_agent,
        torrent_agent.name: torrent_agent,
        "library_manager_agent": library_scan_node
    }
    
    return (WorkflowGraph(tools=agentic_tools, name="Multi-agent Movie Supervisor")
            .compile())

# Global instances for backward compatibility
movie_workflow_agent = create_movie_workflow() 
movie_workflow_graph: CompiledStateGraph = movie_workflow_agent.compiled_graph


def run(message: str) -> str:
    """Simple sync entry point"""
    movie_graph = create_movie_workflow()
    result, _ = movie_graph.invoke(message)
    return result['messages'][-1].content

if __name__ == '__main__':
    # Interactive mode - just import and use run()
    print("🎬 Movie Workflow Interactive Debugging")
    print("Available functions:")
    print("  run('your message') - Simple sync entry point")
    print("  movie_workflow_agent.invoke('message') - Direct sync access")
    print("-" * 50)

    # Uncomment to test:
    question_1 = 'Tell me about movie Monkeybone 2'
    response = run('what movies available in my library')
    print(f"Response: {response}")
