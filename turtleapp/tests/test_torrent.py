import pytest
from unittest.mock import patch, MagicMock

from turtleapp.src.core.tools.torrent_tools import (
    get_torrents, 
    TorrentDownloadsTool,
    TorrentSearchTool
)


@pytest.fixture
def downloads_tool():
    """Fixture to provide a TorrentDownloadsTool instance."""
    return TorrentDownloadsTool()


@pytest.fixture
def search_tool():
    """Fixture to provide a TorrentSearchTool instance."""
    return TorrentSearchTool()


@patch('turtleapp.src.core.tools.torrent_tools.api_call')
def test_list_torrents(mock_api_call):
    """Test the list torrents functionality."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {'name': 'Test Movie', 'state': 'downloading', 'progress': 0.75}
    ]
    mock_api_call.return_value = mock_response
    
    torrents = get_torrents(filter_downloading=True)
    assert isinstance(torrents, list)
    assert len(torrents) == 1
    assert torrents[0]['progress_percent'] == 75.0


def test_downloads_tool_interface(downloads_tool):
    """Test the downloads tool interface."""
    result = downloads_tool._run("")
    assert isinstance(result, str)


def test_search_tool_interface(search_tool):
    """Test the search tool interface."""
    result = search_tool._run("test movie")
    assert isinstance(result, str)


@patch('turtleapp.src.core.tools.torrent_tools.api_call')
def test_error_handling(mock_api_call):
    """Test error handling returns fallback values."""
    mock_api_call.side_effect = Exception("Connection failed")
    
    # Should return empty list on error
    torrents = get_torrents(filter_downloading=True)
    assert isinstance(torrents, list)
    assert len(torrents) == 0