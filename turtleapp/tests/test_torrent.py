import unittest

from turtleapp.src.core.tools.torrent_tools import (
    get_downloading_torrents, 
    TorrentClientTool,
    search_torrents
)

class TestTorrentTools(unittest.TestCase):
    
    def test_list_torrents(self):
        """Test basic torrent listing"""
        torrents = get_downloading_torrents()
        self.assertIsInstance(torrents, list)
        if torrents:  # If we have torrents, check structure
            self.assertIn('name', torrents[0])
            self.assertIn('progress', torrents[0])

    def test_search_torrents(self):
        """Test torrent search"""
        results = search_torrents("test")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)  # Should at least return limitation message

    def test_tool_interface(self):
        """Test LangChain tool interface"""
        tool = TorrentClientTool()
        result = tool._run("list")
        self.assertIsInstance(result, str)
        self.assertIn("torrents", result.lower())

if __name__ == "__main__":
    unittest.main() 