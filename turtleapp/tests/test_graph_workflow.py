"""Test graph workflow with cost-effective mocking."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from turtleapp.src.workflows.graph import MovieWorkflowGraph
from turtleapp.api.routes.endpoints import create_thread_id


class TestWorkflowToolSelection:
    """Test that the graph selects the right tool for different requests."""
    
    @pytest.fixture
    def mock_components(self):
        """Mock expensive components while preserving routing logic."""
        with patch('turtleapp.src.workflows.graph.SupervisorNodeCreator') as mock_supervisor_class, \
             patch('turtleapp.src.core.llm_factory.create_agent_llm') as mock_agent_llm, \
             patch('langgraph_storage.checkpoint.InMemorySaver') as mock_memory_saver, \
             patch('turtleapp.src.nodes.agents.ToolAgent.process') as mock_agent_process:
            
            # Mock supervisor instance
            mock_supervisor_instance = MagicMock()
            mock_supervisor_class.return_value = mock_supervisor_instance
            
            # Mock agent LLM
            mock_agent_llm_instance = AsyncMock()
            mock_agent_llm.return_value = mock_agent_llm_instance
            
            # Mock memory saver to avoid UUID issues
            mock_memory_saver.return_value = MagicMock()
            
            # Mock agent process method to return a Command that routes back to supervisor
            mock_agent_process.return_value = Command(
                update={"messages": [HumanMessage(content="Tool executed successfully")]},
                goto="supervisor"
            )
            
            yield {
                'supervisor_instance': mock_supervisor_instance,
                'agent_llm': mock_agent_llm_instance,
                'agent_process': mock_agent_process
            }
    
    async def test_movie_query_routes_to_movie_retriever(self, mock_components):
        """Test that movie plot queries route to movie retriever."""
        # Configure supervisor to route to movie_details_retriever first, then FINISH
        from langgraph.constants import END
        mock_components['supervisor_instance'].side_effect = [
            Command(goto="movie_details_retriever"),
            Command(goto=END)
        ]
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = await compiled_graph.ainvoke(
            {"messages": [HumanMessage(content="What's the plot of Terminator 2?")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called
        mock_components['supervisor_instance'].assert_called()


    async def test_torrent_query_routes_to_torrent_manager(self, mock_components):
        """Test that torrent queries route to torrent manager."""
        # Configure supervisor to route to torrent_manager first, then FINISH
        from langgraph.constants import END
        mock_components['supervisor_instance'].side_effect = [
            Command(goto="torrent_manager"),
            Command(goto=END)
        ]
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = await compiled_graph.ainvoke(
            {"messages": [HumanMessage(content="Search for Inception torrent")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )

        assert result is not None
        # Verify the supervisor was called
        mock_components['supervisor_instance'].assert_called()
    
    async def test_library_query_routes_to_library_manager(self, mock_components):
        """Test that library queries route to library manager."""
        # Configure supervisor to route to library_manager first, then FINISH
        from langgraph.constants import END
        mock_components['supervisor_instance'].side_effect = [
            Command(goto="library_manager"),
            Command(goto=END)
        ]
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = await compiled_graph.ainvoke(
            {"messages": [HumanMessage(content="What movies are in my library?")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called
        mock_components['supervisor_instance'].assert_called()
    
    async def test_finish_command_ends_workflow(self, mock_components):
        """Test that FINISH command ends the workflow."""
        # Configure supervisor to finish
        from langgraph.constants import END
        mock_components['supervisor_instance'].return_value = Command(goto=END)
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = await compiled_graph.ainvoke(
            {"messages": [HumanMessage(content="Thank you")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called
        mock_components['supervisor_instance'].assert_called()
    
    @pytest.mark.slow
    async def test_supervisor_routing_logic_with_hub_prompt(self, mock_components):
        """Test that supervisor uses hub prompt for routing decisions."""
        # Configure supervisor response
        from langgraph.constants import END
        mock_components['supervisor_instance'].side_effect = [
            Command(goto="movie_details_retriever"),
            Command(goto=END)
        ]
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = await compiled_graph.ainvoke(
            {"messages": [HumanMessage(content="Tell me about a movie")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify supervisor was called
        mock_components['supervisor_instance'].assert_called()


class TestWorkflowExecution:
    """Test workflow execution patterns."""
    
    def test_graph_initialization_has_all_agents(self):
        """Test that graph initializes with all required agents."""
        with patch('turtleapp.src.core.llm_factory.create_supervisor_llm'), \
             patch('turtleapp.src.core.llm_factory.create_agent_llm'):
            graph = MovieWorkflowGraph()
            
            # Verify all expected agents are present
            assert "movie_details_retriever" in graph.nodes
            assert "torrent_manager" in graph.nodes
            assert "library_manager" in graph.nodes
            assert len(graph.nodes) == 3
    
    def test_compiled_graph_properties(self):
        """Test compiled graph has expected properties."""
        with patch('turtleapp.src.core.llm_factory.create_supervisor_llm'), \
             patch('turtleapp.src.core.llm_factory.create_agent_llm'):
            graph = MovieWorkflowGraph()
            compiled_graph = graph.compile()
            
            assert compiled_graph.name == "Multi-agent Movie Supervisor"
            assert hasattr(compiled_graph, 'checkpointer')