"""Subtitle search and download tools for OpenSubtitles.com."""

import re
from pathlib import Path
from typing import Optional

from langchain_core.tools import BaseTool

from turtleapp.src.core.subtitle_manager import SubtitleManager
from turtleapp.settings import settings
from turtleapp.src.utils import handle_tool_errors, logger


class SubtitleSearchTool(BaseTool):
    """Tool for searching subtitles on OpenSubtitles.com."""
    
    name: str = "search_subtitles"
    description: str = """Search for subtitles on OpenSubtitles.com by movie title.
    
    Use this tool when users want to:
    - Find available subtitles for a movie
    - Check subtitle availability in different languages
    - See subtitle quality indicators (downloads, ratings)
    
    Input format: Movie title with optional year and language
    Examples:
    - "Inception 2010"
    - "The Matrix English"
    - "Terminator 2 Hebrew"
    - "Avatar 2009"
    
    The tool will:
    1. Extract movie title, year (if present), and language preference
    2. Search OpenSubtitles.com database
    3. Return top 5 results with quality metrics
    
    Default languages: English and Hebrew (unless specified otherwise)
    """

    def __init__(self):
        super().__init__()
        self.manager = SubtitleManager()

    @handle_tool_errors(default_return="Subtitle search failed")
    def _run(self, query: str) -> str:
        """
        Search for subtitles.
        
        Args:
            query: Movie title with optional year and language
            
        Returns:
            Formatted string with top subtitle results
        """
        # Parse query for title, year, and language
        title, year, language = self._parse_query(query)
        
        languages = [language] if language else settings.opensubtitles.default_languages
        
        # Search subtitles
        results = self.manager.search_subtitles(
            query=title,
            languages=languages,
            year=year
        )
        
        if not results:
            return f"No subtitles found for '{title}'" + (f" ({year})" if year else "")
        
        # Format top 5 results
        result_text = f"Found {len(results)} subtitle(s) for '{title}'" + (f" ({year})" if year else "") + ":\n\n"
        
        for i, subtitle in enumerate(results[:5], 1):
            file_id = subtitle.get("file_id")
            if not file_id:
                continue
                
            result_text += f"{i}. File ID: {file_id}\n"
            result_text += f"   {self.manager._format_subtitle_info(subtitle)}\n"
            result_text += f"   Title: {subtitle.get('title', title)}\n"
            if subtitle.get('year'):
                result_text += f"   Year: {subtitle.get('year')}\n"
            result_text += "\n"
        
        return result_text

    def _parse_query(self, query: str) -> tuple[str, Optional[int], Optional[str]]:
        """
        Parse query string to extract title, year, and language.
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (title, year, language)
        """
        # Language mapping
        language_map = {
            "english": "en",
            "hebrew": "he",
            "en": "en",
            "he": "he"
        }
        
        # Extract year (4-digit number)
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        year = int(year_match.group()) if year_match else None
        
        # Extract language
        language = None
        query_lower = query.lower()
        for lang_key, lang_code in language_map.items():
            if lang_key in query_lower:
                language = lang_code
                break
        
        # Remove year and language from title
        title = query
        if year_match:
            title = title.replace(year_match.group(), "").strip()
        if language:
            for lang_key in language_map.keys():
                title = re.sub(rf'\b{lang_key}\b', '', title, flags=re.IGNORECASE).strip()
        
        # Clean up extra spaces
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title, year, language


class SubtitleDownloadTool(BaseTool):
    """Tool for downloading subtitles from OpenSubtitles.com."""
    
    name: str = "download_subtitle"
    description: str = """Download a specific subtitle file from OpenSubtitles.com.
    
    Use this tool when users want to:
    - Download a subtitle file they've selected
    - Save subtitles next to movie files
    
    Input format: "file_id|movie_path"
    Examples:
    - "12345678|/smb/movies/Inception.2010.1080p.mkv"
    - "87654321|/movies/The Matrix (1999)/The.Matrix.1999.mkv"
    
    The tool will:
    1. Extract file_id and movie_path from input
    2. Determine the subtitle save path (same directory, .srt extension)
    3. Download subtitle from OpenSubtitles.com
    4. Save to SMB share next to movie file
    
    Subtitle files are saved as: MovieName.Year.srt (or MovieName.srt if no year)
    """

    def __init__(self):
        super().__init__()
        self.manager = SubtitleManager()

    @handle_tool_errors(default_return="Subtitle download failed")
    def _run(self, input_str: str) -> str:
        """
        Download subtitle file.
        
        Args:
            input_str: Format "file_id|movie_path"
            
        Returns:
            Confirmation message with file location
        """
        # Parse input: "file_id|movie_path"
        parts = input_str.split("|", 1)
        if len(parts) != 2:
            return "Invalid input format. Expected: 'file_id|movie_path'"
        
        try:
            file_id = int(parts[0].strip())
        except ValueError:
            return f"Invalid file_id: {parts[0]}"
        
        movie_path = parts[1].strip()
        
        # Build subtitle save path
        save_path = self._build_subtitle_path(movie_path)
        
        # Download subtitle
        success = self.manager.download_subtitle(file_id, save_path)
        
        if success:
            return f"Subtitle downloaded successfully to: {save_path}"
        else:
            return f"Failed to download subtitle (file_id: {file_id})"

    def _build_subtitle_path(self, movie_path: str) -> str:
        """
        Build subtitle file path next to movie file.
        
        Args:
            movie_path: Path to movie file
            
        Returns:
            Path for subtitle file (.srt)
        """
        movie_path_obj = Path(movie_path)
        movie_dir = movie_path_obj.parent
        movie_stem = movie_path_obj.stem
        
        # Extract year from filename if present
        year_match = re.search(r'\b(19|20)\d{2}\b', movie_stem)
        if year_match:
            year = year_match.group()
            # Remove year from stem for cleaner subtitle name
            clean_stem = re.sub(r'\b(19|20)\d{2}\b', '', movie_stem).strip(' .-_')
            subtitle_name = f"{clean_stem}.{year}.srt"
        else:
            subtitle_name = f"{movie_stem}.srt"
        
        return str(movie_dir / subtitle_name)


# Export tool instances
subtitle_search_tool = SubtitleSearchTool()
subtitle_download_tool = SubtitleDownloadTool()

