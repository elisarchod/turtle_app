"""Workflow graph implementation for the turtle app."""

from typing import Dict, Union, Callable

from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from turtleapp.src.core.constants import SUPERVISOR_NODE
from turtleapp.src.core.llm_factory import create_supervisor_llm
from turtleapp.src.core.nodes import library_scan_node, movie_retriever_agent, torrent_agent, subtitle_agent
from turtleapp.src.core.nodes import SupervisorNodeCreator, ToolAgent
from turtleapp.src.utils.memory_utils import create_thread_id


class WorkflowGraph:
    """Multi-agent workflow graph for home theater management."""

    def __init__(self, tools: Dict[str, Union[ToolAgent, Callable]], name: str) -> None:
        """Initialize workflow graph with agents and system context.

        Args:
            tools: Dictionary mapping agent names to agent instances. Keys must match
                  the routing names used by the supervisor. Values can be:
                  - ToolAgent instances (ReAct agents with tools)
                  - Direct callable node functions (like library_scan_node)
            name: Human-readable workflow name for logging and context

        The workflow context is injected only into ToolAgent instances to inform them
        of available specialists and the supervisor routing pattern. Direct node
        functions don't receive this context since they don't perform reasoning.
        """
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
        """Compile the workflow graph with supervisor and agent nodes.

        Creates a LangGraph StateGraph with:
        1. START edge pointing to supervisor (entry point)
        2. Supervisor node for routing decisions
        3. Agent nodes (either ToolAgent.process or direct callables)
        4. MemorySaver checkpointer for conversation persistence

        The supervisor is responsible for all routing decisions. Agent nodes
        automatically return to supervisor after completion. Supervisor decides
        when to route to END to terminate the conversation.

        Returns:
            Self for method chaining (e.g., WorkflowGraph(...).compile())
        """
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
        """Execute workflow with conversation state persistence.

        Invokes the compiled graph with proper thread management for conversation
        history. Each thread maintains its own conversation state via MemorySaver
        checkpointer, enabling multi-turn dialogues.

        Args:
            message: User's input message to process
            thread_id: Optional conversation thread ID. If not provided, a new UUID
                      will be auto-generated with timestamp (YYYYMMDD_HHMMSS_uuid).
                      Use the same thread_id for follow-up messages in a conversation.
            recursion_limit: Maximum agent routing hops before terminating (default 10).
                            Prevents infinite loops if agents keep routing to each other.

        Returns:
            Tuple of (result, thread_id) where:
            - result: Dict with 'messages' key containing full conversation history
            - thread_id: The thread ID used (either provided or auto-generated)

        Example:
            result, tid = graph.invoke("Find action movies")
            # Continue conversation with same thread
            result2, _ = graph.invoke("Which ones are available?", thread_id=tid)
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
    """Create and compile the home theater management workflow.

    Instantiates all specialized agents and wires them into a multi-agent workflow:
    - movie_retriever_agent: Search movie database via Pinecone vector store
    - movies_download_manager: Manage torrent downloads via qBittorrent MCP server
    - library_manager_agent: Scan SMB/CIFS network shares for local movies
    - subtitle_manager_agent: Search and download movie subtitles

    Agent names in the dictionary must match the routing names used in the
    supervisor's prompt to ensure proper request routing.

    Returns:
        Compiled WorkflowGraph ready for invocation
    """
    agentic_tools = {
        movie_retriever_agent.name: movie_retriever_agent,
        torrent_agent.name: torrent_agent,
        "library_manager_agent": library_scan_node,
        subtitle_agent.name: subtitle_agent
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
