import unittest
from typing import List, Dict, Any

from turtleapp.src.utils import logger
from turtleapp.src.core.tools.library_manager import LibraryManagerTool


class TestLibraryManager(unittest.TestCase):

    def setUp(self):
        self.tool = LibraryManagerTool()

    def test_interface(self):
        self.assertEqual(self.tool.name, "library_manager")

    def test_tool_run(self):
        result = self.tool._run()
        self.assertIsInstance(result, str, "Expected a string response")
        self.assertGreater(len(result), 0, "Expected non-empty response")
        logger.info(f"Tool response: {result}")
