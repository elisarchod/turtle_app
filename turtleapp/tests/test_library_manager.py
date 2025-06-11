import unittest
from typing import List, Dict, Any

from turtleapp.src.utils.log_handler import logger
from turtleapp.src.core.tools.library_manager import LibraryManagerTool


class TestLibraryManager(unittest.TestCase):

    def setUp(self):
        """Set up the test case"""
        self.tool = LibraryManagerTool()

    def test_interface(self):
        """Test LibraryManagerTool interface"""
        self.assertEqual(self.tool.name, "library_manager")

    def test_tool_run(self):
        """Test tool _run method"""
        result = self.tool._run()
        self.assertIsInstance(result, dict, "Expected a list of movies")
        self.assertGreater(len(result), 0, "Expected at least one movie in the result")
        logger.info(f"Example movie name: {list(result)[0]}")
