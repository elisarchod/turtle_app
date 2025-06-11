import unittest
from turtleapp.src.utils.log_handler import logger

from turtleapp.src.core.tools.movie_scanner import (
    MovieScannerTool,
    get_movies,
    is_movie_file,
    movie_scanner_tool
)


class TestMovieScanner(unittest.TestCase):
    
    def test_tool_interface(self):
        """Test MovieScannerTool interface"""
        tool = MovieScannerTool()
        self.assertEqual(tool.name, "movie_scanner")
        self.assertEqual(tool.description, "list of available movies")
        self.assertIsNotNone(movie_scanner_tool)
        self.assertIsInstance(movie_scanner_tool, MovieScannerTool)
    
    def test_tool_run(self):
        """Test tool _run method"""
        tool = MovieScannerTool()
        result = tool._run()
        
        self.assertIsInstance(result, str)
        self.assertIn("movies", result.lower())
    
    def test_get_movies(self):
        """Test get_movies function"""
        movies = get_movies()
        self.assertIsInstance(movies, list)
        
        print(f"\n=== Movie Scanner Results ===")
        print(f"Retrieved {len(movies)} items")
        
        if movies and movies[0].get('name') != 'Error':
            # If we have actual movies, check structure and show them
            print("Movies found:")
            for movie in movies:
                print(f"  - {movie['name']} at {movie['path']}")
            self.assertIn('name', movies[0])
            self.assertIn('path', movies[0])
        else:
            # Show error or empty result
            if movies:
                print(f"Scanner returned error: {movies[0]}")
            else:
                print("No movies found")
        print("=" * 30)

if __name__ == "__main__":
    unittest.main() 