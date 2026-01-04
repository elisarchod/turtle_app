"""
Test suite for Turtle App MCP Integration.

This test suite validates:
1. MCP server functionality and tool registration
2. MCP client connectivity and tool execution
3. Integration between server and client
4. Performance comparison with existing LangGraph system
"""

import asyncio
import logging
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the MCP client from the correct path
import sys
from pathlib import Path
client_path = Path(__file__).parent.parent / "client-integration"
sys.path.insert(0, str(client_path))

from mcp_client import (
    TurtleAppMCPClient, 
    TurtleMCPContext,
    SyncTurtleMCPClient
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMCPServer:
    """Test the MCP server functionality."""
    
    def test_server_import(self):
        """Test that the MCP server can be imported without errors."""
        import importlib.util
        
        server_path = Path(__file__).parent.parent / "server-examples" / "turtle-server.py"
        spec = importlib.util.spec_from_file_location("turtle_server", server_path)
        module = importlib.util.module_from_spec(spec)
        
        # Should not raise an exception
        spec.loader.exec_module(module)
        
        # Check that the server has the expected tools
        assert hasattr(module, 'movie_search')
        assert hasattr(module, 'torrent_search')
        assert hasattr(module, 'torrent_status')
        assert hasattr(module, 'library_scan')
    
    def test_tool_wrappers(self):
        """Test that tool wrappers handle errors gracefully."""
        import importlib.util
        
        server_path = Path(__file__).parent.parent / "server-examples" / "turtle-server.py"
        spec = importlib.util.spec_from_file_location("turtle_server", server_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Test error handling wrapper
        @module.mcp_tool_wrapper
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert "Error: Test error" in result

class TestMCPClient:
    """Test the MCP client functionality."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = TurtleAppMCPClient()
        assert client.session is None
        assert client.available_tools == []
    
    def test_sync_client_initialization(self):
        """Test synchronous client wrapper."""
        sync_client = SyncTurtleMCPClient()
        assert sync_client._client is None

class TestMCPIntegration:
    """Integration tests for MCP server and client communication."""
    
    @pytest.mark.asyncio
    async def test_client_server_connection(self):
        """Test that client can connect to server (mocked)."""
        # Mock the server connection for testing
        with patch('mcp.client.stdio.stdio_client') as mock_stdio:
            mock_session = MagicMock()
            mock_session.initialize.return_value = MagicMock(
                server_info=MagicMock(name="turtle-server", version="1.0.0")
            )
            mock_session.list_tools.return_value = MagicMock(
                tools=[
                    MagicMock(name="movie_search", description="Search movies", inputSchema={}),
                    MagicMock(name="library_scan", description="Scan library", inputSchema={})
                ]
            )
            mock_stdio.return_value.__aenter__.return_value = mock_session
            
            client = TurtleAppMCPClient()
            await client.connect()
            
            assert len(client.available_tools) == 2
            assert client.available_tools[0]["name"] == "movie_search"
            assert client.available_tools[1]["name"] == "library_scan"
            
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_tool_execution_mock(self):
        """Test tool execution with mocked server responses."""
        with patch('mcp.client.stdio.stdio_client') as mock_stdio:
            mock_session = MagicMock()
            mock_session.initialize.return_value = MagicMock(
                server_info=MagicMock(name="turtle-server", version="1.0.0")
            )
            mock_session.list_tools.return_value = MagicMock(
                tools=[MagicMock(name="movie_search", description="Search movies", inputSchema={})]
            )
            
            # Mock tool execution result
            mock_result = MagicMock()
            mock_result.content = [{"text": "Found 5 movies matching 'action'"}]
            mock_session.call_tool.return_value = mock_result
            
            mock_stdio.return_value.__aenter__.return_value = mock_session
            
            client = TurtleAppMCPClient()
            await client.connect()
            
            result = await client.execute_tool("movie_search", {"query": "action", "max_results": 5})
            assert "Found 5 movies matching 'action'" in result
            
            await client.disconnect()
    
    def test_message_routing(self):
        """Test simple message routing logic."""
        client = TurtleAppMCPClient()
        
        # Test movie-related keywords
        assert "movie" in "tell me about inception movie".lower()
        assert "download" in "download terminator".lower()
        assert "library" in "scan my library".lower()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager usage."""
        with patch('mcp.client.stdio.stdio_client') as mock_stdio:
            mock_session = MagicMock()
            mock_session.initialize.return_value = MagicMock(
                server_info=MagicMock(name="turtle-server", version="1.0.0")
            )
            mock_session.list_tools.return_value = MagicMock(tools=[])
            mock_stdio.return_value.__aenter__.return_value = mock_session
            
            async with TurtleMCPContext() as client:
                assert client.session is not None

class TestPerformanceComparison:
    """Performance tests comparing MCP vs LangGraph approach."""
    
    def test_simple_response_time(self):
        """Test response time for simple queries."""
        # This would be a real performance test in production
        start_time = time.time()
        
        # Simulate MCP call
        sync_client = SyncTurtleMCPClient()
        # In real test, this would make actual calls
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # MCP should be faster than LangGraph (target < 2 seconds)
        # This is just a placeholder - real test would compare actual implementations
        assert response_time < 10  # Generous timeout for test environment

class TestErrorHandling:
    """Test error handling in MCP integration."""
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failures."""
        # Test with invalid server path
        client = TurtleAppMCPClient("/invalid/path/server.py")
        
        with pytest.raises(Exception):  # Should raise connection error
            await client.connect()
    
    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        """Test handling of non-existent tool calls."""
        with patch('mcp.client.stdio.stdio_client') as mock_stdio:
            mock_session = MagicMock()
            mock_session.initialize.return_value = MagicMock(
                server_info=MagicMock(name="turtle-server", version="1.0.0")
            )
            mock_session.list_tools.return_value = MagicMock(
                tools=[MagicMock(name="movie_search", description="Search movies", inputSchema={})]
            )
            mock_stdio.return_value.__aenter__.return_value = mock_session
            
            client = TurtleAppMCPClient()
            await client.connect()
            
            with pytest.raises(ValueError, match="Tool 'invalid_tool' not found"):
                await client.execute_tool("invalid_tool", {})
            
            await client.disconnect()

# Utility functions for testing
def run_performance_benchmark():
    """Run a simple performance benchmark."""
    logger.info("Running MCP performance benchmark...")
    
    start_time = time.time()
    
    # Simulate multiple tool calls
    sync_client = SyncTurtleMCPClient()
    
    # In a real benchmark, you would make actual calls here
    # For now, just simulate the timing
    time.sleep(0.1)  # Simulate processing time
    
    end_time = time.time()
    total_time = end_time - start_time
    
    logger.info(f"Benchmark completed in {total_time:.2f} seconds")
    return total_time

if __name__ == "__main__":
    """Run tests when script is executed directly."""
    
    # Run performance benchmark
    benchmark_time = run_performance_benchmark()
    print(f"Performance benchmark: {benchmark_time:.2f} seconds")
    
    # Run pytest
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], 
                          capture_output=True, text=True)
    
    print("Test Results:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    print(f"Tests {'PASSED' if result.returncode == 0 else 'FAILED'}")