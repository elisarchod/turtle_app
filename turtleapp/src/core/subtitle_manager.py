"""Core subtitle manager for OpenSubtitles.com API integration."""

from typing import List, Optional
from pathlib import Path
import re

from opensubtitles_com import OpenSubtitles
from opensubtitles_com.models import Subtitle

from turtleapp.settings import settings
from turtleapp.src.utils import handle_service_errors, logger


class SubtitleManager:
    """Wrapper around OpenSubtitles.com API for subtitle search and download."""

    def __init__(self):
        """Initialize OpenSubtitles client with credentials from settings."""
        self.client = OpenSubtitles(
            api_key=settings.opensubtitles.api_key,
            user_agent="TurtleApp/1.0"
        )
        self._token = None
        self._ensure_authenticated()

    @handle_service_errors("OpenSubtitles", default_return=None)
    def _ensure_authenticated(self):
        """Handle login and token management."""
        if not self._token:
            login_response = self.client.login(
                username=settings.opensubtitles.username,
                password=settings.opensubtitles.password
            )
            self._token = login_response.token
            logger.info("OpenSubtitles authentication successful")

    @handle_service_errors("OpenSubtitles", default_return=[])
    def search_subtitles(
        self,
        query: str,
        languages: List[str] = None,
        year: Optional[int] = None
    ) -> List[dict]:
        """
        Search subtitles by movie title.
        
        Args:
            query: Movie title to search for
            languages: List of ISO 639-1 language codes (default: English and Hebrew)
            year: Optional year to filter results
            
        Returns:
            List of subtitle dictionaries with file_id, language, downloads, rating
        """
        self._ensure_authenticated()
        
        if languages is None:
            languages = settings.opensubtitles.default_languages
        
        # Search for subtitles
        search_params = {
            "query": query,
            "languages": ",".join(languages)
        }
        
        if year:
            search_params["year"] = str(year)
        
        results = self.client.subtitles.search(**search_params)
        
        if not results:
            return []
        
        # Filter by year if provided
        filtered_results = []
        for subtitle in results:
            if year and subtitle.attributes.get("release"):
                # Extract year from release string if available
                release_year = self._extract_year(subtitle.attributes.get("release", ""))
                if release_year and release_year != year:
                    continue
            
            filtered_results.append({
                "file_id": subtitle.attributes.get("files", [{}])[0].get("file_id") if subtitle.attributes.get("files") else None,
                "language": subtitle.attributes.get("language"),
                "downloads": subtitle.attributes.get("download_count", 0),
                "rating": subtitle.attributes.get("ratings", 0),
                "release": subtitle.attributes.get("release", ""),
                "format": subtitle.attributes.get("format", ""),
                "title": subtitle.attributes.get("feature_details", {}).get("title", query) if subtitle.attributes.get("feature_details") else query,
                "year": subtitle.attributes.get("feature_details", {}).get("year") if subtitle.attributes.get("feature_details") else None
            })
        
        # Sort by downloads (most popular first)
        filtered_results.sort(key=lambda x: x["downloads"], reverse=True)
        
        return filtered_results

    @handle_service_errors("OpenSubtitles", default_return=False)
    def download_subtitle(self, file_id: int, save_path: str) -> bool:
        """
        Download subtitle file to specified path.
        
        Args:
            file_id: OpenSubtitles file ID
            save_path: Full path where subtitle should be saved (including .srt extension)
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_authenticated()
        
        # Download subtitle
        download_response = self.client.download(file_id=file_id)
        
        if not download_response or not download_response.link:
            logger.error(f"Failed to get download link for file_id {file_id}")
            return False
        
        # Download the actual subtitle file
        import requests
        subtitle_response = requests.get(download_response.link)
        subtitle_response.raise_for_status()
        subtitle_content = subtitle_response.content
        
        # Write to SMB path
        save_path_obj = Path(save_path)
        save_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path_obj, 'wb') as f:
            f.write(subtitle_content)
        
        logger.info(f"Subtitle downloaded successfully to {save_path}")
        return True

    def _extract_year(self, release_string: str) -> Optional[int]:
        """Extract year from release string (e.g., 'Inception.2010.1080p.BluRay' -> 2010)."""
        if not release_string:
            return None
        
        # Look for 4-digit year (1900-2099)
        year_match = re.search(r'\b(19|20)\d{2}\b', release_string)
        if year_match:
            return int(year_match.group())
        return None

    def _format_subtitle_info(self, subtitle_data: dict) -> str:
        """
        Format subtitle information for LLM consumption.
        
        Args:
            subtitle_data: Dictionary with subtitle information
            
        Returns:
            Formatted string describing the subtitle
        """
        parts = [
            f"Language: {subtitle_data.get('language', 'Unknown')}",
            f"Downloads: {subtitle_data.get('downloads', 0):,}",
        ]
        
        if subtitle_data.get('rating'):
            parts.append(f"Rating: {subtitle_data.get('rating')}/10")
        
        if subtitle_data.get('release'):
            parts.append(f"Release: {subtitle_data.get('release')}")
        
        if subtitle_data.get('format'):
            parts.append(f"Format: {subtitle_data.get('format')}")
        
        return " | ".join(parts)

