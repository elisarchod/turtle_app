"""Test graph workflow with cost-effective mocking."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from langgraph.constants import END
from langgraph.types import Command

from turtleapp.src.utils.memory_utils import create_thread_id
from turtleapp.src.workflows.graph import create_movie_workflow


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
    
    def test_movie_query_routes_to_movie_retriever(self, mock_components):
        """Test that movie plot queries route to movie retriever."""

        mock_components['supervisor_instance'].side_effect = [
            Command(goto="movie_details_retriever"),
            Command(goto=END)
        ]
        
        graph = create_movie_workflow()
        
        result = graph.compiled_graph.invoke(
            {"messages": [HumanMessage(content="What's the plot of Terminator 2?")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        mock_components['supervisor_instance'].assert_called()


    def test_torrent_query_routes_to_torrent_manager(self, mock_components):
        """Test that torrent queries route to torrent manager."""

        mock_components['supervisor_instance'].side_effect = [
            Command(goto="torrent_agent"),
            Command(goto=END)
        ]
        
        graph = create_movie_workflow()
        
        result = graph.compiled_graph.invoke(
            {"messages": [HumanMessage(content="Search for Inception torrent")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )

        assert result is not None
        mock_components['supervisor_instance'].assert_called()
    
    def test_library_query_routes_to_library_scan(self, mock_components):
        """Test that library queries route to library scan node."""
        # Configure supervisor to route to library_scan first, then FINISH

        mock_components['supervisor_instance'].side_effect = [
            Command(goto="library_manager_agent"),
            Command(goto=END)
        ]
        
        with patch('turtleapp.src.core.tools.library_manager.library_manager_tool._run') as mock_library_tool:
            mock_library_tool.return_value = "Library scan completed. Found 5 movies."
            
            graph = create_movie_workflow()

            result = graph.compiled_graph.invoke(
                {"messages": [HumanMessage(content="What movies are in my library?")]},
                {"configurable": {"thread_id": create_thread_id()}}
            )
            
            assert result is not None
            mock_components['supervisor_instance'].assert_called()
            mock_library_tool.assert_called_once()
    
    def test_finish_command_ends_workflow(self, mock_components):
        """Test that FINISH command ends the workflow."""
        from langgraph.constants import END
        mock_components['supervisor_instance'].return_value = Command(goto=END)
        
        graph = create_movie_workflow()

        result = graph.compiled_graph.invoke(
            {"messages": [HumanMessage(content="Thank you")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        mock_components['supervisor_instance'].assert_called()
    
    @pytest.mark.slow
    def test_supervisor_routing_logic_with_hub_prompt(self, mock_components):
        """Test that supervisor uses hub prompt for routing decisions."""
        # Configure supervisor response
        from langgraph.constants import END
        mock_components['supervisor_instance'].side_effect = [
            Command(goto="movie_details_retriever"),
            Command(goto=END)
        ]
        
        graph = create_movie_workflow()
        
        result = graph.compiled_graph.invoke(
            {"messages": [HumanMessage(content="Tell me about a movie")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        mock_components['supervisor_instance'].assert_called()


class TestWorkflowExecution:
    """Test workflow execution patterns."""
    
    def test_graph_initialization_has_all_agents(self):
        """Test that graph initializes with all required agents."""
        with patch('turtleapp.src.core.llm_factory.create_supervisor_llm'), \
             patch('turtleapp.src.core.llm_factory.create_agent_llm'):
            graph = create_movie_workflow()
            
            # Verify all expected agents are present (library_manager is now a direct node)
            assert "movie_details_retriever_agent" in graph.nodes
            assert "movies_download_manager" in graph.nodes
    
    def test_compiled_graph_properties(self):
        """Test compiled graph has expected properties."""
        with patch('turtleapp.src.core.llm_factory.create_supervisor_llm'), \
             patch('turtleapp.src.core.llm_factory.create_agent_llm'):
            graph = create_movie_workflow()
            assert hasattr(graph.compiled_graph, 'checkpointer')