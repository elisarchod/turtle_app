import unittest

from turtleapp.src.core.tools.torrent_tools import (
    get_downloading_torrents, 
    TorrentClientTool
)
from turtleapp.src.utils import logger

class TestTorrentTools(unittest.TestCase):
    
    def setUp(self):
        logger.info("Setting up torrent tools test")
    
    def test_list_torrents(self):
        logger.info("Testing list torrents functionality")
        torrents = get_downloading_torrents()
        self.assertIsInstance(torrents, list)
        if torrents:
            self.assertIn('name', torrents[0])
            self.assertIn('progress', torrents[0])
            logger.info(f"Found {len(torrents)} torrents")
        else:
            logger.info("No torrents found")

    def test_tool_interface(self):
        logger.info("Testing torrent tool interface")
        tool = TorrentClientTool()
        result = tool._run("list")
        self.assertIsInstance(result, str)
        self.assertIn("torrents", result.lower())
        logger.info("Torrent tool interface test completed")
