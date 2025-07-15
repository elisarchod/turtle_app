import pytest
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
    assert isinstance(result, str)
    assert len(result) > 0
