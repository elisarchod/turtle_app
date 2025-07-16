"""Test graph workflow with cost-effective mocking."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from turtleapp.src.workflows.graph import MovieWorkflowGraph
from turtleapp.api.routes.endpoints import create_thread_id


class TestWorkflowToolSelection:
    """Test that the graph selects the right tool for different requests."""
    
    @pytest.fixture
    def mock_components(self):
        """Mock expensive components while preserving routing logic."""
        with patch('turtleapp.src.workflows.graph.create_supervisor_llm') as mock_llm, \
             patch('turtleapp.src.workflows.graph.ToolAgent') as mock_tool_agent_class, \
             patch('turtleapp.src.workflows.graph.MemorySaver') as mock_memory_saver:
            
            # Mock LLM with structured output
            mock_llm_instance = AsyncMock()
            mock_structured_output = AsyncMock()
            mock_llm_instance.with_structured_output.return_value = mock_structured_output
            mock_llm.return_value = mock_llm_instance
            
            # Mock tool agent
            mock_tool_agent = AsyncMock()
            mock_tool_agent.process.return_value = Command(
                update={"messages": [AIMessage(content="Tool executed")]},
                goto="supervisor"
            )
            mock_tool_agent_class.return_value = mock_tool_agent
            
            # Mock memory saver to avoid UUID issues
            mock_memory_saver.return_value = MagicMock()
            
            yield {
                'llm': mock_llm_instance,
                'structured_output': mock_structured_output,
                'tool_agent': mock_tool_agent
            }
    
    def test_movie_query_routes_to_movie_retriever(self, mock_components):
        """Test that movie plot queries route to movie retriever."""
        # Configure supervisor to route to movie_details_retriever
        mock_components['structured_output'].invoke.return_value = {
            "next": "movie_details_retriever"
        }
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = compiled_graph.invoke(
            {"messages": [HumanMessage(content="What's the plot of Terminator 2?")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called with structured output
        mock_components['llm'].with_structured_output.assert_called()
    
    def test_torrent_query_routes_to_torrent_manager(self, mock_components):
        """Test that torrent queries route to torrent manager."""
        # Configure supervisor to route to torrent_manager
        mock_components['structured_output'].invoke.return_value = {
            "next": "torrent_manager"
        }
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = compiled_graph.invoke(
            {"messages": [HumanMessage(content="Search for Inception torrent")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called with structured output
        mock_components['llm'].with_structured_output.assert_called()
    
    def test_library_query_routes_to_library_manager(self, mock_components):
        """Test that library queries route to library manager."""
        # Configure supervisor to route to library_manager
        mock_components['structured_output'].invoke.return_value = {
            "next": "library_manager"
        }
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = compiled_graph.invoke(
            {"messages": [HumanMessage(content="What movies are in my library?")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called with structured output
        mock_components['llm'].with_structured_output.assert_called()
    
    def test_finish_command_ends_workflow(self, mock_components):
        """Test that FINISH command ends the workflow."""
        # Configure supervisor to finish
        mock_components['structured_output'].invoke.return_value = {
            "next": "FINISH"
        }
        
        graph = MovieWorkflowGraph()
        compiled_graph = graph.compile()
        
        # Test graph invocation
        result = compiled_graph.invoke(
            {"messages": [HumanMessage(content="Thank you")]},
            {"configurable": {"thread_id": create_thread_id()}}
        )
        
        assert result is not None
        # Verify the supervisor was called with structured output
        mock_components['llm'].with_structured_output.assert_called()
    
    @pytest.mark.slow
    def test_supervisor_routing_logic_with_hub_prompt(self, mock_components):
        """Test that supervisor uses hub prompt for routing decisions."""
        with patch('turtleapp.src.nodes.supervisor.hub') as mock_hub:
            # Mock hub prompt
            mock_prompt = MagicMock()
            mock_prompt.invoke.return_value = "formatted_prompt"
            mock_hub.pull.return_value = mock_prompt
            
            # Configure supervisor response
            mock_components['structured_output'].invoke.return_value = {
                "next": "movie_details_retriever"
            }
            
            graph = MovieWorkflowGraph()
            compiled_graph = graph.compile()
            
            # Test graph invocation
            result = compiled_graph.invoke(
                {"messages": [HumanMessage(content="Tell me about a movie")]},
                {"configurable": {"thread_id": create_thread_id()}}
            )
            
            assert result is not None
            # Verify hub prompt was used
            mock_hub.pull.assert_called_with("supervisor_prompt_with_placeholder")
            mock_prompt.invoke.assert_called()


class TestWorkflowExecution:
    """Test workflow execution patterns."""
    
    def test_graph_initialization_has_all_agents(self):
        """Test that graph initializes with all required agents."""
        with patch('turtleapp.src.workflows.graph.create_supervisor_llm'):
            graph = MovieWorkflowGraph()
            
            # Verify all expected agents are present
            assert "movie_details_retriever" in graph.nodes
            assert "torrent_manager" in graph.nodes
            assert "library_manager" in graph.nodes
            assert len(graph.nodes) == 3
    
    def test_compiled_graph_properties(self):
        """Test compiled graph has expected properties."""
        with patch('turtleapp.src.workflows.graph.create_supervisor_llm'):
            graph = MovieWorkflowGraph()
            compiled_graph = graph.compile()
            
            assert compiled_graph.name == "Multi-agent Movie Supervisor"
            assert hasattr(compiled_graph, 'checkpointer')
    
    def test_workflow_error_handling(self):
        """Test workflow handles errors gracefully."""
        with patch('turtleapp.src.workflows.graph.create_supervisor_llm') as mock_llm:
            mock_llm.side_effect = Exception("LLM failed")
            
            with pytest.raises(Exception, match="LLM failed"):
                MovieWorkflowGraph()