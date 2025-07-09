import pytest
from typing import List, Dict, Any

from turtleapp.src.utils import logger
from turtleapp.src.core.tools.library_manager import LibraryManagerTool


@pytest.fixture
def library_manager_tool():
    """Fixture to provide a LibraryManagerTool instance."""
    return LibraryManagerTool()


def test_interface(library_manager_tool):
    """Test the library manager tool interface."""
    assert library_manager_tool.name == "library_manager"


def test_tool_run(library_manager_tool):
    """Test the library manager tool execution."""
    result = library_manager_tool._run()
    assert isinstance(result, str), "Expected a string response"
    assert len(result) > 0, "Expected non-empty response"
    logger.info(f"Tool response: {result}")
