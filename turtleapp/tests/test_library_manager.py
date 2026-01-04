import pytest
from unittest.mock import patch, MagicMock
from turtleapp.src.core.tools.library_manager import LibraryManagerTool, scan_smb_movie_library
from turtleapp.src.utils.movie_names import extract_movie_metadata


@pytest.fixture
def library_manager_tool():
    """Fixture to provide a LibraryManagerTool instance."""
    return LibraryManagerTool()


@pytest.fixture
def mock_movies():
    """Fixture with sample movie data for testing."""
    return {
        "Terminator 2 Judgment Day": "/Movies/Terminator.2.1991.1080p.BluRay.mkv",
        "Inception 2010": "/Movies/Inception.2010.720p.BluRay.mp4",
        "The Dark Knight 2008": "/Movies/The.Dark.Knight.2008.1080p.BluRay.mkv",
        "Pulp Fiction 1994": "/Movies/Pulp.Fiction.1994.720p.BluRay.avi",
        "Avatar 2009": "/Movies/Avatar.2009.1080p.BluRay.mkv",
        "Matrix 1999": "/Movies/The.Matrix.1999.720p.BluRay.mp4",
    }


# Unit tests for helper methods
def test_parse_user_intent_specific_search(library_manager_tool):
    """Test parsing specific movie search queries."""
    query, fmt, intent = library_manager_tool._parse_user_intent("Do I have Inception?")
    assert "inception" in query.lower()
    assert fmt == ""
    assert intent == "specific_search"


def test_parse_user_intent_format_filter(library_manager_tool):
    """Test parsing file format filter queries."""
    query, fmt, intent = library_manager_tool._parse_user_intent("Show me MKV files")
    assert fmt == "mkv"
    assert intent == "format_filter"


def test_parse_user_intent_general(library_manager_tool):
    """Test parsing general library queries."""
    query, fmt, intent = library_manager_tool._parse_user_intent("What movies do I have?")
    assert intent == "general_scan"


def test_filter_by_extension(library_manager_tool, mock_movies):
    """Test filtering movies by file extension."""
    filtered = library_manager_tool._filter_by_extension(mock_movies, "mkv")
    assert len(filtered) == 3
    assert all(".mkv" in path.lower() for path in filtered.values())


def test_search_movies_exact_match(library_manager_tool, mock_movies):
    """Test exact title match in search."""
    results = library_manager_tool._search_movies(mock_movies, "Inception", limit=5)
    assert len(results) > 0
    assert results[0][0] == "Inception 2010"
    assert results[0][2] == 1.0  # Exact match score


def test_search_movies_fuzzy_match(library_manager_tool, mock_movies):
    """Test fuzzy matching handles typos."""
    results = library_manager_tool._search_movies(mock_movies, "Terminater", limit=5)
    assert len(results) > 0
    # Should find "Terminator 2 Judgment Day" despite typo
    assert any("Terminator" in name for name, _, _ in results)


def test_search_movies_partial_keywords(library_manager_tool, mock_movies):
    """Test search with multiple keywords."""
    results = library_manager_tool._search_movies(mock_movies, "dark knight", limit=5)
    assert len(results) > 0
    assert any("Dark Knight" in name for name, _, _ in results)


def test_extract_metadata():
    """Test metadata extraction from filenames."""
    metadata = extract_movie_metadata("Terminator.2.1991.1080p.BluRay.mkv")
    assert metadata['year'] == "1991"
    assert metadata['quality'] == "1080p"
    assert metadata['format'] == ".mkv"
    assert "Terminator" in metadata['title']


def test_format_output_tier1(library_manager_tool, mock_movies):
    """Test Tier 1 output (1-5 specific results)."""
    results = [
        ("Terminator 2 Judgment Day", "/path/to/movie.mkv", 1.0)
    ]
    output = library_manager_tool._format_output(mock_movies, results, "Terminator", "specific_search")
    assert "Found 1 movie" in output
    assert "Terminator" in output
    assert "Format:" in output


def test_format_output_tier2(library_manager_tool, mock_movies):
    """Test Tier 2 output (6-20 results)."""
    results = [
        (f"Movie {i}", f"/path/to/movie{i}.mkv", 0.9) for i in range(10)
    ]
    output = library_manager_tool._format_output(mock_movies, results, "movie", "specific_search")
    assert "Found 10 movies" in output
    assert "Top matches:" in output
    assert "... and 5 more" in output


def test_format_output_tier3(library_manager_tool, mock_movies):
    """Test Tier 3 output (general statistics)."""
    results = [
        (f"Movie {i}", f"/path/to/movie{i}.mkv", 1.0) for i in range(25)
    ]
    output = library_manager_tool._format_output(mock_movies, results, "", "general_scan")
    assert "Library scan completed" in output
    assert "Found" in output
    assert "Sample movies:" in output


# Integration tests (require SMB - mark as expensive)
@pytest.mark.expensive
@patch('turtleapp.src.core.tools.library_manager.scan_smb_movie_library')
def test_tool_specific_movie_search(mock_scan, library_manager_tool, mock_movies):
    """Test tool with specific movie search query."""
    mock_scan.return_value = mock_movies
    result = library_manager_tool._run("Do I have Terminator 2?")
    assert isinstance(result, str)
    assert "Terminator" in result or "Found" in result


@pytest.mark.expensive
@patch('turtleapp.src.core.tools.library_manager.scan_smb_movie_library')
def test_tool_format_filter(mock_scan, library_manager_tool, mock_movies):
    """Test tool with file format filter."""
    mock_scan.return_value = mock_movies
    result = library_manager_tool._run("Show me MKV files")
    assert isinstance(result, str)
    # Should mention MKV or show filtered results


@pytest.mark.expensive
@patch('turtleapp.src.core.tools.library_manager.scan_smb_movie_library')
def test_tool_general_scan(mock_scan, library_manager_tool, mock_movies):
    """Test tool with general library scan."""
    mock_scan.return_value = mock_movies
    result = library_manager_tool._run("What movies do I have?")
    assert isinstance(result, str)
    assert "Library scan completed" in result or "Found" in result


# Original test (keep for backward compatibility)
def test_tool_run(library_manager_tool):
    """Test the library manager tool execution."""
    with patch('turtleapp.src.core.tools.library_manager.scan_smb_movie_library') as mock_scan:
        mock_scan.return_value = {"Test Movie": "/path/to/test.mkv"}
        result = library_manager_tool._run("")
        assert isinstance(result, str)
