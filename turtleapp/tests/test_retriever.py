import pytest

from turtleapp.src.core.tools.movie_summaries_retriever import MovieRetrieverTool, movie_retriever
from turtleapp.src.nodes import ToolAgent


@pytest.fixture
def retriever_agent():
    """Fixture providing a retriever agent."""
    return ToolAgent([MovieRetrieverTool()])


@pytest.mark.asyncio
async def test_retriever_agent_response(retriever_agent):
    """Test that the retriever agent returns a valid response."""
    test_query = {"messages": "recommend 3 comedy movies"}
    response = await retriever_agent.process(test_query)
    
    assert response is not None
    assert 'messages' in response.update
    assert len(response.update['messages']) > 0


@pytest.mark.asyncio 
async def test_retriever_tool_interface():
    """Test the retriever tool interface."""
    result = MovieRetrieverTool()._run("comedy movies")
    assert isinstance(result, str)
    assert len(result) > 0