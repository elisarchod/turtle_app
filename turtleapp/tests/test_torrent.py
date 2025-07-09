import pytest

from turtleapp.src.core.tools.torrent_tools import (
    get_torrents, 
    TorrentClientTool
)
from turtleapp.src.utils import logger


@pytest.fixture
def torrent_tool():
    """Fixture to provide a TorrentClientTool instance."""
    return TorrentClientTool()


def test_list_torrents():
    """Test the list torrents functionality."""
    logger.info("Testing list torrents functionality")
    torrents = get_torrents(filter_downloading=True)
    assert isinstance(torrents, list)
    if torrents:
        assert 'name' in torrents[0]
        assert 'progress_percent' in torrents[0]
        logger.info(f"Found {len(torrents)} torrents")
    else:
        logger.info("No torrents found")


def test_tool_interface(torrent_tool):
    """Test the torrent tool interface."""
    logger.info("Testing torrent tool interface")
    result = torrent_tool._run("list")
    assert isinstance(result, str)
    assert "torrents" in result.lower()
    logger.info("Torrent tool interface test completed")
